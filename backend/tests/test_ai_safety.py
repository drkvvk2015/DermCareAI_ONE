from ai_safety import evaluate_ai_request, sanitize_model_output


def test_safety_gateway_blocks_missing_consent_and_registration():
    decision = evaluate_ai_request(
        consented=False,
        image_present=True,
        model_registered=False,
        model_enabled=True,
    )
    assert decision.allowed is False
    assert "clinical_image_consent_required" in decision.reasons
    assert "model_not_registered" in decision.reasons


def test_safety_gateway_abstains_for_ood_or_low_confidence():
    decision = evaluate_ai_request(
        consented=True,
        image_present=True,
        model_registered=True,
        model_enabled=True,
        out_of_distribution=True,
        confidence=0.42,
        min_confidence=0.8,
    )
    assert decision.allowed is False
    assert "out_of_distribution" in decision.reasons
    assert "below_minimum_confidence" in decision.reasons


def test_safety_gateway_allows_governed_preliminary_request():
    decision = evaluate_ai_request(
        consented=True,
        image_present=True,
        model_registered=True,
        model_enabled=True,
        confidence=0.9,
        min_confidence=0.8,
    )
    assert decision.allowed is True
    assert decision.requires_clinician_verification is True


def test_output_is_bounded_and_normalized():
    assert sanitize_model_output("  visible  erythema \\n") == "visible erythema"
    assert len(sanitize_model_output("x" * 20000)) == 12000
