# DermCareAI Installation Guide

This is the canonical installation guide for the current **PWA + Capacitor** architecture. It is intentionally separate from the clinical-governance and release-evidence documents.

## 1. Current platform model

```text
Browser / PWA
      │
      ├──────────────┐
      │              │
      ▼              ▼
Firebase Auth     Capacitor 8
      │           Android / iOS
      └──────┬───────┘
             ▼
        FastAPI API
             │
             ▼
        PostgreSQL
```

- `webapp/` is the canonical client.
- The PWA is the primary application surface.
- Capacitor wraps the same built web application for Android and iOS.
- Firebase Authentication is the identity boundary for clinical API access.
- FastAPI is the authenticated clinical API boundary.
- PostgreSQL is the production clinical source of truth.
- Firestore is optional and must not be introduced merely as an offline clinical cache.
- Clinical AI remains suggestion-only unless the separate evidence-gated production process is completed.

## 2. Prerequisites

### Required for browser/PWA development

- Git
- Python 3.12
- Node.js 22 LTS or the Node version required by the active CI contract
- npm
- A Firebase project with permission to configure Authentication

### Required for local staging/integration

- Docker + Docker Compose
- PostgreSQL-compatible staging container through `docker-compose.staging.yml`

### Required only for native packaging

- Android: Android Studio, Android SDK and a configured JDK/Android toolchain
- iOS: macOS + Xcode
- Firebase CLI when deploying Firestore Rules or using Firebase emulators

Do not use production Firebase credentials, production database credentials or real patient data for local development.

## 3. Clone and install

From the repository root:

```bash
git clone <repository-url>
cd DermCareAI_ONE
```

### Windows one-click setup

```powershell
powershell -ExecutionPolicy Bypass -File .\setup-dev.ps1
# or
.\setup-dev.cmd
```

The helper creates the Python 3.12 virtual environment, installs the hash-locked backend dependencies, creates `webapp/.env` from `webapp/.env.example` when needed, and installs the frontend lockfile with `npm ci`.

### Manual setup

Backend:

```bash
cd backend
python3.12 -m venv .venv
# Linux/macOS
source .venv/bin/activate
# Windows PowerShell: .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install --require-hashes -r requirements.lock
cp .env.example .env   # Windows: Copy-Item .env.example .env
```

Frontend:

```bash
cd webapp
npm ci
```

## 4. Configure the backend environment

Copy `backend/.env.example` to `backend/.env` and configure at minimum:

```text
APP_ENV=development
FIREBASE_AUTH_REQUIRED=true
FIREBASE_SERVICE_ACCOUNT_JSON=<controlled-development-service-account-json>
CORS_ORIGINS=http://localhost:5173
```

Use the actual PostgreSQL `DATABASE_URL` when running against PostgreSQL. SQLite is a development fallback and is not the production persistence boundary.

Never commit `backend/.env` or a Firebase service-account private key.

## 5. Configure Firebase Authentication — mandatory

Firebase is not an optional add-on for clinical API access.

### 5.1 Create the Firebase project

Use separate Development, Staging and Production Firebase projects where practical. Record the project ID and web-app ID.

### 5.2 Enable Authentication

In Firebase Console → Authentication → Sign-in method:

1. Enable Email/Password.
2. Configure the authorized domains for the deployed PWA.
3. Do not enable anonymous authentication for clinical access.
4. Create clinician accounts through the organization's controlled onboarding process.

### 5.3 Register the web app

Create a Firebase Web App and put these values in `webapp/.env`:

```text
VITE_FIREBASE_API_KEY=<web-api-key>
VITE_FIREBASE_AUTH_DOMAIN=<project-id>.firebaseapp.com
VITE_FIREBASE_PROJECT_ID=<project-id>
VITE_FIREBASE_APP_ID=<web-app-id>
```

These browser configuration values are not Firebase Admin private keys. **Never put the Admin service-account JSON into `webapp/.env`.**

### 5.4 Configure the backend Firebase Admin credential

The backend requires:

```text
FIREBASE_AUTH_REQUIRED=true
FIREBASE_SERVICE_ACCOUNT_JSON=<controlled-secret>
```

For production, inject the secret from the organization's approved secret-management mechanism. Do not place service-account JSON in Git, Docker images, frontend bundles or screenshots.

### 5.5 Provision the first administrator

From the backend environment, use the repository's tenant bootstrap utility:

```bash
cd backend
python tenant_bootstrap.py \
  --uid <firebase-user-uid> \
  --organization-id <organization-id> \
  --clinic-id <clinic-id> \
  --role admin \
  --role doctor
```

The resulting identity must carry the tenant and role claims required by the API:

```json
{
  "organization_id": "org-example",
  "clinic_id": "clinic-main",
  "roles": ["admin", "doctor"],
  "role": "admin"
}
```

After changing claims, refresh the user's Firebase ID token or sign out and sign in again. Verify both positive authorization and cross-tenant rejection before using clinical data.

For the complete Firebase/Firestore contract, see [Firebase Authentication and Firestore Setup](FIREBASE_SETUP.md).

## 6. Configure Firestore only when a module explicitly uses it

Firestore is **not** the current primary clinical datastore. PostgreSQL remains authoritative behind FastAPI.

If a deployment explicitly enables Firestore-backed collections:

```bash
firebase login
firebase use <project-id>
firebase deploy --only firestore:rules
```

Protected documents must contain both `organizationId` and `clinicId`, and client queries must include compatible tenant constraints. The rules are deny-by-default for unspecified collections.

