# DermCareAI — Dermatology Clinic Operating System

DermCareAI is a healthcare-oriented dermatology clinic platform for **Patient 360, encounter documentation, longitudinal lesion tracking, AI-assisted image review, billing, pharmacy, notifications, auditability and production operations**.

> ⚠️ **Clinical boundary:** AI output is decision support, not a diagnosis. The current embedded HAM10000 model is a research fallback and is **not clinically validated for routine patient care**. Clinical deployment requires intended-use review, independent validation and applicable regulatory/privacy approvals.

> ✅ **Engineering baseline:** v5 production hardening + Wave 4 clinical workflow are merged into `main`. Automated backend, mobile, PostgreSQL, CodeQL and clinical workflow gates are in place.
>
> **Dermatology Completion:** v5.1 Wave 1 + Wave 2 are integrated into `main` through the validated `develop` release path. `main` is the stable engineering baseline; clinical validation and regulatory/privacy approval remain separate gates.
>
> **Current swarm hardening:** the final mainline wave adds durable prescription-dispense idempotency, concurrent dispense ownership protection with bounded recovery, and explicit audit events for idempotent replay. CI remains the final technical evidence gate for each merge.

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


## Current application UI previews

The current mobile application contains dedicated screens for authentication, dashboard, patients, appointments, encounters, body-map/lesions, AI screening, billing, prescriptions and pharmacy. The visuals below are repository-local previews aligned to those current screens and workflows; they are **not device screenshots** and should be replaced by runtime captures when a device/emulator capture is available.

| Preview | Current workflow represented |
|---|---|
| [Dashboard](docs/assets/ui-dashboard-preview.svg) | Clinic overview, appointments, clinical workspace and governed AI entry points |
| [Patient + Encounter](docs/assets/ui-patient-encounter-preview.svg) | Patient 360, history, examination, lesions, media consent, assessment and sign-off |
| [AI Review](docs/assets/ui-ai-review-preview.svg) | Image quality gate, model provenance, abstention and Accept / Reject / Override |
| [Billing + Pharmacy](docs/assets/ui-billing-pharmacy-preview.svg) | Billing/UPI, prescription, inventory and replay-safe dispensing workflows |

![DermCareAI dashboard UI preview](docs/assets/ui-dashboard-preview.svg)
![DermCareAI patient and encounter UI preview](docs/assets/ui-patient-encounter-preview.svg)
![DermCareAI AI review UI preview](docs/assets/ui-ai-review-preview.svg)
![DermCareAI billing and pharmacy UI preview](docs/assets/ui-billing-pharmacy-preview.svg)

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

## What is implemented

#### Final stabilization sprint — 24 September 2026

This release-critical pass adds a deterministic native Android smoke gate and records the clinical database migration version in a durable schema ledger. These are engineering gates only; independent clinical validation and regulatory/privacy review remain separate requirements.

#### Final dermatology hardening wave — 24 September 2026

The final engineering swarm has now been integrated as three independently validated streams:

| Stream | Evidence |
|---|---|
| Governed AI safety gateway | ✅ PR #159 merged; inference safety now consumes the shared AI safety gateway and model-registry integrity state |
| Clinical consent boundary | ✅ PR #159 merged; patient-linked AI assessments require active clinical-image consent when linked to media |
| Persistent mobile offline sync | ✅ PR #160 merged; replay-safe encounter updates and lesion upserts persist locally, retry with authenticated transport, and retain real 409 concurrency conflicts |
| Deployment readiness contract | ✅ PR #161 merged; readiness evaluates production PostgreSQL, explicit CORS and Firebase-auth requirements for clinical + commerce stores |
| Tenant regression matrix | ✅ PR #161 merged; cross-clinic clinical record access is covered by automated E2E tests |
| Full required CI matrix | ✅ Historical integration evidence: required workflows passed on PR #159, #160 and #161 heads before merge |
| Native Android smoke gate | 🟡 Added in final stabilization; current GitHub Actions runs are failing before any job steps execute, so no new executable evidence is available |
| Schema migration ledger | ✅ Migration bootstrap now records idempotent version evidence |
| Copyright/contributor governance | ✅ COPYRIGHT.md, CONTRIBUTING.md, CODEOWNERS and NOTICE added |
| Clinical/regulatory/deployment preparation | ✅ Evidence protocols, regulatory dossier and production runbook added |
| Final stabilization PR | 🟡 PR #174 contains the release-preparation work; current CI blocker is pre-step GitHub Actions execution failure |

**Offline synchronization scope:** the persistent queue intentionally covers mutations with deterministic replay/concurrency semantics (PATCH encounter updates and POST lesion upserts). Image uploads, prescriptions and other non-idempotent workflows remain online-first rather than being retried blindly.

