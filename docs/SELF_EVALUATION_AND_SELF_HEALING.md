# DermCareAI automatic evaluation, updates and self-healing

## Safety boundary

DermCareAI is a clinical support application. Automated maintenance must never silently promote a new model or change a clinical recommendation policy based only on live traffic.

The system therefore separates three concerns:

1. **Automatic evaluation** — CI validates Python syntax, safety-gate logic, prediction payloads, classification metrics, TypeScript and an Expo export smoke test.
2. **Automatic updates** — Dependabot opens dependency update pull requests. CI must pass before a dependency update is eligible for normal review/merge.
3. **Self-healing** — the backend can reload its configured local models after a transient inference/runtime failure. It does not download arbitrary models, overwrite model binaries, or promote a new model automatically.

## Runtime safety controls

- Image MIME/type and upload-size validation.
- Basic resolution, luminance and contrast/blur quality gate.
- Conservative confidence threshold with an explicit `Uncertain / Needs Clinical Review` abstention state.
- Distinction between a melanoma risk signal and a confirmed diagnosis.
- `/health` endpoint exposing service and model-file state.
- `/self-heal` endpoint for controlled model-service reload.
- Bounded retry after transient inference failure.
- Model SHA-256 reporting for deployment provenance.
- Configurable `CORS_ORIGINS`, `MIN_CONFIDENCE`, `MAX_IMAGE_BYTES`, `MODEL_DIR` and `APP_VERSION` environment variables.

## Automatic evaluation

`backend/evaluation.py` provides:

- prediction payload validation;
- confidence normalization and range enforcement;
- abstention/safety-gate logic;
- accuracy, macro-sensitivity and macro-specificity calculation.

`backend/tests/test_evaluation.py` contains regression tests for these controls.

## CI

`.github/workflows/continuous-evaluation.yml` runs on pushes, pull requests, scheduled maintenance, and manual dispatch. It performs lightweight backend tests without requiring model weights and performs mobile TypeScript/Expo checks.

Model weight binaries are intentionally not committed to Git. Deployment should provide them from controlled artifact storage and pin their checksums.

## Recommended next-stage MLOps

For clinical validation, add a versioned evaluation dataset with locked train/validation/test splits and subgroup analysis by skin tone, age, sex, anatomical site, acquisition device and imaging modality. Require predefined acceptance criteria and human review before model promotion.
