# Elephant-Goldfish Model (EGM) — DermCareAI Integration

**Status:** Integration documentation and repository conventions prepared; host installation and a live Goldfish review remain pending.
**Scope:** Repository-wide development workflow. This does not change the deployed application or enable any clinical AI capability.
**Upstream:** https://github.com/google/elephant-goldfish-model
**Upstream license:** Apache-2.0. EGM describes itself as an open-source plugin and states that it is not an officially supported Google product.

## 1. Purpose and boundary

EGM adds a specification-first design loop to DermCareAI_ONE:

- **Elephant:** uses repository context and requirements to explore trade-offs and draft specifications.
- **Goldfish reviewers:** inspect the design and referenced source material from fresh subagent contexts, looking for missing assumptions, ambiguity, design flaws, and implementation risks.
- **Human maintainers:** decide which findings to accept and approve the design.
- **CodeSwarm X 3.0:** remains responsible for bounded implementation, debugging, optimization, verification, security/privacy/clinical gates, and evidence-based certification.

EGM is an optional development-time tool. It is not a clinical inference model, application dependency, production service, patient-facing feature, or substitute for clinical, privacy, security, regulatory, or human review.

No EGM package is added to the backend or frontend dependency manifests. No EGM model calls are added to GitHub Actions or application runtime.

## 2. Supported installation route

The upstream repository currently documents Codex CLI installation as follows. Run these commands in a terminal with the working directory set to the DermCareAI_ONE repository:

~~~bash
codex plugin marketplace add google/elephant-goldfish-model
codex plugin add egm@egm
~~~

Start a new Codex session after installation. Confirm the EGM skills are visible, then select the appropriate skill from the Codex skill picker. Do not assume a plugin cache path; use the absolute skill path reported by the installed skill inventory.

For ChatGPT desktop, use the published EGM plugin listing from the upstream README. Cloud/Work sessions have additional limitations: perform a Goldfish review only if the current session exposes a real fresh-context subagent tool and the required isolation parameters. If not, stop the Goldfish stage and report it as unavailable.

### VS Code, Copilot, and Continue

The upstream harness matrix documents Codex, Claude, and Antigravity routes, with additional host-specific integrations and qualified ChatGPT support. It does not establish a verified native VS Code Copilot or Continue integration. A folder or compatibility manifest in the upstream repository is not proof of end-to-end support.

For this repository's VS Code workflow, use a supported Codex CLI installation from the integrated terminal or another explicitly supported EGM host. Do not claim that an Ollama model configured in Continue automatically supplies EGM's fresh-context subagents. Local model selection, reviewer spawning, filesystem access, and review isolation are separate capabilities and must be tested in the chosen host.

## 3. Repository layout and artifact locations

~~~text
AGENTS.md                       Project-wide AI instructions and EGM artifact directory
.dev/docs/                      Ignored working briefs, drafts, and review reports
docs/EGM_INTEGRATION.md         This integration and operating guide
docs/designs/README.md          Approved design index and lifecycle
docs/designs/                   Reviewed, versioned design specifications
.github/agents/                 Existing CodeSwarm X 3.0 agent definitions
.codeswarm/                     Existing CodeSwarm memory and validation tooling
~~~

The root `AGENTS.md` contains the EGM artifact directive:

~~~text
EGM artifact directory: .dev/docs
~~~

Keep working material in `.dev/docs/`. Move only reviewed and explicitly approved specifications into `docs/designs/`. Do not commit private reviewer transcripts or scratch artifacts.

## 4. Full-project rollout

Apply EGM across the project in bounded workstreams rather than generating documentation for every folder in one unreviewed pass.

| Workstream | Scope to inspect | Expected design artifacts |
|---|---|---|
| Platform architecture | Root structure, PWA, Capacitor, FastAPI, data stores, object storage | Platform baseline and context map |
| Backend and API | Authentication, tenant authorization, clinical APIs, commerce, prescriptions, audit | Backend/API boundary specifications |
| Clinical workflows | Patient 360, encounters, examination, lesions, consent, sign-off | Clinical workflow specifications |
| Clinical AI | Assistive lane, adapters, model provenance, abstention, validation and activation gates | Clinical AI governance and model lifecycle specifications |
| Web/PWA and native wrapper | React/Vite client, offline behavior, API integration, Capacitor | Client architecture and synchronization specifications |
| Data and privacy | PostgreSQL, optional Firestore, media, retention, export/deletion, audit | Data lifecycle and privacy architecture |
| Security and operations | Tenant isolation, secrets, CI/CD, deployment, monitoring, backup and recovery | Threat model and operations specifications |

### Initial sequence

