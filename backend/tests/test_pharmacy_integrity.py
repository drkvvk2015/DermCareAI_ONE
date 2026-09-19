from fastapi import HTTPException

from commerce import PHARMACY_STOCK, DispenseRequest, dispense


def setup_function() -> None:
    PHARMACY_STOCK.clear()


def test_missing_medicine_does_not_partially_deduct_stock() -> None:
    PHARMACY_STOCK["m1"] = {"medicine_id": "m1", "name": "Medicine 1", "quantity": 5}
    request = DispenseRequest(
        patient_id="p1",
        items=[
            {"medicine_id": "m1", "quantity": 2},
            {"medicine_id": "unknown", "quantity": 1},
        ],
    )
    try:
        dispense(request)
    except HTTPException as exc:
        assert exc.status_code == 404
    else:
        raise AssertionError("Expected missing medicine failure")
    assert PHARMACY_STOCK["m1"]["quantity"] == 5


def test_insufficient_aggregated_stock_does_not_mutate_inventory() -> None:
    PHARMACY_STOCK["m1"] = {"medicine_id": "m1", "name": "Medicine 1", "quantity": 2}
    request = DispenseRequest(
        patient_id="p1",
        items=[
            {"medicine_id": "m1", "quantity": 1.5},
            {"medicine_id": "m1", "quantity": 1.0},
        ],
    )
    try:
        dispense(request)
    except HTTPException as exc:
        assert exc.status_code == 409
    else:
        raise AssertionError("Expected insufficient stock failure")
    assert PHARMACY_STOCK["m1"]["quantity"] == 2
