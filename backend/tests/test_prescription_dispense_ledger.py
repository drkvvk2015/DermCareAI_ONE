from prescription_dispense_ledger import begin_or_get, record_allocated, finalize


def test_dispense_ledger_is_idempotent_for_same_tenant():
    first = begin_or_get(
        prescription_id="RX-LEDGER-1",
        organization_id="org-a",
        clinic_id="clinic-a",
        patient_id="patient-1",
    )
    second = begin_or_get(
        prescription_id="RX-LEDGER-1",
        organization_id="org-a",
        clinic_id="clinic-a",
        patient_id="patient-1",
    )
    assert first["status"] == "pending"
    assert second["status"] == "pending"

    allocated = record_allocated(
        prescription_id="RX-LEDGER-1",
        organization_id="org-a",
        clinic_id="clinic-a",
        allocations={"med-1": [["batch-1", 2.0]]},
    )
    assert allocated["status"] == "allocated"
    assert allocated["allocations"]["med-1"][0][0] == "batch-1"

    completed = finalize(
        prescription_id="RX-LEDGER-1",
        organization_id="org-a",
        clinic_id="clinic-a",
    )
    assert completed["status"] == "completed"
