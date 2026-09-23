from __future__ import annotations

import hashlib
import hmac
import os
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field

from auth import require_roles
from billing_math import BillLine, invoice_total, money
from commerce_store import atomic_dispense, get_invoice as store_get_invoice, list_stock as store_list_stock
from commerce_store import record_payment_event, save_invoice, upsert_stock, update_invoice

router = APIRouter(prefix="/commerce", tags=["commerce"])


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def verify_razorpay_signature(raw_body: bytes, secret: str, signature: str | None) -> bool:
    if not signature:
        return False
    expected = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


class InvoiceItem(BaseModel):
    description: str = Field(min_length=1, max_length=300)
    quantity: Decimal = Field(gt=0)
    unit_price: Decimal = Field(ge=0)
    tax_percent: Decimal = Field(ge=0, le=100, default=Decimal("0"))


class InvoiceRequest(BaseModel):
    patient_id: str = Field(min_length=1)
    items: List[InvoiceItem] = Field(min_length=1)
    discount: Decimal = Field(ge=0, default=Decimal("0"))
    currency: str = Field(default="INR", min_length=3, max_length=3)


class PaymentRequest(BaseModel):
    invoice_id: str = Field(min_length=1)
    amount: int | None = Field(default=None, gt=0, description="Deprecated client value; ignored for pricing")
    customer_name: str = Field(min_length=1)
    customer_phone: str = Field(min_length=5)
    customer_email: str | None = None


class DispenseItem(BaseModel):
    medicine_id: str = Field(min_length=1)
    quantity: float = Field(gt=0)


class DispenseRequest(BaseModel):
    patient_id: str = Field(min_length=1)
    prescription_id: str | None = None
    items: List[DispenseItem] = Field(min_length=1)


INVOICES: Dict[str, Dict[str, Any]] = {}
PHARMACY_STOCK: Dict[str, Dict[str, Any]] = {}


def compute_invoice(req: InvoiceRequest) -> Dict[str, Any]:
    lines = [
        BillLine(
            description=item.description,
            quantity=item.quantity,
            unit_price=item.unit_price,
            tax_percent=item.tax_percent,
        )
        for item in req.items
    ]
    subtotal, tax, total = invoice_total(lines, req.discount)
    invoice_id = f"INV-{uuid.uuid4().hex[:10].upper()}"
    invoice = {
        "id": invoice_id,
        "patient_id": req.patient_id,
        "items": [
            {
                **item.model_dump(),
                "quantity": money(item.quantity),
                "unit_price": money(item.unit_price),
                "tax_percent": money(item.tax_percent),
            }
            for item in req.items
        ],
        "subtotal": subtotal,
        "tax": tax,
        "discount": money(req.discount),
        "total": total,
        "currency": req.currency.upper(),
        "status": "unpaid",
        "created_at": now_iso(),
    }
    INVOICES[invoice_id] = invoice
    save_invoice(invoice)
    return invoice


@router.post("/invoices")
def create_invoice(req: InvoiceRequest, _: dict[str, Any] = Depends(require_roles("admin", "doctor", "receptionist", "billing"))):
    return compute_invoice(req)


