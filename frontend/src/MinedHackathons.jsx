import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { safeEventUrl } from './services/apiClient';
import './MinedHackathons.css';

const PAGE_SIZE = 18;
const SNAPSHOT_PATH = '/mined-hackathons-20261025.json';

function reportedDay(value) {
  if (!value) return 'Not reported';
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return 'Not reported';
  return parsed.toLocaleDateString(undefined, {
    timeZone: 'UTC', year: 'numeric', month: 'short', day: 'numeric',
  });
}

function MinedListing({ item }) {
  const original = safeEventUrl(item.url);
  const provider = safeEventUrl(item.provider_url);
  return <article className="platform-card mined-card">
    <div className="mined-card-heading"><span className="mined-status">Unverified API listing</span><span className="mined-source">{item.source}</span></div>
    <h2>{item.title}</h2>
    <p className="mined-organizer">{item.organization || 'Organizer not confirmed'}</p>
    <dl>
      <div><dt>Provider-reported deadline</dt><dd>{reportedDay(item.reported_deadline)}</dd></div>
      <div><dt>Reported city</dt><dd>{item.location || 'Not provided'}</dd></div>
      <div><dt>Reported mode</dt><dd>{item.mode || 'Unknown'}</dd></div>
      <div><dt>Captured</dt><dd>25 Oct 2026</dd></div>
    </dl>
    <p className="mined-warning">May be expired or changed. Confirm dates, eligibility, and organizer details at the original listing.</p>
    <div className="mined-links">
      {original && <a href={original} target="_blank" rel="noopener noreferrer">Open original listing ↗</a>}
      {provider && <a href={provider} target="_blank" rel="noopener noreferrer">Brabble source ↗</a>}
    </div>
    <small>Data provided by <a href="https://brabble.ai/" target="_blank" rel="noopener noreferrer">Brabble.ai</a>; not independently verified by Hackathon Radar Finder.</small>
  </article>;
}

export default function MinedHackathons() {
  const [snapshot, setSnapshot] = useState(null);
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');
  const [platform, setPlatform] = useState('all');
  const [mode, setMode] = useState('all');
  const [page, setPage] = useState(1);

  useEffect(() => {
    const controller = new AbortController();
    fetch(SNAPSHOT_PATH, { signal: controller.signal })
      .then(response => { if (!response.ok) throw new Error('Archive snapshot unavailable'); return response.json(); })
      .then(data => {
        if (data.schema_version !== 1 || data.review_state !== 'unverified' ||
            data.record_count !== 206 || !Array.isArray(data.records) || data.records.length !== 206) {
          throw new Error('Archive snapshot failed integrity checks');
        }
        if (!controller.signal.aborted) setSnapshot(data);
      })
      .catch(reason => { if (!controller.signal.aborted) setError(reason.message || 'Could not load archive'); });
    return () => controller.abort();
  }, []);

  const results = useMemo(() => (snapshot?.records || []).filter(item => {
    const text = [item.title, item.organization, item.location].filter(Boolean).join(' ').toLowerCase();
    return (!search.trim() || text.includes(search.trim().toLowerCase())) &&
      (platform === 'all' || item.source === platform) &&
      (mode === 'all' || item.mode === mode);
  }), [snapshot, search, platform, mode]);
  const pages = Math.max(1, Math.ceil(results.length / PAGE_SIZE));
  const visible = results.slice((Math.min(page, pages) - 1) * PAGE_SIZE, Math.min(page, pages) * PAGE_SIZE);
  const changeFilter = (setter, value) => { setter(value); setPage(1); };

  return <section className="mined-archive" aria-label="Mined hackathon data archive">
    <div className="mined-intro">
      <span className="platform-eyebrow">HACKATHON RADAR RESEARCH ARCHIVE</span>
      <h1>Mined hackathon data</h1>
      <p>Browse <strong>206 historical API snapshot listings</strong>: 195 from Unstop and 11 from Devfolio, collected via <a href="https://brabble.ai/" target="_blank" rel="noopener noreferrer">Brabble.ai</a> on 25 October 2026.</p>
      <p className="mined-caution"><strong>Unverified research data — not the verified event catalog.</strong> These are archived provider-reported listings, not current registration offers or independently checked hackathon announcements. Dates, cities, organizers, and links may be outdated or incorrect, and some records could overlap with verified events. Do not use these records as model ground truth.</p>
      <Link to="/explore">Browse the verified catalog instead →</Link>
    </div>
    <div className="mined-controls">
      <label>Search archive<input value={search} onChange={event => changeFilter(setSearch, event.target.value)} placeholder="Title, organizer, or city" maxLength={255} /></label>
      <label>Original platform<select value={platform} onChange={event => changeFilter(setPlatform, event.target.value)}><option value="all">All platforms</option><option value="Unstop">Unstop</option><option value="Devfolio">Devfolio</option></select></label>
      <label>Reported mode<select value={mode} onChange={event => changeFilter(setMode, event.target.value)}><option value="all">All modes</option><option value="ONLINE">Online</option><option value="OFFLINE">Offline</option><option value="HYBRID">Hybrid</option></select></label>
      <button type="button" onClick={() => {setSearch(''); setPlatform('all'); setMode('all'); setPage(1);}}>Clear filters</button>
    </div>
    {error && <div className="platform-error" role="alert">{error}</div>}
    {!snapshot && !error && <p role="status">Loading archived listings…</p>}
    {snapshot && <>
      <p role="status" className="mined-count">{results.length} of {snapshot.record_count} archived listings · page {Math.min(page, pages)} of {pages}</p>
      {results.length === 0 ? <p>No matching archive listings. Try clearing a filter.</p> : <div className="platform-grid mined-grid">{visible.map(item => <MinedListing key={item.id} item={item} />)}</div>}
      {results.length > PAGE_SIZE && <nav className="platform-pagination" aria-label="Archive pages">
        <button type="button" disabled={page <= 1} onClick={() => setPage(p => Math.max(1, p - 1))}>Previous</button>
        <span>Page {page} of {pages}</span>
        <button type="button" disabled={page >= pages} onClick={() => setPage(p => Math.min(pages, p + 1))}>Next</button>
      </nav>}
    </>}
    <p className="platform-muted">Provenance: 25 October 2026 Brabble.ai API archive. Data provided by <a href="https://brabble.ai/docs" target="_blank" rel="noopener noreferrer">Brabble.ai</a>, with source listings on Unstop and Devfolio. Provider-reported deadlines are not organizer-confirmed event dates. Registration takes place on the original platform; this page does not collect registrations or payments.</p>
  </section>;
}
