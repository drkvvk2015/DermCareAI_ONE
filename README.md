# DermCareAI — Dermatology Clinic Operating System

DermCareAI is a healthcare-oriented dermatology clinic platform for **Patient 360, encounter documentation, longitudinal lesion tracking, AI-assisted image review, billing, pharmacy, notifications, auditability and production operations**.

> ⚠️ **Clinical boundary:** AI output is decision support, not a diagnosis. The current embedded HAM10000 model is a research fallback and is **not clinically validated for routine patient care**. Clinical deployment requires intended-use review, independent validation and applicable regulatory/privacy approvals.
> ✅ **Engineering baseline:** v5 production hardening + Wave 4 clinical workflow are merged into `main`. Automated backend, mobile, PostgreSQL, CodeQL and clinical workflow gates are in place.
> **Dermatology Completion:** v5.1 Wave 1 + Wave 2 are integrated into `main` through the validated `develop` release path. `main` is the stable engineering baseline; clinical validation and regulatory/privacy approval remain separate gates.
> **Current mainline hardening:** PR #212 is merged into `main` (4 October 2026) and adds payment event/status enforcement, canonical pharmacy expiry + FEFO validation, prescription/patient linkage enforcement, decoded clinical-image validation, dashboard CI, and release-gated dependency auditing. CI remains the technical evidence gate; clinical validation and regulatory/privacy approval remain separate gates.

## Visual overview

The README uses **repository-local SVG diagrams** so the documentation renders without relying on an external image host. Each visual is also linked to its source file for full-size inspection.

| Visual | Purpose |
| --- | --- |
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

## Production hardening — mainline checkpoint, 5 October 2026

PR #212, merged as commit 8f1a5451c3d25c7210ed980e4667e11e6157310f, is the current security/reliability hardening baseline and supersedes PR #211. It covers the earlier ten-item production audit plus the final commerce, pharmacy, clinical-upload, dashboard-CI, and dependency-gating findings: payment events must be captured and authorized, pharmacy expiry values are canonical real dates, dispensing is tenant/patient/prescription scoped, clinical images are decoded and MIME-verified, the web dashboard has blocking lint/test/build gates, and remediable high/critical dependency findings block release.

Shared patient registration has been added: a tenant-scoped, audited `POST /api/v1/clinical/patients` endpoint serves both the web dashboard and mobile app, with idempotency, tenant/clinician identity server-derived from verified claims, and audit metadata free of patient PHI. Existing Firestore reads and rules remain unchanged for backward compatibility.

Production AI artifact verification has been hardened: the production-eligibility gate now fails closed for any model deployment whose name cannot be resolved to a locally verifiable artifact. Manifest validation test coverage was completed, error codes added for observability/audit, and helper functions extracted for maintainability. All 179 backend tests pass (178 baseline + 1 new manifest test).

The production contract remains explicit: PostgreSQL is required in production; clinical AI remains disabled by default until approved production artifacts and independent clinical validation are in place; CI evidence is required before merge; and clinical/regulatory/privacy validation remains outside software CI. The artifact-identity gate now ensures that any production deployment without a verifiable, SHA-256-matched local artifact is rejected.

The Android build path has also been aligned with Expo's Babel preset so clean native prebuilds link Expo native modules consistently.



## Mainline release checkpoint — 5 October 2026

