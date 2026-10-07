# PWA + Capacitor migration status

## Completed in the migration branch

- `webapp/` is the canonical clinical application and PWA core.
- PWA manifest/service-worker generation is enabled through `vite-plugin-pwa`.
- Capacitor 8 core, Android, iOS, and CLI dependencies are declared.
- `webapp/capacitor.config.ts` uses `dist` as the single web asset directory.
- The legacy root `dermcareai/` Expo/React-Native application tree has been removed.
- Pull-request CI no longer uses Expo web export, Expo Doctor, Expo prebuild, or React Native TypeScript gates.
- CI now installs the PWA dependencies from the branch and can commit the authoritative generated `webapp/package-lock.json` back to the PR branch.
- CI generates and synchronizes a Capacitor Android project on Linux.
- CI generates and synchronizes a Capacitor iOS project on macOS.
- CI checks the web application package graph for active Expo/React-Native dependencies.
- Clinical AI remains suggestion-only with treating-physician decision authority.

## Explicit production-safety boundary

- PWA offline shell caching is enabled.
- Clinical writes must not be queued or replayed optimistically until the repository has an explicit conflict-safe clinical synchronization protocol with idempotency keys, version/ETag handling, audit events, and deterministic conflict resolution.
- This prevents an offline client from silently overwriting a newer clinical record or creating duplicate clinical actions.

## Acceptance gates

1. PWA lint/tests/build pass.
2. Capacitor Android generation/sync pass.
3. Capacitor iOS generation/sync pass on macOS/Xcode-capable CI.
4. No active Expo/React-Native runtime dependencies or deployment gates remain.
5. Clinical AI remains suggestion-only; the treating physician is the final decision-maker.
6. Clinical offline writes remain fail-safe until replay/conflict semantics are implemented and tested.
7. Dependency/security checks must pass before protected-main merge.
8. Main receives the migration only through the protected PR/review path.
