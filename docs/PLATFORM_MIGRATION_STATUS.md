# PWA + Capacitor migration status

## Completed

- `webapp/` is the canonical clinical application and PWA core.
- PWA manifest/service-worker generation is enabled through `vite-plugin-pwa`.
- Capacitor 8 core, Android, iOS, and CLI dependencies are declared.
- `webapp/capacitor.config.ts` uses `dist` as the single web asset directory.
- Pull-request CI no longer runs Expo web export, Expo Doctor, Expo prebuild, or React Native TypeScript gates.
- CI validates the PWA build and generates/synchronizes the Capacitor Android project.
- The legacy `dermcareai/` Expo/React-Native application tree has been removed from the migration branch.
- Web-first platform documentation has been updated for PWA + Capacitor delivery.

## Remaining hardening

- Regenerate and commit `webapp/package-lock.json` after the Capacitor iOS dependency addition.
- Generate and commit native Capacitor projects when native packaging is enabled (`npx cap add android` / `npx cap add ios`).
- Verify feature parity for any legacy mobile workflow not yet represented in the PWA.
- Complete offline clinical synchronization and conflict-replay acceptance tests.
- Update any remaining release/dependency documentation that describes Expo as an active client.

## Acceptance criteria

1. PWA lint/tests/build pass.
2. Capacitor Android generation/sync pass.
3. Capacitor iOS generation/sync pass on macOS/Xcode.
4. Clinical workflows have equivalent PWA routes or explicit scope decisions.
5. Offline clinical synchronization remains replay-safe and conflict-aware.
6. Clinical AI remains suggestion-only with treating-physician decision authority.
7. No CI/deployment script references Expo or React Native.
8. Dependency audit contains no newly introduced unreviewed mobile runtime risk.
9. Main branch receives this migration only through the protected PR/review path.
