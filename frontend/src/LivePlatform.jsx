import { useCallback, useEffect, useState } from 'react';
import { Link, NavLink, Navigate, Route, Routes, useLocation, useParams } from 'react-router-dom';
import { Bookmark, BrainCircuit, ExternalLink, Moon, Sun } from 'lucide-react';
import { useAuth } from './context/AuthContext';
import { api, safeEventUrl } from './services/apiClient';
import Login from './pages/auth/Login';
import Register from './pages/auth/Register';
import { CompanyLogo } from './demo/CompanyLogo';
import './index.css';
import './App.css';
import './platform.css';
import ProviderCredit from './components/ProviderCredit';
import AdminWorkspace from './AdminWorkspace';

function useResource(load) {
  const [state, setState] = useState({ key: null });
  const [revision, setRevision] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    load(controller.signal).then(data => {
      if (!controller.signal.aborted) setState({ key: load, revision, loading: false, data, error: null });
    }).catch(error => {
      if (!controller.signal.aborted) setState({ key: load, revision, loading: false, data: null, error });
    });
    return () => controller.abort();
  }, [load, revision]);
  const current = state.key === load && state.revision === revision ? state : { loading: true, data: null, error: null };
  return { ...current, retry: () => setRevision(value => value + 1) };
}

function Feedback({ resource }) {
  if (resource.loading) return <p role="status">Loading…</p>;
  if (resource.error) return <div role="alert" className="platform-error"><p>{resource.error.message}</p>
    {resource.error.requestId && <small>Request reference: {resource.error.requestId}</small>}
    <button onClick={resource.retry}>Try again</button></div>;
  return null;
}

function date(value, dayOnly = false) {
  if (!value) return 'Not provided';
  const parsed = new Date(/[zZ]|[+-]\d\d:\d\d$/.test(value) ? value : `${value}Z`);
  if (Number.isNaN(parsed.getTime())) return 'Not provided';
  return dayOnly ? `${parsed.toLocaleDateString(undefined, { timeZone: 'UTC' })} (time not published)`
    : parsed.toLocaleString(undefined, { timeZoneName: 'short' });
}

export function EventCard({ event, saved, toggle, organization }) {
  return <article className="platform-card">
    <div className="platform-card-top"><span className="platform-org"><CompanyLogo name={organization || ''} size={24} />{organization || 'Organization not provided'}</span>
      <button aria-label={`${saved ? 'Remove' : 'Add'} saved event for ${event.title}`} aria-pressed={saved} onClick={() => toggle(event.id)}><Bookmark size={18} fill={saved ? 'currentColor' : 'none'} /></button></div>
    <h2><Link to={`/event/${event.id}`}>{event.title}</Link></h2>
    <p>{event.description || 'No description provided.'}</p>
    <dl><div><dt>Mode</dt><dd>{event.mode || 'Not provided'}</dd></div><div><dt>Location</dt><dd>{event.location || 'Not provided'}</dd></div>
      <div><dt>Registration deadline</dt><dd>{date(event.registration_deadline)}</dd></div>
      <div><dt>Starts</dt><dd>{date(event.start_date, event.description?.includes('Date precision: day'))}</dd></div><div><dt>Prize</dt><dd>{event.prize || 'Not provided'}</dd></div></dl>
    <ProviderCredit acquisition={event.acquisition} />
    <Link className="platform-action" to={`/event/${event.id}`}>View details →</Link>
  </article>;
}

