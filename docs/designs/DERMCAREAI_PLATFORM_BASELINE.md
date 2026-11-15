# DermCareAI Platform Baseline

**Document status:** BASELINE DRAFT — NOT HUMAN-APPROVED  
**Scope:** Whole-repository architecture context and source-of-truth map  
**Repository baseline inspected:** `feat/egm-project-integration` at `adec7331fa154941ac53ce5faf5640fec7dcad39`  
**Prepared:** 2026-11-15  
**Purpose:** Give downstream EGM designs, maintainers and implementation agents a traceable description of documented intent, current engineering-release scope, observed implementation boundaries and unresolved architecture decisions.

## Authority and use

This document is a context map, not an architecture decision record, product requirements document, release approval, clinical validation report, or authorization to implement or deploy.

It does not approve a database topology, authorize migration, make de-scoped workflows production-capable, or grant clinical, privacy, security, regulatory or production approval. It records current evidence and unresolved questions so that downstream designs can make explicit decisions.

Each downstream feature or subsystem specification must add its own problem statement, goals/non-goals, alternatives, trade-offs, data/API contracts, failure modes, security/privacy/clinical impact, acceptance criteria, verification plan, rollback strategy and accountable approvers. Do not force all of that detail into this repository-wide map.

## 1. Product intent and current engineering-release scope

DermCareAI's product direction covers a dermatology clinic platform, including patient lookup, encounter documentation, longitudinal lesion information, AI-assisted image review, billing, pharmacy, notifications, auditability and operational support. This is product intent and a list of documented product areas; it is not a claim that every listed workflow is supported in the current engineering release or approved for clinical production use.

### Current engineering-release scope

The current scope is defined by [PWA + Capacitor migration acceptance](../PLATFORM_MIGRATION_ACCEPTANCE.md). That document states that the engineering release validates:

- Patient lookup and tenant-safe patient registration.
- Read-only clinical summary, prescription and procedure views.
- Suggestion-only Clinical AI APIs.
- Clinician-approved guideline lookup with provenance and audit events.

The same acceptance document explicitly de-scopes the following legacy Expo-only workflows from this release: encounter creation/editing, lesion body-map capture and native lesion workflows, prescription creation/editing, screening UI/workflow, appointments, billing UI/workflow and pharmacy UI/workflow. These may exist in parts of the backend or historical documentation; their existence does not make them supported capabilities in this release.

Do not describe a capability as production-supported merely because a route, schema, screen, model, test or old design document exists. Confirm the release acceptance criteria and the relevant end-to-end implementation evidence.

## 2. Current documented and observed architecture

### Client, identity and API flow

~~~text
Browser
  └── React/Vite PWA (webapp/)
        └── Firebase Authentication sign-in
              └── Firebase ID token returned to client
                    └── HTTPS request to FastAPI
                          Authorization: Bearer <Firebase ID token>

Capacitor Android/iOS container
  └── packages the same webapp/ PWA bundle
        └── uses the same client authentication and API flow

FastAPI persistence paths observed in this repository:
  ├── PostgreSQL clinical store
  │     encounters, lesions, lesion observations, consents,
  │     clinical-media metadata, sign-offs, follow-ups and AI reviews
  │
  ├── Firestore Admin SDK patient-registry path
  │     POST /api/v1/clinical/patients
  │     backend/patient_store.py
  │
  └── Cloudinary signed-upload authorization
        POST /media/sign-upload
        upload signature parameters are issued by the backend
~~~

Capacitor is a native container around the same canonical PWA bundle. It is not a separately designed clinical user interface or a second source of clinical workflow behavior.

Firebase Authentication is an identity provider, not a network proxy through which clinical API traffic passes. The client obtains an ID token from Firebase Authentication and presents it to FastAPI as a Bearer token. The backend verifies the token and applies role and tenant authorization.

### Components and observed responsibilities

