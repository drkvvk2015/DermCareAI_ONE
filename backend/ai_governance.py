"""Safety-first AI decision provenance for every clinical screening result."""
from __future__ import annotations

from typing import Any

from platform_contracts import AIGovernanceCard


def build_governance_card(
    *,
    model_name: str,
    model_provenance: str,
    confidence_threshold: float,
    research_model: bool,
) -> dict[str, Any]:
    card = AIGovernanceCard(
        decision_type="clinical_decision_support",
        intended_use="Assist a qualified clinician with dermatology image review and prioritisation.",
        diagnostic_status="not_a_diagnosis",
        human_review_required=True,
        abstention_enabled=True,
        confidence_threshold=confidence_threshold,
        model_provenance=model_provenance,
        model_name=model_name,
        research_model=research_model,
        safety_controls=[
            "Image-quality gate",
            "Minimum confidence threshold",
            "Explicit abstention on uncertain output",
            "Human clinician review requirement",
            "Model provenance and application version reporting",
        ],
        limitations=[
            "Performance may vary across populations, devices, lighting and acquisition conditions.",
            "Research models are not established as standalone diagnostic devices.",
            "A model prediction must be interpreted with clinical history, examination and indicated investigations.",
        ],
    )
    return card.model_dump()
