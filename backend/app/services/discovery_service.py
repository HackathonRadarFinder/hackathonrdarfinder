"""Policy-gated discovery; one durable writer, atomic snapshots, no implicit fetch."""
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import sys
import uuid

from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from app.models.core import Source, EventVersion
from app.models.discovery import DiscoverySource, DiscoveryRun, DiscoveryLock, DiscoveryEvent, DiscoveryEvidence
from app.models.hackathon import Hackathon
from app.models.organization import Organization
from app.schemas.discovery import SourcePolicy
from app.services.scraper_ingestion import normalize_unstop_collection
from workers.ingest_curated import validate_records
from app.services.duplicate_review import merged_alias_id, MergeConflict

BACKEND = Path(__file__).resolve().parents[2]
MATERIAL_FIELDS = ('title', 'organization_id', 'start_date', 'end_date', 'registration_deadline',
                   'location', 'mode', 'prize', 'description', 'url', 'source',
                   'state', 'institution_id', 'registration_url', 'eligibility')


def utc(value):
    if value.tzinfo is None:
        raise ValueError('Worker clock requires UTC-aware timestamps')
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def register_source(db, policy, now, *, commit=True):
    """Protected callers supply reviewed policy; registration never fetches."""
    policy = SourcePolicy.model_validate(policy)
    institution = None
    if policy.adapter not in ('curated-v1', 'unstop-v1') and policy.institution_id is not None:
        from app.models.institution import Institution
        institution = db.get(Institution, policy.institution_id)
        if institution is None or not institution.website_verified_at or policy.url not in institution.event_urls:
            raise ValueError('Source must be an explicitly verified institution event URL')
    row = db.scalar(select(DiscoverySource).where(DiscoverySource.key == policy.key))
    if row is None:
        source = Source(name=policy.name, url=policy.url)
        db.add(source); db.flush()
        row = DiscoverySource(source_id=source.id, key=policy.key, next_run_at=utc(now))
        db.add(row)
    else:
        source = db.get(Source, row.source_id)
        source.name, source.url = policy.name, policy.url
    config = policy.model_dump(mode='json')
    if row.config != config:
        row.next_run_at = utc(now)
    row.config = config
    row.enabled, row.interval_seconds = policy.enabled, policy.interval_seconds
    if institution is not None:
        institution.permission_status = 'approved' if not policy_reason(policy, now, True) else 'awaiting_permission'
    if commit:
        db.commit()
    return row


def curated_policy(now, *, enabled=False):
    return SourcePolicy(key='curated-mvp', name='Reviewed MVP snapshot', adapter='curated-v1',
        url='curated://mvp-20261013', enabled=enabled, owner='Local manifest reviewer',
        basis='Offline reuse of the existing operator-reviewed factual snapshot; no scraping',
        reference='backend/data/curated-mvp-20261013.json', reviewed_at=now,
        expires_at=now + timedelta(days=30), terms_permit=False)


def policy_reason(policy, now, allow_live):
    if not policy.enabled:
        return 'source_disabled'
    if policy.reviewed_at > now or policy.expires_at <= now:
        return 'approval_expired_or_future'
    if policy.adapter not in {'curated-v1', 'unstop-v1', 'official-html-v1', 'events-json-v1', 'rss-v1', 'sitemap-v1'}:
        return 'unsupported_adapter'
    if policy.adapter != 'curated-v1':
        if not policy.terms_permit:
            return 'permission_missing'
        if not allow_live:
            return 'live_collection_disabled'
    return None


def collect_source(policy):
    if policy.adapter == 'curated-v1':
        raw = (BACKEND / 'data' / 'curated-mvp-20261013.json').read_text(encoding='utf-8')
        return validate_records(json.loads(raw)), 0, {'checksum': hashlib.sha256(raw.encode()).hexdigest(),
            'document_url': policy.url, 'adapter_version': policy.adapter, 'transport': 'offline'}
    if policy.adapter not in {'curated-v1', 'unstop-v1', 'official-html-v1', 'events-json-v1', 'rss-v1', 'sitemap-v1'}:
        raise ValueError('unsupported_adapter')
    if policy.adapter not in ('curated-v1', 'unstop-v1'):
        from app.services.nationwide_collection import collect_announcements
        return collect_announcements(policy)
    # Use the existing governed collector: robots, terms, redirects, DNS/IP gates,
    # bounded transfer, retries and atomic raw storage. Never use standalone fetch.
    sys.path.insert(0, str(BACKEND / 'modules' / '2.2-collector' / 'src'))
    from collector_engine.config.loader import Settings
    from collector_engine.manager import CollectorManager
    from collector_engine.models import Source as CollectorSource
    from collector_engine.storage.local_storage import LocalRawStorage
    settings = Settings.from_env()
    settings.alert_webhook_url = ''  # No unrelated outbound notification transport.
    manager = CollectorManager(settings, LocalRawStorage(settings.raw_data_dir))
    result = manager.collect(CollectorSource(source_id=policy.key, url=policy.url,
        type='static', tos_allows_scraping=True, tos_note=policy.basis))
    if result.status != 'success' or not result.robots_allowed:
        raise ValueError('collection_denied_or_failed')
    if 'json' not in result.content_type.lower():
        raise ValueError('unsupported_content_type')
    normalized = normalize_unstop_collection(result.handoff_dict())
    return normalized.events, normalized.rejected, {
        'checksum': hashlib.sha256(result.raw_content.encode()).hexdigest(),
        'document_url': policy.url, 'adapter_version': policy.adapter,
        'http_status': result.http_status, 'attempts': result.attempts,
        'content_type': result.content_type, 'storage_location': result.storage_location,
        'policy_decision': 'terms_and_robots_allowed', 'transport': 'governed-http'}


