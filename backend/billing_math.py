"""Integer-paise invoice arithmetic for deterministic billing totals."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP


TWOPLACES = Decimal("0.01")


def money(value: Decimal | int | float | str) -> Decimal:
    return Decimal(str(value)).quantize(TWOPLACES, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class BillLine:
    description: str
    quantity: Decimal
    unit_price: Decimal
    tax_percent: Decimal = Decimal("0")

    def subtotal(self) -> Decimal:
        if self.quantity <= 0 or self.unit_price < 0:
            raise ValueError("invalid quantity or unit price")
        return money(self.quantity * self.unit_price)

    def tax(self) -> Decimal:
        if not Decimal("0") <= self.tax_percent <= Decimal("100"):
            raise ValueError("tax_percent must be between 0 and 100")
        return money(self.subtotal() * self.tax_percent / Decimal("100"))


def invoice_total(lines: list[BillLine], discount: Decimal = Decimal("0")) -> tuple[Decimal, Decimal, Decimal]:
    if not lines:
        raise ValueError("invoice requires at least one line")
    subtotal = money(sum((line.subtotal() for line in lines), Decimal("0")))
    tax = money(sum((line.tax() for line in lines), Decimal("0")))
    discount = money(discount)
    if discount < 0 or discount > subtotal + tax:
        raise ValueError("invalid discount")
    total = money(subtotal + tax - discount)
    return subtotal, tax, total
