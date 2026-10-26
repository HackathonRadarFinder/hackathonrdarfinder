from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
import pytest
from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import Session
from app.core.database import Base
from app.models.core import User, SavedItem, Notification, Preference
from app.models.hackathon import Hackathon
from app.models.organization import Organization
from app.services.personalized import recommendations, update_preferences, get_preferences
from app.api.routes.personalized import DiscoveryPreferences
from app.services.in_app_reminders import enqueue_in_app


@pytest.fixture
def context():
    engine = create_engine('sqlite://')
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        user = User(name='Test account', email='preferences@example.com', password_hash='test-only')
        other = User(name='Other account', email='other@example.com', password_hash='test-only')
        org = Organization(name='Fixture organizers')
        db.add_all([user, other, org]); db.flush()
        now = datetime(2026, 10, 26, 12, tzinfo=timezone.utc)
        events = [Hackathon(title=title, organization_id=org.id, start_date=(now + timedelta(hours=hours)).replace(tzinfo=None), mode='Online', location='Delhi', description=description)
            for title, hours, description in [('Saved AI event', 3, ''), ('Relevant AI event', 6, ''), ('Past AI event', -24, ''), ('Date-only event', 8, 'Date precision: day')]]
        db.add_all(events); db.flush()
        db.add(SavedItem(user_id=user.id, hackathon_id=events[0].id)); db.commit()
        yield db, user, other, events, now
    engine.dispose()


def test_personalization_uses_private_preferences_and_excludes_saved_and_past(context):
    db, user, other, events, now = context
    update_preferences(db, user.id, DiscoveryPreferences(interests='AI', preferred_location='Delhi', in_app_reminders=False))
    assert get_preferences(db, user.id)['in_app_reminders'] is False
    assert get_preferences(db, other.id)['interests'] == ''
    result = recommendations(db, user.id, now=now)
    assert [row['event'].id for row in result['data']] == [events[1].id, events[3].id]
    assert result['data'][0]['reasons'] and result['method'] == 'deterministic_preference_matching'
    assert recommendations(db, other.id, now=now)['data'] == []


def test_scheduled_in_app_notices_are_idempotent_and_respect_opt_out(context):
    db, user, other, events, now = context
    assert enqueue_in_app(db, now)['inserted'] == 1
    assert enqueue_in_app(db, now)['inserted'] == 0
    notice = db.scalar(select(Notification))
    assert notice.user_id == user.id and not notice.is_read
    db.add(SavedItem(user_id=user.id, hackathon_id=events[3].id)); db.commit()
    assert enqueue_in_app(db, now)['inserted'] == 0
    db.add(SavedItem(user_id=other.id, hackathon_id=events[0].id))
    db.add(Preference(user_id=other.id, key='in_app_reminders', value='false')); db.commit()
    assert enqueue_in_app(db, now)['inserted'] == 0
    assert db.scalar(select(func.count()).select_from(Notification)) == 1
    with pytest.raises(ValueError):
        enqueue_in_app(db, now.replace(tzinfo=None))
