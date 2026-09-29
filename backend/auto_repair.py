"""Guardrailed CI failure analysis and repair-proposal controls.

The module is intentionally proposal-only: it can classify failures, gate paths,
track bounded/idempotent repair attempts, and emit machine-readable evidence.
It never mutates source code, pushes branches, merges PRs, or deploys software.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import hashlib
import json
import time
from typing import Iterable


class FailureKind(StrEnum):
    PYTHON_TEST = "python-test"
    TYPESCRIPT_TEST = "typescript-test"
    LINT = "lint"
    TYPE_CHECK = "type-check"
    DEPENDENCY = "dependency"
    SECURITY = "security"
    INFRASTRUCTURE = "infrastructure"
    UNKNOWN = "unknown"


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass(frozen=True)
class RepairProposal:
    kind: FailureKind
    confidence: float
    summary: str
    commands: tuple[str, ...]
    safe_to_automate: bool = False
    risk: RiskLevel = RiskLevel.HIGH
    path_gate_passed: bool = False
    requires_human_review: bool = True


BLOCKED_PATH_PREFIXES = (
    "backend/dermatology/",
    "backend/clinical.py",
    "backend/evaluation.py",
    "backend/model_registry.py",
    "backend/ai_governance.py",
    "backend/ai_safety.py",
    "backend/auth.py",
    "backend/security/",
    "backend/audit.py",
    "backend/pharmacy/",
    "backend/billing/",
)

# Repair operations are deliberately bounded to avoid recursive/automated loops.
DEFAULT_MAX_ATTEMPTS = 2


@dataclass
class RepairGuard:
    """Bound repair attempts and prevent duplicate execution via idempotency keys."""

    max_attempts: int = DEFAULT_MAX_ATTEMPTS

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        self._attempts: dict[str, int] = {}
        self._seen_attempts: set[tuple[str, int]] = set()

    def allow(self, idempotency_key: str, attempt: int | None = None) -> bool:
        key = idempotency_key.strip()
        if not key:
            return False
        next_attempt = self._attempts.get(key, 0) + 1 if attempt is None else attempt
        if next_attempt < 1 or next_attempt > self.max_attempts:
            return False
        marker = (key, next_attempt)
        if marker in self._seen_attempts:
            return False
        self._seen_attempts.add(marker)
        self._attempts[key] = max(self._attempts.get(key, 0), next_attempt)
        return True

    def attempts(self, idempotency_key: str) -> int:
        return self._attempts.get(idempotency_key.strip(), 0)


def failure_signature(log_text: str) -> str:
    """Create a stable, non-sensitive fingerprint for a failure payload."""
    return hashlib.sha256(log_text.encode("utf-8", errors="replace")).hexdigest()


def classify_failure(log_text: str) -> FailureKind:
    text = log_text.lower()
    if "codeql" in text or "security" in text or "sarif" in text:
        return FailureKind.SECURITY
    if "npm audit" in text or "pip-audit" in text or "dependency" in text:
        return FailureKind.DEPENDENCY
    if "typescript" in text or "tsc " in text or "jest" in text:
        return FailureKind.TYPESCRIPT_TEST
    if "pytest" in text or "assertionerror" in text or "traceback" in text:
        return FailureKind.PYTHON_TEST
    if "ruff" in text or "eslint" in text or "prettier" in text:
        return FailureKind.LINT
    if "mypy" in text or "typecheck" in text:
        return FailureKind.TYPE_CHECK
    if "docker" in text or "postgres" in text or "firestore" in text:
        return FailureKind.INFRASTRUCTURE
    return FailureKind.UNKNOWN


def assess_risk(kind: FailureKind, paths: Iterable[str] = ()) -> RiskLevel:
    normalized = tuple(path.lstrip("/") for path in paths)
    if any(not can_modify_path(path) for path in normalized):
        return RiskLevel.CRITICAL
    if kind is FailureKind.SECURITY:
        return RiskLevel.CRITICAL
    if kind in (FailureKind.DEPENDENCY, FailureKind.INFRASTRUCTURE):
        return RiskLevel.HIGH
    if kind in (FailureKind.TYPE_CHECK, FailureKind.TYPESCRIPT_TEST, FailureKind.PYTHON_TEST):
        return RiskLevel.MEDIUM
    return RiskLevel.LOW


def can_modify_path(path: str) -> bool:
    """Return False for clinical, patient-safety, security or protected source paths."""
    normalized = path.lstrip("/")
    return not normalized.startswith(BLOCKED_PATH_PREFIXES)


def validate_paths(paths: Iterable[str]) -> tuple[bool, tuple[str, ...]]:
    normalized = tuple(path.lstrip("/") for path in paths if path.strip())
    blocked = tuple(path for path in normalized if not can_modify_path(path))
    return not blocked, blocked


def propose_repair(log_text: str, *, paths: Iterable[str] = ()) -> RepairProposal:
    kind = classify_failure(log_text)
    path_gate, blocked = validate_paths(paths)
    commands: dict[FailureKind, tuple[str, ...]] = {
        FailureKind.PYTHON_TEST: ("pytest -q",),
        FailureKind.TYPESCRIPT_TEST: ("npm test -- --runInBand",),
        FailureKind.LINT: ("ruff check backend", "npm run lint"),
        FailureKind.TYPE_CHECK: ("mypy backend", "npx tsc --noEmit"),
        FailureKind.DEPENDENCY: ("pip-audit", "npm audit --omit=dev"),
        FailureKind.SECURITY: ("codeql database analyze",),
        FailureKind.INFRASTRUCTURE: ("docker compose config",),
        FailureKind.UNKNOWN: (),
    }
    confidence = 0.85 if kind is not FailureKind.UNKNOWN else 0.10
    risk = assess_risk(kind, paths)
    requires_human_review = True
    summary = (
        f"Detected {kind.value} failure; generate a minimal reviewed patch and rerun the failing gate."
    )
    if blocked:
        summary += " Protected paths detected; automated modification is prohibited."
    return RepairProposal(
        kind=kind,
        confidence=confidence,
        summary=summary,
        commands=commands[kind],
        safe_to_automate=False,
        risk=risk,
        path_gate_passed=path_gate,
        requires_human_review=requires_human_review,
    )


def build_repair_report(
    log_text: str,
    *,
    paths: Iterable[str] = (),
    dry_run: bool = True,
    attempt: int = 1,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    idempotency_key: str | None = None,
) -> dict[str, object]:
    """Return machine-readable evidence for a proposed repair."""
    normalized_paths = tuple(path.lstrip("/") for path in paths if path.strip())
    proposal = propose_repair(log_text, paths=normalized_paths)
    signature = failure_signature(log_text)
    key = (idempotency_key or signature).strip()
    bounded = 1 <= attempt <= max_attempts
    path_gate, blocked = validate_paths(normalized_paths)

    status = "eligible-for-reviewed-proposal"
    if not bounded:
        status = "blocked-attempt-limit"
    elif not path_gate:
        status = "blocked-protected-path"
    elif not dry_run:
        # The module has no mutating implementation by design.
        status = "blocked-no-mutation-mode"

    return {
        "schema_version": "1.0",
        "failure_signature": signature,
        "idempotency_key": key,
        "generated_at_epoch": int(time.time()),
        "dry_run": dry_run,
        "attempt": attempt,
        "max_attempts": max_attempts,
        "attempt_within_bound": bounded,
        "failure_kind": proposal.kind.value,
        "confidence": proposal.confidence,
        "risk": proposal.risk.value,
        "path_gate_passed": path_gate,
        "blocked_paths": list(blocked),
        "commands": list(proposal.commands),
        "safe_to_automate": proposal.safe_to_automate,
        "requires_human_review": proposal.requires_human_review,
        "status": status,
        "summary": proposal.summary,
        "next_action": (
            "Create a minimal isolated repair PR and require human review before merge."
            if status == "eligible-for-reviewed-proposal"
            else "Stop and require explicit human intervention."
        ),
    }


def report_json(report: dict[str, object]) -> str:
    return json.dumps(report, indent=2, sort_keys=True) + "\n"
