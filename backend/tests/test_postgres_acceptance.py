"""Only the ownership-verified disposable container runner may enable these tests."""
import copy
import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier

import pytest
from fastapi.testclient import TestClient
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, select, func, text, inspect, event as sql_event, delete
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import get_db
from app.main import app
from app.models.core import EventVersion
from app.models.hackathon import Hackathon
from app.models.organization import Organization
from workers.import_reviewed_public import load_approved, stage

BACKEND = Path(__file__).resolve().parents[1]


@pytest.fixture(scope='module')
def pg():
    value = os.getenv('RADAR_POSTGRES_ACCEPTANCE_URL')
    manifest_path = os.getenv('RADAR_POSTGRES_ACCEPTANCE_MANIFEST')
    if not value or not manifest_path:
        pytest.skip('Run scripts/postgres_acceptance.py to create an owned disposable PostgreSQL container')
    manifest = json.loads(Path(manifest_path).read_text(encoding='utf-8'))
    assert manifest['database'].startswith('radar_acceptance_')
    assert manifest['storage'] == 'tmpfs' and manifest['environment'] == 'development'
    engine = create_engine(value, connect_args={'connect_timeout': 5}, pool_pre_ping=True)
    with engine.connect() as connection:
        connection.execute(text('SET TRANSACTION READ ONLY'))
        identity = connection.execute(text('SELECT current_database() AS database, current_user AS username, '
            'host(inet_server_addr()) AS server_address, inet_server_port() AS server_port, '
            "current_setting('server_version_num')::int AS version, pg_is_in_recovery() AS recovery")).mappings().one()
        assert identity['database'] == manifest['database']
        assert identity['username'] == 'radar_acceptance'
        assert identity['server_address'] == manifest['server_address']
        assert identity['server_port'] == 5432 and 160000 <= identity['version'] < 170000
        assert not identity['recovery']
        assert inspect(connection).get_table_names(schema='public') == []
    # No migration or test writes occur until all identity checks above pass.
    environment = dict(os.environ, DATABASE_URL=value, DEBUG='false', ENVIRONMENT='development',
                       SECRET_KEY='disposable-postgres-migration-test-key-123456', EMAIL_MODE='disabled')
    result = subprocess.run([sys.executable, '-m', 'alembic', 'upgrade', 'head'], cwd=BACKEND,
                            env=environment, capture_output=True, text=True)
    assert result.returncode == 0, 'Alembic migration failed: ' + result.stderr
    heads = ScriptDirectory.from_config(Config(str(BACKEND / 'alembic.ini'))).get_heads()
    with engine.connect() as connection:
        assert set(connection.scalars(text('SELECT version_num FROM alembic_version'))) == set(heads)
    identity_report = dict(identity, environment='development', migration_heads=heads,
                           identity_verified_before_writes=True, migrations='passed')
    (Path(manifest_path).parent / 'postgres_identity.json').write_text(json.dumps(identity_report, indent=2), encoding='utf-8')
    yield engine
    engine.dispose()


@pytest.fixture
def database(pg):
    # The pg fixture has already verified the unique database/container identity.
    # Delete test rows only, retaining the schema built by actual migrations.
    with pg.begin() as connection:
        for table in (EventVersion.__table__, Hackathon.__table__, Organization.__table__):
            connection.execute(delete(table))
    yield pg


@pytest.fixture
def records():
    return load_approved(BACKEND / 'radar_collector/fixtures/reviewed_snapshot_20261025/brabble-pilot/reviewed.csv')[0]


def count(db, model):
    return db.scalar(select(func.count()).select_from(model))


