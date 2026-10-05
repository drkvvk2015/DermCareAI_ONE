# Firebase Authentication and Firestore Setup

This document is the mandatory Firebase setup contract for a DermCareAI deployment.

## Architecture decision
DermCareAI uses Firebase Authentication for clinician identity and the FastAPI backend as the authenticated clinical API boundary. PostgreSQL is the production clinical persistence boundary.
The repository also contains Firestore security rules for deployments that explicitly use Firestore collections. The current PWA does not use Firestore as its primary clinical datastore.
Do not introduce Firestore writes for clinical records merely to obtain offline caching. A second clinical source of truth creates synchronization, conflict-resolution, audit, retention and deletion risks.

## 1. Create the Firebase project
Use separate Development, Staging and Production Firebase projects where practical. Never use production credentials for local development.
Record the Firebase project ID, project number, web app ID and Auth domain.

## 2. Enable Firebase Authentication
In Firebase Console > Authentication > Sign-in method:
1. Enable Email/Password.
2. Enable other providers only when explicitly approved by the organization.
3. Configure authorized domains for the web/PWA deployment.
4. Do not enable anonymous authentication for clinical access.
5. Create clinician accounts through the controlled organizational onboarding process.
The current PWA signs in with Firebase email/password authentication and sends the Firebase ID token to FastAPI as a Bearer token.

## 3. Register the web application
Create a Firebase Web App and populate webapp/.env with:

~~~text
VITE_FIREBASE_API_KEY=<web-api-key>
VITE_FIREBASE_AUTH_DOMAIN=<project-id>.firebaseapp.com
VITE_FIREBASE_PROJECT_ID=<project-id>
VITE_FIREBASE_APP_ID=<web-app-id>
~~~

These browser configuration values are not service-account secrets. Never put a Firebase Admin private key in the web app.
The backend requires:

~~~text
FIREBASE_AUTH_REQUIRED=true
FIREBASE_SERVICE_ACCOUNT_JSON=<controlled-secret>
~~~

Use a secret manager, workload identity/ADC, or equivalent controlled identity in production.

## 4. Create the first administrator
Create the initial administrator through the approved organizational process.
Assign tenant claims from the controlled administrative environment using backend/tenant_bootstrap.py.

Example:

~~~bash
cd backend
export FIREBASE_SERVICE_ACCOUNT_JSON='...'
python tenant_bootstrap.py --uid <firebase-user-uid> --organization-id <organization-id> --clinic-id <clinic-id> --role admin --role doctor
~~~

Required claims:

~~~json
{
  "organization_id": "org-example",
  "clinic_id": "clinic-main",
  "roles": ["admin", "doctor"],
  "role": "admin"
}
~~~

Keep organization_id and clinic_id stable. Do not derive them from email addresses or display names.
After changing custom claims, force a token refresh with user.getIdToken(true), or sign out and sign in again.

## 5. Provision clinicians
1. Create the Firebase Authentication account.
2. Obtain the Firebase UID.
3. Create or activate the matching doctors/{uid} record where Firestore is used.
4. Assign exactly one organization/clinic tenant pair.
5. Assign approved role claims.
6. Verify the backend accepts the refreshed ID token.
7. Verify a cross-organization and cross-clinic access attempt is rejected.

## 6. Backend authentication contract
The FastAPI backend validates Firebase ID tokens with the Firebase Admin SDK.
Production must keep FIREBASE_AUTH_REQUIRED=true.
The backend uses uid, email, role/roles, organization_id and clinic_id.
Firebase login alone does not grant clinical-record access; role and tenant authorization remain enforced.

## 7. Firestore rules
Deploy firestore.rules before enabling any Firestore collections:

~~~bash
firebase login
firebase use <project-id>
firebase deploy --only firestore:rules
~~~

Current rules require authentication, approved roles, an active clinician record, matching organization/clinic claims, and matching organizationId/clinicId document fields. Unspecified collections default to deny.

