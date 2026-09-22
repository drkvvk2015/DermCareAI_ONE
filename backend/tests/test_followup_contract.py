from dermatology.followup import FollowUpPlan, next_status, validate_followup

def test_followup_defaults_to_planned():
    validate_followup(FollowUpPlan("ENC-1","PAT-1","2026-09-30T09:00:00+00:00","Review response"))

def test_completed_is_terminal():
    try:
        next_status("completed","planned")
    except ValueError:
        pass
    else:
        raise AssertionError("completed follow-up must be terminal")
