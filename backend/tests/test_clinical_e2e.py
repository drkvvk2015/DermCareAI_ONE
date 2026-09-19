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
