from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from auth import require_roles
from audit import AuditEvent, record_event
from clinical_store import (
    create_consent,
    create_encounter,
    create_media,
    get_encounter,
    list_lesion_timeline,
    upsert_lesion,
    update_encounter,
)

router = APIRouter(prefix="/api/v1/clinical", tags=["clinical"])


def _tenant(user: dict[str, Any]) -> tuple[str, str]:
    claims = user.get("claims", {})
    organization_id = claims.get("organization_id") or claims.get("organizationId")
    clinic_id = claims.get("clinic_id") or claims.get("clinicId")
    if not organization_id or not clinic_id:
        raise HTTPException(
            status_code=403,
            detail="Clinical tenant context is missing. Activate the user with organization_id and clinic_id claims.",
        )
    return str(organization_id), str(clinic_id)


class EncounterCreate(BaseModel):
    patient_id: str = Field(min_length=1, max_length=120)
    appointment_id: str | None = None
    complaints: Dict[str, Any] = {}
    examination: Dict[str, Any] = {}
    assessment: Dict[str, Any] = {}
    plan: Dict[str, Any] = {}


class EncounterPatch(BaseModel):
    expected_version: int = Field(ge=1)
    status: str | None = None
    complaints: Dict[str, Any] | None = None
    examination: Dict[str, Any] | None = None
    assessment: Dict[str, Any] | None = None
    plan: Dict[str, Any] | None = None
    closed_at: str | None = None


class LesionUpsert(BaseModel):
    patient_id: str
    encounter_id: str
    lesion_code: str = Field(min_length=1, max_length=80)
    body_site: str = Field(min_length=1, max_length=120)
    laterality: str | None = None
    morphology: Dict[str, Any] = {}
    size_mm: float | None = Field(default=None, ge=0)
    duration_days: int | None = Field(default=None, ge=0)
    evolution: str | None = None
    symptoms: Dict[str, Any] = {}
    clinical_impression: str | None = None
    differential: List[str] = []
    confirmed_diagnosis: str | None = None


class ConsentCreate(BaseModel):
    patient_id: str
    purpose: str = Field(min_length=1, max_length=120)
    document_version: str = Field(min_length=1, max_length=40)
    status: str = Field(pattern="^(granted|withdrawn)$")
    granted_at: str | None = None
    withdrawn_at: str | None = None
    expires_at: str | None = None


class ClinicalMediaCreate(BaseModel):
    patient_id: str
    encounter_id: str | None = None
    lesion_id: str | None = None
    consent_id: str | None = None
    consent_purpose: str = Field(default="clinical-image", min_length=1, max_length=120)
    object_url: str
    kind: str = Field(pattern="^(original|processed|dermoscopy|histopathology|other)$")
    sha256: str = Field(min_length=64, max_length=64)
    mime_type: str
    byte_size: int = Field(ge=1)
    captured_at: str
    retention_until: str | None = None


@router.post("/encounters")
def post_encounter(req: EncounterCreate, user: dict[str, Any] = Depends(require_roles("doctor", "admin"))):
    organization_id, clinic_id = _tenant(user)
    result = create_encounter(
        organization_id=organization_id,
        clinic_id=clinic_id,
        patient_id=req.patient_id,
        doctor_id=user["uid"],
        appointment_id=req.appointment_id,
        complaints=req.complaints,
        examination=req.examination,
        assessment=req.assessment,
        plan=req.plan,
    )
    record_event(AuditEvent(action='encounter_created', resource_type='encounter', resource_id=result['id'], metadata={'patient_id': req.patient_id, 'clinic_id': clinic_id}), user)
    return result


@router.get("/encounters/{encounter_id}")
def read_encounter(encounter_id: str, user: dict[str, Any] = Depends(require_roles("doctor", "admin", "auditor"))):
    _, clinic_id = _tenant(user)
    encounter = get_encounter(encounter_id, clinic_id)
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")
    return encounter


@router.patch("/encounters/{encounter_id}")
def patch_encounter(encounter_id: str, req: EncounterPatch, user: dict[str, Any] = Depends(require_roles("doctor", "admin"))):
    _, clinic_id = _tenant(user)
    patch = {key: value for key, value in req.model_dump().items() if key != "expected_version" and value is not None}
    try:
        return update_encounter(encounter_id, clinic_id, req.expected_version, patch)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/lesions")
def post_lesion(req: LesionUpsert, user: dict[str, Any] = Depends(require_roles("doctor", "admin"))):
    organization_id, clinic_id = _tenant(user)
    encounter = get_encounter(req.encounter_id, clinic_id)
    if not encounter or encounter["patient_id"] != req.patient_id:
        raise HTTPException(status_code=404, detail="Encounter not found for patient")
    result = upsert_lesion(organization_id=organization_id, clinic_id=clinic_id, **req.model_dump())
    record_event(AuditEvent(action='lesion_upserted', resource_type='lesion', resource_id=result['id'], metadata={'patient_id': req.patient_id, 'lesion_code': req.lesion_code}), user)
    return result


@router.get("/patients/{patient_id}/lesions/{lesion_code}/timeline")
def lesion_timeline(patient_id: str, lesion_code: str, user: dict[str, Any] = Depends(require_roles("doctor", "admin", "auditor"))):
    _, clinic_id = _tenant(user)
    return list_lesion_timeline(clinic_id=clinic_id, patient_id=patient_id, lesion_code=lesion_code)


@router.post("/consents")
def post_consent(req: ConsentCreate, user: dict[str, Any] = Depends(require_roles("doctor", "admin", "receptionist"))):
    organization_id, clinic_id = _tenant(user)
    result = create_consent(organization_id=organization_id, clinic_id=clinic_id, recorded_by=user['uid'], **req.model_dump())
    record_event(AuditEvent(action='consent_recorded', resource_type='consent', resource_id=result['id'], metadata={'patient_id': req.patient_id, 'purpose': req.purpose, 'status': req.status}), user)
    return result


@router.post("/media")
def post_media(req: ClinicalMediaCreate, user: dict[str, Any] = Depends(require_roles("doctor", "admin"))):
    organization_id, clinic_id = _tenant(user)
    try:
        result = create_media(
            organization_id=organization_id,
            clinic_id=clinic_id,
            captured_by=user["uid"],
            **req.model_dump(),
        )
        record_event(AuditEvent(action='clinical_media_recorded', resource_type='clinical_media', resource_id=result['id'], metadata={'patient_id': req.patient_id, 'kind': req.kind}), user)
        return result
    except PermissionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/consents/{patient_id}/active")
def active_consent(
    patient_id: str,
    purpose: str = "clinical-image",
    user: dict[str, Any] = Depends(require_roles("doctor", "admin", "receptionist")),
):
    _, clinic_id = _tenant(user)
    from clinical_store import has_active_consent
    return {
        "patient_id": patient_id,
        "purpose": purpose,
        "active": has_active_consent(clinic_id=clinic_id, patient_id=patient_id, purpose=purpose),
    }
