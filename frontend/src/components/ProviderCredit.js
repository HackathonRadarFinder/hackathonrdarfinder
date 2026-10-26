import { createElement as h } from 'react';

// Used on both catalog cards and event details. Fixed provider origin prevents
// an API-supplied attribution link from becoming an executable/external redirect.
export default function ProviderCredit({ acquisition }) {
  if (acquisition?.provider !== 'Brabble.ai' || acquisition.method !== 'brabble_api') return null;
  const match = /^https:\/\/brabble\.ai\/s\/[a-zA-Z0-9-]+$/.test(acquisition.provider_url || '');
  return h('aside', { className: 'platform-provider-credit', 'aria-label': 'Data attribution' },
    h('p', null, 'Data provided by ', h('a', {
      href: match ? acquisition.provider_url : 'https://brabble.ai',
      target: '_blank', rel: 'noopener noreferrer',
    }, 'Brabble.ai'), ` via its API · Original platform: ${acquisition.original_platform || 'Not provided'}`),
    h('p', null, 'Prize labels and registration counts are provider-supplied and may be incomplete. Verify details on the original platform.'),
    h('small', null, `Acquired: ${acquisition.acquired_at || 'Not provided'} · Source refreshed: ${acquisition.source_refreshed_at || 'Not provided'}`));
}
