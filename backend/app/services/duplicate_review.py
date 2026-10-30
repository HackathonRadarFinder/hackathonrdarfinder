"""Conservative, explicitly reviewed catalog merges; never collect or auto-publish."""
from datetime import datetime, timezone
from difflib import SequenceMatcher
import hashlib
import json
import re
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

from sqlalchemy import func, select
from app.core.database import Base
from app.models.hackathon import Hackathon
from app.models.core import AuditLog, EventVersion, Prediction, SavedItem
from app.models.discovery import DiscoveryEvent, DiscoveryEvidence
from app.models.institution import Announcement
from app.models.email_delivery import EmailDelivery


class MergeConflict(ValueError):
    pass


def _alias_url(url):
    if not url:
        return None
    try:
        parsed = urlsplit(str(url).strip())
        if parsed.scheme.lower() not in {'http', 'https'} or not parsed.hostname or parsed.username or parsed.password:
            return None
        port = parsed.port
        host = parsed.hostname.lower()
        if port and (parsed.scheme.lower(), port) not in {('http', 80), ('https', 443)}:
            host += f':{port}'
        query = sorted((k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=True)
                       if not k.lower().startswith('utm_') and k.lower() not in {'fbclid', 'gclid'})
        return urlunsplit((parsed.scheme.lower(), host, parsed.path.rstrip('/') or '/', urlencode(query), ''))
    except ValueError:
        return None


def merged_alias_id(db, url):
    """Resolve only administrator-merged URLs, using durable preserved snapshots.

    Reparented versions naturally carry aliases through subsequent merges. Never
    choose arbitrarily if conflicting surviving rows claim the same former URL.
    """
    normalized = _alias_url(url)
    if normalized is None:
        return None
    aliases = set()
    versions = db.scalars(select(EventVersion).where(
        EventVersion.changes['action'].as_string() == 'duplicate_merge_before'))
    for version in versions:
        old = version.snapshot
        if (isinstance(old, dict) and old.get('id') != version.hackathon_id
                and _alias_url(old.get('url')) == normalized):
            if db.get(Hackathon, version.hackathon_id) is None:
                raise MergeConflict('Merged URL references a missing survivor; manual review required')
            aliases.add(version.hackathon_id)
    if not aliases:
        return None
    for row in db.scalars(select(Hackathon)):
        if _alias_url(row.url) == normalized:
            aliases.add(row.id)
    if len(aliases) != 1:
        raise MergeConflict('Conflicting merged URL aliases require manual review')
    return next(iter(aliases))


def snapshot(row):
    return {column.name: (value.isoformat() if isinstance(value, datetime) else value)
            for column in Hackathon.__table__.columns
            for value in [getattr(row, column.name)]}


def review_token(a, b):
    payload = sorted([snapshot(a), snapshot(b)], key=lambda item: item['id'])
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def normalize(value):
    return ' '.join(re.findall(r'\w+', (value or '').casefold()))


def match_reason(a, b):
    if a.id == b.id or not a.start_date or not b.start_date:
        return None
    if a.start_date.year != b.start_date.year or abs((a.start_date.date() - b.start_date.date()).days) > 2:
        return None
    years_a, years_b = set(re.findall(r'\b(?:19|20)\d{2}\b', a.title)), set(re.findall(r'\b(?:19|20)\d{2}\b', b.title))
    if years_a and years_b and years_a != years_b:
        return None
    org_a = normalize(a.organization.name if a.organization else '')
    org_b = normalize(b.organization.name if b.organization else '')
    if not org_a or not org_b or org_a != org_b:
        return None
    location_a, location_b = normalize(a.location), normalize(b.location)
    aliases = {'virtual': 'online', 'bangalore': 'bengaluru', 'delhi': 'new delhi'}
    if not location_a or not location_b or aliases.get(location_a, location_a) != aliases.get(location_b, location_b):
        return None
    if a.institution_id and b.institution_id and a.institution_id != b.institution_id:
        return None
    if a.state and b.state and normalize(a.state) != normalize(b.state):
        return None
    if a.mode and b.mode and normalize(a.mode) != normalize(b.mode):
        return None
    titles = [' '.join(sorted(normalize(x.title).split())) for x in (a, b)]
    score = SequenceMatcher(None, *titles).ratio()
    # Shared generic event words alone are insufficient evidence.
    generic = {'hackathon', 'event', 'annual', 'the', 'and', 'online', 'national'}
    informative = [{word for word in t.split() if not word.isdigit()} - generic for t in titles]
    if score < .80 or not informative[0].intersection(informative[1]):
        return None
    return {'title_similarity': round(score, 3), 'date_difference_days': abs((a.start_date.date() - b.start_date.date()).days),
            'organizer': org_a, 'location': location_a, 'requires_review': True}


def candidate_pairs(db, limit=100, scan_limit=1000):
    rows = db.scalars(select(Hackathon).where(Hackathon.start_date.is_not(None))
        .order_by(Hackathon.start_date, Hackathon.id).limit(scan_limit + 1)).all()
    truncated = len(rows) > scan_limit
    rows = rows[:scan_limit]
    pairs = []
    for i, a in enumerate(rows):
        for b in rows[i + 1:]:
            if (b.start_date.date() - a.start_date.date()).days > 2:
                break
            reason = match_reason(a, b)
            if reason:
                pairs.append({'survivor': snapshot(a), 'duplicate': snapshot(b),
                              'evidence': reason, 'review_token': review_token(a, b)})
                if len(pairs) >= limit:
                    return {'data': pairs, 'truncated': True, 'scanned': len(rows)}
    return {'data': pairs, 'truncated': truncated, 'scanned': len(rows)}


