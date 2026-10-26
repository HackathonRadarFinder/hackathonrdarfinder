import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, readFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve, dirname, basename } from 'node:path';
import { spawnSync } from 'node:child_process';
import { createElement as h } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { MemoryRouter } from 'react-router-dom';
import { createServer } from 'vite';
import ProviderCredit from '../src/components/ProviderCredit.js';
import { createApiClient } from '../src/services/apiClient.js';

test('approved synthetic Brabble records flow through SQLite, /events/, API client and actual React cards', async () => {
  const directory = mkdtempSync(join(tmpdir(), 'radar-brabble-ui-'));
  let vite;
  try {
    const output = join(directory, 'response.json');
    const python = process.env.RADAR_TEST_PYTHON || resolve('../backend/.venv/Scripts/python.exe');
    const processResult = spawnSync(python, [resolve('../scripts/brabble_ui_fixture.py'), output],
      { encoding: 'utf-8', timeout: 60000 });
    assert.equal(processResult.status, 0, processResult.stderr || processResult.error?.message);
    const response = JSON.parse(readFileSync(output, 'utf-8'));
    const api = createApiClient('/api', async () => ({ ok: true, status: 200, json: async () => response }));
    const page = await api.events();
    assert.equal(page.total, 2);
    vite = await createServer({ server: { middlewareMode: true }, appType: 'custom' });
    const { EventCard } = await vite.ssrLoadModule('/src/LivePlatform.jsx');
    for (const event of page.data) {
      const html = renderToStaticMarkup(h(MemoryRouter, null, h(EventCard,
        { event, saved: false, toggle() {}, organization: 'Disposable Test Organizers' })));
      assert.match(html, new RegExp(event.title));
      assert.match(html, /Brabble\.ai/);
      assert.match(html, /via its API/);
      assert.match(html, /Original platform:/);
      assert.ok(html.includes(event.acquisition.provider_url));
      assert.match(html, /₹18K/);
      assert.match(html, /Starts<\/dt><dd>Not provided/);
    }
    const source = readFileSync(resolve('src/LivePlatform.jsx'), 'utf-8');
    assert.equal((source.match(/<ProviderCredit acquisition=\{event.acquisition\}/g) || []).length, 2);
  } finally {
    await vite?.close();
    assert.equal(dirname(resolve(directory)), resolve(tmpdir()));
    assert.ok(basename(directory).startsWith('radar-brabble-ui-'));
    rmSync(directory, { recursive: true, force: true });
  }
});

test('provider credit rejects executable links and React escapes API text', () => {
  const html = renderToStaticMarkup(h(ProviderCredit, { acquisition: {
    provider: 'Brabble.ai', method: 'brabble_api', provider_url: 'javascript:alert(1)',
    original_platform: '<script>alert(1)</script>',
  } }));
  assert.match(html, /href="https:\/\/brabble.ai"/);
  assert.doesNotMatch(html, /javascript:|<script>/);
  assert.equal(renderToStaticMarkup(h(ProviderCredit, { acquisition: null })), '');
});

test('genuinely reviewed pilot passes disposable import, API pagination and actual React display', async () => {
  const directory = mkdtempSync(join(tmpdir(), 'radar-brabble-ui-'));
  let vite;
  try {
    const python = process.env.RADAR_TEST_PYTHON || resolve('../backend/.venv/Scripts/python.exe');
    const result = spawnSync(python, ['-m', 'workers.accept_brabble_pilot', '--out', directory], {
      cwd: resolve('../backend'), encoding: 'utf-8', timeout: 60000,
      env: { ...process.env, DEBUG: 'false', DATABASE_URL: 'sqlite+pysqlite://',
        SECRET_KEY: 'disposable-real-pilot-ui-test-secret-123456' },
    });
    assert.equal(result.status, 0, result.stderr || result.error?.message);
    const report = JSON.parse(readFileSync(join(directory, 'acceptance_report.json'), 'utf-8'));
    assert.equal(report.database, 'disposable temporary SQLite');
    assert.equal(report.configured_database_connected, false);
    assert.deepEqual(report.imported, { inserted: 1, duplicate_urls: 0 });
    const response = JSON.parse(readFileSync(join(directory, 'events_response.json'), 'utf-8'));
    const client = createApiClient('/api', async () => ({ ok: true, status: 200, json: async () => response }));
    const page = await client.events();
    assert.equal(page.total, 1);
    assert.equal(page.data[0].registration_deadline, null);
    assert.equal(page.data[0].prize, null);
    vite = await createServer({ server: { middlewareMode: true }, appType: 'custom' });
    const { EventCard } = await vite.ssrLoadModule('/src/LivePlatform.jsx');
    const html = renderToStaticMarkup(h(MemoryRouter, null, h(EventCard, {
      event: page.data[0], saved: false, toggle() {}, organization: 'Causmic Club',
    })));
    assert.match(html, /Hacknauts 2.0/);
    assert.match(html, /Causmic Club/);
    assert.match(html, /time not published/);
    assert.match(html, /Registration deadline<\/dt><dd>Not provided/);
    assert.match(html, /Brabble\.ai/);
    assert.ok(html.includes(page.data[0].acquisition.provider_url));
  } finally {
    await vite?.close();
    assert.equal(dirname(resolve(directory)), resolve(tmpdir()));
    assert.ok(basename(directory).startsWith('radar-brabble-ui-'));
    rmSync(directory, { recursive: true, force: true });
  }
});