- **Latest merged hardening:** Shared patient registration API (5 October 2026) + PR #212 → main (production commerce/pharmacy/clinical-upload hardening)
- **Latest CodeSwarm execution:** Shared patient creation endpoint (tenant-scoped, audited, idempotent) for web and mobile (5 October 2026); Production AI artifact-identity gate hardened (4 October 2026)
- **Merge commit (PR #212):** 8f1a5451c3d25c7210ed980e4667e11e6157310f
- **PR #212 head before merge:** 9b4935534345e97016c77a868a501758d460554f
- **Required engineering gates:** ✅ green on the final PR #212 head, including CodeQL, backend/mobile regression, PostgreSQL integration, staging acceptance, production-preflight contract, Firestore rules, dependency audit, and dashboard lint/test/build
- **Production AI gate improvements (4 Oct 2026):** ✅ artifact-identity fail-closed enforcement, manifest-validation test coverage added (6/6 gate tests + 179/179 full backend suite pass), error codes for observability, refactored helpers for maintainability
- **Dashboard dependency audit:** ✅ 0 reported vulnerabilities in the final npm audit
- **Clinical boundary:** software CI is green, but independent clinical validation, regulatory/privacy approval, and real-production operational evidence remain separate release gates

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

### Final dermatology hardening wave — 24 September 2026

The final engineering swarm has now been integrated as three independently validated streams:

| Stream | Evidence |
| --- | --- |
| Governed AI safety gateway | ✅ PR #159 merged; inference safety now consumes the shared AI safety gateway and model-registry integrity state |
| Clinical consent boundary | ✅ PR #159 merged; patient-linked AI assessments require active clinical-image consent when linked to media |
| Persistent mobile offline sync | ✅ PR #160 merged; replay-safe encounter updates and lesion upserts persist locally, retry with authenticated transport, and retain real 409 concurrency conflicts |
| Deployment readiness contract | ✅ PR #161 merged; readiness evaluates production PostgreSQL, explicit CORS and Firebase-auth requirements for clinical + commerce stores |
| Tenant regression matrix | ✅ PR #161 merged; cross-clinic clinical record access is covered by automated E2E tests |
| Full required CI matrix | ✅ All eight release workflows passed on PR #159, #160 and #161 heads before merge |
| Open pull requests | ℹ️ Remaining open PRs are reviewed individually; no unapproved/stale PR is claimed as merged by this README |

**Offline synchronization scope:** the persistent queue intentionally covers mutations with deterministic replay/concurrency semantics (PATCH encounter updates and POST lesion upserts). Image uploads, prescriptions and other non-idempotent workflows remain online-first rather than being retried blindly.

**Production boundary:** software engineering gates are now hardened, but independent AI clinical validation, intended-use/regulatory review, privacy governance, and deployment into a real production environment remain external evidence/operations gates.

### Clinical workflow

- **Patient registration** — shared audited API endpoint for web and mobile; tenant and clinician identity server-derived from verified Firebase claims; idempotency key prevents duplicate submissions; no patient PHI in audit logs
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

- Model registry with model name/version/artifact SHA-256 binding
- Artifact SHA-256 verification with fail-closed enforcement for unmapped model names
- Production deployment rejects any model whose artifact cannot be verified locally
- Model status/approval lifecycle with separate accountable approver requirement
- Evaluation metadata with sensitivity/specificity/PPV/NPV/AUC recording
- Subgroup metric storage by population characteristics (skin tone, age, sex, anatomical site, device)
- External-validation flagging and prospective-evaluation tracking
- Production deployment restrictions requiring validated, non-research, approved model with evidence manifest
- Confidence threshold and abstention with structured safety-gate checks
- Clinician review traceability with AI assessment accept/reject/override recording
- Formal AI validation manifest template with locked dataset, metrics CI, approval audits and external evidence URIs

## Release state

| Gate | State |
| --- | --- |
| Shared patient registration | ✅ Tenant-scoped audited API; both web/mobile clients use shared endpoint; server-derived tenant/clinician fields; idempotency-safe |
| Backend regression | ✅ Automated; all 24 patient-create tests pass |
| Mobile TypeScript | ✅ Automated |
| Expo export smoke test | ✅ Automated |
| Web dashboard lint/tests/build | ✅ Configured in pull request CI; patient-creation tests added |
| Web API client | ✅ Automated; bearer auth and idempotency-key coverage added |
| PostgreSQL integration | ✅ Automated |
| Clinical API E2E | ✅ Automated |
| Tenant isolation | ✅ Automated |
| AI-review/sign-off safety | ✅ Automated |
| AI production artifact verification | ✅ Fail-closed gate enforces local artifact SHA-256 match; manifest validation complete |
| CodeQL | ✅ Automated |
| Staging acceptance workflow | ✅ Implemented and exercised in release gating |
| Disaster-recovery drill | ✅ Implemented |
| Dependency audit | ✅ Release-gated across mobile npm, web dashboard npm, and backend pip-audit; remediable high/critical findings block; the documented upstream-unfixed Expo build-tooling advisory is tracked as an exception; full JSON reports retained as CI artifacts |
| Privacy operations | 🟡 Runbook added; clinic owners and complete export/deletion/retention automation remain outstanding |
| SBOM/provenance | ✅ Container workflow enabled |
| Independent AI clinical validation | ⏳ Not established; requires external evaluation evidence |
| Prospective clinical validation | ⏳ Not established; requires an approved protocol and real-world evidence |
| Regulatory classification/approval | ⏳ Formal assessment remains pending |
| Production cloud deployment | ⏳ Not deployed; environment setup and accountable approval remain |

See [Wave 5 Release Evidence Status](docs/WAVE5_RELEASE_EVIDENCE_STATUS.md).

### Final mainline engineering checkpoint

| Change | Mainline evidence |
| --- | --- |
| Shared patient registration endpoint | ✅ 5 October 2026; POST /api/v1/clinical/patients; tenant-scoped, audited, idempotent; web + mobile clients integrated; server-derived tenant/clinician from verified claims |
| Durable prescription dispense ledger integration | ✅ PR #155 merged |
| Concurrent dispense ownership / bounded recovery | ✅ PR #156 merged |
| Idempotent replay audit trace | ✅ PR #157 merged |
| Production AI artifact-identity gate hardening | ✅ CodeSwarm execution 4 October 2026; fail-closed for unmapped models; manifest validation test added; 179/179 tests pass |
| Production AI error observability | ✅ Structured error codes added for gate rejection paths; audit/debug clarity improved |
| Required PR CI matrix | ✅ Green on the final integration wave |
| Latest merged hardening | ✅ PR #212 merged to `main` on 4 October 2026; patient registration added 5 October 2026 |
| Open release PRs | ℹ️ Remaining PRs are not represented as approved simply because they are mergeable |
| Clinical validation / regulatory approval | ⏳ Separate external evidence and governance gates remain incomplete |

The pharmacy lifecycle is therefore retry-safe at the application ledger boundary: an already allocated or completed prescription is not re-allocated on a retry, and completed replays are explicitly auditable. This does not claim cross-database transactional atomicity between every persistence subsystem.

## Clinical workflow overview

Patient 360 → Start Clinical Encounter → History → Dermatology Examination → Lesion Capture → Assessment → AI Review (optional) → Follow-up → Sign-off

An AI result can be attached to the encounter, but it cannot silently become a signed diagnosis. Every attached AI assessment must receive an explicit clinician decision before the encounter can be signed.

See [Wave 4 Clinical Workflow](docs/WAVE4_CLINICAL_WORKFLOW.md).

## Production architecture

The production persistence boundary is PostgreSQL. The application rejects SQLite in production mode.

Durable domains include clinical encounters/lesions/consents/media metadata, billing/pharmacy, audit, and AI governance/evaluation/deployment records.

## Release pipeline

GitHub Actions provide backend regression, mobile regression, web dashboard lint/tests/build, PostgreSQL integration, CodeQL, staging acceptance, blocking dependency audits, disaster-recovery drills, and container release with SBOM/provenance. High/critical npm advisories and any Python advisory block the audit job unless a narrow, reviewed, expiring exception exists.

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
├── webapp/
│   └── src/
├── docs/
│   ├── assets/
│   ├── ai-validation/
│   ├── DEPENDENCY_SECURITY.md
│   ├── PRIVACY_OPERATIONS.md
│   ├── WAVE3_PRODUCTION_RELEASE.md
│   ├── WAVE4_CLINICAL_WORKFLOW.md
│   └── WAVE5_RELEASE_EVIDENCE_STATUS.md
├── docker-compose.staging.yml
└── .github/workflows/
```

## Local development

### One-click Windows setup

Use the repository root helper script to install both the backend Python environment and the frontend web app in one step.

```powershell
# From the repository root
powershell -ExecutionPolicy Bypass -File .\setup-dev.ps1
# or
.\setup-dev.cmd
```

This script will:

- create `backend/.venv` with Python 3.12 if it does not exist;
- install the hash-locked Python 3.12 backend requirements from `backend/requirements.lock`;
- copy `webapp/.env.example` to `webapp/.env` when needed;
- install the frontend dependencies from `webapp/package.json` with `npm ci` when a lockfile is present.

### Backend

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

Optional validation:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
pytest -q tests
python -m compileall -q .
```

**Note on Windows test environments:** Backend test suites execute successfully with all assertions passing. On Windows, temporary SQLite database cleanup in conftest may fail with a PermissionError due to file locking; this does not affect test correctness and is a known pytest + Windows + temporary-file interaction. The test assertions themselves complete successfully before cleanup begins.

### Frontend web app

```powershell
cd webapp
npm run dev -- --host 0.0.0.0
```

Production-style frontend validation:

```powershell
cd webapp
npm run lint
npm test -- --run
npm run build
```

Backend runtime dependencies install from the committed, hash-pinned Python 3.12 lock. Refresh both backend locks with the commands in [Dependency security](docs/DEPENDENCY_SECURITY.md) when updating dependencies.

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

Production controls include Firebase authentication, server-side RBAC, tenant-aware authorization, consent enforcement for clinical media, decoded/MIME-verified clinical image uploads, signed server-mediated object uploads, no client-side Cloudinary secret, rate limiting on privileged/high-cost endpoints, captured-event/payment-status validation plus idempotent settlement, canonical pharmacy expiry + FEFO ordering, prescription/patient linkage enforcement, hash-chained audit records, fail-closed production CORS, PostgreSQL production enforcement, a privacy-policy readiness gate, CodeQL, dashboard/backend/mobile dependency gates, and SBOM/provenance-enabled container releases. See [SECURITY.md](SECURITY.md) for private vulnerability reporting and [Privacy operations](docs/PRIVACY_OPERATIONS.md) for patient-data request and incident procedures.

## Dependency security

The dependency audit workflow produces machine-readable reports for mobile, web dashboard, runtime Python, and CI Python dependencies. High/critical npm findings and all Python findings block the audit workflow unless covered by an owner-assigned exception with an expiry date. The currently documented Expo build-tooling exceptions are advisory-specific, time-limited, and do not represent dashboard runtime vulnerabilities. See [Dependency security](docs/DEPENDENCY_SECURITY.md) and [production dependency findings](docs/PRODUCTION_DEPENDENCY_SECURITY.md).

## Clinical / regulatory boundary

The platform does not claim regulatory approval or clinical validation.

For India, the release review should assess the Medical Devices Rules, 2017; current CDSCO guidance applicable to Medical Device Software; Digital Personal Data Protection Act/Rules obligations; institutional privacy/consent/retention/incident controls; pharmacy requirements; payment-provider requirements; and professional/clinical governance.

Official references:

- CDSCO Medical Device & Diagnostics: <https://www.cdsco.gov.in/opencms/opencms/en/Medical-Device-Diagnostics/>
- CDSCO Medical Devices Rules: <https://cdsco.gov.in/opencms/opencms/en/Acts-and-rules/Medical-Devices-Rules/>
- MeitY DPDP Rules 2025: <https://www.meity.gov.in/documents/act-and-policies/digital-personal-data-protection-rules-2025-gDOxUjMtQWa>

## AI validation release package

Use `docs/ai-validation/release-manifest.template.json` and validate a completed evidence package with:

```bash
python backend/scripts/validate_ai_release_manifest.py path/to/release-manifest.json
```

Do **not** enter estimated or invented clinical performance values. Structural validation is not proof of scientific validity. Production AI stays disabled by default and requires an approved evidence manifest whose model name, version, and artifact digest match the active deployment.

Minimum evidence includes frozen model artifact, locked test set, sensitivity/specificity, PPV/NPV where appropriate, ROC-AUC/PR-AUC where appropriate, calibration, subgroup analysis, OOD behavior, abstention performance, clinician override analysis, independent/external validation and accountable approval.

## Important limitations

- AI screening is assistive and cannot replace dermatologist assessment, histopathology or other indicated investigation.
- The research model is not clinically validated for routine patient care.
- Technical CI success is not clinical validation.
- A staging workflow is not the same as a live production deployment.
- Regulatory/privacy status depends on intended use, claims, jurisdiction and the organization's actual controls.

## License

See the repository for the applicable project licensing and dependency notices.

## Deployment hardware budget (India)

Indicative planning ranges; verify vendor quotations before procurement.

| Tier | Typical configuration | Approx. one-time budget |
| --- | --- | ---: |
| Development | Existing 8 GB SSD laptop/workstation | ₹0 incremental |
| Small clinic | 4+ cores, 8–16 GB RAM, 256–512 GB SSD, UPS | ₹40,000–₹55,000 |
| Recommended clinic | 8 cores, 16 GB RAM, 512 GB NVMe, UPS + backup storage | ₹70,000–₹95,000 |
| AI-ready local inference | 8+ cores, 32 GB RAM, 1 TB NVMe, NVIDIA GPU with 8–12+ GB VRAM | ₹1.3–₹2.0 lakh+ |

Recommended production baseline: Ubuntu 24.04 LTS, PostgreSQL 16, Python 3.12, Node.js 22 LTS and Docker/Compose. Use 32 GB RAM and a supported GPU only when local AI inference is independently validated for the intended workload.

## Indicative cloud deployment budget

Monthly planning ranges for a small-to-standard clinic; actual bills vary by region, storage, traffic, backups, managed services and GPU usage.

| Deployment | Approx. monthly budget |
| --- | ---: |
| Development / low traffic | ₹0–₹1,500 |
| Small clinic | ₹3,000–₹6,000 |
| Standard clinic | ₹6,000–₹12,000 |
| Multi-clinic | ₹15,000–₹35,000 |
| AI/GPU-enabled | ₹35,000–₹80,000+ |

A typical production stack consists of an application compute service, managed PostgreSQL, object storage/backups, monitoring and TLS. GPU inference should be treated as a separate cost center and enabled only for validated workloads.

These figures are **budgetary estimates, not guaranteed cloud prices**. Obtain current provider quotations for the deployment region before committing.
