"""Guardrailed CI failure analysis for DermCareAI.

This module deliberately proposes repairs; it never mutates clinical source code,
creates commits, or deploys changes by itself. A human-reviewed PR remains the
required control boundary.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from enum import StrEnum
from pathlib import PurePosixPath
from typing import Callable, Sequence, TypeVar

T = TypeVar("T")


class FailureKind(StrEnum):
    BUILD = "build"
    CI = "ci"
    PYTHON_TEST = "python-test"
    TYPESCRIPT_TEST = "typescript-test"
    DART_TEST = "dart-test"
    LINT = "lint"
    TYPE_CHECK = "type-check"
    DEPENDENCY = "dependency"
    SECURITY = "security"
    CONFIGURATION = "configuration"
    INFRASTRUCTURE = "infrastructure"
    RUNTIME = "runtime"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class RepairProposal:
    kind: FailureKind
    confidence: float
    summary: str
    commands: tuple[str, ...]
    safe_to_automate: bool = False


BLOCKED_PATH_PREFIXES = (
    "backend/dermatology/",
    "backend/clinical.py",
    "backend/evaluation.py",
    "backend/model_registry.py",
    "backend/ai_governance.py",
    "backend/ai_safety.py",
    "backend/auth.py",
    "backend/audit.py",
    "backend/prescriptions.py",
    "backend/prescription_",
    "backend/consent",
)


def classify_failure(log_text: str) -> FailureKind:
    text = log_text.lower()
    if "codeql" in text or "security" in text or "sarif" in text:
        return FailureKind.SECURITY
    if "npm audit" in text or "pip-audit" in text or "dependency" in text or "npm err! code e" in text:
        return FailureKind.DEPENDENCY
    if any(token in text for token in ("build failed", "failed to compile", "compilation error", "flutter build")):
        return FailureKind.BUILD
    if any(token in text for token in ("flutter test", "dart test", "pub get", "dart analyze")):
        return FailureKind.DART_TEST
    if "typescript" in text or "tsc " in text or "jest" in text:
        return FailureKind.TYPESCRIPT_TEST
    if "pytest" in text or "assertionerror" in text or "traceback" in text:
        return FailureKind.PYTHON_TEST
    if "ruff" in text or "eslint" in text or "prettier" in text:
        return FailureKind.LINT
    if "mypy" in text or "typecheck" in text:
        return FailureKind.TYPE_CHECK
    if any(token in text for token in ("yaml", "configuration", "invalid config", "jsondecodeerror")):
        return FailureKind.CONFIGURATION
    if any(token in text for token in ("github actions", "workflow run failed", "process completed with exit code")):
        return FailureKind.CI
    if "docker" in text or "postgres" in text or "firestore" in text:
        return FailureKind.INFRASTRUCTURE
    if any(token in text for token in ("uncaught", "segmentation fault", "runtimeerror", "unhandled exception")):
        return FailureKind.RUNTIME
    return FailureKind.UNKNOWN


def propose_repair(log_text: str) -> RepairProposal:
    kind = classify_failure(log_text)
    commands: dict[FailureKind, tuple[str, ...]] = {
        FailureKind.BUILD: ("python -m compileall -q backend", "npx tsc --noEmit", "npx expo export --platform web"),
        FailureKind.CI: (),
        FailureKind.PYTHON_TEST: ("pytest -q",),
        FailureKind.TYPESCRIPT_TEST: ("npm test -- --runInBand",),
        FailureKind.DART_TEST: ("flutter test", "dart analyze"),
        FailureKind.LINT: ("ruff check backend", "npm run lint"),
        FailureKind.TYPE_CHECK: ("mypy backend", "npx tsc --noEmit"),
        FailureKind.DEPENDENCY: ("pip-audit", "npm audit --omit=dev"),
        FailureKind.SECURITY: ("codeql database analyze",),
        FailureKind.CONFIGURATION: ("python -m compileall -q backend",),
        FailureKind.INFRASTRUCTURE: ("docker compose config",),
        FailureKind.RUNTIME: (),
        FailureKind.UNKNOWN: (),
    }
    confidence = {
        FailureKind.UNKNOWN: 0.10,
        FailureKind.RUNTIME: 0.55,
        FailureKind.SECURITY: 0.60,
        FailureKind.CONFIGURATION: 0.70,
    }.get(kind, 0.85)
    return RepairProposal(
        kind=kind,
        confidence=confidence,
        summary=f"Detected {kind.value} failure; generate a minimal reviewed patch and rerun the failing gate.",
        commands=commands[kind],
    )


def _normalized_repo_path(path: str) -> str | None:
    normalized = path.replace("\\", "/")
    candidate = PurePosixPath(normalized)
    if candidate.is_absolute() or not normalized or ".." in candidate.parts:
        return None
    return str(candidate)


@dataclass(frozen=True)
class RepairPolicy:
    allow_paths: tuple[str, ...] = ()
    deny_paths: tuple[str, ...] = ()
    protected_paths: tuple[str, ...] = BLOCKED_PATH_PREFIXES


def _matches_path(path: str, prefixes: Sequence[str]) -> bool:
    return any(path == prefix.rstrip("/") or path.startswith(prefix.rstrip("/") + "/") for prefix in prefixes)


def can_modify_path(path: str, policy: RepairPolicy | None = None) -> bool:
    """Return whether a repository-relative path passes configured safety gates."""
    normalized = _normalized_repo_path(path)
    if normalized is None:
        return False
    policy = policy or RepairPolicy()
    protected_paths = (*BLOCKED_PATH_PREFIXES, *policy.protected_paths)
    if _matches_path(normalized, protected_paths) or _matches_path(normalized, policy.deny_paths):
        return False
    return not policy.allow_paths or _matches_path(normalized, policy.allow_paths)


_ANSI_ESCAPE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
_TIMESTAMP = re.compile(r"\b\d{4}-\d{2}-\d{2}[T ][0-9:.+-Z]+\b")
_LOCATION = re.compile(r"(?P<path>(?:[\w./-]+)\.(?:py|ts|tsx|js|jsx|dart|yml|yaml|json)):\d+(?::\d+)?")
_UUID = re.compile(r"\b[0-9a-f]{8}-[0-9a-f-]{27,}\b", re.IGNORECASE)
_NUMBER = re.compile(r"\b\d+\b")
_FAILURE_LINE = re.compile(
    r"(error|failed|failure|exception|assert|cannot|not found|invalid|alert|vulnerability|fatal)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class FailureCluster:
    fingerprint: str
    kind: FailureKind
    occurrences: int
    example: str
    root_cause_hypothesis: str


def _failure_signatures(log_text: str) -> tuple[tuple[FailureKind, str], ...]:
    clean = _ANSI_ESCAPE.sub("", log_text)
    lines = [line.strip() for line in clean.splitlines() if line.strip()]
    candidates = [(index, line) for index, line in enumerate(lines) if _FAILURE_LINE.search(line)]
    if not candidates and lines:
        candidates = [(len(lines) - 1, lines[-1])]
    signatures = []
    for index, line in candidates:
        kind = classify_failure("\n".join(lines[max(0, index - 4):index + 1]))
        line = _TIMESTAMP.sub("<timestamp>", line)
        line = _LOCATION.sub(lambda match: match.group("path"), line)
        line = _UUID.sub("<id>", line)
        line = _NUMBER.sub("<n>", line)
        signatures.append((kind, " ".join(line.lower().split())[:300]))
    return tuple(signatures) or ((FailureKind.UNKNOWN, "empty failure log"),)


def _root_cause_hypothesis(kind: FailureKind) -> str:
    return {
        FailureKind.BUILD: "A compilation, application build, or packaging failure is likely; reproduce the failing build command first.",
        FailureKind.CI: "A workflow/job failure is likely; inspect the failed step and its original logs before editing.",
        FailureKind.PYTHON_TEST: "A backend regression or unmet test assumption is likely; reproduce the failing test before editing.",
        FailureKind.TYPESCRIPT_TEST: "A mobile TypeScript/Jest regression or incompatible API/type contract is likely.",
        FailureKind.DART_TEST: "A Flutter/Dart test, analyzer, or package-resolution regression is likely.",
        FailureKind.LINT: "A formatting or static-style violation is likely; avoid behavior changes.",
        FailureKind.TYPE_CHECK: "A static type-contract mismatch is likely.",
        FailureKind.DEPENDENCY: "A dependency resolution, compatibility, or advisory issue is likely.",
        FailureKind.SECURITY: "A security finding needs specialist triage and mandatory human review.",
        FailureKind.CONFIGURATION: "A CI or application configuration syntax/value is likely invalid.",
        FailureKind.INFRASTRUCTURE: "A service, container, database, or infrastructure dependency may be unavailable or misconfigured.",
        FailureKind.RUNTIME: "A runtime exception needs reproduction with its original environment and inputs.",
        FailureKind.UNKNOWN: "Failure evidence is insufficient to identify a reliable root cause.",
    }[kind]


def cluster_failures(logs: Sequence[str]) -> tuple[FailureCluster, ...]:
    """Group repeated log evidence using normalized failure-line fingerprints."""
    grouped: dict[tuple[FailureKind, str], list[str]] = {}
    for log_text in logs:
        for failure in _failure_signatures(log_text):
            grouped.setdefault(failure, []).append(log_text)
    clusters = []
    for (kind, signature), examples in sorted(
        grouped.items(), key=lambda item: (-len(item[1]), item[0][0].value, item[0][1])
    ):
        clusters.append(
            FailureCluster(
                fingerprint=hashlib.sha256(f"{kind.value}:{signature}".encode("utf-8")).hexdigest(),
                kind=kind,
                occurrences=len(examples),
                example=examples[0][:1000],
                root_cause_hypothesis=_root_cause_hypothesis(kind),
            )
        )
    return tuple(clusters)


def risk_score(kind: FailureKind, files_changed: Sequence[str] = ()) -> float:
    """Return a bounded risk estimate; protected paths are never repairable."""
    base = {
        FailureKind.BUILD: 0.50,
        FailureKind.CI: 0.45,
        FailureKind.SECURITY: 0.95,
        FailureKind.RUNTIME: 0.75,
        FailureKind.DEPENDENCY: 0.65,
        FailureKind.CONFIGURATION: 0.60,
        FailureKind.INFRASTRUCTURE: 0.55,
        FailureKind.UNKNOWN: 0.80,
    }.get(kind, 0.35)
    if any(not can_modify_path(path) for path in files_changed):
        return 1.0
    if any(path.startswith(("backend/", "dermcareai/")) for path in files_changed):
        base += 0.10
    return min(1.0, base)


VALIDATION_STAGES = (
    "targeted-tests",
    "full-regression",
    "formatting",
    "static-analysis",
    "dependency-security",
    "codeql",
)

REPAIR_BRANCH_PREFIX = "copilot/repair/"


@dataclass
class RepairHooks:
    """Environment-specific operations; never runs shell commands implicitly."""

    reproduce: Callable[[RepairProposal], bool]
    create_isolated_branch: Callable[[str], str | None]
    propose_patch: Callable[[RepairProposal], Sequence[str]]
    run_checks: Callable[[str, Sequence[str]], bool]
    close_repair_branch: Callable[[str], None]
    open_draft_pr: Callable[[str, dict[str, object]], str | None]


@dataclass
class RepairReport:
    failure: str
    root_cause_hypothesis: str
    files_changed: list[str]
    tests_run: list[str]
    before_after_status: dict[str, str]
    confidence: float
    risk: float
    status: str
    idempotency_key: str
    dry_run: bool
    attempt: int
    draft_pr_url: str | None = None
    audit_trail: list[dict[str, object]] | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "failure": self.failure,
            "root_cause_hypothesis": self.root_cause_hypothesis,
            "files_changed": self.files_changed,
            "tests_run": self.tests_run,
            "before_after_status": self.before_after_status,
            "confidence": self.confidence,
            "risk": self.risk,
            "status": self.status,
            "idempotency_key": self.idempotency_key,
            "dry_run": self.dry_run,
            "attempt": self.attempt,
            "draft_pr_url": self.draft_pr_url,
            "audit_trail": self.audit_trail or [],
        }


class RepairOrchestrator:
    """Run a bounded repair lifecycle through explicit, injected integration hooks."""

    def __init__(self, policy: RepairPolicy | None = None, max_attempts: int = 2):
        if max_attempts < 1:
            raise ValueError("max_attempts must be positive")
        self.policy = policy or RepairPolicy()
        self.max_attempts = max_attempts
        self._reports: dict[tuple[str, int], RepairReport] = {}

    def run(
        self,
        log_text: str,
        *,
        idempotency_key: str,
        attempt: int = 1,
        dry_run: bool = True,
        human_approved: bool = False,
        hooks: RepairHooks | None = None,
    ) -> RepairReport:
        if not idempotency_key.strip():
            raise ValueError("idempotency_key must not be empty")
        cache_key = (idempotency_key, attempt)
        if cache_key in self._reports:
            return self._reports[cache_key]
        proposal = propose_repair(log_text)
        clusters = cluster_failures([log_text])
        repeated_evidence = max((cluster.occurrences for cluster in clusters), default=1)
        report = RepairReport(
            failure=proposal.summary,
            root_cause_hypothesis=_root_cause_hypothesis(proposal.kind),
            files_changed=[],
            tests_run=[],
            before_after_status={"before": "failed", "after": "not-run"},
            confidence=min(0.95, proposal.confidence + min(0.10, (repeated_evidence - 1) * 0.05)),
            risk=risk_score(proposal.kind),
            status="planned",
            idempotency_key=idempotency_key,
            dry_run=dry_run,
            attempt=attempt,
            audit_trail=[],
        )
        assert report.audit_trail is not None

        def record(event: str, **details: object) -> None:
            report.audit_trail.append({"event": event, **details})

        def invoke(event: str, operation: Callable[[], T], default: T) -> T:
            try:
                return operation()
            except Exception as exc:
                record("adapter-error", stage=event, error=type(exc).__name__)
                return default

        def close_branch(branch: str, reason: str) -> None:
            invoke("close-repair-branch", lambda: hooks.close_repair_branch(branch), None)
            record("repair-branch-closed", reason=reason)

        record("detected", kind=proposal.kind.value)
        if attempt < 1 or attempt > self.max_attempts:
            report.status = "retry-limit"
            report.before_after_status["after"] = "blocked"
            record("retry-limit", max_attempts=self.max_attempts)
        elif dry_run:
            report.status = "dry-run"
            record("dry-run", actions_not_executed=["reproduce", "patch", "branch", "validation", "draft-pr"])
        elif hooks is None:
            report.status = "blocked-no-adapter"
            report.before_after_status["after"] = "blocked"
            record("blocked", reason="repair hooks are required")
        elif proposal.kind in (FailureKind.SECURITY, FailureKind.UNKNOWN):
            report.status = "human-review-required"
            report.before_after_status["after"] = "blocked"
            record("risk-gate", reason="security or unknown failures cannot be automated")
        elif report.risk >= 0.60 and not human_approved:
            report.status = "human-review-required"
            report.before_after_status["after"] = "blocked"
            record("risk-gate", reason="human approval is required for elevated-risk repairs")
        elif not invoke("reproduce", lambda: hooks.reproduce(proposal), False):
            report.status = "reproduction-failed"
            report.before_after_status["after"] = "reproduction-failed"
            record("reproduce", passed=False)
        else:
            record("reproduce", passed=True)
            branch = invoke(
                "isolated-branch",
                lambda: hooks.create_isolated_branch(idempotency_key),
                None,
            )
            if not branch or not branch.startswith(REPAIR_BRANCH_PREFIX):
                report.status = "branch-creation-failed"
                report.before_after_status["after"] = "branch-creation-failed"
                record("isolated-branch", created=False, branch=branch)
            else:
                record("isolated-branch", created=True, branch=branch)
                paths = invoke(
                    "propose-patch",
                    lambda: list(dict.fromkeys(hooks.propose_patch(proposal))),
                    [],
                )
                report.files_changed = paths
                rejected = [path for path in paths if not can_modify_path(path, self.policy)]
                if not paths or rejected:
                    report.status = "path-policy-rejected" if rejected else "empty-patch"
                    report.before_after_status["after"] = "blocked"
                    record("path-policy", rejected_paths=rejected)
                    close_branch(branch, "patch was empty or failed the path policy")
                else:
                    report.risk = risk_score(proposal.kind, paths)
                    if report.risk >= 0.60 and not human_approved:
                        report.status = "human-review-required"
                        report.before_after_status["after"] = "blocked"
                        record("risk-gate", reason="changed paths elevate repair risk")
                        close_branch(branch, "human approval was not supplied")
                    else:
                        passed = True
                        for stage in VALIDATION_STAGES:
                            commands = proposal.commands if stage == "targeted-tests" else ()
                            report.tests_run.append(stage)
                            report.tests_run.extend(commands)
                            stage_passed = invoke(
                                f"validation:{stage}",
                                lambda: hooks.run_checks(stage, commands),
                                False,
                            )
                            record("validation", stage=stage, passed=stage_passed, commands=list(commands))
                            if not stage_passed:
                                passed = False
                                report.status = f"{stage}-failed"
                                report.before_after_status["after"] = "validation-failed"
                                if attempt == self.max_attempts:
                                    close_branch(branch, "validation failed on final allowed attempt")
                                break
                        if passed:
                            report.before_after_status["after"] = "passed"
                            report.status = "draft-pr-pending"
                            url = invoke(
                                "draft-pr",
                                lambda: hooks.open_draft_pr(branch, report.to_dict()),
                                None,
                            )
                            report.draft_pr_url = url
                            report.status = "draft-pr-opened" if url else "draft-pr-failed"
                            record("draft-pr", opened=bool(url), url=url)

        self._reports[cache_key] = report
        return report
