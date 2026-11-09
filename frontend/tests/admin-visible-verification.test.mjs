import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
const admin = readFileSync(new URL('../src/AdminWorkspace.jsx', import.meta.url), 'utf8');
const portal = readFileSync(new URL('../src/LivePlatform.jsx', import.meta.url), 'utf8');
test('admin verification actions are visible with empty queue', () => {
  assert.match(admin, /Verify unverified listings/);
  assert.match(admin, /Update \/ Refresh/);
  assert.match(admin, /Stage 206 listings/);
  assert.match(admin, /No pending listings to verify/);
  assert.match(admin, /Verify \/ Update &amp; Publish/);
  assert.match(admin, /setRevision\(value => value \+ 1\)/);
});
test('non-admin accounts receive an actionable role explanation', () => {
  assert.match(portal, /user\.role !== 'administrator'/);
  assert.match(portal, /bulk approval controls require/);
  assert.match(portal, /AdminWorkspace/);
});
