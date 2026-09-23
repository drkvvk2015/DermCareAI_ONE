from decimal import Decimal

from commerce import InvoiceItem, InvoiceRequest, compute_invoice


def test_commerce_invoice_uses_decimal_totals() -> None:
    invoice = compute_invoice(
        InvoiceRequest(
            patient_id="patient-1",
            items=[
                InvoiceItem(
                    description="consultation",
                    quantity=Decimal("1"),
                    unit_price=Decimal("1000"),
                    tax_percent=Decimal("18"),
                ),
                InvoiceItem(
                    description="cream",
                    quantity=Decimal("2"),
                    unit_price=Decimal("125.50"),
                    tax_percent=Decimal("5"),
                ),
            ],
            discount=Decimal("10"),
        )
    )

    assert invoice["subtotal"] == Decimal("1251.00")
    assert invoice["tax"] == Decimal("192.55")
    assert invoice["discount"] == Decimal("10.00")
    assert invoice["total"] == Decimal("1433.55")
