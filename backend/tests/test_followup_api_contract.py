from dermatology.followup import next_status

def test_transition_contract():
    assert next_status("planned", "confirmed") == "confirmed"

def test_cancelled_is_terminal():
    try:
        next_status("cancelled", "planned")
    except ValueError:
        pass
    else:
        raise AssertionError("cancelled follow-up must remain terminal")
