import { useEffect, useMemo, useState } from 'react';
import { safeEventUrl } from './services/apiClient';
import './MinedHackathons.css';

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

/**
 * Archive cards render inside Explore's normal event grid. The source snapshot
 * remains explicitly unverified; it is never merged into the verified API.
 */
export default function MinedHackathons({ filters = {}, page = 1, pageSize = 12, onCountChange }) {
  const [snapshot, setSnapshot] = useState(null);
  const [error, setError] = useState('');
  useEffect(() => {
    const controller = new AbortController();
    fetch(SNAPSHOT_PATH, { signal: controller.signal })
      .then(response => { if (!response.ok) throw new Error('Additional listings unavailable'); return response.json(); })
      .then(data => {
        if (data.schema_version !== 1 || data.review_state !== 'unverified' ||
            data.record_count !== 206 || !Array.isArray(data.records) || data.records.length !== 206) {
          throw new Error('Additional listing snapshot failed integrity checks');
        }
        if (!controller.signal.aborted) setSnapshot(data);
      })
      .catch(reason => { if (!controller.signal.aborted) setError(reason.message || 'Could not load additional listings'); });
    return () => controller.abort();
  }, []);

  const results = useMemo(() => (snapshot?.records || []).filter(item => {
    const text = [item.title, item.organization, item.location].filter(Boolean).join(' ').toLowerCase();
    if (filters.q && !text.includes(filters.q.trim().toLowerCase())) return false;
    if (filters.location && !(item.location || '').toLowerCase().includes(filters.location.trim().toLowerCase())) return false;
    if (filters.mode && !(item.mode || '').toLowerCase().includes(filters.mode.trim().toLowerCase())) return false;
    // Never infer unknown college, organizer, state, or event dates from the archive.
    // The backend handles these filters for verified events only.
    if (filters.organizationId || filters.institutionId || filters.state ||
        filters.startFrom || filters.startTo || filters.deadlineFrom || filters.deadlineTo || filters.period) return false;
    return true;
  }), [snapshot, filters]);

  useEffect(() => { onCountChange?.(snapshot ? results.length : 0); }, [onCountChange, snapshot, results.length]);
  const start = Math.max(0, page - 1) * pageSize;
  const visible = results.slice(start, start + pageSize);
  return <>
    {error && <p role="alert" className="platform-error">{error}</p>}
    {visible.map(item => <MinedListing key={`archive-${item.id}`} item={item} />)}
  </>;
}
