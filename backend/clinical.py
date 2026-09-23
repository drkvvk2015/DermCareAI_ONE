from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from auth import require_roles
from audit import AuditEvent, record_event
from dermatology.clinical_documentation import validate_encounter
from dermatology.clinical_workflow import TEMPLATES, get_history_template
from clinical_store import (
    create_consent,
    create_encounter,
    create_media,
    get_encounter,
    list_lesion_timeline,
    upsert_lesion,
    update_encounter,
    create_signoff,
    get_signoff,
    create_followup,
    list_followups,
    record_ai_review,
    review_ai_assessment,
    list_ai_reviews,
    get_patient_clinical_summary,
    has_pending_ai_reviews,
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


def _documentation_fields(encounter: dict[str, Any]) -> dict[str, str | None]:
    """Map the persisted encounter shape to the documentation completeness contract."""
    complaints = encounter.get("complaints") or {}
    examination = encounter.get("examination") or {}
    assessment = encounter.get("assessment") or {}
    plan = encounter.get("plan") or {}

    def value(*candidates: Any) -> str | None:
        for candidate in candidates:
            if candidate is not None and str(candidate).strip():
                return str(candidate)
        return None

    return {
        "chief_complaint": value(complaints.get("chief_complaint"), complaints.get("complaint")),
        "duration": value(complaints.get("duration"), complaints.get("duration_days")),
        "distribution": value(examination.get("distribution"), complaints.get("distribution")),
        "morphology": value(examination.get("morphology"), examination.get("lesion_morphology")),
        "assessment": value(assessment.get("summary"), assessment.get("diagnosis"), assessment.get("clinical_impression")),
        "plan": value(plan.get("summary"), plan.get("treatment"), plan.get("instructions")),
    }


class EncounterCreate(BaseModel):
    patient_id: str = Field(min_length=1, max_length=120)
    template: str | None = Field(default=None, min_length=1, max_length=80)
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


class EncounterSignoffCreate(BaseModel):
    attestation: str = Field(
        default="I reviewed the encounter documentation and clinical decision-making.",
        min_length=20,
        max_length=500,
    )


class FollowupCreate(BaseModel):
    due_at: str
    instructions: str = Field(min_length=3, max_length=2000)


class AIReviewCreate(BaseModel):
    media_id: str | None = Field(default=None, min_length=1, max_length=120)
    lesion_id: str | None = Field(default=None, min_length=1, max_length=120)
    request_id: str = Field(min_length=1, max_length=120)
    model_name: str = Field(min_length=1, max_length=120)
    model_provenance: str | None = Field(default=None, max_length=500)
    predicted_label: str = Field(min_length=1, max_length=200)
    confidence: float = Field(ge=0, le=1)
    accepted: bool = False


class AIReviewDecision(BaseModel):
    clinician_decision: str = Field(pattern="^(accepted|overridden|rejected)$")
    clinician_override_label: str | None = Field(default=None, max_length=200)


@router.get("/templates")
def clinical_templates(user: dict[str, Any] = Depends(require_roles("doctor", "admin", "auditor"))):
    _tenant(user)
    return {
        "templates": [
            {
                "condition": template.condition,
                "required_sections": template.required_sections,
                "scoring_tools": template.scoring_tools,
            }
            for template in TEMPLATES.values()
        ]
    }


@router.post("/encounters")
def post_encounter(req: EncounterCreate, user: dict[str, Any] = Depends(require_roles("doctor", "admin"))):
    organization_id, clinic_id = _tenant(user)
    selected_template = get_history_template(req.template) if req.template else None
    result = create_encounter(
        organization_id=organization_id,
        clinic_id=clinic_id,
        patient_id=req.patient_id,
        doctor_id=user["uid"],
        appointment_id=req.appointment_id,
        complaints={**req.complaints, **({"template": selected_template.condition} if selected_template else {})},
        examination=req.examination,
        assessment=req.assessment,
        plan=req.plan,
    )
    record_event(AuditEvent(action="encounter_created", resource_type="encounter", resource_id=result["id"], metadata={"patient_id": req.patient_id, "clinic_id": clinic_id}), user)
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
    record_event(AuditEvent(action="lesion_upserted", resource_type="lesion", resource_id=result["id"], metadata={"patient_id": req.patient_id, "lesion_code": req.lesion_code}), user)
    return result


@router.get("/patients/{patient_id}/lesions/{lesion_code}/timeline")
def lesion_timeline(patient_id: str, lesion_code: str, user: dict[str, Any] = Depends(require_roles("doctor", "admin", "auditor"))):
    _, clinic_id = _tenant(user)
    return list_lesion_timeline(clinic_id=clinic_id, patient_id=patient_id, lesion_code=lesion_code)


@router.post("/consents")
def post_consent(req: ConsentCreate, user: dict[str, Any] = Depends(require_roles("doctor", "admin", "receptionist"))):
    organization_id, clinic_id = _tenant(user)
    result = create_consent(organization_id=organization_id, clinic_id=clinic_id, recorded_by=user["uid"], **req.model_dump())
    record_event(AuditEvent(action="consent_recorded", resource_type="consent", resource_id=result["id"], metadata={"patient_id": req.patient_id, "purpose": req.purpose, "status": req.status}), user)
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
        record_event(AuditEvent(action="clinical_media_recorded", resource_type="clinical_media", resource_id=result["id"], metadata={"patient_id": req.patient_id, "kind": req.kind}), user)
        return result
    except PermissionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/patients/{patient_id}/summary")
def patient_clinical_summary(
    patient_id: str,
    user: dict[str, Any] = Depends(require_roles("doctor", "admin", "auditor", "receptionist")),
):
    _, clinic_id = _tenant(user)
    return get_patient_clinical_summary(clinic_id=clinic_id, patient_id=patient_id)


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


@router.post("/encounters/{encounter_id}/sign")
def sign_encounter(
    encounter_id: str,
    req: EncounterSignoffCreate,
    user: dict[str, Any] = Depends(require_roles("doctor", "admin")),
):
    organization_id, clinic_id = _tenant(user)
    encounter = get_encounter(encounter_id, clinic_id)
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")
    if encounter["status"] == "signed":
        existing = get_signoff(clinic_id=clinic_id, encounter_id=encounter_id)
        return existing or {"status": "signed"}

    issues = validate_encounter(_documentation_fields(encounter))
    if issues:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "documentation_incomplete",
                "message": "Clinical sign-off requires the minimum dermatology documentation fields.",
                "issues": [issue.__dict__ for issue in issues],
            },
        )

    if has_pending_ai_reviews(clinic_id=clinic_id, encounter_id=encounter_id):
        raise HTTPException(
            status_code=409,
            detail="Clinical sign-off requires an explicit clinician decision on every attached AI assessment.",
        )
    result = create_signoff(
        organization_id=organization_id,
        clinic_id=clinic_id,
        encounter_id=encounter_id,
        signed_by=user["uid"],
        attestation=req.attestation,
    )
    record_event(
        AuditEvent(
            action="encounter_signed",
            resource_type="encounter",
            resource_id=encounter_id,
            metadata={"patient_id": encounter["patient_id"]},
        ),
        user,
    )
    return result


