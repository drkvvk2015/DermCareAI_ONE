# Guideline and Evidence Governance

DermCareAI Clinical AI uses a governed evidence layer. A language model must not invent a guideline citation or silently treat an arbitrary web page as a current recommendation.

## Evidence hierarchy

1. National regulatory/public-health guidance and hospital-approved policy.
2. Current specialty-society clinical practice guidelines.
3. Systematic reviews and high-quality consensus statements.
4. Authoritative drug/product information.
5. Primary studies when higher-level evidence is unavailable or insufficient.

## Required provenance

Every evidence item used for a clinical recommendation must retain:

- organization and document title;
- publication/update date and version/revision;
- stable HTTPS URL or controlled document identifier;
- retrieval timestamp;
- section/recommendation identifier where available;
- immutable document checksum when available;
- applicability scope and population.

## Freshness states

`current`, `superseded`, `conflicting`, `insufficient`, and `unable_to_verify` are explicit states. Only `current` evidence may directly support a current high-consequence recommendation. Conflicting or unverifiable guidance must be surfaced to the physician rather than resolved by model guesswork.

## Production rule

The production copilot may recommend a treatment pathway only when the evidence layer can provide provenance and applicability. If no governed current evidence is available, the copilot must abstain or provide a clearly labelled evidence gap for physician review.

This file defines the governance contract; it does not itself constitute clinical guidance.
