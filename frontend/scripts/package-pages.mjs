import { copyFile, readFile } from 'node:fs/promises';
import assert from 'node:assert/strict';

// Advanced-mode Pages artifact: the worker is deployed with the static assets,
// even if the upload starts outside the directory containing functions/.
await copyFile('../.test-support/pages-worker/index.js', 'dist/_worker.js');
const routes = JSON.parse(await readFile('dist/_routes.json', 'utf8'));
assert.ok(routes.include.includes('/api/*'));
assert.match(await readFile('dist/_worker.js', 'utf8'), /fetch/);
console.log('Packaged Pages Functions as dist/_worker.js with API routes.');
