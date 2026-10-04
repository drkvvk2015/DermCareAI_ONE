# DermCareAI Platform Migration — PWA + Capacitor

## Decision

DermCareAI is now **web-first**. The `webapp/` React application is the canonical clinical client and will be delivered as:

1. **PWA** — primary application for desktop, tablet and mobile browsers.
2. **Capacitor** — native Android/iOS container around the same PWA bundle when app-store distribution or native device APIs are required.
3. **FastAPI backend** — shared clinical, commerce, pharmacy, audit and AI governance platform.

The Expo/React-Native application is no longer part of the active product architecture or pull-request CI.

## Why this architecture

- One clinical UI instead of maintaining separate React Native and web implementations.
- The browser/PWA is the source of truth for clinical workflows and accessibility.
- Capacitor provides a native bridge without duplicating the application layer.
- Native capabilities can be added selectively through Capacitor plugins while keeping clinical business logic in the web application.
- PWA offline behavior remains governed by the existing clinical synchronization and conflict rules rather than by a second native data layer.

## Runtime boundary

```text
                 DermCareAI Backend
                         │
                  HTTPS / Firebase Auth
                         │
        ┌────────────────┴────────────────┐
        │                                 │
  DermCareAI PWA                    Capacitor Runtime
  React + Vite                     Android / iOS WebView
        │                                 │
        └──────────── same web bundle ────┘
```

## PWA requirements

- installable web application
- service-worker based asset caching
- automatic update strategy
- responsive clinician UI
- browser-standard file/image capture where possible
- persistent offline queue only for deterministic replay-safe clinical mutations
- no autonomous clinical actions

## Capacitor requirements

Capacitor 8 is the selected baseline. Core, Android and CLI versions must remain aligned. Native projects must consume the built `webapp/dist` bundle; clinical logic must not fork into native implementations.

Recommended development flow:

```bash
cd webapp
npm install
npm run build
npx cap add android
npx cap sync android
npx cap open android
```

For iOS, run the equivalent commands on macOS with Xcode installed.

## Migration rules

- Do not add new Expo dependencies.
- Do not add new React Native screens or navigation.
- Do not add Expo-specific CI gates.
- Do not move clinical business logic into Capacitor native code.
- Native plugins are adapters only; authorization, audit, consent and clinical safety remain server/web concerns.
- The PWA remains the primary application even when installed as a native mobile package.

## Legacy cleanup

The existing `dermcareai/` Expo tree is being removed as part of this migration after the PWA/Capacitor parity gates are established. It must not be referenced by CI, deployment scripts, documentation, or new feature work.

## Clinical AI boundary

The platform migration does not change the Clinical AI safety contract. AI remains a **suggestion-only clinical copilot**. The treating physician remains the final decision-maker.