@router.get("/encounters/{encounter_id}/signoff")
def read_signoff(
    encounter_id: str,
    user: dict[str, Any] = Depends(require_roles("doctor", "admin", "auditor")),
):
    _, clinic_id = _tenant(user)
    if not get_encounter(encounter_id, clinic_id):
        raise HTTPException(status_code=404, detail="Encounter not found")
    return get_signoff(clinic_id=clinic_id, encounter_id=encounter_id)


@router.post("/encounters/{encounter_id}/followups")
def post_followup(
    encounter_id: str,
    req: FollowupCreate,
    user: dict[str, Any] = Depends(require_roles("doctor", "admin")),
):
    organization_id, clinic_id = _tenant(user)
    encounter = get_encounter(encounter_id, clinic_id)
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")
    result = create_followup(
        organization_id=organization_id,
        clinic_id=clinic_id,
        encounter_id=encounter_id,
        patient_id=encounter["patient_id"],
        due_at=req.due_at,
        instructions=req.instructions,
        created_by=user["uid"],
    )
    record_event(
        AuditEvent(
            action="followup_planned",
            resource_type="followup",
            resource_id=result["id"],
            metadata={"patient_id": encounter["patient_id"], "encounter_id": encounter_id},
        ),
        user,
    )
    return result


@router.get("/patients/{patient_id}/followups")
def patient_followups(
    patient_id: str,
    user: dict[str, Any] = Depends(require_roles("doctor", "admin", "receptionist", "auditor")),
):
    _, clinic_id = _tenant(user)
    return list_followups(clinic_id=clinic_id, patient_id=patient_id)


