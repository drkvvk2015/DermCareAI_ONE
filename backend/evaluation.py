"""Model evaluation and inference safety utilities.

This module is intentionally model-agnostic so CI can evaluate prediction
artefacts even when proprietary/local model weights are unavailable.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isnan
from typing import Iterable, Mapping, Sequence

from ai_safety import evaluate_ai_request


ABSTAIN_LABEL = "Uncertain / Needs Clinical Review"


@dataclass(frozen=True)
class SafetyDecision:
    accepted: bool
    reason: str
    confidence: float
    needs_clinician_review: bool = True


@dataclass(frozen=True)
class ClassificationMetrics:
    count: int
    accuracy: float
    macro_sensitivity: float
    macro_specificity: float


def safe_confidence(value: object) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    if isnan(number):
        return 0.0
    return max(0.0, min(1.0, number))


def safety_gate(
    *,
    class_name: str,
    confidence: object,
    image_quality_ok: bool = True,
    minimum_confidence: float = 0.70,
    model_registered: bool = True,
    model_enabled: bool = True,
    consented: bool = True,
    out_of_distribution: bool = False,
) -> SafetyDecision:
    """Convert raw model output into the governed AI safety decision used by inference.

    Standalone /predict inference is intentionally consent-neutral because it has no
    patient context. Consent is enforced again at the clinical media / AI-review
    boundary where a patient and tenant are known.
    """
    score = safe_confidence(confidence)
    if not image_quality_ok:
        return SafetyDecision(False, "Image quality is insufficient for reliable inference.", score)

    decision = evaluate_ai_request(
        consented=consented,
        image_present=bool(class_name.strip()),
        model_registered=model_registered,
        model_enabled=model_enabled,
        out_of_distribution=out_of_distribution,
        confidence=score,
        min_confidence=minimum_confidence,
    )
    if not decision.allowed:
        reason_map = {
            "clinical_image_consent_required": "Clinical image consent is required for a patient-linked inference.",
            "clinical_image_required": "The model returned no classification.",
            "model_not_registered": "The model is not registered for governed use.",
            "model_not_enabled": "The model is not enabled for governed use.",
            "out_of_distribution": "The image is outside the supported distribution.",
            "invalid_confidence": "Prediction confidence is invalid.",
            "below_minimum_confidence": "Prediction confidence is below the safety threshold.",
        }
        return SafetyDecision(
            False,
            next((reason_map[item] for item in decision.reasons if item in reason_map), "Prediction failed the automated safety gate."),
            score,
        )
    return SafetyDecision(True, "Prediction passed the governed AI safety gateway.", score)


def classification_metrics(
    y_true: Sequence[str], y_pred: Sequence[str], labels: Iterable[str]
) -> ClassificationMetrics:
    labels = list(labels)
    if len(y_true) != len(y_pred):
        raise ValueError("y_true and y_pred must have the same length")
    if not y_true:
        raise ValueError("At least one evaluation sample is required")
    if not labels:
        raise ValueError("At least one label is required")

    correct = sum(actual == predicted for actual, predicted in zip(y_true, y_pred))
    sensitivities = []
    specificities = []
    total = len(y_true)

    for label in labels:
        tp = sum(a == label and p == label for a, p in zip(y_true, y_pred))
        fn = sum(a == label and p != label for a, p in zip(y_true, y_pred))
        fp = sum(a != label and p == label for a, p in zip(y_true, y_pred))
        tn = total - tp - fn - fp
        sensitivities.append(tp / (tp + fn) if tp + fn else 0.0)
        specificities.append(tn / (tn + fp) if tn + fp else 0.0)

    return ClassificationMetrics(
        count=total,
        accuracy=correct / total,
        macro_sensitivity=sum(sensitivities) / len(sensitivities),
        macro_specificity=sum(specificities) / len(specificities),
    )


def validate_prediction_payload(payload: Mapping[str, object]) -> list[str]:
    errors: list[str] = []
    required = {"class_name", "confidence", "model_used", "visualization"}
    errors.extend(f"missing:{field}" for field in sorted(required - set(payload)))
    if "confidence" in payload:
        confidence = float(payload["confidence"])
        if not 0.0 <= confidence <= 1.0:
            errors.append("confidence_out_of_range")
    if "class_name" in payload and not str(payload["class_name"]).strip():
        errors.append("empty_class_name")
    if "model_used" in payload and not str(payload["model_used"]).strip():
        errors.append("empty_model_used")
    return errors