function Explore({ saved, toggle }) {
  const [filters, setFilters] = useState({ q: '', location: '', mode: '', organizationId: '', state: '', institutionId: '', startFrom: '', startTo: '', deadlineFrom: '', deadlineTo: '', period: '', sort: 'id', pageSize: 12 });
  const [draft, setDraft] = useState(filters);
  const [collegeSearch, setCollegeSearch] = useState('');
  const [page, setPage] = useState(1);
  const organizations = useResource(api.organizations);
  const resource = useResource(useCallback(signal => api.events({ ...filters, page }, signal), [filters, page]));
  const institutions = useResource(useCallback(signal => api.institutions(draft.state, collegeSearch, signal), [draft.state, collegeSearch]));
  const names = new Map((organizations.data || []).map(org => [org.id, org.name]));
  const result = resource.data;
  return <><section className="platform-hero"><span className="platform-eyebrow">HACKATHON RADAR</span><h1>Find your next<br /><em>building opportunity.</em></h1><p>Explore events from the backend catalog. Clear filters, real dates, and a place to keep your next idea.</p><a href="/demo/">Explore the design demo →</a></section>
    <div className="platform-explore"><aside className="platform-filter"><h2>Explore events</h2>
      <form onSubmit={event => { event.preventDefault(); setPage(1); setFilters({ ...draft }); }}>
        <label>Search<input value={draft.q} maxLength={255} placeholder="Title or description" onChange={event => setDraft({ ...draft, q: event.target.value })} /></label>
        <label>Location<input value={draft.location} maxLength={255} placeholder="City or region" onChange={event => setDraft({ ...draft, location: event.target.value })} /></label>
        <label>State or union territory<input value={draft.state} maxLength={100} placeholder="Exact state name" onChange={event => setDraft({ ...draft, state: event.target.value, institutionId: '' })} /></label>
        <label>Find a college<input value={collegeSearch} maxLength={255} placeholder="Institution name" onChange={event => { setCollegeSearch(event.target.value); setDraft({ ...draft, institutionId: '' }); }} /></label>
        <label>College or university<select value={draft.institutionId} onChange={event => setDraft({ ...draft, institutionId: event.target.value })}><option value="">All institutions</option>{(institutions.data?.data || []).map(row => <option key={row.id} value={row.id}>{row.name}</option>)}</select></label>
        {institutions.data?.total > 100 && <p>Showing the first 100 institutions. Narrow by state and institution name.</p>}
        {institutions.error && <p role="alert">Institution directory could not load. <button type="button" onClick={institutions.retry}>Retry directory</button></p>}
        <label>Mode<input value={draft.mode} maxLength={50} placeholder="Online, hybrid…" onChange={event => setDraft({ ...draft, mode: event.target.value })} /></label>
        <label>Organization<select value={draft.organizationId} onChange={event => setDraft({ ...draft, organizationId: event.target.value })}><option value="">All organizations</option>{(organizations.data || []).map(org => <option key={org.id} value={org.id}>{org.name}</option>)}</select></label>
        <label>Starts on or after (UTC)<input type="date" value={draft.startFrom} max={draft.startTo || undefined} onChange={event => setDraft({ ...draft, startFrom: event.target.value })} /></label>
        <label>Starts on or before (UTC)<input type="date" value={draft.startTo} min={draft.startFrom || undefined} onChange={event => setDraft({ ...draft, startTo: event.target.value })} /></label>
        <label>Registration deadline on or after (UTC)<input type="date" value={draft.deadlineFrom} max={draft.deadlineTo || undefined} onChange={event => setDraft({ ...draft, deadlineFrom: event.target.value })} /></label>
        <label>Registration deadline on or before (UTC)<input type="date" value={draft.deadlineTo} min={draft.deadlineFrom || undefined} onChange={event => setDraft({ ...draft, deadlineTo: event.target.value })} /></label>
        <label>Event period<select value={draft.period} onChange={event => setDraft({ ...draft, period: event.target.value })}><option value="">All dates</option><option value="upcoming">Upcoming or ongoing</option><option value="past">Past</option></select></label>
        <label>Sort events<select value={draft.sort} onChange={event => setDraft({ ...draft, sort: event.target.value })}><option value="id">Catalog order</option><option value="title">Title</option><option value="start_date">Start date</option><option value="deadline">Registration deadline</option></select></label>
        {organizations.error && <p role="alert">Organization filters could not load. <button type="button" onClick={organizations.retry}>Retry</button></p>}
        <label>Events per page<select value={draft.pageSize} onChange={event => setDraft({ ...draft, pageSize: Number(event.target.value) })}><option>12</option><option>24</option><option>48</option></select></label>
        <button className="platform-primary" type="submit">Apply filters</button><button type="button" onClick={() => { const cleared = { q: '', location: '', mode: '', organizationId: '', state: '', institutionId: '', startFrom: '', startTo: '', deadlineFrom: '', deadlineTo: '', period: '', sort: 'id', pageSize: 12 }; setCollegeSearch(''); setDraft(cleared); setFilters(cleared); setPage(1); }}>Reset</button>
      </form><p className="platform-muted">The catalog includes historical events. Use start dates to narrow upcoming results. Dates filter by UTC calendar day; events without start dates are excluded when filtering. Choose a sort order above; dates without published values appear last.</p>
    </aside><section aria-label="Event results" aria-busy={resource.loading}><Feedback resource={resource} />
      {result && <><p role="status">{result.total} events · page {result.page}</p>{!result.data.length && <div className="platform-empty"><h2>No events found</h2><p>Try another location or reset your filters.</p></div>}
        <div className="platform-grid">{result.data.map(event => <EventCard key={event.id} event={event} saved={saved.includes(event.id)} toggle={toggle} organization={names.get(event.organization_id)} />)}</div>
        <nav className="platform-pagination" aria-label="Event pages"><button disabled={page <= 1 || resource.loading} onClick={() => setPage(value => value - 1)}>Previous</button><span>Page {page} of {Math.max(1, Math.ceil(result.total / result.page_size))}</span><button disabled={page * result.page_size >= result.total || resource.loading} onClick={() => setPage(value => value + 1)}>Next</button></nav></>}
    </section></div></>;
}

