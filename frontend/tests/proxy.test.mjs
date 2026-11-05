import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { onRequest } from '../functions/api/[[path]].js';
import { BACKEND_ORIGIN, forwardApi } from '../src/server/pagesProxy.js';

test('Pages API routes cannot fall through to the static SPA', () => {
  const routes = JSON.parse(readFileSync(new URL('../public/_routes.json', import.meta.url)));
  assert.deepEqual(routes, { version: 1, include: ['/api', '/api/*'], exclude: [] });
  assert.equal(typeof onRequest, 'function');
});

test('proxy strips only /api and preserves method, query, body and bearer token for fixed origin', async () => {
  const request = new Request('https://frontend.test/api/auth/login?next=%2Fapi%2Fevents%2F', {
    method: 'POST', body: JSON.stringify({ email: 'fixture@example.com', password: 'synthetic-only' }),
    headers: { 'Content-Type': 'application/json', Authorization: 'Bearer synthetic',
      Cookie: 'do-not-forward', Host: 'attacker.test', Origin: 'https://attacker.test',
      'X-Forwarded-Host': 'attacker.test', 'X-Request-ID': 'untrusted', 'CF-Access-Jwt-Assertion': 'private' },
  });
  const response = await forwardApi(request, async (url, options) => {
    assert.equal(url, `${BACKEND_ORIGIN}/auth/login?next=%2Fapi%2Fevents%2F`);
    assert.equal(options.method, 'POST');
    assert.equal(options.redirect, 'manual');
    assert.equal(new TextDecoder().decode(options.body), JSON.stringify({ email: 'fixture@example.com', password: 'synthetic-only' }));
    assert.equal(options.headers.get('authorization'), 'Bearer synthetic');
    for (const name of ['cookie', 'host', 'origin', 'x-forwarded-host', 'cf-access-jwt-assertion']) assert.equal(options.headers.get(name), null);
    assert.notEqual(options.headers.get('x-request-id'), 'untrusted');
    return Response.json({ code: 'HTTP_401', message: 'Invalid email or password', request_id: 'backend-id' }, {
      status: 401, headers: { 'WWW-Authenticate': 'Bearer', 'Set-Cookie': 'never-reflect', 'X-Request-ID': 'backend-id' },
    });
  });
  assert.equal(response.status, 401);
  assert.equal((await response.json()).message, 'Invalid email or password');
  assert.equal(response.headers.get('www-authenticate'), 'Bearer');
  assert.equal(response.headers.get('x-request-id'), 'backend-id');
  assert.equal(response.headers.get('set-cookie'), null);
  assert.equal(response.headers.get('cache-control'), 'no-store');
});

test('all API methods, nested /api segments and double slash paths stay on the fixed backend', async () => {
  for (const method of ['GET', 'HEAD', 'OPTIONS', 'PUT', 'PATCH', 'DELETE']) {
    const response = await forwardApi(new Request('https://frontend.test/api//evil.test/api/events/?q=a%26b', { method }), async (url, options) => {
      assert.equal(new URL(url).origin, BACKEND_ORIGIN);
      assert.equal(new URL(url).pathname, '//evil.test/api/events/');
      assert.equal(options.method, method);
      return Response.json({ data: [] });
    });
    assert.equal(response.status, 200);
  }
  let called = false;
  assert.equal((await forwardApi(new Request('https://frontend.test/apiculture'), () => { called = true; })).status, 404);
  assert.equal(called, false);
});

test('only same-origin backend redirects are rewritten; credentials never follow redirects', async () => {
  for (const location of ['/events/', `${BACKEND_ORIGIN}/events/?q=hello`]) {
    const result = await forwardApi(new Request('https://frontend.test/api/events'), async () => new Response(null, { status: 307, headers: { Location: location } }));
    assert.equal(result.status, 307);
    assert.equal(result.headers.get('location'), `/api${new URL(location, BACKEND_ORIGIN).pathname}${new URL(location, BACKEND_ORIGIN).search}`);
  }
  for (const location of ['https://attacker.test/', '//attacker.test/', 'https://user:password@hackathonrdarfinder.onrender.com/']) {
    let calls = 0;
    const result = await forwardApi(new Request('https://frontend.test/api/auth/me', { headers: { Authorization: 'Bearer synthetic' } }), async () => {
      calls++; return new Response(null, { status: 307, headers: { Location: location } });
    });
    assert.equal(result.status, 502);
    assert.equal(calls, 1);
    assert.equal(result.headers.get('location'), null);
  }
});

test('cold-start HTML, malformed JSON, network errors and timeout produce sanitized JSON without retrying writes', async () => {
  const cases = [() => new Response('<html>provider detail</html>'),
    () => new Response('<html>waking</html>', { status: 503 }),
    () => new Response('{broken', { headers: { 'Content-Type': 'application/json' } }),
    () => { throw new Error('private connection detail'); },
    (_, options) => new Promise((resolve, reject) => options.signal.addEventListener('abort', () => reject(new Error('timeout')), { once: true })),
  ];
  for (const [index, fetcher] of cases.entries()) {
    let calls = 0;
    const result = await forwardApi(new Request('https://frontend.test/api/auth/login', { method: 'POST', body: '{}' }), (...args) => { calls++; return fetcher(...args); }, 5);
    assert.equal(result.status, index === 1 ? 503 : index === 4 ? 504 : 502);
    assert.equal(calls, 1);
    assert.match(result.headers.get('content-type'), /application\/json/);
    assert.doesNotMatch(JSON.stringify(await result.json()), /provider detail|private connection detail|<html>/);
  }
});

test('oversized uploads stop before forwarding and empty responses retain their status', async () => {
  let called = false;
  const oversized = await forwardApi(new Request('https://frontend.test/api/admin/import', { method: 'POST', body: 'x'.repeat(4 * 1024 * 1024 + 1) }), () => { called = true; });
  assert.equal(oversized.status, 413);
  assert.equal(called, false);
  const empty = await forwardApi(new Request('https://frontend.test/api/test', { method: 'DELETE' }), async () => new Response(null, { status: 204 }));
  assert.equal(empty.status, 204);
  assert.equal(await empty.text(), '');
});
