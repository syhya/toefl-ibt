// Compatibility entry point: npm start / node server.mjs launch the Python API.
import { spawn } from 'node:child_process';
import { existsSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = dirname(fileURLToPath(import.meta.url));
const [major, minor] = process.versions.node.split('.').map(Number);
if (major < 22 || (major === 22 && minor < 12)) {
  console.error('Node.js 22.12 or newer is required.');
  process.exit(1);
}
const python = join(root, '.venv', process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python');
const portFlag = process.argv.find(arg => arg.startsWith('--port='))?.slice(7)
  ?? (process.argv.includes('--port') ? process.argv[process.argv.indexOf('--port') + 1] : undefined);
const port = Number(portFlag ?? process.env.PORT ?? 4173);
if (!Number.isInteger(port) || port < 1 || port > 65535) {
  console.error('Choose a local port from 1 to 65535.');
  process.exit(1);
}
if (!existsSync(python)) {
  console.error('The local Python environment is missing. Run ./scripts/install.sh once, then npm start.');
  process.exit(1);
}
if (!existsSync(join(root, 'dist/index.html'))) {
  console.log('Building the local React application…');
  const build = spawn(process.platform === 'win32' ? 'npm.cmd' : 'npm', ['run', 'build'], { cwd: root, stdio: 'inherit' });
  const code = await new Promise(resolve => { build.on('error', () => resolve(1)); build.on('exit', code => resolve(code ?? 1)); });
  if (code) {
    console.error('Frontend build failed. Complete ./scripts/install.sh first.');
    process.exit(code);
  }
}
// A terminal sends Ctrl+C to its whole foreground process group. Isolate the
// Python process on POSIX so it receives our single forwarded signal rather
// than both the terminal's SIGINT and a second SIGINT from this wrapper.
const separateGroup = process.platform !== 'win32';
const child = spawn(python, ['-m', 'backend', '--port', String(port)], {
  cwd: root, stdio: 'inherit', detached: separateGroup,
});
let stopping = false;
for (const signal of ['SIGINT', 'SIGTERM', ...(separateGroup ? ['SIGHUP'] : [])]) process.on(signal, () => {
  if (stopping) return;
  stopping = true;
  // Windows console Ctrl+C already reaches the non-detached child.
  if (!separateGroup && signal === 'SIGINT') return;
  child.kill(signal === 'SIGHUP' ? 'SIGTERM' : signal);
});
process.on('exit', () => {
  if (!stopping && child.pid && child.exitCode === null && child.signalCode === null) child.kill('SIGTERM');
});
child.on('error', () => { console.error('Unable to start Python. Run ./scripts/install.sh.'); process.exitCode = 1; });
child.on('exit', code => process.exit(stopping ? 0 : code ?? 1));
const url = `http://127.0.0.1:${port}`;
console.log(`TOEFL Local Lab → ${url}`);
console.log('Local FastAPI + SQLite. Keep this terminal open; Control+C stops the server.');
if (process.env.TOEFL_OPEN_BROWSER === '1' && process.platform === 'darwin') {
  let tries = 0;
  const ready = setInterval(async () => {
    if (tries++ > 60 || child.exitCode !== null) { clearInterval(ready); return; }
    try {
      const response = await fetch(`${url}/api/health`, { signal: AbortSignal.timeout(750) });
      if ((await response.json()).storage === 'sqlite') {
        clearInterval(ready);
        const opener = spawn('/usr/bin/open', [url], { stdio: 'ignore' });
        opener.on('error', () => console.log(`Open ${url} in Chrome or Edge.`));
      }
    } catch { /* Wait for Python to initialize its local catalog. */ }
  }, 500);
}
