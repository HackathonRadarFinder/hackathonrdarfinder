import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const root = readFileSync(new URL('../src/Root.jsx', import.meta.url), 'utf8');
const live = readFileSync(new URL('../src/LivePlatform.jsx', import.meta.url), 'utf8');

test('production portal never loads the fictional demo bundle', () => {
  assert.match(root, /import\(['"]\.\/App\.jsx['"]\)/);
  assert.doesNotMatch(root, /DemoPlatform|\/demo/);
});

test('public portal has no demo advertising and redirects old demo bookmarks', () => {
  assert.doesNotMatch(live, /href=["']\/demo\//);
  assert.doesNotMatch(live, /Fictional design demo|Explore the design demo|>Design demo</);
  assert.match(live, /path="\/demo\/\*" element=\{<Navigate replace to="\/explore" \/>\}/);
});
