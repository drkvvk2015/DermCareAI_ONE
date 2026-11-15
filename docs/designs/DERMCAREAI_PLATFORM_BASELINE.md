# DermCareAI Platform Baseline

**Document status:** BASELINE DRAFT — NOT EGM-REVIEWED; NOT HUMAN-APPROVED  
**Scope:** Whole repository architecture context  
**Repository baseline:** `main` at `e466a54d3ce57a503bc53120aede5385df7bcdf9`  
**Prepared:** 2026-11-15  
**Purpose:** Provide a starting context map for subsequent EGM design work. This document records documented intent and known constraints; it is not proof that every implementation detail has been independently verified.

## 1. Product context

DermCareAI is a healthcare-oriented dermatology clinic platform. The repository README describes patient 360, encounter documentation, longitudinal lesion tracking, AI-assisted image review, billing, pharmacy, notifications, auditability, and production operations.

The software architecture and clinical AI policy intentionally separate assistive workflows from high-consequence diagnostic use. The treating physician retains final clinical decision authority.

## 2. Current documented architecture

~~~text
Browser / installed PWA
        |
        +------------------+
        |                  |
        v                  v
React/Vite PWA        Capacitor wrapper
(webapp/)             Android / iOS
        |                  |
        +--------+---------+
                 |
                 v
           Firebase Auth
                 |
                 v
           FastAPI /api/v1
                 |
       +---------+----------+
       |                    |
       v                    v
  PostgreSQL           Object storage
 clinical source       clinical media /
   of truth            uploaded objects

Firestore: optional; not the primary clinical datastore
~~~

### Components and boundaries

| Component | Documented responsibility | Design implications |
|---|---|---|
| `webapp/` | Canonical React/Vite PWA client | Keep a single clinical UI implementation |
| Capacitor | Native Android/iOS wrapper around the same web bundle | Native packaging and platform permissions require separate verification |
| `backend/` | FastAPI API and domain services | Enforce authentication, authorization, tenant scope, validation, and audit server-side |
| Firebase Authentication | Clinician identity | Validate identity tokens and tenant/role claims at the backend boundary |
| PostgreSQL | Production clinical source of truth | Clinical persistence and transactions must remain authoritative here |
| Firestore | Optional service | Do not introduce a second clinical source of truth or an unreviewed offline cache |
| Object storage | Clinical media and uploaded objects | Use consent-aware backend authorization and server-side signing |
| `.github/` | CI, agent definitions, repository governance | Preserve branch protections, workflow permissions, and protected control-plane paths |
| `.codeswarm/` | CodeSwarm memory, tests, and tools | Preserve append-only memory and validator integrity rules |
| `docs/` | Architecture, clinical, privacy, security, deployment, and readiness references | Use documentation as a decision record; reconcile stale or conflicting documents |

The root README and platform migration architecture identify `webapp/` as the canonical PWA and explicitly state that Capacitor wraps the same web bundle. Legacy instructions that describe a separate `dermcareai/` React Native/Expo application are stale and must not be used as the implementation baseline.

## 3. Clinical workflow context

The README documents a workflow spanning patient 360, encounter documentation, examination, lesion tracking, assessment, review, and clinician sign-off. The specific API contracts and state transitions must be verified against the current backend and webapp before a feature design is approved.

Clinical records are sensitive. Patient-linked media requires consent and authorized access. Audit events, signed-record integrity, and tenant boundaries are architectural controls rather than optional implementation details.

## 4. Clinical AI boundary

The current Clinical AI Production Activation document describes a physician-final, assistive workflow.

Permitted assistive examples include structured differential-support suggestions from deterministic rules, image-quality assessment, candidate-region measurements for clinician review, and separately gated generative image description.

The documented production boundary does not permit:
- autonomous diagnosis;
- autonomous treatment execution or prescribing;
- autonomous orders;
- automatic changes to signed clinical records;
- silent model promotion;
- production use of an unvalidated diagnostic artifact.

Generative assist requires its own gate, a pinned model revision, and applicable image consent. Any future diagnostic capability requires a separately governed deployment artifact, independent evidence, clinical validation, privacy/security review, regulatory assessment, accountable approval, and rollback evidence.

An EGM reviewer must not infer clinical validity from implementation details, test coverage, model availability, or a passing software pipeline.

## 5. Security, privacy, and operational context

The repository's threat model identifies trust boundaries across the client, Firebase Authentication, API, clinical data stores, media storage, payment providers, messaging providers, and operational infrastructure.

