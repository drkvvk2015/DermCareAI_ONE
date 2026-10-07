from __future__ import annotations

import logging
import os
import threading
from datetime import datetime, timezone
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
logger = logging.getLogger(__name__)


def _dir() -> Path:
    return Path(os.getenv("GUIDELINES_DIR", str(_DEFAULT_DIR)))


class _Loaded:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.reset()

    def reset(self) -> None:
        self.directory: Path | None = None
        self.signature: tuple | None = None
        self.store = GuidelineStore()
        self.loaded_at: str | None = None
        self.load_error = False


_loaded = _Loaded()


def _signature(directory: Path) -> tuple:
    if not directory.is_dir():
        return ()
    return tuple(
        (p.name, p.stat().st_mtime_ns, p.stat().st_size) for p in sorted(directory.glob("*.json"))
    )


def _store() -> GuidelineStore:
    """Return the approved guideline store, reloading when any guideline file changes."""
    directory = _dir()
    signature = _signature(directory)
    with _loaded.lock:
        if directory != _loaded.directory or signature != _loaded.signature:
            try:
                _loaded.store = load_guideline_dir(directory)
                _loaded.load_error = False
                _loaded.loaded_at = datetime.now(timezone.utc).isoformat()
            except Exception as exc:  # keep serving the last good set; never load unvalidated entries
                _loaded.load_error = True
                logger.error("Guideline reload rejected: %s", type(exc).__name__)
            _loaded.directory = directory
            _loaded.signature = signature
        return _loaded.store


def reset_store() -> None:
    with _loaded.lock:
        _loaded.reset()


@router.get("")
def list_guidelines(_: dict = Depends(require_roles("doctor", "admin"))) -> dict[str, object]:
    store = _store()
    return {
        "advisory": ADVISORY_ENVELOPE,
        "sources": store.available_sources(),
        "guidelines": store.list_guidelines(),
        "loaded_at": _loaded.loaded_at,
        "reload_rejected": _loaded.load_error,
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
        reset_store()
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
