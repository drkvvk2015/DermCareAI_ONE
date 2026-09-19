# DermCareAI — Dermatology Clinic Operating System

DermCareAI is a healthcare-oriented dermatology clinic platform for **Patient 360, encounter documentation, longitudinal lesion tracking, AI-assisted image review, billing, pharmacy, notifications, auditability and production operations**.

> ⚠️ **Clinical boundary:** AI output is decision support, not a diagnosis. The current embedded HAM10000 model is a research fallback and is **not clinically validated for routine patient care**. Clinical deployment requires intended-use review, independent validation and applicable regulatory/privacy approvals.

> ✅ **Engineering baseline:** v5 production hardening + Wave 4 clinical workflow are implemented on PR #42. Automated backend, mobile, PostgreSQL, CodeQL and clinical workflow gates are in place.

## Visual overview

![DermCareAI production architecture](docs/assets/architecture.svg)

![DermCareAI clinical encounter workflow](docs/assets/clinical-workflow.svg)

![DermCareAI AI safety boundary](docs/assets/ai-safety.svg)

![DermCareAI production release pipeline](docs/assets/release-pipeline.svg)

## What is implemented

### Clinical workflow
- Patient 360 clinical summary
- Encounter-centered documentation
- Structured dermatology history and examination
- Stable longitudinal lesion identifiers
- Lesion morphology/evolution/symptom tracking
- Clinical image consent enforcement
- Encounter-linked AI assessment
- Explicit clinician **Accept / Reject / Override**
- Override label recording
- AI provenance and request ID traceability
- Follow-up planning
- Clinician attestation and encounter sign-off
- Final sign-off blocked while attached AI assessments remain unreviewed
- Optimistic concurrency protection

### Production platform
- FastAPI `/api/v1` platform contract
- Firebase ID-token authentication
- Role-based authorization
- Organization + clinic tenant claims
- PostgreSQL production persistence
- SQLite development fallback only
- Server-side signed object-storage uploads
- Billing/payment integrity controls
- Pharmacy transactional stock handling
- Hash-chained audit events
- Request correlation and aggregate observability
- Production configuration fail-closed checks
- Containerized backend
- GHCR release artifacts with SBOM/provenance
- PostgreSQL backup/restore tooling
- Controlled SQLite → PostgreSQL migration utility

### AI governance
- Model registry
- Artifact SHA-256 verification
- Model status/approval lifecycle
- Evaluation metadata
- Subgroup metric storage
- External-validation flagging
- Production deployment restrictions
- Confidence threshold and abstention
- Clinician review traceability
- Formal AI validation manifest template

## Release state

| Gate | State |
|---|---|
| Backend regression | ✅ Automated |
| Mobile TypeScript | ✅ Automated |
| Expo export smoke test | ✅ Automated |
| PostgreSQL integration | ✅ Automated |
| Clinical API E2E | ✅ Automated |
| Tenant isolation | ✅ Automated |
| AI-review/sign-off safety | ✅ Automated |
| CodeQL | ✅ Automated |
| Staging acceptance workflow | ✅ Implemented |
| Disaster-recovery drill | ✅ Implemented |
| Dependency audit | ✅ Reporting enabled |
| SBOM/provenance | ✅ Container workflow enabled |
| Independent AI clinical validation | ⚠️ Evidence still required |
| Prospective clinical validation | ⚠️ Evidence still required |
| Regulatory classification/approval | ⚠️ Formal assessment required |
| Production cloud deployment | ⚠️ Environment-specific setup required |

See [Wave 5 Release Evidence Status](docs/WAVE5_RELEASE_EVIDENCE_STATUS.md).

## Clinical workflow

**Patient 360 → Start Clinical Encounter → History → Dermatology Examination → Lesion Capture → Assessment → AI Review (optional) → Follow-up → Sign-off**

An AI result can be attached to the encounter, but it cannot silently become a signed diagnosis. Every attached AI assessment must receive an explicit clinician decision before the encounter can be signed.

See [Wave 4 Clinical Workflow](docs/WAVE4_CLINICAL_WORKFLOW.md).

## Production architecture

![Production architecture](docs/assets/architecture.svg)

The production persistence boundary is PostgreSQL. The application rejects SQLite in production mode.

Durable domains include clinical encounters/lesions/consents/media metadata, billing/pharmacy, audit, and AI governance/evaluation/deployment records.

## Release pipeline

![Production release pipeline](docs/assets/release-pipeline.svg)

GitHub Actions now provide backend regression, mobile regression, PostgreSQL integration, CodeQL, staging acceptance, dependency audit reporting, disaster-recovery drills, and container release with SBOM/provenance.

