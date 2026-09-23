from auto_repair import FailureKind, propose_repair


def test_auto_repair_proposal_is_conservative_for_python_failures():
    proposal = propose_repair("pytest failed with AssertionError in backend/tests/test_clinical.py")
    assert proposal.kind is FailureKind.PYTHON_TEST
    assert proposal.confidence > 0.8
    assert proposal.safe_to_automate is False


def test_auto_repair_keeps_security_failures_non_automatable():
    proposal = propose_repair("CodeQL security alert in backend/dermatology/vision_analysis.py")
    assert proposal.kind is FailureKind.SECURITY
    assert proposal.safe_to_automate is False
