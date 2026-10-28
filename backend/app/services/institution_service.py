"""Incremental, atomic directory imports and coverage metrics."""
import hashlib
import json
from datetime import datetime, timezone
from sqlalchemy import func, select, or_
from app.models.institution import Institution, Announcement
from app.models.discovery import DiscoverySource, DiscoveryRun
from app.schemas.institution import DirectoryImport


def import_directory(db, body):
    body = DirectoryImport.model_validate(body)
    connection = db.connection()
    if connection.dialect.name == 'sqlite' and not connection.connection.driver_connection.in_transaction:
        connection.exec_driver_sql('BEGIN IMMEDIATE')
    counts = dict(inserted=0, updated=0, unchanged=0, stale=0)
    existing = {row.identifier: row for row in db.scalars(select(Institution).where(
        Institution.identifier.in_([item.identifier for item in body.records])).with_for_update())}
    sources = None
    for item in body.records:
        values = item.model_dump(mode='json')
        checksum = hashlib.sha256(json.dumps(values, sort_keys=True).encode()).hexdigest()
        row = existing.get(item.identifier)
        verified = item.verified_at.astimezone(timezone.utc).replace(tzinfo=None)
        if row and row.last_verified_at > verified:
            counts['stale'] += 1
            continue
        if row and row.provenance.get('checksum') == checksum:
            counts['unchanged'] += 1
            continue
        if row and row.last_verified_at == verified:
            raise ValueError('Conflicting directory facts at the same verification time')
        if row is None:
            row = Institution(identifier=item.identifier, permission_status='awaiting_permission')
            db.add(row)
            counts['inserted'] += 1
        else:
            counts['updated'] += 1
            # Changed identity or verified URLs must not retain collection approval.
            if sources is None:
                sources = db.scalars(select(DiscoverySource)).all()
            for source in sources:
                if source.config.get('institution_id') == row.id:
                    source.enabled = False
            row.permission_status = 'awaiting_permission'
        for key in ('name', 'state', 'district', 'city', 'category', 'website', 'event_urls'):
            setattr(row, key, getattr(item, key))
        row.website_verified_at = item.website_verified_at.astimezone(timezone.utc).replace(tzinfo=None) if item.website_verified_at else None
        row.last_verified_at = verified
        row.provenance = dict(provider=body.provider, source_url=body.source_url,
            license_reference=body.license_reference, reviewed_by=body.reviewed_by,
            website_evidence_url=item.website_evidence_url, checksum=checksum)
    db.flush()
    return counts


def coverage(db):
    now = datetime.now(timezone.utc)
    sources = db.scalars(select(DiscoverySource)).all()
    approved = []
    from app.schemas.discovery import SourcePolicy
    from app.services.discovery_service import policy_reason
    for row in sources:
        policy = SourcePolicy.model_validate(row.config)
        if row.enabled and policy.adapter != 'curated-v1' and not policy_reason(policy, now, True):
            approved.append(row)
    total = lambda model: db.scalar(select(func.count()).select_from(model))
    collected = or_(DiscoveryRun.metrics['operation'].as_string().is_(None),
                    DiscoveryRun.metrics['operation'].as_string() != 'review_publication')
    successful = select(DiscoveryRun.source_id).where(DiscoveryRun.status == 'success', collected).distinct().subquery()
    last = db.scalar(select(func.max(DiscoveryRun.finished_at)).where(DiscoveryRun.status == 'success', collected))
    live_successful = db.scalar(select(func.count()).select_from(successful).where(
        successful.c.source_id.in_([row.source_id for row in sources if row.config.get('adapter') != 'curated-v1'])))
    statuses = dict(db.execute(select(Announcement.status, func.count()).group_by(Announcement.status)).all())
    duplicates = 0
    for metrics in db.scalars(select(DiscoveryRun.metrics)):
        duplicates += int(metrics.get('unchanged', 0)) + int(metrics.get('candidate_duplicates', 0))
    return dict(institutions_indexed=total(Institution),
        institutions_with_verified_websites=db.scalar(select(func.count()).select_from(Institution).where(Institution.website_verified_at.is_not(None))),
        approved_sources=len(approved),
        institutions_with_approved_sources=len({row.config.get('institution_id') for row in approved if row.config.get('institution_id')}),
        sources_successfully_checked=live_successful,
        events_discovered=total(Announcement), validated_events=statuses.get('approved', 0),
        pending_review=statuses.get('pending', 0), rejected_events=statuses.get('rejected', 0),
        duplicate_records=duplicates,
        failed_collections=db.scalar(select(func.count()).select_from(DiscoveryRun).where(DiscoveryRun.status == 'failed')),
        sources_awaiting_permission=sum(not row.config.get('terms_permit', False) for row in sources if row.config.get('adapter') != 'curated-v1'),
        last_successful_collection=last,
        institutions_by_state=dict(db.execute(select(Institution.state, func.count()).group_by(Institution.state)).all()),
        note='Institution coverage and source checks do not imply hackathon coverage; discoveries count announcement revisions.')


def verified_event_coverage(db):
    """Only explicit, human-reviewed publication links count as verified coverage."""
    from app.models.hackathon import Hackathon
    from datetime import datetime, timezone
    linked = select(Hackathon.institution_id).join(Announcement,
        (Announcement.hackathon_id == Hackathon.id) & (Announcement.institution_id == Hackathon.institution_id)
    ).where(Announcement.status == 'approved', Hackathon.institution_id.is_not(None))
    upcoming = linked.where(func.coalesce(Hackathon.end_date, Hackathon.start_date) >= datetime.now(timezone.utc).replace(tzinfo=None))
    return dict(total_universities=db.scalar(select(func.count()).select_from(Institution)),
        universities_with_verified_hackathons=db.scalar(select(func.count()).select_from(linked.distinct().subquery())),
        universities_with_upcoming_verified_hackathons=db.scalar(select(func.count()).select_from(upcoming.distinct().subquery())))
