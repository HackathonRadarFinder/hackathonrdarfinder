import test from 'node:test';
import assert from 'node:assert/strict';
import { createApiClient } from '../src/services/apiClient.js';
import { disposableUrl } from './disposable-url.mjs';

test('state and college filters are encoded and passed with the existing filters', async () => {
  let requested;
  const client = createApiClient('/api', async url => {
    requested = new URL(url, 'http://127.0.0.1');
    return { ok: true, json: async () => ({ data: [], total: 0, page: 1 }) };
  });
  await client.events({ state: 'Tamil Nadu', institutionId: 42, q: 'Hack & build', location: 'Chennai' });
  assert.equal(requested.searchParams.get('state'), 'Tamil Nadu');
  assert.equal(requested.searchParams.get('institution_id'), '42');
  assert.equal(requested.searchParams.get('q'), 'Hack & build');
  assert.equal(requested.searchParams.get('location'), 'Chennai');
});

test('disposable browser URLs reject remote hosts and malformed or privileged targets', () => {
  for (const url of ['https://example.org:5184', 'http://localhost:5184', 'http://127.0.0.1:80',
    'http://127.0.0.1:5184/production', 'http://user@127.0.0.1:5184', 'http://127.0.0.1:5184/?x=1']) {
    assert.throws(() => disposableUrl(url));
  }
  assert.equal(disposableUrl('http://127.0.0.1:5184'), 'http://127.0.0.1:5184');
});


test('institution directory pages use the existing public endpoint with bounded page size',async()=>{
  let requested, options;
  const client=createApiClient('/api',async(url,init)=>{requested=new URL(url,'http://127.0.0.1');options=init;return {ok:true,json:async()=>({data:[],total:0,page:2,page_size:25})};});
  await client.institutions('Uttar Pradesh','College & University',undefined,2,25);
  assert.equal(requested.pathname,'/api/institutions');
  assert.equal(requested.searchParams.get('state'),'Uttar Pradesh');
  assert.equal(requested.searchParams.get('q'),'College & University');
  assert.equal(requested.searchParams.get('page'),'2');
  assert.equal(requested.searchParams.get('page_size'),'25');
  assert.equal(options.headers.Authorization,undefined);
});
