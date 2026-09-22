from dermatology.analytics import cohort_summary

def test_cohort_summary_has_stable_shape():
    result = cohort_summary([
        {"diagnosis": "acne", "followup_status": "completed"},
        {"diagnosis": "eczema", "followup_status": "planned"},
    ])
    assert result["encounters"] == 2
    assert result["diagnoses"] == {"acne": 1, "eczema": 1}
    assert result["followup_completion_rate"] == 50.0
