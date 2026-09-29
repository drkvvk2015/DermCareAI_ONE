# DermCareAI Production Deployment Runbook

Updated: 2026-09-29

This is an operational checklist, not evidence that DermCareAI is deployed. The
repository can establish **READY-FOR-SETUP** when its code and CI gates pass.
Only the accountable operator can mark an environment **DEPLOYED** after the
environment-specific checks and external clinical/regulatory approvals below
are recorded.

## 1. Configure the target environment

Set production values in the secret manager or workload identity provider. Do
not commit values or paste secret values into release evidence:

- `APP_ENV=production` and an immutable `APP_VERSION`.
- `FIREBASE_AUTH_REQUIRED=true` and Firebase Admin credentials through ADC,
  workload identity, or a service-account secret.
- `DATABASE_URL` (and any store-specific overrides) using PostgreSQL.
- Explicit HTTPS `CORS_ORIGINS`; wildcard and localhost origins are prohibited.
- `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`,
  `CLOUDINARY_API_SECRET`, and `CLOUDINARY_UPLOAD_PRESET` for clinical-image
  object storage.
- `ENABLE_EMBEDDED_DERM_MODEL=false`, approved `MIN_CONFIDENCE`, and the
  approved `MAX_IMAGE_BYTES`.

Payment and messaging credentials are configured only when those integrations
have provider approval, consent, templates, and an owner.

## 2. Run the fail-closed preflight

From `/app` in the release image (or from `backend/` in a checkout):

```bash
python scripts/production_preflight.py
python scripts/production_preflight.py --json > production-preflight.json
```

The command must exit zero. It checks production mode, authentication,
PostgreSQL, explicit HTTPS CORS, Firebase identity, object storage, model
policy, release version, and bounded image/confidence settings. It does not
print secret values. A non-zero result is a **BLOCK**; do not continue.

## 3. Promote staging to production

1. Build one immutable image from the release commit SHA and record its digest.
2. Deploy that image to isolated staging with production-like PostgreSQL,
   object storage, authentication, and CORS settings.
3. Initialize schemas and run the staging acceptance workflow.
4. Run the smoke checks in section 5 and attach their output to the release.
5. Obtain accountable operational approval and the external clinical,
   regulatory/privacy, and provider-account approvals.
6. Create a verified database backup immediately before promotion.
7. Promote the same image digest and configuration references to production;
   do not rebuild between environments.

## 4. Backup and disaster recovery verification

Create and validate a custom-format backup before migration or promotion:

```bash
DATABASE_URL="$DATABASE_URL" BACKUP_DIR="$BACKUP_DIR" \
  ./scripts/backup_postgres.sh
```

The script must report `Backup written and verified`. Retain the dump outside
the application host according to the organization retention policy. The
scheduled disaster-recovery workflow must restore a recent dump into an
isolated PostgreSQL instance and verify its sentinel record. Record backup
timestamp, restore timestamp, result, and recovery objectives; never record
credentials.

## 5. Health and post-deploy smoke checks

After the service is reachable, require successful responses from:

```bash
curl --fail "$BASE_URL/api/v1/health/live"
curl --fail "$BASE_URL/api/v1/health/ready"
curl --fail "$BASE_URL/api/v1/platform"
```

Then verify, with synthetic non-PHI data and an authenticated test identity:

- login/authentication and tenant boundary enforcement;
- clinical encounter create/read and audit correlation;
- image upload/signing and object-storage retrieval;
- AI request returns an explicit human-review/abstention contract;
- payment/pharmacy/notification paths only if enabled;
- request IDs are present and no response or log contains secrets or PHI.

Readiness must not be treated as clinical approval. A degraded readiness or
failed smoke check blocks traffic expansion.

## 6. Rollback

1. Stop promotion and preserve request IDs, logs, metrics, and audit evidence.
2. Route traffic to the previous known-good image digest.
3. Re-run liveness, readiness, and smoke checks.
4. Restore the pre-deploy backup only when the schema is not compatible with
   the previous version; coordinate this as a separately approved change.
5. Record the rollback reason, image digests, migration state, backup used, and
   verification result. Preserve audit records.

## 7. Evidence and completion state

The release record must contain the commit SHA/image digest, preflight output,
staging acceptance, migration result, backup/restore evidence, health and smoke
results, dependency/security artifacts, and approval references.

- **READY-FOR-SETUP**: repository checks pass, but deployment configuration,
  environment evidence, or external approvals are still outstanding.
- **DEPLOYED**: an operator has verified the target environment, completed the
  promotion and smoke checks, and recorded all required external approvals.

The repository must never claim **DEPLOYED** on its own. Clinical validation,
regulatory classification/approval, privacy review, infrastructure ownership,
and provider approvals remain explicit external gates.