def snapshot(event):
    values = {key: getattr(event, key) for key in (*MATERIAL_FIELDS, 'scraped_at')}
    return {key: value.isoformat() if isinstance(value, datetime) else value for key, value in values.items()}


def ingest_discovery(db, source, run, records, metadata, observed):
    """Called only under the global discovery lock. Caller commits all-or-nothing."""
    counts = {'inserted': 0, 'updated': 0, 'unchanged': 0, 'conflicts': 0}
    seen = set()
    for incoming in records:
        url = str(incoming.url)
        if url in seen:
            counts['unchanged'] += 1
            continue
        seen.add(url)
        alias_id = merged_alias_id(db, url)
        if alias_id is not None:
            retained = db.get(Hackathon, alias_id)
            if retained.start_date and incoming.start_date and retained.start_date.year != incoming.start_date.year:
                counts['conflicts'] += 1
                continue
            identity = db.scalar(select(DiscoveryEvent).where(
                DiscoveryEvent.source_id == source.source_id, DiscoveryEvent.canonical_url == url))
            if identity is not None and identity.hackathon_id != alias_id:
                raise MergeConflict('Discovery identity conflicts with reviewed merged URL')
            if identity is None:
                identity = DiscoveryEvent(source_id=source.source_id, canonical_url=url,
                    hackathon_id=alias_id, last_observed_at=observed)
                db.add(identity)
            identity.last_observed_at = observed
            db.add(DiscoveryEvidence(hackathon_id=alias_id, source_id=source.source_id,
                run_id=run.id, observed_at=observed, checksum=metadata['checksum'],
                document_url=metadata['document_url'], adapter_version=metadata['adapter_version'],
                snapshot=incoming.model_dump(mode='json')))
            counts['unchanged'] += 1
            continue
        identity = db.scalar(select(DiscoveryEvent).where(
            DiscoveryEvent.source_id == source.source_id, DiscoveryEvent.canonical_url == url))
        record = db.get(Hackathon, identity.hackathon_id) if identity else db.scalar(
            select(Hackathon).where(Hackathon.url == url).order_by(Hackathon.id).limit(1))
        # A reused annual landing URL is not evidence that two editions are one event.
        if (record is not None and record.start_date and incoming.start_date
                and record.start_date.year != incoming.start_date.year):
            counts['conflicts'] += 1
            continue
        # Do not overwrite another source's or manually administered event.
        if record is not None and record.source != incoming.source:
            counts['conflicts'] += 1
            continue
        if record is not None and record.scraped_at and incoming.scraped_at < record.scraped_at:
            counts['conflicts'] += 1
            continue
        org = db.scalar(select(Organization).where(Organization.name == incoming.organization))
        if org is None:
            org = Organization(name=incoming.organization); db.add(org); db.flush()
        values = incoming.model_dump(exclude={'organization', 'organization_id'})
        values.update(url=url, organization_id=org.id,
            registration_url=str(incoming.registration_url) if incoming.registration_url else None)
        before = snapshot(record) if record else None
        if record is None:
            record = Hackathon(**values); db.add(record); db.flush()
            counts['inserted'] += 1
        changed = list(MATERIAL_FIELDS) if before is None else [key for key in MATERIAL_FIELDS
            if before[key] != (values[key].isoformat() if isinstance(values.get(key), datetime) else values.get(key))]
        if before is not None:
            if changed:
                for key, value in values.items():
                    setattr(record, key, value)
                counts['updated'] += 1
            else:
                record.scraped_at = incoming.scraped_at
                counts['unchanged'] += 1
        if identity is None:
            identity = DiscoveryEvent(source_id=source.source_id, canonical_url=url,
                hackathon_id=record.id, last_observed_at=observed)
            db.add(identity)
        identity.last_observed_at = observed
        after = snapshot(record)
        # Adopt legacy matching records with an initial snapshot; never rewrite history.
        version = db.scalar(select(func.max(EventVersion.version_number)).where(EventVersion.hackathon_id == record.id))
        if changed or version is None:
            db.add(EventVersion(hackathon_id=record.id, version_number=(version or 0) + 1,
                title=record.title, description=(record.description or '')[:1000],
                snapshot=after, changes={'fields': changed, 'before': before,
                    'source_id': str(source.source_id), 'run_id': str(run.id)}, created_at=observed))
        db.add(DiscoveryEvidence(hackathon_id=record.id, source_id=source.source_id,
            run_id=run.id, observed_at=observed, checksum=metadata['checksum'],
            document_url=metadata['document_url'], adapter_version=metadata['adapter_version'], snapshot=after))
    db.flush()
    return counts


