from dermatology.examination import DermatologyExamination, as_dict, validate_examination

def test_examination_contract():
    exam = DermatologyExamination(
        primary_morphology="plaque",
        secondary_changes=("scale",),
        color="erythematous",
        distribution="extensor surfaces",
    )
    validate_examination(exam)
    assert as_dict(exam)["primary_morphology"] == "plaque"

def test_unknown_morphology_is_rejected():
    try:
        validate_examination(
            DermatologyExamination(
                primary_morphology="unknown",
                distribution="face",
            )
        )
    except ValueError:
        pass
    else:
        raise AssertionError("unknown morphology must be rejected")
