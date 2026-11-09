import { useMemo, useState } from 'react';
import { api, safeEventUrl } from './services/apiClient';
import { BULK_REVIEW_LIMIT, checkCandidateReview } from './adminBulkReview';

export default function BulkReviewPanel({ selected, drafts, setDrafts, onDone, onClear }) {
  const [note, setNote] = useState('');
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState('');
  const records = Object.values(selected);
  const validated = useMemo(() => records.map(candidate => {
    const draft = drafts[candidate.id] || {};
    let event = null;
    try { event = JSON.parse(draft.json || '{}'); } catch { /* Not submitted */ }
    const issues = checkCandidateReview(candidate, event, !!draft.evidenceChecked);
    return { candidate, event, issues };
  }), [records, drafts]);
  const invalid = validated.filter(row => row.issues.length);
  async function submit() {
    if (busy || !validated.length || invalid.length || note.trim().length < 10) return;
    setBusy(true);
    const approved = [];
    let error = null;
    try {
      for (const row of validated) {
        try {
          setProgress(`Publishing ${approved.length + 1}/${validated.length}: ${row.candidate.payload.title}`);
          await api.request(`/admin/discovery/announcements/${row.candidate.id}/review`, {
            method: 'POST',
            body: { decision: 'approved', note: note.trim(), event: row.event },
          });
          approved.push(row.candidate.id);
        } catch (failure) {
          error = `Stopped at ${row.candidate.payload.title}: ${failure.message}. Remaining entries were not submitted.`;
          break;
        }
      }
      onDone({ approved, error });
      setProgress(approved.length ? `${approved.length} verified announcement(s) published.` : 'Nothing published.');
      if (approved.length === validated.length) setNote('');
    } finally {
      setBusy(false);
    }
  }
  return <section className="platform-card" aria-label="Bulk verified announcement approval" style={{ marginTop: 18 }}>
    <h3>Bulk approve selected — {records.length} of {BULK_REVIEW_LIMIT} maximum</h3>
    <p>Approve several independently checked announcements together. Each record is checked again by the backend for source permission, verified start dates, identity conflicts and review status. This action publishes real events; it is not an unverified-label toggle.</p>
    <p>Review each original event page and correct its JSON below. <strong>Do not copy a registration deadline into the event start date.</strong> Unknown dates must remain pending.</p>
    <button type="button" disabled={busy} onClick={onClear}>Clear selection</button>
    {validated.map(({ candidate, issues }) => <details key={candidate.id} className="platform-card" style={{ marginTop: 10 }} open={issues.length > 0 ? true : undefined}>
      <summary>{candidate.payload?.title} — {issues.length ? `${issues.length} checks remaining` : 'Ready for backend review'}</summary>
      <p>{safeEventUrl(candidate.payload?.url) && <a href={safeEventUrl(candidate.payload.url)} target="_blank" rel="noopener noreferrer">Check original announcement</a>}</p>
      <p style={{ fontSize: 13 }}>Detected issues: {candidate.evidence?.issues?.join(', ') || 'None recorded'}.</p>
      <label>Verified event fields (JSON)
        <textarea aria-label={`Verified JSON for ${candidate.payload?.title}`} rows={9} style={{ width: '100%', fontFamily: 'monospace' }}
          value={drafts[candidate.id]?.json || ''} onChange={e => setDrafts(prev => ({ ...prev, [candidate.id]: { ...prev[candidate.id], json: e.target.value, evidenceChecked: false } }))} />
      </label>
      <label><input type="checkbox" checked={!!drafts[candidate.id]?.evidenceChecked}
        onChange={e => setDrafts(prev => ({ ...prev, [candidate.id]: { ...prev[candidate.id], evidenceChecked: e.target.checked } }))} /> I personally checked this listing's title, organizer, event start date and original URL against the organizer or official source.</label>
      {issues.length > 0 && <p role="status">{issues.join('; ')}</p>}
    </details>)}
    <label>Shared review rationale (at least 10 characters)
      <textarea maxLength={2000} value={note} onChange={e => setNote(e.target.value)} placeholder="Describe the independent source checks performed for each selected event." />
    </label>
    {invalid.length > 0 && <p role="status">{invalid.length} of {records.length} selected records still need verification. No incomplete records will be published.</p>}
    <button type="button" className="platform-primary" disabled={busy || !!invalid.length || !records.length || note.trim().length < 10} onClick={submit}>
      {busy ? 'Approving checked records…' : `Bulk approve & publish ${records.length} verified records`}
    </button>
    {progress && <p role="status">{progress}</p>}
    <p className="platform-muted">Approvals are sent sequentially to the existing audited backend endpoint. If one fails, previous successes remain published and remaining records stay pending. No blanket approval is possible without per-record evidence confirmation.</p>
  </section>;
}
