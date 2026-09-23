"""Structured dermatology encounter completeness checks.

These checks are documentation-quality gates only. They do not diagnose, rank
treatments, or replace clinician judgment.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CompletenessIssue:
    field: str
    message: str
    severity: str = "warning"


REQUIRED_FIELDS = (
    "chief_complaint",
    "duration",
    "distribution",
    "morphology",
    "assessment",
    "plan",
)


def validate_encounter(fields: dict[str, str | None]) -> tuple[CompletenessIssue, ...]:
    issues: list[CompletenessIssue] = []
    for field in REQUIRED_FIELDS:
        value = fields.get(field)
        if value is None or not str(value).strip():
            issues.append(
                CompletenessIssue(field=field, message=f"Document {field.replace('_', ' ')} before finalizing the encounter.")
            )
    if fields.get("assessment") and not fields.get("plan"):
        issues.append(
            CompletenessIssue(
                field="plan",
                message="An assessment is documented without a corresponding plan.",
                severity="warning",
            )
        )
    return tuple(issues)


def can_finalize_encounter(fields: dict[str, str | None]) -> bool:
    return not any(issue.field in REQUIRED_FIELDS for issue in validate_encounter(fields))


DERMATOLOGY_RECOMMENDED_FIELDS = (
    "onset_and_course",
    "site_and_distribution_detail",
    "primary_lesion",
    "secondary_changes",
    "color",
    "surface",
    "border",
    "configuration",
    "palpation",
    "symptoms",
    "exposure_history",
    "drug_history",
    "atopy_history",
    "family_history",
    "systemic_symptoms",
)


def recommended_field_issues(fields: dict[str, str | None]) -> tuple[CompletenessIssue, ...]:
    """Return non-blocking prompts for richer dermatology documentation."""
    return tuple(
        CompletenessIssue(
            field=field,
            message=f"Consider documenting {field.replace('_', ' ')} when clinically relevant.",
            severity="info",
        )
        for field in DERMATOLOGY_RECOMMENDED_FIELDS
        if fields.get(field) is None or not str(fields.get(field)).strip()
    )