Do not enable Firestore offline persistence for clinical records simply to obtain offline capability. The application's offline clinical synchronization must remain replay-safe and conflict-aware.

## 7. Start the backend

```bash
cd backend
# activate .venv first
python -m uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

Before clinical use, verify that an unauthenticated clinical API request is rejected and that an authenticated user with the wrong role or tenant is rejected.

## 8. Start the PWA

```bash
cd webapp
npm run dev -- --host 0.0.0.0
```

The Vite development server normally uses `http://localhost:5173` unless a different port is selected. Keep the Firebase Authentication authorized-domain configuration aligned with the URL actually used.

## 9. Validate the web application

```bash
cd webapp
npm run lint
npm run test -- --run
npm run build
```

The production build output is `webapp/dist/`.

## 10. Native Android/iOS packaging

The migration branch is web-first. Native projects are generated/synchronized when native packaging is enabled; do not maintain a second native clinical UI.

Android:

```bash
cd webapp
npm run cap:android
```

iOS (macOS + Xcode):

```bash
cd webapp
npm run cap:ios
```

The Capacitor configuration uses app ID `com.dermcareai.clinic` and the web build directory `dist`.

## 11. Local PostgreSQL staging

```bash
docker compose -f docker-compose.staging.yml up --build
docker compose -f docker-compose.staging.yml exec backend python scripts/migrate_postgres.py
```

Use staging/test data only. Keep production credentials and patient data out of local containers.

## 12. First-install acceptance checklist

### Environment

- [ ] Python 3.12 installed
- [ ] Node/npm installed
- [ ] Backend virtual environment created
- [ ] Hash-locked backend dependencies installed
- [ ] Frontend `npm ci` completed
- [ ] `backend/.env` created and kept out of source control
- [ ] `webapp/.env` created and kept out of source control

### Firebase

- [ ] Correct Firebase project selected
- [ ] Email/password authentication enabled
- [ ] Authorized domains configured
- [ ] Anonymous authentication disabled
- [ ] Web-app values populated in `webapp/.env`
- [ ] `FIREBASE_AUTH_REQUIRED=true`
- [ ] Backend Admin credential injected securely
- [ ] First admin/clinician provisioned
- [ ] `organization_id`, `clinic_id`, and `roles` claims verified
- [ ] ID token refreshed after claim changes
- [ ] Cross-tenant access test rejected
- [ ] Firestore Rules deployed if Firestore is used

### Application

- [ ] Backend starts successfully
- [ ] PWA starts successfully
- [ ] Login succeeds with an authorized clinician account
- [ ] Unauthenticated clinical API access is rejected
- [ ] Unauthorized role access is rejected
- [ ] Tenant isolation is enforced
- [ ] `npm run lint` passes
- [ ] `npm run test -- --run` passes
- [ ] `npm run build` passes
- [ ] PostgreSQL staging path passes where applicable

### Clinical safety

- [ ] AI output is visibly suggestion-only
- [ ] AI cannot sign a diagnosis
- [ ] AI cannot prescribe or place orders
- [ ] AI cannot silently modify signed clinical records
- [ ] Research models are not represented as clinically validated
- [ ] Production AI activation follows the evidence-gated release process

## 13. Production deployment gate

Installation is not production approval. Before production use, separately verify:

1. Environment-specific Firebase project and authorized domains.
2. Secret-management and service-account controls.
3. Managed PostgreSQL and backup/restore evidence.
4. Tenant-isolation and authentication acceptance tests.
5. Privacy, retention, deletion and incident-response controls.
6. Dependency/security/CodeQL/CI evidence.
7. Clinical AI validation, intended-use and regulatory/privacy review where applicable.
8. Staging acceptance and accountable production approval.

See [Wave 5 Release Evidence Status](WAVE5_RELEASE_EVIDENCE_STATUS.md), [Privacy Operations](PRIVACY_OPERATIONS.md), and [Clinical AI Production Activation](CLINICAL_AI_PRODUCTION_ACTIVATION.md).

## 14. Troubleshooting quick map

| Symptom | First checks |
| --- | --- |
| Firebase login fails | Firebase project ID, Auth domain, Email/Password provider, authorized domain |
| Login succeeds but API returns 401 | Firebase issuer/audience/project alignment, backend Admin credential, token expiry/revocation |
| API returns 403 | `organization_id`, `clinic_id`, `roles`, clinician activation, stale ID token |
| Firestore permission denied | Tenant fields, role/claims, active clinician record, query constraints, deployed rules |
| PWA build fails | `npm ci`, Node version, TypeScript/lint errors, lockfile integrity |
| Capacitor native build fails | Android Studio/JDK or Xcode/toolchain, then `npm run build` and `npx cap sync` |
| Clinical offline conflict | Treat as an application synchronization issue; do not enable Firestore persistence as an unreviewed workaround |

## 15. Canonical documents

- [Firebase Authentication and Firestore Setup](FIREBASE_SETUP.md)
- [Platform Migration Acceptance](PLATFORM_MIGRATION_ACCEPTANCE.md)
- [Platform Migration Architecture](PLATFORM_MIGRATION_ARCHITECTURE.md)
- [Dependency Security](DEPENDENCY_SECURITY.md)
- [Privacy Operations](PRIVACY_OPERATIONS.md)
- [Clinical AI Production Activation](CLINICAL_AI_PRODUCTION_ACTIVATION.md)
