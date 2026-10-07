"""Deterministic guideline lookup; output is advisory and always needs clinician review."""
from __future__ import annotations

import json
from datetime import date
from enum import Enum
from pathlib import Path
from typing import Iterable, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

GuidelineSource = Literal["IADVL", "AAD", "BAD", "NICE"]
SUPPORTED_SOURCES: tuple[str, ...] = ("IADVL", "AAD", "BAD", "NICE")

_STRENGTH_HEURISTIC = {"high": 0.95, "moderate": 0.8, "low": 0.65}
_STRENGTH_RANK = {"high": 2, "moderate": 1, "low": 0}
_MISSING_INFO_PENALTY = 0.15
_CONTRAINDICATION_PENALTY = 0.2
_MIN_HEURISTIC_SCORE = 0.05
_ESCALATION_THRESHOLD = 0.7
_MAX_ALTERNATIVES = 3


class EvidenceStrength(str, Enum):
    HIGH = "high"
    MODERATE = "moderate"
    LOW = "low"


class TrustedSource(BaseModel):
    name: GuidelineSource
    category: str = Field(min_length=1)
    region: str = "global"


class EvidenceVersion(BaseModel):
    guideline_id: str = Field(min_length=1)
    version: str = Field(min_length=1)
    publication_date: date

    @field_validator("publication_date")
    @classmethod
    def _publication_date_is_valid(cls, value: date) -> date:
        if value > date.today():
            raise ValueError("publication_date cannot be in the future")
        return value


class EvidenceItem(BaseModel):
    """A guideline entry; usable only when a named clinician has approved it."""

    model_config = ConfigDict(frozen=True)

    guideline_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    disease: str = Field(min_length=1)
    match_terms: tuple[str, ...] = ()
    recommendation: str = Field(min_length=1)
    supporting_evidence: tuple[str, ...] = ()
    strength: EvidenceStrength
    source: TrustedSource
    version: EvidenceVersion
    medications: tuple[str, ...] = ()
    contraindications: tuple[str, ...] = ()
    required_information: tuple[str, ...] = ()
    region: str = "global"
    approved_by: str = Field(min_length=1)
    approved_on: date

    @field_validator("approved_by")
    @classmethod
    def _approved_by_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("clinician approval is required")
        return value

    @field_validator("approved_on")
    @classmethod
    def _approval_date_is_valid(cls, value: date) -> date:
        if value > date.today():
            raise ValueError("approved_on cannot be in the future")
        return value


class PatientContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    symptoms: tuple[str, ...] = Field(default=(), max_length=50)
    conditions: tuple[str, ...] = Field(default=(), max_length=50)
    medications: tuple[str, ...] = Field(default=(), max_length=100)
    allergies: tuple[str, ...] = Field(default=(), max_length=50)
    sources: tuple[GuidelineSource, ...] = Field(default=(), max_length=4)


class Recommendation(BaseModel):
    summary: str
    guideline_id: str
    guideline_version: str
    citations: tuple[str, ...]
    evidence_quality: str
    approved_by: str
    approved_on: str
    matched_terms: tuple[str, ...]
    missing_information: tuple[str, ...]
    contraindications_flagged: tuple[str, ...]
    alternatives: tuple[str, ...]
    heuristic_score: float
    escalation_required: bool
    notes: tuple[str, ...]
    human_review_required: bool = True


def _norm(values: Iterable[str]) -> set[str]:
    return {value.strip().lower() for value in values if value and value.strip()}


