const { execFileSync } = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');

function validateAndroidApk({
  apkPath,
  aaptPath,
  apksignerPath,
  configPath = path.join(__dirname, '..', 'app.json'),
  runCommand = execFileSync,
}) {
  if (!apkPath || !fs.existsSync(apkPath) || !fs.statSync(apkPath).isFile()) {
    throw new Error(`APK does not exist: ${apkPath || '(not specified)'}`);
  }
  if (!aaptPath || !apksignerPath) {
    throw new Error('Both aapt and apksigner paths are required');
  }

  const expo = JSON.parse(fs.readFileSync(configPath, 'utf8')).expo;
  const packageId = expo.android.package;
  const versionName = expo.version;
  const versionCode = expo.android.versionCode;
  if (!packageId || !versionName || !Number.isInteger(versionCode)) {
    throw new Error('app.json must define Android package, version, and integer versionCode');
  }

  const badging = runCommand(aaptPath, ['dump', 'badging', apkPath], {
    encoding: 'utf8',
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  const packageInfo = badging.match(
    /^package: name='([^']+)' versionCode='([^']+)' versionName='([^']*)'/m,
  );
  if (!packageInfo) {
    throw new Error('APK package and version metadata could not be read');
  }
  if (packageInfo[1] !== packageId) {
    throw new Error(`APK package ID ${packageInfo[1]} does not match ${packageId}`);
  }
  if (packageInfo[2] !== String(versionCode) || packageInfo[3] !== versionName) {
    throw new Error(
      `APK version ${packageInfo[3]} (${packageInfo[2]}) does not match ${versionName} (${versionCode})`,
    );
  }
  if (!/^launchable-activity:/m.test(badging)) {
    throw new Error('APK has no launchable activity');
  }

  runCommand(apksignerPath, ['verify', '--verbose', apkPath], {
    encoding: 'utf8',
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  return { packageId, versionName, versionCode };
}

function readArgument(name, args) {
  const index = args.indexOf(name);
  return index === -1 ? undefined : args[index + 1];
}

if (require.main === module) {
  try {
    const result = validateAndroidApk({
      apkPath: readArgument('--apk', process.argv),
      aaptPath: readArgument('--aapt', process.argv),
      apksignerPath: readArgument('--apksigner', process.argv),
    });
    console.log(
      `Validated signed APK: ${result.packageId} ${result.versionName} (${result.versionCode})`,
    );
  } catch (error) {
    console.error(error.message);
    process.exitCode = 1;
  }
}

module.exports = { validateAndroidApk };
