from dermatology.clinical_ai import ClinicalFeatures, generate_differential


def test_psoriasis_pattern_is_explainable():
    result = generate_differential(
        ClinicalFeatures(
            primary_morphology="plaque",
            secondary_changes=("scale",),
            color="silvery",
            distribution="extensor surfaces",
            pruritus=True,
        )
    )

    assert result.abstained is False
    assert result.candidates
    assert result.candidates[0].label == "Possible psoriasis"
    assert any(item.feature == "extensor distribution" for item in result.candidates[0].evidence)


def test_emergency_pattern_abstains_and_escalates():
    result = generate_differential(
        ClinicalFeatures(
            primary_morphology="patch",
            distribution="trunk",
            systemic_red_flags=("mucosal erosions", "skin pain", "rapidly progressive"),
        )
    )

    assert result.abstained is True
    assert result.safety.urgent_review is True
    assert not result.candidates
    assert "mucosal erosions" in result.safety.matched_flags


def test_weak_evidence_abstains():
    result = generate_differential(
        ClinicalFeatures(
            primary_morphology="papule",
            distribution="arm",
        )
    )

    assert result.abstained is True
    assert not result.candidates


def test_tinea_pattern_is_ranked():
    result = generate_differential(
        ClinicalFeatures(
            primary_morphology="plaque",
            secondary_changes=("scale",),
            border="annular",
            distribution="trunk",
            pruritus=True,
        )
    )

    assert result.candidates
    assert result.candidates[0].label == "Possible tinea corporis"