def run_source(db, key, now, *, allow_live=False, collector=None):
    """One-shot due run. A crash leaves a durable lock requiring operator review."""
    current = utc(now)
    connection = db.connection()
    if connection.dialect.name == 'sqlite' and not connection.connection.driver_connection.in_transaction:
        connection.exec_driver_sql('BEGIN IMMEDIATE')
    source = db.scalar(select(DiscoverySource).where(DiscoverySource.key == key))
    if source is None or not source.enabled or source.next_run_at > current:
        db.rollback()
        return {'status': 'not_due'}
    original = dict(source.config)
    run = DiscoveryRun(id=uuid.uuid4(), source_id=source.source_id, started_at=current, status='running', metrics={})
    db.add(run); db.flush()
    try:
        db.add(DiscoveryLock(id=1, run_id=run.id)); db.flush()
    except IntegrityError:
        db.rollback()
        return {'status': 'busy'}
    source.next_run_at = current + timedelta(seconds=source.interval_seconds)
    db.commit()
    status, error, metrics = 'failed', 'validation_or_collection_failed', {}
    try:
        policy = SourcePolicy.model_validate(original)
        reason = policy_reason(policy, now, allow_live)
        if reason:
            status, error = 'paused', reason
            if reason != 'live_collection_disabled':
                source.enabled = False
            db.commit()
        else:
            records, rejected, metadata = (collector or collect_source)(policy)
            # Adapters must return validated input. Revalidate the whole batch.
            from app.schemas.event import EventCreate
            if len(records) > 1000:
                raise ValueError('batch_too_large')
            records = [EventCreate.model_validate(item.model_dump() if isinstance(item, EventCreate) else item) for item in records]
            if any(not item.organization or not item.url or not item.source or not item.scraped_at for item in records):
                raise ValueError('provenance_missing')
            db.expire_all()
            source = db.get(DiscoverySource, run.source_id)
            if not source.enabled or source.config != original:
                raise ValueError('policy_changed_during_collection')
            observed = max(current, utc(datetime.now(timezone.utc)))
            if policy_reason(policy, observed.replace(tzinfo=timezone.utc), allow_live):
                raise ValueError('approval_expired_during_collection')
            if policy.adapter not in ('curated-v1', 'unstop-v1'):
                from app.services.nationwide_collection import stage_announcements
                if records:
                    raise ValueError('New adapters must stage announcements for review')
                candidate_counts = stage_announcements(db, source, metadata.pop('announcements'), metadata, observed)
            else:
                candidate_counts = {}
            metrics = {**candidate_counts, **ingest_discovery(db, source, run, records, metadata, observed),
                       'rejected': rejected, **metadata}
            status, error = 'success', None
    except Exception:
        db.rollback()  # Do not publish partial batches or leak SQL/raw content.
    run = db.get(DiscoveryRun, run.id)
    run.status, run.error_code, run.metrics = status, error, metrics
    run.finished_at = max(current, utc(datetime.now(timezone.utc)))
    db.execute(delete(DiscoveryLock).where(DiscoveryLock.id == 1, DiscoveryLock.run_id == run.id))
    db.commit()
    return {'status': status, 'error_code': error, **metrics}


def run_due(db, now, *, allow_live=False, limit=10):
    keys = db.scalars(select(DiscoverySource.key).where(DiscoverySource.enabled,
        DiscoverySource.next_run_at <= utc(now)).order_by(DiscoverySource.key).limit(limit)).all()
    db.rollback()
    return {key: run_source(db, key, now, allow_live=allow_live) for key in keys}
