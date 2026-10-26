import assert from 'node:assert/strict';
import { existsSync, mkdirSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { chromium } from 'playwright-core';
import AxeBuilder from '@axe-core/playwright';
import { disposableUrl } from './disposable-url.mjs';
const base=disposableUrl(process.env.FRONTEND_DISPOSABLE_BROWSER_BASE);
assert.equal((await fetch(`${base}/api/__disposable_fixture`).then(r=>r.json())).database,'temporary-sqlite-frontend-tests');
let token;
async function api(path,method='GET',body){const response=await fetch(`${base}/api${path}`,{method,headers:{'Content-Type':'application/json',...(token?{Authorization:`Bearer ${token}`}:{})},...(body?{body:JSON.stringify(body)}:{})});assert.ok(response.ok,`${path}: ${response.status} ${await response.clone().text()}`);return response.json();}
token=(await api('/auth/login','POST',{email:'admin@example.com',password:'DisposablePassword123!'})).access_token;
const now=new Date();const policy={key:'release-browser-fixture',name:'Synthetic browser fixture',adapter:'events-json-v1',url:'https://example.org/fixture',enabled:true,owner:'Disposable acceptance',basis:'Synthetic fixture owned by test',reference:'synthetic-fixture-only',reviewed_at:now.toISOString(),expires_at:new Date(+now+86400000).toISOString(),terms_permit:true};
await api('/admin/discovery/sources','PUT',policy);
const browser=await chromium.launch({executablePath:process.env.BROWSER_EXECUTABLE_PATH||['C:/Program Files/Google/Chrome/Application/chrome.exe','C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'].find(existsSync),headless:true});
const checks=[];const errors=[];
try{const page=await browser.newPage({viewport:{width:1440,height:1000}});page.on('pageerror',e=>errors.push(e.message));
await page.goto(`${base}/login`);await page.getByLabel(/^Email Address/).fill('admin@example.com');await page.getByLabel(/^Password/).fill('DisposablePassword123!');await page.getByRole('button',{name:'Sign In to Radar',exact:true}).click();await page.waitForURL(url=>!url.pathname.includes('login'));
await page.getByRole('navigation',{name:'Main navigation'}).getByRole('link',{name:'Admin',exact:true}).click();await page.getByRole('heading',{name:'Operations workspace'}).waitFor();
await page.getByRole('button',{name:'Sources',exact:true}).click();await page.getByLabel('Registered source',{exact:true}).selectOption(policy.key);await page.getByLabel('Approval record reference').fill(policy.reference);
const csv='title,url,organization,start_date,location,mode\nSynthetic release browser,https://example.org/release-browser,Synthetic organizer,2027-01-15T10:00:00+00:00,Delhi,Online\n';
await page.getByLabel('Dataset file').setInputFiles({name:'synthetic.csv',mimeType:'text/csv',buffer:Buffer.from(csv)});await page.getByRole('button',{name:'Upload to review queue',exact:true}).click();await page.getByText('1 announcements staged for review; 0 duplicates. No events published.',{exact:true}).waitFor();checks.push('CSV upload through React stages candidate with permission reference');
await page.getByRole('button',{name:'Review',exact:true}).click();await page.getByRole('button',{name:'Review and publish',exact:true}).click();await page.getByLabel('Review rationale (at least 10 characters)').fill('Explicit synthetic browser acceptance review');await page.getByRole('button',{name:'Approve and publish',exact:true}).click();await page.getByText('Change saved.',{exact:true}).waitFor();checks.push('Authorized review publishes the synthetic candidate');
await page.getByRole('button',{name:'Audit',exact:true}).click();await page.getByRole('heading',{name:'announcement_reviewed',exact:true}).waitFor();checks.push('Publication audit is visible in administration');
await page.getByRole('navigation',{name:'Main navigation'}).getByRole('link',{name:'Explore',exact:true}).click();await page.getByLabel('Search',{exact:true}).fill('Synthetic release browser');await page.getByRole('button',{name:'Apply filters',exact:true}).click();await page.getByRole('heading',{name:'Synthetic release browser',exact:true}).waitFor();checks.push('Published candidate appears through frontend API proxy');
await page.getByRole('navigation',{name:'Main navigation'}).getByRole('link',{name:'Preferences',exact:true}).click();await page.getByLabel('Interests (comma separated)').fill('synthetic');await page.getByRole('button',{name:'Save discovery preferences',exact:true}).click();await page.getByRole('region',{name:'Personalization'}).getByRole('link',{name:'Synthetic release browser',exact:true}).waitFor();checks.push('Private preferences produce explainable recommendations');
for(const width of [390,1440]){await page.setViewportSize({width,height:1000});assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);assert.deepEqual((await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa']).analyze()).violations,[]);}
checks.push('Personalized account has no accessibility violations or mobile overflow');assert.deepEqual(errors,[]);
const out=resolve('../.test-support/release-final/browser');mkdirSync(out,{recursive:true});await page.screenshot({path:resolve(out,'personalized-account.png'),fullPage:true});writeFileSync(resolve(out,'acceptance.json'),JSON.stringify({checks,errors,synthetic_fixture_only:true},null,2));console.log(JSON.stringify({checks:checks.length,errors:errors.length,synthetic_fixture_only:true}));
}finally{await browser.close();await api('/auth/logout','POST');}
