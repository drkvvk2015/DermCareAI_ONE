# DermCareAI — Dermatology Clinic Operating System

DermCareAI is a healthcare-oriented dermatology clinic platform for **Patient 360, encounter documentation, longitudinal lesion tracking, AI-assisted image review, billing, pharmacy, notifications, auditability and production operations**.

> ⚠️ **Clinical boundary:** AI output is decision support, not a diagnosis. Research models are disabled by default and are not clinically validated for routine patient care. Clinical deployment requires intended-use review, independent validation and applicable regulatory/privacy approvals.\n>\n> 📚 **Documentation principle:** this README is the operator/developer map; detailed release evidence belongs in `docs/`. GitHub renders repository-local SVGs and Mermaid diagrams directly, so the visuals below are kept versioned with the codebase.\n
> ✅ **Engineering baseline:** v5 production hardening + Wave 4 clinical workflow are merged into `main`. Automated backend, mobile, PostgreSQL, CodeQL and clinical workflow gates are in place.
>
> **Dermatology Completion:** v5.1 Wave 1 + Wave 2 are integrated into `main` through the validated `develop` release path. `main` is the stable engineering baseline; clinical validation and regulatory/privacy approval remain separate gates.
>
> **Current swarm hardening:** the latest mainline wave adds clinical audit/provenance regression coverage, React Native longitudinal-workflow API hardening, and pharmacy tenant-reassignment protection. CI remains the final technical evidence gate for each merge.

## Visual overview

The README uses **repository-local SVG diagrams** so the documentation renders without relying on an external image host. Each visual is also linked to its source file for full-size inspection.

| Visual | Purpose |
|---|---|
| [Production architecture](docs/assets/architecture.svg) | Client, API, AI governance, object storage and PostgreSQL boundaries |
| [Clinical encounter workflow](docs/assets/clinical-workflow.svg) | Patient 360 → encounter → examination → lesion → assessment → review → sign-off |
| [AI safety boundary](docs/assets/ai-safety.svg) | Consent, quality gate, model provenance, abstention and clinician controls |
| [Production release pipeline](docs/assets/release-pipeline.svg) | CI, PostgreSQL, staging, security, DR and clinical/AI evidence gates |

### 1. Production architecture

![DermCareAI production architecture — tenant-scoped clinical platform with governed AI and PostgreSQL](docs/assets/architecture.svg)

The architecture separates the clinician experience, authenticated FastAPI platform, AI governance, object storage and durable SQL persistence. **PostgreSQL is the production persistence boundary; SQLite is a development fallback only.**

### 2. Clinical encounter workflow

![DermCareAI clinical encounter workflow — Patient 360 to signed encounter](docs/assets/clinical-workflow.svg)

The **encounter is the central clinical record**. Longitudinal lesion data and optional AI assessment are attached to it, with explicit clinician review before final sign-off.

### 3. AI safety boundary

![DermCareAI AI safety boundary — consent, abstention and clinician review](docs/assets/ai-safety.svg)

AI output remains **traceable and reviewable**. An attached AI assessment cannot silently become a signed diagnosis; pending AI reviews block final encounter sign-off.

### 4. Production release pipeline

![DermCareAI production release pipeline — automated engineering gates plus clinical and regulatory evidence](docs/assets/release-pipeline.svg)

The release model deliberately separates **software validation**, **clinical/AI validation**, and **regulatory/privacy review**. Passing CI is necessary engineering evidence, not proof of clinical validity or regulatory clearance.

## System at a glance

```text
Clinician
   │
   ▼
Patient 360
   │
   ▼
Clinical Encounter
   ├── History / Examination
   ├── Longitudinal Lesion
   ├── Clinical Image + Consent
   ├── Assessment + Plan
   └── AI Decision Support (optional)
             │
             ▼
      Accept / Reject / Override
             │
             ▼
       Follow-up + Sign-off
             │
             ▼
     Audit + Governance Trace
```


## Quick start guide

### 1. Choose the deployment mode

| Mode | Database | AI | Intended use |
|---|---|---|---|
| Development | SQLite fallback | Disabled by default | Local engineering |
| Staging | PostgreSQL | Governed/opt-in | Integration and acceptance |
| Production | PostgreSQL | Only separately validated/approved models | Controlled clinical deployment |

**Never use SQLite as the production persistence boundary.**

### 2. Start the backend

```bash
cd backend
python -m pip install -U pip
python -m pip install -r requirements.txt
pytest -q tests
python -m compileall -q .
```

### 3. Start the mobile/web client

```bash
cd dermcareai
npm ci
npx tsc --noEmit
npx expo export --platform web
```

### 4. Start PostgreSQL staging

```bash
docker compose -f docker-compose.staging.yml up --build
docker compose -f docker-compose.staging.yml exec backend python scripts/migrate_postgres.py
```

### 5. Validate before release

Run the same classes of checks used by CI:

```bash
cd backend
pytest -q tests
python -m compileall -q .
cd ../dermcareai
npx tsc --noEmit
npx expo export --platform web
```

Then require the repository's PostgreSQL, staging, security, CodeQL, dependency, production-preflight and clinical E2E workflows to pass for the **exact commit being merged**.

## Clinical user workflow

The primary dermatology workflow is:

```mermaid
flowchart LR
    A[Patient 360] --> B[Clinical Encounter]
    B --> C[History]
    C --> D[Dermatology Examination]
    D --> E[Lesion / Media]
    E --> F[Assessment + Plan]
    F --> G{AI review needed?}
    G -->|No| H[Follow-up]
    G -->|Yes| I[Consent + Safety Gate]
    I --> J[Preliminary AI output]
    J --> K[Clinician Accept / Reject / Override]
    K --> H
    H --> L[Sign-off + Audit]
```