| Component | Documented or source-observed responsibility | Important boundary |
|---|---|---|
| `webapp/` | Canonical React/Vite PWA client | Keep one clinical UI implementation |
| Capacitor | Android/iOS container for the same web bundle | Native packaging, permissions and platform builds require their own verification |
| `backend/` | FastAPI API and domain services | Authentication, role checks, tenant checks, resource authorization, validation and audit belong at the server boundary |
| Firebase Authentication | Clinician identity and ID-token issuer | A valid identity token alone does not grant access to every tenant/resource |
| PostgreSQL | Production database required by the clinical SQLAlchemy store | Current clinical-store tables include encounters, lesions, observations, consents, media metadata, sign-offs, follow-ups and AI reviews |
| Firestore | Current patient-registry write path through Firebase Admin SDK; also has client Security Rules for direct client access where used | It is not the primary store for the longitudinal clinical-store tables; this is a hybrid persistence boundary that needs an explicit architecture decision |
| Cloudinary | Clinical-image object storage integration | The inspected `/media/sign-upload` endpoint returns signed-upload parameters after role, tenant-claim and consent checks; this is not evidence of signed download/access URLs |
| `.github/` | CI, agent definitions and repository governance | Preserve workflow permissions, branch protections and protected control-plane paths |
| `.codeswarm/` | CodeSwarm memory, tests and tools | Preserve append-only memory and validator integrity rules |
| `docs/` | Architecture, clinical, privacy, security, deployment and readiness records | Reconcile stale or conflicting claims against code and approved decisions |

### Persistence split: important unresolved architecture decision

The inspected implementation shows two distinct persistence paths:

1. `backend/clinical.py` exposes `POST /api/v1/clinical/patients` and calls `backend/patient_store.py`. That store uses the Firebase Admin SDK to create a document in the Firestore `patients` collection.
2. `backend/clinical_store.py` defines SQLAlchemy-backed tables for encounters, lesions, lesion observations, consents, clinical-media metadata, encounter sign-offs, follow-ups and AI reviews. It calls `require_postgres_in_production`, so PostgreSQL is required for this clinical store in production.

Therefore, the phrase “PostgreSQL is the production clinical source of truth” must be scoped to the clinical SQL store and must not conceal the current Firestore-backed patient-registration path. The platform currently has a hybrid persistence boundary. This PR documents that fact; it does not migrate records or change runtime persistence.

A dedicated architecture decision is required to determine whether the patient registry remains in Firestore, moves into PostgreSQL, or uses another governed arrangement. That decision must address identity and patient identifiers, cross-store consistency, tenant isolation, audit, idempotency, export/correction/deletion, retention, backup/recovery, migration and rollback. Do not silently implement a migration as part of this documentation change.

## 3. Clinical workflow and data lifecycle context

The README describes a broader product workflow across patient lookup, encounters, examination, lesions, assessment, review and clinician sign-off. The current engineering release scope is narrower, as listed in §1. Backend route or schema presence does not override the release acceptance document.

Clinical records and images are sensitive. Patient-linked media requires the existing consent and authorization controls. Signed records, audit events, tenant boundaries and provenance are safety and data-integrity controls.

### Object-storage authorization

The inspected `backend/media.py` endpoint `POST /media/sign-upload`:

- Requires a doctor/admin role.
- Requires organization and clinic claims.
- Checks active consent for clinical-image upload purposes (with separate non-clinical avatar/logo purposes).
- Applies a per-user rate limit.
- Produces Cloudinary signed-upload parameters using the configured server-side secret.

The response is an upload-signature contract. Do not describe this evidence as proof that object downloads, reads or all media access URLs are signed or authorized. Those access paths require their own inspection and specification.

## 4. Clinical AI boundary

The [Clinical AI Production Activation](../CLINICAL_AI_PRODUCTION_ACTIVATION.md) document defines a physician-final, assistive production workflow.

The documented assistive lane includes structured differential-support suggestions from deterministic rules, image-quality assessment, candidate-region measurement for clinician review and separately gated generative image description. Generative assist requires its own gate, a pinned model revision and applicable image consent.

The documented production boundary does not permit autonomous diagnosis, autonomous treatment or prescribing, autonomous orders, automatic changes to signed clinical records, silent model promotion or production use of an unvalidated diagnostic artifact.

Any future diagnostic capability requires a separately governed deployment artifact, independent evidence, clinical validation, privacy/security review, regulatory assessment, accountable approval and rollback evidence. A software test, model endpoint or EGM review is not clinical validation.

## 5. Security, privacy and operational context

### Authentication and authorization

The inspected `backend/auth.py` verifies Firebase ID tokens with revocation checking and extracts role/roles and token claims. Clinical routes use role dependencies and require organization and clinic claims. Resource-level tenant checks must still be applied by the relevant route/store; authentication is not a substitute for authorization.

### Firestore rules versus Admin SDK calls

The repository's `firestore.rules` protects direct client-SDK access to configured Firestore collections, including tenant and active-doctor constraints.

