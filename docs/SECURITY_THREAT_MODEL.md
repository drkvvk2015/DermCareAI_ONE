# DermCareAI Security Threat Model

## Trust boundaries

1. Mobile application
2. Firebase Authentication
3. DermCareAI API
4. Clinical data stores
5. Object/media storage
6. Payment providers
7. Messaging providers
8. Operational/deployment infrastructure

## High-risk threats and controls

| Threat | Primary control |
| --- | --- |
| Unauthenticated AI abuse | Firebase ID-token verification + role checks + rate limits |
| Client-extracted Cloudinary secret | Server-side signing only |
| Cross-doctor patient access | Firestore rules + API authorization + tenant model |
| Payment tampering | Server-derived invoice totals + exact webhook signature verification + idempotency |
| Pharmacy race condition | Durable transactional stock ledger |
| Audit manipulation | Server-generated audit events + append-only storage |
| PHI leakage to notifications | Payload allow-list and template controls |
| Model substitution | Model registry + checksum + controlled promotion |
| Model overconfidence | Calibration + abstention + clinician review |
| Dependency compromise | Dependabot + CodeQL + dependency auditing + SBOM |
| Inference denial-of-service | Request-size limits + bounded concurrency/rate limiting |
| Production configuration drift | Environment validation + immutable deployment artifacts |

## Clinical safety principle

AI output is an assistive signal. The application must never present model confidence as diagnostic certainty and must preserve clinician interpretation as the final clinical decision.
