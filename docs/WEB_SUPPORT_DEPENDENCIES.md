# Expo Web Dependency Contract

DermCareAI declares a web target in `dermcareai/app.json`. The Expo SDK 52 web export
therefore requires the matching web runtime packages:

- `react-dom@18.3.1`
- `react-native-web@~0.19.13`

These dependencies are intentionally pinned through the project package manifest and lockfile.
Native Android validation remains the primary mobile release path; the web export is a build
smoke check and is not a substitute for Android/device validation.

