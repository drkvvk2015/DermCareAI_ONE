# AI Validation Release Manifest

Copy `release-manifest.template.json` to `release-manifest.json` and replace every `null` or empty value with traceable evidence. The template is intentionally marked `not_ready` and `research_only`; it does not assert that external validation or clinician approval has occurred.

Validate with:

```sh
python backend/scripts/validate_ai_release_manifest.py docs/ai-validation/release-manifest.json
```

The validator checks manifest structure, value formats, evidence references, and release-gate consistency. A PASS only means the manifest is complete and internally consistent; it does not authenticate evidence, reproduce results, establish clinical performance, or grant clinical/regulatory approval. External validation must identify an independent site or dataset and its evidence. Clinician review and accountable approval require their own completed records and audit references.

Include immutable model and training-data digests, source revisions, a locked evaluation dataset manifest and digest, evaluation code revision, environment, dependency-lock digest, random seed, and protocol version. Report each listed metric with a value and 95% confidence bounds. Document the assessed subgroup definitions and sample counts, OOD challenge sets and observed behavior, and the abstention policy, threshold, coverage, and selective risk.

Do not enter estimated, synthetic, or invented clinical performance numbers or evidence references. Any test fixtures are artificial validator test data and are not clinical evidence. Preserve `research_only: true` and `release_status: not_ready` until the required real evidence and approvals exist.
