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
    assert list_procedures(
        organization_id="org1",
        clinic_id="clinic1",
        patient_id="patient1",
    )[0]["id"] == row["id"]


def test_procedure_list_isolated_between_organizations_in_same_clinic():
    first = create_procedure(
        organization_id="org1",
        clinic_id="shared-clinic",
        patient_id="shared-patient",
        encounter_id="ENC-ORG-1",
        procedure_type="biopsy",
        body_site="forearm",
        indication="synthetic test indication",
        consent_id="CONS-ORG-1",
        performed_by="doctor1",
        performed_at="2026-09-22T12:00:00+00:00",
    )
    create_procedure(
        organization_id="org2",
        clinic_id="shared-clinic",
        patient_id="shared-patient",
        encounter_id="ENC-ORG-2",
        procedure_type="biopsy",
        body_site="forearm",
        indication="synthetic test indication",
        consent_id="CONS-ORG-2",
        performed_by="doctor2",
        performed_at="2026-09-23T12:00:00+00:00",
    )

    visible = list_procedures(
        organization_id="org1",
        clinic_id="shared-clinic",
        patient_id="shared-patient",
    )
    assert first["id"] in {procedure["id"] for procedure in visible}
    assert {procedure["organization_id"] for procedure in visible} == {"org1"}
