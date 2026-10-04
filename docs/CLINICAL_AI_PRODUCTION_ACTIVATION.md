# DermCareAI Clinical AI Production Activation

## Production strategy

DermCareAI uses tiered clinical-AI activation.

### Lane A — Clinical Assist

This lane is intended for clinician-support functions that do not autonomously diagnose, prescribe, or sign an encounter.

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
AI_DIAGNOSTIC_MODE=disabled
```

### Lane B — Diagnostic model shadow mode

Use:

```text
AI_DIAGNOSTIC_MODE=shadow
```

only for controlled evaluation where predictions are not presented as clinical decisions. Shadow-mode evidence must be handled under the clinic's approved evaluation protocol and privacy controls.

### Lane C — Diagnostic clinical mode

Use:

```text
AI_DIAGNOSTIC_MODE=clinical
```

only after the strict evidence manifest, exact artifact binding, independent validation, accountable approvals, staging/rollback evidence, and applicable regulatory/privacy review all pass. The backend independently re-checks the completed evidence package and artifact hash.

## Generative assist

Generative clinical image review is separately gated:

```text
ENABLE_CLINICAL_ASSIST_AI=true
ENABLE_GENERATIVE_CLINICAL_ASSIST=true
ENABLE_MEDGEMMA=true
MEDGEMMA_MODEL_ID=...
MEDGEMMA_REVISION=<immutable-pinned-revision>
```

In production, an unpinned MedGemma revision is rejected. Generative output is preliminary assistive content only and cannot sign a diagnosis or prescribe treatment.

Clinical-image consent is required before patient-linked image review.

## UI / workflow requirements

Present assistive output with a visible safety label:

> AI Clinical Assist — not a diagnosis. Clinician verification required.

The clinician must be able to accept, modify, or reject AI-supported content. AI-supported review remains subject to the existing encounter sign-off gate.

## What remains locked

The following are not enabled merely by turning on Clinical Assist:

- autonomous diagnosis;
- autonomous treatment recommendations;
- autonomous prescribing;
- silent model promotion;
- production use of an unvalidated diagnostic artifact.

The diagnostic evidence gate remains authoritative.
