import assert from 'node:assert/strict';
import { existsSync, mkdirSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { chromium } from 'playwright-core';
import AxeBuilder from '@axe-core/playwright';
import { disposableUrl } from './disposable-url.mjs';

// Browser writes are restricted to the marked temporary SQLite fixture.
const base = process.env.FRONTEND_DISPOSABLE_BROWSER_BASE;
disposableUrl(base);
const marker = await fetch(`${base}/api/__disposable_fixture`).then(response => response.json());
assert.equal(marker.database, 'temporary-sqlite-frontend-tests');
const executablePath = process.env.BROWSER_EXECUTABLE_PATH || [
  'C:/Program Files/Google/Chrome/Application/chrome.exe',
  'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
].find(existsSync);
assert.ok(executablePath, 'Set BROWSER_EXECUTABLE_PATH to an installed Chromium browser.');
const artifactDir = resolve('../.test-support/browser-evidence');
mkdirSync(artifactDir, { recursive: true });
const browser = await chromium.launch({ executablePath, headless: true });
const runStartedAt = new Date().toISOString();
const evidence = [];
const errors = [];
const checks = [];
function passed(name) { checks.push(name); console.log(`PASS ${name}`); }
try {
  const context = await browser.newContext();
  const page = await context.newPage();
  page.on('pageerror', error => errors.push(error.message));
  async function accessible(label) {
    const result = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa']).analyze();
    const failures = result.violations.map(row => ({ id: row.id, impact: row.impact, targets: row.nodes.map(node => node.target) }));
    evidence.push({ label, failures });
    assert.deepEqual(failures, [], `Accessibility failures: ${label}`);
  }
  async function navigate(name) {
    const menu = page.getByRole('button', { name: 'Menu', exact: true });
    if (await menu.isVisible() && await menu.getAttribute('aria-expanded') === 'false') await menu.click();
    await page.getByRole('navigation', { name: 'Main navigation' }).getByRole('link', { name, exact: true }).click();
    if (await menu.isVisible()) await page.locator('.platform-menu[aria-expanded="false"]').waitFor();
    await page.waitForLoadState('networkidle');
  }
  async function theme(name, dark) {
    await page.getByRole('button', { name }).click();
    await page.locator(dark ? '.platform.platform-dark' : '.platform:not(.platform-dark)').waitFor();
    // Sample contrast after finite CSS transitions; do not wait for decorative loops.
    await page.locator('.platform').evaluate(element => Promise.all(element.getAnimations({ subtree: true })
      .filter(animation => animation.effect.getComputedTiming().iterations !== Infinity)
      .map(animation => animation.finished.catch(() => {}))));
  }
  for (const width of (process.argv.includes('--journey-only') ? [] : [320, 390, 768, 1440])) {
    await page.setViewportSize({ width, height: 900 });
    for (const path of ['/explore', '/login', '/register', '/predictions']) {
      await page.goto(`${base}${path}`);
      await page.getByRole('main').waitFor();
      await page.waitForLoadState('networkidle');
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth);
      assert.equal(overflow, false, `${width}px ${path} must not overflow horizontally`);
      await accessible(`${width}px ${path} light`);
      passed(`Responsive ${width}px ${path}`);
      await page.screenshot({ path: resolve(artifactDir, `${width}-${path.slice(1)}.png`), fullPage: true });
    }
  }
  await page.goto(`${base}/login`);
  await page.getByRole('button', { name: 'Sign In to Radar', exact: true }).click();
  await page.getByText('Email address is required.', { exact: true }).waitFor();
  await page.getByText('Password is required.', { exact: true }).waitFor();
  await accessible('Light theme login field errors');
  await page.getByLabel(/^Email Address/).fill('user@example.com');
  await page.getByLabel(/^Password/).fill('DisposablePassword123!');
  await accessible('Light theme focused password field');
  const toggle = page.getByRole('button', { name: 'Show password', exact: true });
  await toggle.click();
  assert.equal(await page.getByLabel(/^Password/).getAttribute('type'), 'text');
  assert.equal(await page.getByRole('button', { name: 'Hide password' }).getAttribute('aria-pressed'), 'true');
  passed('Labeled login errors and password visibility');
  await theme('Use dark theme', true);
  await accessible('Dark theme focused password field');
  await theme('Use light theme', false);
  await page.goto(`${base}/register`);
  const password = page.getByLabel(/^Password/);
  await password.fill('short');
  await page.getByLabel(/^Confirm Password/).focus();
  await page.getByText('Password must be at least 8 characters long.', { exact: true }).waitFor();
  assert.equal(await password.getAttribute('aria-invalid'), 'true');
  passed('Password blur validation announces and identifies error');
  const email = `browser-${Date.now()}@example.com`;
  await page.getByLabel(/^Full Name/).fill('Disposable Browser User');
  await page.getByLabel(/^Email Address/).fill(email);
  await password.fill('DisposablePassword123!');
  await page.getByLabel(/^Confirm Password/).fill('DisposablePassword123!');
  await page.getByRole('button', { name: 'Create Account', exact: true }).click();
  await page.waitForURL(`${base}/`);
  await page.getByRole('button', { name: 'Sign out', exact: true }).waitFor();
  passed('Browser registration and authenticated catalog');
  await page.getByRole('button', { name: 'Next', exact: true }).click();
  await page.getByRole('heading', { name: 'Disposable Event 13', exact: true }).waitFor();
  assert.equal(await page.getByRole('heading', { name: 'Disposable Event 1', exact: true }).count(), 0);
  passed('Distinct pagination pages');
  await page.getByLabel('Search', { exact: true }).fill('Disposable Event 25');
  await page.getByRole('button', { name: 'Apply filters', exact: true }).click();
  await page.getByRole('heading', { name: 'Disposable Event 25', exact: true }).waitFor();
  await page.getByRole('button', { name: 'Add saved event for Disposable Event 25', exact: true }).click();
  await page.getByRole('button', { name: 'Remove saved event for Disposable Event 25', exact: true }).waitFor();
  await page.getByRole('link', { name: 'View details →', exact: true }).click();
  await page.getByRole('heading', { name: 'Disposable Event 25', exact: true }).waitFor();
  const organizer = page.getByRole('link', { name: 'Visit organizer website' });
  assert.equal(await organizer.getAttribute('href'), 'https://example.com/event');
  assert.match(await organizer.getAttribute('rel'), /noopener/);
  passed('Keyword filtering, saving and safe organizer links');
  await navigate('Preferences');
  const consent = page.getByLabel('I consent to email reminders');
  assert.equal(await consent.isChecked(), false);
  await consent.check();
  await page.getByRole('button', { name: 'Save preferences', exact: true }).click();
  await page.getByText(/Preferences saved\./).waitFor();
  const read = page.getByRole('button', { name: 'Mark as read', exact: true });
  assert.ok(await read.count() > 0, 'Saving an event generates a persisted account notification');
  await read.first().click();
  await page.getByText('Read', { exact: true }).first().waitFor();
  passed('Explicit consent and persistent notification read state');
  await navigate('Admin');
  await page.getByRole('alert').waitFor();
  assert.equal(await page.getByRole('table').count(), 0, 'Ordinary account must never see admin data');
  passed('Ordinary account admin denial');
  let revokedToken;
  page.on('request', request => {
    if (request.url().endsWith('/auth/logout')) revokedToken = request.headers().authorization;
  });
  await page.getByRole('button', { name: 'Sign out', exact: true }).click();
  await page.locator('.platform-session').getByRole('link', { name: 'Sign in', exact: true }).waitFor();
  assert.ok(revokedToken);
  const revoked = await fetch(`${base}/api/auth/me`, { headers: { Authorization: revokedToken } });
  assert.equal(revoked.status, 401, 'Browser logout token must be revoked by backend');
  passed('Logout server revocation');
  await page.locator('.platform-session').getByRole('link', { name: 'Sign in', exact: true }).click();
  await page.getByLabel(/^Email Address/).fill(email);
  await page.getByLabel(/^Password/).fill('DisposablePassword123!');
  await page.getByRole('button', { name: 'Sign In to Radar', exact: true }).click();
  await page.waitForURL(`${base}/`);
  await navigate('Saved events');
  await page.getByRole('heading', { name: 'Disposable Event 25', exact: true }).waitFor();
  await navigate('Preferences');
  assert.equal(await consent.isChecked(), true);
  await page.getByText('Read', { exact: true }).first().waitFor();
  passed('Saved event, consent and notification persist across login sessions');
  await consent.uncheck();
  await page.getByRole('button', { name: 'Save preferences', exact: true }).click();
  await page.getByText(/Preferences saved\./).waitFor();
  await page.setViewportSize({ width: 320, height: 900 });
  await navigate('Explore');
  assert.equal(await page.getByRole('button', { name: 'Menu', exact: true }).getAttribute('aria-expanded'), 'false');
  await page.getByRole('button', { name: 'Menu', exact: true }).focus();
  await page.keyboard.press('Enter');
  await page.getByRole('navigation', { name: 'Main navigation' }).getByRole('link', { name: 'Predictions', exact: true }).focus();
  await page.keyboard.press('Enter');
  await page.getByRole('heading', { name: 'Predictions', exact: true }).waitFor();
  await page.locator('.platform-menu[aria-expanded="false"]').waitFor();
  assert.equal(await page.getByRole('button', { name: 'Menu', exact: true }).getAttribute('aria-expanded'), 'false');
  assert.equal(await page.evaluate(() => document.activeElement?.id), 'platform-content');
  await accessible('Authenticated mobile predictions and keyboard navigation');
  passed('Mobile menu keyboard activation, route closure and content focus');
  await page.getByText(/No eligible public predictions\./).waitFor();
  assert.equal(await page.locator('.platform-grid article').count(), 0);
  passed('Uncalibrated public forecasts are suppressed');
  await theme('Use dark theme', true);
  await accessible('Dark mobile predictions');
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.goto(`${base}/login`);
  assert.equal(await page.locator('.auth-radar-pulse').evaluate(element => getComputedStyle(element).animationName), 'none');
  passed('Reduced motion preference');
  assert.deepEqual(await page.evaluate(() => Object.keys(localStorage).filter(key => /token|password/i.test(key))), []);
  // Synthetic response tests presentation only; it is never persisted or claimed as a forecast.
  await page.route('**/api/predictions/catalog', route => route.fulfill({
    contentType: 'application/json', body: JSON.stringify({ message: 'Synthetic UI test only', data: [{
      organization_id: 999, organization: 'Synthetic UI Fixture Organizer',
      predicted_date: '1999-01-01', window: { start: '2027-04-01', end: '2027-04-30' },
      confidence_band: 'medium', model_version: 'ui-fixture-only', generated_at: '2026-10-13T00:00:00Z',
      historical_events: 3, reasoning: 'Synthetic recurrence signal for component verification only.',
      evidence: [{ date: '2025-04-14', title: 'Synthetic source evidence', url: 'https://example.com/evidence' }],
    }] }),
  }));
  await page.goto(`${base}/predictions`);
  await page.getByText('2027-04-01 to 2027-04-30', { exact: true }).waitFor();
  await page.getByText('Confidence: medium', { exact: true }).waitFor();
  await page.getByText(/Model: ui-fixture-only; generated:/).waitFor();
  assert.equal(await page.getByText('1999-01-01', { exact: true }).count(), 0);
  assert.ok(await page.getByText('Prediction - not officially announced', { exact: true }).count() > 0);
  await page.getByText('Historical source evidence (latest 10 records)', { exact: true }).click();
  assert.equal(await page.getByRole('link', { name: 'Synthetic source evidence' }).getAttribute('href'), 'https://example.com/evidence');
  await accessible('Synthetic date range, confidence, evidence, model and generated-time presentation');
  await page.screenshot({ path: resolve(artifactDir, 'synthetic-prediction-rendering.png'), fullPage: true });
  await page.unroute('**/api/predictions/catalog');
  passed('Synthetic prediction UI fixture: range, disclaimer, confidence, evidence and model timestamp');
  assert.deepEqual(errors, [], 'No unhandled browser exceptions');
  passed('No browser credential persistence or unhandled exceptions');
  console.log(`Browser acceptance: ${checks.length} checks passed; ${evidence.length} axe scans without violations.`);
} finally {
  writeFileSync(resolve(artifactDir, 'acceptance.json'), JSON.stringify({ run_started_at: runStartedAt,
    browser: browser.version(), database: marker.database, checks, evidence, errors }, null, 2));
  await browser.close();
}
