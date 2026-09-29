# Controlled Auto-Repair Governance

DermCareAI's auto-repair subsystem is a **proposal and evidence system**, not an autonomous deployment mechanism.

## Control flow

`detect -> classify -> reproduce -> propose -> targeted tests -> full regression -> security/static analysis -> risk gate -> draft PR -> human review -> merge`

The current implementation records:

- a stable failure fingerprint;
- failure classification and confidence;
- risk level;
- protected-path gate status;
- bounded attempt information;
- idempotency key;
- proposed verification commands;
- dry-run/mutation status;
- explicit human-review requirement;
- a machine-readable evidence report.

## Hard safety boundaries

The proposal engine cannot directly modify source files, create commits, push branches, merge PRs, or deploy software.

Protected paths include clinical reasoning, AI safety/governance, authentication/security, audit, pharmacy, and billing modules. A proposal touching these areas is blocked from automated modification and marked critical risk.

Security-classified failures are always critical-risk and require human review.

Retries are bounded. Duplicate idempotency keys are rejected by the in-process guard. CI integrations should persist the idempotency key in the repair evidence artifact when coordinating retries across runners.

## CLI

Dry-run proposal generation:

```bash
PYTHONPATH=backend python -m backend.auto_repair_cli \
  --log repair-evidence/combined.log \
  --output repair-evidence/repair-report.json \
  --path backend/tests/test_health.py
```

The CLI returns a non-zero exit code for blocked/prohibited execution states. `--apply` is intentionally blocked because this component has no mutation implementation.

## Acceptance boundary

A generated report is evidence for a **minimal isolated repair PR**. It is not evidence that the repair is correct. Targeted tests, the full regression suite, security/static-analysis gates, code review, and the repository's merge protections remain mandatory.
