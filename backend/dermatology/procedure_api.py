from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from auth import require_roles
from audit import AuditEvent, record_event
from dermatology.procedures import SUPPORTED_PROCEDURES, ProcedureRecord, validate_procedure
from dermatology.procedure_store import create_procedure, list_procedures
from clinical_store import get_encounter, has_active_consent

router = APIRouter(prefix="/api/v1/dermatology/procedures", tags=["dermatology-procedures"])

def _tenant(user: dict[str, Any]) -> tuple[str, str]:
    claims = user.get("claims", {})
    organization_id = claims.get("organization_id") or claims.get("organizationId")
    clinic_id = claims.get("clinic_id") or claims.get("clinicId")
    if not organization_id or not clinic_id:
        raise HTTPException(status_code=403, detail="Clinical tenant context is missing")
    return str(organization_id), str(clinic_id)

class ProcedureCreate(BaseModel):
    patient_id: str = Field(min_length=1, max_length=120)
    encounter_id: str = Field(min_length=1, max_length=120)
    procedure_type: str = Field(min_length=1, max_length=60)
    body_site: str = Field(min_length=1, max_length=120)
    indication: str = Field(min_length=1, max_length=1000)
    consent_id: str = Field(min_length=1, max_length=120)
    performed_at: str = Field(min_length=1, max_length=80)
    outcome: str | None = Field(default=None, max_length=2000)

@router.get("/supported")
def supported_procedures(_: dict[str, Any] = Depends(require_roles("doctor", "admin", "auditor"))):
    return {"procedures": list(SUPPORTED_PROCEDURES)}

@router.post("")
def post_procedure(
    req: ProcedureCreate,
    user: dict[str, Any] = Depends(require_roles("doctor", "admin")),
):
    organization_id, clinic_id = _tenant(user)
    encounter = get_encounter(req.encounter_id, clinic_id)
    if not encounter or encounter["patient_id"] != req.patient_id:
        raise HTTPException(status_code=404, detail="Encounter not found for patient")
    if not has_active_consent(clinic_id=clinic_id, patient_id=req.patient_id, purpose="procedure"):
        raise HTTPException(status_code=409, detail="Active procedure consent is required")
    try:
        validate_procedure(ProcedureRecord(
            procedure_type=req.procedure_type,
            body_site=req.body_site,
            indication=req.indication,
            consent_id=req.consent_id,
            performed_by=user["uid"],
            performed_at=req.performed_at,
            outcome=req.outcome,
        ))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    result = create_procedure(
        organization_id=organization_id,
        clinic_id=clinic_id,
        patient_id=req.patient_id,
        encounter_id=req.encounter_id,
        procedure_type=req.procedure_type,
        body_site=req.body_site,
        indication=req.indication,
        consent_id=req.consent_id,
        performed_by=user["uid"],
        performed_at=req.performed_at,
        outcome=req.outcome,
    )
    record_event(
        AuditEvent(
            action="dermatology_procedure_recorded",
            resource_type="dermatology_procedure",
            resource_id=result["id"],
            metadata={"patient_id": req.patient_id, "encounter_id": req.encounter_id, "procedure_type": req.procedure_type},
        ),
        user,
    )
    return result

@router.get("/patients/{patient_id}")
def patient_procedures(patient_id: str, user: dict[str, Any] = Depends(require_roles("doctor", "admin", "auditor"))):
    _, clinic_id = _tenant(user)
    return list_procedures(clinic_id=clinic_id, patient_id=patient_id)
