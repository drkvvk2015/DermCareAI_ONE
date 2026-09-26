# DermCareAI Production Deployment Runbook

**Status:** Deployment package ready — environment activation and accountable approval required

## 1. Production architecture contract

Required components:

- application/backend compute;
- managed PostgreSQL;
- private secret/configuration store;
- object storage for clinical media;
- Firebase authentication configuration;
- payment provider configuration where enabled;
- TLS termination;
- centralized logs/metrics;
- scheduled backups;
- disaster-recovery restoration path;
- monitoring and alerting.

SQLite must not be used as the production persistence boundary.

## 2. Required production configuration

Set these values through the deployment platform's secret/configuration mechanism; never commit secrets:

- APP_ENV=production
- DATABASE_URL=<managed PostgreSQL>
- CORS_ORIGINS=<explicit production origins>
- Firebase authentication/service configuration
- Cloudinary/object-storage server credentials where enabled
- payment provider credentials/webhook secret where enabled
- production AI/model registry configuration
- audit/observability configuration

The deployment must fail closed when required production configuration is missing.

## 3. Database

Before activation:

1. create managed PostgreSQL instance;
2. restrict network access;
3. create database/user with least privilege;
4. run the checked-in migration/bootstrap process;
5. verify schema migration ledger;
6. configure automated backups;
7. perform a restoration test;
8. record the backup/restore evidence.

## 4. Release artifact

Build the backend container from a tagged release. Use the generated SBOM/provenance artifacts and retain the image digest.

Do not deploy an unreviewed mutable branch as the production release artifact.

## 5. Security gate

Verify:

- TLS enabled;
- production CORS explicit;
- authentication enforced;
- privileged endpoints protected;
- tenant isolation tests passed;
- rate limiting enabled;
- object storage uses server-mediated credentials;
- secrets absent from logs;
- audit logging enabled;
- backup and restore verified.

## 6. Clinical safety gate

Before clinical activation:

- intended-use statement approved;
- AI evidence package approved for the intended claim;
- independent validation complete where required;
- clinical governance approval complete;
- regulatory/privacy assessment complete;
- training and support procedures complete;
- rollback/disable-AI procedure tested.

The system may technically run before these gates, but it must not be represented as clinically approved.

## 7. Deployment verification

After deployment, verify:

- health/readiness endpoint;
- authentication;
- patient isolation;
- encounter create/update/sign-off;
- image consent enforcement;
- AI review boundary;
- billing/payment test path where enabled;
- prescription/pharmacy workflow;
- audit trace;
- backup job;
- alerting;
- rollback artifact availability.

Use synthetic/non-production test data for deployment verification.

## 8. Rollback

Rollback triggers include:

- unsafe clinical workflow behavior;
- authentication/authorization regression;
- tenant leakage;
- data-integrity failure;
- payment integrity failure;
- unavailable recovery path;
- critical security vulnerability.

Rollback to the last approved immutable image digest and document the incident.

## 9. Environment activation record

Record:

- cloud/provider;
- region;
- environment ID;
- database identifier;
- image digest;
- release tag;
- model artifact digest;
- deployment approver;
- clinical approval status;
- regulatory/privacy status;
- date/time;
- rollback target.

## 10. Current state

The repository now contains a production deployment contract and operational runbook. Actual cloud activation remains environment-specific because it requires organization-owned infrastructure, secrets, approvals and operational accounts that must not be fabricated inside the repository.
