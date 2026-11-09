import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const snapshot = JSON.parse(readFileSync(new URL('../public/mined-hackathons-20261025.json', import.meta.url), 'utf8'));
const portal = readFileSync(new URL('../src/LivePlatform.jsx', import.meta.url), 'utf8');
const archive = readFileSync(new URL('../src/MinedHackathons.jsx', import.meta.url), 'utf8');

test('public archive retains exactly 206 separately credited API snapshot entries', () => {
  assert.equal(snapshot.schema_version, 1);
  assert.equal(snapshot.review_state, 'unverified');
  assert.equal(snapshot.record_count, 206);
  assert.equal(snapshot.records.length, 206);
  assert.equal(snapshot.records.filter(x => x.source === 'Unstop').length, 195);
  assert.equal(snapshot.records.filter(x => x.source === 'Devfolio').length, 11);
  assert.equal(new Set(snapshot.records.map(x => x.id)).size, 206);
  assert.equal(new Set(snapshot.records.map(x => x.url.replace(/\/$/, '').toLowerCase())).size, 206);
  assert.match(snapshot.attribution, /Brabble\.ai/);
  assert.match(snapshot.notes, /Historical API capture only/);
});

test('archive entries link to allowed sources and do not claim independent verification', () => {
  for (const row of snapshot.records) {
    assert.match(row.id, /^(unstop|devfolio)-[a-z0-9-]+$/);
    assert.ok(row.title?.trim());
    assert.match(row.url, /^https:\/\/(?:www\.)?unstop\.com\/(?:hackathons|competitions)\/|^https:\/\/[a-z0-9-]+\.devfolio\.co\/?$/);
    assert.match(row.provider_url, /^https:\/\/brabble\.ai\/s\/[a-z0-9-]+$/);
    assert.equal(Object.hasOwn(row, 'review_status'), false);
    assert.equal(Object.hasOwn(row, 'registered'), false);
  }
  assert.match(archive, /Unverified API listing/);
  assert.match(archive, /not independently verified/);
  assert.match(archive, /Data provided by/);
  assert.doesNotMatch(archive, /api\.save\(/);
});

test('all provider listings appear on Explore and no separate Mined Data page remains', () => {
  assert.match(portal, /<MinedHackathons exploreQuery=\{filters\.q\} exploreLocation=\{filters\.location\} exploreMode=\{filters\.mode\} \/>/);
  assert.match(portal, /<Route path="\/mined-hackathons" element=\{<Navigate replace to="\/explore" \/>\}/);
  assert.doesNotMatch(portal, /<NavLink to="\/mined-hackathons">/);
  assert.match(portal, /<NavLink to="\/explore">Explore<\/NavLink>/);
  assert.match(portal, /<Route path="\/explore" element=\{<Explore saved=\{saved\} toggle=\{toggle\} \/>\}/);
  assert.match(portal, /href="#additional-hackathons"/);
  assert.match(archive, /id="additional-hackathons"/);
  assert.match(archive, /Additional hackathon listings/);
  assert.match(archive, /exploreQuery/);
  assert.match(archive, /exploreLocation/);
  assert.match(archive, /exploreMode/);
});
