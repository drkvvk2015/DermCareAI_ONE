from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter(prefix="/audit", tags=["audit"])


class AuditEvent(BaseModel):
    actor_id: str = Field(min_length=1, max_length=200)
    actor_role: str = Field(min_length=1, max_length=100)
    action: str = Field(min_length=1, max_length=200)
    resource_type: str = Field(min_length=1, max_length=100)
    resource_id: str = Field(min_length=1, max_length=200)
    metadata: Dict[str, Any] = {}
    correlation_id: str | None = None


AUDIT_EVENTS: list[Dict[str, Any]] = []


def record_event(event: AuditEvent) -> Dict[str, Any]:
    entry = {
        "id": f"AUD-{len(AUDIT_EVENTS) + 1:09d}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **event.model_dump(),
    }
    AUDIT_EVENTS.append(entry)
    return entry


@router.post("/events")
def create_audit_event(event: AuditEvent):
    return record_event(event)


@router.get("/events")
def list_audit_events(limit: int = 100):
    return list(reversed(AUDIT_EVENTS[-max(1, min(limit, 500)):]))
