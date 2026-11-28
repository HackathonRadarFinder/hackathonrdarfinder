import { useEffect, useRef, useState } from 'react';
import { api, safeEventUrl } from '../services/apiClient';

const ISSUE_TYPES = [
  { value: 'inaccurate', label: 'Information is inaccurate' },
  { value: 'outdated', label: 'Information is outdated' },
  { value: 'broken_link', label: 'Link is broken' },
  { value: 'other', label: 'Other' },
];
const EMPTY = { issueType: '', description: '', suggestedCorrection: '', evidenceUrl: '' };

export default function ReportIssueModal({ open, onClose, listingType = 'hackathon', listingId, listingName }) {
  const [form, setForm] = useState(EMPTY);
  const [errors, setErrors] = useState({});
  const [busy, setBusy] = useState(false);
  const [submitError, setSubmitError] = useState('');
  const [done, setDone] = useState(false);
  const dialogRef = useRef(null);

  useEffect(() => {
    if (!open) return;
    setForm(EMPTY); setErrors({}); setSubmitError(''); setDone(false);
    dialogRef.current?.focus();
    const onKey = event => { if (event.key === 'Escape') onClose(); };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [open, onClose]);

  if (!open) return null;

  function validate() {
    const next = {};
    if (!form.issueType) next.issueType = 'Please choose the type of problem.';
    const description = form.description.trim();
    if (description.length < 10) next.description = 'Please describe the problem (at least 10 characters).';
    else if (description.length > 1000) next.description = 'Description must be 1000 characters or fewer.';
    if (form.suggestedCorrection.length > 1000) next.suggestedCorrection = 'Correction must be 1000 characters or fewer.';
    if (form.evidenceUrl.trim() && !safeEventUrl(form.evidenceUrl.trim())) next.evidenceUrl = 'Enter a valid http(s) link, or leave this empty.';
    setErrors(next);
    return Object.keys(next).length === 0;
  }

  async function submit(event) {
    event.preventDefault();
    setSubmitError('');
    if (!validate()) return;
    setBusy(true);
    try {
      await api.reportListing({
        listing_type: listingType,
        listing_id: listingId,
        issue_type: form.issueType,
        description: form.description.trim(),
        suggested_correction: form.suggestedCorrection.trim() || null,
        evidence_url: form.evidenceUrl.trim() || null,
      });
      setDone(true);
    } catch (error) {
      setSubmitError(error.message || 'Could not submit the report.');
    } finally {
      setBusy(false);
    }
  }

  const overlay = { position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000, padding: '1rem' };
  const box = { background: '#fff', color: '#111', borderRadius: 12, padding: '1.5rem', width: '100%', maxWidth: 520, maxHeight: '90vh', overflowY: 'auto' };
  const fieldError = { color: '#b00020', fontSize: '0.85rem', margin: '0.25rem 0 0.75rem' };

  return <div style={overlay} onMouseDown={event => { if (event.target === event.currentTarget) onClose(); }}>
    <div ref={dialogRef} tabIndex={-1} role="dialog" aria-modal="true" aria-labelledby="report-title" style={box}>
      <h2 id="report-title">Report inaccurate or outdated listing</h2>
      {listingName && <p><strong>{listingName}</strong></p>}
      {done ? <>
        <p role="status">Thank you. Your report was submitted and will be reviewed.</p>
        <button type="button" onClick={onClose}>Close</button>
      </> : <form onSubmit={submit} noValidate>
        <label>What is wrong?
          <select value={form.issueType} onChange={event => setForm({ ...form, issueType: event.target.value })} aria-invalid={!!errors.issueType}>
            <option value="">Select a problem</option>
            {ISSUE_TYPES.map(item => <option key={item.value} value={item.value}>{item.label}</option>)}
          </select>
        </label>
        {errors.issueType && <p role="alert" style={fieldError}>{errors.issueType}</p>}
        <label>Describe the problem
          <textarea rows={4} maxLength={1000} value={form.description} onChange={event => setForm({ ...form, description: event.target.value })} aria-invalid={!!errors.description} />
        </label>
        {errors.description && <p role="alert" style={fieldError}>{errors.description}</p>}
        <label>Correct information (optional)
          <textarea rows={3} maxLength={1000} value={form.suggestedCorrection} onChange={event => setForm({ ...form, suggestedCorrection: event.target.value })} />
        </label>
        {errors.suggestedCorrection && <p role="alert" style={fieldError}>{errors.suggestedCorrection}</p>}
        <label>Proof link (optional)
          <input type="url" maxLength={500} placeholder="https://..." value={form.evidenceUrl} onChange={event => setForm({ ...form, evidenceUrl: event.target.value })} aria-invalid={!!errors.evidenceUrl} />
        </label>
        {errors.evidenceUrl && <p role="alert" style={fieldError}>{errors.evidenceUrl}</p>}
        {submitError && <p role="alert" style={fieldError}>{submitError}</p>}
        <div style={{ display: 'flex', gap: '0.5rem', marginTop: '1rem' }}>
          <button type="submit" disabled={busy}>{busy ? 'Submitting...' : 'Submit report'}</button>
          <button type="button" onClick={onClose} disabled={busy}>Cancel</button>
        </div>
      </form>}
    </div>
  </div>;
}