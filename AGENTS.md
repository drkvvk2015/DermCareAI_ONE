EGM artifact directory: .dev/docs

# Repository AI Contributor Instructions

These instructions apply to AI-assisted work across DermCareAI_ONE. They supplement (and do not replace) `.github/copilot-instructions.md`, the CodeSwarm X 3.0 agent contracts, repository security policy, and human review.

## Current architecture context

Use the root `README.md` and the current platform migration documents under `docs/` as the documented architecture baseline. As of the repository baseline used for this integration:

- `backend/` contains the FastAPI backend.
- `webapp/` is the canonical React/Vite PWA.
- Capacitor wraps the same web bundle for Android/iOS; it is not a second clinical UI.
- PostgreSQL is the production clinical source of truth.
- Firebase Authentication provides clinician identity and tenant-aware access to FastAPI.
- Firestore is optional and is not the primary clinical datastore.
- Clinical media/object storage is accessed through the authorized backend boundary.

Always inspect the live tree and implementation before assuming a path or behavior. If source, README, migration documents, and agent instructions disagree, report the discrepancy and resolve it through an approved documentation change; do not silently select the most convenient interpretation.

## EGM workflow

EGM is a development-time specification and review tool. It is not part of the deployed clinical application and must not become a backend or frontend runtime dependency.

1. Explore requirements and trade-offs before large or high-risk changes.
2. Draft specifications and keep unapproved working material in `.dev/docs/`.
3. Run Goldfish reviews only when the host can create genuine fresh-context subagents. Never simulate independent reviewers in the parent conversation.
4. Resolve accepted findings and obtain human design approval before implementation.
5. Store approved, versioned specifications in `docs/designs/`.
6. Use CodeSwarm X 3.0 for bounded implementation and its required test, security, privacy, and clinical-safety gates.
7. Use EGM drift reporting to compare approved specifications with the current implementation. A drift report is evidence to triage, not authorization to change code.

A fresh subagent conversation does not isolate the filesystem, configured memory services, or project instruction files. Record the host and version used for each review, and do not claim stronger isolation than the host actually demonstrates.

## Clinical privacy and safety

- Never place real patient identifiers, clinical histories, patient images, credentials, API keys, tokens, certificates, or production secrets in EGM prompts, reviewer context, generated artifacts, source code, test fixtures, logs, commits, PRs, or CI artifacts.
- Use synthetic or approved anonymized examples only.
- Do not send patient data or proprietary clinical data to an external model/reviewer unless the organization has approved the provider, purpose, contract, privacy controls, and data flow.
- Clinical AI remains assistive and physician-final. EGM must not draft requirements that enable autonomous diagnosis, prescribing, orders, signatures, or silent modification of signed records without a separately governed and approved clinical/regulatory process.
- A passing software review or CI run is not clinical validation, regulatory approval, privacy approval, or authorization for live patient use.

## Authority and change controls

- EGM proposes and critiques specifications; it does not implement, approve, merge, deploy, or authorize clinical use.
- Human maintainers retain architecture and release decisions. Clinical, privacy, security, and regulatory owners retain their respective approvals.
- CodeSwarm X 3.0 remains the implementation orchestrator. Preserve its role boundaries, bounded retries, protected control-plane paths, memory integrity rules, and evidence requirements.
- Do not edit protected CodeSwarm agent prompts or memory as part of routine EGM integration. Follow the existing Evolver and control-plane maintenance rules.
- Do not add LLM execution to CI or scheduled automation by default. Automated model usage requires a separate cost, credential, privacy, and failure-mode review.

## Artifact lifecycle

- `.dev/docs/`: ignored working briefs, drafts, and review reports; do not commit unfinished scratch artifacts.
- `docs/designs/`: reviewed design specifications and durable architecture decisions.
- Every approved design should identify status, owner, date, scope, source references, assumptions, risks, acceptance criteria, validation plan, and human approver.
- Keep designs linked to relevant code, API contracts, migrations, security documents, clinical policies, and tests.