function InstitutionDirectory() {
  const [filters, setFilters] = useState({state:'', q:''});
  const [draft, setDraft] = useState(filters);
  const [page, setPage] = useState(1);
  const resource = useResource(useCallback(signal => api.institutions(filters.state, filters.q, signal, page, 25), [filters, page]));
  const result = resource.data;
  return <section aria-label="University directory"><h1>University directory</h1><p>Browse the stored institution directory. Directory entries do not imply permission to collect from their websites.</p>
    <form onSubmit={event => {event.preventDefault();setFilters({...draft});setPage(1);}}><label>University name search<input maxLength={255} value={draft.q} onChange={event => setDraft({...draft,q:event.target.value})} /></label><label>Directory state<input maxLength={100} value={draft.state} placeholder="Exact state or union territory" onChange={event => setDraft({...draft,state:event.target.value})} /></label><button type="submit">Search universities</button><button type="button" onClick={() => {const empty={state:'',q:''};setDraft(empty);setFilters(empty);setPage(1);}}>Reset directory</button></form>
    <Feedback resource={resource} />{result && <><p role="status">{result.total} institutions | page {page}</p>{!result.data.length && <p>No institutions match these filters.</p>}<div className="platform-grid">{result.data.map(row => <article className="platform-card" key={row.id}><h2>{row.name}</h2><p>{row.state}{row.city ? ` | ${row.city}` : ''}</p><p>{row.category} | {row.identifier}</p>{safeEventUrl(row.website) && <a href={safeEventUrl(row.website)} target="_blank" rel="noopener noreferrer">Institution website</a>}{safeEventUrl(row.source_url) && <p><a href={safeEventUrl(row.source_url)} target="_blank" rel="noopener noreferrer">Directory source</a></p>}<small>Directory verified: {date(row.last_verified_at, true)}</small></article>)}</div><nav aria-label="Directory pages" className="platform-pagination"><button disabled={page<=1 || resource.loading} onClick={() => setPage(value => value-1)}>Previous institutions</button><span>Page {page} of {Math.max(1,Math.ceil(result.total/25))}</span><button disabled={page*25>=result.total || resource.loading} onClick={() => setPage(value => value+1)}>Next institutions</button></nav></>}
  </section>;
}