**Production boundary:** software engineering gates are now hardened, but independent AI clinical validation, intended-use/regulatory review, privacy governance, and deployment into a real production environment remain external evidence/operations gates.
## Clinical workflow
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
| Staging acceptance workflow | ✅ Implemented and exercised in release gating |
| Disaster-recovery drill | ✅ Implemented |
| Dependency audit | ✅ Reporting enabled |
| SBOM/provenance | ✅ Container workflow enabled |
| Independent AI clinical validation | 🟡 **Evidence package ready** — [validation protocol](docs/AI_CLINICAL_VALIDATION_PROTOCOL.md) + manifest; independent execution/sign-off still required |
| Prospective clinical validation | 🟡 **Protocol ready** — [prospective evaluation protocol](docs/PROSPECTIVE_CLINICAL_EVALUATION_PROTOCOL.md); real-world execution still required |
| Regulatory classification/approval | 🟡 **Assessment dossier ready** — [India regulatory/privacy assessment](docs/INDIA_REGULATORY_ASSESSMENT.md); formal accountable classification/approval still required |
| Production cloud deployment | 🟢 **Deployment package ready** — [production runbook](docs/PRODUCTION_DEPLOYMENT_RUNBOOK.md); environment activation requires organization infrastructure, secrets and approval |

See [Wave 5 Release Evidence Status](docs/WAVE5_RELEASE_EVIDENCE_STATUS.md).

### Clinical, regulatory and deployment readiness packages

The repository-side preparation for the four previously open release areas is now complete:

| Area | Repository package | What remains outside code |
|---|---|---|
| Independent AI clinical validation | [AI validation protocol](docs/AI_CLINICAL_VALIDATION_PROTOCOL.md) + [release manifest template](docs/ai-validation/release-manifest.template.json) | Locked study data, independent analysis, actual results and accountable sign-off |
| Prospective clinical evaluation | [Prospective protocol](docs/PROSPECTIVE_CLINICAL_EVALUATION_PROTOCOL.md) | Institutional/ethics governance where applicable, real prospective execution and safety review |
| India regulatory/privacy | [Regulatory assessment dossier](docs/INDIA_REGULATORY_ASSESSMENT.md) | Formal classification, legal/regulatory review, institutional approvals and applicable registrations |
| Production deployment | [Production deployment runbook](docs/PRODUCTION_DEPLOYMENT_RUNBOOK.md) | Organization-owned cloud account, secrets, infrastructure activation and release approval |

These gates are intentionally not marked as completed by software alone. No clinical result, regulatory clearance or live production environment is claimed unless the corresponding external evidence exists.


### Final mainline engineering checkpoint

| Change | Mainline evidence |
|---|---|
| Durable prescription dispense ledger integration | ✅ PR #155 merged |
| Concurrent dispense ownership / bounded recovery | ✅ PR #156 merged |
| Idempotent replay audit trace | ✅ PR #157 merged |
| Required PR CI matrix | ✅ Green on the final integration wave |
| Open release PRs | 🟡 PR #174 remains open pending executable CI evidence |
| Clinical validation / regulatory approval | ⚠️ Separate evidence and governance gates remain |

The pharmacy lifecycle is therefore retry-safe at the application ledger boundary: an already allocated or completed prescription is not re-allocated on a retry, and completed replays are explicitly auditable. This does not claim cross-database transactional atomicity between every persistence subsystem.


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

The platform does not claim regulatory approval or clinical validation. Repository-side evidence preparation is documented, but external clinical, regulatory and production-operations gates remain distinct.

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

DermCareAI is currently licensed under **GNU AGPLv3** unless a file or component states otherwise.

- [AGPL-3.0 license text](LICENSE)
- [Copyright & rights record](COPYRIGHT.md)
- [Contribution and provenance policy](CONTRIBUTING.md)
- [Repository attribution notice](NOTICE)

The repository steward entry in `COPYRIGHT.md` records GitHub repository stewardship and review ownership; it does **not** by itself establish legal ownership of every historical contribution. Third-party components remain subject to their own licenses and copyright notices.


## Deployment hardware budget (India)

Indicative planning ranges; verify vendor quotations before procurement.

| Tier | Typical configuration | Approx. one-time budget |
|---|---|---:|
| Development | Existing 8 GB SSD laptop/workstation | ₹0 incremental |
| Small clinic | 4+ cores, 8–16 GB RAM, 256–512 GB SSD, UPS | ₹40,000–₹55,000 |
| Recommended clinic | 8 cores, 16 GB RAM, 512 GB NVMe, UPS + backup storage | ₹70,000–₹95,000 |
| AI-ready local inference | 8+ cores, 32 GB RAM, 1 TB NVMe, NVIDIA GPU with 8–12+ GB VRAM | ₹1.3–₹2.0 lakh+ |

Recommended production baseline: Ubuntu 24.04 LTS, PostgreSQL 16, Python 3.12, Node.js 22 LTS and Docker/Compose. Use 32 GB RAM and a supported GPU only when local AI inference is independently validated for the intended workload.

## Indicative cloud deployment budget

Monthly planning ranges for a small-to-standard clinic; actual bills vary by region, storage, traffic, backups, managed services and GPU usage.

| Deployment | Approx. monthly budget |
|---|---:|
| Development / low traffic | ₹0–₹1,500 |
| Small clinic | ₹3,000–₹6,000 |
| Standard clinic | ₹6,000–₹12,000 |
| Multi-clinic | ₹15,000–₹35,000 |
| AI/GPU-enabled | ₹35,000–₹80,000+ |

A typical production stack consists of an application compute service, managed PostgreSQL, object storage/backups, monitoring and TLS. GPU inference should be treated as a separate cost center and enabled only for validated workloads.

These figures are **budgetary estimates, not guaranteed cloud prices**. Obtain current provider quotations for the deployment region before committing.