def test_postgres_reviewed_merge_reimport_preserves_identity(database, records):
    from app.models.core import User, SavedItem, AuditLog
    from app.services.duplicate_review import merge_reviewed, review_token, merged_alias_id
    from app.services.duplicate_review import MergeConflict
    with Session(database) as db:
        assert stage(db, records, 'Disposable PostgreSQL duplicate reviewer')['inserted'] == 1
        original = db.scalar(select(Hackathon))
        actor = User(name='Disposable duplicate reviewer', email='duplicate-review@fixture.test', password_hash='unused')
        db.add(actor); db.flush()
        keep = Hackathon(title=original.title, organization_id=original.organization_id,
            start_date=original.start_date, end_date=original.end_date, location=original.location,
            mode=original.mode, url='https://organizer.example.test/retained', source='Retained official record')
        db.add(keep); db.flush()
        db.add_all([SavedItem(user_id=actor.id, hackathon_id=keep.id), SavedItem(user_id=actor.id, hackathon_id=original.id)])
        db.flush()
        old_id, old_url = original.id, original.url
        token = review_token(keep, original)
        merge_reviewed(db, keep.id, original.id, token, actor.id, 'Same-edition organizer evidence reviewed')
        assert merged_alias_id(db, old_url) == keep.id
        assert stage(db, records, 'Disposable PostgreSQL repeat import') == {'inserted': 0, 'duplicate_urls': 1}
        assert db.get(Hackathon, old_id) is None
        assert count(db, Hackathon) == count(db, SavedItem) == count(db, AuditLog) == 1
        assert count(db, EventVersion) == 4
        assert keep.source == 'Retained official record'
        with pytest.raises(MergeConflict):
            merge_reviewed(db, keep.id, old_id, token, actor.id, 'Stale repeat request')
        # This test owns only a transaction in the ownership-verified disposable DB.
        db.rollback()


def test_actual_migrations_match_required_tables(pg):
    assert {'hackathons', 'organizations', 'event_versions', 'discovery_sources', 'revoked_tokens',
            'email_deliveries'}.issubset(inspect(pg).get_table_names())


def test_migrated_postgres_matches_orm_metadata(pg):
    environment = dict(os.environ, DATABASE_URL=os.environ['RADAR_POSTGRES_ACCEPTANCE_URL'],
                       DEBUG='false', ENVIRONMENT='development', EMAIL_MODE='disabled')
    result = subprocess.run([sys.executable, '-m', 'alembic', 'check'], cwd=BACKEND,
                            env=environment, capture_output=True, text=True)
    assert result.returncode == 0, 'Migration/model drift: ' + result.stdout + result.stderr


def test_postgres_caller_rollback(database, records):
    with Session(database) as db:
        assert stage(db, records, 'AI-reviewed disposable PostgreSQL acceptance')['inserted'] == 1
        db.rollback()
    with Session(database) as db:
        assert count(db, Hackathon) == count(db, EventVersion) == count(db, Organization) == 0


def test_postgres_commit_duplicates_and_provenance(database, records):
    with Session(database) as db, db.begin():
        assert stage(db, records + records, 'Disposable PostgreSQL operator') == {'inserted': 1, 'duplicate_urls': 1}
    with Session(database) as db, db.begin():
        assert stage(db, records, 'Disposable PostgreSQL operator') == {'inserted': 0, 'duplicate_urls': 1}
        version = db.scalar(select(EventVersion))
        assert version.changes['acquisition']['review']['reviewer_type'] == 'ai_assistant'
        assert 'human_approval' not in version.changes['acquisition']
        assert 'source_html_sha256' not in version.changes


def test_postgres_late_failure_preserves_caller_work(database, records):
    def fail(*args):
        raise ValueError('Injected provenance write failure')
    with Session(database) as db:
        db.add(Organization(name='Unrelated caller organization'))
        db.flush()
        sql_event.listen(EventVersion, 'before_insert', fail)
        try:
            with pytest.raises(ValueError, match='Injected provenance'):
                stage(db, records, 'Disposable PostgreSQL operator')
        finally:
            sql_event.remove(EventVersion, 'before_insert', fail)
        assert count(db, Hackathon) == count(db, EventVersion) == 0
        assert db.scalars(select(Organization.name)).all() == ['Unrelated caller organization']
        db.commit()


def test_postgres_concurrent_imports(database, records):
    ready = Barrier(2)
    def write():
        ready.wait(timeout=10)
        with Session(database) as db, db.begin():
            db.execute(text("SET LOCAL lock_timeout = '10s'"))
            return stage(db, records, 'Concurrent disposable PostgreSQL operator')
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: write(), range(2)))
    assert sorted(result['inserted'] for result in results) == [0, 1]
    assert sorted(result['duplicate_urls'] for result in results) == [0, 1]
    with Session(database) as db:
        assert count(db, Hackathon) == count(db, EventVersion) == 1


