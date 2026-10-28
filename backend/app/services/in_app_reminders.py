"""Saved-event notices only; deterministic IDs prevent duplicate notices."""
from datetime import timedelta
import uuid
from sqlalchemy import select, exists, func
from sqlalchemy.exc import IntegrityError
from app.models.core import Notification, Preference, SavedItem, User
from app.models.hackathon import Hackathon
from app.services.notification_service import utc, KINDS


def enqueue_in_app(db, now, batch_size=100):
    current = utc(now)
    if not 1 <= batch_size <= 1000 or db.new or db.dirty or db.deleted:
        raise ValueError('Use a clean worker session and batch size 1..1000')
    inserted = scanned = 0
    for kind, field in KINDS.items():
        column = getattr(Hackathon, field)
        opted_out = exists(select(Preference.id).where(Preference.user_id == User.id,
            Preference.key == 'in_app_reminders', Preference.value == 'false'))
        rows = db.execute(select(User.id, Hackathon.id, Hackathon.title, column).select_from(SavedItem)
            .join(User, User.id == SavedItem.user_id).join(Hackathon, Hackathon.id == SavedItem.hackathon_id)
            .where(User.status == 'active', ~opted_out, column > current,
                column <= current + timedelta(hours=24),
                ~func.coalesce(Hackathon.description, '').contains('Date precision: day'))
            .order_by(column, Hackathon.id, User.id).limit(10000)).all()
        for user_id, event_id, title, event_at in rows:
            scanned += 1
            identity = uuid.uuid5(uuid.NAMESPACE_URL, f'radar:reminder:{user_id}:{event_id}:{kind}:{event_at.isoformat()}')
            if db.get(Notification, identity) is not None:
                continue
            try:
                with db.begin_nested():
                    db.add(Notification(id=identity, user_id=user_id,
                        title='Registration deadline reminder' if kind == 'registration' else 'Upcoming saved event',
                        message=f'{title} ({kind}): {event_at.isoformat()} UTC. Check the organizer for updates.'))
                    db.flush()
                inserted += 1
            except IntegrityError:
                pass
            if inserted >= batch_size:
                db.commit()
                return {'inserted': inserted, 'scanned': scanned, 'batch_full': True}
    db.commit()
    return {'inserted': inserted, 'scanned': scanned, 'batch_full': False}
