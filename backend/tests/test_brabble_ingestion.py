"""Brabble normalization and reviewed ingestion into disposable SQLite only."""
import csv
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, func, event as sql_event
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import Base, get_db
from app.main import app
from app.models.core import EventVersion
from app.models.hackathon import Hackathon
from app.models.organization import Organization
from app.schemas.event import EventCreate
from app.services.brabble_adapter import normalize, prepare, validate_evidence
from radar_collector.radar_scraper import save
from workers.import_reviewed_public import ACCEPT, load_approved, stage

DATA = Path(__file__).resolve().parents[1] / 'radar_collector/output/brabble-live'


@pytest.fixture
def inputs(monkeypatch):
    import requests
    def forbidden(*args, **kwargs):
        raise AssertionError('Brabble normalization/import must remain offline')
    monkeypatch.setattr(requests.Session, 'request', forbidden)
    exports = json.loads((DATA / 'hackathons.json').read_text(encoding='utf-8-sig'))
    raw = json.loads((DATA / 'unstop.json').read_text(encoding='utf-8-sig'))
    return raw[0], exports[0]


def test_real_dataset_quality_and_dry_run(tmp_path, inputs):
    report = prepare(DATA, tmp_path)
    assert report['input_records'] == report['pending_review'] == 206
    assert report['platforms'] == {'Unstop': 195, 'Devfolio': 11}
    assert report['schema_valid'] == 195 and report['schema_invalid'] == 11
    assert report['duplicates'] == report['rejected'] == report['invalid_url_count'] == 0
    assert report['input_csv_json_match'] is True
    assert report['missing_fields']['organization'] == 11
    assert report['missing_fields']['start_date'] == report['missing_fields']['end_date'] == 206
    assert load_approved(tmp_path / 'candidates.csv') == ([], 206)


@pytest.mark.parametrize('kind', ['competition', 'contest'])
def test_deadline_semantics_and_no_invented_dates(inputs, kind):
    raw, metadata = inputs
    raw['kind'] = kind
    row = normalize(raw, metadata)
    assert bool(row['registration_deadline']) == (kind == 'competition')
    assert bool(row['start_date']) == (kind == 'contest')
    assert row['end_date'] == ''
    assert row['prize'] == '\u20b918K'
    assert row['source_hash'] == ''
    assert row['collection_mode'] == 'brabble_api'
    assert row['acquisition_evidence']['raw_record'] == raw
    assert row['acquisition_evidence']['acquired_at'] == metadata['acquired_at']


def test_placeholders_and_venue(inputs):
    raw, metadata = inputs
    raw.update(organiser='See listing', city='See listing', prize={'label': 'See listing'})
    row = normalize(raw, metadata)
    assert row['organization'] == row['location'] == row['prize'] == ''
    assert 'organization_missing' in row['issues']


@pytest.mark.parametrize('change', [
    {'kind': 'ambiguous'}, {'deadline': '2026-10-25'},
    {'url': 'https://unstop.com.evil.test/hackathons/x'},
    {'shareUrl': 'https://evil.test/s/unstop-1771873'},
])
def test_invalid_api_evidence_rejected(inputs, change):
    raw, metadata = inputs
    raw.update(change)
    with pytest.raises(ValueError):
        normalize(raw, metadata)


def reviewed_csv(inputs, tmp_path):
    raw, metadata = inputs
    unstop = normalize(raw, metadata)
    dev_raw = json.loads((DATA / 'devfolio.json').read_text(encoding='utf-8-sig'))[0]
    dev_metadata = next(row for row in json.loads((DATA / 'hackathons.json').read_text(encoding='utf-8-sig'))
                        if row['provider_id'] == dev_raw['id'])
    devfolio = normalize(dev_raw, dev_metadata)
    # Simulated review only in disposable tests. Never alter the live review queue.
    devfolio['organization'] = 'Test-only verified Devfolio organizer'
    for row in (unstop, devfolio):
        row['review_status'] = 'approved'
        row['acquisition_evidence']['verified_fields'] = ['organization', 'url', 'dates']
        from test_support.brabble_review import attest_row
        attest_row(row)
    save([dict(row, acquisition_evidence=json.dumps(row['acquisition_evidence']))
          for row in (unstop, devfolio)], tmp_path)
    return tmp_path / 'candidates.csv'


def test_review_gate_and_hash_truth(inputs, tmp_path):
    path = reviewed_csv(inputs, tmp_path)
    with path.open(encoding='utf-8-sig', newline='') as f:
        rows = list(csv.DictReader(f))
    evidence = json.loads(rows[0]['acquisition_evidence'])
    evidence['verified_fields'] = []
    rows[0]['acquisition_evidence'] = json.dumps(evidence)
    save(rows, tmp_path)
    with pytest.raises(ValueError, match='review is required'):
        load_approved(path)
    evidence['verified_fields'] = ['organization', 'url', 'dates']
    rows[0]['acquisition_evidence'] = json.dumps(evidence)
    rows[0]['source_hash'] = 'a' * 64
    save(rows, tmp_path)
    with pytest.raises(ValueError, match='must not claim a source HTML hash'):
        load_approved(path)
    evidence['raw_record']['title'] = 'Tampered'
    with pytest.raises(ValueError, match='checksum mismatch'):
        validate_evidence(evidence)


