import os
os.environ.setdefault("CLINICAL_DB_PATH", "/tmp/dermcareai-procedure-test.db")

from dermatology.procedure_store import create_procedure, init_store, list_procedures

def setup_function():
    init_store()

def test_procedure_roundtrip():
    row = create_procedure(
        organization_id="org1",
        clinic_id="clinic1",
        patient_id="patient1",
        encounter_id="ENC-1",
        procedure_type="biopsy",
        body_site="left forearm",
        indication="changing lesion",
        consent_id="CONS-1",
        performed_by="doctor1",
        performed_at="2026-09-22T12:00:00+00:00",
        outcome="specimen sent",
    )
    assert row["procedure_type"] == "biopsy"
    assert list_procedures(clinic_id="clinic1", patient_id="patient1")[0]["id"] == row["id"]
