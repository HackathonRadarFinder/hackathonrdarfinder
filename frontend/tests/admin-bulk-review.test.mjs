import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { BULK_REVIEW_LIMIT, checkCandidateReview, encodeCsvToBase64, prepareBrabbleArchiveCsv } from '../src/adminBulkReview.js';

const snapshot = JSON.parse(readFileSync(new URL('../public/mined-hackathons-20261025.json', import.meta.url), 'utf8'));
const admin = readFileSync(new URL('../src/AdminWorkspace.jsx', import.meta.url), 'utf8');
const panel = readFileSync(new URL('../src/BulkReviewPanel.jsx', import.meta.url), 'utf8');
const candidate = { id: 'candidate-one', institution_id: null, payload: { title: 'Sample event', url: 'https://example.org/event' } };
const good = { ...candidate.payload, organization: 'Verified organizer', start_date: '2026-12-15T09:00:00+05:30' };

test('full 206-listing archive can be staged as an attributed CSV, not approved automatically', () => {
  const csv = prepareBrabbleArchiveCsv(snapshot);
  const rows = csv.trimEnd().split('\r\n');
  assert.equal(rows.length, 207);
  assert.match(rows[0], /registration_deadline/);
  assert.match(csv, /Data provided by Brabble\.ai API/);
  assert.match(csv, /Original platform: Devfolio/);
  assert.match(csv, /Original platform: Unstop/);
  assert.doesNotMatch(rows[0], /review_status|approved|verified_fields/);
  const decoded = Buffer.from(encodeCsvToBase64(csv), 'base64').toString('utf8');
  assert.equal(decoded, csv);
});

test('archive staging rejects missing, duplicate or untrusted snapshot data', () => {
  assert.throws(() => prepareBrabbleArchiveCsv({ records: [] }), /Unexpected/);
  const duplicate = structuredClone(snapshot);
  duplicate.records[1].id = duplicate.records[0].id;
  assert.throws(() => prepareBrabbleArchiveCsv(duplicate), /invalid or duplicated/);
  const untrusted = structuredClone(snapshot);
  untrusted.records[0].url = 'javascript:alert(1)';
  assert.throws(() => prepareBrabbleArchiveCsv(untrusted), /invalid or duplicated/);
});

test('approval requires original URL, independently confirmed organizer and event start timezone', () => {
  assert.deepEqual(checkCandidateReview(candidate, good, true), []);
  assert.match(checkCandidateReview(candidate, good, false).join(' '), /Confirm evidence/);
  assert.match(checkCandidateReview(candidate, { ...good, start_date: null }, true).join(' '), /event start date/);
  assert.match(checkCandidateReview(candidate, { ...good, start_date: '2026-12-15T09:00:00' }, true).join(' '), /timezone/);
  assert.match(checkCandidateReview(candidate, { ...good, organization: 'See listing' }, true).join(' '), /organizer/);
  assert.match(checkCandidateReview(candidate, { ...good, url: 'https://other.org/' }, true).join(' '), /original source URL/);
  assert.match(checkCandidateReview(candidate, { ...good, end_date: '2026-12-14T09:00:00+05:30' }, true).join(' '), /End date/);
});

test('admin bulk controls only call audited review endpoint for selected pending records', () => {
  assert.equal(BULK_REVIEW_LIMIT, 25);
  assert.match(admin, /Select for bulk approval/);
  assert.match(admin, /stageBrabbleArchive/);
  assert.match(admin, /Stage 206 listings into review queue/);
  assert.match(admin, /BulkReviewPanel/);
  assert.match(admin, /status === 'pending'/);
  assert.match(panel, /checkCandidateReview/);
  assert.match(panel, /decision: 'approved'/);
  assert.match(panel, /admin\/discovery\/announcements\//);
  assert.match(panel, /Remaining entries were not submitted/);
  assert.doesNotMatch(panel, /Promise\.all/);
});
