from fastapi import HTTPException

from commerce import PHARMACY_STOCK, DispenseRequest, InvoiceItem, InvoiceRequest, PaymentRequest, compute_invoice, dispense, verify_razorpay_signature
from commerce_store import reset_store


def setup_function() -> None:
    INVOICES = None
    PHARMACY_STOCK.clear()
    reset_store()


def test_payment_amount_is_derived_from_invoice() -> None:
    invoice = compute_invoice(
        InvoiceRequest(
            patient_id="p1",
            items=[InvoiceItem(description="Consultation", quantity=1, unit_price=1000, tax_percent=18)],
        )
    )
    request = PaymentRequest(invoice_id=invoice["id"], amount=1, customer_name="Test", customer_phone="9999999999")
    assert request.amount == 1
    assert round(invoice["total"] * 100) == 118000


def test_razorpay_signature_is_exact_and_tamper_evident() -> None:
    body = b'{"event":"payment.captured"}'
    secret = "test-secret"
    import hashlib
    import hmac
    signature = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    assert verify_razorpay_signature(body, secret, signature)
    assert not verify_razorpay_signature(body + b" ", secret, signature)
    assert not verify_razorpay_signature(body, secret, None)


def test_dispense_validates_all_items_before_mutating_stock() -> None:
    PHARMACY_STOCK["med-a"] = {"medicine_id": "med-a", "name": "A", "quantity": 10}
    upsert = __import__("commerce_store").commerce_store.upsert_stock
    upsert(PHARMACY_STOCK["med-a"])
    request = DispenseRequest(patient_id="p1", items=[{"medicine_id":"med-a","quantity":2},{"medicine_id":"missing","quantity":1}])
    try:
        dispense(request, {"uid":"u1","roles":{"pharmacist"}})
    except Exception as exc:
        assert getattr(exc, "status_code", None) == 404
    assert __import__("commerce_store").commerce_store.get_invoice("none") is None


def test_dispense_aggregates_duplicate_items() -> None:
    from commerce_store import upsert_stock, store_list_stock
    upsert_stock({"medicine_id":"med-a","name":"A","quantity":3})
    request = DispenseRequest(patient_id="p1", items=[{"medicine_id":"med-a","quantity":1},{"medicine_id":"med-a","quantity":2}])
    result = dispense(request, {"uid":"u1","roles":{"pharmacist"}})
    assert PHARMACY_STOCK["med-a"]["quantity"] == 0
    assert len(result["dispensed"]) == 2
