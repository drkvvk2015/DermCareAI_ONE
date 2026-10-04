# AI validation release evidence

Independent clinical and prospective evidence is external to software CI. Do not enter estimated, synthetic, or invented performance numbers. The current repository does not contain a completed clinical evidence package, and the research model must remain unavailable for production clinical use.

## Evidence package

1. Copy `release-manifest.template.json` into the deployment's controlled evidence store. Do not put PHI, images, patient-level records, or restricted datasets in GitHub.
2. Freeze the intended-use statement, exact model artifact and SHA-256, locked test-set manifest and SHA-256, protocol, cohort, analysis methods, and reviewer roles before evaluation.
3. Record sensitivity, specificity, PPV, NPV, ROC-AUC, and PR-AUC with sample counts and 95% confidence intervals. Attach calibration, subgroup, out-of-distribution, abstention, clinician review/override, independent external validation, and prospective evaluation evidence by secure URI and SHA-256.
4. Obtain approval from an accountable reviewer who is distinct from the independent external reviewer. Keep the approval record traceable to the exact model version and artifact digest.
5. Validate the completed manifest:

   ```bash
   python backend/scripts/validate_ai_release_manifest.py path/to/release-manifest.json
   ```

The validator checks completeness, formats, timestamp zones, numeric intervals, digest formatting, and model identity when expected values are supplied. It does not fetch evidence URIs, verify their contents, establish that an evaluation is scientifically valid, or verify reviewer independence.

## Production enforcement

AI remains disabled by default through `AI_ENABLED_IN_PRODUCTION=false`. If an accountable organization later considers enabling it, configure `AI_VALIDATION_MANIFEST_PATH` to a read-only mounted manifest from the approved evidence store, run the production preflight, and use the model registry to deploy the exact matching artifact. Production startup rechecks the manifest's approval state and model name, version, and SHA-256 against the active deployment. Missing, incomplete, research-only, or mismatched evidence blocks inference.

Passing these structural checks is not proof of safety, effectiveness, regulatory approval, or fitness for clinical use. Human clinical, regulatory, privacy, and deployment approvals remain separate requirements.
