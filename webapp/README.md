# DermCare Clinical Dashboard

Independent React, TypeScript, and Vite dashboard for authenticated, read-only patient record views.

## Setup

1. Copy `.env.example` to `.env` and provide the Firebase Web app settings. Keep `VITE_API_BASE_URL` blank for local development so Vite proxies `/api/*` to FastAPI on `http://localhost:8000`; set it to an explicit API origin for split-host deployments.
2. Run `npm ci`.
3. Run `npm run dev`.

For local development, Vite serves the dashboard on `http://localhost:5173` and proxies API requests to FastAPI on `http://localhost:8000`. The backend development CORS example therefore includes port 5173. For a deployed browser/PWA, set `VITE_API_BASE_URL` to the approved API origin and explicitly allow the deployed web origin in `CORS_ORIGINS`.

Firebase Authentication must be configured for email/password sign-in. The API must accept Firebase ID tokens. The client obtains ID tokens from Firebase at request time and does not store tokens itself.

## Scripts

- `npm run lint`
- `npm test -- --run`
- `npm run build`

The dashboard only reads existing clinical summary, prescription, and procedure endpoints. It does not provide patient directory, write, diagnosis, treatment, prescribing, or procedure mutation features.
