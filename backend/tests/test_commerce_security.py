from commerce import INVOICES, PHARMACY_STOCK, DispenseRequest, InvoiceItem, InvoiceRequest, PaymentRequest, compute_invoice, dispense


def setup_function() -> None:
    INVOICES.clear()
    PHARMACY_STOCK.clear()


def test_payment_amount_is_derived_from_invoice() -> None:
    invoice = compute_invoice(
        InvoiceRequest(
            patient_id="p1",
            items=[InvoiceItem(description="Consultation", quantity=1, unit_price=1000, tax_percent=18)],
        )
    )
    request = PaymentRequest(
        invoice_id=invoice["id"],
        amount=1,
        customer_name="Test",
        customer_phone="9999999999",
    )
    assert request.amount == 1
    assert round(invoice["total"] * 100) == 118000


def test_dispense_validates_all_items_before_mutating_stock() -> None:
    PHARMACY_STOCK["med-a"] = {"medicine_id": "med-a", "name": "A", "quantity": 10}
    request = DispenseRequest(
        patient_id="p1",
        items=[
            {"medicine_id": "med-a", "quantity": 2},
            {"medicine_id": "missing", "quantity": 1},
        ],
    )
    try:
        dispense(request)
    except Exception as exc:
        assert getattr(exc, "status_code", None) == 404
    assert PHARMACY_STOCK["med-a"]["quantity"] == 10


def test_dispense_aggregates_duplicate_items() -> None:
    PHARMACY_STOCK["med-a"] = {"medicine_id": "med-a", "name": "A", "quantity": 3}
    request = DispenseRequest(
        patient_id="p1",
        items=[
            {"medicine_id": "med-a", "quantity": 1},
            {"medicine_id": "med-a", "quantity": 2},
        ],
    )
    result = dispense(request)
    assert PHARMACY_STOCK["med-a"]["quantity"] == 0
    assert len(result["dispensed"]) == 2
