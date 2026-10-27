/** Read-only browser checks; explicitly block every mutating request. */
import assert from 'node:assert/strict';
import {existsSync,mkdirSync,writeFileSync} from 'node:fs';
import {resolve} from 'node:path';
import {chromium} from 'playwright-core';
import AxeBuilder from '@axe-core/playwright';
const base=process.env.RADAR_DIRECTORY_UI||'http://127.0.0.1:5173';
const target=new URL(base);assert.equal(target.hostname,'127.0.0.1');assert.equal(target.protocol,'http:');
async function directory(params=''){const response=await fetch(`${base}/api/institutions?${params}`);assert.ok(response.ok);return response.json();}
const initial=await directory('page_size=25');assert.ok(initial.total>=25);
if(process.env.RADAR_EXPECT_INSTITUTIONS)assert.equal(initial.total,Number(process.env.RADAR_EXPECT_INSTITUTIONS));
const browser=await chromium.launch({executablePath:process.env.BROWSER_EXECUTABLE_PATH||['C:/Program Files/Google/Chrome/Application/chrome.exe','C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'].find(existsSync)||chromium.executablePath(),headless:true});
const checks=[],errors=[];
try{const context=await browser.newContext({viewport:{width:1440,height:1000}});const page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));
await page.route('**/*',route=>{const req=route.request();return new URL(req.url()).origin===target.origin&&['GET','HEAD','OPTIONS'].includes(req.method())?route.continue():route.abort();});
await page.goto(`${base}/universities`);await page.getByRole('status').filter({hasText:`${initial.total} institutions | page 1`}).waitFor();
assert.equal(await page.locator('.platform-grid article').count(),25);
const first=await page.locator('.platform-grid article h2').allTextContents();
await page.getByRole('button',{name:'Next institutions',exact:true}).click();await page.getByText(`${initial.total} institutions | page 2`,{exact:true}).waitFor();
const second=await page.locator('.platform-grid article h2').allTextContents();assert.notDeepEqual(first,second);checks.push('Directory pagination uses distinct stored pages');
await page.getByLabel('Directory state',{exact:true}).fill('Uttar Pradesh');await page.getByRole('button',{name:'Search universities',exact:true}).click();
const filtered=await directory('state=Uttar%20Pradesh&page_size=1');assert.ok(filtered.total>0);await page.getByText(`${filtered.total} institutions | page 1`,{exact:true}).waitFor();
await page.getByLabel('University name search',{exact:true}).fill(filtered.data[0].name);await page.getByRole('button',{name:'Search universities',exact:true}).click();await page.getByRole('heading',{name:filtered.data[0].name,exact:true}).first().waitFor();checks.push('State and full university-name search use stored directory records');
await page.getByLabel('Directory state',{exact:true}).fill('No Such State');await page.getByRole('button',{name:'Search universities',exact:true}).click();await page.getByText('No institutions match these filters.',{exact:true}).waitFor();
await page.getByRole('button',{name:'Reset directory',exact:true}).click();await page.getByText(`${initial.total} institutions | page 1`,{exact:true}).waitFor();checks.push('Empty state and reset restore directory results');
for(const width of [390,1440]){await page.setViewportSize({width,height:1000});assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);assert.deepEqual((await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa']).analyze()).violations,[]);}
checks.push('Directory has no mobile overflow or accessibility violations');assert.deepEqual(errors,[]);
const output=resolve('../.test-support/final-handoff/directory-browser');mkdirSync(output,{recursive:true});await page.screenshot({path:resolve(output,'directory.png'),fullPage:true});writeFileSync(resolve(output,'report.json'),JSON.stringify({checks,errors,total:initial.total,state_count:filtered.total,all_requests_read_only:true},null,2));console.log(JSON.stringify({checks:checks.length,total:initial.total,state_count:filtered.total,errors:errors.length}));
}finally{await browser.close();}