The repository intentionally keeps the **software release gate** separate from the **clinical validation gate** and **regulatory/privacy gate**.

## Repository layout

```text
.
├── backend/
│   ├── app.py
│   ├── clinical.py
│   ├── clinical_store.py
│   ├── commerce.py
│   ├── commerce_store.py
│   ├── ai_registry.py
│   ├── audit.py
│   ├── storage.py
│   ├── admin.py
│   ├── media.py
│   └── tests/
├── dermcareai/
│   └── src/
├── docs/
│   ├── assets/
│   ├── ai-validation/
│   ├── WAVE3_PRODUCTION_RELEASE.md
│   ├── WAVE4_CLINICAL_WORKFLOW.md
│   └── WAVE5_RELEASE_EVIDENCE_STATUS.md
├── docker-compose.staging.yml
└── .github/workflows/
```

## Local development

### Backend
```bash
cd backend
python -m pip install -U pip
python -m pip install -r requirements.txt
pytest -q tests
python -m compileall -q .
```

### Mobile
```bash
cd dermcareai
npm ci
npx tsc --noEmit
npx expo export --platform web
```

### Local PostgreSQL staging
```bash
docker compose -f docker-compose.staging.yml up --build
docker compose -f docker-compose.staging.yml exec backend python scripts/migrate_postgres.py
```

## Production database migration

A controlled migration utility is included:
```bash
python backend/scripts/copy_sqlite_to_postgres.py \
  --source sqlite:///clinical.db \
  --target postgresql+psycopg://USER:PASSWORD@HOST/DB \
  --tables encounters,lesions,consents,clinical_media
```

Pre-create the PostgreSQL schema first and use a maintenance window for production migration.

## Backup and restore

Create a PostgreSQL backup:
```bash
DATABASE_URL=... BACKUP_DIR=./backups ./backend/scripts/backup_postgres.sh
```

Restore:
```bash
DATABASE_URL=... BACKUP_FILE=./backups/<backup>.dump ./backend/scripts/restore_postgres.sh
```

An automated disaster-recovery drill is also included in GitHub Actions.

## Security

Production controls include Firebase authentication, server-side RBAC, tenant-aware authorization, consent enforcement for clinical media, signed server-mediated object uploads, no client-side Cloudinary secret, rate limiting on privileged/high-cost endpoints, payment idempotency/signature validation, hash-chained audit records, fail-closed production CORS, PostgreSQL production enforcement, CodeQL, dependency audit reporting, and SBOM/provenance-enabled container releases.

## Dependency security

The dependency audit workflow produces machine-readable npm and Python vulnerability reports as CI artifacts. Unresolved findings remain release evidence and are not hidden behind a false-green gate.

## Clinical / regulatory boundary

The platform does not claim regulatory approval or clinical validation.

For India, the release review should assess the Medical Devices Rules, 2017; current CDSCO guidance applicable to Medical Device Software; Digital Personal Data Protection Act/Rules obligations; institutional privacy/consent/retention/incident controls; pharmacy requirements; payment-provider requirements; and professional/clinical governance.

Official references:
- CDSCO Medical Device & Diagnostics: https://www.cdsco.gov.in/opencms/opencms/en/Medical-Device-Diagnostics/
- CDSCO Medical Devices Rules: https://cdsco.gov.in/opencms/opencms/en/Acts-and-rules/Medical-Devices-Rules/
- MeitY DPDP Rules 2025: https://www.meity.gov.in/documents/act-and-policies/digital-personal-data-protection-rules-2025-gDOxUjMtQWa

## AI validation release package

Use `docs/ai-validation/release-manifest.template.json` and validate a completed evidence package with:

```bash
python backend/scripts/validate_ai_release_manifest.py docs/ai-validation/release-manifest.json
```

Do **not** enter estimated or invented clinical performance values.

Minimum evidence includes frozen model artifact, locked test set, sensitivity/specificity, PPV/NPV where appropriate, ROC-AUC/PR-AUC where appropriate, calibration, subgroup analysis, OOD behavior, abstention performance, clinician override analysis, independent/external validation and accountable approval.

## Important limitations

- AI screening is assistive and cannot replace dermatologist assessment, histopathology or other indicated investigation.
- The research model is not clinically validated for routine patient care.
- Technical CI success is not clinical validation.
- A staging workflow is not the same as a live production deployment.
- Regulatory/privacy status depends on intended use, claims, jurisdiction and the organization's actual controls.

## License

See the repository for the applicable project licensing and dependency notices.
