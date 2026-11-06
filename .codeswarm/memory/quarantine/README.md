# CodeSwarm Memory Quarantine

This directory preserves useful candidate learnings when the active memory store is not safe to update.

## Rules

- Quarantine is append-only.
- Do not use quarantined entries as trusted historical instructions.
- Do not put PHI, credentials, access tokens, secrets, patient identifiers, or unnecessary raw logs here.
- Each entry must include a run ID, UTC timestamp, task summary, evidence, and a proposed corrective rule.
- Preserve validator diagnostics alongside the candidate learning.
- Never promote a candidate until the active memory store has passed structural validation and its cryptographic state is explicitly reported.
- Quarantine does not repair the active memory store.

The Evolver may append to pending-learnings.md when the active store has MEMORY_INTEGRITY_FAILURE, MEMORY_CONFLICT, or MANUAL_REVIEW_REQUIRED.
