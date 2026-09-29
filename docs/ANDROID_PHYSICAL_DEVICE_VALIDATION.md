# Android physical-device validation

## What CI proves (and does not prove)

The pull-request gate generates the Android project from Expo and builds
`app-debug.apk`. It checks that the APK exists, its package ID and version
metadata match `dermcareai/app.json`, it declares a launcher activity, and
`apksigner` verifies its debug signature. CI publishes the APK as the
`dermcareai-android-debug-apk` workflow artifact for 14 days.

This is a reproducible build and package sanity check, not a release-signed
production APK, a successful installation on hardware, or evidence of clinical
workflow behavior. A physical-device check is complete only when someone
performs and records the steps below. Do not report CI build evidence as a
device test result.

## Requirements

- A physical Android device with USB debugging or Wireless debugging enabled.
- Termux with `android-tools` installed, or a computer with Android platform
  tools (the same `adb` commands apply).
- The APK downloaded from the `dermcareai-android-debug-apk` artifact of the
  intended successful pull-request workflow run. Extract the downloaded
  artifact ZIP; install the contained `app-debug.apk`.
- A non-production/test account. Do not enter patient-identifiable data during
  validation.

## Termux setup and connection

In Termux, install ADB and grant file access:

```sh
pkg update
pkg install android-tools unzip
termux-setup-storage
```

Download the artifact ZIP to the device's Downloads folder and extract it:

```sh
mkdir -p ~/dermcareai-apk
unzip -o ~/storage/downloads/dermcareai-android-debug-apk.zip -d ~/dermcareai-apk
APK="$HOME/dermcareai-apk/app-debug.apk"
test -s "$APK" && ls -l "$APK"
```

On Android 11 or later, enable **Developer options → Wireless debugging**.
Choose **Pair device with pairing code** and use the displayed pairing address,
pairing port, and code:

```sh
adb pair <device-ip>:<pairing-port>
```

Enter the pairing code when prompted, then connect to the separate address and
port shown on the Wireless debugging screen:

```sh
adb connect <device-ip>:<adb-port>
adb devices -l
```

Expected: pairing succeeds, and `adb devices -l` lists the device as
`device` (not `unauthorized` or `offline`). If Termux cannot connect to the
device's wireless-debugging endpoint, use a computer with platform-tools and
connect the device via USB or wireless debugging instead; do not treat an
unconnected ADB session as a test.

## Install, launch, and inspect

Run the following from the same shell with `APK` set to the extracted APK path:

```sh
adb install -r "$APK"
adb shell dumpsys package com.yourcompany.dermcareai \
  | grep -E 'versionName=|versionCode='
adb shell monkey -p com.yourcompany.dermcareai \
  -c android.intent.category.LAUNCHER 1
```

Expected outcomes:

1. `adb install -r` prints `Success`.
2. `dumpsys` reports `versionName=1.0.0` and version code `1`.
3. `monkey` reports that it is launching the app, and DermCareAI opens without
   immediately closing or showing a fatal error.

To capture startup failures, clear the device log and launch once more:

```sh
adb logcat -c
adb shell monkey -p com.yourcompany.dermcareai \
  -c android.intent.category.LAUNCHER 1
adb logcat -d -t 500 | grep -E 'AndroidRuntime|FATAL EXCEPTION|com.yourcompany.dermcareai'
```

Expected: no `FATAL EXCEPTION` associated with the app. Review any startup
errors rather than assuming an empty filtered result proves all functionality.
Record whether the login screen appears and whether basic navigation is
responsive. Do not attempt real clinical decisions or use patient data in this
smoke test.

## Record the result

Record the workflow run/artifact link, APK SHA-256, date, Android version,
device model, ADB install/launch outcome, and any failure details. For example:

```sh
sha256sum "$APK"
adb shell getprop ro.build.version.release
adb shell getprop ro.product.model
```

A report should identify this as a physical-device smoke check and name the
tested artifact. If no device test was performed, state that explicitly; CI
evidence alone does not satisfy physical-device validation.
