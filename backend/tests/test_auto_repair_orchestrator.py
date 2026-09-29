from pathlib import Path

from auto_repair import (
    FailureKind,
    RepairHooks,
    RepairOrchestrator,
    RepairPolicy,
    can_modify_path,
    classify_failure,
    cluster_failures,
)


FIXTURES = Path(__file__).parent / "fixtures" / "auto_repair"


def test_failure_fixture_corpus_covers_supported_stacks() -> None:
    expected = {
        "flutter.log": FailureKind.DART_TEST,
        "backend.log": FailureKind.PYTHON_TEST,
        "ci.log": FailureKind.CONFIGURATION,
        "dependency.log": FailureKind.DEPENDENCY,
        "configuration.log": FailureKind.CONFIGURATION,
        "runtime.log": FailureKind.RUNTIME,
    }
    for filename, kind in expected.items():
        assert classify_failure((FIXTURES / filename).read_text()) is kind


def test_clusters_repeat_failure_messages_across_volatile_locations() -> None:
    clusters = cluster_failures(
        [
            "pytest failed\nAssertionError: expected 1, got 2 in backend/tests/test_a.py:17",
            "pytest failed\nAssertionError: expected 3, got 4 in backend/tests/test_a.py:29",
            "npx tsc --noEmit\nTypeScript error TS2322 in src/App.tsx:10",
        ]
    )
    assert clusters[0].occurrences == 2
    assert clusters[0].kind is FailureKind.PYTHON_TEST
    assert clusters[0].fingerprint != clusters[1].fingerprint


def test_clusters_preserve_kinds_in_mixed_failure_logs() -> None:
    clusters = cluster_failures(
        [
            "pytest failed\nAssertionError: unexpected result\n"
            "CodeQL security alert: unsafe flow in backend/app.py:90"
        ]
    )
    assert {cluster.kind for cluster in clusters} == {FailureKind.PYTHON_TEST, FailureKind.SECURITY}


def test_path_policy_blocks_traversal_protected_and_non_allowlisted_paths() -> None:
    policy = RepairPolicy(allow_paths=("backend/tests/",), deny_paths=("backend/tests/fixtures/",))
    assert can_modify_path("backend/tests/test_auto_repair.py", policy)
    assert not can_modify_path("backend/tests/fixtures/log.txt", policy)
    assert not can_modify_path("backend/clinical.py", policy)
    assert not can_modify_path("../backend/tests/test_auto_repair.py", policy)
    assert not can_modify_path("/backend/tests/test_auto_repair.py", policy)
    assert not can_modify_path("docs/README.md", policy)


def _hooks(calls: list[str], *, failed_stage: str | None = None) -> RepairHooks:
    def run_checks(stage: str, commands: tuple[str, ...] | list[str]) -> bool:
        calls.append(stage)
        return stage != failed_stage

    return RepairHooks(
        reproduce=lambda _proposal: calls.append("reproduce") is None,
        create_isolated_branch=lambda _key: "copilot/repair/test",
        propose_patch=lambda _proposal: ["backend/tests/test_auto_repair.py"],
        run_checks=run_checks,
        close_repair_branch=lambda _branch: calls.append("close-branch"),
        open_draft_pr=lambda _branch, _report: calls.append("draft-pr") or "https://example.test/draft/1",
    )


def test_dry_run_has_audit_report_and_never_calls_integration_hooks() -> None:
    calls: list[str] = []
    report = RepairOrchestrator().run(
        "pytest failed: AssertionError",
        idempotency_key="workflow-42",
        hooks=_hooks(calls),
    )
    assert report.status == "dry-run"
    assert report.dry_run
    assert report.before_after_status == {"before": "failed", "after": "not-run"}
    assert report.audit_trail[0]["event"] == "detected"
    assert calls == []
    assert set(report.to_dict()) >= {
        "failure",
        "root_cause_hypothesis",
        "files_changed",
        "tests_run",
        "before_after_status",
        "confidence",
        "risk",
    }


