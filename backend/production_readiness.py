from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ReadinessFinding:
    code: str
    severity: str
    message: str


def evaluate_readiness(
    *,
    app_env: str,
    database_url: str,
    cors_origins: str,
    app_version: str,
    commerce_database_url: str | None = None,
    firebase_auth_required: bool = True,
) -> list[ReadinessFinding]:
    """Validate deployment contracts without opening a production connection.

    Runtime stores still fail closed on SQLite in production. This helper is the
    explicit preflight contract used by the health/readiness endpoint and CI.
    """
    findings: list[ReadinessFinding] = []
    production = app_env.lower() == "production"

    if production and not database_url.strip().lower().startswith(("postgresql://", "postgresql+")):
        findings.append(ReadinessFinding("DB-001", "block", "Production requires PostgreSQL for the clinical store"))
    if production and commerce_database_url is not None and not commerce_database_url.strip().lower().startswith(("postgresql://", "postgresql+")):
        findings.append(ReadinessFinding("DB-002", "block", "Production requires PostgreSQL for the commerce store"))
    if production and cors_origins.strip() in {"", "*"}:
        findings.append(ReadinessFinding("WEB-001", "block", "Production CORS origins must be explicit"))
    if production and not firebase_auth_required:
        findings.append(ReadinessFinding("AUTH-001", "block", "Firebase authentication must remain enabled in production"))
    if not app_version.strip():
        findings.append(ReadinessFinding("REL-001", "block", "APP_VERSION must be immutable and non-empty"))
    return findings
