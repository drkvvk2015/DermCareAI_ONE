# Clinical AI Go-Live Checklist

## Safe production activation

Set:

```text
APP_ENV=production
ENABLE_CLINICAL_ASSIST_AI=true
ENABLE_GENERATIVE_CLINICAL_ASSIST=false
ENABLE_MEDGEMMA=false
```

Verify:

- Firebase authentication is enforced.
- organization and clinic claims are present.
- PostgreSQL is the production persistence layer.
- patient-linked clinical-image review requires active consent.
- audit logging is enabled.
- Clinical AI Copilot visibly states: **Suggestions only. Verify all information and make the final clinical decision.**
- diagnostic AI is unavailable through the production application.
- no research model is exposed through the diagnostic endpoint.
- `/predict` cannot execute clinical diagnostic inference.

## Optional generative assist

Only enable after the organization explicitly approves the use case:

```text
ENABLE_CLINICAL_ASSIST_AI=true
ENABLE_GENERATIVE_CLINICAL_ASSIST=true
ENABLE_MEDGEMMA=true
MEDGEMMA_MODEL_ID=<approved-model-id>
MEDGEMMA_REVISION=<immutable-pinned-revision>
```

The production adapter rejects an unpinned revision. Patient-linked image review requires clinical-image consent. Generative output remains suggestion-only and requires clinician verification.

## Diagnostic development/evaluation boundary

The application does not expose an environment-variable switch for diagnostic inference. Any future diagnostic evaluation must use a separately governed deployment and complete the schema-v2 evidence manifest, exact model-artifact identity, validation evidence, accountable approvals, privacy/security review, staging/rollback evidence, and applicable regulatory/governance requirements before any patient-facing use.

## Clinical safety

- No autonomous diagnosis.
- No autonomous prescribing or treatment execution.
- No autonomous orders.
- No automatic modification of signed encounters.
- No silent model or policy promotion.
- Clinician remains the final decision-maker.
