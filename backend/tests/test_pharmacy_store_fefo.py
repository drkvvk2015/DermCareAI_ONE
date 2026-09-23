from datetime import date

from commerce_store import atomic_fefo_dispense, list_batches, upsert_batch


def test_fefo_persistence_allocates_earliest_expiry() -> None:
    upsert_batch({"batch_id": "B2", "medicine_id": "M1", "expiry": "2027-06-01", "quantity": 5})
    upsert_batch({"batch_id": "B1", "medicine_id": "M1", "expiry": "2027-03-01", "quantity": 3})
    upsert_batch({"batch_id": "EXPIRED", "medicine_id": "M1", "expiry": "2025-01-01", "quantity": 99})
    upsert_batch({"batch_id": "BLOCKED", "medicine_id": "M1", "expiry": "2027-01-01", "quantity": 99, "blocked": True})

    allocation = atomic_fefo_dispense({"M1": 6}, on=date(2026, 9, 23).isoformat())

    assert allocation == {"M1": [("B1", 3.0), ("B2", 3.0)]}
    batches = {item["batch_id"]: item for item in list_batches("M1")}
    assert batches["B1"]["quantity"] == 0.0
    assert batches["B2"]["quantity"] == 2.0
    assert batches["EXPIRED"]["quantity"] == 99.0
    assert batches["BLOCKED"]["quantity"] == 99.0
