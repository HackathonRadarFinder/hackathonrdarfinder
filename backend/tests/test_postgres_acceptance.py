"""Only ownership-verified disposable container/native runners may enable writes."""
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

from app.core.database import Base, get_db
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
    assert manifest['environment'] == 'development'
    native = manifest['storage'] == 'native-temporary'
    if native:
        from sqlalchemy.engine import make_url
        target = make_url(value)
        assert target.host == '127.0.0.1' and target.port == manifest['server_port']
        assert target.database == manifest['database'] and target.username == 'radar_acceptance'
        data = Path(manifest['data_directory']).resolve()
        owned_root = BACKEND.parent / '.test-support/native-postgres'
        assert data.is_relative_to(owned_root.resolve()) and data != owned_root.resolve()
        assert (data / '.radar-acceptance-owner').read_text(encoding='utf-8') == manifest['ownership_marker'] == manifest['run_id']
        assert manifest['server_address'] == '127.0.0.1'
        assert manifest['server_version_major'] in (16, 18)
        assert value.startswith('postgresql+psycopg://')
    else:
        assert manifest['storage'] == 'tmpfs'
    engine = create_engine(value, connect_args={'connect_timeout': 5}, pool_pre_ping=True)
    with engine.connect() as connection:
        connection.execute(text('SET TRANSACTION READ ONLY'))
        identity = connection.execute(text('SELECT current_database() AS database, current_user AS username, '
            'host(inet_server_addr()) AS server_address, inet_server_port() AS server_port, '
            "current_setting('server_version_num')::int AS version, pg_is_in_recovery() AS recovery")).mappings().one()
        assert identity['database'] == manifest['database']
        assert identity['username'] == 'radar_acceptance'
        assert identity['server_address'] == manifest['server_address']
        if native:
            assert identity['server_port'] == manifest['server_port']
            major = manifest['server_version_major']
            assert major * 10000 <= identity['version'] < (major + 1) * 10000
            actual = connection.scalar(text("SELECT current_setting('data_directory')"))
            assert Path(actual).resolve() == data
        else:
            assert identity['server_port'] == 5432 and 160000 <= identity['version'] < 170000
        assert not identity['recovery']
        assert inspect(connection).get_table_names(schema='public') == []
    # No migration or test writes occur until all identity checks above pass.
    environment = dict(os.environ, DATABASE_URL=value, DEBUG='false', ENVIRONMENT='development',
                       SECRET_KEY='disposable-postgres-migration-test-key-123456', EMAIL_MODE='disabled')
    result = subprocess.run([sys.executable, '-m', 'workers.migrate'], cwd=BACKEND,
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
        for table in reversed(Base.metadata.sorted_tables):
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



def test_postgres_complete_reviewed_release_journey(database, monkeypatch):
    """Synthetic owned data; actual API authorization, publication and merge transactions."""
    import base64
    from datetime import datetime, timedelta, timezone
    from types import SimpleNamespace
    from app.models.core import User, Role
    from app.core.security import create_access_token
    from app.services.in_app_reminders import enqueue_in_app
    from app.services.notification_service import enqueue_due, dispatch_due
    from app.services import notification_service
    factory = sessionmaker(bind=database)
    with factory.begin() as db:
        admin = User(name='Synthetic release administrator', email='release-admin@example.com',
            password_hash='not-a-login-password', roles=[Role(name='administrator')])
        db.add(admin); db.flush(); admin_id = admin.id
    def dependency():
        with factory() as db:
            yield db
    previous = dict(app.dependency_overrides)
    app.dependency_overrides[get_db] = dependency
    checks = []
    try:
        with TestClient(app) as client:
            now = datetime.now(timezone.utc)
            date = (now + timedelta(hours=6)).isoformat()
            policy = dict(key='complete-release-fixture', name='Synthetic owned acceptance source',
                adapter='events-json-v1', url='https://example.org/owned-fixture', enabled=True,
                owner='Disposable acceptance', basis='Synthetic data generated only for isolated tests',
                reference='synthetic-owned-data-only', reviewed_at=now.isoformat(),
                expires_at=(now + timedelta(days=1)).isoformat(), terms_permit=True)
            admin_headers = {'Authorization': f'Bearer {create_access_token(admin_id, "administrator")}'}
            assert client.put('/admin/discovery/sources', headers=admin_headers, json=policy).status_code == 200
            content = ('title,url,organization,start_date,location,mode\n'
                f'Synthetic Release Buildathon,https://root-release.example.org,Synthetic College,{date},Delhi,Online\n'
                f'Synthetic Release Buildathon,https://example.org/release-b,Synthetic College,{date},Delhi,Online\n')
            upload = dict(source_key=policy['key'], filename='owned-fixture.csv',
                content_base64=base64.b64encode(content.encode()).decode(), approval_reference=policy['reference'])
            staged = client.post('/admin/discovery/dataset-imports', headers=admin_headers, json=upload)
            assert staged.status_code == 200 and staged.json()['candidates_inserted'] == 2
            assert client.get('/events/?page=1').json()['total'] == 0
            repeated = client.post('/admin/discovery/dataset-imports', headers=admin_headers, json=upload)
            assert repeated.json()['candidate_duplicates'] == 2
            candidates = client.get('/admin/discovery/announcements', headers=admin_headers).json()['data']
            published = []
            for candidate in candidates:
                event = dict(candidate['payload']); event.pop('scraped_at', None)
                result = client.post(f"/admin/discovery/announcements/{candidate['id']}/review",
                    headers=admin_headers, json={'decision':'approved', 'note':'Explicit synthetic owned-data review', 'event':event})
                assert result.status_code == 200, result.text
                published.append(result.json()['event_id'])
            assert len(published) == 2 and client.get('/events/?page=1').json()['total'] == 2
            checks.append('source registration, import, repeat idempotency, review and publication')
            registration = client.post('/auth/register', json={'name':'Synthetic release user',
                'email':'release-user@example.com', 'password':'DisposableReleasePassword123!'})
            assert registration.status_code in (200, 201), registration.text
            signed_in = client.post('/auth/login', json={'email':'release-user@example.com','password':'DisposableReleasePassword123!'})
            assert signed_in.status_code == 200
            user_headers = {'Authorization': 'Bearer ' + signed_in.json()['access_token']}
            profile = client.put('/account/profile', headers=user_headers, json={'name':'Updated synthetic account'})
            assert profile.status_code == 200 and profile.json()['name'] == 'Updated synthetic account'
            assert client.get('/auth/me', headers=user_headers).json()['name'] == 'Updated synthetic account'
            for path in ['/admin/audit','/admin/duplicates','/admin/notification-monitor']:
                assert client.get(path, headers=user_headers).status_code == 403
            assert client.post('/admin/discovery/dataset-imports', headers=user_headers, json=upload).status_code == 403
            assert client.put('/account/discovery-preferences', headers=user_headers, json={
                'preferred_location':'Delhi','preferred_mode':'Online','interests':'Buildathon','in_app_reminders':True}).status_code == 200
            matches = client.get('/account/recommendations', headers=user_headers).json()['data']
            assert len(matches) == 2 and all(row['reasons'] for row in matches)
            assert client.get('/account/discovery-preferences', headers=admin_headers).json()['interests'] == ''
            for event_id in published:
                assert client.put(f'/account/saved/{event_id}', headers=user_headers).status_code == 200
            assert len(client.get('/account/saved', headers=user_headers).json()['data']) == 2
            pairs = client.get('/admin/duplicates', headers=admin_headers).json()['data']
            assert len(pairs) == 1
            pair = pairs[0]
            merge_body = {'survivor_id':pair['survivor']['id'], 'duplicate_id':pair['duplicate']['id'],
                'review_token':pair['review_token'], 'note':'Confirmed same synthetic edition across two listing URLs'}
            assert client.post('/admin/duplicates/merge', headers=user_headers, json=merge_body).status_code == 403
            merged = client.post('/admin/duplicates/merge', headers=admin_headers, json=merge_body)
            assert merged.status_code == 200, merged.text
            assert client.get('/events/?page=1').json()['total'] == 1
            saved = client.get('/account/saved', headers=user_headers).json()['data']
            assert len(saved) == 1 and saved[0]['id'] == pair['survivor']['id']
            assert client.post('/admin/discovery/dataset-imports', headers=admin_headers, json=upload).json()['candidate_duplicates'] == 2
            assert client.get('/admin/duplicates', headers=admin_headers).json()['data'] == []
            assert client.post('/admin/duplicates/merge', headers=admin_headers, json=merge_body).status_code == 409
            checks.append('live role denials, private preferences, recommendations and saved-item-preserving duplicate merge')
            with factory() as db:
                assert enqueue_in_app(db, now)['inserted'] == 1
                assert enqueue_in_app(db, now)['inserted'] == 0
            notices = client.get('/notifications/', headers=user_headers).json()['data']
            assert notices and client.get('/notifications/', headers=admin_headers).json()['data'] == []
            assert client.put(f"/notifications/{notices[0]['id']}/read", headers=user_headers).json()['is_read'] is True
            assert client.put(f"/notifications/{notices[0]['id']}/read", headers=admin_headers).status_code == 404
            assert client.put('/account/preferences', headers=user_headers, json={'email_reminders':True}).status_code == 200
            def forbidden(*args, **kwargs):
                raise AssertionError('Release acceptance must never contact SMTP')
            monkeypatch.setattr(notification_service, 'send_message', forbidden)
            with factory() as db:
                assert enqueue_due(db, now) == 1
                assert dispatch_due(db, SimpleNamespace(EMAIL_MODE='dry-run'), now) == {'dry-run':0}
            assert client.put('/account/preferences', headers=user_headers, json={'email_reminders':False}).status_code == 200
            readiness = client.get('/predictions/readiness')
            assert readiness.status_code == 200 and readiness.json()['data']['public_predictions_enabled'] is False
            assert client.get('/predictions/catalog').json()['data'] == []
            actions = {row['action'] for row in client.get('/admin/audit', headers=admin_headers).json()['data']}
            assert {'dataset_import_staged','announcement_reviewed','duplicate_events_merged'}.issubset(actions)
            assert client.post('/auth/logout', headers=user_headers).status_code == 200
            assert client.get('/account/saved', headers=user_headers).status_code == 401
            checks.append('idempotent scheduled notices, owned read state, email consent/dry-run, ML suppression and logout revocation')
        output = Path(os.environ['RADAR_POSTGRES_ACCEPTANCE_MANIFEST']).parent / 'complete-release-journey.json'
        output.write_text(json.dumps({'synthetic_owned_data_only':True, 'checks':checks,
            'smtp_attempts':0, 'remaining_public_events_after_merge':1, 'status':'passed'}, indent=2), encoding='utf-8')
    finally:
        app.dependency_overrides.clear(); app.dependency_overrides.update(previous)


def test_postgres_maximum_dataset_import_is_batched_and_idempotent(database):
    import base64
    from datetime import datetime, timedelta, timezone
    from time import perf_counter
    from types import SimpleNamespace
    from app.models.core import User, Source
    from app.models.discovery import DiscoverySource
    from app.models.institution import Announcement
    from app.api.routes.dataset_import import DatasetUpload
    from app.services.dataset_import import import_dataset
    now = datetime.now(timezone.utc)
    with Session(database) as db:
        user = User(name='Synthetic capacity operator', email='capacity@example.com', password_hash='unused')
        source = Source(name='Synthetic owned capacity data', url='https://example.org/capacity')
        db.add_all([user,source]); db.flush()
        policy = dict(key='capacity-fixture', name=source.name, adapter='events-json-v1', url=source.url,
            enabled=True, interval_seconds=21600, owner='Disposable test', basis='Synthetic fixture owned by test',
            reference='synthetic-only', terms_permit=True, reviewed_at=now.isoformat(), expires_at=(now+timedelta(days=1)).isoformat())
        db.add(DiscoverySource(source_id=source.id, key=policy['key'], config=policy, enabled=True,
            interval_seconds=21600, next_run_at=now.replace(tzinfo=None)))
        db.commit(); actor=SimpleNamespace(sub=str(user.id))
        csv='title,url,organization,start_date\n'+''.join(f'Synthetic capacity {i},https://example.org/capacity-{i},Synthetic College,2027-01-01T10:00:00+00:00\n' for i in range(1000))
        upload=DatasetUpload(source_key=policy['key'], filename='synthetic-capacity.csv', approval_reference=policy['reference'], content_base64=base64.b64encode(csv.encode()).decode())
        selects=[]
        def observe(conn,cursor,statement,parameters,context,executemany):
            if statement.lstrip().upper().startswith('SELECT'):
                selects.append(statement)
        sql_event.listen(database,'before_cursor_execute',observe)
        try:
            started=perf_counter();first=import_dataset(db,upload,actor);first_seconds=perf_counter()-started
            first_queries=len(selects);selects.clear()
            started=perf_counter();repeat=import_dataset(db,upload,actor);repeat_seconds=perf_counter()-started
            repeat_queries=len(selects)
        finally:
            sql_event.remove(database,'before_cursor_execute',observe)
        assert first['candidates_inserted']==repeat['candidate_duplicates']==1000
        assert first_queries<=4 and repeat_queries<=4, (first_queries,repeat_queries)
        assert db.scalar(select(func.count()).select_from(Announcement))==1000
        assert db.scalar(select(func.count()).select_from(Hackathon))==0
        output=Path(os.environ['RADAR_POSTGRES_ACCEPTANCE_MANIFEST']).parent/'import-performance.json'
        output.write_text(json.dumps({'rows':1000,'database':'owned disposable PostgreSQL 16',
            'first_import_seconds':first_seconds,'repeat_import_seconds':repeat_seconds,
            'first_selects':first_queries,'repeat_selects':repeat_queries,
            'published_events':0,'idempotency':'passed','synthetic_data_only':True},indent=2),encoding='utf-8')

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
