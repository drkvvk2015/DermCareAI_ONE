"""Consent-aware teledermatology session state machine.

This module manages session metadata only. Media transport/storage remains behind
the existing authenticated media service and is never exposed as a public URL.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
from uuid import uuid4


class TeledermStatus(StrEnum):
    REQUESTED = "requested"
    CONSENTED = "consented"
    SCHEDULED = "scheduled"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


_ALLOWED: dict[TeledermStatus, set[TeledermStatus]] = {
    TeledermStatus.REQUESTED: {TeledermStatus.CONSENTED, TeledermStatus.CANCELLED},
    TeledermStatus.CONSENTED: {TeledermStatus.SCHEDULED, TeledermStatus.CANCELLED},
    TeledermStatus.SCHEDULED: {TeledermStatus.ACTIVE, TeledermStatus.CANCELLED},
    TeledermStatus.ACTIVE: {TeledermStatus.COMPLETED, TeledermStatus.CANCELLED},
    TeledermStatus.COMPLETED: set(),
    TeledermStatus.CANCELLED: set(),
}


@dataclass(frozen=True)
class TeledermSession:
    session_id: str
    patient_id: str
    clinician_id: str
    status: TeledermStatus
    consent_record_id: str | None
    created_at: str
    updated_at: str

    @classmethod
    def create(cls, patient_id: str, clinician_id: str) -> "TeledermSession":
        now = datetime.now(timezone.utc).isoformat()
        return cls(
            session_id=f"TD-{uuid4().hex}",
            patient_id=patient_id,
            clinician_id=clinician_id,
            status=TeledermStatus.REQUESTED,
            consent_record_id=None,
            created_at=now,
            updated_at=now,
        )

    def consent(self, consent_record_id: str) -> "TeledermSession":
        if not consent_record_id:
            raise ValueError("consent_record_id is required")
        return self._transition(TeledermStatus.CONSENTED, consent_record_id)

    def transition(self, status: TeledermStatus) -> "TeledermSession":
        if status is TeledermStatus.CONSENTED:
            raise ValueError("Use consent() to enter the consented state")
        return self._transition(status, self.consent_record_id)

    def _transition(self, status: TeledermStatus, consent_record_id: str | None) -> "TeledermSession":
        if status not in _ALLOWED[self.status]:
            raise ValueError(f"Invalid telederm transition: {self.status} -> {status}")
        if status in {TeledermStatus.SCHEDULED, TeledermStatus.ACTIVE, TeledermStatus.COMPLETED} and not consent_record_id:
            raise ValueError("Documented consent is required before clinical teledermatology")
        return TeledermSession(
            session_id=self.session_id,
            patient_id=self.patient_id,
            clinician_id=self.clinician_id,
            status=status,
            consent_record_id=consent_record_id,
            created_at=self.created_at,
            updated_at=datetime.now(timezone.utc).isoformat(),
        )