def merge_reviewed(db, survivor_id, duplicate_id, token, actor_id, note):
    """Caller owns commit/rollback. PostgreSQL locks serialize opposing merges."""
    if survivor_id == duplicate_id:
        raise MergeConflict('Select two distinct events')
    locked = db.scalars(select(Hackathon).where(Hackathon.id.in_([survivor_id, duplicate_id]))
        .order_by(Hackathon.id).with_for_update()).all()
    by_id = {row.id: row for row in locked}
    if len(by_id) != 2:
        raise MergeConflict('An event no longer exists; refresh the review')
    keep, remove = by_id[survivor_id], by_id[duplicate_id]
    if review_token(keep, remove) != token:
        raise MergeConflict('Event details changed; refresh the review')
    if not match_reason(keep, remove):
        raise MergeConflict('Events lack sufficient same-edition evidence')
    merged_start = keep.start_date or remove.start_date
    merged_end = keep.end_date or remove.end_date
    if merged_start and merged_end and merged_end < merged_start:
        raise MergeConflict('Selected metadata would end before the event starts')
    supported = {model.__tablename__ for model in (EventVersion, Prediction, SavedItem, DiscoveryEvent,
                 DiscoveryEvidence, Announcement, EmailDelivery)}
    for table in Base.metadata.tables.values():
        if any(fk.target_fullname == 'hackathons.id' for fk in table.foreign_keys) and table.name not in supported:
            raise MergeConflict('An unsupported event relationship requires manual migration')
    # Delivery records are evidence. Reject collisions rather than discard or resend them.
    keep_deliveries = {(r.user_id, r.kind, r.event_at) for r in db.scalars(select(EmailDelivery).where(EmailDelivery.hackathon_id == keep.id))}
    if any((r.user_id, r.kind, r.event_at) in keep_deliveries for r in db.scalars(select(EmailDelivery).where(EmailDelivery.hackathon_id == remove.id))):
        raise MergeConflict('Overlapping email delivery history requires manual review')
    now = datetime.now(timezone.utc)
    before = [snapshot(keep), snapshot(remove)]
    version = db.scalar(select(func.max(EventVersion.version_number)).where(EventVersion.hackathon_id == keep.id)) or 0
    # Original versions remain immutable snapshots; retain their former identity in changes.
    for historical in db.scalars(select(EventVersion).where(EventVersion.hackathon_id == remove.id).order_by(EventVersion.version_number, EventVersion.id)):
        version += 1
        historical.changes = dict(historical.changes or {}, merged_from_event_id=remove.id,
                                  original_version_number=historical.version_number)
        historical.hackathon_id, historical.version_number = keep.id, version
    for original in before:
        version += 1
        db.add(EventVersion(hackathon_id=keep.id, version_number=version, snapshot=original,
            changes={'action': 'duplicate_merge_before', 'original_event_id': original['id']}, created_at=now))
    preserved = []
    keep_saves = {r.user_id: r for r in db.scalars(select(SavedItem).where(SavedItem.hackathon_id == keep.id))}
    for saved in db.scalars(select(SavedItem).where(SavedItem.hackathon_id == remove.id)):
        if saved.user_id in keep_saves:
            preserved.append({'saved_id': str(saved.id), 'user_id': str(saved.user_id),
                              'created_at': saved.created_at.isoformat() if saved.created_at else None})
            existing = keep_saves[saved.user_id]
            if saved.created_at and existing.created_at and saved.created_at < existing.created_at:
                existing.created_at = saved.created_at
            db.delete(saved)
        else:
            saved.hackathon_id = keep.id
    for model in (DiscoveryEvent, DiscoveryEvidence, Announcement, Prediction, EmailDelivery):
        for related in db.scalars(select(model).where(model.hackathon_id == remove.id)):
            related.hackathon_id = keep.id
    # Keep reviewer-selected values, filling only absent facts; snapshots retain conflicts.
    for column in Hackathon.__table__.columns:
        if column.name != 'id' and not getattr(keep, column.name) and getattr(remove, column.name):
            setattr(keep, column.name, getattr(remove, column.name))
    version += 1
    db.add(EventVersion(hackathon_id=keep.id, version_number=version, snapshot=snapshot(keep),
        changes={'action': 'duplicate_merge', 'merged_event_id': remove.id}, created_at=now))
    db.add(AuditLog(user_id=actor_id, action='duplicate_events_merged', entity_type='hackathon',
        details=json.dumps({'survivor_id': keep.id, 'duplicate_id': remove.id, 'note': note,
                            'before': before, 'coalesced_saved_items': preserved}, sort_keys=True)))
    db.flush()  # Reparent every FK before deleting the redundant public catalog row.
    db.delete(remove)
    db.flush()
    return {'survivor_id': keep.id, 'merged_event_id': duplicate_id, 'version': version}
