# Copilot Instructions — DermCareAI_ONE

This repository is a clinical dermatology platform with a Python/FastAPI backend (`backend/`) and a canonical React/Vite PWA (`webapp/`) wrapped by Capacitor for Android/iOS. The README and platform migration documents are the primary architecture references; inspect the current tree before assuming any path exists.

Treat all clinical and patient-related information as sensitive. Never place real patient-identifiable or clinical data in source code, fixtures, logs, commits, prompts, screenshots, or test output.

## Architecture

- `backend/` — FastAPI services covering clinical, commerce, prescription, authentication, and related backend domains.
- `backend/ai_adapters/` — AI/ML model adapters and screening integrations (verify current paths before relying on them).
- `backend/dermatology/` — dermatology-specific clinical workflow modules (verify current paths before relying on them).
- `webapp/` — canonical React/Vite clinical PWA and primary application client.
- Capacitor — wraps the canonical web bundle for Android/iOS; it is not a separate clinical UI.
- PostgreSQL — production database for the clinical workflow SQL store (encounters, lesions, consents, media metadata, sign-offs, follow-ups and AI reviews).
- Firebase Authentication — clinician identity and tenant-aware access to FastAPI.
- Firestore — current patient-registration route writes registry documents through the Firebase Admin SDK; Firestore Rules govern direct client-SDK access but do not authorize Admin-SDK operations.
- Object storage — clinical media/object persistence behind server-side authorization and signing.
- `docs/` — architecture, security, clinical governance, deployment, and production-readiness documentation.

Do not create or revive a separate React Native/Expo client without an approved architecture decision. Before a large structural change, inspect the relevant documentation under `docs/` and verify the current repository tree.

## Repository conventions

### Backend

- Use Python with type hints for all new functions and public interfaces.
- Follow the existing FastAPI/router/service/store architecture.
- Prefer existing `*_store.py` persistence modules rather than introducing direct database access.
- Reuse established validation, authentication, authorization, error-handling, and audit patterns.
- Do not introduce a new persistence abstraction when an existing repository abstraction already serves the requirement.
- Preserve tenant isolation and transaction semantics.

### Web/PWA and Capacitor

- Use TypeScript with strict typing.
- Prefer functional React components and existing patterns under `webapp/`.
- Reuse existing routing, state-management, API-client, and UI abstractions.
- Keep the PWA as the canonical clinical UI; Capacitor wraps the same web bundle for native Android/iOS delivery.
- Do not introduce a second implementation of an existing workflow or a new React Native/Expo client without an approved architecture decision.
- Treat native Capacitor/Android/iOS changes as build-sensitive and verify the relevant native toolchain before modifying native configuration.

## Security and sensitive data

This repository handles clinical/PHI-adjacent information.

- Never log raw patient information.
- Never commit credentials, tokens, API keys, private certificates, or production secrets.
- Do not place real patient data in fixtures or examples.
- Use synthetic or anonymized test data.
- Follow `SECURITY.md`.
- Consult `docs/SECURITY_THREAT_MODEL.md` for security-sensitive changes.
- Preserve authentication, authorization, tenant isolation, audit logging, input validation, and security controls.
- Do not weaken a security control simply to make tests pass.

## Clinical-safety rules

- Treat AI functionality as assistive unless the repository explicitly documents otherwise.
- Do not invent diagnostic or treatment rules.
- Do not silently change clinical workflow semantics.
- Do not remove clinical warnings, human-review requirements, auditability, or safety checks to simplify implementation.
- Changes affecting prescriptions, patient records, AI screening, clinical decision support, consent, or audit trails require targeted tests and explicit verification.
- Never represent an unvalidated AI model as clinically validated.

## Change discipline

- Prefer editing existing files over creating new ones; create a new file only after confirming no existing file/module can be extended (CodeSwarm-Coder may create files per its approved plan, following the same search/confirm step).
- Search for existing functionality before adding a new module.
- Keep changes minimal and scoped to the requested requirement.
- Do not perform unrelated refactoring.
- Do not introduce new top-level dependencies without clear justification.
- Preserve existing public interfaces unless an approved plan explicitly requires a contract change.
- Do not silently change database schemas, persistence formats, API contracts, or authentication behavior.

