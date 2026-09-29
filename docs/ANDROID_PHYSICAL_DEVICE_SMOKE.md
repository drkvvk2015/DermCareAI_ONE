# Physical Android Smoke Procedure

## Automated preparation

Run:

```bash
bash scripts/android_device_smoke.sh
```

The script requires exactly one connected Android device unless `ANDROID_SERIAL` is set.
It installs the debug APK, launches the application, and records device/Android/package
information without collecting patient data.

## Manual smoke sequence

After launch, record pass/fail for:

1. App launch and initial navigation.
2. Authentication/session handling.
3. Patient search/open.
4. Create or open dermatology encounter.
5. Clinical examination/navigation.
6. Clinical image/media capture or selection.
7. AI review presentation and abstention/clinician-review boundary.
8. Prescription creation.
9. Pharmacy navigation and dispense state.
10. Offline/reconnect behavior where supported.
11. Audit-sensitive actions complete without UI crashes.
12. Clean logout.

Do not enter real patient-identifying information during the validation run.
Use a dedicated synthetic/staging account and synthetic patient.

## Evidence

Record:

- commit SHA;
- APK filename and checksum;
- device model;
- Android version;
- test date/time;
- each smoke step as PASS/FAIL;
- crash/logcat evidence for any failure.

A successful APK installation and launch does not establish clinical validity, regulatory approval,
or production readiness.
