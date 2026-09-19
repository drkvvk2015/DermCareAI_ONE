# DermCareAI v5 — Production Hardening

## Scope

v5 hardens the application around the highest-risk gaps found in the v4 review:
authentication boundaries, mobile secret exposure, clinical data authorization, transaction durability, audit integrity, abuse controls, and operational release safety.

## Non-negotiable production controls

- Firebase authentication remains mandatory for all clinic operations.
- AI inference is restricted to authenticated clinical users.
- Model management and self-healing are restricted to privileged operational roles.
- Cloudinary API secrets remain server-side.
- Clinical Firestore access is governed by deployed rules and tested before release.
- Billing and pharmacy state must use durable transactional storage in production.
- External notification payloads must not contain PHI.
- Production CORS is explicit and fail-closed.
- Inference and media-signing endpoints are rate limited.
- AI models remain research-only until independent clinical validation establishes the intended-use evidence.

## Deployment boundary

A single-instance deployment may use encrypted persistent SQLite for controlled clinic pilots. Horizontal scaling should use a managed PostgreSQL deployment with migrations, backups, and transactional isolation.

## Release gate

Every production candidate should pass backend regression, mobile type/export, CodeQL, dependency audit, Firestore rules tests, staging smoke/E2E tests, and a clinical safety review for any AI/model change.

## Remaining deployment-level evidence

Repository hardening does not itself establish regulatory clearance, clinical validation, data-protection compliance, penetration-test completion, backup/restore evidence, or production service-level objectives.
