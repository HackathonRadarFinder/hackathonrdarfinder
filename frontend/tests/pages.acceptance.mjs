/** Compiled Pages router/workerd -> fixed upstream intercepted locally -> FastAPI.
 * All API requests go to a self-created, marked temporary SQLite fixture.
 * Never connects to Render/Supabase, deploys, or uses production credentials.
 */
import assert from 'node:assert/strict';
import { spawn, spawnSync } from 'node:child_process';
import { createServer } from 'node:net';
import { readFile, stat } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { resolve, sep, extname } from 'node:path';
import { Miniflare, convertV4MiniflareOptions } from 'miniflare';
import { chromium } from 'playwright-core';
import { BACKEND_ORIGIN } from '../src/server/pagesProxy.js';

const root = resolve('..');
const localPython = resolve('../backend/.venv/Scripts/python.exe');
const python = process.env.RADAR_TEST_PYTHON || (process.platform === 'win32' && existsSync(localPython) ? localPython : 'python');
const probe = spawnSync(python, ['-c', 'import fastapi, sqlalchemy, alembic, bcrypt, jwt, uvicorn'], { encoding: 'utf8', timeout: 15000 });
assert.equal(probe.status, 0, 'Disposable Python dependencies unavailable. Set RADAR_TEST_PYTHON to an existing backend virtualenv interpreter.');
const port = await new Promise((resolvePort, reject) => {
  const listener = createServer();
  listener.once('error', reject);
  listener.listen(0, '127.0.0.1', () => { const value = listener.address().port; listener.close(() => resolvePort(value)); });
});
const fixture = spawn(python, [resolve('../scripts/disposable_backend.py'), '--port', String(port)], {
  cwd: root, stdio: ['ignore', 'pipe', 'pipe'], env: { ...process.env, EMAIL_MODE: 'disabled', DISCOVERY_ENABLED: 'false' },
});
let fixtureError;
fixture.on('error', error => { fixtureError = error; });
// Drain only. Never surface arbitrary backend exception text/credentials.
fixture.stdout.resume(); fixture.stderr.resume();
let runtime;
let calls = 0;
const fixtureBase = `http://127.0.0.1:${port}`;

async function runNode(script, env, args = []) {
  return new Promise((resolveRun, reject) => {
    const child = spawn(process.execPath, [script, ...args], { env: { ...process.env, ...env }, stdio: ['ignore', 'pipe', 'pipe'] });
    child.stdout.on('data', data => process.stdout.write(data));
    child.stderr.on('data', data => process.stderr.write(data));
    child.once('error', reject);
    child.once('exit', code => code === 0 ? resolveRun() : reject(new Error(`${script} failed (${code})`)));
  });
}

try {
  let ready = false;
  const started = Date.now();
  // First-time Python imports and migrations can take over 30s on Windows.
  const startupTimeout = 90_000;
  let readinessFailure = 'not yet listening';
  while (Date.now() - started < startupTimeout) {
    if (fixtureError || fixture.exitCode !== null) throw new Error(`Disposable fixture failed to start (${fixtureError?.code || fixture.exitCode}). Check RADAR_TEST_PYTHON dependencies.`);
    try {
      const marker = await fetch(`${fixtureBase}/__disposable_fixture`, { signal: AbortSignal.timeout(1000) }).then(response => response.json());
      assert.equal(marker.database, 'temporary-sqlite-frontend-tests');
      ready = true; break;
    } catch (error) { readinessFailure = error.name; await new Promise(resolveWait => setTimeout(resolveWait, 250)); }
  }
  assert.ok(ready, `Disposable fixture readiness timeout after ${startupTimeout}ms (${readinessFailure}).`);
  console.log(`Disposable Python backend ready in ${Date.now() - started}ms.`);
  const dist = resolve('dist');
  runtime = new Miniflare(convertV4MiniflareOptions({
    modules: true, script: await readFile(resolve('dist/_worker.js'), 'utf-8'),
    compatibilityDate: '2026-11-03', host: '127.0.0.1', port: 0,
    outboundService: async request => {
      const url = new URL(request.url);
      assert.equal(url.origin, BACKEND_ORIGIN, 'No outbound production or arbitrary-host requests allowed');
      calls++;
      const local = new URL(fixtureBase);
      local.pathname = url.pathname; local.search = url.search;
      const body = ['GET', 'HEAD'].includes(request.method) ? undefined : await request.arrayBuffer();
      return fetch(local, { method: request.method, headers: request.headers, body, redirect: 'manual' });
    },
    serviceBindings: { ASSETS: async request => {
      const path = new URL(request.url).pathname;
      assert.ok(!/^\/api(?:\/|$)/.test(path), 'API routing must never fall back to SPA assets');
      let file = resolve(dist, '.' + decodeURIComponent(path));
      assert.ok(file === dist || file.startsWith(dist + sep), 'Static path outside dist');
      try { if (!(await stat(file)).isFile()) file = resolve(dist, 'index.html'); }
      catch { file = resolve(dist, 'index.html'); }
      const type = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.svg': 'image/svg+xml', '.json': 'application/json' }[extname(file)] || 'application/octet-stream';
      return new Response(await readFile(file), { headers: { 'Content-Type': type } });
    } },
  }));
  const base = (await runtime.ready).origin;
  assert.equal((await fetch(`${base}/api/auth/status`).then(response => response.json())).message, 'Authentication API is ready');
  const events = await fetch(`${base}/api/events/?page_size=2`).then(response => response.json());
  assert.equal(events.total, 25); assert.equal(events.data.length, 2);
  const badLogin = await fetch(`${base}/api/auth/login`, { method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email: 'missing@example.com', password: 'synthetic-invalid-password' }) });
  assert.equal(badLogin.status, 401);
  assert.equal((await badLogin.json()).message, 'Invalid email or password');
  for (const path of ['/login', '/register', '/explore', '/event/1', '/colleges', '/admin/colleges']) {
    const page = await fetch(`${base}${path}`);
    assert.equal(page.status, 200); assert.match(await page.text(), /<div id="root"><\/div>/);
  }
  // The shared acceptance scripts verify their own disposable marker before writes.
  await runNode('tests/backend.test.mjs', { FRONTEND_DISPOSABLE_API: `${base}/api` });
  const browserPath = process.env.BROWSER_EXECUTABLE_PATH || [chromium.executablePath(),
    'C:/Program Files/Google/Chrome/Application/chrome.exe',
    'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'].find(existsSync);
  assert.ok(browserPath, 'Install Chromium with playwright-core or configure BROWSER_EXECUTABLE_PATH');
  await runNode('tests/browser.acceptance.mjs', { FRONTEND_DISPOSABLE_BROWSER_BASE: base, BROWSER_EXECUTABLE_PATH: browserPath }, process.argv.includes('--journey-only') ? ['--journey-only'] : []);
  assert.ok(calls > 0);
  console.log(`PASS compiled Pages router/workerd, JSON auth failures, SPA refresh and real local API/browser journeys (${calls} intercepted backend requests; no external backend requests).`);
} finally {
  await runtime?.dispose();
  fixture.kill('SIGTERM');
}
