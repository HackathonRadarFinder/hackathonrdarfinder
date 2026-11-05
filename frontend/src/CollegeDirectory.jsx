import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api, safeEventUrl } from './services/apiClient';

export default function CollegeDirectory() {
  const [draft, setDraft] = useState({ search: '', state: '', district: '' });
  const [query, setQuery] = useState({ ...draft, page: 1 });
  const [states, setStates] = useState([]);
  const [districts, setDistricts] = useState([]);
  const [facetsError, setFacetsError] = useState('');
  useEffect(() => {
    const controller = new AbortController();
    api.institutionFacets('', controller.signal)
      .then(data => { if (!controller.signal.aborted) setStates(data.states); })
      .catch(() => { if (!controller.signal.aborted) setFacetsError('State choices are unavailable. Reload to retry.'); });
    return () => controller.abort();
  }, []);
  useEffect(() => {
    const controller = new AbortController();
    setDistricts([]);
    if (draft.state) {
      api.institutionFacets(draft.state, controller.signal)
        .then(data => { if (!controller.signal.aborted) setDistricts(data.districts); })
        .catch(() => { if (!controller.signal.aborted) setFacetsError('District choices could not load.'); });
    }
    return () => controller.abort();
  }, [draft.state]);
  const [revision, setRevision] = useState(0);
  const [result, setResult] = useState(null);
  const key = JSON.stringify([query, revision]);
  useEffect(() => {
    const controller = new AbortController();
    api.institutions(query.state, query.search, controller.signal, query.page, 25, query.district)
      .then(data => { if (!controller.signal.aborted) setResult({ key, data }); })
      .catch(error => { if (!controller.signal.aborted) setResult({ key, error }); });
    return () => controller.abort();
  }, [query, revision, key]);
  const current = result?.key === key ? result : null;
  const data = current?.data;
  const filtered = Boolean(query.search || query.state || query.district);
  return <section aria-label="College directory">
    <h1>College directory</h1><p>Browse factual college records mined and structured from AISHE dashboard data. The portal has not independently verified individual institutions.</p>
    <form onSubmit={event => { event.preventDefault(); setQuery({ search: draft.search.trim(), state: draft.state.trim(), district: draft.district.trim(), page: 1 }); }}>
      <label>College name<input maxLength={255} value={draft.search} onChange={event => setDraft({ ...draft, search: event.target.value })} /></label>
      <label>State<select aria-label="State" value={draft.state} onChange={event => { setFacetsError(''); setDraft({ ...draft, state: event.target.value, district: '' }); }}><option value="">All states and union territories</option>{states.map(state => <option key={state} value={state}>{state}</option>)}</select></label>
      <label>District<select aria-label="District" value={draft.district} disabled={!draft.state} onChange={event => setDraft({ ...draft, district: event.target.value })}><option value="">All districts</option>{districts.map(district => <option key={district} value={district}>{district}</option>)}</select></label>
      {facetsError && <p role="alert">{facetsError}</p>}
      <button>Search colleges</button><button type="button" onClick={() => { const empty = { search: '', state: '', district: '' }; setDraft(empty); setQuery({ ...empty, page: 1 }); }}>Clear filters</button>
    </form>
    {!current && <p role="status">Loading colleges…</p>}
    {current?.error && <div className="platform-error" role="alert"><p>{current.error.message}</p><button onClick={() => setRevision(value => value + 1)}>Try again</button></div>}
    {data && <>
      <p role="status">{data.total.toLocaleString()} publicly listed colleges{filtered ? ' matching your filters' : ''}</p>
      {data.total === 0 && <div className="platform-empty"><h2>{filtered ? 'No colleges match these filters' : 'No colleges are publicly listed yet'}</h2><p>{filtered ? 'Try another name, state or district, or clear your filters.' : 'Public college records are not currently available. Check back later.'}</p></div>}
      <div className="platform-grid">{data.data.map(row => <article className="platform-card" key={row.id}>
        <h2>{row.name}</h2><p>{[row.state, row.district, row.city].filter(Boolean).join(' · ')}</p><p>{row.category} · {row.identifier}</p>
        <details><summary>College details and source</summary>
          {safeEventUrl(row.website) && <p><a href={safeEventUrl(row.website)} target="_blank" rel="noopener noreferrer">Institution website</a></p>}
          {safeEventUrl(row.source_url) ? <p><a href={safeEventUrl(row.source_url)} target="_blank" rel="noopener noreferrer">Directory source</a></p> : <p>A source link is not provided for this record.</p>}
          {row.last_verified_at && <p>Directory record updated: {String(row.last_verified_at).slice(0, 10)}</p>}
        </details><Link to={`/?institutionId=${row.id}`}>View related hackathons</Link>
      </article>)}</div>
      {data.total > 0 && <nav className="platform-pagination" aria-label="College directory pages"><button disabled={query.page <= 1} onClick={() => setQuery(value => ({ ...value, page: value.page - 1 }))}>Previous</button><span>Page {data.page} of {Math.max(1, Math.ceil(data.total / data.page_size))}</span><button disabled={query.page * data.page_size >= data.total} onClick={() => setQuery(value => ({ ...value, page: value.page + 1 }))}>Next</button></nav>}
    </>}
  </section>;
}
