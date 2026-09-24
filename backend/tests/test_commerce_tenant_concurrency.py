import os
from uuid import uuid4

os.environ.setdefault("COMMERCE_DB_PATH", f"/tmp/dermcareai-commerce-hardening-{uuid4().hex}.db")

from commerce_store import atomic_dispense, init_store, list_stock, upsert_stock


def setup_function() -> None:
    init_store()


def test_stock_isolated_by_tenant() -> None:
    upsert_stock({"medicine_id": "MED-1", "quantity": 10}, organization_id="org-a", clinic_id="clinic-a")
    upsert_stock({"medicine_id": "MED-1", "quantity": 20}, organization_id="org-b", clinic_id="clinic-b")

    assert list_stock(organization_id="org-a", clinic_id="clinic-a")[0]["quantity"] == 10
    assert list_stock(organization_id="org-b", clinic_id="clinic-b")[0]["quantity"] == 20


def test_atomic_stock_decrement_cannot_overdraw() -> None:
    upsert_stock({"medicine_id": "MED-2", "quantity": 5}, organization_id="org-a", clinic_id="clinic-a")
    assert atomic_dispense({"MED-2": 3}, organization_id="org-a", clinic_id="clinic-a")["MED-2"]["quantity"] == 2
    try:
        atomic_dispense({"MED-2": 3}, organization_id="org-a", clinic_id="clinic-a")
    except ValueError as exc:
        assert exc.args[0] == "MED-2"
    else:
        raise AssertionError("stock overdraw must be rejected")
