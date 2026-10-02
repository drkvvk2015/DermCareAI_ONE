# CodeSwarm Learnings

Append-only log of durable lessons learned across CodeSwarm runs for `DermCareAI_ONE`.

Entries must be concise, actionable, evidence-based, and free of PHI, credentials, secrets, or unnecessary raw logs.

Existing entries must never be silently rewritten or deleted.

<!-- CodeSwarm-Evolver appends new entries below this line. -->

### LEARNING-0001

- Date (UTC): 2026-10-01
- Run ID: NOT_PROVIDED
- Source stage: DEBUG
- Pattern: Escalation left frontend validation incomplete after the package-manager command targeted the wrong directory.
- Root cause: `npm ci --prefix webapp` was run with the persistent working directory set to `backend/`, so npm resolved the prefix as `backend/webapp` instead of the repository-root `webapp/`.
- Evidence: The frontend install attempt failed to find the lockfile; the Debugger's two-attempt limit was exhausted and frontend checks were not run.
- Action: Before package-manager commands that use relative prefixes, verify the current working directory or use an explicitly repository-root-relative path; classify any remaining unrun checks as blockers rather than passing validation.
- Affected area: webapp validation / CodeSwarm Debugger
- Occurrences: 1
- Confidence: low

### LEARNING-0002

- Date (UTC): 2026-10-01
- Run ID: NOT_PROVIDED
- Source stage: EVOLVE
- Pattern: The earlier account conflated a successful frontend install with a later command that resolved its relative prefix from the wrong working directory.
- Root cause: `npm install --prefix webapp` succeeded and generated `webapp/package-lock.json`. A later `npm ci --prefix webapp` ran with cwd `backend/`, resolved to `backend/webapp`, and failed there; reruns from the explicit `webapp/` root passed.
- Evidence: Debugger reports `npm ci` from `E:\DermCareAI_ONE\webapp` passed on two runs; final lint passed with one non-blocking react-refresh warning, frontend tests passed (2 files, 6 tests), production build passed, and Vite HTTP smoke passed. Earlier backend suite passed 150 tests; no optimizer backend changes.
- Action: Keep the initial package install/lockfile creation distinct from the later cwd-relative prefix failure; use the explicit `webapp/` working directory for npm validation. EVOLUTION_REJECTED: a single correction does not meet the independent-run threshold for prompt evolution.
- Affected area: webapp validation / CodeSwarm Debugger
- Occurrences: 1
- Confidence: low

### LEARNING-0003

- Date (UTC): 2026-10-02
- Run ID: NOT_PROVIDED
- Source stage: DEBUG
- Pattern: The dependency audit release gate must remain evidence-producing and must distinguish repository dependency defects from unfixable upstream advisories.
- Root cause: CI correctly parsed the `pip-audit` `dependencies` array and retained failed-audit artifacts, exposing two Python findings including `ecdsa` with no published fix; npm audit also reported high/critical findings across Expo, React Native, Firebase, and transitive tooling.
- Evidence: Dependency Audit run 343 failed at the release gate and uploaded `dermcareai-dependency-audit` evidence; backend regression, mobile regression, CodeQL, PostgreSQL staging, Firestore rules, continuous evaluation, production preflight, and staging acceptance passed.
- Action: Never weaken the release gate to obtain green CI. Remediate or explicitly govern each dependency exception, and retain machine-readable audit evidence on both pass and failure paths.
- Affected area: dependency security / CI release gating
- Occurrences: 1
- Confidence: high

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
- Do not fabricate run IDs, test/build results, root causes, or occurrence counts.
- A retry or second attempt within the same CodeSwarm run is not an independent run.
- Do not store patient-identifiable information, credentials, tokens, secrets, or unnecessary raw logs.
- Historical lessons are advisory evidence; current repository evidence takes precedence.
- A single occurrence does not authorize automatic prompt evolution.
- Prompt evolution requires the independent-run thresholds defined in `CodeSwarm-Evolver.agent.md`.