**Operational rule:** AI output is preliminary assistive information. It cannot silently become a signed diagnosis or prescription.

## Prescription → pharmacy workflow

```mermaid
sequenceDiagram
    participant D as Doctor
    participant C as Clinical API
    participant P as Prescription Store
    participant F as Pharmacy
    participant A as Audit

    D->>C: Create signed prescription
    C->>P: Tenant-scoped prescription
    D->>C: Pharmacy dispensing request
    C->>P: Validate active prescription
    C->>F: FEFO allocation
    F-->>C: Allocation result
    C->>P: Persist dispense state
    C->>A: Record dispensing event
    C-->>D: Prescription + dispensing result
```

**Production hardening requirement:** dispensing and prescription-state changes must remain idempotent/reconcilable so stock cannot be silently consumed without a durable dispensing state.

## AI governance workflow

```mermaid
flowchart TD
    A[Clinical image + context] --> B{Consent?}
    B -->|No| X[ABSTAIN]
    B -->|Yes| C{Model registered?}
    C -->|No| X
    C -->|Yes| D{Model enabled?}
    D -->|No| X
    D -->|Yes| E{Data quality / OOD checks}
    E -->|Unsafe / OOD| X
    E -->|Acceptable| F[Model inference]
    F --> G{Confidence / calibration policy}
    G -->|Below threshold| X
    G -->|Acceptable| H[Preliminary assistive output]
    H --> I[Clinician verification]
    I --> J[Audit + provenance]
```

The governance model deliberately separates **model registration**, **evaluation evidence**, **deployment approval**, and **clinical use**.

## Architecture at a glance

```mermaid
flowchart TB
    UI[React Native / Web Client] --> API[Authenticated FastAPI API]
    API --> CL[Clinical Domain]
    API --> PH[Pharmacy / Commerce]
    API --> AU[Audit + Observability]
    API --> AI[AI Governance Gateway]
    CL --> PG[(PostgreSQL)]
    PH --> PG
    AU --> PG
    AI --> REG[Model Registry / Evaluation]
    AI --> OBJ[Clinical Media / Object Storage]
    AI --> PG
```

### Tenant boundary

Every clinical, prescription and media operation should resolve **organization + clinic tenant context** from authenticated claims before accessing durable data. Cross-tenant object access is treated as an authorization failure, not a filtering convenience.

## AI model policy

Current policy:

1. Research/open-weight does **not** mean clinically validated.
2. Models remain disabled unless explicitly configured.
3. Model artifacts require immutable provenance/versioning.
4. Image/context provenance must be retained for review.
5. OOD/low-confidence cases must abstain rather than force an answer.
6. AI output requires clinician verification.
7. AI cannot sign a diagnosis or prescribe treatment.
8. Clinical validation is an independent release gate.

### MedGemma integration

The MedGemma adapter is an **opt-in research/assistive integration foundation**. It must not be treated as regulatory clearance or clinical validation. Do not commit model weights to the repository.

## Environment configuration

At minimum, review these production controls before deployment:

```text
APP_ENV=production
DATABASE_URL=postgresql+...
CORS_ORIGINS=https://...
FIREBASE_* / authentication configuration
APP_VERSION=<immutable release version>
ENABLE_EMBEDDED_DERM_MODEL=false
ENABLE_MEDGEMMA=false
MIN_CONFIDENCE=<validated policy value>
MAX_IMAGE_BYTES=<validated limit>
```

Secrets belong in the deployment secret manager/CI secret store, not in Git.

## Troubleshooting guide

### CI fails after a repair

Do not merge an older green commit. Inspect the **current PR head SHA**, reproduce the failing test, patch that branch, and wait for the required checks to rerun.

### PostgreSQL failures

Confirm:

```bash
echo "$DATABASE_URL"
docker compose -f docker-compose.staging.yml ps
docker compose -f docker-compose.staging.yml logs backend
```

Production must not silently fall back to SQLite.

### AI output is unavailable

Check the model's registration/approval state, explicit enable flag, model loading status, consent, image validity, OOD result and confidence policy. A safe abstention is an expected outcome.

### Mobile build/export fails

Run:

```bash
cd dermcareai
npm ci
npx tsc --noEmit
npx expo export --platform web
```

Fix TypeScript/build errors before changing clinical logic.

## Documentation map

| Document | Purpose |
|---|---|
| `docs/WAVE4_CLINICAL_WORKFLOW.md` | Clinical encounter workflow |
| `docs/WAVE5_RELEASE_EVIDENCE_STATUS.md` | Release evidence status |
| `docs/ai-validation/` | AI validation/evidence package |
| `docs/assets/` | Versioned architecture/workflow visuals |
| `.github/workflows/` | Automated engineering gates |

For GitHub rendering, repository-local image paths are preferred because they continue to work when the repository is cloned or viewed from another branch. Mermaid diagrams are also rendered natively by GitHub. 

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

> **Live release rule:** the table below describes engineering capabilities, not clinical approval. The current swarm PRs must be green and merged before their changes are represented as part of the stable `main` baseline.

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
| Staging acceptance workflow | ✅ Implemented and exercised in release gating |
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

The production persistence boundary is PostgreSQL. The application rejects SQLite in production mode.

Durable domains include clinical encounters/lesions/consents/media metadata, billing/pharmacy, audit, and AI governance/evaluation/deployment records.

## Release pipeline

GitHub Actions provide backend regression, mobile regression, PostgreSQL integration, CodeQL, staging acceptance, dependency audit reporting, disaster-recovery drills, and container release with SBOM/provenance.

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
