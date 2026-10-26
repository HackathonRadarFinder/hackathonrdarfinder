"""Explainable deterministic matching of real catalog events to account facts."""
import re
from datetime import datetime, timezone
from sqlalchemy import select, or_
from app.models.core import Preference, SavedItem
from app.models.hackathon import Hackathon
from app.services.database import database_operation
from app.services.event_service import with_attribution

KEYS = ('preferred_location', 'preferred_mode', 'interests', 'in_app_reminders')


def get_preferences(db, user_id):
    with database_operation(db):
        stored = dict(db.execute(select(Preference.key, Preference.value).where(
            Preference.user_id == user_id, Preference.key.in_(KEYS))).all())
        return {**{key: stored.get(key) or '' for key in KEYS if key != 'in_app_reminders'}, 'in_app_reminders': stored.get('in_app_reminders', 'true') != 'false'}


def update_preferences(db, user_id, body):
    with database_operation(db, 'Preferences changed concurrently; reload and retry'):
        for key, value in body.model_dump().items():
            row = db.scalar(select(Preference).where(Preference.user_id == user_id, Preference.key == key))
            if row is None:
                row = Preference(user_id=user_id, key=key)
                db.add(row)
            row.value = str(value).lower() if isinstance(value, bool) else value
        db.commit()
        return body


def normalize(value):
    return ' '.join((value or '').casefold().split())


def recommendations(db, user_id, limit=12, now=None):
    now = now or datetime.now(timezone.utc)
    if now.tzinfo:
        now = now.astimezone(timezone.utc).replace(tzinfo=None)
    with database_operation(db):
        preferences = get_preferences(db, user_id)
        saved_query = select(SavedItem.hackathon_id).where(SavedItem.user_id == user_id)
        saved = db.scalars(select(Hackathon).where(Hackathon.id.in_(saved_query))).all()
        organizations = {row.organization_id for row in saved if row.organization_id}
        locations = {normalize(row.location) for row in saved if row.location}
        modes = {normalize(row.mode) for row in saved if row.mode}
        preferred_location = normalize(preferences['preferred_location'])
        preferred_mode = normalize(preferences['preferred_mode'])
        interests = sorted({normalize(value) for value in preferences['interests'].split(',') if normalize(value)})
        # A declared end time can establish that an already-started event is ongoing.
        # Without an end time we do not assume it is still running.
        eligible = db.scalars(select(Hackathon).where(Hackathon.start_date.is_not(None),
            or_(Hackathon.start_date >= now, Hackathon.end_date >= now),
            or_(Hackathon.end_date.is_(None), Hackathon.end_date >= Hackathon.start_date),
            Hackathon.id.not_in(saved_query)).order_by(Hackathon.start_date, Hackathon.id).limit(1001)).all()
        truncated = len(eligible) > 1000
        eligible = eligible[:1000]
        ranked = []
        for event in eligible:
            score, reasons = 0, []
            location, mode = normalize(event.location), normalize(event.mode)
            if preferred_location and preferred_location in location:
                score += 4; reasons.append('Matches your preferred location')
            if preferred_mode and preferred_mode == mode:
                score += 3; reasons.append('Matches your preferred mode')
            tokens = set(re.findall(r'\w+', normalize(f'{event.title} {event.description or ""} {event.eligibility or ""}')))
            matched = [interest for interest in interests if set(re.findall(r'\w+', interest)).issubset(tokens) and re.search(r'\w', interest)]
            if matched:
                score += min(len(matched), 3) * 2
                reasons.append('Matches your interests: ' + ', '.join(matched))
            if event.organization_id in organizations:
                score += 3; reasons.append('Same organizer as an event you saved')
            if location and location in locations:
                score += 1; reasons.append('Same location as an event you saved')
            if mode and mode in modes:
                score += 1; reasons.append('Same mode as an event you saved')
            if score:
                ranked.append((score, event, reasons))
        ranked.sort(key=lambda row: (-row[0], row[1].start_date, row[1].id))
        chosen = ranked[:limit]
        with_attribution(db, [row[1] for row in chosen])
        return {'data': [dict(event=event, reasons=reasons, relevance_score=score) for score, event, reasons in chosen],
            'method': 'deterministic_preference_matching', 'scanned': len(eligible), 'truncated': truncated,
            'message': 'Matches use your saved events and stated preferences; scores are not probabilities'}