def test_approved_api_records_are_idempotent_and_retrievable(inputs, tmp_path):
    approved, skipped = load_approved(reviewed_csv(inputs, tmp_path))
    assert skipped == 0
    engine = create_engine(f"sqlite:///{(tmp_path / 'api.db').as_posix()}",
                           connect_args={'check_same_thread': False})
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    with factory.begin() as db:
        assert stage(db, approved, 'disposable-api-reviewer')['inserted'] == 2
    with factory.begin() as db:
        assert stage(db, approved + approved, 'disposable-api-reviewer') == {'inserted': 0, 'duplicate_urls': 4}
        payload = approved[0].event.model_dump()
        payload['url'] = 'https://unstop.com/hackathons/new-provider-slug'
        changed_url = approved[0]._replace(event=EventCreate.model_validate(payload))
        from test_support.brabble_review import attest_record
        changed_url = attest_record(changed_url)
        assert stage(db, [changed_url], 'disposable-api-reviewer')['duplicate_urls'] == 1
        versions = db.scalars(select(EventVersion)).all()
        assert len(versions) == 2
        assert all('source_html_sha256' not in version.changes for version in versions)
        assert all(version.changes['acquisition']['provider'] == 'Brabble.ai' for version in versions)

    def database():
        with factory() as db:
            yield db
    previous = dict(app.dependency_overrides)
    app.dependency_overrides[get_db] = database
    try:
        with TestClient(app) as client:
            response = client.get('/events/', params={'page': 1, 'page_size': 12})
            assert response.status_code == 200
            assert response.json()['total'] == 2
            for item in response.json()['data']:
                assert item['source'] in {'Unstop', 'Devfolio'}
                assert item['start_date'] is item['end_date'] is None
                assert item['registration_deadline']
                assert item['acquisition']['provider'] == 'Brabble.ai'
                assert item['acquisition']['provider_id']
                assert item['acquisition']['attribution'] == 'Data provided by Brabble.ai'
                assert 'raw_record' not in item['acquisition']
                assert client.get(f"/events/{item['id']}").json()['data'] == item
            assert len(client.get('/events/').json()['data']) == 2
            from app.api.deps import get_current_db_user
            from app.models.core import User
            from types import SimpleNamespace
            with factory.begin() as db:
                user = User(name='Disposable Brabble Reader', email='brabble-test@example.com',
                            password_hash='not-a-real-login')
                db.add(user)
                db.flush()
                user_id = user.id
            app.dependency_overrides[get_current_db_user] = lambda: SimpleNamespace(id=user_id)
            event_id = response.json()['data'][0]['id']
            assert client.put(f'/account/saved/{event_id}').status_code == 200
            saved = client.get('/account/saved')
            assert saved.status_code == 200
            assert saved.json()['data'][0]['acquisition']['provider'] == 'Brabble.ai'
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)
        engine.dispose()


def test_provenance_failure_rolls_back_and_existing_record_is_preserved(inputs, tmp_path):
    records, _ = load_approved(reviewed_csv(inputs, tmp_path))
    engine = create_engine('sqlite://')
    Base.metadata.create_all(engine)
    def fail(*args):
        raise ValueError('API provenance failure')
    with Session(engine) as db:
        sql_event.listen(EventVersion, 'before_insert', fail)
        try:
            with pytest.raises(ValueError, match='API provenance failure'):
                stage(db, records, 'disposable-reviewer')
        finally:
            sql_event.remove(EventVersion, 'before_insert', fail)
        assert db.scalar(select(func.count()).select_from(Hackathon)) == 0
        assert db.scalar(select(func.count()).select_from(Organization)) == 0
        existing = Hackathon(title='Existing curated record', url=str(records[0].event.url), source='Manual')
        db.add(existing)
        db.commit()
        assert stage(db, records[:1], 'disposable-reviewer')['duplicate_urls'] == 1
        assert db.get(Hackathon, existing.id).title == 'Existing curated record'
        assert db.scalar(select(func.count()).select_from(EventVersion)) == 0
        db.rollback()
    engine.dispose()


def test_legacy_root_url_is_deduplicated_without_rewriting(inputs, tmp_path):
    records, _ = load_approved(reviewed_csv(inputs, tmp_path))
    engine = create_engine('sqlite://')
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        legacy = Hackathon(title='Legacy event', source='Devfolio', url=str(records[1].event.url).rstrip('/'))
        db.add(legacy)
        db.commit()
        assert stage(db, records[1:], 'disposable-reviewer')['duplicate_urls'] == 1
        assert db.scalar(select(func.count()).select_from(Hackathon)) == 1
        assert db.get(Hackathon, legacy.id).title == 'Legacy event'
    engine.dispose()
