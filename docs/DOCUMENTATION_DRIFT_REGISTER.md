# Documentation Drift Register

**Baseline inspected:** `feat/egm-project-integration` at `adec7331fa154941ac53ce5faf5640fec7dcdf9`  
**Review date:** 2026-11-15  
**Purpose:** Track material documentation conflicts found during the EGM platform-baseline review and the source evidence used to reconcile them.

This register records documentation and architecture-description drift. It does not authorize application changes, data migrations, security-control weakening or production activation.

## Findings and dispositions

| ID | Priority | Finding | Source evidence | Disposition |
|---|---|---|---|---|
| DDR-001 | High | CI contract described Expo web-export smoke checks that are no longer in the current PR workflow. | `.github/workflows/pull-request-gates.yml`; `.github/workflows/continuous-evaluation.yml`; `docs/CI_CONTRACT.md` | **Corrected in this PR.** CI contract now describes PWA/Capacitor, TypeScript, lint/test/build, lockfile, Android/iOS sync and other configured gates. No Expo export/Doctor/prebuild job was found in the inspected active workflow set. |
| DDR-002 | Medium | Migration acceptance said no CI/deployment path could reference the strings Expo or React Native, while the PR workflow intentionally contains a negative guard that searches for those strings. | `docs/PLATFORM_MIGRATION_ACCEPTANCE.md`; `.github/workflows/pull-request-gates.yml` lines 105–110 | **Corrected in this PR.** The criterion now prohibits Expo/React Native build/export/prebuild/deployment jobs while permitting a negative dependency/reference guard. |
| DDR-003 | High | “Firestore is optional” and “PostgreSQL is the clinical source of truth” were too broad without disclosing the active Firestore-backed patient-registry write. | `backend/clinical.py` `POST /api/v1/clinical/patients`; `backend/patient_store.py`; `backend/clinical_store.py`; `firestore.rules` | **Clarified in this PR.** Documents now describe the hybrid boundary: patient registry create path in Firestore via Admin SDK; longitudinal clinical workflow tables in PostgreSQL. A dedicated architecture decision remains open. |
| DDR-004 | High | The security threat model did not distinguish direct client-SDK Firestore access from trusted backend Admin-SDK calls. | `backend/patient_store.py`; `backend/auth.py`; `firestore.rules`; Firebase official Admin-SDK guidance | **Clarified in this PR.** Firestore Rules govern direct client access; Admin SDK operations bypass those rules and require API-level authorization. The route/store controls are described without claiming complete authorization coverage for every resource path. |
| DDR-005 | Medium | Architecture diagram implied Firebase Auth was a network proxy and showed a retired Expo/React Native client, generic shared SQL persistence and “signed upload URLs.” | `docs/assets/architecture.svg`; `backend/media.py`; `backend/clinical_store.py`; `backend/patient_store.py` | **Corrected in this PR.** Diagram now shows PWA/Capacitor, client ID-token hand-off, split persistence paths and backend-issued Cloudinary signed-upload authorization. It does not claim signed download URLs. |
| DDR-006 | Medium | README/Firebase setup did not clearly distinguish the patient-registry Firestore path, PostgreSQL clinical workflow store and Admin-SDK authorization boundary. | `README.md`; `docs/FIREBASE_SETUP.md`; backend source files listed under DDR-003 | **Corrected in this PR.** Updated architecture and setup explanations and linked the baseline/drift register. |
| DDR-007 | Medium | CodeSwarm X 3.0 protected orchestrator still describes `dermcareai/` React Native/Expo as a reference architecture and retains legacy mobile/Expo validation instructions. | `.github/agents/CodeSwarm.agent.md` sections 2, 12.1, 12.3 | **Open — protected control-plane change.** Not modified by this EGM documentation PR. Route through the documented CodeSwarm-Evolver/control-plane maintenance process with the required evidence threshold and independent review. |

## Important architecture decision still open

The inspected implementation currently stores a patient-registry document through Firestore Admin SDK while clinical workflow data uses the PostgreSQL-backed SQLAlchemy clinical store. This creates a cross-store architecture boundary.

The platform owner must commission a dedicated design decision that covers:
- authoritative patient identifier and source of truth;
- referential integrity between patient registry and clinical workflow records;
- transaction/idempotency behavior across the store boundary;
- authorization and tenant isolation for every API operation;
- patient lookup and update paths (not just creation);
- audit/provenance and error recovery for partial failures;
- access/export/correction/deletion and retention across both stores;
- backup, restore, migration, rollback and cutover acceptance.

No data migration or application behavior change is included in this PR.

## Scope and verification limitations

- Workflow statements above are based on inspection of the repository's current workflow YAML at the baseline commit; they do not claim that any run passed.
- Backend statements are based on source inspection of the cited files; this register is not a penetration test or exhaustive route-by-route authorization audit.
- The EGM review reported fresh reviewer conversations, but workspace filesystem and instruction-file isolation were not independently established.
- The protected CodeSwarm control-plane discrepancy remains open until handled under its own authority process.

## Source references

- [PR workflow gates](../.github/workflows/pull-request-gates.yml)
- [Continuous evaluation](../.github/workflows/continuous-evaluation.yml)
- [Patient registration API](../backend/clinical.py)
- [Patient registry store](../backend/patient_store.py)
- [Clinical SQL store](../backend/clinical_store.py)
- [Firebase authentication](../backend/auth.py)
- [Firestore rules](../firestore.rules)
- [Media upload signing](../backend/media.py)
- [Firebase Admin SDK and Security Rules trust boundary](https://developers.google.com/learn/pathways/quizzes/firebase-security-layers)
