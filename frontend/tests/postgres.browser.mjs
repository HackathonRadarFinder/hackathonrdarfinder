/** Read-only browser checks against this run's isolated Docker acceptance network. */
import assert from 'node:assert/strict';
import { existsSync, mkdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { chromium } from 'playwright-core';

const base = process.env.RADAR_ACCEPTANCE_UI;
const runId = process.env.RADAR_ACCEPTANCE_RUN_ID;
assert.match(runId || '', /^[a-f0-9]{12}$/);
const target = new URL(base);
assert.equal(target.hostname, '127.0.0.1');
const artifact = process.env.RADAR_ACCEPTANCE_ARTIFACT;
assert.ok(artifact);
mkdirSync(artifact, { recursive: true });
const executablePath = process.env.BROWSER_EXECUTABLE_PATH || [
  'C:/Program Files/Google/Chrome/Application/chrome.exe',
  'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
].find(existsSync);
assert.ok(executablePath);
const browser = await chromium.launch({ executablePath, headless: true });
const report = { run_id: runId, database: 'owned disposable PostgreSQL 16', checks: [], errors: [] };
try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  page.on('pageerror', error => report.errors.push(error.message));
  await page.route('**/*', route => new URL(route.request().url()).origin === target.origin
    ? route.continue() : route.abort());
  await page.goto(`${base}/explore`);
  const card = page.locator('.platform-grid article');
  await card.getByRole('heading', { name: 'Hacknauts 2.0', exact: true }).waitFor();
  await card.locator('.platform-org').filter({ hasText: 'Causmic Club' }).waitFor();
  assert.equal(await card.count(), 1);
  await card.getByRole('link', { name: 'Brabble.ai', exact: true }).waitFor();
  report.checks.push('Built Nginx/React image loads reviewed event from built FastAPI image and migrated PostgreSQL');
  await page.screenshot({ path: join(artifact, 'catalog.png'), fullPage: true });
  const response = await fetch(`${base}/api/events/?page=2&page_size=1`).then(r => r.json());
  assert.equal(response.total, 1);
  assert.deepEqual(response.data, []);
  await page.getByRole('link', { name: 'Hacknauts 2.0', exact: true }).click();
  await page.getByRole('heading', { name: 'Hacknauts 2.0', exact: true }).waitFor();
  assert.equal(await page.getByRole('link', { name: /Visit organizer website/ }).getAttribute('href'),
    'https://hacknauts26.devfolio.co/');
  await page.getByRole('link', { name: 'Brabble.ai', exact: true }).waitFor();
  assert.match(await page.locator('.platform-detail').innerText(), /Registration deadline\s+Not provided/);
  report.checks.push('Container proxy preserves pagination, event detail, unknown deadline and linked attribution');
  await page.screenshot({ path: join(artifact, 'detail.png'), fullPage: true });
  assert.deepEqual(report.errors, []);
  report.passed = true;
} finally {
  await browser.close();
  writeFileSync(join(artifact, 'report.json'), JSON.stringify(report, null, 2));
}
console.log(JSON.stringify(report, null, 2));
