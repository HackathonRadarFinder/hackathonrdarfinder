import { useEffect, useState } from 'react';
import { api, safeEventUrl } from './services/apiClient';
import BulkReviewPanel from './BulkReviewPanel';
import { BULK_REVIEW_LIMIT, encodeCsvToBase64, prepareBrabbleArchiveCsv } from './adminBulkReview';

const roles = ['user', 'institution_coordinator', 'reviewer', 'source_manager', 'data_scientist', 'administrator'];
const sections = {
  sources: '/admin/discovery/sources', review: '/admin/discovery/announcements',
  audit: '/admin/audit', roles: '/admin/users', events: '/admin/events',
  organizations: '/admin/organizations', notifications: '/admin/notification-monitor',
  duplicates: '/admin/duplicates',
};
const sourceExample = { key: '', name: '', adapter: 'rss-v1', url: '', enabled: false,
  interval_seconds: 21600, owner: '', basis: '', reference: '', reviewed_at: '', expires_at: '', terms_permit: false };

/** All requests use the shared in-memory session and backend role checks. */
export default function AdminWorkspace() {
  const [tab, setTab] = useState('review');
  const [resource, setResource] = useState(null);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);
  const [revision, setRevision] = useState(0);
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState('pending');
  const [editor, setEditor] = useState(null);
  const [text, setText] = useState('');
  const [note, setNote] = useState('');
  const [dataset, setDataset] = useState({ source_key: '', approval_reference: '' });
  const [upload, setUpload] = useState(null);
  const [selectedRows, setSelectedRows] = useState({});
  const [reviewDrafts, setReviewDrafts] = useState({});
  function clearSelection() { setSelectedRows({}); setReviewDrafts({}); }
  function toggleReview(row, checked) {
    if (!checked) {
      setSelectedRows(previous => { const next = { ...previous }; delete next[row.id]; return next; });
      setReviewDrafts(previous => { const next = { ...previous }; delete next[row.id]; return next; });
      return;
    }
    if (!selectedRows[row.id] && Object.keys(selectedRows).length >= BULK_REVIEW_LIMIT) {
      setError(`Select at most ${BULK_REVIEW_LIMIT} announcements per bulk action.`);
      return;
    }
    setSelectedRows(previous => ({ ...previous, [row.id]: row }));
    setReviewDrafts(previous => ({ ...previous, [row.id]: previous[row.id] || { json: JSON.stringify(row.payload, null, 2), evidenceChecked: false } }));
    setError('');
  }
  function selectPageForReview(items) {
    const available = items.filter(row => row.status === 'pending' && !selectedRows[row.id]);
    const remaining = BULK_REVIEW_LIMIT - Object.keys(selectedRows).length;
    const added = available.slice(0, Math.max(0, remaining));
    setSelectedRows(previous => ({ ...previous, ...Object.fromEntries(added.map(row => [row.id, row])) }));
    setReviewDrafts(previous => ({ ...previous, ...Object.fromEntries(added.map(row =>
      [row.id, { json: JSON.stringify(row.payload, null, 2), evidenceChecked: false }])) }));
    if (available.length > added.length) setMessage(`Selected ${added.length} additional records; maximum ${BULK_REVIEW_LIMIT} per batch.`);
  }
  function bulkReviewCompleted({ approved, error: failed }) {
    if (approved.length) {
      setSelectedRows(previous => { const next = { ...previous }; for (const id of approved) delete next[id]; return next; });
      setReviewDrafts(previous => { const next = { ...previous }; for (const id of approved) delete next[id]; return next; });
    }
    setMessage(`${approved.length} verified announcement(s) published. ${failed ? 'Other records remain pending.' : ''}`);
    setError(failed || '');
    setRevision(value => value + 1);
  }
  async function stageBrabbleArchive() {
    setBusy(true); setError(''); setMessage('');
    try {
      const source = (result?.data || []).find(row => row.key === dataset.source_key);
      if (!source || source.config?.adapter !== 'brabble-api-v1' || !source.enabled || !source.config?.terms_permit ||
          dataset.approval_reference !== source.config?.reference) {
        throw new Error('Select an enabled Brabble API source with documented reuse permission and the matching approval reference.');
      }
      const response = await fetch('/mined-hackathons-20261025.json', { cache: 'no-cache' });
      if (!response.ok) throw new Error('Could not load the preserved 206-listing snapshot.');
      const csv = prepareBrabbleArchiveCsv(await response.json());
      const imported = await api.request('/admin/discovery/dataset-imports', { method: 'POST', body: {
        source_key: dataset.source_key, approval_reference: dataset.approval_reference,
        filename: 'brabble-archive-review-20261025.csv', content_base64: encodeCsvToBase64(csv),
      } });
      setMessage(`${imported.candidates_inserted} source listings staged in the approval queue; ${imported.candidate_duplicates} previously present. No listing was approved automatically.`);
      clearSelection(); setStatus('pending'); setPage(1); setTab('review'); setRevision(value => value + 1);
    } catch (err) { setError(err.message); }
    finally { setBusy(false); }
  }
  const resourceKey = `${tab}:${revision}:${page}:${status}`;
  const result = resource?.key === resourceKey ? resource.data : null;
  useEffect(() => {
    const controller = new AbortController();
    const query = tab === 'audit' ? `?page=${page}` : tab === 'review' ? `?page=${page}&status=${status}` : '';
    api.request(sections[tab] + query, { signal: controller.signal }).then(data => {
      if (!controller.signal.aborted) { setResource({ key: resourceKey, data }); setError(''); }
    }).catch(err => {
      if (!controller.signal.aborted) setError(err.message);
    });
    return () => controller.abort();
  }, [tab, revision, page, status, resourceKey]);
  function open(kind, row) {
    setEditor({ kind, row }); setNote(''); setError('');
    let body = row;
    if (kind === 'source') body = row ? { ...row.config, key: row.key, enabled: row.enabled, interval_seconds: row.interval_seconds } : sourceExample;
    if (kind === 'review') body = row.payload;
    if (kind === 'event') {
      const { id, acquisition, ...fields } = row; // server-generated fields cannot be submitted
      void id; void acquisition; body = fields;
    }
    if (kind === 'organization') { const { id, ...fields } = row; void id; body = fields; }
    setText(JSON.stringify(body, null, 2));
  }
  async function mutate(path, body, method = 'PUT') {
    setBusy(true); setError(''); setMessage('');
    try { await api.request(path, { method, body }); setMessage('Change saved.'); setEditor(null); setRevision(value => value + 1); }
    catch (err) { setError(err.message); }
    finally { setBusy(false); }
  }
  function save(decision) {
    try {
      const kind = editor.kind;
      if (kind === 'review') {
        mutate(`/admin/discovery/announcements/${editor.row.id}/review`, {
          decision, note, ...(decision === 'approved' ? { event: JSON.parse(text) } : {}),
        }, 'POST');
      } else {
        const path = kind === 'source' ? '/admin/discovery/sources' : kind === 'event'
          ? `/events/${editor.row.id}` : `/organizations/${editor.row.id}`;
        mutate(path, JSON.parse(text));
      }
    } catch { setError('Enter valid JSON before saving.'); }
  }
  async function uploadDataset(event) {
    event.preventDefault(); setBusy(true); setError(''); setMessage('');
    try {
      if (!upload || !/\.(csv|xlsx)$/i.test(upload.name) || upload.size > 2000000 || !upload.size) throw new Error('Select a nonempty CSV or XLSX file up to 2 MB.');
      const bytes = new Uint8Array(await upload.arrayBuffer());
      let binary = '';
      for (let offset = 0; offset < bytes.length; offset += 8192) binary += String.fromCharCode(...bytes.subarray(offset, offset + 8192));
      const imported = await api.request('/admin/discovery/dataset-imports', { method: 'POST', body: {
        ...dataset, filename: upload.name, content_base64: btoa(binary),
      } });
      setMessage(`${imported.candidates_inserted} announcements staged for review; ${imported.candidate_duplicates} duplicates. No events published.`);
      setRevision(value => value + 1);
    } catch (err) { setError(err.message); }
    finally { setBusy(false); }
  }
  const rows = result?.data || [];
  return <section className="platform-panel" aria-label="Administration workspace">
    <h2>Operations workspace</h2>
    <section className="platform-card" aria-label="Verification and update actions">
      <h3>Verify &amp; update hackathons</h3>
      <p>Use <strong>Review</strong> to verify pending events, or <strong>Sources</strong> to stage the 206 unverified listings first. Listings shown on Explore are not automatically in this review queue.</p>
      <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
        <button type="button" className="platform-primary" onClick={() => { setTab('review'); setStatus('pending'); setPage(1); setRevision(value => value + 1); clearSelection(); setEditor(null); setMessage('Review queue updated.'); }}>Verify unverified listings</button>
        <button type="button" onClick={() => { setTab('sources'); setPage(1); setRevision(value => value + 1); setEditor(null); setMessage('Select an authorized source to stage archived listings.'); }}>Stage 206 listings</button>
        <button type="button" disabled={busy} onClick={() => { setRevision(value => value + 1); setMessage('Admin data updated.'); }}>Update / Refresh</button>
      </div>
    </section>
    <nav aria-label="Administration sections" style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
      {Object.keys(sections).map(key => <button key={key} aria-pressed={tab === key} onClick={() => { setTab(key); setPage(1); setEditor(null); setMessage(''); clearSelection(); }}>{key[0].toUpperCase() + key.slice(1)}</button>)}
    </nav>
    {message && <p role="status">{message}</p>}
    {error && <p role="alert">{error} <button onClick={() => setRevision(value => value + 1)}>Retry loading</button></p>}
    {!result && !error && <p role="status">Loading operationsâ€¦</p>}
    {tab === 'review' && <label>Review status <select value={status} onChange={e => { setStatus(e.target.value); setPage(1); clearSelection(); }}>{['pending', 'approved', 'rejected'].map(value => <option key={value}>{value}</option>)}</select></label>}
    {tab === 'sources' && <><p>Configuration saves do not start a discovery run. Enable only after recording current permission and expiry.</p><button onClick={() => open('source', null)}>Register source</button>
      <button type="button" onClick={() => {
        open('source', null);
        setText(JSON.stringify({ ...sourceExample, key: 'brabble-archive', name: 'Brabble.ai research archive',
          adapter: 'brabble-api-v1', url: 'https://brabble.ai/api/listings', interval_seconds: 21600,
          reference: 'https://brabble.ai/docs', enabled: false, terms_permit: false }, null, 2));
      }}>Prepare Brabble source policy</button>
      <form onSubmit={uploadDataset} className="platform-card" style={{ marginTop: 16 }}><h3>Import dataset</h3>
        <p>Upload CSV (UTF-8) or a single-sheet XLSX with unique field headers. Required headers: title, url. Optional: organization, start_date, end_date, registration_deadline, registration_url, description, eligibility, location, mode, prize, state. Maximum 2 MB and 1000 rows. Dates without an explicit timezone remain unverified for human review.</p>
        <label>Registered source<select required value={dataset.source_key} onChange={e => setDataset({ ...dataset, source_key: e.target.value })}><option value="">Select approved source</option>{rows.map(row => <option key={row.key} value={row.key}>{row.key} ({row.enabled ? 'enabled' : 'disabled'})</option>)}</select></label>
        {dataset.source_key && <p>Recorded reuse basis: {rows.find(row => row.key === dataset.source_key)?.config?.basis || 'Not recorded'}</p>}
        <label>Approval record reference<input required maxLength={500} value={dataset.approval_reference} placeholder="Exact reference from the current source approval" onChange={e => setDataset({ ...dataset, approval_reference: e.target.value })} /></label>
        <label>Dataset file<input required type="file" accept=".csv,.xlsx" onChange={e => setUpload(e.target.files?.[0] || null)} /></label>
        <p>Source must be enabled with current explicit reuse permission. Imports enter the review queue and do not publish events.</p>
        <button disabled={busy || !upload} type="submit">{busy ? 'Staging…' : 'Upload to review queue'}</button>
      </form>
      <section className="platform-card" style={{ marginTop: 18 }} aria-label="Stage archived hackathons">
        <h3>Stage the 206 Brabble listings for review</h3>
        <p>Select an enabled, permission-reviewed Brabble API source above, enter its exact approval reference, then stage the saved snapshot as pending records. This does not verify or publish them. The bulk approval tool appears in Review after staging.</p>
        <button type="button" disabled={busy || !dataset.source_key || !dataset.approval_reference.trim()} onClick={stageBrabbleArchive}>
          {busy ? 'Staging archive…' : 'Stage 206 listings into review queue'}
        </button>
        <p className="platform-muted">The original Brabble snapshot has no independently confirmed event start dates. You must supply verified dates and organizers for any event you approve.</p>
      </section></>}
    {result && tab === 'notifications' && <><p>Persisted delivery counts. This view does not send messages.</p><dl><dt>In-app notifications</dt><dd>{result.in_app_total}</dd><dt>Unread</dt><dd>{result.in_app_unread}</dd><dt>Email delivery records</dt><dd>{result.email_total}</dd>{Object.entries(result.email_by_status).map(([key, value]) => <div key={key}><dt>{key}</dt><dd>{value}</dd></div>)}</dl></>}
    {tab === 'review' && status === 'pending' && result && <section className="platform-card" aria-label="Bulk approval tools" style={{ marginTop: 16 }}>
      <h3>Bulk approval</h3>
      <p>Select pending announcements to verify and publish in one workflow. You can select up to {BULK_REVIEW_LIMIT} across pages. Every selected listing needs its own source check, verified start date and organizer.</p>
      <button type="button" disabled={busy || !rows.some(row => !selectedRows[row.id]) || Object.keys(selectedRows).length >= BULK_REVIEW_LIMIT} onClick={() => selectPageForReview(rows)}>Select this page (up to {BULK_REVIEW_LIMIT})</button>
      {Object.keys(selectedRows).length > 0 && <BulkReviewPanel selected={selectedRows} drafts={reviewDrafts}
        setDrafts={setReviewDrafts} onClear={clearSelection} onDone={bulkReviewCompleted} />}
    </section>}
    {result && tab !== 'notifications' && !rows.length && <p>No records in this section.</p>}
    {tab === 'review' && result && rows.length === 0 && <section className="platform-card" aria-label="Empty verification queue">
      <h3>No pending listings to verify</h3>
      <p>The 206 unverified Explore listings must first be staged into the backend review queue. Select <strong>Stage 206 listings</strong> above, configure a source with documented permission, then return here to verify them.</p>
      <button type="button" onClick={() => { setTab('sources'); setPage(1); setRevision(value => value + 1); }}>Go to Sources to stage listings</button>
    </section>}
    {tab === 'duplicates' && result && <p>Compared {result.scanned} events. {result.truncated ? 'This is a limited review window; more candidates may exist.' : 'All events in the scan window were compared.'} Verify both records before merging. The retained record keeps its identity.</p>}
    {rows.map(row => <article className="platform-card" key={row.id || row.key || `${row.survivor?.id}-${row.duplicate?.id}`} style={{ marginTop: 12 }}>
      <h3>{row.title || row.name || row.key || row.payload?.title || row.action || row.email || `Potential duplicate: ${row.survivor?.title}`}</h3>
      {tab === 'sources' && <><p>{row.enabled ? 'Enabled' : 'Disabled'} Â· every {row.interval_seconds} seconds</p><button onClick={() => open('source', row)}>Configure</button></>}
      {tab === 'review' && <>{row.status === 'pending' && <label style={{ display: 'flex', gap: 8 }}><input type="checkbox" aria-label={`Select ${row.payload?.title || row.id} for bulk review`} checked={!!selectedRows[row.id]} onChange={e => toggleReview(row, e.target.checked)} /> Select for bulk approval</label>}<p>{row.status} Â· observed {row.observed_at}</p><pre style={{ whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' }}>{JSON.stringify(row.evidence, null, 2)}</pre>{safeEventUrl(row.payload?.url) && <a href={safeEventUrl(row.payload.url)} target="_blank" rel="noreferrer">Open evidence page</a>}{row.status === 'pending' && <button className="platform-primary" type="button" onClick={() => open('review', row)}>Verify / Update &amp; Publish</button>}{row.review_note && <p>{row.review_note}</p>}</>}
      {tab === 'audit' && <><p>{row.created_at} Â· actor {row.actor_id || 'system'} Â· {row.entity_type}</p><pre style={{ whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' }}>{row.details}</pre></>}
      {tab === 'roles' && <><p>{row.email} Â· current role: {row.roles?.join(', ')}</p><label>Assign role <select aria-label={`Role for ${row.email}`} value={row.roles?.[0] || 'user'} disabled={busy} onChange={e => mutate(`/admin/users/${row.id}/role`, { role: e.target.value })}>{roles.map(role => <option key={role}>{role}</option>)}</select></label></>}
      {['events', 'organizations'].includes(tab) && <button onClick={() => open(tab === 'events' ? 'event' : 'organization', row)}>Edit {tab === 'events' ? 'event' : 'organization'}</button>}
      {tab === 'duplicates' && <><div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: 16 }}>{[['Retain', row.survivor], ['Merge into retained record', row.duplicate]].map(([label, record]) => <section key={record.id}><h4>{label}: #{record.id}</h4><p>{record.title}</p><dl><dt>Starts</dt><dd>{record.start_date || 'Unknown'}</dd><dt>Location</dt><dd>{record.location || 'Unknown'}</dd><dt>Organization ID</dt><dd>{record.organization_id || 'Unknown'}</dd><dt>Source</dt><dd>{record.source || 'Unknown'}</dd></dl>{safeEventUrl(record.url) && <a href={safeEventUrl(record.url)} target="_blank" rel="noreferrer">Inspect source</a>}<details><summary>All event facts</summary><pre style={{ whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' }}>{JSON.stringify(record, null, 2)}</pre></details></section>)}</div><pre style={{ whiteSpace: 'pre-wrap' }}>{JSON.stringify(row.evidence, null, 2)}</pre><button onClick={() => open('merge', row)}>Review merge</button></>}
    </article>)}
    {result && ['audit', 'review'].includes(tab) && <nav aria-label="Operations pages"><button disabled={page === 1} onClick={() => setPage(value => value - 1)}>Previous</button><span> Page {page} Â· {result.total} records </span><button disabled={page * 50 >= result.total} onClick={() => setPage(value => value + 1)}>Next</button></nav>}
    {editor?.kind === 'merge' && <section className="platform-card" aria-label="Confirm duplicate merge"><h3>Merge #{editor.row.duplicate.id} into #{editor.row.survivor.id}</h3><p>Confirm these are the same event edition. The retained event keeps its ID. Saved items and discovery history move to the retained event, and the duplicate record is removed.</p><label>Review rationale (at least 10 characters)<textarea value={note} maxLength={1000} onChange={e => setNote(e.target.value)} /></label><button disabled={busy || note.trim().length < 10} onClick={() => mutate('/admin/duplicates/merge', { survivor_id: editor.row.survivor.id, duplicate_id: editor.row.duplicate.id, review_token: editor.row.review_token, note }, 'POST')}>{busy ? 'Merging…' : 'Confirm merge and retain selected event'}</button><button disabled={busy} onClick={() => setEditor(null)}>Cancel</button></section>}
    {editor && editor.kind !== 'merge' && <section aria-label="Edit record" className="platform-card" style={{ marginTop: 16 }}><h3>{editor.kind === 'review' ? 'Verify announcement before publishing' : 'Edit record'}</h3>
      <p>{editor.kind === 'review' ? 'Confirm the event fields against the evidence. Provide the verified organization name and preserve explicitly verified timezones. Approval publishes the event.' : 'Enter validated fields as JSON. Source approval dates need explicit timezone offsets.'}</p>
      <label>Record fields<textarea aria-label="Record fields JSON" rows={18} style={{ width: '100%', fontFamily: 'monospace' }} value={text} onChange={e => setText(e.target.value)} /></label>
      {editor.kind === 'review' && <label>Review rationale (at least 10 characters)<textarea minLength={10} maxLength={2000} value={note} onChange={e => setNote(e.target.value)} /></label>}
      <button disabled={busy || (editor.kind === 'review' && note.trim().length < 10)} onClick={() => save('approved')}>{busy ? 'Savingâ€¦' : editor.kind === 'review' ? 'Approve and publish' : 'Save changes'}</button>
      {editor.kind === 'review' && <button disabled={busy || note.trim().length < 10} onClick={() => save('rejected')}>Reject announcement</button>}
      <button disabled={busy} onClick={() => setEditor(null)}>Cancel</button>
    </section>}
  </section>;
}
