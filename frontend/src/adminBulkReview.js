/** Offline archive staging and review preflight; final authorization lives on the backend. */
export const BULK_REVIEW_LIMIT = 25;

const verifiedDate = value => typeof value === 'string' &&
  /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:\d{2})$/.test(value) &&
  !Number.isNaN(Date.parse(value));

export function checkCandidateReview(candidate, event, evidenceChecked) {
  const issues = [];
  if (!evidenceChecked) issues.push('Confirm evidence against the original event page');
  if (!event || typeof event !== 'object' || Array.isArray(event)) return ['Enter a valid event object'];
  if (typeof event.title !== 'string' || !event.title.trim()) issues.push('Verified title required');
  if (typeof event.organization !== 'string' || !event.organization.trim() || /^(see listing|unknown|n\/a)$/i.test(event.organization.trim())) issues.push('Verified organizer required');
  if (!event.url || event.url !== candidate?.payload?.url) issues.push('Keep the original source URL');
  if (event.institution_id !== (candidate?.institution_id ?? null) &&
      !(event.institution_id == null && candidate?.institution_id == null)) issues.push('Keep the original institution identity');
  if (!verifiedDate(event.start_date)) issues.push('Verified event start date with timezone required (not registration deadline)');
  for (const field of ['end_date', 'registration_deadline']) {
    if (event[field] && !verifiedDate(event[field])) issues.push(field + ' requires a verified timezone');
  }
  if (event.start_date && event.end_date && verifiedDate(event.start_date) && verifiedDate(event.end_date) &&
      Date.parse(event.end_date) < Date.parse(event.start_date)) issues.push('End date must follow start date');
  return issues;
}

function csvCell(value) {
  return '"' + String(value ?? '').replace(/"/g, '""') + '"';
}

export function prepareBrabbleArchiveCsv(snapshot) {
  if (snapshot?.schema_version !== 1 || snapshot.review_state !== 'unverified' ||
      snapshot.record_count !== 206 || !Array.isArray(snapshot.records) || snapshot.records.length !== 206) {
    throw new Error('Unexpected Brabble archive snapshot; no dataset staged');
  }
  const ids = new Set();
  const fields = ['title', 'organization', 'url', 'description'];
  const rows = [fields.map(csvCell).join(',')];
  for (const row of snapshot.records) {
    if (!row.id || ids.has(row.id) || !row.title || !row.url ||
        !['Unstop', 'Devfolio'].includes(row.source) || !/^https:\/\//.test(row.url) ||
        !/^https:\/\/brabble\.ai\/s\//.test(row.provider_url)) {
      throw new Error('Archive has an invalid or duplicated source record');
    }
    ids.add(row.id);
    const description = 'Data provided by Brabble.ai API (snapshot 25 October 2026). Original platform: ' +
      row.source + '. Unverified provider reports: deadline ' + (row.reported_deadline || 'not known') +
      ', city ' + (row.location || 'not known') + ', mode ' + (row.mode || 'not known') +
      '. All facts require independent review before publication.';
    rows.push(fields.map(field => csvCell(field === 'description' ? description : row[field])).join(','));
  }
  if (ids.size !== 206 || snapshot.records.filter(x => x.source === 'Unstop').length !== 195) {
    throw new Error('Brabble source counts did not match the preserved snapshot');
  }
  return rows.join('\r\n') + '\r\n';
}

export function encodeCsvToBase64(csv) {
  const bytes = new TextEncoder().encode(csv);
  let binary = '';
  for (let i = 0; i < bytes.length; i += 8192) {
    binary += String.fromCharCode(...bytes.subarray(i, i + 8192));
  }
  return btoa(binary);
}
