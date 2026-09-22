# DermCareAI v5.1 production deployment

## Tenant bootstrap

Clinical API access requires verified Firebase custom claims:

- organization_id
- clinic_id
- roles

Use backend/tenant_bootstrap.py only from a controlled administrative environment with the Firebase service account.

## Data stores

The v5 clinical layer currently supports persistent SQLite for a controlled single-instance clinic deployment. For multi-instance production, migrate the clinical, commerce, audit and AI-governance stores to managed PostgreSQL with tested migrations and transaction isolation.

Persist database files outside the application container for a pilot. Never commit database files.

## Firestore

Deploy firestore.rules before enabling clinical access. Backfill existing patients, appointments and screeningReports with organizationId and clinicId before removing the legacy ownership exception.

## Object storage

Clinical images require an active consent purpose and should be retained in managed object storage with lifecycle policies, encryption and access logging.

## AI release

A model may be staged for evaluation. Production deployment requires:

1. immutable artifact SHA-256;
2. completed evaluation record;
3. independent validation evidence where intended;
4. calibration evidence when confidence is displayed;
5. subgroup evaluation;
6. explicit administrator approval;
7. research_only=false;
8. validated=true.

Rollback is represented by the deployment ledger and must also be wired to the production serving configuration.

## Backup and recovery

Define and test:

- RPO/RTO;
- encrypted database backups;
- object-storage retention/versioning;
- point-in-time recovery where supported;
- restore drills;
- application configuration/secrets recovery;
- incident-response ownership.

## Clinical release gate

A release candidate is not a clinical production release solely because CI passes. Clinical validation, privacy governance, regulatory assessment and operational evidence remain separate release gates.
