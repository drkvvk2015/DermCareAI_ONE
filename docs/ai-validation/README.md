# AI Validation Release Manifest

The clinical AI release manifest is the authoritative evidence gate for production model activation.

Copy release-manifest.template.json to release-manifest.json only when real evidence exists. Replace every placeholder with evidence tied to the exact frozen model artifact and locked evaluation dataset. Do not enter estimated, synthetic, or invented clinical performance values.

The validator now requires:

- schema version 2;
- approved release status and research_only=false;
- exact model identity and SHA-256;
- locked dataset manifest, provenance and inclusion/exclusion evidence;
- sensitivity/specificity/PPV/NPV/ROC-AUC/PR-AUC with confidence intervals;
- completed calibration, subgroup, OOD, abstention, clinician-review and external-validation evidence;
- two distinct accountable approvers with traceable approval records;
- completed clinical intended-use, regulatory and privacy reviews; and
- staging plus rollback evidence.

Validate with:

python backend/scripts/validate_ai_release_manifest.py docs/ai-validation/release-manifest.json

Production inference also re-validates this manifest and requires it to match the active model-governance record and controlled artifact hash. A missing or invalid package keeps clinical AI disabled.
