# DermCareAI Clinical AI Production Activation

## Production strategy

DermCareAI uses a strict physician-final Clinical AI Copilot boundary. The production application exposes assistive suggestions only; diagnostic inference is not an application-level production capability.

### Lane A — Clinical Assist

This lane is intended for clinician-support functions that do not autonomously diagnose, prescribe, order, sign, or modify a signed encounter.

Available capabilities:

- structured differential-support suggestions from deterministic clinical rules;
- clinical image-quality assessment;
- candidate-region measurement for clinician review;
- optional generative image description through the separately gated MedGemma adapter.

All outputs are explicitly marked as assistive, require clinician verification, and remain outside autonomous diagnosis/prescribing.

Enable the assistive lane with:

```text
APP_ENV=production
ENABLE_CLINICAL_ASSIST_AI=true
```

### Lane B — Controlled evaluation

The repository does not expose a live-patient diagnostic shadow switch. Diagnostic evaluation must be a separate, approved evaluation deployment with explicit data-governance, privacy, reference-label, clinical-validation, and rollback controls. It must not be activated by changing a production application environment variable.

### Lane C — Governed diagnostic development/evaluation boundary

The application policy deliberately has **no executable diagnostic activation switch**. Diagnostic inference cannot be enabled through application configuration.

If a future diagnostic capability is developed, it must be delivered as a separately governed deployment artifact outside this application-level Clinical AI Assist lane. That deployment must independently satisfy the complete evidence package, exact artifact binding, external/clinical validation, accountable clinical approvals, privacy/security review, staging/rollback evidence, applicable regulatory requirements, and documented release decision before any patient-facing use.

## Generative assist

Generative clinical image review is separately gated:

```text
ENABLE_CLINICAL_ASSIST_AI=true
ENABLE_GENERATIVE_CLINICAL_ASSIST=true
ENABLE_MEDGEMMA=true
MEDGEMMA_MODEL_ID=...
MEDGEMMA_REVISION=<immutable-pinned-revision>
```

In production, an unpinned MedGemma revision is rejected. Generative output is assistive content only and cannot sign a diagnosis, prescribe treatment, place orders, or modify a signed record.

Clinical-image consent is required before patient-linked image review.

## UI / workflow requirements

Present assistive output with the visible safety label:

> **Clinical AI Copilot — Suggestions only. Verify all information and make the final clinical decision.**

The clinician must be able to accept, modify, or reject AI-supported content. AI-supported review remains subject to the existing encounter sign-off gate.

## What remains locked

The following are not enabled merely by turning on Clinical Assist:

- autonomous diagnosis;
- autonomous treatment execution or prescribing;
- autonomous orders;
- automatic changes to signed records;
- silent model promotion;
- production use of an unvalidated diagnostic artifact;
- patient-facing diagnostic inference through `/predict`.

The physician-final safety boundary is authoritative for the production application.
