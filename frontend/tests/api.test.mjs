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

test('unsupported reset never fabricates an email or calls an invented endpoint', async () => {
  const client = createApiClient('/api', () => { assert.fail('No request expected'); });
  await assert.rejects(client.forgotPassword('a@example.com'), /No email was sent/);
});

test('request cancellation stays abortable', async () => {
  const error = new DOMException('Aborted', 'AbortError');
  const client = createApiClient('/api', async () => { throw error; });
  await assert.rejects(client.events(), caught => caught === error);
});
