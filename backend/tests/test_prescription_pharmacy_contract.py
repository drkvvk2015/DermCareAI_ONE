from __future__ import annotations

import pytest

import commerce_store
import prescription_store
from prescription_pharmacy import dispense_prescription


def test_active_prescription_can_be_dispensed_only_for_same_patient_and_tenant(monkeypatch, tmp_path):
    monkeypatch.setenv("CLINICAL_DB_PATH", str(tmp_path / "clinical.db"))
    monkeypatch.setenv("COMMERCE_DB_PATH", str(tmp_path / "commerce.db"))

    prescription_store.ENGINE = prescription_store.create_store_engine("CLINICAL_DATABASE_URL", "CLINICAL_DB_PATH", str(tmp_path / "clinical.db"))
    commerce_store.ENGINE = commerce_store.create_store_engine("COMMERCE_DATABASE_URL", "COMMERCE_DB_PATH", str(tmp_path / "commerce.db"))

    rx = prescription_store.create_prescription(
        organization_id="org-1",
        clinic_id="clinic-1",
        patient_id="patient-1",
        encounter_id="enc-1",
        instructions="Use as directed",
        items=[{"medicine_id": "med-1", "quantity": 2}],
        prescribed_by="doctor-1",
    )
    commerce_store.upsert_batch({"batch_id": "b-1", "medicine_id": "med-1", "expiry": "2099-01-01", "quantity": 5, "blocked": False})

    result = dispense_prescription(
        prescription_id=rx["id"],
        organization_id="org-1",
        clinic_id="clinic-1",
        patient_id="patient-1",
        on="2026-09-23",
    )
    assert result["prescription_id"] == rx["id"]
    assert result["allocations"]["med-1"] == [("b-1", 2.0)]

    with pytest.raises(PermissionError):
        dispense_prescription(
            prescription_id=rx["id"],
            organization_id="org-1",
            clinic_id="clinic-1",
            patient_id="patient-2",
            on="2026-09-23",
        )

    with pytest.raises(KeyError):
        dispense_prescription(
            prescription_id=rx["id"],
            organization_id="org-2",
            clinic_id="clinic-2",
            patient_id="patient-1",
            on="2026-09-23",
        )
