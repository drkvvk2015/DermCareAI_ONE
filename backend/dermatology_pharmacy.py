"""Deterministic FEFO pharmacy inventory primitives.

Persistence and authorization remain in the existing commerce layer. This module
provides validation and allocation logic that can be unit-tested independently.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Batch:
    batch_id: str
    medicine_id: str
    expiry: date
    quantity: float
    blocked: bool = False


class InventoryError(ValueError):
    pass


def validate_batch(batch: Batch) -> None:
    if not batch.batch_id or not batch.medicine_id:
        raise InventoryError("batch_id and medicine_id are required")
    if batch.quantity < 0:
        raise InventoryError("batch quantity cannot be negative")


def allocate_fefo(batches: list[Batch], requested: float, *, on: date | None = None) -> list[tuple[str, float]]:
    if requested <= 0:
        raise InventoryError("requested quantity must be greater than zero")
    today = on or date.today()
    candidates = sorted(
        (batch for batch in batches if not batch.blocked and batch.expiry >= today and batch.quantity > 0),
        key=lambda batch: (batch.expiry, batch.batch_id),
    )
    remaining = float(requested)
    allocations: list[tuple[str, float]] = []
    for batch in candidates:
        take = min(remaining, batch.quantity)
        if take:
            allocations.append((batch.batch_id, take))
            remaining -= take
        if remaining <= 0:
            break
    if remaining > 0:
        raise InventoryError("insufficient non-expired stock")
    return allocations
