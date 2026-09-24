import os
from uuid import uuid4

os.environ.setdefault("COMMERCE_DB_PATH", f"/tmp/dermcareai-commerce-hardening-{uuid4().hex}.db")

from commerce_store import get_invoice, init_store, list_stock, save_invoice, upsert_stock, atomic_dispense


def setup_function() -> None:
    init_store()


def test_invoice_reads_are_tenant_scoped() -> None:
    invoice = {
        "id": "INV-TENANT-1",
        "patient_id": "patient-a",
        "status": "unpaid",
        "created_at": "2026-09-24T00:00:00+00:00",
        "total": "100.00",
    }
    save_invoice(invoice, organization_id="org-a", clinic_id="clinic-a")
    assert get_invoice("INV-TENANT-1", organization_id="org-a", clinic_id="clinic-a")["id"] == "INV-TENANT-1"
    assert get_invoice("INV-TENANT-1", organization_id="org-b", clinic_id="clinic-b") is None


def test_stock_is_tenant_scoped_and_atomic() -> None:
    upsert_stock({"medicine_id": "MED-A", "quantity": 10}, organization_id="org-a", clinic_id="clinic-a")
    upsert_stock({"medicine_id": "MED-A", "quantity": 3}, organization_id="org-b", clinic_id="clinic-b")

    assert list_stock(organization_id="org-a", clinic_id="clinic-a")[0]["quantity"] == 10
    updated = atomic_dispense({"MED-A": 4}, organization_id="org-a", clinic_id="clinic-a")
    assert updated["MED-A"]["quantity"] == 6
    assert list_stock(organization_id="org-b", clinic_id="clinic-b")[0]["quantity"] == 3


def test_atomic_stock_rejects_overdraw() -> None:
    upsert_stock({"medicine_id": "MED-B", "quantity": 2}, organization_id="org-a", clinic_id="clinic-a")
    try:
        atomic_dispense({"MED-B": 3}, organization_id="org-a", clinic_id="clinic-a")
    except ValueError:
        pass
    else:
        raise AssertionError("Overdraw must fail")
