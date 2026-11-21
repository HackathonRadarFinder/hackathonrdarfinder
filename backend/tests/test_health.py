from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "healthy"
    assert payload["service"] == "hackathon-radar-api"


def test_readiness_rejects_missing_or_stale_schema_and_accepts_head(tmp_path, monkeypatch):
    from sqlalchemy import create_engine, text
    from app.core import database
    engine = create_engine(f"sqlite:///{(tmp_path / 'readiness.db').as_posix()}", connect_args={"check_same_thread": False})
    monkeypatch.setattr(database, 'engine', engine)
    try:
        response = client.get('/ready')
        assert response.status_code == 503 and response.json()['code'] == 'DATABASE_NOT_READY'
        with engine.begin() as connection:
            connection.execute(text('CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)'))
            connection.execute(text("INSERT INTO alembic_version VALUES ('c8d9e0f1a2b3')"))
        assert client.get('/ready').json()['code'] == 'SCHEMA_NOT_READY'
        from alembic.config import Config
        from alembic.script import ScriptDirectory
        from pathlib import Path
        config = Config()
        config.set_main_option('script_location', str(Path(__file__).resolve().parents[1] / 'database/migrations'))
        head = ScriptDirectory.from_config(config).get_current_head()
        with engine.begin() as connection:
            connection.execute(text('UPDATE alembic_version SET version_num=:head'), {'head': head})
        assert client.get('/ready').json() == {'status': 'ready', 'database': 'connected', 'migrations': 'current'}
    finally:
        engine.dispose()


def _health_engine(tmp_path, monkeypatch):
    from sqlalchemy import create_engine
    from app.core import database
    engine = create_engine(f"sqlite:///{(tmp_path / 'health.db').as_posix()}", connect_args={"check_same_thread": False})
    monkeypatch.setattr(database, 'engine', engine)
    return engine


def _record_run(engine, finished_at, status='succeeded'):
    import uuid
    from sqlalchemy import insert
    from app.models.discovery import DiscoveryRun
    DiscoveryRun.__table__.create(engine, checkfirst=True)
    with engine.begin() as connection:
        connection.execute(insert(DiscoveryRun).values(
            id=uuid.uuid4(), source_id=uuid.uuid4(), started_at=finished_at, finished_at=finished_at,
            status=status, metrics={}))


def test_api_health_reports_connected_database_and_unknown_workers_without_runs(tmp_path, monkeypatch):
    engine = _health_engine(tmp_path, monkeypatch)
    try:
        response = client.get('/api/v1/health')
        assert response.status_code == 200
        payload = response.json()
        assert payload['status'] == 'healthy' and payload['database'] == 'connected'
        assert payload['workers']['status'] == 'unknown' and payload['workers']['last_run_at'] is None
        monkeypatch.setenv('WORKER_FRESHNESS_REQUIRED', 'true')
        assert client.get('/api/v1/health').status_code == 503
    finally:
        engine.dispose()


def test_api_health_reports_worker_freshness_and_alerts_when_stale(tmp_path, monkeypatch):
    from datetime import datetime, timedelta, timezone
    engine = _health_engine(tmp_path, monkeypatch)
    monkeypatch.setenv('WORKER_MAX_AGE_SECONDS', '7200')
    try:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        _record_run(engine, now - timedelta(minutes=30))
        response = client.get('/api/v1/health')
        assert response.status_code == 200
        workers = response.json()['workers']
        assert workers['status'] == 'fresh' and workers['last_run_status'] == 'succeeded'
        assert 1700 <= workers['age_seconds'] <= 1900 and workers['max_age_seconds'] == 7200
        _record_run(engine, now - timedelta(days=1), status='failed')
        assert client.get('/api/v1/health').json()['workers']['status'] == 'fresh'  # newest finished run wins
        with engine.begin() as connection:
            connection.exec_driver_sql('DELETE FROM discovery_runs')
        _record_run(engine, now - timedelta(hours=5))
        stale = client.get('/api/v1/health')
        assert stale.status_code == 503
        assert stale.json()['status'] == 'degraded' and stale.json()['workers']['status'] == 'stale'
    finally:
        engine.dispose()


def test_api_health_fails_when_database_is_unavailable(monkeypatch):
    from sqlalchemy import create_engine
    from app.core import database
    engine = create_engine('sqlite:////nonexistent-directory/radar.db')
    monkeypatch.setattr(database, 'engine', engine)
    try:
        response = client.get('/api/v1/health')
        assert response.status_code == 503
        payload = response.json()
        assert payload['status'] == 'unhealthy' and payload['database'] == 'unavailable'
        assert 'nonexistent' not in response.text
    finally:
        engine.dispose()
