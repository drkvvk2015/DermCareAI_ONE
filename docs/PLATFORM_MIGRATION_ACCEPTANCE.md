# PWA + Capacitor migration acceptance

The canonical client is `webapp/`. The PWA is the primary application; Capacitor is the native Android/iOS container around the same web bundle.

Acceptance gates before deleting the legacy Expo tree:

- PWA lint/tests/build pass.
- Capacitor Android generation and sync pass.
- Legacy mobile-only workflows have PWA equivalents or explicit scope decisions.
- Offline clinical synchronization remains replay-safe and conflict-aware.
- No CI/deployment path references Expo or React Native.
- New web/PWA/Capacitor dependencies have a regenerated lockfile.
- Clinical AI remains suggestion-only with physician final decision authority.
