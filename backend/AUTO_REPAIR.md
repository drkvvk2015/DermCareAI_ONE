# Guardrailed automatic repair

The repair layer classifies CI failure evidence, clusters repeated messages, creates
a confidence/risk-scored machine-readable report, and exposes a bounded orchestration
API. The CLI and current GitHub Actions integration run in dry-run/proposal-only mode.

## Orchestration contract

`auto_repair.RepairOrchestrator` accepts environment-specific `RepairHooks` for
reproduction, isolated branch creation, patch proposal, validation, branch cleanup,
and draft PR creation. The orchestrator does not run shell commands or call GitHub
itself. An integration must:

1. Reproduce the failure before proposing a patch.
2. Create a branch named `copilot/repair/<unique-name>`; other branches are rejected.
3. Restrict proposed files with `RepairPolicy` allow/deny paths. Built-in protected
   paths cannot be unprotected.
4. Run targeted tests, then full regression, formatting, static analysis,
   dependency/security checks, and CodeQL in that order. Only a passing validation
   sequence reaches the draft-PR hook.
5. Use the `attempt` and stable `idempotency_key` inputs to deduplicate requests and
   bound retries. The same key/attempt is idempotent within an orchestrator instance;
   a persistent integration must persist that ledger across workflow invocations.
   Close the isolated branch after validation still fails on the final allowed attempt.
6. Persist `RepairReport.to_dict()` as the audit record. It includes the failure,
   root-cause hypothesis, changed files, validation stages, before/after status,
   confidence, risk, retry key, draft PR URL, and an event trail.

The CLI takes `--log` and `--output`; it is always dry-run and writes a complete JSON
report. Optional repeated `--allow-path` and `--deny-path` arguments narrow editable
paths. `--attempt`, `--max-attempts`, and `--idempotency-key` control retry metadata.
The workflow uses its source run ID as the idempotency key, uploads the report as an
artifact, serializes concurrent processing per source run, and ignores repair branches.
Because it is proposal-only, the checked-in workflow cannot recursively create repairs;
a write-capable adapter must persist idempotency state across workflow runs.

## Safety boundary

- The checked-in workflow has read-only `contents` and `actions` permissions and only
  publishes a report. It does not create branches, write source files, or open PRs.
- A separately reviewed integration adapter must explicitly implement the hooks to
  generate a patch and open a **draft PR** after all gates pass. It must not merge or
  deploy; repository branch protection and human review remain mandatory.
- Clinical reasoning, diagnosis, medication/prescription, consent, audit, security,
  and model-safety files are protected by default. The orchestrator rejects them even
  when an adapter requests them. Security and unknown failures also stop at the
  human-review gate.
- Elevated risk requires explicit human approval before tests/PR progression. No
  automatic merge or production deployment interface is provided.
- Dry-run is the default and never calls any adapter hook.

## Tests and fixtures

`backend/tests/test_auto_repair_orchestrator.py` covers classifier fixtures for
Flutter/Dart, backend tests, CI, dependencies, configuration and runtime; repeated
failure clustering; path policies; idempotency; dry-run; validation ordering; draft
PR gating; protected modules; and bounded retry cleanup.
