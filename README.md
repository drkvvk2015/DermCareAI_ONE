

## Tiered clinical AI activation — 4 October 2026

DermCareAI now separates **Clinical AI Assist** from high-consequence diagnostic AI. The production application is a **physician-final Clinical AI Copilot**: it provides suggestions and evidence-oriented support only. It does not make the final diagnosis, prescribe, place orders, sign an encounter, or silently modify a signed record. The treating physician remains the sole clinical decision-maker.

Production configuration:

```text
APP_ENV=production
ENABLE_CLINICAL_ASSIST_AI=true
ENABLE_GENERATIVE_CLINICAL_ASSIST=false
ENABLE_MEDGEMMA=false
AI_DIAGNOSTIC_MODE=disabled
```

The optional generative-assist lane is separately controlled and requires an immutable MedGemma revision in production. Diagnostic inference is intentionally unavailable in this application; an environment variable cannot activate it. Any future diagnostic evaluation must be a separate governed deployment with its own evidence, validation, privacy/security, rollback, and accountable clinical approvals.

Clinical AI Copilot UI language:

> **Suggestions only. Verify all information and make the final clinical decision.**

## Mainline release checkpoint — 4 October 2026

- **Latest merged hardening:** PR #212 → main
- **Merge commit:** 8f1a5451c3d25c7210ed980e4667e11e6157310f
- **PR #212 head before merge:** 9b4935534345e97016c77a868a501758d460554
- **Required engineering gates:** ✅ green on the final PR #212 head, including CodeQL, backend/mobile regression, PostgreSQL integration, staging acceptance, production-preflight contract, Firestore rules, dependency audit, and dashboard lint/test/build
- **Dashboard dependency audit:** ✅ 0 reported vulnerabilities in the final npm audit
- **Clinical boundary:** software CI is green, but independent clinical validation, regulatory/privacy approval, and real-production operational evidence remain separate release gates

## System at a glance

```text
Clinician
   │
   ▼
Patient 360
