from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ReadinessFinding:
    code: str
    severity: str
    message: str


def evaluate_readiness(*, app_env: str, database_url: str, cors_origins: str, app_version: str) -> list[ReadinessFinding]:
    findings: list[ReadinessFinding] = []
    if app_env.lower() == "production" and not database_url.lower().startswith(("postgresql://", "postgresql+")):
        findings.append(ReadinessFinding("DB-001", "block", "Production requires PostgreSQL"))
    if app_env.lower() == "production" and cors_origins.strip() in {"", "*"}:
        findings.append(ReadinessFinding("WEB-001", "block", "Production CORS origins must be explicit"))
    if not app_version.strip():
        findings.append(ReadinessFinding("REL-001", "block", "APP_VERSION must be immutable and non-empty"))
    return findings
