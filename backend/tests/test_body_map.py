from dermatology.body_map import LesionObservation, compare_size, validate_observation

def test_valid_observation():
    validate_observation(LesionObservation("L-01","face","left",4.0,"papule","2026-09-22"))

def test_invalid_body_site_is_rejected():
    try:
        validate_observation(LesionObservation("L-01","unknown",None,4.0,"papule","2026-09-22"))
    except ValueError:
        pass
    else:
        raise AssertionError("unsupported body site must be rejected")

def test_size_trend():
    assert compare_size(5.0, 5.0) == "stable"
