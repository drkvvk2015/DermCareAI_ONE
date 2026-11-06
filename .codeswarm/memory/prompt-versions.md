# CodeSwarm Prompt Versions

<!-- cspell:ignore codeswarm -->

Tracks revisions made by `CodeSwarm-Evolver` to agent prompt files in `.github/agents/`.

This file is **append-only**. Historical rows must not be silently edited or deleted.

Prompt changes require the evidence threshold defined in `CodeSwarm-Evolver.agent.md`.

| Date (UTC) | Run ID | Agent | Previous Version / Hash | New Version / Hash | Change | Reason | Supporting Runs | Threshold | Validation |
| - | - | - | - | - | - | - | - | -: | - |
| — | — | — | — | — | Initial baseline | Initial CodeSwarm agent set | — | — | Baseline |

<!-- CodeSwarm-Evolver appends new rows below this line. -->
| 2026-11-06 | codeswarm-x-3.0-memory-intelligence | CodeSwarm | 2fc3e40d054c4b38cb6540b13080cee10786a586 | 2fc3e40d054c4b38cb6540b13080cee10786a586 | CodeSwarm X 3.0 orchestrator, state ledger, bounded routing, validation and certification gates | Explicit user-directed major upgrade; adds memory intelligence and governed recovery | USER-AUTHORIZED | USER-DIRECTED | Text reviewed; automated CI validation pending |
| 2026-11-06 | codeswarm-x-3.0-memory-intelligence | CodeSwarm-Evolver | 78b8692ac2707a690c18ab5400e8c3e19bb73423 | 78b8692ac2707a690c18ab5400e8c3e19bb73423 | Memory integrity, safe baseline, quarantine and metadata-only recovery | Explicit user-directed major upgrade; preserves append-only history and tool boundaries | USER-AUTHORIZED | USER-DIRECTED | Text reviewed; validator/CI validation pending |
| 2026-11-06 | codeswarm-x-3.0-memory-intelligence | CodeSwarm-Memory-Guardian | NEW | de3396aa19bca12f9ed9dfb9769b941bad186aa7 | Added independent read-only memory validation agent | Adds structural and cryptographic consistency checks with recovery classification | USER-AUTHORIZED | USER-DIRECTED | Text reviewed; validator/CI validation pending |

## Evolution Rules

- Entries are append-only.
- Explicit user-directed prompt releases are recorded as maintainer-authorized changes; the independent-run thresholds apply to autonomous Evolver-initiated prompt evolution, not to a direct user instruction to upgrade a prompt.
- A prompt change must never overwrite historical entries.
- Every prompt patch must identify the previous and new prompt version or content hash when genuinely available.
- A normal prompt evolution requires evidence from at least **2 independent CodeSwarm runs** with the same root cause.
- Changes affecting tool permissions, Debugger verification, memory integrity, self-evolution boundaries, security controls, or other swarm safety controls require at least **3 independent runs**.
- A retry, second Debugger attempt, or multiple failures within one CodeSwarm run does **not** count as an independent run.
- `Supporting Runs` must contain the run IDs that satisfy the threshold.
- `Validation` must identify how the prompt change was checked before being accepted.
- The Evolver must not invent hashes or validation results.
- If a genuine content hash cannot be calculated, record `UNVERIFIED` rather than fabricating one.
- Prompt evolution must never weaken the mandatory Debugger stage, stage-attempt limits, memory-integrity controls, least-privilege boundaries, security safeguards, or clinical-safety constraints.

## Version Semantics

Prompt versions may use either:

1. a genuine content hash, or
2. an explicit repository revision identifier.

Where both are available, prefer recording both.

The prompt-version history is separate from the memory-schema version stored in:

```text
.codeswarm/memory/schema-version
```

## Example Evolution Entry

```text
| 2026-10-01T10:00:00Z | run-0027 | CodeSwarm-Debugger | sha256:abc... | sha256:def... | Added explicit environment-failure classification | Same Gradle/network misclassification occurred in independent runs | run-0021, run-0027 | 2 | Reviewed by Evolver; no verification-gate weakening |
```
