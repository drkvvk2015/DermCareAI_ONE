# Production Deployment Preflight

This document is an executable preparation checklist for a real DermCareAI deployment.
It does not constitute production deployment, clinical validation, or regulatory approval.

## 1. Required environment contract

Set the following in the deployment secret/configuration manager:

| Variable | Production requirement |
|---|---|
| `APP_ENV` | `production` |
| `APP_VERSION` | immutable release identifier |
| `CORS_ORIGINS` | explicit HTTPS origin(s); never `*` |
| `FIREBASE_AUTH_REQUIRED` | `true` |
| `DATABASE_URL` | PostgreSQL URL using the `psycopg` driver |
| `COMMERCE_DATABASE_URL` | PostgreSQL URL when commerce is enabled |
| `CLINICAL_DATABASE_URL` | PostgreSQL URL when isolated clinical store is enabled |
| `AUDIT_DATABASE_URL` | PostgreSQL URL when isolated audit store is enabled |
| `AI_GOVERNANCE_DATABASE_URL` | PostgreSQL URL when isolated AI-governance store is enabled |
| `REDIS_URL` | managed Redis when distributed rate limiting is mandatory |
| `FIREBASE_SERVICE_ACCOUNT_JSON` | secret-managed service account |
| Payment/webhook secrets | secret-managed; never committed |
| Cloudinary signing secrets | server-side only; never embedded in mobile code |

## 2. Preflight checks

Before deployment, run the repository's production-readiness contract and verify:

- PostgreSQL is configured for every production store that is enabled.
- SQLite is not used as a production backing store.
- CORS is explicit.
- Firebase authentication remains required.
- `APP_VERSION` is non-empty and immutable for the release.
- Distributed Redis rate limiting is present when required.
- Model registry/integrity controls remain enabled for governed AI paths.
- No client bundle contains Cloudinary or payment secrets.
- Database migrations are idempotent and have a recorded migration version.
- Required backups, retention, rollback and disaster-recovery procedures are configured outside the application repository.

## 3. Deployment sequence

`validate configuration -> build immutable artifact -> run required CI -> migrate staging -> staging acceptance -> backup production -> apply migrations -> deploy -> smoke test -> monitor -> release sign-off`

Do not skip staging acceptance or the production-backup step.

## 4. Rollback

A rollback must include both application and schema considerations:

1. Stop promotion of new application instances.
2. Preserve logs and deployment identifiers.
3. Revert application artifact to the last known-good immutable version.
4. Do not automatically reverse irreversible schema migrations.
5. Use an explicitly tested forward-compatible migration/repair procedure where schema changes are involved.
6. Re-run health, auth, database and audit smoke checks.
7. Record the incident and release decision.

## 5. Evidence to record

Record the following for every real production release:

- Git commit SHA;
- container/artifact digest;
- migration ledger version;
- CI workflow run IDs;
- staging acceptance result;
- backup identifier;
- deployment timestamp;
- operator/accountable approver;
- rollback verification status.

## 6. External gates

The following remain outside software-only preflight:

- independent clinical/AI validation;
- prospective clinical evaluation;
- formal intended-use and regulatory classification/approval;
- clinic-specific privacy/governance approval;
- accountable production release authorization.
