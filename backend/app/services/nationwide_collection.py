"""Governed static adapters and revision-aware staging; no implicit publication."""
from collections import OrderedDict
from datetime import datetime, timezone
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import sys
import time
from sqlalchemy import select
from app.models.institution import Institution, Announcement
from app.services.announcement_extraction import extract

_cache = OrderedDict()


@lru_cache(maxsize=1)
def manager():
    # One manager per worker: rate limits and robots cache survive source changes.
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'modules' / '2.2-collector' / 'src'))
    from collector_engine.config.loader import Settings
    from collector_engine.manager import CollectorManager
    from collector_engine.storage.local_storage import LocalRawStorage
    settings = Settings.from_env()
    settings.alert_webhook_url = ''
    settings.max_response_bytes = min(settings.max_response_bytes, 2_000_000)
    return CollectorManager(settings, LocalRawStorage(settings.raw_data_dir))


def collect_announcements(policy):
    collector = manager()
    from collector_engine.models import Source
    key = (policy.url, policy.basis, policy.reference)
    cached = _cache.get(key)
    if cached and time.monotonic() - cached[0] < 300:
        result = cached[1]
        hit = True
    else:
        result = collector.collect(Source(source_id=policy.key, url=policy.url, type='static',
            tos_allows_scraping=True, tos_note=policy.basis))
        if result.status != 'success' or not result.robots_allowed:
            raise ValueError('collection_denied_or_failed')
        _cache[key] = (time.monotonic(), result)
        _cache.move_to_end(key)
        while len(_cache) > 16:
            _cache.popitem(last=False)
        hit = False
    content_type = result.content_type.lower()
    expected = {'official-html-v1': ('html',), 'events-json-v1': ('json',),
                'rss-v1': ('xml', 'rss', 'atom'), 'sitemap-v1': ('xml',)}[policy.adapter]
    if not any(value in content_type for value in expected):
        raise ValueError('unsupported_content_type')
    rows = extract(result.raw_content, policy.adapter, result.final_url or policy.url)
    return [], 0, dict(checksum=hashlib.sha256(result.raw_content.encode()).hexdigest(),
        document_url=policy.url, adapter_version=policy.adapter, transport='governed-http',
        fetched_at=result.fetched_at, cache_hit=hit, announcements=rows)


def stage_announcements(db, source, rows, metadata, observed):
    if len(rows) > 1000:
        raise ValueError('batch_too_large')
    institution = db.get(Institution, source.config.get('institution_id')) if source.config.get('institution_id') else None
    counts = dict(candidates_inserted=0, candidate_duplicates=0)
    for extracted in rows:
        item = dict(extracted)
        issues = list(item.pop('_issues', []))
        dates = item.pop('_raw_dates', {})
        item.update(source=source.key, scraped_at=observed.isoformat())
        if institution:
            # Directory identity is operator-verified. Conflicting page geography is reviewed explicitly.
            if item.get('state') and item['state'] != institution.state:
                issues.append('page_directory_state_conflict')
            item.update(institution_id=institution.id)
            item.setdefault('state', institution.state)
            if not item.get('state'):
                item['state'] = institution.state
            if not item.get('organization'):
                item['organization'] = institution.name
        stable = {key: value for key, value in item.items() if key != 'scraped_at'}
        fingerprint = hashlib.sha256(json.dumps(dict(payload=stable, dates=dates, issues=issues), sort_keys=True).encode()).hexdigest()
        existing = db.scalar(select(Announcement).where(Announcement.source_id == source.source_id,
            Announcement.fingerprint == fingerprint))
        if existing:
            existing.last_seen_at = observed
            counts['candidate_duplicates'] += 1
            continue
        db.add(Announcement(source_id=source.source_id, institution_id=institution.id if institution else None,
            fingerprint=fingerprint, payload=item, observed_at=observed, last_seen_at=observed,
            status='pending', evidence=dict(checksum=metadata['checksum'], document_url=metadata['document_url'],
                adapter_version=metadata['adapter_version'], fetched_at=metadata.get('fetched_at'),
                issues=issues, raw_dates=dates)))
        counts['candidates_inserted'] += 1
    db.flush()
    return counts
