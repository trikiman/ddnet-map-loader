// TTY shim for gsd-tools.cjs — lets us capture its JSON output when stdout is piped.
// Usage: node .planning/.gsd-shim.js <subcommand> [args...]
const { spawnSync } = require('child_process');
const os = require('os');
const path = require('path');
const home = process.env.HOME || os.homedir();
const tool = path.join(home, '.kiro', 'get-shit-done', 'bin', 'gsd-tools.cjs');
// Force isTTY so gsd-tools writes its output
Object.defineProperty(process.stdout, 'isTTY', { value: true, configurable: true });
Object.defineProperty(process.stderr, 'isTTY', { value: true, configurable: true });
const args = process.argv.slice(2);
// Run in a child process with stdio piped so we can see the output
const result = spawnSync(process.execPath, [tool, ...args], {
  env: { ...process.env, FORCE_COLOR: '0', TERM: 'dumb' },
  stdio: ['inherit', 'pipe', 'pipe'],
});
if (result.stdout) process.stdout.write(result.stdout);
if (result.stderr) process.stderr.write(result.stderr);
process.exit(result.status || 0);