The privacy runbook explicitly records limits in current patient export and coordinated deletion coverage, as well as the absence of an automated retention scheduler for clinical media. These are known design and operational gaps, not assumptions that should be papered over in new specifications.

New designs should address, where relevant:
- identity, tenant and object-level authorization;
- consent enforcement for patient-linked media;
- secret handling and server-side credential use;
- audit integrity and non-repudiation;
- PHI minimization in logs, telemetry, prompts, and artifacts;
- retention, legal holds, export, correction and deletion ownership;
- backup, restore, incident response and disaster recovery;
- payment/pharmacy transaction integrity where those domains are affected.

## 6. Engineering and change governance

CodeSwarm X 3.0 is the repository's implementation orchestration system. Its documented roles separate planning, coding, debugging, optimization, memory evolution, and read-only memory integrity verification.

EGM complements this system:
- EGM helps clarify requirements, draft design specifications, and challenge them with fresh reviewers.
- Human maintainers approve the accepted design and applicable domain decisions.
- CodeSwarm implements only the approved scope and must retain its bounded retries, control-plane protection, validation, and evidence requirements.

EGM does not supersede CodeSwarm authority boundaries, and neither system can replace a human clinical or security approval.

## 7. Known documentation drift to resolve

The current root README and `docs/PLATFORM_MIGRATION_ARCHITECTURE.md` describe `webapp/` as the canonical client. The pre-integration `.github/copilot-instructions.md` described `dermcareai/` and React Native/Expo paths that are absent from the current root tree. This integration PR updates the Copilot instructions to match the documented platform direction.

The CodeSwarm orchestrator file also contains a reference architecture sketch with a `dermcareai/` path while instructing agents to inspect the actual tree. That protected control-plane file is not changed in this PR. Reconcile it only through the existing CodeSwarm-Evolver/control-plane maintenance process; do not edit it as an incidental EGM change.

## 8. Design questions for the full-project EGM rollout

1. **API boundaries:** Are clinical, commerce, pharmacy, payment, messaging, and administrative domains clearly separated at the service and authorization layers?
2. **Tenant isolation:** Is every patient, encounter, lesion, media object, invoice, prescription, and audit query scoped to the authenticated tenant and authorized actor?
3. **Offline behavior:** What is the canonical offline data set, conflict-resolution policy, replay/idempotency contract, and safe behavior when consent or authorization changes while a device is offline?
4. **Clinical record lifecycle:** Which encounter states are mutable, signed, amended, or immutable, and how are provenance and audit events linked?
5. **Media lifecycle:** How are upload authorization, consent, metadata, object access, retention, legal hold, export, and deletion coordinated?
6. **Clinical AI lifecycle:** How are input quality, model identity/revision, provenance, uncertainty, abstention, clinician accept/reject/override, and evaluation evidence represented?
7. **Privacy operations:** What are the accountable owners and verified procedures for access/export, correction, deletion, retention, backups, and incident response?
8. **Client/native parity:** How are PWA and Capacitor releases versioned, tested, and rolled back without creating divergent clinical behavior?
9. **Production operations:** What are the deployment, observability, backup/restore, disaster-recovery, and incident-response acceptance gates?
10. **Evidence and governance:** Which checks are automated, which require external evidence, and who is authorized to approve each release decision?

These are review questions, not claims that the implementation currently fails them. Each requires source inspection and, where appropriate, a dedicated design specification.

## 9. Review and approval record

| Gate | Status | Evidence |
|---|---|---|
| Repository context assembled from current README and selected architecture/policy documents | PREPARED | Source commit recorded above |
| Live EGM bootstrap run | NOT RUN | EGM host not invoked during preparation of this draft |
| Goldfish fresh-context review | NOT RUN | Requires supported host and real fresh-context subagents |
| Human architecture approval | PENDING | No approval recorded |
| Clinical/privacy/security domain approval | PENDING / AS APPLICABLE | Obtain for affected designs |
| Implementation authorization | NOT GRANTED BY THIS DOCUMENT | Use approved designs and normal change control |

## 10. Source documents

- [Root README](../../README.md)
- [Platform migration architecture](../PLATFORM_MIGRATION_ARCHITECTURE.md)
- [Platform migration acceptance](../PLATFORM_MIGRATION_ACCEPTANCE.md)
- [Clinical AI production activation](../CLINICAL_AI_PRODUCTION_ACTIVATION.md)
- [Privacy operations](../PRIVACY_OPERATIONS.md)
- [Security threat model](../SECURITY_THREAT_MODEL.md)
- [CI contract](../CI_CONTRACT.md)
- [EGM integration guide](../EGM_INTEGRATION.md)
