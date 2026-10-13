"""Runtime integration check; refuses databases without a disposable name."""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from app.core.database import engine, SessionLocal
from app.main import app
from app.models.core import Role, User, Notification
from app.models.hackathon import Hackathon
from app.models.organization import Organization
from app.services import notification_service

assert engine.dialect.name == 'postgresql'
assert engine.url.database.startswith('mvp_disposable_')
with SessionLocal() as db:
    assert db.scalar(text('SELECT version_num FROM alembic_version')) == 'd9e0f1a2b3c4'
    org = Organization(name='Disposable test organizer')
    db.add(org); db.flush()
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    event = Hackathon(title='DISPOSABLE TEST ONLY', organization_id=org.id,
                     start_date=now + timedelta(hours=12), url='https://example.org/test')
    db.add(event); db.commit(); event_id = event.id
with TestClient(app) as client:
    for email in ('one@example.org', 'two@example.org'):
        assert client.post('/auth/register', json={'name':'Disposable', 'email':email,
                           'password':'DisposableTestPassword123'}).status_code == 201
    tokens = [client.post('/auth/login', json={'email':email, 'password':'DisposableTestPassword123'}).json()['access_token']
              for email in ('one@example.org','two@example.org')]
    one, two = [{'Authorization':f'Bearer {token}'} for token in tokens]
    assert client.put(f'/account/saved/{event_id}', headers=one).status_code == 200
    assert client.get('/account/saved', headers=two).json()['data'] == []
    assert client.put('/account/preferences', headers=one, json={'email_reminders':True}).status_code == 200
    assert client.get('/admin/stats', headers=one).status_code == 403
    with SessionLocal() as db:
        assert notification_service.enqueue_due(db, datetime.now(timezone.utc)) == 1
        assert notification_service.enqueue_due(db, datetime.now(timezone.utc)) == 0
        with patch.object(notification_service, 'render_message', return_value=object()), \
             patch.object(notification_service, 'send_message', return_value='accepted') as sender:
            assert notification_service.dispatch_due(db, SimpleNamespace(EMAIL_MODE='enabled'),
                datetime.now(timezone.utc)) == {'accepted':1}
            assert notification_service.dispatch_due(db, SimpleNamespace(EMAIL_MODE='enabled'),
                datetime.now(timezone.utc)) == {}
            assert sender.call_count == 1
        assert len(db.scalars(select(Notification)).all()) == 1
        user = db.scalar(select(User).where(User.email == 'two@example.org'))
        role = Role(name='administrator'); db.add(role); user.roles.append(role); db.commit()
    # Existing token's regular role claim cannot grant admin; DB profile governs.
    stats = client.get('/admin/stats', headers=two)
    assert stats.status_code == 200 and stats.json()['total_events'] == 1
    assert client.post('/auth/logout', headers=one).status_code == 200
    assert client.get('/auth/me', headers=one).status_code == 401
print('Disposable PostgreSQL 16 migrations, ownership, roles, persistent notices, consent, dedup, mocked SMTP and revocation: PASS')