function EventDetails({ saved, toggle }) {
  const { id } = useParams();
  const resource = useResource(useCallback(signal => api.event(id, signal), [id]));
  const discovery = useResource(useCallback(signal => api.eventDiscovery(id, signal), [id]));
  const event = resource.data;
  const link = safeEventUrl(event?.url);
  const registrationLink = safeEventUrl(event?.registration_url);
  return <section className="platform-detail"><Link to="/explore">← Back to events</Link><Feedback resource={resource} />{event && <>
    <span className="platform-eyebrow">EVENT DETAILS</span><h1>{event.title}</h1><p className="platform-description">{event.description || 'No description provided.'}</p>
    <dl><div><dt>Starts</dt><dd>{date(event.start_date, event.description?.includes('Date precision: day'))}</dd></div><div><dt>Ends</dt><dd>{date(event.end_date, event.description?.includes('Date precision: day'))}</dd></div><div><dt>Registration deadline</dt><dd>{date(event.registration_deadline)}</dd></div><div><dt>Location / mode</dt><dd>{event.location || 'Not provided'} / {event.mode || 'Not provided'}</dd></div><div><dt>Prize</dt><dd>{event.prize || 'Not provided'}</dd></div><div><dt>Source</dt><dd>{event.source || 'Not provided'}</dd></div><div><dt>State</dt><dd>{event.state || 'Not provided'}</dd></div><div><dt>Eligibility</dt><dd>{event.eligibility || 'Not provided'}</dd></div></dl>
    <ProviderCredit acquisition={event.acquisition} />
    <button onClick={() => toggle(event.id)} aria-pressed={saved.includes(event.id)}>{saved.includes(event.id) ? 'Remove saved event' : 'Save to account'}</button>
    {link ? <a className="platform-action" href={link} target="_blank" rel="noopener noreferrer">Visit organizer website <ExternalLink size={16} /></a> : <p>No valid organizer link is available.</p>}
    {registrationLink && <a className="platform-action" href={registrationLink} target="_blank" rel="noopener noreferrer">Registration information <ExternalLink size={16} /></a>}
    <p className="platform-muted">Source observed: {date(event.scraped_at)}. This is a stored snapshot; check the organizer for changes.</p>
    <section aria-label="Discovery history"><h2>Discovery and update history</h2><Feedback resource={discovery} />
      {discovery.data && <>{discovery.data.evidence.length === 0 && <p>No automated discovery evidence is recorded for this event.</p>}
        {discovery.data.evidence.slice(0, 3).map((item, index) => <p key={index}>Collected by {item.source} at {date(item.observed_at)} using {item.adapter_version}.</p>)}
        {discovery.data.versions.map(item => <details key={item.version}><summary>Version {item.version} · {date(item.observed_at)}</summary>
          <p>Recorded fields: {item.changed_fields.join(', ') || 'Initial adopted snapshot'}</p>
          <p>{item.snapshot.title}</p><p>Starts: {date(item.snapshot.start_date, item.snapshot.description?.includes('Date precision: day'))}</p></details>)}</>}
    </section>
    <p className="platform-muted">Registration takes place on the organizer’s website. This portal does not register you.</p>
  </>}</section>;
}

function Bookmarks({ saved, toggle }) {
  const { user } = useAuth();
  const resource = useResource(useCallback(signal => user ? api.saved(signal).then(rows => rows.filter(row => saved.includes(row.id))) : Promise.resolve([]), [user, saved]));
  return <section><h1>Saved events</h1><p>Saved to your account. Enable email reminders in Preferences.</p>
    {!user && <Link to="/login">Sign in to view saved events</Link>}<Feedback resource={resource} />
    {user && resource.data?.length === 0 && <p>No saved events yet.</p>}
    <div className="platform-grid">{resource.data?.map(event => <EventCard key={event.id} event={event} saved toggle={toggle} />)}</div></section>;
}

function DiscoveryCoverage() {
  const resource = useResource(api.discoveryCoverage);
  const runs = useResource(api.discoveryRuns);
  const labels = { institutions_indexed: 'Institutions indexed', institutions_with_verified_websites: 'Verified institution websites', approved_sources: 'Approved sources', institutions_with_approved_sources: 'Institutions with approved sources', sources_successfully_checked: 'Sources successfully checked', events_discovered: 'Announcement revisions discovered', validated_events: 'Validated event revisions', pending_review: 'Awaiting review', duplicate_records: 'Duplicate observations', failed_collections: 'Failed collections', sources_awaiting_permission: 'Sources awaiting permission' };
  return <section aria-label="Discovery coverage"><h2>Discovery coverage and failures</h2><p>Source coverage does not measure hackathon coverage. Only reviewed announcements enter the public catalog.</p><Feedback resource={resource} />
    {resource.data && <><dl>{Object.entries(labels).map(([key, label]) => <div key={key}><dt>{label}</dt><dd>{resource.data[key]}</dd></div>)}</dl><p>Last successful collection: {date(resource.data.last_successful_collection)}</p></>}
    <h3>Recent collection runs</h3><Feedback resource={runs} />{runs.data?.length === 0 && <p>No collection runs recorded.</p>}
    <ul>{runs.data?.slice(0, 20).map(run => <li key={run.id}>{run.source_key || run.source_id}: {run.status} ? {date(run.started_at)}{run.error_code ? ` ? ${run.error_code}` : ''}</li>)}</ul>
  </section>;
}

