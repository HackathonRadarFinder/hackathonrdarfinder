/** A single Explore grid: verified catalog entries first, followed by attributed API listings.
 * The client never promotes archived provider data to verified database events.
 */
export function excludesUnverifiedListings(filters) {
  return Boolean(filters.state?.trim() || filters.institutionId || filters.organizationId ||
    filters.startFrom || filters.startTo || filters.deadlineFrom || filters.deadlineTo || filters.period);
}

export function filterUnverifiedListings(records, filters) {
  if (excludesUnverifiedListings(filters)) return [];
  const query = (filters.q || '').trim().toLowerCase();
  const location = (filters.location || '').trim().toLowerCase();
  const mode = (filters.mode || '').trim().toLowerCase();
  const filtered = records.filter(item => {
    const text = [item.title, item.organization, item.location].filter(Boolean).join(' ').toLowerCase();
    return (!query || text.includes(query)) &&
      (!location || (item.location || '').toLowerCase().includes(location)) &&
      (!mode || (item.mode || '').toLowerCase().includes(mode));
  });
  // The source supplies no confirmed start dates. Keep verified entries first
  // and sort unverified records only within their own part of the feed.
  if (filters.sort === 'title') return filtered.sort((a, b) => a.title.localeCompare(b.title));
  if (filters.sort === 'deadline') return filtered.sort((a, b) =>
    (a.reported_deadline || '9999').localeCompare(b.reported_deadline || '9999'));
  return filtered;
}

export function composeExplorePage(verifiedResult, unverifiedRecords, page, pageSize) {
  const verifiedTotal = verifiedResult?.total || 0;
  const offset = (page - 1) * pageSize;
  const catalog = offset < verifiedTotal ? verifiedResult?.data || [] : [];
  const additionalOffset = Math.max(0, offset - verifiedTotal);
  const additionalSlots = Math.max(0, pageSize - catalog.length);
  const unverified = unverifiedRecords.slice(additionalOffset, additionalOffset + additionalSlots);
  return {
    total: verifiedTotal + unverifiedRecords.length,
    totalPages: Math.max(1, Math.ceil((verifiedTotal + unverifiedRecords.length) / pageSize)),
    entries: [
      ...catalog.map(event => ({ key: `verified-${event.id}`, type: 'verified', event })),
      ...unverified.map(item => ({ key: `unverified-${item.id}`, type: 'unverified', item })),
    ],
    unverifiedTotal: unverifiedRecords.length,
  };
}
