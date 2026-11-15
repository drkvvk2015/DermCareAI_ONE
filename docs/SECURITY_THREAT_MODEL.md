# DermCareAI Security Threat Model

## Trust boundaries

1. Browser PWA and Capacitor container (same canonical `webapp/` client)
2. Firebase Authentication and client-issued ID tokens
3. FastAPI clinical/API boundary
4. PostgreSQL-backed clinical, commerce and audit stores
5. Firestore client-SDK access and separate backend Admin-SDK operations
6. Cloudinary/object-media storage
7. Payment providers
8. Messaging providers
9. Operational/deployment infrastructure

## High-risk threats and controls

| Threat | Primary control |
|---|---|
| Unauthenticated API/AI use | Firebase ID-token verification with revocation checking, role checks and rate limits |
| Cross-tenant or cross-doctor access through FastAPI | API-level role, organization/clinic claim, resource-ownership and tenant-scoped store checks; Firestore Rules are not a substitute for backend authorization |
| Unauthorized direct Firestore client access | Firestore Security Rules for the collections accessed directly by client SDKs; active-doctor and tenant-claim/document matching |
| Privileged server write bypasses Firestore Rules | Treat Firebase Admin SDK as trusted server authority; enforce role, tenant, actor and resource authorization in the API before every Admin-SDK read/write |
| Client-extracted Cloudinary secret | Keep API secret server-side; issue narrowly scoped upload-signature parameters only after API authorization and consent checks |
| Payment tampering | Server-derived invoice totals + exact signature verification + captured-state/event-type validation + idempotency |
| Pharmacy race condition | Durable transactional stock ledger + canonical expiry validation + FEFO date filtering + tenant scope |
| Audit manipulation | Server-generated audit events + append-only storage |
| PHI leakage to notifications | Payload allow-list and template controls |
| Model substitution | Model registry + checksum + controlled promotion |
| Model overconfidence | Calibration + abstention + clinician review |
| Dependency compromise | Dependabot + CodeQL + dependency auditing + SBOM |
| Inference denial-of-service | Request-size limits enforced during chunked reads + decoded image validation + bounded inference concurrency/rate limiting |
| Production configuration drift | Environment validation + immutable deployment artifacts |

## Current data-store boundary observed in the repository

The current patient-registration API path is hybrid:

- `POST /api/v1/clinical/patients` in `backend/clinical.py` calls `backend/patient_store.py`, which writes a patient-registry document to Firestore using the Firebase Admin SDK.
- `backend/clinical_store.py` stores encounters, lesions, lesion observations, consents, clinical-media metadata, sign-offs, follow-ups and AI reviews in its SQLAlchemy store; production configuration requires PostgreSQL.
- `firestore.rules` governs direct client-SDK access to Firestore collections. It does not govern Admin-SDK operations executed by the backend.

Firebase explicitly documents that the Admin SDK is intended for trusted server environments and bypasses Firebase Security Rules. Consequently, the backend patient-registration route must enforce its own authentication, role, tenant and resource controls. The inspected route requires doctor/admin role and organization/clinic claims; the store checks active doctor status for non-admin doctors and derives stored tenant fields from server arguments. Preserve and test this API-level boundary.

This split is a documented architecture decision to resolve, not an authorization to migrate data in this threat-model update. See [Documentation Drift Register](DOCUMENTATION_DRIFT_REGISTER.md) and [Platform Baseline](designs/DERMCAREAI_PLATFORM_BASELINE.md).

Official Firebase references:
- [Firebase Security Rules and Admin SDK trust boundary](https://developers.google.com/learn/pathways/quizzes/firebase-security-layers)
- [Verify Firebase ID tokens on a custom backend](https://firebase.google.com/docs/auth/admin/verify-id-tokens)

## Cloudinary upload-signature boundary

The inspected `POST /media/sign-upload` endpoint in `backend/media.py` requires doctor/admin role, organization/clinic claims, rate limiting and active consent for clinical-image purposes (with specific non-clinical avatar/logo exceptions). It creates an HMAC signature for Cloudinary upload parameters using a server-side secret.

This establishes a signed-upload authorization path. It does not by itself establish that object reads, downloads or every access URL are signed. Those paths must be separately inspected and threat-modeled before describing them as protected by signed access URLs.

## Clinical safety principle

AI output is an assistive signal. The application must never present model confidence as diagnostic certainty and must preserve clinician interpretation as the final clinical decision.

## Production safety invariants

- A signed Razorpay webhook cannot settle an invoice unless the event is exactly `payment.captured` and the payment entity reports `captured`.
- Pharmacy batch expiry is canonical `YYYY-MM-DD` at both API and persistence boundaries; malformed legacy rows are excluded from FEFO allocation.
- Prescription-linked dispensing is tenant- and patient-scoped; direct commerce dispensing is restricted to pharmacy/admin roles.
- Clinical image uploads are bounded while streaming, then decoded and checked against an allow-listed MIME/format pair before inference.
- Clinical AI remains suggestion-only and physician-final; no unvalidated diagnostic model is activated by this application-level production path.
