"""Audited human verification, under the existing durable discovery writer lock."""
from datetime import datetime, timezone
import json
import uuid
from fastapi import HTTPException
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from app.models.core import AuditLog, EventVersion
from app.models.discovery import DiscoveryRun, DiscoveryLock, DiscoverySource, DiscoveryEvent
from app.models.institution import Announcement, Institution
from app.schemas.event import EventCreate
from app.schemas.discovery import SourcePolicy
from app.schemas.institution import public_https
from app.services.discovery_service import ingest_discovery, policy_reason


def review(db, candidate_id, body, actor):
    now = datetime.now(timezone.utc)
    # Serializes publication on SQLite before reading mutable review state.
    connection = db.connection()
    if connection.dialect.name == 'sqlite' and not connection.connection.driver_connection.in_transaction:
        connection.exec_driver_sql('BEGIN IMMEDIATE')
    candidate = db.scalar(select(Announcement).where(Announcement.id == candidate_id).with_for_update())
    if candidate is None:
        raise HTTPException(404, 'Announcement not found')
    if candidate.status != 'pending':
        raise HTTPException(409, 'Announcement already reviewed')
    if body.decision == 'approved':
        source = db.get(DiscoverySource, candidate.source_id)
        policy = SourcePolicy.model_validate(source.config)
        if (not source.enabled or policy_reason(policy, now, True)
                or policy.adapter != candidate.evidence['adapter_version']
                or policy.url != candidate.evidence['document_url']
                or policy.institution_id != candidate.institution_id):
            raise HTTPException(409, 'Source approval is not currently valid')
        newer = db.scalar(select(Announcement.id).where(Announcement.source_id == candidate.source_id,
            Announcement.payload['url'].as_string() == candidate.payload.get('url'),
            Announcement.observed_at > candidate.observed_at).limit(1))
        if newer:
            raise HTTPException(409, 'A newer observation requires review')
        item = body.event
        if item is None or not item.title or not item.start_date or not item.organization or not item.url:
            raise HTTPException(422, 'Verified title, organizer, source URL and event start with timezone are required')
        # Immutable collection provenance; reviewers can correct event facts, not invent observations.
        original_url = candidate.payload.get('url')
        if str(item.url) != original_url or item.institution_id != candidate.institution_id:
            raise HTTPException(422, 'Keep the observed URL and institution identity')
        public_https(str(item.url))
        if item.registration_url:
            public_https(str(item.registration_url))
        if candidate.institution_id:
            institution = db.get(Institution, candidate.institution_id)
            if item.state != institution.state:
                raise HTTPException(422, 'State must match verified institution directory')
        item = EventCreate.model_validate({**item.model_dump(), 'source': source.key,
            'scraped_at': candidate.observed_at})
        run = DiscoveryRun(id=uuid.uuid4(), source_id=source.source_id, started_at=now.replace(tzinfo=None),
            finished_at=now.replace(tzinfo=None), status='success', metrics={'operation': 'review_publication'})
        db.add(run); db.flush()
        try:
            db.add(DiscoveryLock(id=1, run_id=run.id)); db.flush()
        except IntegrityError:
            db.rollback()
            raise HTTPException(409, 'Discovery writer is busy') from None
        outcome = ingest_discovery(db, source, run, [item], candidate.evidence, candidate.observed_at)
        if outcome['conflicts']:
            db.rollback()
            raise HTTPException(409, 'Event identity or observation conflicts with existing history')
        candidate.hackathon_id = db.scalar(select(DiscoveryEvent.hackathon_id).where(
            DiscoveryEvent.source_id == source.source_id, DiscoveryEvent.canonical_url == str(item.url)))
        if candidate.evidence.get('acquisition'):
            version = db.scalar(select(EventVersion).where(EventVersion.hackathon_id == candidate.hackathon_id).order_by(EventVersion.version_number.desc()).limit(1))
            if version.changes.get('run_id') == str(run.id):
                version.changes = {**version.changes, 'acquisition': candidate.evidence['acquisition']}
            else:
                db.add(EventVersion(hackathon_id=candidate.hackathon_id, version_number=version.version_number + 1,
                    title=version.title, description=version.description, snapshot=version.snapshot,
                    changes={'fields': [], 'acquisition': candidate.evidence['acquisition'], 'run_id': str(run.id)},
                    created_at=now.replace(tzinfo=None)))
        db.execute(delete(DiscoveryLock).where(DiscoveryLock.id == 1, DiscoveryLock.run_id == run.id))
    candidate.status = body.decision
    candidate.reviewer_id = uuid.UUID(actor.sub)
    candidate.reviewed_at = now.replace(tzinfo=None)
    candidate.review_note = body.note
    db.add(AuditLog(user_id=uuid.UUID(actor.sub), action='announcement_reviewed', entity_type='announcement',
        entity_id=candidate.id, details=json.dumps({'decision': body.decision, 'note': body.note})))
    db.commit()
    return dict(id=candidate.id, status=candidate.status, event_id=candidate.hackathon_id)
