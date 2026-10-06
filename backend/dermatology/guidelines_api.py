from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, Depends

from audit import AuditEvent, record_event
from auth import require_roles
from dermatology.clinical_ai_api import ADVISORY_ENVELOPE
from medguide_ai import GuidelineStore, PatientContext, load_guideline_dir

router = APIRouter(
    prefix="/api/v1/dermatology/guidelines",
    tags=["dermatology-guidelines"],
)

_DEFAULT_DIR = Path(__file__).resolve().parent.parent / "guidelines"


@lru_cache(maxsize=1)
def _store() -> GuidelineStore:
    return load_guideline_dir(Path(os.getenv("GUIDELINES_DIR", str(_DEFAULT_DIR))))


@router.get("")
def list_guidelines(_: dict = Depends(require_roles("doctor", "admin"))) -> dict[str, object]:
    return {"advisory": ADVISORY_ENVELOPE, "guidelines": _store().list_guidelines()}


@router.post("/recommend")
def recommend(
    patient: PatientContext,
    user: dict = Depends(require_roles("doctor", "admin")),
) -> dict[str, object]:
    result = _store().recommend(patient)
    record_event(
        AuditEvent(
            action="guideline_suggestion_requested",
            resource_type="guideline",
            resource_id=result.guideline_id if result else "no_match",
            metadata={"matched": result is not None},
        ),
        user,
    )
    return {
        "advisory": ADVISORY_ENVELOPE,
        "matched": result is not None,
        "recommendation": result.model_dump() if result else None,
    }