Before editing an existing file:

```text
READ → SEARCH REFERENCES → UNDERSTAND CONVENTIONS → EDIT
```

Before creating a new file:

```text
SEARCH EXISTING EQUIVALENTS → CONFIRM NEED → CREATE
```

## Testing and verification

Behavior changes require corresponding tests.

### Backend

Canonical validation should use the repository's existing scripts and test configuration. At minimum, use the relevant backend test/type/lint commands defined by the project.

Backend tests are located under:

```text
backend/tests/
```

### Web/PWA and Capacitor

For PWA changes, use the repository's existing frontend lint, test, and production-build commands. When Capacitor or native platform files are affected, include the relevant Capacitor synchronization and Android/iOS build verification where the required toolchain is available.

### General rule

Do not claim that code works merely because it was inspected.

Execution-based verification belongs to the Debugger agent within the CodeSwarm workflow. When working outside the CodeSwarm workflow, you may run the repository's test/lint/build commands yourself and report the actual output; inside the workflow, only the Debugger certifies PASS.

## CodeSwarm multi-agent workflow

This repository uses the CodeSwarm agent team for complex engineering work.

### CodeSwarm-Planner

- Inspects repository structure and conventions.
- Produces the implementation/dependency map.
- Defines acceptance and verification criteria.
- Does not write implementation code.

### CodeSwarm-Coder

- Implements only the approved plan.
- Prefers editing existing files; creates new application files only when the plan requires it and no existing file/module can be extended.
- Preserves repository conventions.
- Does not self-certify builds or tests.

### CodeSwarm-Debugger

- Executes builds/tests and other relevant validation.
- Diagnoses failures from actual execution evidence.
- Applies only minimal corrective fixes.
- Has a strict two-attempt correction boundary. If validation still fails after two correction attempts, stop, report FAIL with the execution evidence and the remaining errors, and return control to the Orchestrator/user without further edits.
- Must never report `PASS` without current execution evidence.

### CodeSwarm-Optimizer

- Runs only after a verified Debugger pass.
- Performs targeted performance, resource, readability, and maintainability improvements.
- Does not self-certify the optimization.
- All optimization changes require final Debugger re-validation.

### CodeSwarm-Evolver

- Maintains persistent swarm memory under `.codeswarm/memory/`.
- Records evidence-based recurring lessons.
- May modify `CodeSwarm*.agent.md` prompts only when the same root cause appears in at least 3 separate runs recorded in `.codeswarm/memory/`.
- Must preserve memory integrity/versioning.
- Must not modify application source code as part of self-evolution.

## Swarm control-plane boundaries

The following paths are swarm control-plane resources:

```text
.github/agents/CodeSwarm*.agent.md
.codeswarm/memory/**
```

Application agents must not modify these paths unless their role explicitly authorizes it.

Only `CodeSwarm-Evolver` may perform self-evolution operations on those paths, subject to its memory-integrity and evidence rules.

## Persistent swarm memory

Persistent swarm memory is stored under:

```text
.codeswarm/memory/
```

Memory is append-only, versioned, and integrity-checked.

Agents should:

- consult applicable prior learnings when supplied by the Orchestrator;
- treat historical learnings as evidence rather than unquestionable authority;
- never fabricate historical runs;
- never silently rewrite historical evidence.

The Evolver owns memory writes.

## Repository-state discipline

Before substantial changes:

- inspect the current repository state;
- identify relevant existing changes;
- avoid overwriting unrelated user work.

After implementation:

- report created/modified/deleted files;
- report validation status;
- identify remaining warnings or blockers;
- do not claim completion without the required Debugger verification.

## General guidance

- Prefer the simplest change that satisfies the requirement.
- Reuse existing abstractions before introducing new ones.
- Keep interfaces stable unless a planned change requires otherwise.
- Favor explicit, testable behavior over clever abstractions.
- Preserve security, clinical safety, auditability, and tenant isolation above convenience.
- Document meaningful architectural or operational changes under `docs/` when appropriate.