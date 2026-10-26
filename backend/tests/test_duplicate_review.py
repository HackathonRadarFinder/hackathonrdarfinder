"""Production service/router regressions on an isolated FK-enforcing database."""
from datetime import datetime, timedelta
from types import SimpleNamespace
import uuid
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from app.core.database import Base, get_db
from app.api.deps import require_admin, get_current_db_user, get_current_user_token
from app.api.routes.duplicate_review import router
from app.models.hackathon import Hackathon
from app.models.organization import Organization
from app.models.core import User, Source, SavedItem, Prediction, EventVersion, AuditLog
from app.models.discovery import DiscoveryRun, DiscoveryEvidence, DiscoveryEvent
from app.models.email_delivery import EmailDelivery
from app.models.institution import Announcement
from app.schemas.user import TokenPayload
from app.services.duplicate_review import candidate_pairs, merge_reviewed, review_token, merged_alias_id, MergeConflict

NOW = datetime(2026, 11, 12)


@pytest.fixture
def db():
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    @event.listens_for(engine, 'connect')
    def enforce_fk(connection, _):
        connection.execute('PRAGMA foreign_keys=ON')
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


def seed(db):
    org = Organization(name='Example Institute')
    admin = User(name='Reviewer', email='review@example.test', password_hash='unused')
    other = User(name='Other', email='other@example.test', password_hash='unused')
    source = Source(name='Approved fixture source')
    db.add_all([org, admin, other, source]); db.flush()
    a = Hackathon(title='Open Buildathon 2026', organization_id=org.id, start_date=NOW, location='Online', source='alpha', url='https://a.test/1')
    b = Hackathon(title='2026 Open Buildathon', organization_id=org.id, start_date=NOW + timedelta(days=1), location='Virtual', source='beta', url='https://b.test/1', description='Preserved source details')
    db.add_all([a, b]); db.flush()
    return a, b, admin, other, source


def test_candidates_require_evidence_and_exclude_annual_editions(db):
    a, b, *_ = seed(db)
    assert len(candidate_pairs(db)['data']) == 1
    b.start_date = NOW.replace(year=2027)
    assert candidate_pairs(db)['data'] == []
    b.start_date = NOW
    b.title = 'Open Buildathon 2027'
    assert candidate_pairs(db)['data'] == []
    b.title = a.title
    b.organization_id = None; b.organization = None
    assert candidate_pairs(db)['data'] == []


def test_explicit_merge_preserves_all_relations_and_history(db):
    a, b, admin, other, source = seed(db)
    run = DiscoveryRun(source_id=source.id, started_at=NOW, status='success')
    db.add(run); db.flush()
    db.add_all([SavedItem(user_id=admin.id, hackathon_id=a.id),
        SavedItem(user_id=admin.id, hackathon_id=b.id), SavedItem(user_id=other.id, hackathon_id=b.id),
        Prediction(hackathon_id=b.id, prediction='test baseline'),
        EventVersion(hackathon_id=b.id, version_number=1, snapshot={'title': 'Original historical title'}),
        DiscoveryEvent(source_id=source.id, canonical_url=b.url, hackathon_id=b.id, last_observed_at=NOW),
        DiscoveryEvidence(hackathon_id=b.id, run_id=run.id, source_id=source.id, observed_at=NOW,
            checksum='a'*64, document_url=b.url, adapter_version='fixture-v1', snapshot={'original': True}),
        Announcement(source_id=source.id, fingerprint='b'*64, payload={}, evidence={}, observed_at=NOW,
            last_seen_at=NOW, status='approved', hackathon_id=b.id),
        EmailDelivery(user_id=other.id, hackathon_id=b.id, kind='upcoming', event_at=NOW,
            next_attempt_at=NOW, status='accepted', attempts=1)])
    db.commit()
    removed = b.id
    result = merge_reviewed(db, a.id, b.id, review_token(a, b), admin.id, 'Reviewed official same-edition evidence')
    db.commit()
    assert db.get(Hackathon, removed) is None
    assert result['survivor_id'] == a.id
    assert a.description == 'Preserved source details'
    assert db.scalar(select(func.count()).select_from(SavedItem)) == 2
    for model in (SavedItem, Prediction, EventVersion, DiscoveryEvent, DiscoveryEvidence, Announcement, EmailDelivery):
        assert set(db.scalars(select(model.hackathon_id))) == {a.id}
    versions = db.scalars(select(EventVersion).order_by(EventVersion.version_number)).all()
    assert len({v.version_number for v in versions}) == len(versions) == 4
    assert versions[0].snapshot == {'title': 'Original historical title'}
    assert versions[0].changes['merged_from_event_id'] == removed
    audit = db.scalar(select(AuditLog))
    assert audit.user_id == admin.id and 'coalesced_saved_items' in audit.details
    assert db.scalar(select(DiscoveryEvidence)).snapshot == {'original': True}


