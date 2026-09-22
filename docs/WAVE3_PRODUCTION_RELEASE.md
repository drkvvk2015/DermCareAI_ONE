# DermCareAI Wave 3 — Production Release Assurance

## Production storage boundary

The four durable domains now use the shared SQLAlchemy storage layer:

- clinical encounters, lesions, consent and media metadata;
- billing and pharmacy;
- audit;
- AI model governance, evaluation and deployment ledger.

SQLite remains a local-development fallback. Production startup rejects SQLite for these stores. Production must use managed PostgreSQL through DATABASE_URL or a store-specific PostgreSQL URL.

## Staging

Start the staging stack with:

docker compose -f docker-compose.staging.yml up --build

The stack provides PostgreSQL plus the containerized FastAPI backend, with a persistent PostgreSQL volume and health checks.

Never place production credentials in docker-compose.staging.yml.

## Database bootstrap

Run backend/scripts/migrate_postgres.py in the deployment environment before application promotion.

The script initializes all four persistence schemas against the configured PostgreSQL database.

## Backup and restore

Create a custom-format backup with backend/scripts/backup_postgres.sh.

Restore with backend/scripts/restore_postgres.sh during a controlled maintenance window.

Production additionally requires encrypted off-host backup retention, access control, and periodic restore drills.

## Production configuration gate

Run backend/scripts/check_production_config.py with APP_ENV=production.

The validator fails closed when:

- Firebase authentication is disabled;
- wildcard or localhost CORS remains;
- any durable store resolves to SQLite;
- Firebase service credentials are missing;
- Cloudinary signing credentials are missing;
- Razorpay secrets are missing.

## CI release gates

The candidate should remain blocked until all of these are green:

1. backend regression;
2. mobile TypeScript and Expo export;
3. CodeQL;
4. PostgreSQL staging integration;
5. Firestore rules deployment/test;
6. clinical end-to-end workflow;
7. backup/restore evidence;
8. AI safety/evidence review for model changes.

CI success is necessary but is not, by itself, clinical validation, regulatory clearance, or privacy-law compliance.

## Rollback

Application rollback and database rollback are separate operations.

- Application: revert to an immutable build/image.
- Database: use point-in-time recovery or a tested restore.
- AI: revert the active model deployment and the serving configuration.

Do not perform a destructive schema migration without a tested restore path.