def test_postgres_existing_manual_record_not_overwritten(database, records):
    with Session(database) as db:
        db.add(Hackathon(title='Existing manual record', source='Manual', url=str(records[0].event.url)))
        db.commit()
        assert stage(db, records, 'Disposable PostgreSQL operator')['duplicate_urls'] == 1
        assert db.scalar(select(Hackathon)).title == 'Existing manual record'
        assert count(db, EventVersion) == 0


def test_postgres_unsafe_isolation_refused(database, records):
    with database.connect().execution_options(isolation_level='REPEATABLE READ') as connection:
        with Session(connection) as db:
            with pytest.raises(ValueError, match='READ COMMITTED'):
                stage(db, records, 'Disposable PostgreSQL operator')


def test_postgres_health_events_and_details(database, records):
    factory = sessionmaker(bind=database)
    with factory.begin() as db:
        stage(db, records, 'Disposable PostgreSQL operator')
    def dependency():
        with factory() as db:
            yield db
    previous = dict(app.dependency_overrides)
    app.dependency_overrides[get_db] = dependency
    try:
        with TestClient(app) as client:
            assert client.get('/health').json()['status'] == 'healthy'
            result = client.get('/events/', params={'page': 1, 'page_size': 1})
            assert result.status_code == 200 and result.json()['total'] == 1
            item = result.json()['data'][0]
            assert item['acquisition']['provider'] == 'Brabble.ai'
            assert client.get(f"/events/{item['id']}").json()['data'] == item
            assert client.get('/events/', params={'page': 2, 'page_size': 1}).json()['data'] == []
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)


def test_postgres_dataset_review_publication_is_idempotent(database):
    import base64
    from datetime import datetime, timedelta, timezone
    from app.models.core import User, Role
    from app.core.security import create_access_token
    factory = sessionmaker(bind=database)
    with factory.begin() as db:
        role = Role(name='administrator')
        user = User(name='Synthetic acceptance admin', email='import-admin@example.com', password_hash='isolated-test-only', roles=[role])
        db.add(user); db.flush(); user_id = user.id
    def dependency():
        with factory() as db:
            yield db
    previous = dict(app.dependency_overrides)
    app.dependency_overrides[get_db] = dependency
    try:
        with TestClient(app) as client:
            client.headers['Authorization'] = f'Bearer {create_access_token(user_id, "administrator")}'
            now = datetime.now(timezone.utc)
            policy = dict(key='pg-synthetic-import', name='Synthetic acceptance fixture', adapter='events-json-v1', url='https://example.org/fixture', enabled=True, owner='Disposable acceptance', basis='Synthetic records owned by test', reference='synthetic-fixture-only', reviewed_at=now.isoformat(), expires_at=(now+timedelta(days=1)).isoformat(), terms_permit=True)
            assert client.put('/admin/discovery/sources', json=policy).status_code == 200
            csv = 'title,url,organization,start_date,location,mode\nSynthetic release test,https://example.org/release-event,Synthetic organizer,2027-01-15T10:00:00+00:00,Delhi,Online\n'
            body = dict(source_key=policy['key'], filename='synthetic.csv', content_base64=base64.b64encode(csv.encode()).decode(), approval_reference=policy['reference'])
            first = client.post('/admin/discovery/dataset-imports', json=body)
            assert first.status_code == 200 and first.json()['candidates_inserted'] == 1
            assert client.post('/admin/discovery/dataset-imports', json=body).json()['candidate_duplicates'] == 1
            candidate = client.get('/admin/discovery/announcements').json()['data'][0]
            event = {key:value for key,value in candidate['payload'].items() if key != 'scraped_at'}
            published = client.post(f"/admin/discovery/announcements/{candidate['id']}/review", json={'decision':'approved','note':'Explicit synthetic acceptance review','event':event})
            assert published.status_code == 200, published.text
            event_id = published.json()['event_id']
            assert client.get(f'/events/{event_id}').json()['data']['title'] == 'Synthetic release test'
            assert client.get('/admin/audit').json()['total'] >= 3
            assert client.post('/admin/discovery/dataset-imports', json=body).json()['candidate_duplicates'] == 1
            assert client.get('/events/?q=Synthetic%20release%20test').json()['total'] == 1
    finally:
        app.dependency_overrides.clear(); app.dependency_overrides.update(previous)
