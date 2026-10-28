"""Disposable database coverage; collectors never contact live websites."""
from datetime import datetime, timedelta, timezone
import pytest
from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient
from app.core.database import Base, get_db
from app.main import app
from app.models.core import EventVersion
from app.models.discovery import DiscoveryEvidence, DiscoveryRun, DiscoveryLock
from app.models.hackathon import Hackathon
from app.services.discovery_service import register_source, curated_policy, run_source, collect_source

NOW = datetime.now(timezone.utc)

@pytest.fixture
def db(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'discovery.db'}")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        register_source(session, curated_policy(NOW, enabled=True), NOW)
        yield session
    engine.dispose()

def count(db, model):
    return db.scalar(select(func.count()).select_from(model))

def test_repeat_update_stale_and_public_history(db):
    assert run_source(db, 'curated-mvp', NOW)['inserted'] == 5
    assert run_source(db, 'curated-mvp', NOW)['status'] == 'not_due'
    later = NOW + timedelta(hours=6)
    assert run_source(db, 'curated-mvp', later)['unchanged'] == 5
    assert count(db, Hackathon) == count(db, EventVersion) == 5
    assert count(db, DiscoveryEvidence) == 10
    records, rejected, metadata = collect_source(curated_policy(NOW))
    item = records[0].model_copy(update={'title': 'Updated factual title', 'scraped_at': later.replace(tzinfo=None)})
    result = run_source(db, 'curated-mvp', later + timedelta(hours=6), collector=lambda _: ([item], rejected, metadata))
    assert result['updated'] == 1
    assert count(db, EventVersion) == 6
    stale = run_source(db, 'curated-mvp', later + timedelta(hours=12), collector=lambda _: ([records[0]], 0, metadata))
    assert stale['conflicts'] == 1
    event = db.scalar(select(Hackathon).where(Hackathon.title == item.title))
    app.dependency_overrides[get_db] = lambda: db
    try:
        with TestClient(app) as client:
            history = client.get(f'/events/{event.id}/discovery').json()['data']
            assert len(history['versions']) == 2
            assert 'title' in history['versions'][0]['changed_fields']
            assert client.get('/admin/discovery/sources').status_code == 401
            assert client.get('/predictions/catalog').json()['data'] == []
    finally:
        app.dependency_overrides.clear()

def test_invalid_batch_atomic_and_retry(db):
    records, _, metadata = collect_source(curated_policy(NOW))
    bad = records[1].model_dump(); bad['end_date'] = datetime(1900, 1, 1)
    result = run_source(db, 'curated-mvp', NOW, collector=lambda _: ([records[0], bad], 0, metadata))
    assert result['status'] == 'failed'
    assert count(db, Hackathon) == count(db, DiscoveryEvidence) == count(db, EventVersion) == 0
    assert count(db, DiscoveryLock) == 0
    assert db.scalar(select(DiscoveryRun)).error_code == 'validation_or_collection_failed'
    assert run_source(db, 'curated-mvp', NOW + timedelta(hours=6))['inserted'] == 5

@pytest.mark.parametrize('reason', ['expired', 'terms', 'live'])
def test_policy_gates_never_call_transport(db, reason):
    policy = curated_policy(NOW, enabled=True).model_dump()
    if reason == 'expired':
        policy.update(reviewed_at=NOW-timedelta(days=2), expires_at=NOW-timedelta(days=1))
    else:
        policy.update(adapter='unstop-v1', url='https://unstop.com/api/public/opportunity/search-result', terms_permit=reason == 'live')
    register_source(db, policy, NOW)
    def forbidden(_):
        pytest.fail('Policy gate must precede transport')
    result = run_source(db, 'curated-mvp', NOW, collector=forbidden)
    assert result['status'] == 'paused'
    assert count(db, Hackathon) == count(db, DiscoveryLock) == 0

def test_single_writer_lock(db):
    from app.models.discovery import DiscoveryRun, DiscoveryLock
    from app.models.discovery import DiscoverySource
    source = db.scalar(select(DiscoverySource))
    run = DiscoveryRun(source_id=source.source_id, started_at=NOW.replace(tzinfo=None), status='running', metrics={})
    db.add(run); db.flush(); db.add(DiscoveryLock(id=1, run_id=run.id)); db.commit()
    assert run_source(db, 'curated-mvp', NOW)['status'] == 'busy'
    assert count(db, Hackathon) == 0