def test_stale_review_and_email_collisions_reject_without_data_loss(db):
    a, b, admin, *_ = seed(db)
    token = review_token(a, b)
    b.description = 'Changed after inspection'
    with pytest.raises(MergeConflict, match='changed'):
        merge_reviewed(db, a.id, b.id, token, admin.id, 'Reviewed')
    for row in (a, b):
        db.add(EmailDelivery(user_id=admin.id, hackathon_id=row.id, kind='upcoming', event_at=NOW, next_attempt_at=NOW))
    db.flush()
    with pytest.raises(MergeConflict, match='delivery'):
        merge_reviewed(db, a.id, b.id, review_token(a, b), admin.id, 'Reviewed')
    assert db.scalar(select(func.count()).select_from(Hackathon)) == 2
    assert db.scalar(select(func.count()).select_from(EventVersion)) == 0


def test_router_requires_admin_and_explicit_fresh_confirmation(db):
    a, b, admin, *_ = seed(db)
    db.commit()
    app = FastAPI(); app.include_router(router)
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as client:
        assert client.get('/admin/duplicates').status_code == 401
        app.dependency_overrides[get_current_db_user] = lambda: SimpleNamespace(roles=[])
        app.dependency_overrides[get_current_user_token] = lambda: TokenPayload(sub=str(admin.id), role='user', jti='test', exp=9999999999)
        assert client.get('/admin/duplicates').status_code == 403
        app.dependency_overrides[require_admin] = lambda: SimpleNamespace(sub=str(admin.id))
        candidate = client.get('/admin/duplicates').json()['data'][0]
        body = dict(survivor_id=a.id, duplicate_id=b.id, review_token=candidate['review_token'], note='Verified same edition')
        assert client.post('/admin/duplicates/merge', json={**body, 'note': '     '}).status_code == 422
        assert client.post('/admin/duplicates/merge', json={**body, 'review_token': '0'*64}).status_code == 409
        response = client.post('/admin/duplicates/merge', json=body)
        assert response.status_code == 200, response.text
        assert client.post('/admin/duplicates/merge', json=body).status_code == 409
        assert client.get('/admin/duplicates').json()['data'] == []


def test_postgresql_merge_locks_compile_and_invalid_chronology_rejects(db):
    from sqlalchemy.dialects import postgresql
    statement = select(Hackathon).where(Hackathon.id.in_([1, 2])).order_by(Hackathon.id).with_for_update()
    assert 'FOR UPDATE' in str(statement.compile(dialect=postgresql.dialect()))
    a, b, admin, *_ = seed(db)
    a.start_date = NOW + timedelta(days=1)
    b.end_date = NOW
    with pytest.raises(MergeConflict, match='end before'):
        merge_reviewed(db, a.id, b.id, review_token(a, b), admin.id, 'Reviewed')
    assert db.scalar(select(func.count()).select_from(Hackathon)) == 2


def test_merged_url_survives_reviewed_curated_and_discovery_reimports(db):
    from app.schemas.event import EventCreate
    from app.models.discovery import DiscoverySource
    from app.services.discovery_service import ingest_discovery
    from workers.import_reviewed_public import ReviewedRecord, stage
    from workers.ingest_curated import ingest
    a, b, admin, _, source = seed(db)
    b.url, b.source = 'https://unstop.com/hackathons/reviewed-123456', 'Unstop'
    incoming = EventCreate(title=b.title, organization=b.organization.name, start_date=b.start_date,
        location=b.location, url=b.url, source=b.source, scraped_at=NOW, description='Approved source facts')
    policy = DiscoverySource(source_id=source.id, key='alias-fixture', config={}, enabled=False, next_run_at=NOW)
    run = DiscoveryRun(source_id=source.id, started_at=NOW, status='success')
    db.add_all([policy, run]); db.commit()
    keep_id, removed_id = a.id, b.id
    merge_reviewed(db, a.id, b.id, review_token(a, b), admin.id, 'Reviewed source duplicate')
    db.commit()
    assert merged_alias_id(db, str(incoming.url) + '/?utm_source=retry') == keep_id
    record = ReviewedRecord(incoming, 'a'*64, 'exact', 'reviewed_manual', 'Fixture approval')
    assert stage(db, [record], 'Fixture operator') == {'inserted': 0, 'duplicate_urls': 1}
    db.commit()
    assert ingest(db, [incoming]) == {'inserted': 0, 'duplicates': 1}
    metadata = dict(checksum='a'*64, document_url=str(incoming.url), adapter_version='fixture-v1')
    assert ingest_discovery(db, policy, run, [incoming], metadata, NOW)['unchanged'] == 1
    db.commit()
    assert db.get(Hackathon, removed_id) is None
    assert db.get(Hackathon, keep_id).source == 'alpha'
    assert db.scalar(select(func.count()).select_from(Hackathon)) == 1
    assert db.scalar(select(DiscoveryEvent)).hackathon_id == keep_id
    assert db.scalar(select(DiscoveryEvidence)).snapshot['source'] == 'Unstop'


def test_conflicting_merged_alias_claim_is_rejected(db):
    a, b, admin, *_ = seed(db)
    url = b.url
    merge_reviewed(db, a.id, b.id, review_token(a, b), admin.id, 'Reviewed duplicate')
    db.flush()
    db.add(Hackathon(title='Conflicting legacy row', url=url))
    db.flush()
    with pytest.raises(MergeConflict, match='Conflicting merged URL'):
        merged_alias_id(db, url)
