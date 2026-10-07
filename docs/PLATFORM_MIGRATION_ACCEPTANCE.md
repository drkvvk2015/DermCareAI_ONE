# PWA + Capacitor migration acceptance

The canonical client is `webapp/`. The PWA is the primary application; Capacitor is the native Android/iOS container around the same web bundle.

## Explicit engineering release scope

The current engineering release validates:
- patient lookup and tenant-safe patient registration;
- read-only clinical summary, prescription and procedure views;
- suggestion-only Clinical AI APIs;
- clinician-approved guideline lookup with provenance and audit events.

The following legacy Expo-only workflows are explicitly **de-scoped from this release** and must not be represented as supported production capabilities:
- encounter creation/editing;
- lesion body-map capture and native lesion workflows;
- prescription creation/editing;
- screening UI/workflow;
- appointments;
- billing UI/workflow;
- pharmacy UI/workflow.

These workflows remain a separate backlog. A future implementation must be separately validated before it is enabled or advertised as production functionality. Removing the legacy Expo tree therefore does not remove a claimed current production capability; it removes unsupported legacy implementation.

## Acceptance gates

- PWA lint/tests/build pass.
- Capacitor Android generation and sync pass.
- Capacitor iOS generation and sync pass.
- Legacy mobile-only workflows are explicitly de-scoped as above.
- Offline clinical writes are not enabled in this release; PostgreSQL remains authoritative.
- No CI/deployment path references Expo or React Native.
- Web/PWA/Capacitor dependencies are lockfile-synchronized.
- Clinical AI remains suggestion-only with physician final decision authority.
