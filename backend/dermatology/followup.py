from __future__ import annotations

from dataclasses import dataclass

from typing import Final


VALID_STATUSES: Final[tuple[str, ...]] = ("planned","confirmed","completed","cancelled")

@dataclass(frozen=True)
class FollowUpPlan:
    encounter_id: str
    patient_id: str
    due_at: str
    instructions: str
    status: str = "planned"

def validate_followup(plan: FollowUpPlan) -> None:
    if not plan.encounter_id.strip() or not plan.patient_id.strip():
        raise ValueError("encounter_id and patient_id are required")
    if not plan.due_at.strip():
        raise ValueError("due_at is required")
    if not plan.instructions.strip():
        raise ValueError("instructions are required")
    if plan.status not in VALID_STATUSES:
        raise ValueError(f"Unsupported follow-up status: {plan.status}")

def next_status(current: str, requested: str) -> str:
    if current not in VALID_STATUSES or requested not in VALID_STATUSES:
        raise ValueError("Unsupported follow-up status")
    if current == "completed" and requested != "completed":
        raise ValueError("Completed follow-ups cannot be reopened")
    if current == "cancelled" and requested != "cancelled":
        raise ValueError("Cancelled follow-ups cannot be reopened")
    return requested
