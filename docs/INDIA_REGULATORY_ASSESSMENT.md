# India Regulatory & Privacy Assessment — DermCareAI

**Status:** Assessment dossier ready — formal accountable classification/review required  
**Jurisdiction:** India  
**Last reviewed:** 24 September 2026

## 1. Purpose

Provide a structured assessment package for determining whether the deployed DermCareAI configuration, intended use and claims fall within applicable medical-device software, clinical-investigation, privacy, pharmacy, payment and institutional requirements.

This document is a decision-support checklist, not legal advice or a regulatory approval.

## 2. Intended-use and claims lock

Before regulatory classification, freeze the exact claims made in:

- application UI;
- onboarding;
- model output;
- marketing material;
- clinician documentation;
- API/documentation;
- deployment configuration.

Avoid claims that imply diagnosis or clinical performance unless supported by the corresponding evidence.

## 3. CDSCO / medical-device software review

Assess against the current Medical Devices Rules, 2017 and current CDSCO guidance applicable to Medical Device Software, including:

- whether the intended use constitutes a medical-device software function;
- applicable risk classification;
- manufacturer/legal-manufacturer responsibilities;
- quality-management requirements;
- technical documentation;
- software lifecycle, verification and validation evidence;
- clinical investigation/evaluation requirements where applicable;
- licensing/import/manufacture obligations;
- post-market obligations.

The classification must be made for the actual intended use and claims rather than inferred only from the technology used.

## 4. Clinical investigation/evaluation

Determine whether the intended deployment requires clinical-investigation or other formal clinical evidence under the applicable regulatory route and institutional governance.

Attach the final independent/clinical validation package separately.

## 5. Privacy and personal-data governance

Assess the actual deployment against applicable privacy requirements, including the Digital Personal Data Protection Act, 2023 and the notified Digital Personal Data Protection Rules, 2025, together with institutional policy and contractual obligations.

Document:

- purpose and lawful/approved processing basis;
- consent/notice workflow where required;
- roles and responsibilities;
- retention/deletion;
- access and correction/rights processes;
- breach/incident handling;
- processor/vendor controls;
- cross-border/data-transfer considerations where relevant;
- audit and logging;
- data minimisation.

The DPDP Rules were notified in November 2025 with staged commencement provisions; the live deployment must be assessed against the provisions in force for the relevant date and processing activity.

## 6. Pharmacy, billing and payments

Separate assessments should cover:

- pharmacy dispensing and applicable state/institutional requirements;
- billing and record retention;
- payment-provider contracts and webhook/signature controls;
- financial reconciliation and refund workflows.

## 7. Accountability

The final assessment record should identify:

- accountable organization;
- manufacturer/legal manufacturer as applicable;
- responsible clinical lead;
- regulatory/legal reviewer;
- privacy lead;
- deployment approver;
- date/version of the assessment;
- conclusion and conditions.

## 8. Evidence index

Link these artifacts before a production clinical claim:

- AI clinical validation manifest;
- prospective evaluation protocol/report where applicable;
- software V&V evidence;
- risk management file;
- cybersecurity evidence;
- privacy/retention SOPs;
- incident response;
- backup/restore/DR evidence;
- release SBOM/provenance;
- deployment configuration;
- applicable licences/registrations/approvals.

## 9. Current repository status

Engineering preparation is complete enough to support formal review. The repository must not represent this document as regulatory clearance or a final classification decision.

## Official references

- CDSCO Medical Devices and Diagnostics: https://www.cdsco.gov.in/opencms/opencms/en/Medical-Device-Diagnostics/
- Medical Devices Rules, 2017: https://cdsco.gov.in/opencms/resources/UploadCDSCOWeb/2022/m_device/Medical%20Devices%20Rules%2C%202017.pdf
- CDSCO Medical Device Software guidance listing: https://www.cdsco.gov.in/opencms/opencms/en/Medical-Device-Diagnostics/
- MeitY DPDP Rules 2025: https://www.meity.gov.in/documents/act-and-policies/digital-personal-data-protection-rules-2025-gDOxUjMtQWa
