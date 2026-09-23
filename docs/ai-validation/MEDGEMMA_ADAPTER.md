# MedGemma adapter — DermCareAI

This adapter adds an opt-in research integration for google/medgemma-1.5-4b-it.

## Safety boundary
- Disabled by default (ENABLE_MEDGEMMA=false).
- Output is preliminary assistive content only.
- The adapter cannot sign a diagnosis or prescribe treatment.
- A clinician must independently verify any output before it is attached to a clinical record.
- Clinical deployment requires a frozen artifact, intended-use definition, independent validation, calibration/OOD evidence, subgroup analysis, and applicable regulatory/privacy review.

## Runtime
The existing backend already includes transformers and torch. The adapter lazily imports the model stack so the normal test suite does not download model weights.

Environment:

    ENABLE_MEDGEMMA=false
    MEDGEMMA_MODEL_ID=google/medgemma-1.5-4b-it
    MEDGEMMA_REVISION=<optional pinned revision>
    MEDGEMMA_MAX_NEW_TOKENS=256
    MEDGEMMA_TEMPERATURE=0.0

Do not enable the model in production until the project's AI release manifest is complete and approved.

Google documents MedGemma 1.5 4B as a starting point for downstream healthcare applications and explicitly requires application-specific validation/adaptation; its outputs are not intended to directly inform diagnosis, management or treatment without further development and verification.