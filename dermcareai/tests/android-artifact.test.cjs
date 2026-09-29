const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');
const { validateAndroidApk } = require('../scripts/validate-android-apk.cjs');

const badging = [
  "package: name='com.yourcompany.dermcareai' versionCode='1' versionName='1.0.0'",
  "launchable-activity: name='com.yourcompany.dermcareai.MainActivity'",
].join('\n');

function setup() {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'dermcareai-apk-'));
  const apkPath = path.join(directory, 'app-debug.apk');
  fs.writeFileSync(apkPath, 'test apk');
  const commands = [];
  const runCommand = (command, args) => {
    commands.push({ command, args });
    if (command === 'aapt') return badging;
    if (command === 'apksigner') return 'Verifies';
    throw new Error(`Unexpected command: ${command}`);
  };
  return {
    directory,
    apkPath,
    commands,
    run: (overrides = {}) =>
      validateAndroidApk({
        apkPath,
        aaptPath: 'aapt',
        apksignerPath: 'apksigner',
        runCommand,
        ...overrides,
      }),
  };
}

test('validates APK package, version, launcher, and signature', () => {
  const context = setup();
  try {
    assert.deepEqual(context.run(), {
      packageId: 'com.yourcompany.dermcareai',
      versionName: '1.0.0',
      versionCode: 1,
    });
    assert.equal(context.commands.length, 2);
    assert.deepEqual(context.commands[1].args, [
      'verify',
      '--verbose',
      context.apkPath,
    ]);
  } finally {
    fs.rmSync(context.directory, { recursive: true, force: true });
  }
});

test('rejects a missing APK', () => {
  const context = setup();
  try {
    assert.throws(
      () => context.run({ apkPath: path.join(context.directory, 'missing.apk') }),
      /does not exist/,
    );
  } finally {
    fs.rmSync(context.directory, { recursive: true, force: true });
  }
});

test('rejects mismatched application ID and version metadata', () => {
  const context = setup();
  try {
    assert.throws(
      () =>
        context.run({
          runCommand: (command) =>
            command === 'aapt'
              ? badging.replace('com.yourcompany.dermcareai', 'com.other.app')
              : 'Verifies',
        }),
      /package ID/,
    );
    assert.throws(
      () =>
        context.run({
          runCommand: (command) =>
            command === 'aapt'
              ? badging.replace("versionCode='1'", "versionCode='2'")
              : 'Verifies',
        }),
      /version/,
    );
    assert.throws(
      () =>
        context.run({
          runCommand: (command) =>
            command === 'aapt'
              ? badging.replace("versionName='1.0.0'", "versionName='2.0.0'")
              : 'Verifies',
        }),
      /version/,
    );
  } finally {
    fs.rmSync(context.directory, { recursive: true, force: true });
  }
});

test('rejects APKs without a launcher or valid signature', () => {
  const context = setup();
  try {
    assert.throws(
      () =>
        context.run({
          runCommand: (command) =>
            command === 'aapt' ? badging.replace(/^launchable-activity:.*\n?/m, '') : 'Verifies',
        }),
      /launchable activity/,
    );
    assert.throws(
      () =>
        context.run({
          runCommand: (command) => {
            if (command === 'aapt') return badging;
            throw new Error('signature verification failed');
          },
        }),
      /signature verification failed/,
    );
  } finally {
    fs.rmSync(context.directory, { recursive: true, force: true });
  }
});