@router.post("/encounters/{encounter_id}/ai-reviews")
def post_ai_review(
    encounter_id: str,
    req: AIReviewCreate,
    user: dict[str, Any] = Depends(require_roles("doctor", "admin")),
):
    organization_id, clinic_id = _tenant(user)
    encounter = get_encounter(encounter_id, clinic_id)
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")
    payload = req.model_dump()
    media_id = payload.get("media_id")
    lesion_id = payload.get("lesion_id")
    if media_id or lesion_id:
        from clinical_store import list_media, list_lesion_timeline
        if media_id:
            media = [item for item in list_media(clinic_id=clinic_id, patient_id=encounter["patient_id"]) if item["id"] == media_id]
            if not media or media[0].get("encounter_id") != encounter_id:
                raise HTTPException(status_code=404, detail="Linked clinical media not found for encounter")
            if media[0].get("lesion_id") and lesion_id and media[0]["lesion_id"] != lesion_id:
                raise HTTPException(status_code=409, detail="Media and lesion linkage conflict")
        if lesion_id:
            timeline = list_lesion_timeline(clinic_id=clinic_id, patient_id=encounter["patient_id"], lesion_code=lesion_id)
            if not timeline:
                raise HTTPException(status_code=404, detail="Linked lesion not found for patient")
            if not any(item.get("encounter_id") == encounter_id for item in timeline):
                raise HTTPException(status_code=409, detail="Linked lesion is not part of encounter")
    result = record_ai_review(
        organization_id=organization_id,
        clinic_id=clinic_id,
        encounter_id=encounter_id,
        **payload,
    )
    record_event(
        AuditEvent(
            action="ai_assessment_attached",
            resource_type="encounter_ai_review",
            resource_id=result["id"],
            metadata={"patient_id": encounter["patient_id"], "encounter_id": encounter_id},
        ),
        user,
    )
    return result


@router.patch("/encounters/{encounter_id}/ai-reviews/{review_id}")
def patch_ai_review(
    encounter_id: str,
    review_id: str,
    req: AIReviewDecision,
    user: dict[str, Any] = Depends(require_roles("doctor", "admin")),
):
    _, clinic_id = _tenant(user)
    encounter = get_encounter(encounter_id, clinic_id)
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")
    try:
        result = review_ai_assessment(
            clinic_id=clinic_id,
            encounter_id=encounter_id,
            review_id=review_id,
            clinician_decision=req.clinician_decision,
            clinician_override_label=req.clinician_override_label,
            reviewed_by=user["uid"],
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    record_event(
        AuditEvent(
            action="ai_assessment_reviewed",
            resource_type="encounter_ai_review",
            resource_id=review_id,
            metadata={
                "patient_id": encounter["patient_id"],
                "encounter_id": encounter_id,
                "decision": req.clinician_decision,
            },
        ),
        user,
    )
    return result


@router.get("/encounters/{encounter_id}/ai-reviews")
def encounter_ai_reviews(
    encounter_id: str,
    user: dict[str, Any] = Depends(require_roles("doctor", "admin", "auditor")),
):
    _, clinic_id = _tenant(user)
    if not get_encounter(encounter_id, clinic_id):
        raise HTTPException(status_code=404, detail="Encounter not found")
    return list_ai_reviews(clinic_id=clinic_id, encounter_id=encounter_id)
