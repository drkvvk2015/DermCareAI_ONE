from datetime import date, timedelta

import pytest

from dermatology_pharmacy import Batch, InventoryError, allocate_fefo


def test_fefo_allocates_earliest_expiry_first() -> None:
    today = date(2026, 9, 23)
    batches = [
        Batch("B2", "M1", today + timedelta(days=60), 5),
        Batch("B1", "M1", today + timedelta(days=10), 3),
    ]
    assert allocate_fefo(batches, 6, on=today) == [("B1", 3), ("B2", 3)]


def test_expired_and_blocked_batches_are_never_allocated() -> None:
    today = date(2026, 9, 23)
    batches = [
        Batch("EXPIRED", "M1", today - timedelta(days=1), 20),
        Batch("BLOCKED", "M1", today + timedelta(days=1), 20, blocked=True),
    ]
    with pytest.raises(InventoryError):
        allocate_fefo(batches, 1, on=today)


def test_zero_or_negative_request_is_rejected() -> None:
    with pytest.raises(InventoryError):
        allocate_fefo([], 0)
