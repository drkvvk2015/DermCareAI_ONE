from clinical import _documentation_fields
from dermatology.clinical_documentation import can_finalize_encounter


def test_encounter_documentation_mapping_supports_signoff_gate() -> None:
    encounter = {
        "complaints": {"chief_complaint": "itchy plaques", "duration": "3 weeks"},
        "examination": {"distribution": "extensor surfaces", "morphology": "well-demarcated plaques"},
        "assessment": {"summary": "clinical assessment documented"},
        "plan": {"summary": "topical treatment and follow-up"},
    }

    fields = _documentation_fields(encounter)

    assert can_finalize_encounter(fields)
    assert all(fields.values())


def test_incomplete_encounter_maps_to_missing_documentation() -> None:
    encounter = {
        "complaints": {"chief_complaint": "rash"},
        "examination": {},
        "assessment": {"summary": "assessment"},
        "plan": {},
    }

    fields = _documentation_fields(encounter)

    assert not can_finalize_encounter(fields)
    assert fields["duration"] is None
    assert fields["morphology"] is None
    assert fields["plan"] is None