function Admin() {
  const { user } = useAuth();
  const resource = useResource(useCallback(signal => user ? api.admin(signal) : Promise.reject(new Error('Sign in to request admin access.')), [user]));
  return <section><h1>Administration</h1>{['administrator', 'source_manager'].includes(user?.role) && <DiscoveryCoverage />}<p>The backend checks current permissions on every request.</p><Feedback resource={resource} />
    {!user && <Link to="/login">Sign in</Link>}{resource.data && <><div className="platform-grid">{Object.entries(resource.data.stats).map(([key, value]) => <article className="platform-card" key={key}><h2>{value}</h2><p>{key.replaceAll('_', ' ')}</p></article>)}</div>
      <h2>Users</h2><div className="platform-table" tabIndex={0} role="region" aria-label="User accounts table"><table><thead><tr><th>Name</th><th>Email</th><th>Status</th><th>Roles</th></tr></thead><tbody>{resource.data.users.map(user => <tr key={user.id}><td>{user.name}</td><td>{user.email}</td><td>{user.status}</td><td>{user.roles.join(', ')}</td></tr>)}</tbody></table></div>
      <h2>Organizations</h2><ul>{resource.data.organizations.map(org => <li key={org.id}>{org.name}</li>)}</ul>
      <p className="platform-muted">Use the administration tools below to manage records, review announcements, and inspect audit history.</p></>}
    {user?.role === 'administrator' && <AdminWorkspace />}
  </section>;
}

function Predictions() {
  const resource = useResource(api.predictions);
  const readiness = useResource(api.predictionReadiness);
  return <section><h1>Predictions</h1><p>Prediction - not officially announced. Only forecasts from an approved, calibrated model meeting the public confidence policy appear here. Organizer dates may change.</p>
    <Feedback resource={resource} /><Feedback resource={readiness} />
    {readiness.data && <p aria-label="Prediction data readiness">{readiness.data.reviewed_editions} reviewed event editions; {readiness.data.recurring_series} recurring series. {readiness.data.reason}</p>}
    <div className="platform-grid">{resource.data?.map(row => <article className="platform-card" key={row.organization_id}>
      <h2>{row.organization}</h2><p>Prediction - not officially announced</p>
      <p>{row.window ? `${row.window.start} to ${row.window.end}` : 'No supported date window'}</p>
      <p>Confidence: {row.confidence_band || 'unavailable'}</p><p>{row.reasoning}</p>
      <small>Model: {row.model_version || 'unavailable'}; generated: {date(row.generated_at)}. {row.historical_events} distinct historical event dates.</small>
      {row.evidence?.length > 0 && <details><summary>Historical source evidence (latest 10 records)</summary><ul>{row.evidence.map((item, index) =>
        <li key={`${item.date}-${index}`}>{item.date}: {safeEventUrl(item.url) ? <a href={safeEventUrl(item.url)} target="_blank" rel="noopener noreferrer">{item.title}</a> : item.title}</li>)}</ul></details>}
    </article>)}</div>
    {resource.data?.length === 0 && <p>No eligible public predictions. The current baseline is uncalibrated; insufficient or sub-threshold forecasts remain internal for evaluation. Confirmed events are still available in Explore.</p>}</section>;
}

function ProfileEditor() {
  const { user } = useAuth();
  const [name, setName] = useState(user?.name || '');
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  async function submit(event) {
    event.preventDefault(); setBusy(true); setMessage('');
    try { await api.updateProfile(name); setMessage('Display name updated.'); }
    catch (error) { setMessage(error.message); }
    finally { setBusy(false); }
  }
  return <form onSubmit={submit} aria-label="Account profile"><label>Display name<input value={name} required minLength={1} maxLength={100} onChange={event => setName(event.target.value)} /></label><button disabled={busy || !name.trim()}>{busy ? 'Saving name...' : 'Update display name'}</button>{message && <p role="status">{message}</p>}</form>;
}

