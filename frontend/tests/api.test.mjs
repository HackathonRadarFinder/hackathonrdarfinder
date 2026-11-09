import test from 'node:test';
import assert from 'node:assert/strict';
import { createApiClient, safeEventUrl, validateApiBase } from '../src/services/apiClient.js';

const jwt = (role = 'administrator', exp = Math.floor(Date.now() / 1000) + 3600) => `header.${Buffer.from(JSON.stringify({ role, exp })).toString('base64url')}.signature`;
const ok = data => ({ ok: true, status: 200, json: async () => data });
const bad = (status, message = 'Denied') => ({ ok: false, status, json: async () => ({ code: 'HTTP_ERROR', message, request_id: 'test-reference' }) });

test('only credential-free relative or HTTP(S) API bases are accepted', () => {
  assert.equal(validateApiBase('/api/'), '/api');
  assert.equal(validateApiBase('https://example.com/api/'), 'https://example.com/api');
  for (const base of ['//evil.test', '/\\evil.test', 'javascript:alert(1)', 'https://user:secret@example.com', 'https://example.com/?token=secret']) assert.throws(() => validateApiBase(base));
});

test('organizer links reject executable URLs, credentials and controls', () => {
  assert.equal(safeEventUrl('https://example.com/event?a=1&b=2'), 'https://example.com/event?a=1&b=2');
  for (const url of ['javascript:alert(1)', '//evil.test', 'https://user:secret@example.com', 'https://example.com\n', null]) assert.equal(safeEventUrl(url), null);
});

test('event pages always opt into bounded pagination and encode literal filters', async () => {
  let requested;
  const client = createApiClient('/api', async (url, options) => {
    requested = { url, options };
    return ok({ message: 'Events fetched successfully', data: [], total: 0, page: 2, page_size: 12 });
  });
  const result = await client.events({ page: 2, location: ' Delhi %_ ', mode: 'Online', organizationId: 3, startFrom: '2026-10-14', startTo: '2026-11-30' });
  const url = new URL(requested.url, 'http://localhost');
  assert.equal(url.pathname, '/api/events/');
  assert.deepEqual(Object.fromEntries(url.searchParams), { page: '2', page_size: '12', location: 'Delhi %_', mode: 'Online', organization_id: '3', start_from: '2026-10-14', start_to: '2026-11-30' });
  assert.equal(requested.options.headers.Authorization, undefined);
  assert.deepEqual(result.data, []);
});

test('event detail unwraps data, rejects invalid IDs and never invents fixtures', async () => {
  const client = createApiClient('/api', async url => { assert.equal(url, '/api/events/12'); return ok({ message: 'Event fetched successfully', data: { id: 12, title: 'Actual event' } }); });
  assert.equal((await client.event(12)).title, 'Actual event');
  for (const id of ['../../admin/users', 0, -1, 2147483648, 'abc']) await assert.rejects(client.event(id));
});

test('current error envelope and request reference survive HTTP failures', async () => {
  const client = createApiClient('/api', async () => bad(404, 'Event not found'));
  await assert.rejects(client.event(1), error => error.status === 404 && error.message === 'Event not found' && error.requestId === 'test-reference');
});

test('network and malformed response errors have no success fallback', async () => {
  await assert.rejects(createApiClient('/api', async () => { throw new Error('private'); }).events(), /Cannot reach/);
  await assert.rejects(createApiClient('/api', async () => ok({ items: [] })).events(), /Invalid event page/);
  await assert.rejects(createApiClient('/api', async () => ({ json: async () => { throw new Error(); } })).events(), /unreadable/);
});

test('login uses actual /me profile rather than the claimed token role', async () => {
  const calls = [];
  const token = jwt('administrator');
  const client = createApiClient('/api', async (url, options) => {
    calls.push({ url, options });
    if (url.endsWith('/login')) return ok({ access_token: token, token_type: 'bearer', role: 'administrator' });
    assert.equal(options.headers.Authorization, `Bearer ${token}`);
    return ok({ id: 'uuid', name: 'User', role: 'user' });
  });
  const result = await client.login(' user@example.com ', 'password');
  assert.equal(result.user.role, 'user');
  assert.deepEqual(JSON.parse(calls[0].options.body), { email: 'user@example.com', password: 'password' });
  client.clearSession();
});

