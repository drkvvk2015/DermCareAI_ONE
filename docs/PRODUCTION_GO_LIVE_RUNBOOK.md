# DermCareAI Production Go-Live Runbook

Updated: 2026-09-22

This runbook is the operational handoff for deploying the current DermCareAI engineering baseline. It does not replace clinical validation, regulatory/privacy review, or accountable release approval.

## 1. Required production configuration

Set these values in the deployment secret manager; never commit them to Git:

- `APP_ENV=production`
- `APP_VERSION=<release-version>`
- `FIREBASE_AUTH_REQUIRED=true`
- `DATABASE_URL=postgresql+psycopg://...`
- `CORS_ORIGINS=https://approved-clinic-origin,...`
- Firebase credentials through service-account JSON, workload identity/ADC, or equivalent Google Cloud identity.
- `ENABLE_EMBEDDED_DERM_MODEL=false`
- `MIN_CONFIDENCE` within `[0,1]`.
- `MAX_IMAGE_BYTES` within the approved operational limit.

For clinical-image storage, configure the production Cloudinary/object-storage integration used by the deployment. For payments, configure the Razorpay key, secret and webhook secret. For communications, configure WhatsApp and/or the approved SMS provider only when those channels are enabled.

## 2. Preflight

From the backend directory:

```bash
python scripts/production_preflight.py
python scripts/production_preflight.py --json
```

The preflight fails closed on production CORS wildcard use, SQLite persistence, disabled Firebase enforcement, placeholder database credentials, invalid confidence/image limits, or the embedded research model being enabled.

The check never prints secret values.

## 3. Database and resilience

Before first production traffic:

```bash
DATABASE_URL=... BACKUP_DIR=./backups ./scripts/backup_postgres.sh
```

Verify PostgreSQL migrations and execute a restore drill using the repository DR workflow. Record the resulting evidence and recovery objective.

## 4. Service health

Check:

```text
GET /api/v1/health/live
GET /api/v1/health/ready
GET /api/v1/platform
```

`/health/live` confirms process liveness. `/api/v1/health/ready` reports model, registry and authentication readiness. A degraded readiness state must be triaged before enabling AI-dependent workflows.

## 5. Clinical release gate

Verify on the target environment:

1. Tenant isolation between organizations/clinics.
2. Clinical-image consent enforcement.
3. Structured encounter creation and optimistic concurrency.
4. Body-map/longitudinal lesion persistence.
5. Procedure consent enforcement.
6. AI attachment followed by explicit Accept/Reject/Override.
7. Encounter sign-off remains blocked while AI reviews are pending.
8. Follow-up creation and retrieval.
9. Audit events are written without PHI in observability summaries.
10. PostgreSQL is the active persistence boundary.

## 6. Payments, pharmacy and messaging

Run provider sandbox tests before live credentials:

- Razorpay invoice amount integrity and signed webhook processing.
- Pharmacy atomic dispensing and insufficient-stock conflict behavior.
- WhatsApp template delivery or approved SMS provider delivery.
- Registration notification audit/troubleshooting without storing message secrets.

Do not enable a channel merely because its environment variables exist; confirm provider approval, templates, consent and institutional policy.

## 7. AI boundary

The embedded HAM10000 research fallback is not a clinically validated diagnostic model. Production clinical use therefore requires the independent AI evidence package documented in `docs/WAVE5_RELEASE_EVIDENCE_STATUS.md`.

The application must retain clinician review and sign-off controls, including abstention for unsafe/low-quality inputs.

## 8. Rollout and rollback

Use a staged rollout:

1. Deploy to an isolated production-like environment.
2. Run database migrations.
3. Run live health and clinical smoke tests.
4. Enable a small controlled clinician cohort.
5. Monitor request/error metrics and audit integrity.
6. Expand only after accountable sign-off.

For rollback, redeploy the previous known-good image/version and restore database state only when schema compatibility requires it. Preserve audit records during rollback.

## 9. Evidence to retain

Keep:

- release commit SHA;
- production preflight output;
- migration output;
- backup/restore evidence;
- staging/production smoke-test results;
- dependency and CodeQL artifacts;
- clinical validation/approval records;
- regulatory/privacy decisions;
- incident and rollback evidence.

## 10. Completion boundary

The repository's engineering release is complete when CI, staging, database, security and operational preflight gates are green.

Clinical validation, regulatory classification/approval, organizational privacy processes, provider account approvals and production infrastructure configuration remain evidence- and environment-dependent activities.
