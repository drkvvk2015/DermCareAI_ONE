from __future__ import annotations

import asyncio
import os
from typing import Any, Dict

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field

from auth import require_roles
from notification_outbox import claim_batch, enqueue_registration, mark_failed, mark_sent


router = APIRouter(prefix="/notifications", tags=["notifications"])
ALLOWED_CHANNELS = {"whatsapp", "sms", "social_webhook"}
_worker_task: asyncio.Task[None] | None = None
_worker_stop: asyncio.Event | None = None


class RegistrationNotification(BaseModel):
    patient_name: str = Field(min_length=1, max_length=120)
    phone: str = Field(min_length=5, max_length=30)
    appointment_text: str = Field(min_length=1, max_length=500)
    template_name: str = Field(default="patient_registration", min_length=1, max_length=120)
    template_language: str = Field(default="en", min_length=2, max_length=20)
    channels: list[str] = Field(default_factory=lambda: ["whatsapp", "sms"])


def _tenant(user: dict[str, Any]) -> tuple[str, str]:
    claims = user.get("claims", {})
    organization_id = claims.get("organization_id") or claims.get("organizationId")
    clinic_id = claims.get("clinic_id") or claims.get("clinicId")
    if not organization_id or not clinic_id:
        raise HTTPException(status_code=403, detail="Notification tenant context is missing")
    return str(organization_id), str(clinic_id)


async def send_whatsapp(req: RegistrationNotification) -> Dict[str, Any]:
    token = os.getenv("META_WHATSAPP_ACCESS_TOKEN")
    phone_number_id = os.getenv("META_WHATSAPP_PHONE_NUMBER_ID")
    if not token or not phone_number_id:
        return {"channel": "whatsapp", "status": "not_configured"}
    url = f"https://graph.facebook.com/v23.0/{phone_number_id}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "to": req.phone,
        "type": "template",
        "template": {
            "name": req.template_name,
            "language": {"code": req.template_language},
            "components": [{
                "type": "body",
                "parameters": [
                    {"type": "text", "text": req.patient_name},
                    {"type": "text", "text": req.appointment_text},
                ],
            }],
        },
    }
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(
            url,
            headers={"Authorization": f"Bearer {token}"},
            json=payload,
        )
    if response.status_code >= 400:
        raise RuntimeError("WhatsApp provider rejected the message")
    messages = response.json().get("messages", [])
    return {
        "channel": "whatsapp",
        "status": "sent",
        "provider_message_id": messages[0].get("id") if messages else None,
    }


async def send_sms(req: RegistrationNotification) -> Dict[str, Any]:
    url = os.getenv("SMS_PROVIDER_URL")
    token = os.getenv("SMS_PROVIDER_TOKEN")
    sender = os.getenv("SMS_SENDER_ID")
    if not url or not token or not sender:
        return {"channel": "sms", "status": "not_configured"}
    payload = {
        "to": req.phone,
        "sender": sender,
        "template": req.template_name,
        "message": f"Dear {req.patient_name}, {req.appointment_text}",
    }
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(
            url,
            headers={"Authorization": f"Bearer {token}"},
            json=payload,
        )
    if response.status_code >= 400:
        raise RuntimeError("SMS provider rejected the message")
    return {"channel": "sms", "status": "sent", "provider_message_id": None}


async def social_safe_webhook(req: RegistrationNotification) -> Dict[str, Any]:
    url = os.getenv("SOCIAL_NOTIFICATION_WEBHOOK_URL")
    if not url:
        return {"channel": "social_webhook", "status": "not_configured"}
    payload = {"event": "patient_registration", "event_version": "v1"}
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(url, json=payload)
    if response.status_code >= 400:
        raise RuntimeError("Social notification webhook failed")
    return {"channel": "social_webhook", "status": "sent", "provider_message_id": None}


async def _deliver(row: dict[str, Any]) -> None:
    req = RegistrationNotification.model_validate(__import__("json").loads(row["payload_json"]))
    try:
        if row["channel"] == "whatsapp":
            result = await send_whatsapp(req)
        elif row["channel"] == "sms":
            result = await send_sms(req)
        else:
            result = await social_safe_webhook(req)
        status = result.get("status")
        if status == "not_configured":
            mark_failed(row_id=row["id"], error=f"{row['channel']} provider is not configured", max_attempts=1)
            return
        mark_sent(
            row_id=row["id"],
            provider_message_id=result.get("provider_message_id"),
        )
    except Exception as exc:
        mark_failed(row_id=row["id"], error=str(exc))


async def _worker_loop() -> None:
    assert _worker_stop is not None
    while not _worker_stop.is_set():
        rows = await asyncio.to_thread(claim_batch)
        if rows:
            await asyncio.gather(*[_deliver(row) for row in rows])
            continue
        try:
            await asyncio.wait_for(_worker_stop.wait(), timeout=5)
        except asyncio.TimeoutError:
            pass


def start_notification_worker() -> None:
    global _worker_task, _worker_stop
    if _worker_task is not None and not _worker_task.done():
        return
    _worker_stop = asyncio.Event()
    _worker_task = asyncio.create_task(_worker_loop(), name="dermcareai-notification-outbox")


async def stop_notification_worker() -> None:
    global _worker_task, _worker_stop
    if _worker_task is None:
        return
    if _worker_stop is not None:
        _worker_stop.set()
    try:
        await asyncio.wait_for(_worker_task, timeout=10)
    except asyncio.TimeoutError:
        _worker_task.cancel()
        await asyncio.gather(_worker_task, return_exceptions=True)
    finally:
        _worker_task = None
        _worker_stop = None


@router.post("/registration")
async def registration_notifications(
    req: RegistrationNotification,
    idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=8, max_length=200),
    user: dict[str, Any] = Depends(require_roles("admin", "receptionist", "doctor")),
):
    organization_id, clinic_id = _tenant(user)
    unknown = sorted(set(req.channels) - ALLOWED_CHANNELS)
    if unknown:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported notification channel(s): {', '.join(unknown)}",
        )

    if not req.channels:
        raise HTTPException(status_code=400, detail="At least one notification channel is required")

    rows = await asyncio.to_thread(
        enqueue_registration,
        organization_id=organization_id,
        clinic_id=clinic_id,
        event_key=idempotency_key,
        payload=req.model_dump(),
        channels=req.channels,
    )
    return {
        "status": "queued",
        "event_key": idempotency_key,
        "results": [
            {
                "channel": row["channel"],
                "status": row["status"],
                "attempts": row["attempts"],
                "notification_id": row["id"],
                "last_error": row.get("last_error"),
            }
            for row in rows
        ],
    }
