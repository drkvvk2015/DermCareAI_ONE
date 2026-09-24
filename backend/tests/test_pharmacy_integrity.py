from fastapi import HTTPException

from commerce import DispenseRequest, dispense
from commerce_store import list_stock, reset_store, upsert_stock


def setup_function() -> None:
    reset_store()


def test_missing_medicine_does_not_partially_deduct_stock() -> None:
    upsert_stock({"medicine_id": "m1", "name": "Medicine 1", "quantity": 5})
    request = DispenseRequest(
        patient_id="p1",
        items=[
            {"medicine_id": "m1", "quantity": 2},
            {"medicine_id": "unknown", "quantity": 1},
        ],
    )
    try:
        dispense(request, {"uid": "u1", "roles": {"pharmacist"}, "claims": {"organization_id": "default-org", "clinic_id": "default-clinic"}})
    except HTTPException as exc:
        assert exc.status_code == 404
    else:
        raise AssertionError("Expected missing medicine failure")
    assert list_stock()[0]["quantity"] == 5


def test_insufficient_aggregated_stock_does_not_mutate_inventory() -> None:
    upsert_stock({"medicine_id": "m1", "name": "Medicine 1", "quantity": 2})
    request = DispenseRequest(
        patient_id="p1",
        items=[
            {"medicine_id": "m1", "quantity": 1.5},
            {"medicine_id": "m1", "quantity": 1.0},
        ],
    )
    try:
        dispense(request, {"uid": "u1", "roles": {"pharmacist"}, "claims": {"organization_id": "default-org", "clinic_id": "default-clinic"}})
    except HTTPException as exc:
        assert exc.status_code == 409
    else:
        raise AssertionError("Expected insufficient stock failure")
    assert list_stock()[0]["quantity"] == 2