The backend patient-registry path uses the Firebase Admin SDK. Admin SDK operations execute in a trusted server context and bypass Firestore Security Rules. The rules therefore do not authorize or constrain the server-side `POST /api/v1/clinical/patients` operation. That route must independently verify the caller's role, organization/clinic claims, active-doctor status where applicable, and all relevant resource ownership. The inspected route/store contains role/tenant derivation and an active-doctor check for non-admin doctors; preserve and test those API controls.

Official Firebase references:
- [Firebase Security Rules and Admin SDK trust boundary](https://developers.google.com/learn/pathways/quizzes/firebase-security-layers)
- [Verify Firebase ID tokens on a custom backend](https://firebase.google.com/docs/auth/admin/verify-id-tokens)

### Known privacy and operational gaps

The privacy runbook records that:

- Patient-data export is not complete across all application and provider stores.
- There is no coordinated deletion workflow spanning clinical and commerce databases, Firebase/Firestore, media storage, vendors, logs and backups.
- Clinical media can carry `retention_until`, but there is no automated retention scheduler that also deletes external objects.

These are known application and operational gaps. They need owners, policy decisions, release-impact assessment and verified evidence. Do not invent a retention period or delete clinical data solely because consent was withdrawn.

New designs should address identity and least privilege, tenant/object authorization, consent enforcement, server-side secret handling, audit integrity, PHI minimization, retention/legal holds, export/correction/deletion, backup/restore, incident response and disaster recovery.

## 6. Engineering governance and EGM hand-off

CodeSwarm X 3.0 remains the repository's implementation orchestrator. Its documented roles separate planning, coding, debugging, optimization, memory evolution and read-only memory integrity verification.

EGM complements CodeSwarm:

- EGM helps clarify requirements, draft specifications and challenge them through fresh-context reviewers where the host supports genuine isolated subagent conversations.
- Human maintainers decide which findings to accept and approve the resulting design.
- CodeSwarm implements only an approved, scoped design and retains its bounded retries, protected control-plane paths, validation and evidence requirements.

EGM does not implement, approve, merge, deploy or authorize clinical use. Human architecture, clinical, security, privacy and regulatory approvals remain separate.

## 7. Known documentation drift and reconciliation

The repository contains conflicting or stale architecture statements. The verified conflicts and their disposition are tracked in [Documentation Drift Register](../DOCUMENTATION_DRIFT_REGISTER.md).

Important items include:
- `docs/CI_CONTRACT.md` previously described Expo web-export smoke checks, while the current PR workflow builds the PWA, generates/synchronizes Capacitor Android/iOS projects and checks for active Expo/React Native package references in `webapp/`.
- `docs/PLATFORM_MIGRATION_ACCEPTANCE.md` previously said no CI/deployment path could reference the words Expo or React Native, even though CI deliberately contains a guard that searches for those references. The requirement is about the absence of Expo/React Native build/export/deployment paths, not the absence of a text guard.
- The README and Firebase setup documentation previously described Firestore as simply optional, without disclosing the current Admin-SDK-backed patient-registration path.
- The CodeSwarm orchestrator still has an obsolete `dermcareai/` React Native/Expo reference architecture sketch and legacy Expo/mobile validation instructions. That file is a protected control-plane asset. This EGM documentation change does not modify it; reconcile it only through the authorized CodeSwarm-Evolver/control-plane maintenance process.

## 8. Design questions for the full-project EGM rollout

1. **Patient registry and clinical persistence:** Should the patient registry move from Firestore to PostgreSQL, remain split, or use another architecture? What are the authoritative identifiers and consistency rules?
2. **Tenant isolation:** Are patient, encounter, lesion, media, invoice, prescription and audit operations scoped to the authenticated organization, clinic and authorized actor at every API/store boundary?
3. **Direct Firestore access:** Which clients/features still need direct Firestore SDK access, and which collections should be API-only? Are Firestore Rules tests aligned with that inventory?
4. **Offline behavior:** What clinical data can be cached, what mutations are permitted offline, how are conflicts/replay/idempotency handled, and how are consent or authorization changes applied to queued work?
5. **Clinical record lifecycle:** Which encounter states are mutable, signed, amended or immutable, and how are provenance and audit events linked?
6. **Media lifecycle:** How are upload authorization, consent, object access, metadata, retention, legal holds, export and deletion coordinated across Cloudinary and PostgreSQL?
7. **Clinical AI lifecycle:** How are input quality, model identity/revision, provenance, uncertainty, abstention, clinician accept/reject/override and evaluation evidence represented?
8. **Privacy operations:** Who owns access/export, correction, deletion, retention, backups, legal holds and incident response, and what is the evidence of successful execution?
9. **Client/native parity:** How are PWA and Capacitor releases versioned, tested and rolled back without divergent clinical behavior?
10. **Production operations:** What are the deployment, observability, backup/restore, disaster-recovery and incident-response acceptance gates?
11. **Evidence and approvals:** Which checks are automated, which require external evidence, and which accountable roles approve each release decision?

These are questions for scoped downstream specifications, not claims that every underlying function is absent. Each question requires source inspection and, where appropriate, a dedicated EGM design.

## 9. Review, ownership and approval record

| Gate | Status | Evidence / accountable role |
|---|---|---|
| Repository baseline assembled | PREPARED | Source files and commit listed in §§2, 10 |
| Initial EGM review | STAGES 5–8 COMPLETED | Consolidated local report under ignored `.dev/docs/`; not committed |
| EGM implementation-readiness stage | NOT RUN | Baseline has no implementation plan; do not mark this stage passed |
| Goldfish isolation | PARTIALLY EVIDENCED | Review reported separate fresh agent conversations; filesystem and instruction-file isolation were not established |
| Architecture approval | PENDING | Platform architecture owner / repository maintainer |
| Clinical approval | PENDING WHEN APPLICABLE | Designated clinical safety owner |
| Security approval | PENDING WHEN APPLICABLE | Designated security owner |
| Privacy approval | PENDING WHEN APPLICABLE | Clinic privacy lead |
| Regulatory assessment | PENDING WHEN APPLICABLE | Organization's accountable regulatory/legal owner |
| Production/release approval | NOT GRANTED | Deployment/release owner after all applicable evidence gates |
| Implementation authorization | NOT GRANTED BY THIS DOCUMENT | Requires an approved downstream design and normal change control |

The platform architecture owner, with the relevant domain owners, determines which clinical, security, privacy and regulatory approvals apply to each downstream design. Individual names must be assigned by the organization; this baseline does not invent them.

## 10. Source documents and code evidence

- [Root README](../../README.md)
- [PWA/Capacitor migration architecture](../PLATFORM_MIGRATION_ARCHITECTURE.md)
- [PWA/Capacitor migration acceptance](../PLATFORM_MIGRATION_ACCEPTANCE.md)
- [CI contract](../CI_CONTRACT.md)
- [Documentation drift register](../DOCUMENTATION_DRIFT_REGISTER.md)
- [Clinical AI production activation](../CLINICAL_AI_PRODUCTION_ACTIVATION.md)
- [Privacy operations](../PRIVACY_OPERATIONS.md)
- [Security threat model](../SECURITY_THREAT_MODEL.md)
- [Firebase setup](../FIREBASE_SETUP.md)
- [Firestore rules](../../firestore.rules)
- [Backend authentication](../../backend/auth.py)
- [Patient registration route](../../backend/clinical.py)
- [Patient registry store](../../backend/patient_store.py)
- [Clinical SQL store](../../backend/clinical_store.py)
- [Media upload-signature route](../../backend/media.py)
- [Pull request workflow](../../.github/workflows/pull-request-gates.yml)
- [Continuous evaluation workflow](../../.github/workflows/continuous-evaluation.yml)
- [CodeSwarm X 3.0 orchestrator](../../.github/agents/CodeSwarm.agent.md)
- [Copilot repository instructions](../../.github/copilot-instructions.md)

## 11. Glossary

| Term | Meaning in this repository |
|---|---|
| Patient 360 | Product term for a consolidated patient view; exact release scope is controlled by migration acceptance |
| CodeSwarm X 3.0 | Repository engineering orchestrator with separate planning, coding, debugging, optimization and memory-governance roles |
| Evolver | CodeSwarm agent responsible for controlled memory evolution and eligible prompt changes under evidence thresholds |
| Control-plane protection | Restrictions on who may change CodeSwarm agents, memory, validators and related workflows |
| Bounded retries | Explicit maximum number of correction/validation attempts before escalation |
| Append-only memory | CodeSwarm learning history is preserved rather than silently rewritten |
| EGM | Elephant-Goldfish Model: development-time specification and review workflow |
| Elephant | EGM role that uses project context to explore requirements and draft a specification |
| Goldfish | EGM reviewer that critiques a document from a fresh subagent conversation |
| Fresh-context review | Reviewer starts without the parent conversation; it does not by itself prove filesystem or instruction-file isolation |
| EGM bootstrap | The upstream `egm-bootstrap` skill that generates or updates repository documentation contracts; generated files require human review |