@router.get("/invoices/{invoice_id}")
def get_invoice(invoice_id: str, _: dict[str, Any] = Depends(require_roles("admin", "doctor", "receptionist", "billing"))):
    invoice = INVOICES.get(invoice_id) or store_get_invoice(invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    INVOICES[invoice_id] = invoice
    return invoice


@router.post("/payments/razorpay")
async def create_razorpay_payment(req: PaymentRequest, _: dict[str, Any] = Depends(require_roles("admin", "doctor", "receptionist", "billing"))):
    invoice = INVOICES.get(req.invoice_id) or store_get_invoice(req.invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    if invoice.get("status") != "unpaid":
        raise HTTPException(status_code=409, detail="Invoice is not payable")
    if str(invoice.get("currency", "INR")).upper() != "INR":
        raise HTTPException(status_code=400, detail="Razorpay payment links require an INR invoice")

    amount_paise = int(money(invoice["total"]) * 100)
    if amount_paise <= 0:
        raise HTTPException(status_code=400, detail="Invoice total must be greater than zero")

    key_id = os.getenv("RAZORPAY_KEY_ID")
    key_secret = os.getenv("RAZORPAY_KEY_SECRET")
    if not key_id or not key_secret:
        raise HTTPException(status_code=503, detail="Razorpay is not configured")

    payload = {
        "amount": amount_paise,
        "currency": "INR",
        "accept_partial": False,
        "reference_id": req.invoice_id,
        "description": f"DermCareAI invoice {req.invoice_id}",
        "customer": {"name": req.customer_name, "contact": req.customer_phone, "email": req.customer_email},
        "notify": {"sms": False, "email": False},
        "reminder_enable": True,
    }
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post("https://api.razorpay.com/v1/payment_links", auth=(key_id, key_secret), json=payload)
    if response.status_code >= 400:
        raise HTTPException(status_code=502, detail="Unable to create payment link")
    data = response.json()
    invoice["razorpay_payment_link_id"] = data.get("id")
    INVOICES[invoice["id"]] = invoice
    update_invoice(invoice)
    return {"provider": "razorpay", "id": data.get("id"), "short_url": data.get("short_url"), "status": data.get("status"), "invoice_id": req.invoice_id, "amount_paise": amount_paise, "upi_supported": True, "note": "Use UPI Intent/QR through the hosted checkout; do not use deprecated UPI Collect flows."}


@router.post("/payments/webhook")
async def payment_webhook(request: Request, x_razorpay_signature: str | None = Header(default=None, alias="X-Razorpay-Signature")):
    secret = os.getenv("RAZORPAY_WEBHOOK_SECRET")
    if not secret:
        raise HTTPException(status_code=503, detail="Webhook signing secret is not configured")
    raw_body = await request.body()
    if not verify_razorpay_signature(raw_body, secret, x_razorpay_signature):
        raise HTTPException(status_code=401, detail="Missing or invalid webhook signature")
    try:
        payload = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid webhook JSON") from exc

    event_id = str(payload.get("id") or hashlib.sha256(raw_body).hexdigest())
    entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
    notes = entity.get("notes") or {}
    reference_id = notes.get("invoice_id") or entity.get("order_id") or entity.get("reference_id")
    invoice = INVOICES.get(reference_id) or store_get_invoice(reference_id) if reference_id else None
    if invoice is None:
        record_payment_event(event_id, payload)
        return {"received": True, "ignored": True, "reason": "invoice_not_found"}

    expected_amount = int(money(invoice["total"]) * 100)
    provider_amount = int(entity.get("amount") or 0)
    if provider_amount != expected_amount:
        raise HTTPException(status_code=409, detail="Payment amount does not match invoice total")

    payment_id = entity.get("id")
    if invoice.get("status") == "paid" and invoice.get("razorpay_payment_id") == payment_id:
        record_payment_event(event_id, payload)
        return {"received": True, "idempotent": True}

    if invoice.get("status") != "unpaid":
        raise HTTPException(status_code=409, detail="Invoice is already settled by another payment")

    invoice["status"] = "paid"
    invoice["paid_at"] = now_iso()
    invoice["razorpay_payment_id"] = payment_id
    invoice["paid_amount_paise"] = provider_amount
    INVOICES[invoice["id"]] = invoice
    update_invoice(invoice)
    if not record_payment_event(event_id, payload):
        return {"received": True, "idempotent": True}
    return {"received": True, "updated": True}


@router.post("/pharmacy/stock")
def add_stock(item: Dict[str, Any], _: dict[str, Any] = Depends(require_roles("admin", "pharmacist"))):
    medicine_id = str(item.get("medicine_id", "")).strip()
    if not medicine_id:
        raise HTTPException(status_code=400, detail="medicine_id is required")
    item = {**item, "medicine_id": medicine_id, "quantity": float(item.get("quantity", 0))}
    saved = upsert_stock(item)
    PHARMACY_STOCK[medicine_id] = saved
    return saved


@router.get("/pharmacy/stock")
def list_stock(_: dict[str, Any] = Depends(require_roles("admin", "pharmacist", "doctor"))):
    items = store_list_stock()
    PHARMACY_STOCK.clear()
    PHARMACY_STOCK.update({str(item["medicine_id"]): item for item in items})
    return items


@router.post("/pharmacy/dispense")
def dispense(req: DispenseRequest, _: dict[str, Any] = Depends(require_roles("admin", "pharmacist", "doctor"))):
    required: Dict[str, float] = {}
    for item in req.items:
        required[item.medicine_id] = required.get(item.medicine_id, 0.0) + float(item.quantity)
    try:
        updated = atomic_dispense(required)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Medicine {exc.args[0]} not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=f"Insufficient stock for {exc.args[0]}") from exc
    PHARMACY_STOCK.update(updated)
    return {
        "patient_id": req.patient_id,
        "prescription_id": req.prescription_id,
        "dispensed": [item.model_dump() for item in req.items],
        "dispensed_at": now_iso(),
    }
