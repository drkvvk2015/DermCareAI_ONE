from dermatology.analytics import cohort_summary, diagnosis_counts, followup_completion_rate

def test_diagnosis_counts():
    assert diagnosis_counts(["acne","acne","eczema",""]) == {"acne":2,"eczema":1}

def test_followup_completion_rate():
    assert followup_completion_rate(["completed","planned","completed"]) == 66.67

def test_cohort_summary():
    result = cohort_summary([{"diagnosis":"acne","followup_status":"completed"}])
    assert result["encounters"] == 1
    assert result["diagnoses"] == {"acne":1}
