from datetime import date, datetime, timezone

import pytest

from clinical_copilot import PatientContext, build_copilot_recommendation
from clinical_evidence_registry import EvidenceRecord, EvidenceRegistry


def current_evidence() -> EvidenceRecord:
    return EvidenceRecord(
        evidence_id="guideline.test.001",
        organization="Test Specialty Society",
        title="Test Dermatology Guideline",
        tier="specialty_guideline",
        publication_date=date(2026, 1, 1),
        update_date=date(2026, 9, 1),
        version="2026.1",
        stable_url="https://example.org/guideline",
        document_id="DOC-001",
        section="4.2",
        recommendation_id="REC-4.2",
        retrieval_timestamp=datetime.now(timezone.utc),
        checksum_sha256="a" * 64,
        scope="dermatology treatment",
    )


def test_registry_rejects_superseded_evidence_for_current_recommendation():
    record = current_evidence()
    superseded = EvidenceRecord(**{**record.__dict__, "status": "superseded"})
    registry = EvidenceRegistry([superseded])
    with pytest.raises(ValueError):
        registry.require_current([superseded.evidence_id])


def test_copilot_abstains_without_governed_evidence():
    result = build_copilot_recommendation(
        context=PatientContext(pregnancy_status="not_pregnant"),
        differential=("eczema",),
        supporting_features=("itch",),
        missing_information=(),
        investigations=(),
        treatment_options=("consider topical therapy",),
        contraindication_checks=("review allergy history",),
        monitoring=("clinical response",),
        referral_or_escalation=(),
        counselling=(),
        evidence=(),
    )
    assert result.abstained is True
    assert result.abstention_reason
    assert result.to_dict()["human_authority"]["physician_final_decision"] is True
    assert result.to_dict()["human_authority"]["ai_can_sign_diagnosis"] is False
    assert result.to_dict()["human_authority"]["ai_can_prescribe"] is False


def test_copilot_abstains_on_non_current_evidence():
    record = current_evidence()
    for status in ("superseded", "conflicting", "insufficient", "unable_to_verify"):
        non_current = EvidenceRecord(**{**record.__dict__, "status": status})
        result = build_copilot_recommendation(
            context=PatientContext(pregnancy_status="not_pregnant"),
            differential=("eczema",),
            supporting_features=("itch",),
            missing_information=(),
            investigations=(),
            treatment_options=("consider topical therapy",),
            contraindication_checks=(),
            monitoring=(),
            referral_or_escalation=(),
            counselling=(),
            evidence=(non_current,),
        )
        assert result.abstained is True
        assert "current governed evidence" in (result.abstention_reason or "")


def test_copilot_abstains_on_red_flags_even_with_current_evidence():
    result = build_copilot_recommendation(
        context=PatientContext(pregnancy_status="not_pregnant", red_flags=("mucosal involvement",)),
        differential=("severe drug reaction",),
        supporting_features=("mucosal involvement",),
        missing_information=(),
        investigations=("urgent clinical assessment",),
        treatment_options=(),
        contraindication_checks=(),
        monitoring=(),
        referral_or_escalation=("urgent specialist assessment",),
        counselling=(),
        evidence=(current_evidence(),),
    )
    assert result.abstained is True
    assert "mucosal involvement" in result.safety_flags


def test_current_evidence_can_support_non_autonomous_copilot_output():
    result = build_copilot_recommendation(
        context=PatientContext(pregnancy_status="not_pregnant"),
        differential=("atopic dermatitis", "contact dermatitis"),
        supporting_features=("pruritus",),
        missing_information=("exposure history",),
        investigations=("review exposure history",),
        treatment_options=("consider guideline-concordant topical therapy",),
        contraindication_checks=("review allergy and medication history",),
        monitoring=("response and adverse effects",),
        referral_or_escalation=(),
        counselling=("skin care and safety-netting",),
        evidence=(current_evidence(),),
    )
    assert result.abstained is False
    payload = result.to_dict()
    assert payload["evidence"][0]["version"] == "2026.1"
    assert payload["human_authority"]["physician_final_decision"] is True
    assert payload["human_authority"]["ai_can_modify_signed_record"] is False