test('backend 403 denies administration even with an administrator token claim', async () => {
  let snapshot;
  const client = createApiClient('/api', async url => url.endsWith('/login') ? ok({ access_token: jwt(), token_type: 'bearer' }) : url.endsWith('/me') ? ok({ role: 'user' }) : bad(403));
  client.subscribe(user => { snapshot = user; });
  await client.login('a@example.com', 'password');
  await assert.rejects(client.admin(), error => error.status === 403);
  assert.equal(snapshot.role, 'user'); // denied privilege does not impersonate an administrator
  client.clearSession();
});

test('expired or revoked sessions clear user and authorization headers', async () => {
  let snapshot;
  let headers;
  const client = createApiClient('/api', async (url, options) => {
    if (url.endsWith('/login')) return ok({ access_token: jwt(), token_type: 'bearer' });
    if (url.endsWith('/me')) return ok({ role: 'user' });
    headers = options.headers;
    return bad(401, 'Session has been revoked');
  });
  client.subscribe(user => { snapshot = user; });
  await client.login('a@example.com', 'password');
  await assert.rejects(client.request('/admin/stats'), /revoked/);
  assert.equal(snapshot, null);
  await assert.rejects(client.request('/admin/stats'));
  assert.equal(headers.Authorization, undefined);
});

test('already expired token never creates a session', async () => {
  const client = createApiClient('/api', async url => url.endsWith('/login') ? ok({ access_token: jwt('user', 1), token_type: 'bearer' }) : ok({ role: 'user' }));
  let snapshot;
  client.subscribe(user => { snapshot = user; });
  await assert.rejects(client.login('a@example.com', 'password'), /expired/);
  assert.equal(snapshot, null);
});

test('logout persists backend revocation and clears local session even on failure', async () => {
  const calls = [];
  const client = createApiClient('/api', async (url, options) => {
    calls.push({ url, options });
    if (url.endsWith('/login')) return ok({ access_token: jwt(), token_type: 'bearer' });
    if (url.endsWith('/me')) return ok({ role: 'user' });
    return bad(503, 'Database unavailable');
  });
  let snapshot;
  client.subscribe(user => { snapshot = user; });
  await client.login('a@example.com', 'password');
  await assert.rejects(client.logout(), /Database unavailable/);
  assert.equal(calls.at(-1).url, '/api/auth/logout');
  assert.equal(calls.at(-1).options.method, 'POST');
  assert.equal(snapshot, null);
});

test('late login completion cannot undo logout', async () => {
  let finish;
  const client = createApiClient('/api', () => new Promise(resolve => { finish = resolve; }));
  const pending = client.login('a@example.com', 'password');
  await client.logout();
  finish(ok({ access_token: jwt(), token_type: 'bearer' }));
  await assert.rejects(pending, /cancelled/);
});

test('registration whitelists regular-account fields and authenticates through backend', async () => {
  const calls = [];
  const client = createApiClient('/api', async (url, options) => {
    calls.push({ url, options });
    if (url.endsWith('/register')) return ok({ id: 'uuid' });
    if (url.endsWith('/login')) return ok({ access_token: jwt('user'), token_type: 'bearer' });
    return ok({ role: 'user' });
  });
  await client.register({ name: ' User ', email: ' a@example.com ', password: 'password', role: 'administrator' });
  assert.deepEqual(JSON.parse(calls[0].options.body), { name: 'User', email: 'a@example.com', password: 'password' });
  client.clearSession();
});

test('unconfigured OTP reset reports backend failure and never claims email delivery', async () => {
  let called = 0;
  const client = createApiClient('/api', async (url, options) => {
    called++;
    assert.equal(url, '/api/auth/password-reset/request');
    assert.deepEqual(JSON.parse(options.body), { email: 'a@example.com' });
    assert.equal(options.headers.Authorization, undefined);
    return bad(503, 'Email password reset is not configured.');
  });
  await assert.rejects(client.forgotPassword('a@example.com'), /not configured/);
  assert.equal(called, 1);
});

test('request cancellation stays abortable', async () => {
  const error = new DOMException('Aborted', 'AbortError');
  const client = createApiClient('/api', async () => { throw error; });
  await assert.rejects(client.events(), caught => caught === error);
});