function Personalization() {
  const { user } = useAuth();
  const resource = useResource(useCallback(signal => api.request('/account/discovery-preferences', { signal }), []));
  const recommendations = useResource(useCallback(signal => api.request('/account/recommendations', { signal }), []));
  const [draft, setDraft] = useState(null);
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);
  const values = draft || resource.data;
  async function submit(event) {
    event.preventDefault(); setBusy(true); setMessage('');
    try { await api.request('/account/discovery-preferences', { method: 'PUT', body: values }); setMessage('Discovery preferences saved.'); recommendations.retry(); }
    catch (error) { setMessage(error.message); }
    finally { setBusy(false); }
  }
  return <section aria-label="Personalization"><h2>Your account and interests</h2><ProfileEditor /><p>{user?.name} ? {user?.email}</p><Feedback resource={resource} />
    {values && <form onSubmit={submit}>{Object.entries({preferred_location:'Preferred city or location',preferred_mode:'Preferred mode',interests:'Interests (comma separated)'}).map(([key,label]) => <label key={key}>{label}<input value={values[key]} maxLength={key === 'interests' ? 255 : key === 'preferred_mode' ? 50 : 100} onChange={event => setDraft({...values,[key]:event.target.value})} /></label>)}<label><input type="checkbox" checked={values.in_app_reminders} onChange={event => setDraft({...values,in_app_reminders:event.target.checked})} />In-app saved-event reminders</label><button disabled={busy}>Save discovery preferences</button></form>}
    {message && <p role="status">{message}</p>}<h2>Recommended for you</h2><p>Matches use stated preferences and saved events. Relevance scores are rules, not prediction probabilities.</p><Feedback resource={recommendations} />
    {recommendations.data?.data.length === 0 && <p>No matching upcoming events yet. Add interests or save events to improve matching.</p>}
    {recommendations.data?.data.map(({event,reasons}) => <article className="platform-card" key={event.id}><h3><Link to={`/event/${event.id}`}>{event.title}</Link></h3><p>{reasons.join(' ? ')}</p></article>)}
  </section>;
}

function Preferences() {
  const { user } = useAuth();
  const resource = useResource(useCallback(signal => user ? api.preferences(signal) : Promise.resolve(null), [user]));
  const [draft, setDraft] = useState(null);
  const [message, setMessage] = useState(null);
  const [busy, setBusy] = useState(false);
  const notifications = useResource(useCallback(signal => user ? api.notifications(signal) : Promise.resolve([]), [user]));
  async function markRead(id) {
    try { await api.readNotification(id); notifications.retry(); }
    catch (error) { setMessage(error.message); }
  }
  const values = draft?.userId === user?.id ? draft.values : resource.data;
  async function submit(event) {
    event.preventDefault(); setBusy(true); setMessage(null);
    try { await api.updatePreferences(values); setMessage('Preferences saved. Reminders require a saved event and an enabled email worker.'); }
    catch (error) { setMessage(error.message); }
    finally { setBusy(false); }
  }
  return <section><h1>Email reminder preferences</h1><p>Opt in to reminders for your saved events within 24 hours of the event or registration deadline. Email delivery depends on server configuration.</p>
    {!user && <Link to="/login">Sign in to configure reminders</Link>}<Feedback resource={resource} />
    {user && values && <form onSubmit={submit}>{Object.entries({email_reminders: 'I consent to email reminders', email_registration_reminders: 'Registration deadlines', email_upcoming_reminders: 'Upcoming events'}).map(([key, label]) =>
      <label key={key}><input type="checkbox" checked={values[key]} onChange={event => setDraft({userId: user.id, values: {...values, [key]: event.target.checked}})} />{label}</label>)}
      <button disabled={busy} type="submit">Save preferences</button></form>}{message && <p role="status">{message}</p>}
    {user && <Personalization key={user.id} />}
    {user && <><h2>Account notifications</h2><p>Latest 100 stored notices. Email delivery records are separate.</p><Feedback resource={notifications} />
      {notifications.data?.length === 0 && <p>No account notifications yet.</p>}
      {notifications.data?.map(row => <article className="platform-card" key={row.id}><h3>{row.title}</h3><p>{row.message}</p>
        {row.is_read ? <small>Read</small> : <button onClick={() => markRead(row.id)}>Mark as read</button>}</article>)}</>}
  </section>;
}

