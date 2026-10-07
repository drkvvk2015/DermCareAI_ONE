# Clinical AI Production Evidence Checklist

This checklist is the clinical-AI activation gate. Passing software CI does not satisfy these items.

Every claim must be traceable to the exact frozen model artifact SHA-256 and locked evaluation dataset. Synthetic, estimated, copied, or placeholder clinical performance numbers are prohibited.

## Required evidence

1. Exact frozen production model artifact and SHA-256.
2. Exact artifact/version identity recorded in the evidence manifest.
3. Frozen evaluation dataset manifest, provenance, and inclusion/exclusion criteria.
4. Sensitivity and specificity with confidence intervals.
5. PPV and NPV for the intended prevalence setting.
6. ROC-AUC and PR-AUC where appropriate.
7. Calibration method and results.
8. Prespecified subgroup analysis.
9. OOD and low-quality-image behavior.
10. Abstention performance.
11. Clinician-review and override analysis.
12. Independent/external validation.
13. Accountable approval records bound to the exact artifact.
14. Staging deployment and tested rollback evidence.
15. Intended-use, regulatory and privacy assessments appropriate to the actual deployment.

## Enforcement

Production inference is eligible only when:

- release-manifest.json exists and validates;
- release_status is approved;
- research_only is false;
- the exact model name/version/hash matches the active governance record;
- the controlled artifact hash matches the evidence manifest and governance record;
- all required validation/evidence sections are completed;
- at least two distinct accountable approvers are recorded with traceable approval records; and
- staging and rollback evidence is recorded.

Until those conditions are met, production clinical AI remains disabled by policy.

Validate with:

python backend/scripts/validate_ai_release_manifest.py docs/ai-validation/release-manifest.json
