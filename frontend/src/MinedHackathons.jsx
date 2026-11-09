import { useEffect, useState } from 'react';
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

/** Display the provider card alongside normal event cards, never as a verified event. */
export function MinedListing({ item }) {
  const original = safeEventUrl(item.url);
  const provider = safeEventUrl(item.provider_url);
  return <article className="platform-card mined-card">
    <div className="platform-card-top">
      <span className="platform-org">{item.organization || 'Organizer not confirmed'}</span>
      <span className="mined-status">Unverified</span>
    </div>
    <h2>{original ? <a href={original} target="_blank" rel="noopener noreferrer">{item.title}</a> : item.title}</h2>
    <p>Provider-reported {item.source} listing. Details may be outdated; confirm with the organizer before applying.</p>
    <dl>
      <div><dt>Mode (reported)</dt><dd>{item.mode || 'Not provided'}</dd></div>
      <div><dt>Location (reported)</dt><dd>{item.location || 'Not provided'}</dd></div>
      <div><dt>Deadline (reported)</dt><dd>{reportedDay(item.reported_deadline)}</dd></div>
      <div><dt>Starts</dt><dd>Not independently confirmed</dd></div>
    </dl>
    <small>Snapshot: 25 Oct 2026 · Data provided by <a href="https://brabble.ai/" target="_blank" rel="noopener noreferrer">Brabble.ai</a></small>
    <div className="mined-links">
      {original && <a className="platform-action" href={original} target="_blank" rel="noopener noreferrer">View original listing ↗</a>}
      {provider && <a href={provider} target="_blank" rel="noopener noreferrer">Provider record ↗</a>}
    </div>
    <small>Unverified API data, not independently verified by Hackathon Radar Finder. May duplicate a verified catalog event.</small>
  </article>;
}

/** Fetches only a static, attributed snapshot; it does not change database approval status. */
export function useMinedArchive() {
  const [state, setState] = useState({ loading: true, records: [], error: '' });
  useEffect(() => {
    const controller = new AbortController();
    fetch(SNAPSHOT_PATH, { signal: controller.signal })
      .then(response => { if (!response.ok) throw new Error('Provider snapshot unavailable'); return response.json(); })
      .then(data => {
        if (data.schema_version !== 1 || data.review_state !== 'unverified' ||
            data.record_count !== 206 || !Array.isArray(data.records) || data.records.length !== 206) {
          throw new Error('Provider snapshot failed integrity checks');
        }
        if (!controller.signal.aborted) setState({ loading: false, records: data.records, error: '' });
      })
      .catch(error => {
        if (!controller.signal.aborted) setState({ loading: false, records: [], error: error.message || 'Could not load provider listings' });
      });
    return () => controller.abort();
  }, []);
  return state;
}
