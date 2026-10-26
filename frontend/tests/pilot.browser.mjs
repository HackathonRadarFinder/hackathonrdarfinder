/** Full HTTP/browser acceptance, restricted to an owned temporary SQLite fixture. */
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { createServer } from 'node:net';
import { existsSync, mkdirSync, writeFileSync } from 'node:fs';
import { resolve, join } from 'node:path';
import { once } from 'node:events';
import { chromium } from 'playwright-core';

async function port() {
  const server = createServer();
  server.listen(0, '127.0.0.1');
  await once(server, 'listening');
  const number = server.address().port;
  await new Promise(done => server.close(done));
  return number;
}
async function ready(url, child) {
  for (let attempt = 0; attempt < 120; attempt++) {
    assert.equal(child.exitCode, null, 'Owned fixture exited before readiness');
    try { const response = await fetch(url); if (response.ok) return; } catch { /* starting */ }
    await new Promise(done => setTimeout(done, 250));
  }
  throw new Error('Owned fixture readiness timeout');
}
async function waitExit(child) {
  if (child.exitCode !== null || child.signalCode !== null) return;
  const exited = once(child, 'exit');
  const timer = setTimeout(() => child.kill(), 5000);
  try { await exited; } finally { clearTimeout(timer); }
}

const apiPort = await port();
const uiPort = await port();
const apiBase = `http://127.0.0.1:${apiPort}`;
const uiBase = `http://127.0.0.1:${uiPort}`;
const artifact = resolve('../.test-support/brabble-pilot-browser');
mkdirSync(artifact, { recursive: true });
const report = { database: 'temporary-reviewed-brabble-pilot', checks: [], browser_errors: [] };
const python = process.env.RADAR_TEST_PYTHON || resolve('../backend/.venv/Scripts/python.exe');
const api = spawn(python, ['-u', resolve('../scripts/brabble_pilot_demo.py'), '--port', String(apiPort)], {
  cwd: resolve('..'), stdio: ['ignore', 'ignore', 'pipe'],
});
let apiErrors = '';
api.stderr.on('data', chunk => { apiErrors += chunk; });
let vite;
let browser;
try {
  await ready(`${apiBase}/__pilot_acceptance`, api);
  const marker = await fetch(`${apiBase}/__pilot_acceptance`).then(r => r.json());
  assert.equal(marker.database, report.database);
  assert.equal(marker.configured_database_connected, false);
  assert.equal(marker.records, 1);
  vite = spawn(process.execPath, [resolve('node_modules/vite/bin/vite.js'), '--host', '127.0.0.1',
    '--port', String(uiPort), '--strictPort'], {
    cwd: process.cwd(), env: { ...process.env, API_PROXY_TARGET: apiBase }, stdio: 'ignore',
  });
  await ready(`${uiBase}/api/__pilot_acceptance`, vite);
  const executablePath = process.env.BROWSER_EXECUTABLE_PATH || [
    'C:/Program Files/Google/Chrome/Application/chrome.exe',
    'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
  ].find(existsSync);
  assert.ok(executablePath, 'Set BROWSER_EXECUTABLE_PATH to an installed Chromium browser');
  browser = await chromium.launch({ executablePath, headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  // No external assets/trackers/platform requests during this local acceptance.
  await page.route('**/*', route => new URL(route.request().url()).origin === uiBase
    ? route.continue() : route.abort());
  page.on('pageerror', error => report.browser_errors.push(error.message));
  await page.goto(`${uiBase}/explore`);
  await page.getByRole('heading', { name: 'Hacknauts 2.0', exact: true }).waitFor();
  const card = page.locator('.platform-grid article');
  assert.equal(await card.count(), 1);
  await card.locator('.platform-org').filter({ hasText: 'Causmic Club' }).waitFor();
  assert.equal(await card.getByRole('link', { name: 'Brabble.ai', exact: true }).getAttribute('href'),
    'https://brabble.ai/s/devfolio-c4045a4afcb94f6f89cfb8c48dfdf892');
  assert.match(await card.innerText(), /time not published/);
  report.checks.push('Real reviewed CSV → temporary SQLite → HTTP FastAPI → Vite proxy → React catalog');
  await page.screenshot({ path: join(artifact, 'catalog.png'), fullPage: true });
  const second = await fetch(`${uiBase}/api/events/?page=2&page_size=1`).then(r => r.json());
  assert.equal(second.total, 1);
  assert.deepEqual(second.data, []);
  report.checks.push('Real HTTP pagination returns empty second page with total=1');
  await page.getByRole('link', { name: 'Hacknauts 2.0', exact: true }).click();
  await page.getByRole('heading', { name: 'Hacknauts 2.0', exact: true }).waitFor();
  assert.equal(await page.getByRole('link', { name: /Visit organizer website/ }).getAttribute('href'),
    'https://hacknauts26.devfolio.co/');
  await page.getByRole('link', { name: 'Brabble.ai', exact: true }).waitFor();
  assert.match(await page.locator('.platform-detail').innerText(), /Registration deadline\s+Not provided/);
  report.checks.push('Event detail shows original URL, unknown deadline and linked Brabble attribution');
  await page.screenshot({ path: join(artifact, 'detail.png'), fullPage: true });
  assert.deepEqual(report.browser_errors, []);
  report.passed = true;
} catch (error) {
  report.passed = false;
  report.failure = error.message;
  throw new Error(`${error.message}\n${apiErrors}`);
} finally {
  await browser?.close();
  if (vite) { vite.kill(); await waitExit(vite); }
  try { await fetch(`${apiBase}/__pilot_shutdown`, { method: 'POST' }); } catch { /* failed startup */ }
  await waitExit(api);
  report.fixture_stopped = true;
  report.fixture_exit_code = api.exitCode;
  report.temporary_database_cleanup_confirmed = api.exitCode === 0;
  writeFileSync(join(artifact, 'report.json'), JSON.stringify(report, null, 2));
}
assert.equal(report.fixture_exit_code, 0, 'Temporary API fixture must exit cleanly and remove its SQLite directory');
console.log(JSON.stringify(report, null, 2));
