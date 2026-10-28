import assert from 'node:assert/strict';

// Different worktrees may run together. Every write-capable suite also checks
// its backend fixture marker before it creates browser contexts or accounts.
export function disposableUrl(value, pathname = '/') {
  const url = new URL(value);
  assert.equal(url.protocol, 'http:');
  assert.equal(url.hostname, '127.0.0.1');
  assert.ok(Number(url.port) >= 1024 && Number(url.port) <= 65535);
  assert.equal(url.pathname, pathname);
  assert.equal(url.username + url.password + url.search + url.hash, '');
  return value;
}