class GuidelineStore:
    def __init__(self, items: Iterable[EvidenceItem] = ()) -> None:
        self._items: dict[str, EvidenceItem] = {}
        for item in items:
            self.add(item)

    def add(self, item: EvidenceItem) -> None:
        if item.guideline_id in self._items:
            raise ValueError(f"Duplicate guideline_id: {item.guideline_id}")
        self._items[item.guideline_id] = item

    def list_guidelines(self) -> list[dict[str, str]]:
        return [
            {
                "guideline_id": item.guideline_id,
                "title": item.title,
                "disease": item.disease,
                "version": item.version.version,
                "source": item.source.name,
                "publication_date": item.version.publication_date.isoformat(),
            }
            for item in sorted(self._items.values(), key=lambda item: item.guideline_id)
        ]

    def available_sources(self) -> dict[str, int]:
        counts = {source: 0 for source in SUPPORTED_SOURCES}
        for item in self._items.values():
            counts[item.source.name] += 1
        return counts

    def _match(self, patient: PatientContext) -> list[tuple[EvidenceItem, tuple[str, ...]]]:
        terms = _norm((*patient.symptoms, *patient.conditions))
        selected = set(patient.sources)
        matches: list[tuple[EvidenceItem, tuple[str, ...]]] = []

        for item in self._items.values():
            if selected and item.source.name not in selected:
                continue
            keys = {item.disease.lower(), *_norm(item.match_terms)}
            hit = tuple(sorted(terms & keys))
            if hit:
                matches.append((item, hit))

        matches.sort(
            key=lambda match: (
                _STRENGTH_RANK[match[0].strength.value],
                match[0].version.publication_date,
                match[0].guideline_id,
            ),
            reverse=True,
        )
        return matches

    def recommend(self, patient: PatientContext) -> Recommendation | None:
        matches = self._match(patient)
        if not matches:
            return None

        item, hit = matches[0]
        meds = _norm(patient.medications)
        flagged = tuple(
            sorted(
                contraindication
                for contraindication in item.contraindications
                if contraindication.lower() in _norm((*patient.conditions, *patient.allergies))
            )
        )
        findings = _norm((*patient.symptoms, *patient.conditions))
        missing = tuple(
            sorted(
                required
                for required in item.required_information
                if required.lower() not in findings
            )
        )

        heuristic_score = _STRENGTH_HEURISTIC[item.strength.value]
        heuristic_score -= _MISSING_INFO_PENALTY * len(missing)
        heuristic_score -= _CONTRAINDICATION_PENALTY * len(flagged)
        heuristic_score = round(max(_MIN_HEURISTIC_SCORE, min(heuristic_score, 0.99)), 2)

        alternatives = tuple(
            dict.fromkeys(
                match.recommendation
                for match, _ in matches[1 : 1 + _MAX_ALTERNATIVES]
                if match.recommendation != item.recommendation
            )
        )

        notes = [
            "Suggestion only; the treating clinician makes the decision.",
            "Drug interactions and dose adjustment were not evaluated by this lookup.",
            "Heuristic score is not calibrated clinical confidence and must not be interpreted as such.",
        ]
        if meds & _norm(item.medications):
            notes.append("Patient already lists a medication named in this guideline; review for continuity.")
        if missing:
            notes.append("Additional clinical information is needed before relying on this suggestion.")
        if flagged:
            notes.append("Possible contraindication matched; review before use.")
        if item.region != "global":
            notes.append(f"Confirm applicability to region: {item.region}.")

        return Recommendation(
            summary=item.recommendation,
            guideline_id=item.guideline_id,
            guideline_version=item.version.version,
            citations=(
                f"{item.source.name} | {item.guideline_id} | {item.version.version}",
                *item.supporting_evidence,
            ),
            evidence_quality=item.strength.value,
            approved_by=item.approved_by,
            approved_on=item.approved_on.isoformat(),
            matched_terms=hit,
            missing_information=missing,
            contraindications_flagged=flagged,
            alternatives=alternatives,
            heuristic_score=heuristic_score,
            escalation_required=bool(flagged) or heuristic_score < _ESCALATION_THRESHOLD,
            notes=tuple(notes),
        )


def load_guideline_dir(directory: Path) -> GuidelineStore:
    """Load approved guideline JSON files (an object or a list of objects per file)."""
    store = GuidelineStore()
    if not directory.is_dir():
        return store

    for path in sorted(directory.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        for entry in payload if isinstance(payload, list) else [payload]:
            store.add(EvidenceItem.model_validate(entry))
    return store
