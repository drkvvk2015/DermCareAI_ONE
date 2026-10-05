import os

from clinical_ai_policy import DiagnosticMode, capabilities
from dermatology.clinical_ai import ClinicalFeatures, generate_differential


def test_clinical_assist_can_be_enabled_without_diagnostic_activation(monkeypatch):
    monkeypatch.setenv("ENABLE_CLINICAL_ASSIST_AI", "true")
    monkeypatch.setenv("AI_DIAGNOSTIC_MODE", "disabled")
    monkeypatch.setenv("ENABLE_GENERATIVE_CLINICAL_ASSIST", "false")
    monkeypatch.setenv("ENABLE_MEDGEMMA", "false")

    state = capabilities()

    assert state.clinical_assist_enabled is True
    assert state.generative_assist_enabled is False
    assert state.diagnostic_mode is DiagnosticMode.DISABLED


def test_production_generative_assist_requires_model_revision(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("ENABLE_CLINICAL_ASSIST_AI", "true")
    monkeypatch.setenv("ENABLE_GENERATIVE_CLINICAL_ASSIST", "true")
    monkeypatch.setenv("ENABLE_MEDGEMMA", "true")
    monkeypatch.delenv("MEDGEMMA_REVISION", raising=False)

    assert capabilities().generative_assist_enabled is False

    monkeypatch.setenv("MEDGEMMA_REVISION", "0123456789abcdef0123456789abcdef01234567")
    assert capabilities().generative_assist_enabled is True


def test_diagnostic_mode_never_changes_assistive_disclaimer():
    result = generate_differential(
        ClinicalFeatures(
            primary_morphology="plaque",
            secondary_changes=("scale",),
            distribution="extensor surfaces",
            pruritus=True,
        )
    )

    assert result.disclaimer
    assert "not a diagnosis" in result.disclaimer.lower()
    assert result.abstained is False


def test_urgent_patterns_force_abstention():
    result = generate_differential(
        ClinicalFeatures(
            primary_morphology="patch",
            systemic_red_flags=("mucosal erosions", "skin pain", "rapidly progressive"),
        )
    )

    assert result.abstained is True
    assert result.safety.urgent_review is True
