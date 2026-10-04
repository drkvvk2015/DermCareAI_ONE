# DermCare Clinical Dashboard

Independent React, TypeScript, and Vite installable web PWA for authenticated, read-only patient record views. The separate Expo application is outside this web release scope and remains unchanged.

## Setup

1. Copy `.env.example` to `.env` and provide the Firebase Web app settings and API base URL for your environment.
2. Run `npm ci`.
3. Run `npm run dev`.

Firebase Authentication must be configured for email/password sign-in. All four Firebase web settings are required; missing settings disable sign-in with a safe setup message. These client settings are public configuration, not secrets. Never place service-account credentials, private keys, API secrets, or other privileged credentials in `VITE_*` variables: Vite embeds them in public assets.

The API base URL must point to the approved HTTPS API and the API must accept Firebase ID tokens. The API's exact CORS allow-list, server-side role checks, and tenant authorization remain authoritative; client routes are not an authorization boundary. Configure the Firebase project's authorized web domain for the eventual production origin. The application obtains ID tokens from Firebase when making requests; it does not implement its own token storage.

## PWA and offline behavior

The production build includes a web app manifest and service worker for installation. The service worker precaches only the static application shell (HTML and built JavaScript/CSS). API calls and Firebase authentication requests are network-only; patient summaries, prescriptions, procedures, tokens, and API responses are never intentionally cached by the service worker. A cached shell may open offline, but sign-in and all clinical reads require a network connection. If a read cannot reach the service, the dashboard displays a safe retryable error and must not present stale/offline clinical data.

Serve the deployed PWA over HTTPS (localhost is suitable for local development). Do not use a shared device's offline shell as evidence that a clinical record is available.

## Scripts

- `npm run lint`
- `npm test -- --run`
- `npm run build`

The dashboard only reads existing clinical summary, prescription, and procedure endpoints. It does not provide patient directory, write, diagnosis, treatment, prescribing, or procedure mutation features.

## Production release boundary

Use `../docs/PRODUCTION_GO_LIVE_RUNBOOK.md` for the web release preflight, deployment smoke checks, and rollback guidance. The hosting provider, production hostname/origin, accountable operational/privacy approvals, and final production authorization are intentionally unresolved and must be confirmed before a deployment workflow or production settings are added.
