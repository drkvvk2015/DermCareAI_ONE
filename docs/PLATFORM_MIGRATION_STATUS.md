# PWA + Capacitor migration status

## Completed

- `webapp/` designated as the canonical clinical client.
- PWA manifest/service-worker generation enabled through `vite-plugin-pwa`.
- Capacitor 8 core/Android/CLI dependencies declared.
- `webapp/capacitor.config.ts` added with `dist` as the web asset directory.
- Pull-request CI no longer runs Expo web export, Expo Doctor, Expo prebuild, or React Native TypeScript gates.
- CI now validates the PWA build and generates/synchronizes the Capacitor Android project.
- Web application documentation updated for PWA-first delivery.

## In progress

- Regenerate and commit the webapp lockfile with the new Capacitor/PWA dependency graph.
- Remove the legacy `dermcareai/` Expo/React-Native source tree after parity gates pass.
- Add committed Capacitor Android/iOS projects when native packaging is enabled.
- Migrate any remaining functionality that exists only in the legacy mobile client into the PWA using browser standards or Capacitor plugins.
- Update all root documentation and release/dependency workflows that still describe Expo as an active client.

## Acceptance criteria before deleting legacy mobile code

1. PWA lint/tests/build pass.
2. Capacitor Android generation/sync pass.
3. Clinical workflows used by the legacy client have equivalent PWA routes or explicit scope decisions.
4. Offline clinical synchronization behavior remains replay-safe and conflict-aware.
5. Clinical AI suggestion-only boundary is preserved.
6. No CI/deployment script references Expo or React Native.
7. Dependency audit contains no newly introduced unreviewed mobile runtime risk.
