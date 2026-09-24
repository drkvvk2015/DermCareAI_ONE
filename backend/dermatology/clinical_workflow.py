from __future__ import annotations
from dataclasses import dataclass
from typing import Final

@dataclass(frozen=True)
class HistoryTemplate:
    condition: str
    required_sections: tuple[str, ...]
    scoring_tools: tuple[str, ...] = ()

TEMPLATES: Final[dict[str, HistoryTemplate]] = {
    "acne": HistoryTemplate("acne", ("onset", "distribution", "severity", "treatment_history", "triggers")),
    "atopic_dermatitis": HistoryTemplate("atopic_dermatitis", ("onset", "distribution", "itch", "atopy", "triggers", "treatment_history"), ("SCORAD",)),
    "psoriasis": HistoryTemplate("psoriasis", ("onset", "distribution", "nail_involvement", "joint_symptoms", "treatment_history"), ("PASI",)),
    "vitiligo": HistoryTemplate("vitiligo", ("onset", "distribution", "progression", "mucosal_involvement", "family_history"), ("VASI",)),
    "urticaria": HistoryTemplate("urticaria", ("onset", "episode_duration", "frequency", "triggers", "angioedema", "medication_history")),
    "dermatophytosis": HistoryTemplate("dermatophytosis", ("site", "duration", "itch", "exposure", "recurrence", "prior_antifungal_use")),
    "alopecia": HistoryTemplate("alopecia", ("onset", "pattern", "shedding", "scalp_symptoms", "family_history", "systemic_symptoms"), ("SALT",)),
    "nail_disorder": HistoryTemplate("nail_disorder", ("nails_involved", "duration", "morphology", "pain", "trauma", "systemic_associations")),
    "leprosy": HistoryTemplate("leprosy", ("skin_lesion_count", "sensory_change", "nerve_symptoms", "contact_history", "systemic_symptoms")),
    "skin_cancer": HistoryTemplate("skin_cancer", ("onset", "change", "bleeding", "ulceration", "risk_factors", "prior_skin_cancer")),
}

def get_history_template(condition: str) -> HistoryTemplate:
    key = condition.strip().lower()
    if key not in TEMPLATES:
        raise ValueError(f"Unsupported dermatology condition: {condition}")
    return TEMPLATES[key]

def missing_sections(condition: str, completed_sections: set[str]) -> tuple[str, ...]:
    template = get_history_template(condition)
    return tuple(section for section in template.required_sections if section not in completed_sections)

def build_soap_note(*, subjective: str, objective: str, assessment: str, plan: str) -> dict[str, str]:
    sections = {k: v.strip() for k, v in {
        "subjective": subjective, "objective": objective,
        "assessment": assessment, "plan": plan,
    }.items()}
    if any(not value for value in sections.values()):
        raise ValueError("All SOAP sections must contain non-empty content")
    return sections


# Longitudinal lesion tracking is intentionally non-blocking: it supplements, but does not
# replace, the required clinical documentation and clinician sign-off workflow.
LONGITUDINAL_FIELDS: Final[tuple[str, ...]] = (
    "lesion_code", "body_site", "laterality", "morphology", "size_mm",
    "duration_days", "evolution", "symptoms", "comparison_note", "photo_reference",
)


def longitudinal_completeness(record: dict[str, object]) -> tuple[str, ...]:
    """Return missing longitudinal fields without making them clinical sign-off blockers."""
    return tuple(field for field in LONGITUDINAL_FIELDS if not record.get(field))
