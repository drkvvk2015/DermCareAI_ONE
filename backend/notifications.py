from __future__ import annotations

import os
from typing import Any, Dict

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from auth import require_roles

router = APIRouter(prefix="/notifications", tags=["notifications"])
ALLOWED_CHANNELS = {"whatsapp", "sms", "social_webhook"}


class RegistrationNotification(BaseModel):
    patient_name: str = Field(min_length=1, max_length=120)
    phone: str = Field(min_length=5, max_length=30)
    appointment_text: str = Field(min_length=1, max_length=500)
    template_name: str = Field(default="patient_registration", min_length=1, max_length=120)
    template_language: str = "en"
    channels: list[str] = ["whatsapp", "sms"]


async def send_whatsapp(req: RegistrationNotification) -> Dict[str, Any]:
    token = os.getenv("META_WHATSAPP_ACCESS_TOKEN")
    phone_number_id = os.getenv("META_WHATSAPP_PHONE_NUMBER_ID")
    if not token or not phone_number_id:
        return {"channel": "whatsapp", "status": "not_configured"}
    url = f"https://graph.facebook.com/v23.0/{phone_number_id}/messages"
    payload = {"messaging_product": "whatsapp", "to": req.phone, "type": "template", "template": {"name": req.template_name, "language": {"code": req.template_language}, "components": [{"type": "body", "parameters": [{"type": "text", "text": req.patient_name}, {"type": "text", "text": req.appointment_text}]}]}}
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(url, headers={"Authorization": f"Bearer {token}"}, json=payload)
    if r.status_code >= 400:
        raise HTTPException(status_code=502, detail="WhatsApp provider rejected the message")
    return {"channel": "whatsapp", "status": "sent", "provider_message_id": r.json().get("messages", [{}])[0].get("id")}


async def send_sms(req: RegistrationNotification) -> Dict[str, Any]:
    url = os.getenv("SMS_PROVIDER_URL")
    token = os.getenv("SMS_PROVIDER_TOKEN")
    sender = os.getenv("SMS_SENDER_ID")
    if not url or not token or not sender:
        return {"channel": "sms", "status": "not_configured"}
    payload = {"to": req.phone, "sender": sender, "template": req.template_name, "message": f"Dear {req.patient_name}, {req.appointment_text}"}
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(url, headers={"Authorization": f"Bearer {token}"}, json=payload)
    if r.status_code >= 400:
        raise HTTPException(status_code=502, detail="SMS provider rejected the message")
    return {"channel": "sms", "status": "sent", "provider_response": r.json() if "application/json" in r.headers.get("content-type", "") else r.text}


async def social_safe_webhook(req: RegistrationNotification) -> Dict[str, Any]:
    url = os.getenv("SOCIAL_NOTIFICATION_WEBHOOK_URL")
    if not url:
        return {"channel": "social_webhook", "status": "not_configured"}
    payload = {"event": "patient_registration", "event_version": "v1"}
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(url, json=payload)
    if r.status_code >= 400:
        raise HTTPException(status_code=502, detail="Social notification webhook failed")
    return {"channel": "social_webhook", "status": "sent"}


@router.post("/registration")
async def registration_notifications(req: RegistrationNotification, _: dict[str, Any] = Depends(require_roles("admin", "receptionist", "doctor"))):
    unknown = sorted(set(req.channels) - ALLOWED_CHANNELS)
    if unknown:
        raise HTTPException(status_code=400, detail=f"Unsupported notification channel(s): {', '.join(unknown)}")

    results: list[Dict[str, Any]] = []
    for channel in req.channels:
        if channel == "whatsapp":
            results.append(await send_whatsapp(req))
        elif channel == "sms":
            results.append(await send_sms(req))
        elif channel == "social_webhook":
            results.append(await social_safe_webhook(req))
    return {"results": results}
