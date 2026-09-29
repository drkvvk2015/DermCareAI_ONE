from auto_repair import (
    FailureKind,
    RiskLevel,
    RepairGuard,
    build_repair_report,
    can_modify_path,
    classify_failure,
    failure_signature,
    propose_repair,
)


def test_classifies_python_failures() -> None:
    assert classify_failure("pytest failed: AssertionError") is FailureKind.PYTHON_TEST


def test_classifies_security_failures_before_generic_test_signals() -> None:
    assert classify_failure("CodeQL found a security alert during pytest") is FailureKind.SECURITY


def test_proposal_is_not_self_authorizing() -> None:
    proposal = propose_repair("ruff check failed")
    assert proposal.kind is FailureKind.LINT
    assert proposal.safe_to_automate is False
    assert proposal.requires_human_review is True
    assert proposal.commands


def test_clinical_paths_are_human_review_only() -> None:
    assert can_modify_path("backend/dermatology/clinical_ai.py") is False
    assert can_modify_path("backend/clinical.py") is False
    assert can_modify_path("backend/tests/test_health.py") is True


def test_protected_paths_raise_critical_risk() -> None:
    proposal = propose_repair("pytest failed", paths=["backend/ai_safety.py"])
    assert proposal.path_gate_passed is False
    assert proposal.risk is RiskLevel.CRITICAL


def test_failure_signature_is_stable() -> None:
    assert failure_signature("same failure") == failure_signature("same failure")


def test_repair_guard_bounds_and_deduplicates_attempts() -> None:
    guard = RepairGuard(max_attempts=2)
    assert guard.allow("k1", attempt=1) is True
    assert guard.allow("k1", attempt=1) is False
    assert guard.allow("k1", attempt=2) is True
    assert guard.allow("k1", attempt=3) is False
    assert guard.attempts("k1") == 2
    assert guard.allow("k2") is True
    assert guard.attempts("k2") == 1


def test_machine_readable_report_blocks_apply_mode() -> None:
    report = build_repair_report(
        "ruff check failed",
        paths=["backend/tests/test_health.py"],
        dry_run=False,
    )
    assert report["status"] == "blocked-no-mutation-mode"
    assert report["requires_human_review"] is True


def test_machine_readable_report_blocks_protected_paths() -> None:
    report = build_repair_report(
        "pytest failed",
        paths=["backend/dermatology/clinical_ai.py"],
    )
    assert report["status"] == "blocked-protected-path"
    assert report["risk"] == "critical"