export default function LivePlatform() {
  const { user, logout, isLoading, authError } = useAuth();
  const location = useLocation();
  const [mobileOpenKey, setMobileOpenKey] = useState(null);
  const mobileOpen = mobileOpenKey === location.key;
  const [dark, setDark] = useState(false);
  const [savedState, setSavedState] = useState({ userId: null, ids: [] });
  const saved = savedState.userId === user?.id ? savedState.ids : [];
  const [bookmarkError, setBookmarkError] = useState(null);
  const [saving, setSaving] = useState(false);
  useEffect(() => {
    if (!user) return;
    const controller = new AbortController();
    api.saved(controller.signal).then(rows => {
      if (!controller.signal.aborted) setSavedState({userId: user.id, ids: rows.map(row => row.id)});
    }).catch(error => { if (!controller.signal.aborted) setBookmarkError(error.message); });
    return () => controller.abort();
  }, [user]);
  async function toggle(id) {
    if (!user) { setBookmarkError('Sign in to save events to your account.'); return; }
    if (saving) return;
    setSaving(true);
    try {
      await api.save(id, saved.includes(id));
      const rows = await api.saved();
      setSavedState({userId: user.id, ids: rows.map(row => row.id)});
      setBookmarkError(null);
    } catch (error) { setBookmarkError(error.message); }
    finally { setSaving(false); }
  }
  useEffect(() => { window.scrollTo({ top: 0 }); document.getElementById('platform-content')?.focus(); }, [location.pathname]);
  return <div className={`platform ${dark ? 'platform-dark' : ''}`}><a className="platform-skip" href="#platform-content">Skip to content</a>
    <header className="platform-header"><Link className="platform-brand" to="/"><BrainCircuit size={26} />Hackathon <strong>Radar</strong></Link>
      <button className="platform-menu" aria-expanded={mobileOpen} aria-controls="platform-navigation" onClick={() => setMobileOpenKey(mobileOpen ? null : location.key)}>Menu</button>
      <nav id="platform-navigation" className={mobileOpen ? 'open' : ''} aria-label="Main navigation"><NavLink to="/explore">Explore</NavLink><NavLink to="/universities">Universities</NavLink><NavLink to="/saved">Saved events</NavLink><NavLink to="/predictions">Predictions</NavLink><NavLink to="/notifications">Preferences</NavLink><NavLink to="/admin">Admin</NavLink><a href="/demo/">Design demo</a></nav>
      <div className="platform-session"><button aria-label={`Use ${dark ? 'light' : 'dark'} theme`} onClick={() => setDark(value => !value)}>{dark ? <Sun size={18} /> : <Moon size={18} />}</button>{user ? <><span>{user.name}</span><button disabled={isLoading} onClick={logout}>Sign out</button></> : <Link to="/login">Sign in</Link>}</div>
    </header><main id="platform-content" tabIndex={-1}><div className="platform-container">{authError && <p role="alert">{authError}</p>}{bookmarkError && <p role="alert">{bookmarkError}</p>}
      <Routes><Route path="/" element={<Explore saved={saved} toggle={toggle} />} /><Route path="/home" element={<Navigate replace to="/" />} /><Route path="/explore" element={<Explore saved={saved} toggle={toggle} />} /><Route path="/event/:id" element={<EventDetails saved={saved} toggle={toggle} />} /><Route path="/universities" element={<InstitutionDirectory />} /><Route path="/saved" element={<Bookmarks saved={saved} toggle={toggle} />} /><Route path="/login" element={<Login />} /><Route path="/register" element={<Register />} /><Route path="/forgot-password" element={<section><h1>Password reset unavailable</h1><p>The current backend does not support password reset. No email has been sent.</p><Link to="/login">Return to sign in</Link></section>} /><Route path="/admin/*" element={<Admin />} /><Route path="/notifications" element={<Preferences key={user?.id || "guest"} />} /><Route path="/predictions" element={<Predictions />} /><Route path="*" element={<section><h1>Page not found</h1><Link to="/">Return to events</Link></section>} /></Routes>
    </div></main><footer className="platform-footer">Hackathon Radar · Backend catalog and saved events. <a href="/demo/">Fictional design demo</a></footer></div>;
}
