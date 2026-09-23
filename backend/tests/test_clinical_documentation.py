from clinical_documentation import can_finalize_encounter, validate_encounter


def test_complete_encounter_can_finalize() -> None:
    fields = {name: "documented" for name in (
        "chief_complaint", "duration", "distribution", "morphology", "assessment", "plan"
    )}
    assert can_finalize_encounter(fields)
    assert validate_encounter(fields) == ()


def test_missing_morphology_blocks_finalization() -> None:
    fields = {name: "documented" for name in (
        "chief_complaint", "duration", "distribution", "assessment", "plan"
    )}
    assert not can_finalize_encounter(fields)
    assert any(issue.field == "morphology" for issue in validate_encounter(fields))


def test_assessment_without_plan_is_flagged() -> None:
    fields = {
        "chief_complaint": "rash",
        "duration": "2 weeks",
        "distribution": "forearms",
        "morphology": "papules",
        "assessment": "documented",
        "plan": "",
    }
    issues = validate_encounter(fields)
    assert any(issue.field == "plan" for issue in issues)
