from dermatology.clinical_workflow import build_soap_note, get_history_template, missing_sections

def test_psoriasis_template():
    template = get_history_template("Psoriasis")
    assert "PASI" in template.scoring_tools
    assert "joint_symptoms" in template.required_sections

def test_missing_sections():
    assert missing_sections("acne", {"onset", "distribution"}) == (
        "severity", "treatment_history", "triggers"
    )

def test_soap_rejects_empty_section():
    try:
        build_soap_note(subjective="x", objective="", assessment="x", plan="x")
    except ValueError:
        pass
    else:
        raise AssertionError("empty SOAP sections must be rejected")
