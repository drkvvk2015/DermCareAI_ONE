# Wave 5 — Release Evidence Status

Updated: 2026-10-07

This document separates automated software evidence from clinical, regulatory and deployment evidence that requires real-world data, environments or accountable human review.

| Area | Current state | Evidence |
|---|---|---|
| Backend regression | PASS | GitHub Actions |
| PWA/Capacitor client build | PASS | GitHub Actions |
| Web dashboard lint/tests/build | GATE CONFIGURED | Pull request workflow includes the independent Vite dashboard |
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
| Dependency audit | PASS in current release gating | Webapp npm + Python runtime/CI audits; high/critical npm and any Python findings block unless a narrow, reviewed, expiring exception exists |
| Python dependency resolution | LOCKED | Python 3.12 runtime and CI graphs pin transitive versions and hashes |
| Native packaging | PASS | Capacitor Android/iOS projects are generated and synced by CI from the canonical PWA |
| SBOM/provenance | ENABLED | Container release workflow |
| Independent clinical validation | NOT ESTABLISHED | Requires locked test set and external/independent validation; no results are recorded here |
| Prospective clinical evaluation | NOT ESTABLISHED | Requires approved clinical protocol and real-world evidence; no results are recorded here |
| AI calibration/subgroup/OOD evidence | NOT ESTABLISHED | Evidence manifest and actual evaluation results required |
| Regulatory classification | PENDING FORMAL ASSESSMENT | Depends on intended use, claims and deployment |
| Production cloud deployment | NOT DEPLOYED | Requires organization secrets, infrastructure and accountable release approval |
| Privacy operational program | PARTIAL | [Operational runbook](PRIVACY_OPERATIONS.md) added; clinic owners must approve retention, export, deletion, and incident processes. Automated full export/deletion/retention remains unimplemented |
| Guardrailed CI auto-repair proposals | ENABLED | Failure classification + repair evidence; human-reviewed merge required |

## Clinical AI evidence-gate hardening — 4 October 2026

The repository now enforces the 15-item clinical-AI activation contract in software: production eligibility requires a schema-v2 evidence manifest, exact model/version/SHA-256 binding, locked-dataset provenance, quantitative metrics with confidence intervals, completed calibration/subgroup/OOD/abstention/clinician-review/external-validation evidence, traceable accountable approvals, governance review records, and staging/rollback evidence. The gate is deliberately fail-closed when the evidence package is absent or incomplete.

This does **not** create clinical evidence. The current repository still has no completed production evidence manifest, and clinical AI remains disabled until the real artifact, validation dataset/results, accountable approvals, and applicable regulatory/privacy reviews exist.

For India, the compliance review should use the current CDSCO Medical Device Software guidance and applicable MDR-2017 framework, plus the notified DPDP Rules 2025 and their staged commencement timeline. See the official references linked in this document and the production evidence checklist.

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

**Software release gate:** automated CI + staging + DR + security evidence, including backend, mobile, dashboard, payment/FEFO/prescription safety tests and dependency audit enforcement. The current v5.1 engineering release candidate is gated by PR CI and staging; environment-specific production deployment remains separate.

**Clinical release gate:** independent clinical/AI evidence + intended-use review + accountable clinician approval.

**Regulatory/privacy gate:** jurisdiction-specific assessment + institutional approval + documented operational controls.

## Tiered Clinical AI — engineering implementation

| Capability | State | Safety boundary |
|---|---|---|
| Structured differential assist | ENABLED BY EXPLICIT FEATURE FLAG | Assistive only; not a diagnosis; clinician verification required |
| Clinical image-quality assist | ENABLED BY EXPLICIT FEATURE FLAG | Requires patient-linked clinical-image consent; candidate segmentation is not validated diagnosis |
| Generative image assist | SEPARATE OPT-IN | Production requires immutable model revision; output remains preliminary assistive content |
| Diagnostic model | EVIDENCE-GATED | Disabled/shadow only until completed evidence package and accountable approvals pass |

The current release exposes Clinical AI Assist at the backend API boundary only. No mobile encounter workflow is claimed in this release. Clinical AI remains suggestion-only; the existing AI-review/sign-off gate remains authoritative for any model assessment attached to the clinical record.
