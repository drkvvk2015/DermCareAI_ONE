from auto_repair import FailureKind, can_modify_path, classify_failure, propose_repair


def test_classifies_python_failures() -> None:
    assert classify_failure("pytest failed: AssertionError") is FailureKind.PYTHON_TEST


def test_classifies_security_failures_before_generic_test_signals() -> None:
    assert classify_failure("CodeQL found a security alert during pytest") is FailureKind.SECURITY


def test_proposal_is_not_self_authorizing() -> None:
    proposal = propose_repair("ruff check failed")
    assert proposal.kind is FailureKind.LINT
    assert proposal.safe_to_automate is False
    assert proposal.commands


def test_clinical_paths_are_human_review_only() -> None:
    assert can_modify_path("backend/dermatology/clinical_ai.py") is False
    assert can_modify_path("backend/clinical.py") is False
    assert can_modify_path("backend/tests/test_health.py") is True
