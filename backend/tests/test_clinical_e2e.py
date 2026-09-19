import os
from uuid import uuid4

os.environ.setdefault("CLINICAL_DB_PATH", f"/tmp/dermcareai-api-{uuid4().hex}.db")
os.environ.setdefault("AUDIT_DB_PATH", f"/tmp/dermcareai-audit-{uuid4().hex}.db")

from fastapi import FastAPI
from fastapi.testclient import TestClient

from auth import get_current_user
from clinical import router as clinical_router
from audit import router as audit_router

app = FastAPI()
app.include_router(clinical_router)
app.include_router(audit_router)

_CURRENT = {
    "uid": "doctor-1",
    "roles": {"doctor"},
    "claims": {"organization_id": "org-1", "clinic_id": "clinic-1"},
}


def override_user():
    return _CURRENT


app.dependency_overrides[get_current_user] = override_user


def test_clinical_workflow_and_tenant_isolation() -> None:
    client = TestClient(app)

    encounter = client.post(
        "/api/v1/clinical/encounters",
        json={
            "patient_id": "patient-1",
            "complaints": {"chief_complaint": "changing mole"},
            "examination": {"site": "forearm", "morphology": "pigmented"},
            "assessment": {"differential": ["nevus", "melanoma"]},
            "plan": {"follow_up_days": 14},
        },
    )
    assert encounter.status_code == 200
    encounter_id = encounter.json()["id"]

    lesion = client.post(
        "/api/v1/clinical/lesions",
        json={
            "patient_id": "patient-1",
            "encounter_id": encounter_id,
            "lesion_code": "L-001",
            "body_site": "left forearm",
            "size_mm": 6.0,
            "morphology": {"primary": "papule"},
        },
    )
    assert lesion.status_code == 200

    consent = client.post(
        "/api/v1/clinical/consents",
        json={
            "patient_id": "patient-1",
            "purpose": "clinical-image",
            "document_version": "clinic-approved-v1",
            "status": "granted",
            "granted_at": "2026-09-19T00:00:00+00:00",
        },
    )
    assert consent.status_code == 200
    consent_id = consent.json()["id"]

    active = client.get("/api/v1/clinical/consents/patient-1/active?purpose=clinical-image")
    assert active.status_code == 200
    assert active.json()["active"] is True

    media = client.post(
        "/api/v1/clinical/media",
        json={
            "patient_id": "patient-1",
            "encounter_id": encounter_id,
            "consent_id": consent_id,
            "consent_purpose": "clinical-image",
            "object_url": "https://storage.example/clinical.jpg",
            "kind": "original",
            "sha256": "a" * 64,
            "mime_type": "image/jpeg",
            "byte_size": 1234,
            "captured_at": "2026-09-19T00:01:00+00:00",
        },
    )
    assert media.status_code == 200

    _CURRENT["claims"] = {"organization_id": "org-1", "clinic_id": "clinic-2"}
    isolated = client.get(f"/api/v1/clinical/encounters/{encounter_id}")
    assert isolated.status_code == 404

    _CURRENT["claims"] = {"organization_id": "org-1", "clinic_id": "clinic-1"}
    timeline = client.get("/api/v1/clinical/patients/patient-1/lesions/L-001/timeline")
    assert timeline.status_code == 200
    assert timeline.json()[0]["lesion_code"] == "L-001"



def test_signoff_is_blocked_by_pending_ai_review() -> None:
    client = TestClient(app)
    encounter = client.post(
        "/api/v1/clinical/encounters",
        json={"patient_id": "patient-pending", "complaints": {}, "examination": {}, "assessment": {}, "plan": {}},
    )
    assert encounter.status_code == 200
    encounter_id = encounter.json()["id"]

    review = client.post(
        f"/api/v1/clinical/encounters/{encounter_id}/ai-reviews",
        json={
            "request_id": "REQ-PENDING",
            "model_name": "research-demo",
            "predicted_label": "Uncertain / Needs Clinical Review",
            "confidence": 0.42,
            "accepted": False,
        },
    )
    assert review.status_code == 200

    signoff = client.post(
        f"/api/v1/clinical/encounters/{encounter_id}/sign",
        json={"attestation": "I reviewed the clinical history examination assessment and plan and accept responsibility for this clinical record."},
    )
    assert signoff.status_code == 409


def test_signoff_followup_and_ai_review_workflow() -> None:
    client = TestClient(app)

    encounter = client.post(
        "/api/v1/clinical/encounters",
        json={
            "patient_id": "patient-2",
            "complaints": {"chief_complaint": "new rash"},
            "examination": {"dermatology": {"primary_morphology": "plaque"}},
            "assessment": {"provisional_diagnosis": "dermatitis"},
            "plan": {"management_plan": "topical treatment"},
        },
    )
    assert encounter.status_code == 200
    encounter_id = encounter.json()["id"]

    followup = client.post(
        f"/api/v1/clinical/encounters/{encounter_id}/followups",
        json={
            "due_at": "2026-10-03T09:00:00+05:30",
            "instructions": "Review treatment response and lesion evolution.",
        },
    )
    assert followup.status_code == 200
    assert followup.json()["status"] == "planned"

    ai_review = client.post(
        f"/api/v1/clinical/encounters/{encounter_id}/ai-reviews",
        json={
            "request_id": "REQ-1",
            "model_name": "research-demo",
            "model_provenance": "test",
            "predicted_label": "Dermatitis",
            "confidence": 0.81,
            "accepted": False,
        },
    )
    assert ai_review.status_code == 200
    review_id = ai_review.json()["id"]

    decision = client.patch(
        f"/api/v1/clinical/encounters/{encounter_id}/ai-reviews/{review_id}",
        json={"clinician_decision": "overridden", "clinician_override_label": "Tinea corporis"},
    )
    assert decision.status_code == 200
    assert decision.json()["clinician_decision"] == "overridden"

    other = client.post(
        "/api/v1/clinical/encounters",
        json={
            "patient_id": "patient-3",
            "complaints": {"chief_complaint": "another case"},
            "examination": {},
            "assessment": {},
            "plan": {},
        },
    )
    assert other.status_code == 200
    other_id = other.json()["id"]
    cross_encounter = client.patch(
        f"/api/v1/clinical/encounters/{other_id}/ai-reviews/{review_id}",
        json={"clinician_decision": "rejected"},
    )
    assert cross_encounter.status_code == 409

    signoff = client.post(
        f"/api/v1/clinical/encounters/{encounter_id}/sign",
        json={
            "attestation": "I reviewed the clinical history examination assessment and plan and accept responsibility for this clinical record."
        },
    )
    assert signoff.status_code == 200

    signed = client.get(f"/api/v1/clinical/encounters/{encounter_id}")
    assert signed.status_code == 200
    assert signed.json()["status"] == "signed"

    summary = client.get("/api/v1/clinical/patients/patient-2/summary")
    assert summary.status_code == 200
    assert summary.json()["patient_id"] == "patient-2"
    assert any(item["encounter_id"] == encounter_id for item in summary.json()["followups"])
    assert any(item["encounter_id"] == encounter_id for item in summary.json()["signoffs"])
