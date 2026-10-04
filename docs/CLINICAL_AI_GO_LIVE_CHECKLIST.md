# Clinical AI Go-Live Checklist

## Safe production activation

Set:

```text
APP_ENV=production
ENABLE_CLINICAL_ASSIST_AI=true
ENABLE_GENERATIVE_CLINICAL_ASSIST=false
ENABLE_MEDGEMMA=false
AI_DIAGNOSTIC_MODE=disabled
```

Verify:

- Firebase authentication is enforced.
- organization and clinic claims are present.
- PostgreSQL is the production persistence layer.
- patient-linked clinical-image review requires active consent.
- audit logging is enabled.
- Clinical Assist UI displays "not a diagnosis" and "clinician verification required".
- diagnostic AI remains unavailable.
- no research model is exposed through the diagnostic endpoint.

## Optional generative assist

Only enable after the organization explicitly approves the use case:

```text
ENABLE_CLINICAL_ASSIST_AI=true
ENABLE_GENERATIVE_CLINICAL_ASSIST=true
ENABLE_MEDGEMMA=true
MEDGEMMA_MODEL_ID=<approved-model-id>
MEDGEMMA_REVISION=<immutable-pinned-revision>
```

The production adapter rejects an unpinned revision. Patient-linked image review requires clinical-image consent.

## Diagnostic activation

Do not set:

```text
AI_DIAGNOSTIC_MODE=clinical
```

until the completed schema-v2 evidence manifest is mounted at:

```text
/var/lib/dermcareai/ai/release-manifest.json
```

or an explicitly configured controlled path, and the exact model artifact hash matches the approved evidence package and model-governance record.

## Clinical safety

- No autonomous diagnosis.
- No autonomous prescribing.
- No automatic modification of signed encounters.
- No silent model or policy promotion.
- Clinician remains the final decision-maker.
