/** UI acceptance restricted to scripts/local_demo.py's disposable database. */
import assert from 'node:assert/strict';
import { randomUUID } from 'node:crypto';
import { existsSync, mkdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { tmpdir } from 'node:os';
import { chromium } from 'playwright-core';
import AxeBuilder from '@axe-core/playwright';

const base = process.env.FRONTEND_CURATED_DEMO_BASE;
assert.equal(base, 'http://127.0.0.1:5176');
const marker = await fetch(`${base}/api/__local_demo`).then(response => response.json());
assert.equal(marker.database, 'temporary-curated-local-demo');
assert.equal(marker.email, 'disabled');
assert.equal(marker.records, 5);
const executablePath = process.env.BROWSER_EXECUTABLE_PATH || [
  'C:/Program Files/Google/Chrome/Application/chrome.exe',
  'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
].find(existsSync);
assert.ok(executablePath, 'Set BROWSER_EXECUTABLE_PATH to an installed Chromium browser.');
const browser = await chromium.launch({ executablePath, headless: true });
const evidence = { database: marker.database, checks: [], errors: [] };
const artifactDir = join(tmpdir(), 'radar-curated-demo-acceptance');
mkdirSync(artifactDir, { recursive: true });
function passed(name) { evidence.checks.push(name); console.log(`PASS ${name}`); }
try {
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
  const page = await context.newPage();
  page.on('pageerror', error => evidence.errors.push(error.message));
  await page.goto(`${base}/explore`);
  await page.getByText('5 events · page 1', { exact: true }).waitFor();
  assert.equal(await page.locator('.platform-grid article').count(), 5);
  passed('Five reviewed curated records load from ingestion through API to React');
  await page.getByLabel('Starts on or after (UTC)').fill('2026-10-14');
  await page.getByLabel('Starts on or before (UTC)').fill('2026-11-30');
  await page.getByRole('button', { name: 'Apply filters', exact: true }).click();
  await page.getByText('2 events · page 1', { exact: true }).waitFor();
  await page.getByRole('heading', { name: 'HackHarvard 2026', exact: true }).waitFor();
  await page.getByRole('heading', { name: 'MIT Policy Hackathon 2026', exact: true }).waitFor();
  assert.equal(await page.locator('.platform-grid article').count(), 2);
  passed('UTC date filters return the two matching curated events');
  await page.getByRole('button', { name: 'Reset', exact: true }).click();
  await page.getByText('5 events · page 1', { exact: true }).waitFor();
  assert.equal(await page.getByLabel('Starts on or after (UTC)').inputValue(), '');
  assert.equal(await page.getByLabel('Starts on or before (UTC)').inputValue(), '');
  await page.getByLabel('Location', { exact: true }).fill('Hyderabad');
  await page.getByRole('button', { name: 'Apply filters', exact: true }).click();
  await page.getByText('3 events · page 1', { exact: true }).waitFor();
  passed('Reset restores the catalog and location filtering shows historical editions');
  await page.getByRole('button', { name: 'Reset', exact: true }).click();
  await page.getByRole('link', { name: 'HackHarvard 2026', exact: true }).click();
  const source = page.getByRole('link', { name: /Visit organizer website/ });
  await source.waitFor();
  assert.equal(await source.getAttribute('href'), 'https://hhuh.io/');
  await page.getByText(/Source observed:/).waitFor();
  await page.getByText(/Applications are closed/).waitFor();
  passed('Detail preserves source attribution, observation time and closed-application caveat');
  if (process.env.FRONTEND_DISCOVERY_EXPECTED === 'true') {
    await page.getByRole('heading', { name: 'Discovery and update history', exact: true }).waitFor();
    await page.getByText(/Collected by Reviewed MVP snapshot/).first().waitFor();
    await page.getByText(/Version 1/).waitFor();
    passed('Automated collection evidence and initial version render in event detail');
  }
  const email = `curated-${randomUUID()}@example.com`;
  const password = `Demo-${randomUUID()}`;
  await page.goto(`${base}/register`);
  await page.getByLabel(/^Full Name/).fill('Disposable Curated User');
  await page.getByLabel(/^Email Address/).fill(email);
  await page.getByLabel(/^Password/).fill(password);
  await page.getByLabel(/^Confirm Password/).fill(password);
  await page.getByRole('button', { name: 'Create Account', exact: true }).click();
  await page.waitForURL(`${base}/`);
  await page.getByRole('button', { name: 'Sign out', exact: true }).waitFor();
  passed('Registration authenticates a disposable account');
  await page.getByRole('button', { name: 'Add saved event for HackHarvard 2026', exact: true }).click();
  await page.getByRole('button', { name: 'Remove saved event for HackHarvard 2026', exact: true }).waitFor();
  async function navigate(name) {
    await page.getByRole('navigation', { name: 'Main navigation' }).getByRole('link', { name, exact: true }).click();
    await page.waitForLoadState('networkidle');
  }
  await navigate('Saved events');
  await page.getByRole('heading', { name: 'HackHarvard 2026', exact: true }).waitFor();
  await page.getByRole('button', { name: 'Remove saved event for HackHarvard 2026', exact: true }).click();
  await page.getByText('No saved events yet.', { exact: true }).waitFor();
  passed('Save and unsave update account-owned curated bookmarks');
  await navigate('Explore');
  await page.getByRole('button', { name: 'Add saved event for HackHarvard 2026', exact: true }).click();
  await page.getByRole('button', { name: 'Remove saved event for HackHarvard 2026', exact: true }).waitFor();
  await navigate('Preferences');
  const consent = page.getByLabel('I consent to email reminders');
  assert.equal(await consent.isChecked(), false);
  await consent.check();
  await page.getByRole('button', { name: 'Save preferences', exact: true }).click();
  await page.getByText(/Preferences saved\. Reminders require a saved event and an enabled email worker\./).waitFor();
  await page.getByRole('button', { name: 'Mark as read', exact: true }).first().click();
  await page.getByText('Read', { exact: true }).first().waitFor();
  passed('Explicit consent and stored notices work without claiming email delivery');
  await navigate('Admin');
  await page.getByRole('alert').first().waitFor();
  assert.equal(await page.getByRole('table').count(), 0);
  assert.equal((await fetch(`${base}/api/admin/stats`)).status, 401);
  passed('Unauthorized administration exposes no protected data');
  let revokedToken;
  page.on('request', request => {
    if (request.url().endsWith('/auth/logout')) revokedToken = request.headers().authorization;
  });
  await page.getByRole('button', { name: 'Sign out', exact: true }).click();
  await page.locator('.platform-session').getByRole('link', { name: 'Sign in', exact: true }).waitFor();
  assert.ok(revokedToken);
  assert.equal((await fetch(`${base}/api/auth/me`, { headers: { Authorization: revokedToken } })).status, 401);
  await page.goto(`${base}/login`);
  await page.getByLabel(/^Email Address/).fill(email);
  await page.getByLabel(/^Password/).fill(password);
  await page.getByRole('button', { name: 'Sign In to Radar', exact: true }).click();
  await page.waitForURL(`${base}/`);
  await navigate('Saved events');
  await page.getByRole('heading', { name: 'HackHarvard 2026', exact: true }).waitFor();
  await navigate('Preferences');
  assert.equal(await consent.isChecked(), true);
  await page.getByText('Read', { exact: true }).first().waitFor();
  await consent.uncheck();
  await page.getByRole('button', { name: 'Save preferences', exact: true }).click();
  await page.getByText(/Preferences saved\./).waitFor();
  passed('Login preserves saves and preferences; logout revokes JWT access');
  await navigate('Saved events');
  await page.getByRole('button', { name: 'Remove saved event for HackHarvard 2026', exact: true }).click();
  await page.getByText('No saved events yet.', { exact: true }).waitFor();
  await page.getByRole('button', { name: 'Sign out', exact: true }).click();
  await page.locator('.platform-session').getByRole('link', { name: 'Sign in', exact: true }).waitFor();
  await page.goto(`${base}/forgot-password`);
  await page.getByRole('heading', { name: 'Password reset unavailable', exact: true }).waitFor();
  passed('Unsupported password recovery shows an accurate unavailable state');
  await page.goto(`${base}/predictions`);
  await page.getByText(/No eligible public predictions/).waitFor();
  assert.equal(await page.locator('.platform-grid article').count(), 0);
  if (process.env.FRONTEND_PREDICTION_READINESS_EXPECTED === 'true') {
    await page.getByLabel('Prediction data readiness').waitFor();
    assert.match(await page.getByLabel('Prediction data readiness').textContent(), /5 reviewed event editions; 1 recurring series/);
    passed('Verified history readiness displays without publishing unsupported forecasts');
  }
  passed('Unsupported public predictions remain suppressed');
  await page.setViewportSize({ width: 390, height: 900 });
  await page.goto(`${base}/explore`);
  await page.getByText('5 events · page 1', { exact: true }).waitFor();
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
  const axe = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa']).analyze();
  assert.deepEqual(axe.violations.map(row => row.id), []);
  assert.deepEqual(evidence.errors, []);
  await page.screenshot({ path: join(artifactDir, 'curated-mobile.png'), fullPage: true });
  passed('Curated mobile catalog has no overflow, axe violations or browser exceptions');
  console.log(`Curated acceptance: ${evidence.checks.length} checks passed.`);
} finally {
  writeFileSync(join(artifactDir, 'acceptance.json'), JSON.stringify(evidence, null, 2));
  await browser.close();
}
