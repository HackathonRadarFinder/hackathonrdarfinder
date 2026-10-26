"""Offline upload coverage: permissions, bounded parsing, staging, idempotency."""
import base64
import io
import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from app.core.database import Base, get_db
from app.models.core import User, Role, Source, AuditLog
from app.models.discovery import DiscoverySource
from app.models.institution import Announcement
from app.models.hackathon import Hackathon
from app.api.routes.dataset_import import router, DatasetUpload
from app.api.deps import get_current_db_user, get_current_user_token
from app.services.dataset_import import import_dataset, read_table, parse_rows


@pytest.fixture
def context():
    engine = create_engine('sqlite+pysqlite://', poolclass=StaticPool, connect_args={'check_same_thread': False})
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        now = datetime.now(timezone.utc)
        user = User(name='Manager', email='manager@example.com', password_hash='test', roles=[Role(name='source_manager')])
        source = Source(name='Approved dataset', url='https://example.edu/events')
        db.add_all([user, source]); db.flush()
        policy = dict(key='test-dataset', name='Approved dataset', adapter='rss-v1',
            url=source.url, enabled=True, interval_seconds=21600, owner='Test owner',
            basis='Explicit reuse license', reference='LICENSE-123', terms_permit=True,
            reviewed_at=(now - timedelta(days=1)).isoformat(), expires_at=(now + timedelta(days=1)).isoformat())
        registry = DiscoverySource(source_id=source.id, key='test-dataset', config=policy,
            enabled=True, interval_seconds=21600, next_run_at=now.replace(tzinfo=None))
        db.add(registry); db.commit()
        yield db, user, registry
    engine.dispose()


def body(content=b'title,url,organization,start_date\nReal event,https://example.edu/event,Example University,2027-01-01\n', **changes):
    return DatasetUpload(**{**dict(source_key='test-dataset', filename='dataset.csv',
        approval_reference='LICENSE-123', content_base64=base64.b64encode(content).decode()), **changes})


def test_csv_stages_uncertain_dates_without_inventing_and_is_idempotent(context):
    db, user, registry = context
    actor = SimpleNamespace(sub=str(user.id))
    first = import_dataset(db, body(), actor)
    assert first['published'] is False and first['candidates_inserted'] == 1
    candidate = db.scalar(select(Announcement))
    assert candidate.status == 'pending'
    assert 'start_date' not in candidate.payload
    assert candidate.evidence['raw_dates']['start_date'] == '2027-01-01'
    assert candidate.evidence['checksum'] == first['checksum']
    assert 'start_date_requires_review' in candidate.evidence['issues']
    assert db.scalar(select(func.count()).select_from(Hackathon)) == 0
    second = import_dataset(db, body(), actor)
    assert second['candidate_duplicates'] == 1 and second['candidates_inserted'] == 0
    assert db.scalar(select(func.count()).select_from(Announcement)) == 1
    assert 'LICENSE-123' in db.scalar(select(AuditLog)).details


@pytest.mark.parametrize('change', ['disabled', 'expired', 'permission', 'reference'])
def test_requires_current_explicit_reuse_approval(context, change):
    db, user, registry = context
    upload = body()
    config = dict(registry.config)
    if change == 'disabled': registry.enabled = False
    if change == 'permission': config['terms_permit'] = False
    if change == 'expired': config['expires_at'] = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    if change == 'reference': upload = body(approval_reference='different-record')
    registry.config = config; db.commit()
    with pytest.raises(HTTPException) as exc:
        import_dataset(db, upload, SimpleNamespace(sub=str(user.id)))
    assert exc.value.status_code == 409
    assert db.scalar(select(func.count()).select_from(Announcement)) == 0


@pytest.mark.parametrize('content', [b'title,title,url\na,b,https://example.edu/a\n',
    b'name,url\na,https://example.edu/a\n', b'title,url\na\n',
    b'title,url\na,http://localhost/a\n', b'title,url\na,https://127.0.0.1/a\n',
    b'title,url\na,https://example.edu/a,extra\n', b'\xff',
    b'title,url\n' + b'a,https://example.edu/a\n' * 1001])
def test_malformed_tables_rejected_without_partial_writes(context, content):
    db, user, registry = context
    with pytest.raises(HTTPException) as exc:
        import_dataset(db, body(content), SimpleNamespace(sub=str(user.id)))
    assert exc.value.status_code == 422
    assert db.scalar(select(func.count()).select_from(Announcement)) == 0


def test_bad_base64_and_oversized_upload_rejected():
    for value in ['invalid!', base64.b64encode(b'x' * 2000001).decode()]:
        with pytest.raises(HTTPException):
            read_table('data.csv', value)


def test_xlsx_explicit_values_dates_and_formulas(context):
    from openpyxl import Workbook
    db, user, registry = context
    book = Workbook(); sheet = book.active
    sheet.append(['title', 'url', 'organization', 'start_date'])
    sheet.append(['Verified event', 'https://example.edu/xlsx', 'Example', '2027-01-01T12:00:00+05:30'])
    stream = io.BytesIO(); book.save(stream)
    result = import_dataset(db, body(stream.getvalue(), filename='events.xlsx'), SimpleNamespace(sub=str(user.id)))
    assert result['candidates_inserted'] == 1
    candidate = db.scalar(select(Announcement))
    assert candidate.payload['start_date'] == '2027-01-01T12:00:00+05:30'
    sheet['A2'] = '=1+1'; stream = io.BytesIO(); book.save(stream)
    with pytest.raises(HTTPException):
        read_table('events.xlsx', base64.b64encode(stream.getvalue()).decode())


def test_upload_route_checks_current_database_role(context):
    db, user, registry = context
    app = FastAPI(); app.include_router(router)
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as client:
        assert client.post('/admin/discovery/dataset-imports', json=body().model_dump()).status_code in (401, 403)
        app.dependency_overrides[get_current_db_user] = lambda: user
        app.dependency_overrides[get_current_user_token] = lambda: SimpleNamespace(jti='test', exp=2000000000)
        assert client.post('/admin/discovery/dataset-imports', json=body().model_dump()).status_code == 200
        user.roles = [Role(name='user')]; db.commit()
        assert client.post('/admin/discovery/dataset-imports', json=body().model_dump()).status_code == 403
