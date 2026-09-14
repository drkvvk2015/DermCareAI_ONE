from __future__ import annotations

import hashlib
import hmac
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

import httpx
from fastapi import APIRouter, HTTPException
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
    amount: int = Field(gt=0, description="Amount in paise")
    customer_name: str = Field(min_length=1)
    customer_phone: str = Field(min_length=5)
    customer_email: str | None = None


class DispenseItem(BaseModel):
    medicine_id: str = Field(min_length=1)
    quantity: float = Field(gt=0)


class DispenseRequest(BaseModel):
    patient_id: str = Field(min_length=1)
    prescription_id: str | None = None
    items: List[DispenseItem]


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
    key_id = os.getenv("RAZORPAY_KEY_ID")
    key_secret = os.getenv("RAZORPAY_KEY_SECRET")
    if not key_id or not key_secret:
        raise HTTPException(status_code=503, detail="Razorpay is not configured")

    payload = {
        "amount": req.amount,
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
        "upi_supported": True,
        "note": "Use UPI Intent/QR through the hosted checkout; do not use deprecated UPI Collect flows.",
    }


@router.post("/payments/webhook")
async def payment_webhook(payload: Dict[str, Any], x_razorpay_signature: str | None = None):
    secret = os.getenv("RAZORPAY_WEBHOOK_SECRET")
    raw = payload.get("_raw_body")
    if secret and raw and x_razorpay_signature:
        expected = hmac.new(secret.encode(), raw.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, x_razorpay_signature):
            raise HTTPException(status_code=401, detail="Invalid webhook signature")
    entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
    reference_id = entity.get("notes", {}).get("invoice_id") or entity.get("order_id")
    if reference_id in INVOICES:
        INVOICES[reference_id]["status"] = "paid"
        INVOICES[reference_id]["paid_at"] = now_iso()
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
    dispensed: list[Dict[str, Any]] = []
    for item in req.items:
        stock = PHARMACY_STOCK.get(item.medicine_id)
        if not stock:
            raise HTTPException(status_code=404, detail=f"Medicine {item.medicine_id} not found")
        available = float(stock.get("quantity", 0))
        if available < item.quantity:
            raise HTTPException(status_code=409, detail=f"Insufficient stock for {item.medicine_id}")
        stock["quantity"] = available - item.quantity
        stock["updated_at"] = now_iso()
        dispensed.append({"medicine_id": item.medicine_id, "quantity": item.quantity})
    return {"patient_id": req.patient_id, "prescription_id": req.prescription_id, "dispensed": dispensed, "dispensed_at": now_iso()}
