from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from audit import AuditEvent, record_event
from auth import require_roles
from dermatology.clinical_ai_api import ADVISORY_ENVELOPE
from medguide_ai import GuidelineStore, PatientContext, load_guideline_dir
from medguide_ai.updates import REVIEW_OUTCOMES, acknowledge, check_for_updates, list_pending

router = APIRouter(
    prefix="/api/v1/dermatology/guidelines",
    tags=["dermatology-guidelines"],
)

_DEFAULT_DIR = Path(__file__).resolve().parent.parent / "guidelines"


def _dir() -> Path:
    return Path(os.getenv("GUIDELINES_DIR", str(_DEFAULT_DIR)))


@lru_cache(maxsize=1)
def _store() -> GuidelineStore:
    return load_guideline_dir(_dir())


@router.get("")
def list_guidelines(_: dict = Depends(require_roles("doctor", "admin"))) -> dict[str, object]:
    return {
        "advisory": ADVISORY_ENVELOPE,
        "sources": _store().available_sources(),
        "guidelines": _store().list_guidelines(),
    }


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


class ReviewRequest(BaseModel):
    outcome: str


@router.get("/updates")
def pending_updates(_: dict = Depends(require_roles("doctor", "admin"))) -> dict[str, object]:
    return {"pending": list_pending(_dir())}


@router.post("/updates/check")
def run_update_check(user: dict = Depends(require_roles("admin"))) -> dict[str, object]:
    result = check_for_updates(_dir())
    record_event(
        AuditEvent(
            action="guideline_update_check",
            resource_type="guideline",
            resource_id="monitor",
            metadata={key: len(value) for key, value in result.items()},
        ),
        user,
    )
    return result


@router.post("/updates/{notice_id}/review")
def review_update(
    notice_id: str,
    req: ReviewRequest,
    user: dict = Depends(require_roles("doctor", "admin")),
) -> dict[str, object]:
    if req.outcome not in REVIEW_OUTCOMES:
        raise HTTPException(status_code=422, detail="Unsupported review outcome")
    try:
        notice = acknowledge(_dir(), notice_id, str(user["uid"]), req.outcome)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Invalid notice id") from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Update notice not found") from exc
    if req.outcome == "entry_updated":
        _store.cache_clear()
    record_event(
        AuditEvent(
            action="guideline_update_reviewed",
            resource_type="guideline_update",
            resource_id=notice_id,
            metadata={"outcome": req.outcome},
        ),
        user,
    )
    return notice
