#!/usr/bin/env bash
set -euo pipefail

APK_PATH="${1:-dermcareai/android/app/build/outputs/apk/debug/app-debug.apk}"
PACKAGE="${PACKAGE:-com.yourcompany.dermcareai}"

if ! command -v adb >/dev/null 2>&1; then
  echo "ERROR: adb is not installed or not on PATH." >&2
  exit 2
fi

if [[ ! -f "$APK_PATH" ]]; then
  echo "ERROR: APK not found: $APK_PATH" >&2
  echo "Build it first with the native Android workflow or ./gradlew assembleDebug." >&2
  exit 2
fi

if [[ -z "${ANDROID_SERIAL:-}" ]]; then
  devices="$(adb devices | awk 'NR>1 && $2=="device" {print $1}')"
  count="$(printf '%s\n' "$devices" | sed '/^$/d' | wc -l | tr -d ' ')"
  if [[ "$count" != "1" ]]; then
    echo "ERROR: expected exactly one connected Android device; found $count." >&2
    adb devices
    exit 3
  fi
else
  devices="$ANDROID_SERIAL"
fi

echo "Using Android device: $devices"
adb -s "$devices" wait-for-device >/dev/null
adb -s "$devices" install -r "$APK_PATH"

echo "Launching $PACKAGE"
adb -s "$devices" shell monkey -p "$PACKAGE" 1 >/dev/null

echo "Installed and launched successfully."
echo "Record device model:"
adb -s "$devices" shell getprop ro.product.model
echo "Record Android release:"
adb -s "$devices" shell getprop ro.build.version.release
echo "Record package version:"
adb -s "$devices" shell dumpsys package "$PACKAGE" | grep -m1 'versionName=' || true

echo "Next: perform the documented manual smoke flow and attach the evidence to issue #194."
