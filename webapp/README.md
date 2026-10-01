# DermCare Clinical Dashboard

Independent React, TypeScript, and Vite dashboard for authenticated, read-only patient record views.

## Setup

1. Copy `.env.example` to `.env` and provide the Firebase Web app settings and API base URL for your environment.
2. Run `npm ci`.
3. Run `npm run dev`.

Firebase Authentication must be configured for email/password sign-in. The API must accept Firebase ID tokens and allow the dashboard origin through its CORS configuration. The client obtains ID tokens from Firebase at request time and does not store tokens itself.

## Scripts

- `npm run lint`
- `npm test -- --run`
- `npm run build`

The dashboard only reads existing clinical summary, prescription, and procedure endpoints. It does not provide patient directory, write, diagnosis, treatment, prescribing, or procedure mutation features.