## 8. Firestore tenant model
Protected documents must contain both:

~~~json
{
  "organizationId": "org-example",
  "clinicId": "clinic-main"
}
~~~

Do not store only clinicId. Existing records must be backfilled before relying on tenant matching.

## 9. Firestore query alignment
Firestore rules are not filters. An unrestricted collection read can still be rejected.
When a module explicitly uses Firestore, client queries should include the same tenant constraints required by the rules, for example:

~~~ts
query(
  collection(db, "patients"),
  where("organizationId", "==", organizationId),
  where("clinicId", "==", clinicId),
)
~~~

The current PWA does not use Firestore for its primary clinical API calls. This section applies only to future or explicitly Firestore-backed modules.

## 10. Offline persistence: DermCareAI distinction
The current architecture is:

~~~text
PWA / Capacitor
      |
      v
Firebase Authentication
      |
      v
FastAPI authenticated API
      |
      v
PostgreSQL clinical persistence
~~~

Therefore, do not enable Firestore persistence for clinical records unless the architecture is deliberately changed to make Firestore authoritative and the following are redesigned and revalidated: conflict resolution, auditability, retention/deletion, tenant isolation, signed-record behavior, backups/recovery, migration and offline mutation replay.
The PWA + Capacitor migration instead requires replay-safe, conflict-aware clinical synchronization as defined by docs/PLATFORM_MIGRATION_ACCEPTANCE.md.

## 11. Emulator setup
The repository currently configures a Firestore emulator in firebase.json. Firebase Auth emulator coverage should be added as a separate development-only mode before using it in local end-to-end auth tests.
Never point a production build at emulators.

## 12. Production verification checklist
Authentication
- Correct Firebase project selected.
- Email/password enabled.
- Authorized domains configured.
- Test clinician can sign in.
- Revoked or expired ID token is rejected.
- Anonymous authentication is disabled.

Claims
- Admin claims bootstrap completed.
- organization_id present.
- clinic_id present.
- roles present.
- ID token refreshed after claim changes.
- Cross-tenant access test fails as expected.

Backend
- FIREBASE_AUTH_REQUIRED=true.
- Admin credentials are outside source control.
- Unauthenticated clinical API requests are rejected.
- Unauthorized roles are rejected.
- Production PostgreSQL is active.

Firestore, when used
- firestore.rules deployed to the intended project.
- Tenant fields exist on protected documents.
- Queries include compatible tenant constraints.
- Security Rules tests pass.
- No client relies on rules to filter an unrestricted query.

Offline/resilience
- Clinical offline scope is explicitly documented.
- Supported mutations are replay-safe and idempotent.
- Conflicts are surfaced rather than silently overwritten.
- Non-idempotent image uploads and similar operations are not blindly replayed.
- Backup/recovery evidence is retained.

## 13. Common failures
Permission denied after successful login usually means missing/stale claims, tenant mismatch, missing tenant document fields, or a query incompatible with the rules.
Backend 401 after Firebase sign-in usually means a Firebase project/issuer/audience mismatch, invalid backend credentials, or an expired/revoked token.
Backend 403 after successful authentication usually means missing roles, tenant claims, or inactive clinician status.

## 14. Security responsibility
Authentication and Firestore Rules tests prove access-control behavior. They do not establish clinical safety, regulatory approval or production readiness.
The treating organization remains responsible for identity lifecycle, least privilege, tenant administration, privacy/retention, incident response, clinical validation and regulatory assessment.

## 15. Deployment summary

~~~text
Firebase project
  |-- Authentication -> clinician accounts
  |-- Custom claims  -> organization_id / clinic_id / roles
  `-- Firestore      -> only where explicitly used and tenant-scoped

PWA / Capacitor
  -> Firebase ID token
  -> FastAPI
  -> PostgreSQL clinical source of truth
~~~

A new DermCareAI environment is not complete until Firebase project configuration, Authentication, custom claims, backend verification, tenant-isolation acceptance and environment-specific checks have been verified.