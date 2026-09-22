# AI Validation Release Manifest

Copy `release-manifest.json`, replace placeholders with actual locked evidence, and only set `release_status` to `approved` after accountable clinical/AI review.

Validate with:

`python backend/scripts/validate_ai_release_manifest.py docs/ai-validation/release-manifest.json`

Do not enter estimated, synthetic, or invented clinical performance numbers. Evidence must be traceable to the frozen artifact and dataset used for the release.
