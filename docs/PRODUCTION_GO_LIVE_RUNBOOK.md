# DermCareAI Production Go-Live Runbook

Updated: 2026-09-22

This runbook is the operational handoff for deploying the current DermCareAI engineering baseline. It does not replace clinical validation, regulatory/privacy review, or accountable release approval.

## Web PWA release addendum

This addendum applies only to `webapp/`, the authenticated, read-only clinical dashboard. It does not change the backend API or policy, the Expo mobile app, or native/mobile CI. No hosting-provider-specific workflow is defined: the provider, production domain/origin, and accountable deployment and privacy approvals remain unresolved. Confirm these before selecting deployment automation or production configuration.

### Web pre-deployment requirements

1. Select and approve the hosting provider and one canonical production HTTPS origin. Serve the PWA only over HTTPS; use localhost HTTPS exceptions only for development.
2. Set the API base URL to the approved API. Configure backend `CORS_ORIGINS` with the exact dashboard origin only (scheme, hostname, and any non-default port; no path and no trailing slash), for example `https://dashboard.example.invalid`. Do not use `*`, broad subdomains, preview URLs, or an origin supplied by an untrusted request. Backend CORS and authorization remain authoritative.
3. Configure Firebase Authentication for email/password sign-in, add the exact production web origin's host to Firebase authorized domains, and provide the matching Firebase Web app `apiKey`, `authDomain`, `projectId`, and `appId`. Verify Firebase ID-token verification and server-side role and tenant checks for every existing read endpoint. Confirm the organization's clinician/staff role mapping and tenant membership in the server policy before release; client-side route protection is only a user-interface measure.
4. Supply browser-visible settings only as `VITE_*` build configuration. Firebase Web app settings and the public API URL are not privileged credentials. Never put service-account JSON, private keys, server API secrets, bearer tokens, or other privileged credentials into Vite variables, source, build artifacts, or client environment files. Keep server credentials in the approved server-side secret/identity system.
5. Review privacy controls for the selected hosting, monitoring, Firebase, and API services. Do not place patient data in deployment logs, analytics, crash reports, test fixtures, screenshots, browser storage, or service-worker caches. The PWA caches only static shell assets. Authentication and all patient-record reads require a live network; offline shell availability is not offline clinical access. Confirm the Firebase SDK's configured session-persistence behavior is acceptable for the organization's managed-device policy.
6. Run the webapp dependency, lint, test, and production-build checks in the release pipeline. Review generated asset/service-worker precaching and verify no API, authentication, or clinical response is stored. Do not change backend policy/API or the Expo application as part of this web release.

### Web deployment smoke and rollback

Use approved synthetic/test accounts and synthetic records only; never use real patient data for a release smoke test unless explicitly authorized under clinic procedures.

1. Confirm the HTTPS origin, certificate, app manifest, icons, service worker, and installability on supported browsers/devices. Confirm the service worker can serve the static app shell on a subsequent visit.
2. Confirm signed-out access redirects to sign-in and invalid Firebase configuration fails safely. Sign in with an authorized test account; confirm a permitted synthetic record can be read through summary, prescription, and procedure routes without write controls.
3. Confirm a test user lacking the required server role or tenant membership is denied by the API on each relevant route. A hidden/blocked client route is not a substitute for this API authorization check.
4. Confirm API `401`/`403` and network/offline failures produce safe states, with retry available where appropriate. With the shell available offline, verify clinical endpoints are not served from cache and no stale clinical content is displayed. Inspect browser/service-worker storage for API response or clinical-record caches.
5. Check hosting and API health, error rates, CORS behavior from the exact approved origin, and audit integrity. Review operational logs for accidental patient identifiers or credentials before widening access.
6. On failure, disable/roll back the web release using the hosting provider's approved previous-known-good artifact/version process. Recheck the HTTPS origin, authentication, API authorization/CORS, and offline behavior after rollback. Preserve backend audit records; do not roll back or modify clinical data as a side effect of restoring the web shell.

The hosting-specific deployment, cache-purge, and rollback commands cannot be finalized until the provider and production origin are approved.

## 1. Required production configuration

Set these values in the deployment secret manager; never commit them to Git:

- `APP_ENV=production`
- `APP_VERSION=<release-version>`
- `FIREBASE_AUTH_REQUIRED=true`
- `PRIVACY_OPERATIONS_APPROVED=true` only after the accountable clinic privacy lead completes the [privacy operations readiness checklist](PRIVACY_OPERATIONS.md).
- `PRIVACY_POLICY_VERSION=<approved clinic policy revision>` matching the policy used for the deployment.
- `DATABASE_URL=postgresql+psycopg://...`
- `CORS_ORIGINS=https://approved-clinic-origin,...`
- Firebase credentials through service-account JSON, workload identity/ADC, or equivalent Google Cloud identity.
- `ENABLE_EMBEDDED_DERM_MODEL=false`
- `AI_ENABLED_IN_PRODUCTION=false` unless all independent clinical evidence and accountable approvals are complete.
- `AI_RELEASE_MANIFEST_PATH=<read-only mounted approved evidence manifest>` when a governed production AI release is explicitly authorized.
- `MIN_CONFIDENCE` within `[0,1]`.
- `MAX_IMAGE_BYTES` within the approved operational limit.

For clinical-image storage, configure the production Cloudinary/object-storage integration used by the deployment. For payments, configure the Razorpay key, secret and webhook secret. For communications, configure WhatsApp and/or the approved SMS provider only when those channels are enabled.

## 2. Preflight

From the backend directory:

```bash
python scripts/production_preflight.py
python scripts/production_preflight.py --json
```

The preflight fails closed on production CORS wildcard use, SQLite persistence, disabled Firebase enforcement, placeholder database credentials, invalid confidence/image limits, or the embedded research model being enabled. If production AI is enabled, it also requires a structurally complete approved evidence manifest; application startup checks that its model name, version, and artifact digest match the active model-registry deployment.

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

The embedded HAM10000 research fallback is not a clinically validated diagnostic model. Production clinical use therefore requires the independent AI evidence package documented in `docs/WAVE5_RELEASE_EVIDENCE_STATUS.md`. The evidence manifest is a structural release control; a valid manifest alone does not establish clinical validity or regulatory approval.

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
