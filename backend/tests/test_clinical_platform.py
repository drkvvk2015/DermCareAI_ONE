import os

os.environ.setdefault("CLINICAL_DB_PATH", "/tmp/dermcareai-test-clinical-wave2.db")

from clinical_store import create_consent, create_encounter, create_media, has_active_consent, init_store, list_lesion_timeline, upsert_lesion  # noqa: E402


def setup_function() -> None:
    init_store()


def _encounter() -> dict:
    return create_encounter(
        organization_id="org1",
        clinic_id="clinic1",
        patient_id="patient1",
        doctor_id="doctor1",
        appointment_id=None,
        complaints={"chief_complaint": "changing lesion"},
        examination={"morphology": "pigmented"},
        assessment={"working": "needs review"},
        plan={"follow_up_days": 14},
    )


def test_encounter_and_lesion_timeline_roundtrip() -> None:
    encounter = _encounter()
    assert encounter["id"].startswith("ENC-")
    upsert_lesion(
        organization_id="org1",
        clinic_id="clinic1",
        patient_id="patient1",
        encounter_id=encounter["id"],
        lesion_code="L-001",
        body_site="left forearm",
        morphology={"primary": "papule"},
        size_mm=5.5,
        differential=["melanocytic nevus"],
    )
    timeline = list_lesion_timeline(clinic_id="clinic1", patient_id="patient1", lesion_code="L-001")
    assert len(timeline) == 1
    assert timeline[0]["size_mm"] == 5.5


def test_media_requires_active_consent() -> None:
    encounter = _encounter()
    kwargs = dict(
        organization_id="org1",
        clinic_id="clinic1",
        patient_id="patient1",
        encounter_id=encounter["id"],
        lesion_id=None,
        consent_id=None,
        consent_purpose="clinical-image",
        object_url="https://example.invalid/image.jpg",
        kind="original",
        sha256="a" * 64,
        mime_type="image/jpeg",
        byte_size=100,
        captured_at="2026-09-19T00:00:00+00:00",
        captured_by="doctor1",
        retention_until=None,
    )
    try:
        create_media(**kwargs)
    except PermissionError:
        pass
    else:
        raise AssertionError("Media must require active consent")


def test_consent_withdrawal_invalidates_previous_grant() -> None:
    create_consent(
        organization_id="org1",
        clinic_id="clinic1",
        patient_id="patient1",
        purpose="clinical-image",
        document_version="v1",
        status="granted",
        granted_at="2026-09-19T00:00:00+00:00",
        recorded_by="doctor1",
    )
    assert has_active_consent(clinic_id="clinic1", patient_id="patient1", purpose="clinical-image")

    create_consent(
        organization_id="org1",
        clinic_id="clinic1",
        patient_id="patient1",
        purpose="clinical-image",
        document_version="v1",
        status="withdrawn",
        withdrawn_at="2026-09-19T01:00:00+00:00",
        recorded_by="doctor1",
    )
    assert not has_active_consent(clinic_id="clinic1", patient_id="patient1", purpose="clinical-image")
