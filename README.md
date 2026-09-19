# DermCareAI — Dermatology Clinic Operating System

DermCareAI is a healthcare-oriented dermatology clinic platform that combines patient and appointment management with AI-assisted image screening, clinical documentation, billing and hosted UPI checkout, pharmacy inventory/dispensing, audit logging, and authenticated notifications.

> **v4 platform revolution:** The platform now has a versioned `/api/v1` runtime contract, request correlation IDs, readiness/liveness endpoints, privacy-safe aggregate observability, explicit AI governance/provenance metadata, and a clinician-facing platform command centre. See [docs/REVOLUTION_V4_ARCHITECTURE.md](docs/REVOLUTION_V4_ARCHITECTURE.md).


> **Clinical safety:** DermCareAI is an assistive software platform. AI screening output is not a diagnosis and must not be used as the sole basis for treatment. The embedded HAM10000 model is a research fallback and is not clinically validated for routine patient care.

## v4 platform capabilities

- Versioned platform API contract under `/api/v1`
- Runtime readiness and liveness signals
- Request correlation via `X-Request-ID`
- Aggregate observability without patient payload persistence
- AI governance card attached to every screening decision
- Explicit model provenance, threshold, abstention and human-review metadata
- Mobile Clinical Command Center exposing backend readiness and authentication posture

## Current capabilities

### Clinical and patient workflow
- Patient profiles and clinic records
- Appointment and clinical workflow support
- Prescription and clinical-note support
- Dermatology image screening and screening reports
- Authenticated clinic APIs using Firebase ID tokens
- Role-based authorization for protected clinic operations

### AI and model management
- Repository-backed model registry
- Optional locally cached embedded dermatology model: `PREMAADC/vit-base-ham10000`
- Model hash verification and registry integrity checks
- Bounded model reload/self-healing behaviour
- Automated backend evaluation and regression tests
- No model binaries are committed to Git; controlled deployment storage is expected

### Billing and payments
- Invoice creation and payment lifecycle support
- Razorpay hosted payment links
- UPI Intent/QR through hosted checkout
- Server-side invoice amount calculation
- Razorpay signature verification using the exact request body
- Provider amount validation against the stored invoice
- Idempotent payment handling

Do not add new UPI Collect flows. Confirm current Razorpay requirements before production deployment.

### Pharmacy
- Medicine master and stock management
- Batch and expiry tracking
- Reorder thresholds
- Prescription-linked dispensing
- Duplicate medicine-ID aggregation for stock validation/deduction
- Validation before mutation to avoid partial stock updates

A persistent transactional database and production pharmacy authorization model are still required for a live dispensing deployment.

### Notifications
- WhatsApp Cloud API adapter
- Indian SMS-provider integration
- Privacy-safe operational webhook
- Explicit channel allow-listing
- Authenticated provider configuration

Never transmit diagnoses, prescriptions, payment details, lesion images, or other protected health information to public social networks.

### Auditing
- Timestamped audit events
- Hash-chained audit records
- Coverage for critical workflow events such as patients, prescriptions, dispensing, invoices, payments, notifications, AI screening, and administrative actions
- SQLite-backed local audit store for development/single-instance use

For multi-instance production deployments, move auditing to a managed append-only datastore with appropriate retention, backup, access control, and monitoring.

## Architecture

```text
Mobile / Web (Expo + React Native)
        |
        | Firebase ID token
        v
Clinic API / Backend (FastAPI)
        |
        +-- Auth / RBAC
        +-- Clinical workflow
        +-- AI model registry + evaluation
        +-- Billing / Razorpay
        +-- Pharmacy
        +-- Notifications
        +-- Audit logging
        |
        +-- Controlled model storage
        +-- SQLite / managed production datastore
```

## Repository layout

```text
.
├── backend/
│   ├── app.py
│   ├── auth.py
│   ├── commerce.py
│   ├── evaluation.py
│   ├── model_registry.py
│   ├── notifications.py
│   ├── resilience.py
│   ├── audit.py
│   ├── main.py
│   └── tests/
├── dermcareai/
│   └── src/
├── docs/
├── .github/
│   └── workflows/
└── README.md
```

## Configuration

Start from `backend/.env.example`.

Important server-side settings include:

- `FIREBASE_AUTH_REQUIRED=true`
- Firebase service-account configuration
- Razorpay credentials and webhook secret
- WhatsApp Cloud API credentials
- SMS provider / DLT template configuration
- Optional privacy-safe operational webhook
- Audit database path
- Model directory and model selection settings

Never commit API keys, access tokens, webhook secrets, Firebase credentials, or patient data.

## Local development

### Backend

```bash
cd backend
python -m pip install -U pip
python -m pip install pytest fastapi pydantic httpx firebase-admin
pytest -q tests
python -m compileall -q .
```

### Mobile

```bash
cd dermcareai
npm ci
npx tsc --noEmit
npx expo export --platform web
```

## Continuous validation

The repository runs automated validation on GitHub Actions.

### Backend gate
- Python compilation
- Full backend test suite
- Safety/evaluation regression checks
- Protection against accidentally committed model binaries

### Mobile gate
- Clean `npm ci`
- TypeScript compilation
- Expo web export smoke test

### Security scanning
CodeQL scans:
- GitHub Actions
- JavaScript / TypeScript
- Python

The project should treat a failing security or regression gate as a release blocker.

## Security model

Production clinics should keep the following controls enabled:

1. Firebase authentication for clinic APIs
2. Server-side role enforcement
3. Audit identity derived from the verified user
4. Server-side payment amount calculation
5. Payment webhook signature verification
6. Provider amount validation
7. Idempotent payment processing
8. Channel allow-listing for outbound notifications
9. No PHI in public/social notification payloads
10. Controlled storage for model binaries and secrets
11. CodeQL and regression checks before production merges

## Regulatory and clinical boundary

Healthcare software and AI functionality may fall under medical-device, privacy, cybersecurity, pharmacy, payment, and professional-practice requirements depending on intended use, claims, geography, and deployment model.

For India, conduct a formal assessment against applicable CDSCO / Medical Devices Rules requirements, privacy obligations, pharmacy requirements, payment-provider rules, and institutional policies before commercialization or clinical deployment.

The repository does not by itself establish regulatory clearance or clinical validation.

## Production readiness checklist

Before a real clinic deployment:

- Use a managed transactional database instead of development SQLite where required
- Enable encrypted backups, restore testing, and disaster recovery
- Configure Firebase production authentication and least-privilege service credentials
- Store secrets outside Git
- Configure Razorpay webhooks and verify signatures
- Configure approved WhatsApp/SMS templates and patient consent workflows
- Establish pharmacy authorization and stock audit controls
- Move audit logging to durable append-only infrastructure for multi-instance deployment
- Complete penetration testing and dependency/security review
- Complete clinical validation and intended-use documentation for any AI-enabled claim
- Configure GitHub branch protection/rulesets so production merges require reviewed pull requests and passing CI/security checks

## Important limitations

- AI screening is assistive and not a substitute for dermatologist assessment, histopathology, or other indicated investigations.
- The embedded HAM10000 model is a research fallback, not a clinically validated diagnostic model.
- Production payment, pharmacy, audit, notification, and identity infrastructure requires deployment-specific hardening.
- Regulatory status depends on the actual product claims, workflow, jurisdiction, and implementation.

## License

See the repository for the applicable project licensing and dependency notices.
