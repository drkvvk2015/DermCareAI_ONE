# CodeSwarm Learnings

Append-only log of durable lessons learned across CodeSwarm runs for `DermCareAI_ONE`.

Entries must be concise, actionable, evidence-based, and free of PHI, credentials, secrets, or unnecessary raw logs.

Existing entries must never be silently rewritten or deleted.

<!-- CodeSwarm-Evolver appends new entries below this line. -->

## Entry Format

```text
### LEARNING-<unique-id>

- Date (UTC): <timestamp>
- Run ID: <run-id>
- Source stage: <RECALL|PLAN|CODE|DEBUG|OPTIMIZE|FINAL_DEBUG|EVOLVE>
- Pattern: <recurring failure or useful lesson>
- Root cause: <evidence-based cause>
- Evidence: <specific test/build/result>
- Action: <what future runs should do differently>
- Affected area: <backend/mobile/CI/Android/etc.>
- Occurrences: <count>
- Confidence: <low|medium|high>
```

## Rules

- Append new entries only.
- Do not rewrite historical evidence.
- Do not fabricate run IDs, test results, root causes, or occurrence counts.
- A retry or second attempt within the same CodeSwarm run is not an independent run.
- Do not store patient-identifiable information, credentials, tokens, secrets, or unnecessary raw logs.
- Historical lessons are advisory evidence; current repository evidence takes precedence.
- A single occurrence does not authorize automatic prompt evolution.
- Prompt evolution requires the independent-run thresholds defined in `CodeSwarm-Evolver.agent.md`.
