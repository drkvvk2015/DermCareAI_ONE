from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture()
def prescription_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    db = tmp_path / "clinical-prescriptions.db"
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("CLINICAL_DB_PATH", str(db))
    import prescription_store

    prescription_store.ENGINE.dispose()
    prescription_store.ENGINE = prescription_store.create_store_engine(
        "CLINICAL_DATABASE_URL",
        "CLINICAL_DB_PATH",
        str(db),
    )
    yield prescription_store
    prescription_store.ENGINE.dispose()


def test_prescription_is_tenant_scoped_and_cancellable(prescription_env):
    store = prescription_env
    created = store.create_prescription(
        organization_id="org-a",
        clinic_id="clinic-a",
        patient_id="patient-a",
        encounter_id="enc-1",
        instructions="Apply after cleansing",
        items=[{
            "medicine_id": "m1",
            "name": "Example cream",
            "strength": "1%",
            "dose": "thin layer",
            "route": "topical",
            "frequency": "BID",
            "duration": "14 days",
            "quantity": 1,
            "instructions": "Avoid eyes",
        }],
        prescribed_by="doctor-a",
    )
    assert created["status"] == "active"
    assert store.get_prescription(created["id"], organization_id="org-a", clinic_id="clinic-a") is not None
    assert store.get_prescription(created["id"], organization_id="org-b", clinic_id="clinic-b") is None
    cancelled = store.cancel_prescription(created["id"], organization_id="org-a", clinic_id="clinic-a")
    assert cancelled["status"] == "cancelled"
    with pytest.raises(ValueError, match="Only active"):
        store.cancel_prescription(created["id"], organization_id="org-a", clinic_id="clinic-a")


def test_prescription_store_schema_initialization_is_repeatable(prescription_env):
    store = prescription_env
    store.init_store()
    store.init_store()
    created = store.create_prescription(
        organization_id="org-repeat",
        clinic_id="clinic-repeat",
        patient_id="patient-repeat",
        encounter_id="enc-repeat",
        instructions="repeatable schema migration",
        items=[{"medicine_id": "m-repeat", "quantity": 1}],
        prescribed_by="doctor-repeat",
    )
    assert created["dispense_status"] == "not_dispensed"
