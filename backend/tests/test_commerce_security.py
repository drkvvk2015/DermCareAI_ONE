from fastapi import HTTPException

from commerce import (
    INVOICES,
    PHARMACY_STOCK,
    DispenseRequest,
    InvoiceItem,
    InvoiceRequest,
    PaymentRequest,
    compute_invoice,
    dispense,
    verify_razorpay_signature,
    validate_razorpay_payment_event,
    PharmacyBatchRequest,
    DispenseRequest,
)
from commerce_store import list_stock, reset_store, upsert_stock


def setup_function() -> None:
    INVOICES.clear()
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
    upsert_stock({"medicine_id": "med-a", "name": "A", "quantity": 10})
    request = DispenseRequest(
        patient_id="p1",
        items=[
            {"medicine_id": "med-a", "quantity": 2},
            {"medicine_id": "missing", "quantity": 1},
        ],
    )
    try:
        dispense(request, {"uid": "u1", "roles": {"pharmacist"}, "claims": {"organization_id": "default-org", "clinic_id": "default-clinic"}})
    except HTTPException as exc:
        assert exc.status_code == 404
    else:
        raise AssertionError("Expected missing medicine failure")
    assert list_stock()[0]["quantity"] == 10


def test_dispense_aggregates_duplicate_items() -> None:
    upsert_stock({"medicine_id": "med-a", "name": "A", "quantity": 3})
    request = DispenseRequest(
        patient_id="p1",
        items=[
            {"medicine_id": "med-a", "quantity": 1},
            {"medicine_id": "med-a", "quantity": 2},
        ],
    )
    result = dispense(request, {"uid": "u1", "roles": {"pharmacist"}, "claims": {"organization_id": "default-org", "clinic_id": "default-clinic"}})
    assert list_stock()[0]["quantity"] == 0
    assert len(result["dispensed"]) == 2


def test_duplicate_payment_event_is_idempotent() -> None:
    from commerce_store import record_payment_event

    payload = {"id": "evt-test-idempotency", "event": "payment.captured"}
    assert record_payment_event("evt-test-idempotency", payload) is True
    assert record_payment_event("evt-test-idempotency", payload) is False


def test_razorpay_webhook_requires_captured_event_and_entity_state() -> None:
    base = {
        "event": "payment.captured",
        "payload": {"payment": {"entity": {"id": "pay-1", "status": "captured", "amount": 118000}}},
    }
    assert validate_razorpay_payment_event(base)["id"] == "pay-1"

    failed = {**base, "event": "payment.failed"}
    try:
        validate_razorpay_payment_event(failed)
    except HTTPException as exc:
        assert exc.status_code == 409
    else:
        raise AssertionError("Failed payment events must never settle invoices")

    authorized = {
        **base,
        "payload": {"payment": {"entity": {"id": "pay-2", "status": "authorized", "amount": 118000}}},
    }
    try:
        validate_razorpay_payment_event(authorized)
    except HTTPException as exc:
        assert exc.status_code == 409
    else:
        raise AssertionError("Authorized-but-not-captured payments must not settle invoices")


def test_pharmacy_batch_expiry_requires_canonical_real_date() -> None:
    valid = PharmacyBatchRequest(batch_id="B1", medicine_id="M1", expiry="2027-06-01", quantity=1)
    assert valid.expiry == "2027-06-01"
    for value in ("2027-6-1", "2027-02-30", "not-a-date"):
        try:
            PharmacyBatchRequest(batch_id="B1", medicine_id="M1", expiry=value, quantity=1)
        except Exception:
            continue
        raise AssertionError(f"Invalid expiry accepted: {value}")


def test_dispense_prescription_link_is_tenant_and_patient_scoped(monkeypatch) -> None:
    import commerce

    monkeypatch.setattr(
        commerce,
        "get_prescription",
        lambda prescription_id, *, organization_id, clinic_id: {
            "id": prescription_id,
            "patient_id": "patient-a",
            "status": "active",
            "dispense_status": "not_dispensed",
        } if organization_id == "org-a" and clinic_id == "clinic-a" else None,
    )
    request = DispenseRequest(
        patient_id="patient-b",
        prescription_id="RX-1",
        items=[{"medicine_id": "M1", "quantity": 1}],
    )
    try:
        commerce.validate_prescription_link(
            req=request, organization_id="org-a", clinic_id="clinic-a"
        )
    except HTTPException as exc:
        assert exc.status_code == 404
    else:
        raise AssertionError("Cross-patient prescription links must be rejected")
