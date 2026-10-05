# AI validation release evidence

Independent clinical and prospective evidence is external to software CI. Do not enter estimated, synthetic, or invented performance numbers. The repository does not contain a completed clinical evidence package, and research models must remain unavailable for production clinical use.

## Evidence package

Copy `release-manifest.template.json` into the deployment's controlled evidence store only when preparing a separately governed evaluation. Do not put PHI, images, patient-level records, or restricted datasets in GitHub.

Freeze the intended-use statement, exact model artifact and SHA-256, locked test-set manifest and SHA-256, protocol, cohort, analysis methods, and reviewer roles before evaluation. Record sensitivity, specificity, PPV, NPV, ROC-AUC, and PR-AUC with sample counts and 95% confidence intervals. Attach calibration, subgroup, out-of-distribution, abstention, clinician review/override, independent external validation, and prospective evaluation evidence by secure URI and SHA-256. Obtain approval from an accountable reviewer distinct from the independent external reviewer, and trace the approval to the exact model version and artifact digest.

Validate a completed manifest with:

```bash
python backend/scripts/validate_ai_release_manifest.py path/to/release-manifest.json
```

The validator checks structural completeness, formats, timestamp zones, numeric intervals, digest formatting, and model identity when expected values are supplied. It does not fetch evidence URIs, verify their contents, establish scientific validity, or independently verify reviewer accountability.

## Physician-final application boundary

The Clinical AI application remains suggestion-only. Its policy disables diagnostic inference and cannot be overridden by a production environment variable; a complete evidence package does not activate `/predict`. Any future diagnostic evaluation or deployment must be separately governed, with accountable clinical, regulatory, privacy, security, validation, staging, and rollback approvals before patient-facing use.

When operationally required for a separately governed deployment, mount its approved evidence manifest read-only in the controlled deployment environment. Do not treat software preflight or a structurally valid manifest as proof of safety, effectiveness, regulatory approval, or fitness for clinical use.
