"""Guardrailed CI failure analysis for DermCareAI.

This module deliberately proposes repairs; it never mutates clinical source code,
creates commits, or deploys changes by itself. A human-reviewed PR remains the
required control boundary.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class FailureKind(StrEnum):
    PYTHON_TEST = "python-test"
    TYPESCRIPT_TEST = "typescript-test"
    LINT = "lint"
    TYPE_CHECK = "type-check"
    DEPENDENCY = "dependency"
    SECURITY = "security"
    INFRASTRUCTURE = "infrastructure"
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
)


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


def propose_repair(log_text: str) -> RepairProposal:
    kind = classify_failure(log_text)
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
    return RepairProposal(
        kind=kind,
        confidence=confidence,
        summary=f"Detected {kind.value} failure; generate a minimal reviewed patch and rerun the failing gate.",
        commands=commands[kind],
    )


def can_modify_path(path: str) -> bool:
    """Return False for clinical/AI safety-critical source paths."""
    normalized = path.lstrip("/")
    return not normalized.startswith(BLOCKED_PATH_PREFIXES)
