/** New discovery UI; writes only to the marked temporary fixture after base regression. */
import assert from 'node:assert/strict';
import { existsSync, mkdirSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { chromium } from 'playwright-core';
import AxeBuilder from '@axe-core/playwright';
import { disposableUrl } from './disposable-url.mjs';

const base = disposableUrl(process.env.FRONTEND_DISPOSABLE_BROWSER_BASE);
assert.equal((await fetch(`${base}/api/__disposable_fixture`).then(r => r.json())).database, 'temporary-sqlite-frontend-tests');
let token;
async function api(path, method='GET', body) {
  const response = await fetch(`${base}/api${path}`, { method,
    headers: { 'Content-Type':'application/json', ...(token ? { Authorization:`Bearer ${token}` } : {}) },
    ...(body ? { body:JSON.stringify(body) } : {}) });
  assert.ok(response.ok, `${method} ${path}: ${response.status}`);
  return response.json();
}
token = (await api('/auth/login', 'POST', {email:'admin@example.com',password:'DisposablePassword123!'})).access_token;
const verified = new Date().toISOString();
const records = ['Tamil Nadu', 'Assam'].map((state, index) => ({ identifier:`OFFICIAL:BROWSER-TEST-${index}`,
  name:`Synthetic Browser College ${index}`, state, category:'Offline browser fixture',
  verified_at:verified }));
await api('/admin/discovery/institutions','PUT',{provider:'institution',source_url:'https://example.org/offline-test',
  reuse_permitted:true,license_reference:'Synthetic fixture only',reviewed_by:'Browser test',records});
const institutions = (await api('/institutions')).data;
const event = (await api('/events/?page=1&page_size=1')).data[0];
const institution = institutions.find(row => row.identifier === records[0].identifier);
const { id, ...eventBody } = event;
await api(`/events/${id}`, 'PUT', { ...eventBody, state:institution.state, institution_id:institution.id });
const executablePath = process.env.BROWSER_EXECUTABLE_PATH || ['C:/Program Files/Google/Chrome/Application/chrome.exe',
  'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'].find(existsSync);
const browser = await chromium.launch({ executablePath, headless:true });
const checks = [];
const errors = [];
try {
  const context = await browser.newContext({ viewport:{width:390,height:1000} });
  const page = await context.newPage();
  page.on('pageerror', error => errors.push(error.message));
  await page.goto(`${base}/explore`);
  await page.getByLabel('State or union territory').fill('Tamil Nadu');
  await page.getByLabel('Find a college').fill('Synthetic Browser College 0');
  await page.getByLabel('College or university').selectOption(String(institution.id));
  await page.getByRole('button',{name:'Apply filters',exact:true}).click();
  await page.getByText('1 events · page 1',{exact:true}).waitFor();
  await page.getByRole('heading',{name:event.title,exact:true}).waitFor();
  checks.push('State and searched college filters render the matching stored event');
  await page.goto(`${base}/universities`);
  await page.getByRole('heading',{name:institution.name,exact:true}).locator('..').getByRole('link',{name:'View college hackathons',exact:true}).click();
  await page.getByText(/^1 events . page 1$/).waitFor();
  assert.equal(new URL(page.url()).searchParams.get('institutionId'),String(institution.id));
  checks.push('University directory links open the college-specific catalog');

  await page.getByRole('button',{name:'Reset',exact:true}).click();
  await page.getByText('25 events · page 1',{exact:true}).waitFor();
  assert.equal(await page.getByLabel('State or union territory').inputValue(),'');
  assert.equal(await page.getByLabel('Find a college').inputValue(),'');
  checks.push('Reset clears state, college search and institution selection');
  await page.goto(`${base}/login`);
  await page.getByLabel(/^Email Address/).fill('admin@example.com');
  await page.getByLabel(/^Password/).fill('DisposablePassword123!');
  await page.getByRole('button',{name:'Sign In to Radar',exact:true}).click();
  await page.waitForURL(url => !url.pathname.includes('login'));
  const menu = page.getByRole('button',{name:'Menu',exact:true});
  if (await menu.isVisible() && await menu.getAttribute('aria-expanded') === 'false') await menu.click();
  await page.getByRole('navigation',{name:'Main navigation'}).getByRole('link',{name:'Admin',exact:true}).click();
  await page.getByRole('heading',{name:'Discovery coverage and failures'}).waitFor();
  await page.getByText('Institutions indexed',{exact:true}).waitFor();
  await page.waitForLoadState('networkidle');
  const section = page.getByRole('region',{name:'Discovery coverage',exact:true});
  await section.getByText('No collection runs recorded.',{exact:true}).waitFor();
  assert.equal(await section.locator('dt').filter({hasText:/^Institutions indexed$/}).locator('..').locator('dd').textContent(),'2');
  checks.push('Authorized administration shows actual directory counts and empty collection history');
  assert.deepEqual((await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa','wcag22aa']).analyze()).violations,[]);
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth),false);
  assert.deepEqual(errors,[]);
  checks.push('Mobile coverage dashboard has no axe violations, overflow or browser exceptions');
  const dir=resolve('../.test-support/india-browser-evidence');mkdirSync(dir,{recursive:true});
  await page.screenshot({path:resolve(dir,'coverage-mobile.png'),fullPage:true});
  writeFileSync(resolve(dir,'acceptance.json'),JSON.stringify({checks,errors,realInstitutions:0,fixtureInstitutions:2},null,2));
  console.log(`India discovery browser acceptance: ${checks.length} checks passed; synthetic fixture only.`);
} finally {
  await browser.close();
  await api('/auth/logout','POST');
}
