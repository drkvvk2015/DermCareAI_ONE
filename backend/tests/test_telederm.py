from dermatology.telederm import TeledermStatus, TeledermSession


def test_telederm_requires_consent_before_clinical_states() -> None:
    session = TeledermSession.create("patient-1", "doctor-1")
    try:
        session.transition(TeledermStatus.SCHEDULED)
    except ValueError as exc:
        assert "consent" in str(exc).lower()
    else:
        raise AssertionError("scheduled session without consent must fail")


def test_telederm_consent_then_schedule() -> None:
    session = TeledermSession.create("patient-1", "doctor-1")
    session = session.consent("consent-123")
    session = session.transition(TeledermStatus.SCHEDULED)
    assert session.status is TeledermStatus.SCHEDULED
    assert session.consent_record_id == "consent-123"


def test_telederm_terminal_state_cannot_reopen() -> None:
    session = TeledermSession.create("patient-1", "doctor-1").transition(TeledermStatus.CANCELLED)
    try:
        session.transition(TeledermStatus.ACTIVE)
    except ValueError:
        pass
    else:
        raise AssertionError("cancelled session must remain terminal")
