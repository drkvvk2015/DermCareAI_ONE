# Clinical AI Physician Review and Audit Contract

## Required encounter presentation

Every clinical AI response shown to a clinician must visibly identify:

- **AI Clinical Copilot — decision support only**
- Physician verification required
- diagnostic certainty/uncertainty and abstention state
- urgent/red-flag signals
- missing patient information that could change management
- differential suggestions separately from treatment suggestions
- evidence source, organization, version/update date, and retrieval timestamp
- whether evidence is current, superseded, conflicting, insufficient, or unable to verify

## Physician actions

The physician may accept, reject, edit, or ignore a suggestion. Acceptance is a clinician decision and must never be represented as an AI-confirmed diagnosis.

The AI must not:

- sign a diagnosis;
- prescribe or submit a high-consequence order;
- alter a signed record;
- suppress a safety alert;
- silently promote a model or guideline source.

## Audit event

For each clinical AI interaction, retain the minimum necessary audit metadata: encounter identifier, organization/clinic scope, clinician identity, capability, model/policy version, evidence identifiers and hashes, abstention/safety state, candidate categories, and clinician disposition when captured by the application workflow. Do not store raw image or free-text clinical content in an audit event unless separately governed and required.

## Evidence refresh

A recommendation should display its evidence freshness. When a source becomes superseded or cannot be verified, the source must be blocked from current high-consequence recommendations until reviewed by the clinical owner.
