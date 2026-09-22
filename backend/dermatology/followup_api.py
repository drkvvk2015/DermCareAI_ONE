from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from auth import require_roles
from clinical_store import list_followups
from dermatology.followup import next_status

router = APIRouter(prefix="/api/v1/dermatology/followups", tags=["dermatology-followups"])

class FollowupStatusUpdate(BaseModel):
    current_status: str = Field(min_length=1, max_length=30)
    requested_status: str = Field(min_length=1, max_length=30)

@router.post("/validate-transition")
def validate_transition(
    req: FollowupStatusUpdate,
    _: dict = Depends(require_roles("doctor", "admin")),
):
    try:
        next_value = next_status(req.current_status, req.requested_status)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"valid": True, "next_status": next_value}

@router.get("/patients/{patient_id}")
def patient_followup_state(patient_id: str, user: dict = Depends(require_roles("doctor", "admin", "receptionist", "auditor"))):
    claims = user.get("claims", {})
    clinic_id = claims.get("clinic_id") or claims.get("clinicId")
    if not clinic_id:
        raise HTTPException(status_code=403, detail="Clinical tenant context is missing")
    return {"patient_id": patient_id, "followups": list_followups(clinic_id=str(clinic_id), patient_id=patient_id)}