test('profile edits notify the active session and whitelist name', async () => {
  const calls=[];let lastUser;
  const original={id:'owned-account',name:'Before',email:'user@example.com',role:'user'};
  const client=createApiClient('/api',async (url,options)=>{
    calls.push([url,options]);
    if(url.endsWith('/auth/login')) return ok({access_token:jwt('user'),token_type:'bearer'});
    if(url.endsWith('/auth/me')) return ok(original);
    return ok({...original,name:'After'});
  });
  client.subscribe(user=>{lastUser=user;});
  await client.login('user@example.com','password');
  await client.updateProfile('  After  ');
  assert.equal(lastUser.name,'After');
  const call=calls.find(([url])=>url.endsWith('/account/profile'));
  assert.equal(call[1].method,'PUT');
  assert.deepEqual(JSON.parse(call[1].body),{name:'After'});
  client.clearSession();
});

test('late profile response cannot restore a logged-out account',async()=>{
  let resolveUpdate,lastUser;
  const original={id:'owned-account',name:'Before',email:'user@example.com',role:'user'};
  const client=createApiClient('/api',async url=>{
    if(url.endsWith('/auth/login')) return ok({access_token:jwt('user'),token_type:'bearer'});
    if(url.endsWith('/auth/me')) return ok(original);
    return new Promise(resolve=>{resolveUpdate=resolve;});
  });
  client.subscribe(user=>{lastUser=user;});
  await client.login('user@example.com','password');
  const update=client.updateProfile('After');
  client.clearSession();
  resolveUpdate(ok({...original,name:'After'}));
  await assert.rejects(update,/session ended/);
  assert.equal(lastUser,null);
});

test('college filter choices use the published facets endpoint and state-scoped districts', async () => {
  const paths = [];
  const client = createApiClient('/api', async (url, options) => {
    paths.push(url);
    assert.equal(options.headers.Authorization, undefined);
    return ok({ states: ['Uttar Pradesh'], districts: ['Ghaziabad'] });
  });
  const choices = await client.institutionFilters('Uttar Pradesh');
  assert.deepEqual(choices, { states: ['Uttar Pradesh'], districts: ['Ghaziabad'] });
  const url = new URL(paths[0], 'http://localhost');
  assert.equal(url.pathname, '/api/institutions/facets');
  assert.equal(url.searchParams.get('state'), 'Uttar Pradesh');
});

test('college search combines state, district, name and pagination without changing source visibility', async () => {
  let requestUrl;
  const client = createApiClient('/api', async (url, options) => {
    requestUrl = url;
    assert.equal(options.headers.Authorization, undefined);
    return ok({ data: [], page: 2, page_size: 25, total: 0 });
  });
  await client.institutions('Uttar Pradesh', 'Engineering', undefined, 2, 25, 'Ghaziabad');
  const url = new URL(requestUrl, 'http://localhost');
  assert.equal(url.pathname, '/api/institutions');
  assert.deepEqual(Object.fromEntries(url.searchParams), {
    page: '2', page_size: '25', state: 'Uttar Pradesh',
    district: 'Ghaziabad', q: 'Engineering',
  });
});

test('email OTP reset uses credential-free endpoints without leaking codes in URLs', async () => {
  const captured = [];
  const api = createApiClient('/api', async (url, options) => {
    captured.push({ url, options });
    return ok({ message: 'Request processed' });
  });
  await api.forgotPassword(' test@example.com ');
  await api.confirmPasswordReset(' test@example.com ', ' 123456 ', 'NewStrongPassword123!');
  assert.equal(captured[0].url, '/api/auth/password-reset/request');
  assert.equal(captured[1].url, '/api/auth/password-reset/confirm');
  for (const item of captured) {
    assert.equal(item.options.method, 'POST');
    assert.equal(item.options.headers.Authorization, undefined);
    assert.ok(!item.url.includes('123456') && !item.url.includes('NewStrongPassword'));
  }
  assert.deepEqual(JSON.parse(captured[0].options.body), { email: 'test@example.com' });
  assert.deepEqual(JSON.parse(captured[1].options.body), {
    email: 'test@example.com', code: '123456', new_password: 'NewStrongPassword123!',
  });
});
