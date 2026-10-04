from __future__ import annotations

"""Structured physician-final clinical copilot contract.

The engine is deliberately evidence-gated: it can assemble suggestions, safety
checks and treatment considerations, but it cannot sign a diagnosis, prescribe,
or modify a signed record.
"""

from dataclasses import dataclass, field
from typing import Any

from clinical_evidence_registry import EvidenceRecord


@dataclass(frozen=True)
class PatientContext:
    age_years: int | None = None
    pregnancy_status: str | None = None
    allergies: tuple[str, ...] = ()
    renal_function: str | None = None
    hepatic_function: str | None = None
    comorbidities: tuple[str, ...] = ()
    medications: tuple[str, ...] = ()
    previous_treatment_failures: tuple[str, ...] = ()
    red_flags: tuple[str, ...] = ()
    diagnosis_certainty: str | None = None


@dataclass(frozen=True)
class CopilotRecommendation:
    diagnosis_differential: tuple[str, ...] = ()
    supporting_features: tuple[str, ...] = ()
    missing_information: tuple[str, ...] = ()
    investigations: tuple[str, ...] = ()
    treatment_options: tuple[str, ...] = ()
    contraindication_checks: tuple[str, ...] = ()
    monitoring: tuple[str, ...] = ()
    referral_or_escalation: tuple[str, ...] = ()
    counselling: tuple[str, ...] = ()
    safety_flags: tuple[str, ...] = ()
    evidence: tuple[EvidenceRecord, ...] = ()
    abstained: bool = False
    abstention_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "diagnosis_differential": list(self.diagnosis_differential),
            "supporting_features": list(self.supporting_features),
            "missing_information": list(self.missing_information),
            "investigations": list(self.investigations),
            "treatment_options": list(self.treatment_options),
            "contraindication_checks": list(self.contraindication_checks),
            "monitoring": list(self.monitoring),
            "referral_or_escalation": list(self.referral_or_escalation),
            "counselling": list(self.counselling),
            "safety_flags": list(self.safety_flags),
            "evidence": [item.provenance for item in self.evidence],
            "abstained": self.abstained,
            "abstention_reason": self.abstention_reason,
            "human_authority": {
                "physician_final_decision": True,
                "ai_can_sign_diagnosis": False,
                "ai_can_prescribe": False,
                "ai_can_modify_signed_record": False,
            },
        }


def safety_gate(context: PatientContext) -> tuple[bool, str | None, tuple[str, ...]]:
    flags: list[str] = []
    if context.red_flags:
        flags.extend(context.red_flags)
    if context.pregnancy_status is None:
        flags.append("pregnancy status not documented when medication safety may depend on it")
    if context.allergies is None:
        flags.append("allergy status is unavailable")
    if flags:
        return False, "High-consequence recommendation requires physician review of unresolved safety context", tuple(flags)
    return True, None, ()


def build_copilot_recommendation(
    *,
    context: PatientContext,
    differential: tuple[str, ...],
    supporting_features: tuple[str, ...],
    missing_information: tuple[str, ...],
    investigations: tuple[str, ...],
    treatment_options: tuple[str, ...],
    contraindication_checks: tuple[str, ...],
    monitoring: tuple[str, ...],
    referral_or_escalation: tuple[str, ...],
    counselling: tuple[str, ...],
    evidence: tuple[EvidenceRecord, ...],
) -> CopilotRecommendation:
    safe, reason, safety_flags = safety_gate(context)
    if not safe or not evidence:
        return CopilotRecommendation(
            diagnosis_differential=differential,
            supporting_features=supporting_features,
            missing_information=missing_information,
            safety_flags=safety_flags,
            evidence=evidence,
            abstained=True,
            abstention_reason=reason or "No governed current evidence is available for this recommendation",
        )

    return CopilotRecommendation(
        diagnosis_differential=differential,
        supporting_features=supporting_features,
        missing_information=missing_information,
        investigations=investigations,
        treatment_options=treatment_options,
        contraindication_checks=contraindication_checks,
        monitoring=monitoring,
        referral_or_escalation=referral_or_escalation,
        counselling=counselling,
        safety_flags=safety_flags,
        evidence=evidence,
    )
