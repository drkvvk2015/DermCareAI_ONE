from __future__ import annotations

"""Governed registry for clinical guideline/evidence provenance.

This registry deliberately stores metadata rather than silently treating arbitrary
web content as clinical guidance. High-consequence recommendations must resolve
to an approved source with explicit freshness and applicability metadata.
"""

from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Iterable


ALLOWED_STATUS = {"current", "superseded", "conflicting", "insufficient", "unable_to_verify"}
ALLOWED_TIERS = {"regulatory_public_health", "specialty_guideline", "systematic_review", "authoritative_drug_info", "primary_study"}


@dataclass(frozen=True)
class EvidenceRecord:
    evidence_id: str
    organization: str
    title: str
    tier: str
    publication_date: date | None
    update_date: date | None
    version: str
    stable_url: str
    document_id: str
    section: str | None
    recommendation_id: str | None
    retrieval_timestamp: datetime
    checksum_sha256: str | None
    status: str = "current"
    scope: str = ""

    def __post_init__(self) -> None:
        if not self.evidence_id.strip() or not self.organization.strip() or not self.title.strip():
            raise ValueError("Evidence identity fields are required")
        if self.tier not in ALLOWED_TIERS:
            raise ValueError(f"Unsupported evidence tier: {self.tier}")
        if self.status not in ALLOWED_STATUS:
            raise ValueError(f"Unsupported evidence status: {self.status}")
        if not self.version.strip() or not self.document_id.strip() or not self.stable_url.startswith("https://"):
            raise ValueError("Version, document ID, and HTTPS stable URL are required")
        if self.retrieval_timestamp.tzinfo is None:
            raise ValueError("Retrieval timestamp must be timezone-aware")
        if self.checksum_sha256 is not None and len(self.checksum_sha256) != 64:
            raise ValueError("Evidence checksum must be SHA-256 when supplied")

    @property
    def provenance(self) -> dict[str, str | None]:
        return {
            "evidence_id": self.evidence_id,
            "organization": self.organization,
            "title": self.title,
            "tier": self.tier,
            "publication_date": self.publication_date.isoformat() if self.publication_date else None,
            "update_date": self.update_date.isoformat() if self.update_date else None,
            "version": self.version,
            "stable_url": self.stable_url,
            "document_id": self.document_id,
            "section": self.section,
            "recommendation_id": self.recommendation_id,
            "retrieval_timestamp": self.retrieval_timestamp.astimezone(timezone.utc).isoformat(),
            "checksum_sha256": self.checksum_sha256,
            "status": self.status,
            "scope": self.scope,
        }


class EvidenceRegistry:
    def __init__(self, records: Iterable[EvidenceRecord] = ()) -> None:
        self._records = {record.evidence_id: record for record in records}

    def register(self, record: EvidenceRecord) -> None:
        self._records[record.evidence_id] = record

    def get(self, evidence_id: str) -> EvidenceRecord | None:
        return self._records.get(evidence_id)

    def current_for(self, topic: str) -> list[EvidenceRecord]:
        needle = topic.casefold().strip()
        return [
            record
            for record in self._records.values()
            if record.status == "current" and (needle in record.title.casefold() or needle in record.scope.casefold())
        ]

    def require_current(self, evidence_ids: Iterable[str]) -> list[EvidenceRecord]:
        records = [self._records.get(item) for item in evidence_ids]
        if any(record is None for record in records):
            raise ValueError("Requested evidence is not registered")
        resolved = [record for record in records if record is not None]
        if any(record.status != "current" for record in resolved):
            raise ValueError("A superseded, conflicting, or unverifiable source cannot support a current recommendation")
        return resolved


# Seed with no clinical claims. Deployments populate this registry from the hospital's
# governed evidence bundle after provenance and freshness checks.
DEFAULT_REGISTRY = EvidenceRegistry()
