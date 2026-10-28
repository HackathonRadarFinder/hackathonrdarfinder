"""Authorized API snapshots -> pending review, never direct publication."""
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import uuid

from app.services.brabble_adapter import normalize
from pydantic import HttpUrl
from workers.refresh_brabble import collect_api


def collect_brabble(policy):
    directory = Path(os.environ.get('COLLECTOR_SNAPSHOT_DIR', '/app/collector-data')) / uuid.uuid4().hex
    outcome = collect_api(directory, os.environ.get('BRABBLE_API_KEY', ''))
    raw = (directory / 'response_envelopes.json').read_bytes()
    candidates, rejected = [], 0
    for envelope in json.loads(raw):
        for row in envelope['response']['listings']:
            try:
                normalized = normalize(row, {'acquired_at': envelope['acquired_at'],
                    'source_refreshed_at': envelope['response']['refreshedAt']})
                fields = ('title', 'organization', 'url', 'start_date', 'end_date',
                          'registration_deadline', 'location', 'mode', 'prize', 'description')
                payload = {key: (normalized[key].isoformat() if isinstance(normalized[key], datetime)
                                else normalized[key] or None) for key in fields}
                payload['url'] = str(HttpUrl(payload['url']))
                payload['_acquisition'] = normalized['acquisition_evidence']
                payload['_issues'] = normalized['issues'].split('; ')
                candidates.append(payload)
            except (ValueError, TypeError, KeyError):
                rejected += 1
    return [], rejected, {'checksum': hashlib.sha256(raw).hexdigest(), 'document_url': policy.url,
        'adapter_version': policy.adapter, 'transport': 'authorized-brabble-api',
        'storage_location': str(directory), 'requests': outcome['requests'],
        'records_collected': outcome['records'], 'announcements': candidates}
