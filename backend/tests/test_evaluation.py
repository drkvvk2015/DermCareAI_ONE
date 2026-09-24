import pytest

from evaluation import ABSTAIN_LABEL, classification_metrics, safety_gate, validate_prediction_payload


def test_low_confidence_abstains():
    result = safety_gate(class_name="Melanoma", confidence=0.42)
    assert result.accepted is False


def test_bad_image_abstains():
    result = safety_gate(class_name="Melanoma", confidence=0.99, image_quality_ok=False)
    assert result.accepted is False


def test_valid_payload():
    assert validate_prediction_payload(
        {
            "class_name": ABSTAIN_LABEL,
            "confidence": 0.0,
            "model_used": "quality-gate",
            "visualization": "",
        }
    ) == []


def test_invalid_confidence_is_rejected():
    with pytest.raises(ValueError):
        classification_metrics(["a"], ["a"], labels=[])
    assert "confidence_out_of_range" in validate_prediction_payload(
        {
            "class_name": "a",
            "confidence": 2,
            "model_used": "m",
            "visualization": "",
        }
    )


def test_metrics_are_bounded():
    metrics = classification_metrics(["a", "a", "b", "b"], ["a", "b", "b", "b"], ["a", "b"])
    assert metrics.count == 4
    assert 0 <= metrics.accuracy <= 1
    assert 0 <= metrics.macro_sensitivity <= 1
    assert 0 <= metrics.macro_specificity <= 1


def test_safety_gate_uses_governed_gateway_for_model_registration_and_enablement():
    unregistered = safety_gate(class_name="Melanoma", confidence=0.95, model_registered=False)
    assert unregistered.accepted is False
    assert "registered" in unregistered.reason

    disabled = safety_gate(class_name="Melanoma", confidence=0.95, model_enabled=False)
    assert disabled.accepted is False
    assert "enabled" in disabled.reason
