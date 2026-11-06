# CodeSwarm Prompt Versions

<!-- cspell:ignore codeswarm -->

Tracks revisions made by `CodeSwarm-Evolver` to agent prompt files in `.github/agents/`.

This file is **append-only**. Historical rows must not be silently edited or deleted.

Prompt changes require the evidence threshold defined in `CodeSwarm-Evolver.agent.md`.

| Date (UTC) | Run ID | Agent | Previous Version / Hash | New Version / Hash | Change | Reason | Supporting Runs | Threshold | Validation |
| - | - | - | - | - | - | - | - | -: | - |
| — | — | — | — | — | Initial baseline | Initial CodeSwarm agent set | — | — | Baseline |

<!-- CodeSwarm-Evolver appends new rows below this line. -->
| 2026-11-06 | codeswarm-x-3.0-memory-intelligence | CodeSwarm | d0308c107aebab4157ddcc534d7eca07f4ebc8e0 | 90496b607742a3f49267e69dfe4be263520da830 | Added deterministic memory knowledge graph and engineering intelligence policy | Make prior learnings navigable for future planning without inferring causality | USER-AUTHORIZED | USER-DIRECTED | Validator tests and CI validation queued |
| 2026-11-06 | codeswarm-x-3.0-memory-intelligence | CodeSwarm-Evolver | d772755b670ccc41756152add209adc8e1f98763 | 3f5124810b0765507d27a59453339e2fad73b48d | Added trust-gated knowledge context to RECALL | Allow exact-pattern/area summaries to support planning only when structural integrity permits | USER-AUTHORIZED | USER-DIRECTED | Validator tests and CI validation queued |
| 2026-11-06 | codeswarm-x-3.0-memory-intelligence | CodeSwarm-Memory-Guardian | 9b12c6d59f649e10190ed724fbe4b67cf35e63df | 75e13e1781544e31f5c1a1bbbf19c6e289335a4f | Added knowledge graph and engineering intelligence output contract | Expose read-only learning relationships and exact-text trend summaries | USER-AUTHORIZED | USER-DIRECTED | Validator tests and CI validation queued |
| 2026-11-06 | codeswarm-x-3.0-memory-intelligence | CodeSwarm | f5469dcef01d261d12890101a9a57d50000ba067 | d0308c107aebab4157ddcc534d7eca07f4ebc8e0 | Added protected control-plane resource boundaries for validator, tests and workflow | Prevent ordinary application agents from modifying memory integrity infrastructure | USER-AUTHORIZED | USER-DIRECTED | PR diff reviewed; CI pending |
| 2026-11-06 | codeswarm-x-3.0-memory-intelligence | CodeSwarm-Coder | 313c1ffb0c408f8302107918e3cdbe7f9555c1b1 | a772b96a9ad1a40d0feb60c912043f6592135639 | Protected memory validator, its tests and integrity workflow from application edits | Preserve control-plane separation | USER-AUTHORIZED | USER-DIRECTED | PR diff reviewed; CI pending |
| 2026-11-06 | codeswarm-x-3.0-memory-intelligence | CodeSwarm-Debugger | 1282df3fa328e86a6fc9791b545a30e75796a732 | da28e16c54caff733dc75786d1a31c5434e4c4c8 | Protected memory validator, its tests and integrity workflow from corrective edits | Preserve independent validation/control-plane separation | USER-AUTHORIZED | USER-DIRECTED | PR diff reviewed; CI pending |
| 2026-11-06 | codeswarm-x-3.0-memory-intelligence | CodeSwarm-Optimizer | 839dd188eaedc8fbfdefeb3c1d9619f161dca8fa | 634e833ddc9fab78b4d854d4027439176dc30478 | Protected memory validator, its tests and integrity workflow from optimization edits | Preserve control-plane separation | USER-AUTHORIZED | USER-DIRECTED | PR diff reviewed; CI pending |
| 2026-11-06 | codeswarm-x-3.0-memory-intelligence | CodeSwarm | 2fc3e40d054c4b38cb6540b13080cee10786a586 | f5469dcef01d261d12890101a9a57d50000ba067 | Harmonized actual Planner/Coder/Debugger/Optimizer output schemas; added explicit failure statuses; removed direct edit/execute tools from delegate-only Orchestrator | Prevent false malformed-agent retries and enforce least privilege | USER-AUTHORIZED | USER-DIRECTED | PR branch diff reviewed; CI pending for latest commit |
| 2026-11-06 | codeswarm-x-3.0-memory-intelligence | CodeSwarm-Memory-Guardian | de3396aa19bca12f9ed9dfb9769b941bad186aa7 | 9b12c6d59f649e10190ed724fbe4b67cf35e63df | Added separate cryptographic_issues output field | Keep structural and cryptographic failure diagnostics distinct | USER-AUTHORIZED | USER-DIRECTED | PR branch diff reviewed; CI pending for latest commit |
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
