# DermCareAI Independent AI Clinical Validation Protocol

**Status:** Protocol package ready — execution and independent sign-off are required  
**Scope:** Dermatology image-screening decision support only  
**Clinical boundary:** The current embedded HAM10000 model remains research fallback and must not be represented as clinically validated by this repository.

## 1. Purpose

This protocol defines the evidence required before DermCareAI's image-screening component may support any clinical performance claim.

The protocol is deliberately independent of the software engineering CI gate. Passing automated tests does not establish clinical validity.

## 2. Intended-use lock

Before data analysis begins, the accountable clinical/research team must freeze:

- target population;
- clinical setting;
- intended decision-support task;
- target condition/classification labels;
- minimum/maximum image-quality requirements;
- referral/escalation behavior;
- model version and artifact SHA-256;
- software version;
- primary and secondary endpoints.

Any change after lock requires documented protocol deviation and versioned approval.

## 3. Evaluation dataset

Create a frozen dataset manifest containing:

- case identifier;
- acquisition site;
- image identifier/hash;
- reference-standard label;
- reference-standard source;
- inclusion/exclusion status;
- demographic/subgroup variables permitted by the study protocol;
- acquisition/device metadata when relevant;
- train/validation/test provenance.

No patient-identifying data should be committed to the repository.

## 4. Reference standard

Define the reference standard before unblinding model outputs. The study record should specify the responsible clinical experts, adjudication procedure, disagreement resolution, and any histopathology or other definitive evidence used.

## 5. Statistical analysis plan

Pre-specify:

- primary sensitivity and specificity endpoints;
- confidence interval method;
- PPV/NPV interpretation for the target prevalence;
- ROC-AUC and PR-AUC where appropriate;
- calibration assessment;
- subgroup analyses;
- missing-data handling;
- abstention/low-quality-image analysis;
- out-of-distribution analysis;
- multiplicity handling where relevant.

Do not enter estimated results into the release manifest.

## 6. Independence requirement

The final analysis must be performed or independently reproduced by an evaluator who is not solely responsible for developing the model/software.

The signed evidence package should identify:

- evaluator;
- institution/site;
- analysis version;
- locked dataset digest;
- model artifact digest;
- statistical code revision;
- date;
- conflicts/independence statement.

## 7. Clinician review analysis

Record the relationship between model suggestions and clinician decisions, including:

- accept;
- reject;
- override;
- abstention;
- unsafe/ambiguous cases;
- clinically significant discordance.

## 8. Release package

Store only non-identifying evidence and hashes in the repository. The release package should contain:

1. frozen model artifact hash;
2. frozen dataset manifest/hash;
3. signed protocol;
4. statistical analysis plan;
5. analysis output with confidence intervals;
6. subgroup/OOD/abstention outputs;
7. clinician override analysis;
8. independent evaluator statement;
9. accountable approval;
10. versioned release manifest.

## 9. Stop/release criteria

Do not enable a clinical performance claim when required evidence is missing, contradictory, materially degraded, or not independently reviewed.

A failed or inconclusive validation result must remain visible in the evidence record; it must not be replaced by a green status without new evidence.

## 10. Repository boundary

This document completes the engineering preparation for independent validation. It does not fabricate or substitute for clinical study execution, ethics/institutional governance, independent evaluation, or regulatory review.