def test_success_runs_validation_in_order_then_opens_draft_pr_once() -> None:
    calls: list[str] = []
    orchestrator = RepairOrchestrator()
    report = orchestrator.run(
        "pytest failed: AssertionError",
        idempotency_key="workflow-43",
        dry_run=False,
        hooks=_hooks(calls),
    )
    repeated = orchestrator.run(
        "pytest failed: AssertionError",
        idempotency_key="workflow-43",
        dry_run=False,
        hooks=_hooks(calls),
    )
    assert report.status == "draft-pr-opened"
    assert report.draft_pr_url == "https://example.test/draft/1"
    assert calls == [
        "reproduce",
        "targeted-tests",
        "full-regression",
        "formatting",
        "static-analysis",
        "dependency-security",
        "codeql",
        "draft-pr",
    ]
    assert repeated is report


def test_failed_validation_stops_before_draft_pr() -> None:
    calls: list[str] = []
    report = RepairOrchestrator().run(
        "pytest failed: AssertionError",
        idempotency_key="workflow-44",
        dry_run=False,
        hooks=_hooks(calls, failed_stage="full-regression"),
    )
    assert report.status == "full-regression-failed"
    assert "draft-pr" not in calls


def test_protected_path_and_exhausted_retries_are_blocked() -> None:
    calls: list[str] = []
    hooks = _hooks(calls)
    protected = RepairOrchestrator().run(
        "pytest failed: AssertionError",
        idempotency_key="workflow-45",
        dry_run=False,
        hooks=RepairHooks(
            hooks.reproduce,
            hooks.create_isolated_branch,
            lambda _proposal: ["backend/clinical.py"],
            hooks.run_checks,
            hooks.close_repair_branch,
            hooks.open_draft_pr,
        ),
    )
    exhausted = RepairOrchestrator(max_attempts=2).run(
        "pytest failed: AssertionError",
        idempotency_key="workflow-46",
        attempt=3,
        dry_run=False,
        hooks=hooks,
    )
    assert protected.status == "path-policy-rejected"
    assert exhausted.status == "retry-limit"
    assert calls.count("reproduce") == 1


def test_failed_final_attempt_closes_isolated_branch() -> None:
    calls: list[str] = []
    report = RepairOrchestrator(max_attempts=2).run(
        "pytest failed: AssertionError",
        idempotency_key="workflow-47",
        attempt=2,
        dry_run=False,
        hooks=_hooks(calls, failed_stage="targeted-tests"),
    )
    assert report.status == "targeted-tests-failed"
    assert calls[-1] == "close-branch"
    assert "draft-pr" not in calls


def test_adapter_exceptions_are_reported_and_final_branch_is_closed() -> None:
    calls: list[str] = []
    hooks = _hooks(calls)

    def fail_check(_stage: str, _commands: tuple[str, ...] | list[str]) -> bool:
        raise RuntimeError("private adapter details")

    report = RepairOrchestrator(max_attempts=2).run(
        "pytest failed: AssertionError",
        idempotency_key="workflow-49",
        attempt=2,
        dry_run=False,
        hooks=RepairHooks(
            hooks.reproduce,
            hooks.create_isolated_branch,
            hooks.propose_patch,
            fail_check,
            hooks.close_repair_branch,
            hooks.open_draft_pr,
        ),
    )
    assert report.status == "targeted-tests-failed"
    assert calls[-1] == "close-branch"
    assert any(event.get("event") == "adapter-error" for event in report.audit_trail)
    assert all("private adapter details" not in str(event) for event in report.audit_trail)


def test_security_repairs_require_review_and_are_never_started() -> None:
    calls: list[str] = []
    report = RepairOrchestrator().run(
        "CodeQL security alert",
        idempotency_key="workflow-48",
        dry_run=False,
        human_approved=True,
        hooks=_hooks(calls),
    )
    assert report.status == "human-review-required"
    assert calls == []