def test_unstop_adapter_handoff_without_network(db, monkeypatch, tmp_path):
    import json
    from pathlib import Path
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / 'modules' / '2.2-collector' / 'src'))
    from collector_engine.models import CollectionResult
    from collector_engine.manager import CollectorManager
    from app.schemas.discovery import SourcePolicy
    url = 'https://unstop.com/api/public/opportunity/search-result'
    policy = SourcePolicy.model_validate({**curated_policy(NOW, enabled=True).model_dump(),
        'key': 'unstop-test', 'adapter': 'unstop-v1', 'url': url, 'terms_permit': True})
    monkeypatch.setenv('RAW_DATA_DIR', str(tmp_path / 'raw'))
    result = CollectionResult('unstop-test', url, 'static', status='success', robots_allowed=True,
        fetched_at=NOW.isoformat(), http_status=200, final_url=url, content_type='application/json',
        raw_content=json.dumps({'data': {'data': [{'title': 'Adapter fixture',
            'seo_url': 'https://unstop.com/hackathons/adapter-fixture', 'organisation': {'name': 'Fixture organizer'},
            'start_date': '2026-11-01T10:00:00Z', 'region': 'online'}]}}))
    monkeypatch.setattr(CollectorManager, 'collect', lambda self, source: result)
    register_source(db, policy, NOW)
    outcome = run_source(db, policy.key, NOW, allow_live=True)
    assert outcome['status'] == 'success' and outcome['inserted'] == 0
    assert outcome['candidates_inserted'] == 1
    assert count(db, Hackathon) == 0  # Live records always require a separate review.
    from app.models.institution import Announcement
    assert db.scalar(select(Announcement)).status == 'pending'
    assert outcome['transport'] == 'governed-http'
    result.robots_allowed = False
    assert run_source(db, policy.key, NOW + timedelta(hours=6), allow_live=True)['status'] == 'failed'
    assert count(db, Hackathon) == 0

def test_worker_disabled_and_enabled_disposable_schedule(db, monkeypatch, capsys):
    import json
    from workers.discovery import main
    monkeypatch.setattr('sys.argv', ['discovery'])
    monkeypatch.delenv('DISCOVERY_ENABLED', raising=False)
    assert main() == 0
    assert json.loads(capsys.readouterr().out)['executed'] is False
    monkeypatch.setenv('DISCOVERY_ENABLED', 'true')
    monkeypatch.setattr('app.core.database.SessionLocal', lambda: Session(db.bind))
    assert main() == 0
    assert json.loads(capsys.readouterr().out)['curated-mvp']['inserted'] == 5
    assert main() == 0
    assert json.loads(capsys.readouterr().out) == {}

def test_registry_uses_database_roles_and_audits_configuration(db):
    from app.models.core import User, Role, AuditLog
    from app.core.security import create_access_token
    user = User(name='Review operator', email='operator@example.com', password_hash='test')
    db.add(user); db.commit()
    headers = {'Authorization': 'Bearer ' + create_access_token(subject=str(user.id), role='administrator')}
    app.dependency_overrides[get_db] = lambda: db
    try:
        with TestClient(app) as client:
            assert client.get('/admin/discovery/sources', headers=headers).status_code == 403
            user.roles.append(Role(name='administrator')); db.commit()
            policy = curated_policy(NOW, enabled=False).model_dump(mode='json')
            result = client.put('/admin/discovery/sources', json=policy, headers=headers)
            assert result.status_code == 200 and result.json()['network_started'] is False
            assert count(db, AuditLog) == 1
            assert client.get('/admin/discovery/runs', headers=headers).status_code == 200
    finally:
        app.dependency_overrides.clear()

def test_policy_changed_during_collection_discards_batch(db):
    def collect(policy):
        register_source(db, curated_policy(NOW, enabled=False), NOW)
        return collect_source(policy)
    assert run_source(db, 'curated-mvp', NOW, collector=collect)['status'] == 'failed'
    assert count(db, Hackathon) == count(db, DiscoveryLock) == 0
