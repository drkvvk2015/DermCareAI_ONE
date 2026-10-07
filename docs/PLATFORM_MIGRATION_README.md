# PWA-first client migration

The `webapp/` React/Vite application is the canonical DermCareAI client. PWA is the primary distribution surface. Capacitor 8 is the native mobile runtime around the same web bundle.

Expo/React Native is no longer part of active development or CI. Legacy Expo code is removed only after the PWA/Capacitor parity and lockfile gates pass.
