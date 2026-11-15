# DermCareAI Design Specifications

This directory contains reviewed and approved design specifications and durable architecture decisions for DermCareAI_ONE.

## Lifecycle

1. **Working draft:** create briefs, draft specifications, and review reports under the ignored `.dev/docs/` directory.
2. **EGM review:** use real fresh-context Goldfish reviewers where the host supports them. Record skipped stages and host limitations honestly.
3. **Finding triage:** the author and relevant technical owners decide which findings to accept, reject, or defer.
4. **Human approval:** obtain architecture approval and the applicable security, privacy, clinical, and regulatory approvals before treating a specification as accepted.
5. **Promotion:** copy the approved specification into this directory, update this index, and record the approver and date.
6. **Implementation:** provide the approved specification to CodeSwarm X 3.0 as the source for a scoped implementation plan.
7. **Drift review:** periodically compare approved specifications with the current codebase and resolve material divergence through normal change control.

EGM output is advisory. A completed EGM review is not human approval and does not authorize implementation, merging, deployment, or clinical use.

## Design document minimum metadata

Each accepted design should include:

- Status: DRAFT, IN_REVIEW, APPROVED, SUPERSEDED, or RETIRED.
- Owner and accountable approver.
- Date and revision.
- Problem statement, goals, non-goals, and affected subsystems.
- Current-state evidence and source/code references.
- Assumptions, constraints, alternatives, and trade-offs.
- Security, privacy, data-integrity, and clinical-safety implications.
- API/schema/migration compatibility where applicable.
- Failure modes, rollback, observability, and operational ownership.
- Acceptance criteria and verification plan.
- Deferred decisions and known risks.

Never include real patient data, secrets, credentials, or private incident evidence.

## Specification index

| Specification | Scope | Status |
|---|---|---|
| [DermCareAI platform baseline](DERMCAREAI_PLATFORM_BASELINE.md) | Repository-wide architecture context and design questions | BASELINE DRAFT — EGM and human review pending |

Add a row when a new design is promoted. Keep working drafts and unaccepted reviewer reports out of this directory.
