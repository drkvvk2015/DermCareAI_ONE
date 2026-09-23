import os
from uuid import uuid4

os.environ.setdefault("CLINICAL_DB_PATH", f"/tmp/dermcareai-provenance-{uuid4().hex}.db")

from fastapi import FastAPI
from fastapi.testclient import TestClient

from auth import get_current_user
from clinical import router as clinical_router


app = FastAPI()
app.include_router(clinical_router)

CURRENT_USER = {
    "uid": "doctor-provenance",
    "roles": {"doctor"},
    "claims": {"organization_id": "org-provenance", "clinic_id": "clinic-provenance"},
}


def override_user():
    return CURRENT_USER


app.dependency_overrides[get_current_user] = override_user


def test_media_ai_provenance_is_tenant_and_encounter_scoped() -> None:
    client = TestClient(app)

    encounter = client.post(
        "/api/v1/clinical/encounters",
        json={
            "patient_id": "patient-provenance",
            "complaints": {"chief_complaint": "pigmented lesion", "duration": "2 months"},
            "examination": {"distribution": "left forearm", "morphology": "papule"},
            "assessment": {"diagnosis": "pigmented lesion"},
            "plan": {"treatment": "clinical review"},
        },
    )
    assert encounter.status_code == 200
    encounter_id = encounter.json()["id"]

    lesion = client.post(
        "/api/v1/clinical/lesions",
        json={
            "patient_id": "patient-provenance",
            "encounter_id": encounter_id,
            "lesion_code": "L-PROV-1",
            "body_site": "left forearm",
            "morphology": {"primary": "papule"},
            "size_mm": 5.0,
        },
    )
    assert lesion.status_code == 200
    lesion_id = lesion.json()["id"]

    consent = client.post(
        "/api/v1/clinical/consents",
        json={
            "patient_id": "patient-provenance",
            "purpose": "clinical-image",
            "document_version": "v1",
            "status": "granted",
        },
    )
    assert consent.status_code == 200

    media = client.post(
        "/api/v1/clinical/media",
        json={
            "patient_id": "patient-provenance",
            "encounter_id": encounter_id,
            "lesion_id": lesion_id,
            "consent_id": consent.json()["id"],
            "consent_purpose": "clinical-image",
            "object_url": "https://storage.example/provenance.jpg",
            "kind": "original",
            "sha256": "b" * 64,
            "mime_type": "image/jpeg",
            "byte_size": 2048,
            "captured_at": "2026-09-23T10:00:00+00:00",
        },
    )
    assert media.status_code == 200
    media_id = media.json()["id"]

    linked = client.post(
        f"/api/v1/clinical/encounters/{encounter_id}/ai-reviews",
        json={
            "media_id": media_id,
            "lesion_id": lesion_id,
            "request_id": "REQ-PROV-1",
            "model_name": "research-demo",
            "model_provenance": "test",
            "predicted_label": "Needs clinician review",
            "confidence": 0.51,
        },
    )
    assert linked.status_code == 200
    assert linked.json()["media_id"] == media_id
    assert linked.json()["lesion_id"] == lesion_id

    media_list = client.get("/api/v1/clinical/patients/patient-provenance/media", params={"encounter_id": encounter_id, "lesion_id": lesion_id})
    assert media_list.status_code == 200
    assert [item["id"] for item in media_list.json()] == [media_id]

    CURRENT_USER["claims"] = {"organization_id": "org-provenance", "clinic_id": "other-clinic"}
    isolated_media = client.get("/api/v1/clinical/patients/patient-provenance/media")
    assert isolated_media.status_code == 200
    assert isolated_media.json() == []

    CURRENT_USER["claims"] = {"organization_id": "other-org", "clinic_id": "clinic-provenance"}
    isolated_review = client.post(
        f"/api/v1/clinical/encounters/{encounter_id}/ai-reviews",
        json={
            "media_id": media_id,
            "request_id": "REQ-CROSS-TENANT",
            "model_name": "research-demo",
            "predicted_label": "Should not attach",
            "confidence": 0.5,
        },
    )
    assert isolated_review.status_code == 404