1. Read the current root README, `AGENTS.md`, `.github/copilot-instructions.md`, and the key architecture, privacy, security, clinical AI, and CI documents.
2. Use EGM bootstrap on a controlled subtree at a time. Review generated directory contracts before accepting them; do not overwrite existing human-maintained READMEs blindly.
3. Start with the platform baseline in `docs/designs/DERMCAREAI_PLATFORM_BASELINE.md`. Treat it as a draft context map, not as an already reviewed design.
4. Create or update one design specification per substantial workstream. Avoid one enormous specification that hides subsystem-specific decisions.
5. Run EGM review with the intended Goldfish stages and fresh-context subagents. Record skipped or unsupported stages as NOT RUN, never PASS.
6. Triage the findings with the human maintainer. Update the design and request another review where appropriate.
7. Obtain explicit human architecture approval and, for clinical/security/privacy changes, the relevant accountable domain approvals.
8. Hand approved specifications to CodeSwarm X 3.0 with scoped files, acceptance criteria, tests, risks, and rollback boundaries.
9. Run EGM drift reporting against approved designs as a periodic documentation check. The upstream guide recommends a weekly review cadence; teams may set a different cadence based on change rate and risk.

The upstream bootstrap skill requires a pause for user approval when it discovers more than 15 subdirectories. Follow that gate. For DermCareAI, prefer the bounded workstreams above and exclude generated, dependency, build, cache, and test-only trees where appropriate.

## 5. Goldfish review integrity and known limitations

A valid Goldfish review requires actual fresh subagent contexts. The parent agent must not write simulated independent reports. If the current host cannot spawn reviewers or establish a fresh context, stop the review and report the limitation.

Fresh conversation context is not equivalent to an isolated filesystem or instruction environment. The upstream EGM Codex guide records a known issue in which host project/user instruction files may still be present in reviewer context. Therefore:

- Do not put secrets, patient data, private notes, or sensitive operational details into the workspace or instructions.
- Provide reviewers with a deliberate reading list and explicit review questions.
- Record the host/runtime and version, skill/plugin version, reviewer completion evidence, and known isolation limits.
- Do not represent a review as independent if all reviewers ran in the same conversation context.
- Treat review findings as advisory until a human maintainer accepts them.

## 6. Clinical, privacy, and security safeguards

All EGM inputs and artifacts must use synthetic or approved anonymized data. Never supply patient names, identifiers, clinical records, photographs, credentials, API keys, tokens, production certificates, or incident evidence.

The current application boundary remains unchanged:

- Clinical AI output is assistive and physician-final.
- The application must not autonomously diagnose, prescribe, place orders, sign, or silently modify a signed encounter.
- Diagnostic AI production activation remains separately governed and fail-closed.
- Patient-linked image review requires the existing consent and authorization controls.
- PostgreSQL is required for the clinical workflow SQL store in production; the current patient-registration API path also writes a registry document to Firestore through the Firebase Admin SDK. Treat this as a hybrid persistence boundary. Firestore Rules do not authorize Admin-SDK operations; the API must enforce its own controls.
- Tenant isolation, auditability, authentication, and backend authorization must not be weakened to make a design simpler.

EGM review, bootstrap, and drift reports do not constitute clinical validation, regulatory clearance, privacy approval, security certification, or production authorization.

## 7. Cost and execution policy

- EGM is optional; the application continues to build and run without it.
- No new runtime packages, database migrations, external API calls, secrets, or GitHub Actions model jobs are required by this integration.
- Plugin installation and model usage are developer-host specific and may incur account/model costs.
- Review only the design scope needed for the task. Use staged subtrees and explicit reviewer reading lists to constrain context and cost.
- Do not run unattended or recurring LLM reviews until a separate owner, budget, provider approval, privacy assessment, and failure policy exist.

## 8. Validation checklist

Before treating EGM as operational on a developer workstation:

- [ ] Install the whole upstream plugin using a supported host route.
- [ ] Start a new host session and confirm the expected EGM skills are discovered.
- [ ] Run a harmless documentation-only bootstrap on a small, non-sensitive subtree.
- [ ] Confirm existing READMEs are not overwritten without review.
- [ ] Confirm the host can spawn fresh reviewers; otherwise record Goldfish review as unavailable.
- [ ] Verify reviewers receive only the intended files and no patient data or secrets.
- [ ] Run a small design review and preserve its actual report in `.dev/docs/`.
- [ ] Have a human maintainer triage findings before promoting any design to `docs/designs/`.
- [ ] Run the relevant existing tests/CI for any later implementation changes.

**Current integration state:** repository instructions and documentation are prepared. Plugin installation, bootstrap execution, Goldfish review, EGM drift reporting, and host-specific verification have not been run in this PR.
