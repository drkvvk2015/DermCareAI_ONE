from dermatology.clinical_workflow import longitudinal_completeness


def test_longitudinal_completeness_reports_missing_nonblocking_fields():
    missing = longitudinal_completeness({"lesion_code": "L1", "body_site": "left arm"})
    assert "laterality" in missing
    assert "morphology" in missing
    assert "size_mm" in missing


def test_longitudinal_completeness_accepts_complete_record():
    record = {
        "lesion_code": "L1", "body_site": "left arm", "laterality": "left",
        "morphology": {"primary": "papule"}, "size_mm": 4,
        "duration_days": 30, "evolution": "stable", "symptoms": "itch",
        "comparison_note": "unchanged", "photo_reference": "media-1",
    }
    assert longitudinal_completeness(record) == ()
