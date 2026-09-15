from __future__ import annotations

import hashlib
import hmac
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

import httpx
from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel, Field

router = APIRouter(prefix="/commerce", tags=["commerce"])


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class InvoiceItem(BaseModel):
    description: str = Field(min_length=1, max_length=300)
    quantity: float = Field(gt=0)
    unit_price: float = Field(ge=0)
    tax_percent: float = Field(ge=0, le=100, default=0)


class InvoiceRequest(BaseModel):
    patient_id: str = Field(min_length=1)
    items: List[InvoiceItem]
    discount: float = Field(ge=0, default=0)
    currency: str = Field(default="INR", min_length=3, max_length=3)


class PaymentRequest(BaseModel):
    invoice_id: str = Field(min_length=1)
    # Kept optional for client compatibility; the server derives the payable
    # amount from the stored invoice and never trusts this field.
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
    subtotal = sum(item.quantity * item.unit_price for item in req.items)
    taxable = sum(item.quantity * item.unit_price * (item.tax_percent / 100) for item in req.items)
    total = max(0.0, subtotal + taxable - req.discount)
    invoice_id = f"INV-{uuid.uuid4().hex[:10].upper()}"
    invoice = {
        "id": invoice_id,
        "patient_id": req.patient_id,
        "items": [item.model_dump() for item in req.items],
        "subtotal": round(subtotal, 2),
        "tax": round(taxable, 2),
        "discount": round(req.discount, 2),
        "total": round(total, 2),
        "currency": req.currency.upper(),
        "status": "unpaid",
        "created_at": now_iso(),
    }
    INVOICES[invoice_id] = invoice
    return invoice


@router.post("/invoices")
def create_invoice(req: InvoiceRequest):
    return compute_invoice(req)


@router.get("/invoices/{invoice_id}")
def get_invoice(invoice_id: str):
    invoice = INVOICES.get(invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice


@router.post("/payments/razorpay")
async def create_razorpay_payment(req: PaymentRequest):
    invoice = INVOICES.get(req.invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    if invoice.get("status") != "unpaid":
        raise HTTPException(status_code=409, detail="Invoice is not payable")
    if str(invoice.get("currency", "INR")).upper() != "INR":
        raise HTTPException(status_code=400, detail="Razorpay payment links require an INR invoice")

    amount_paise = int(round(float(invoice["total"]) * 100))
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
        "customer": {
            "name": req.customer_name,
            "contact": req.customer_phone,
            "email": req.customer_email,
        },
        "notify": {"sms": False, "email": False},
        "reminder_enable": True,
    }
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(
            "https://api.razorpay.com/v1/payment_links",
            auth=(key_id, key_secret),
            json=payload,
        )
    if response.status_code >= 400:
        raise HTTPException(status_code=502, detail="Unable to create payment link")
    data = response.json()
    return {
        "provider": "razorpay",
        "id": data.get("id"),
        "short_url": data.get("short_url"),
        "status": data.get("status"),
        "invoice_id": req.invoice_id,
        "amount_paise": amount_paise,
        "upi_supported": True,
        "note": "Use UPI Intent/QR through the hosted checkout; do not use deprecated UPI Collect flows.",
    }


@router.post("/payments/webhook")
async def payment_webhook(
    request: Request,
    x_razorpay_signature: str | None = Header(default=None, alias="X-Razorpay-Signature"),
):
    secret = os.getenv("RAZORPAY_WEBHOOK_SECRET")
    raw_body = await request.body()
    if secret:
        if not x_razorpay_signature:
            raise HTTPException(status_code=401, detail="Missing webhook signature")
        expected = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, x_razorpay_signature):
            raise HTTPException(status_code=401, detail="Invalid webhook signature")

    try:
        payload = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid webhook JSON") from exc

    entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
    notes = entity.get("notes") or {}
    reference_id = notes.get("invoice_id") or entity.get("order_id")
    if reference_id in INVOICES:
        INVOICES[reference_id]["status"] = "paid"
        INVOICES[reference_id]["paid_at"] = now_iso()
        INVOICES[reference_id]["razorpay_payment_id"] = entity.get("id")
    return {"received": True}


@router.post("/pharmacy/stock")
def add_stock(item: Dict[str, Any]):
    medicine_id = str(item.get("medicine_id", "")).strip()
    if not medicine_id:
        raise HTTPException(status_code=400, detail="medicine_id is required")
    PHARMACY_STOCK[medicine_id] = {
        **item,
        "updated_at": now_iso(),
    }
    return PHARMACY_STOCK[medicine_id]


@router.get("/pharmacy/stock")
def list_stock():
    return list(PHARMACY_STOCK.values())


@router.post("/pharmacy/dispense")
def dispense(req: DispenseRequest):
    # Aggregate first so duplicate lines cannot bypass a stock check.
    required: Dict[str, float] = {}
    for item in req.items:
        required[item.medicine_id] = required.get(item.medicine_id, 0.0) + float(item.quantity)

    # Validate the complete request before mutating any inventory.
    for medicine_id, requested_qty in required.items():
        stock = PHARMACY_STOCK.get(medicine_id)
        if not stock:
            raise HTTPException(status_code=404, detail=f"Medicine {medicine_id} not found")
        available = float(stock.get("quantity", 0))
        if available < requested_qty:
            raise HTTPException(status_code=409, detail=f"Insufficient stock for {medicine_id}")

    now = now_iso()
    for medicine_id, requested_qty in required.items():
        stock = PHARMACY_STOCK[medicine_id]
        stock["quantity"] = float(stock.get("quantity", 0)) - requested_qty
        stock["updated_at"] = now

    return {
        "patient_id": req.patient_id,
        "prescription_id": req.prescription_id,
        "dispensed": [item.model_dump() for item in req.items],
        "dispensed_at": now,
    }
