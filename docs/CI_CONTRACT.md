# DermCareAI CI Contract

The executable pull-request gates validate backend compilation and regression tests, reject committed model binaries, and run mobile TypeScript, Expo web-export, and Android debug-APK smoke checks. The Android gate checks APK metadata and signature and publishes a debug APK artifact; it does not replace physical-device validation described in [the Android device runbook](ANDROID_PHYSICAL_DEVICE_VALIDATION.md).

The recovery/integration workflow uses the backend working directory with `PYTHONPATH=.` so local backend modules resolve correctly.
