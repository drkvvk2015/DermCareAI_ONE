# DermCareAI Clinical PWA

This directory is the **canonical DermCareAI client**.

## Product model

- **Primary:** React + Vite Progressive Web App (PWA)
- **Mobile:** Capacitor 8 wrapper around the same built PWA
- **Backend:** FastAPI under `../backend`
- **Authentication:** Firebase Authentication
- **Clinical AI:** suggestion-only; treating physician makes the final decision

There is intentionally no separate mobile UI implementation here. Android and iOS consume the same `dist/` web bundle through Capacitor.

## Development

```bash
npm install
npm run dev
```

For local development, Vite serves the PWA on `http://localhost:5173` and proxies `/api/*` to FastAPI on `http://localhost:8000`. Keep `VITE_API_BASE_URL` blank when using this local proxy. For a deployed browser/PWA, set `VITE_API_BASE_URL` to the approved API origin and configure `CORS_ORIGINS` for that exact deployed origin.

## Validation

```bash
npm run lint
npm run test -- --run
npm run build
```

## Capacitor Android

```bash
npm run cap:android
```

This builds the PWA, synchronizes it into the Capacitor Android project, and opens Android Studio.

## Capacitor iOS

Run on macOS with Xcode installed:

```bash
npm run cap:ios
```

## Architecture

```text
React/Vite PWA
     │
     ├── Browser / installed PWA
     │
     └── Capacitor WebView
             ├── Android
             └── iOS
     │
     ▼
FastAPI clinical platform
```

The PWA is the source of truth for clinical workflows. Capacitor native code is an infrastructure bridge only and must not become a second clinical application.
