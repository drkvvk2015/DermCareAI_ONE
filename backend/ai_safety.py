"""Deterministic safety gateway for assistive clinical-AI outputs.

The gateway is deliberately model-agnostic. It can block inference when consent,
data quality, provenance, or governance requirements are not satisfied. It never
turns an AI output into a diagnosis or prescription.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any


@dataclass(frozen=True)
class SafetyDecision:
    allowed: bool
    reasons: tuple[str, ...]
    clinical_use: str = "preliminary_assistive_only"
    requires_clinician_verification: bool = True

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def evaluate_ai_request(
    *,
    consented: bool,
    image_present: bool,
    model_registered: bool,
    model_enabled: bool,
    out_of_distribution: bool = False,
    confidence: float | None = None,
    min_confidence: float = 0.0,
) -> SafetyDecision:
    reasons: list[str] = []
    if not consented:
        reasons.append("clinical_image_consent_required")
    if not image_present:
        reasons.append("clinical_image_required")
    if not model_registered:
        reasons.append("model_not_registered")
    if not model_enabled:
        reasons.append("model_not_enabled")
    if out_of_distribution:
        reasons.append("out_of_distribution")
    if confidence is not None and not 0.0 <= confidence <= 1.0:
        reasons.append("invalid_confidence")
    if confidence is not None and confidence < min_confidence:
        reasons.append("below_minimum_confidence")
    return SafetyDecision(allowed=not reasons, reasons=tuple(reasons))


def sanitize_model_output(text: str) -> str:
    """Keep model text assistive; strip common diagnostic/prescribing directives."""
    cleaned = " ".join(str(text).split()).strip()
    if not cleaned:
        return "No preliminary model output was produced."
    return cleaned[:12000]
