from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from auth import require_roles
from dermatology.telederm import TeledermSession, TeledermStatus

router = APIRouter(prefix="/api/v1/dermatology/telederm", tags=["telederm"])


class TeledermCreateRequest(BaseModel):
    patient_id: str = Field(min_length=1, max_length=200)
    clinician_id: str = Field(min_length=1, max_length=200)


class TeledermConsentRequest(BaseModel):
    consent_record_id: str = Field(min_length=1, max_length=200)


class TeledermTransitionRequest(BaseModel):
    status: TeledermStatus


@router.post("/sessions")
def create_session(
    request: TeledermCreateRequest,
    _: dict = Depends(require_roles("doctor", "admin")),
):
    return TeledermSession.create(request.patient_id, request.clinician_id).__dict__


@router.post("/sessions/{session_id}/consent")
def record_consent(
    session_id: str,
    request: TeledermConsentRequest,
    _: dict = Depends(require_roles("doctor", "admin")),
):
    # Session persistence is intentionally delegated to the clinical store in the next
    # integration step; this endpoint validates the consent transition contract.
    session = TeledermSession(
        session_id=session_id,
        patient_id="",
        clinician_id="",
        status=TeledermStatus.REQUESTED,
        consent_record_id=None,
        created_at="",
        updated_at="",
    )
    try:
        return session.consent(request.consent_record_id).__dict__
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
