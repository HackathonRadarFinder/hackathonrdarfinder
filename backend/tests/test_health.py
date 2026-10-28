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
