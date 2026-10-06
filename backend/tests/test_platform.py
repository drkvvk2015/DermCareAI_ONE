from ai_governance import build_governance_card
from ai_safety import SafetyDecision
from observability import record_prediction, record_request, snapshot
from platform_contracts import AIGovernanceCard
from pydantic import ValidationError
from request_context import new_request_id
import pytest


def test_request_id_accepts_safe_correlation_id() -> None:
    assert new_request_id("clinic-2026:001") == "clinic-2026:001"


def test_request_id_rejects_unsafe_or_long_values() -> None:
    generated = new_request_id("../patient/123")
    assert generated.startswith("req_")
    assert len(new_request_id("a" * 81)) > 1


def test_ai_governance_card_is_explicitly_non_diagnostic() -> None:
    card = build_governance_card(
        model_name="test-model",
        model_provenance="test provenance",
        confidence_threshold=0.7,
        research_model=True,
    )
    validated = AIGovernanceCard(**card)
    assert validated.diagnostic_status == "not_a_diagnosis"
    assert validated.human_review_required is True
    assert validated.abstention_enabled is True
    assert validated.can_sign_diagnosis is False
    assert validated.can_prescribe is False
    assert "dosage adjustment suggestions" in validated.advisory_scope


@pytest.mark.parametrize("field", ["human_review_required", "can_sign_diagnosis", "can_prescribe"])
def test_ai_cannot_be_configured_as_decision_maker(field: str) -> None:
    card = build_governance_card(
        model_name="m", model_provenance="p", confidence_threshold=0.7, research_model=True
    )
    card[field] = not card[field]
    with pytest.raises(ValidationError):
        AIGovernanceCard(**card)


def test_safety_decision_cannot_waive_clinician_verification() -> None:
    with pytest.raises(ValueError):
        SafetyDecision(allowed=True, reasons=(), requires_clinician_verification=False)


def test_observability_contains_only_aggregate_metrics() -> None:
    record_request(200, 10.0)
    record_prediction(model="test-model", accepted=False)
    metrics = snapshot()
    assert "http_requests" in metrics
    assert metrics["ai_decisions"]["abstained"] >= 1
    assert "patient" not in str(metrics).lower()
