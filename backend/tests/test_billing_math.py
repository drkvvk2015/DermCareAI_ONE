from decimal import Decimal

import pytest

from billing_math import BillLine, invoice_total


def test_invoice_rounding_is_deterministic() -> None:
    lines = [
        BillLine("consultation", Decimal("1"), Decimal("1000"), Decimal("18")),
        BillLine("cream", Decimal("2"), Decimal("125.50"), Decimal("5")),
    ]
    assert invoice_total(lines, Decimal("10")) == (
        Decimal("1251.00"), Decimal("188.88"), Decimal("1429.88")
    )


def test_invalid_discount_fails_closed() -> None:
    with pytest.raises(ValueError):
        invoice_total([BillLine("x", Decimal("1"), Decimal("10"))], Decimal("11"))


def test_empty_invoice_is_rejected() -> None:
    with pytest.raises(ValueError):
        invoice_total([])
