"""Disposable account journey, ownership and database-driven predictions."""
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.database import Base, get_db
from app.core.security import create_access_token
from app.main import app
from app.models.core import User, SavedItem, Preference, Role
from app.models.hackathon import Hackathon
from app.models.organization import Organization
from app.services.notification_service import enqueue_due


@pytest.fixture
def journey(tmp_path):
    engine = create_engine(f"sqlite:///{(tmp_path / 'journey.db').as_posix()}",
                           connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        users = [User(name=name, email=f"{name}@example.com", password_hash="test") for name in ("one", "two")]
        org = Organization(name="Historical organizer")
        db.add_all([*users, org]); db.flush()
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        events = [Hackathon(title="Literal %_ Search", organization_id=org.id,
                    start_date=now + timedelta(hours=12), registration_deadline=now + timedelta(hours=6),
                    url="https://example.com/event")]
        events += [Hackathon(title="Past", organization_id=org.id, start_date=now - timedelta(days=days))
                   for days in (1095, 730, 365)]
        db.add_all(events); db.commit()
        headers = [{"Authorization": f"Bearer {create_access_token(subject=str(user.id), role='user')}"} for user in users]
        event_id = events[0].id
    def override():
        with Session(engine) as db:
            yield db
    app.dependency_overrides[get_db] = override
    with TestClient(app) as client:
        yield client, headers, event_id, engine
    app.dependency_overrides.clear(); engine.dispose()


def test_account_ownership_consent_and_worker_queue(journey):
    client, (one, two), event_id, engine = journey
    assert client.get('/account/saved').status_code == 401
    assert client.get('/account/preferences', headers=one).json()['email_reminders'] is False
    for _ in range(2):
        assert client.put(f'/account/saved/{event_id}', headers=one).status_code == 200
    assert len(client.get('/account/saved', headers=one).json()['data']) == 1
    assert client.get('/account/saved', headers=two).json()['data'] == []
    assert client.delete(f'/account/saved/{event_id}', headers=two).status_code == 200
    with Session(engine) as db:
        assert len(db.scalars(select(SavedItem)).all()) == 1
        assert enqueue_due(db, datetime.now(timezone.utc)) == 0
    values = {'email_reminders': True, 'email_registration_reminders': True, 'email_upcoming_reminders': False}
    assert client.put('/account/preferences', headers=one, json=values).json() == values
    assert client.get('/account/preferences', headers=two).json()['email_reminders'] is False
    with Session(engine) as db:
        assert enqueue_due(db, datetime.now(timezone.utc)) == 1
        assert enqueue_due(db, datetime.now(timezone.utc)) == 0
        assert len(db.scalars(select(Preference)).all()) == 3
    assert client.put('/account/preferences', headers=one, json={'email_reminders': 'true'}).status_code == 422
    assert client.put('/account/preferences', headers=one, json={**values, 'user_id': 'other'}).status_code == 422
    assert client.put('/account/saved/2147483647', headers=one).status_code == 404
    assert client.delete(f'/account/saved/{event_id}', headers=one).status_code == 200
    assert client.get('/account/saved', headers=one).json()['data'] == []


def evaluation_header(journey):
    _, (one, _), _, engine = journey
    with Session(engine) as db:
        user = db.scalar(select(User).where(User.name == 'one'))
        user.roles.append(Role(name='data_scientist'))
        db.commit()
    return one


def test_literal_search_and_future_catalog_forecast(journey):
    client, _, _, _ = journey
    page = client.get('/events/', params={'q': '%_', 'page': 1}).json()
    assert page['total'] == 1
    assert page['data'][0]['title'] == 'Literal %_ Search'
    assert client.get('/events/', params={'q': "' OR 1=1"}).json()['total'] == 0
    assert client.get('/predictions/catalog').json()['data'] == []
    forecast = client.get('/predictions/evaluation', headers=evaluation_header(journey)).json()['data'][0]
    assert forecast['historical_events'] == 3  # future scheduled event excluded
    assert forecast['confidence_kind'] == 'heuristic'
    assert forecast['confirmed'] is False
    assert len(forecast['evidence']) == 3
    assert all(item['title'] == 'Past' for item in forecast['evidence'])
    assert forecast['confidence'] == 0.65
    assert forecast['predicted_date'] is None
    assert forecast['window']['start'] < forecast['window']['end']
    assert forecast['suppression_reason'] == 'uncalibrated_model'


def test_collector_storage_ingestion_api_and_prediction(journey, tmp_path, monkeypatch, capsys):
    import json
    from pathlib import Path
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / 'modules' / '2.2-collector' / 'src'))
    from collector_engine.models import CollectionResult
    from collector_engine.storage.local_storage import LocalRawStorage
    from workers.ingest_collection import main
    client, _, _, engine = journey
    monkeypatch.setattr('app.core.database.SessionLocal', lambda: Session(engine))
    items = [{'title': f'Collected Radar {year}', 'seo_url': f'https://unstop.com/hackathons/radar-{year}',
              'organisation': {'name': 'Collected organizer'}, 'region': 'online',
              'start_date': f'{year}-11-01T10:00:00Z'} for year in (2023, 2024, 2025)]
    url = 'https://unstop.com/api/public/opportunity/search-result?page=1'
    storage = LocalRawStorage(tmp_path / 'raw')
    location = storage.save(CollectionResult('unstop', url, 'static', status='success',
        fetched_at='2026-10-13T10:00:00Z', http_status=200, final_url=url,
        content_type='application/json', raw_content=json.dumps({'data': {'data': items}})))
    args = ['--storage-root', str(tmp_path / 'raw'), '--location', location]
    assert main(args) == 0
    assert json.loads(capsys.readouterr().out)['inserted'] == 3
    assert main(args) == 0
    assert json.loads(capsys.readouterr().out)['duplicates'] == 3
    page = client.get('/events/', params={'q': 'Collected Radar'}).json()
    assert page['total'] == 3
    assert client.get(f"/events/{page['data'][0]['id']}").json()['data']['source'] == 'Unstop'
    assert client.get('/predictions/catalog').json()['data'] == []
    forecasts = client.get('/predictions/evaluation', headers=evaluation_header(journey)).json()['data']
    forecast = next(row for row in forecasts if row['organization'] == 'Collected organizer')
    assert forecast['historical_events'] == 3 and forecast['window'] is not None
    assert main(['--storage-root', str(tmp_path / 'raw'), '--location', '../outside']) == 1
    assert client.get('/events/', params={'q': 'Collected Radar'}).json()['total'] == 3
