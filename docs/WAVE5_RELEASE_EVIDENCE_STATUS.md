# Wave 5 — Release Evidence Status

Updated: 2026-09-24

This document separates automated software evidence from clinical, regulatory and deployment evidence that requires real-world data, environments or accountable human review.

| Area | Current state | Evidence |
|---|---|---|
| Backend regression | PASS | GitHub Actions |
| Mobile TypeScript/export | PASS | GitHub Actions |
| CodeQL | PASS | GitHub Actions |
| PostgreSQL integration | PASS | PostgreSQL staging gate |
| Clinical API workflow | PASS | Clinical E2E tests |
| Dermatology Wave 2 API integration | PASS | Integrated router registration + regression tests |
| AI media/lesion tenant provenance | HARDENED | Tenant-scoped resource lookup + cross-tenant rejection tests |
| Clinical media integrity / retention | PASS | Deterministic metadata validation + regression tests |
| Encounter sign-off safety | PASS | Pending-AI review gate |
| Tenant isolation | PASS | Clinical E2E tests |
| Backup/restore automation | READY | Monthly DR workflow |
| Staging acceptance | PASS in current release gating | Docker staging workflow; current hotfix gate passed build, schema init and clinical acceptance |
| Dependency audit | PASS / INVENTORY ENABLED | Current release gate + machine-readable audit artifact |
| SBOM/provenance | ENABLED | Container release workflow |
| Independent clinical validation | 🟡 EVIDENCE PACKAGE READY | Protocol + release manifest are now versioned; independent execution/sign-off still required |
| Prospective clinical evaluation | 🟡 PROTOCOL READY | Prospective protocol, safety monitoring and end-of-study evidence structure are versioned; real-world execution still required |
| AI calibration/subgroup/OOD evidence | 🟡 EVIDENCE PACKAGE READY | Pre-specified evidence fields and protocol are versioned; populate only from actual locked-study results |
| Regulatory classification | 🟡 ASSESSMENT DOSSIER READY | India regulatory/privacy assessment checklist is versioned; formal accountable classification/review remains required |
| Production cloud deployment | 🟢 DEPLOYMENT PACKAGE READY | Production runbook, security gate and activation record are versioned; actual cloud activation requires organization-owned infrastructure/secrets/approval |
| Privacy operational program | 🟡 OPERATIONAL PACKAGE READY | Technical controls plus deployment/privacy assessment structure are versioned; organization-specific SOPs and approvals remain required |
| Guardrailed CI auto-repair proposals | ENABLED | Failure classification + repair evidence; human-reviewed merge required |


## Newly completed release-preparation packages — 24 September 2026

| Package | Location |
|---|---|
| Independent AI clinical validation protocol | [docs/AI_CLINICAL_VALIDATION_PROTOCOL.md](AI_CLINICAL_VALIDATION_PROTOCOL.md) |
| Prospective clinical evaluation protocol | [docs/PROSPECTIVE_CLINICAL_EVALUATION_PROTOCOL.md](PROSPECTIVE_CLINICAL_EVALUATION_PROTOCOL.md) |
| India regulatory/privacy assessment dossier | [docs/INDIA_REGULATORY_ASSESSMENT.md](INDIA_REGULATORY_ASSESSMENT.md) |
| Production deployment runbook | [docs/PRODUCTION_DEPLOYMENT_RUNBOOK.md](PRODUCTION_DEPLOYMENT_RUNBOOK.md) |
| AI validation manifest template hardened against false-green defaults | [docs/ai-validation/release-manifest.template.json](ai-validation/release-manifest.template.json) |

These packages close the repository-side preparation work. They do not manufacture clinical outcomes, regulatory clearance, ethics approval, or cloud infrastructure that does not yet exist.

## Clinical / AI release evidence that must not be fabricated

The repository intentionally does **not** claim:

- clinical sensitivity/specificity;
- external validation;
- calibration performance;
- subgroup parity;
- prospective safety;
- regulatory clearance;
- production privacy compliance certification.

Those claims require actual evidence, not software tests.

## Minimum AI evidence package

Before enabling any diagnostic or high-consequence clinical claim, provide:

1. frozen model artifact and SHA-256;
2. frozen test-set manifest;
3. dataset provenance and inclusion/exclusion criteria;
4. pre-specified primary and secondary metrics;
5. sensitivity and specificity with confidence intervals;
6. PPV/NPV for the intended prevalence setting;
7. ROC-AUC and PR-AUC where appropriate;
8. calibration assessment;
9. subgroup analysis;
10. out-of-distribution / low-quality image behavior;
11. abstention performance;
12. clinician override analysis;
13. independent or external validation;
14. locked approval record;
15. deployment and rollback evidence.

## India regulatory/privacy references

For an India deployment, the formal review should include the current CDSCO Medical Devices Rules framework and the CDSCO guidance on Medical Device Software, together with the Digital Personal Data Protection Act / Rules and the actual clinic's institutional, professional and pharmacy requirements.

Official sources:

- CDSCO medical device and diagnostics guidance: https://www.cdsco.gov.in/opencms/opencms/en/Medical-Device-Diagnostics/
- CDSCO Medical Devices Rules, 2017: https://cdsco.gov.in/opencms/opencms/en/Acts-and-rules/Medical-Devices-Rules/
- MeitY Digital Personal Data Protection Rules, 2025: https://www.meity.gov.in/documents/act-and-policies/digital-personal-data-protection-rules-2025-gDOxUjMtQWa

The CDSCO site currently lists a guidance document on Medical Device Software under MDR-2017 dated 21 July 2026. The DPDP Rules 2025 were notified in November 2025 with a staged commencement schedule.

## Release decision

A build can be technically deployable while still being clinically or regulatorily unapproved. Keep these gates separate.

**Software release gate:** automated CI + staging + DR + security evidence. The current v5.1 engineering promotion is complete in `main`; environment-specific production deployment remains separate.

**Clinical release gate:** independent clinical/AI evidence + intended-use review + accountable clinician approval.

**Regulatory/privacy gate:** jurisdiction-specific assessment + institutional approval + documented operational controls.
