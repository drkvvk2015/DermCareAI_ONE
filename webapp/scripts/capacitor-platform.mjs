/* global process, console */
import { existsSync } from 'node:fs';
import { spawnSync } from 'node:child_process';

const platform = process.argv[2];
const shouldOpen = process.argv.includes('open');
if (!['android', 'ios'].includes(platform)) {
  console.error('Usage: node scripts/capacitor-platform.mjs <android|ios> [open]');
  process.exit(2);
}
const npx = process.platform === 'win32' ? 'npx.cmd' : 'npx';
const run = (args) => {
  const result = spawnSync(npx, ['cap', ...args], { stdio: 'inherit', shell: false });
  if (result.status !== 0) process.exit(result.status ?? 1);
};
if (!existsSync(platform)) run(['add', platform]);
run(['sync', platform]);
if (shouldOpen) run(['open', platform]);
