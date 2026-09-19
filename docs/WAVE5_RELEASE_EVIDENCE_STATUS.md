# Wave 5 — Release Evidence Status

Updated: 2026-09-19

This document separates automated software evidence from clinical, regulatory and deployment evidence that requires real-world data, environments or accountable human review.

| Area | Current state | Evidence |
|---|---|---|
| Backend regression | PASS | GitHub Actions |
| Mobile TypeScript/export | PASS | GitHub Actions |
| CodeQL | PASS | GitHub Actions |
| PostgreSQL integration | PASS | PostgreSQL staging gate |
| Clinical API workflow | PASS | Clinical E2E tests |
| Encounter sign-off safety | PASS | Pending-AI review gate |
| Tenant isolation | PASS | Clinical E2E tests |
| Backup/restore automation | READY | Monthly DR workflow |
| Staging acceptance | READY | Docker staging workflow |
| Dependency audit | INVENTORY ENABLED | Weekly/PR audit artifact |
| SBOM/provenance | ENABLED | Container release workflow |
| Independent clinical validation | NOT ESTABLISHED | Requires locked test set and external/independent validation |
| Prospective clinical evaluation | NOT ESTABLISHED | Requires approved clinical protocol and real-world evidence |
| AI calibration/subgroup/OOD evidence | NOT ESTABLISHED | Evidence manifest required |
| Regulatory classification | PENDING FORMAL ASSESSMENT | Depends on intended use, claims and deployment |
| Production cloud deployment | READY FOR ENVIRONMENT SETUP | Requires organization secrets, infrastructure and accountable release approval |
| Privacy operational program | PARTIAL | Technical controls exist; organizational policies and rights workflows still require implementation |

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

**Software release gate:** automated CI + staging + DR + security evidence.

**Clinical release gate:** independent clinical/AI evidence + intended-use review + accountable clinician approval.

**Regulatory/privacy gate:** jurisdiction-specific assessment + institutional approval + documented operational controls.
