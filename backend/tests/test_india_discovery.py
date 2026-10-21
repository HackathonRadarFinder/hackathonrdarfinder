"""Controlled multi-state offline pilot; synthetic institutions are never national coverage."""
from datetime import datetime, timedelta, timezone
import json
from types import SimpleNamespace
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from app.core.database import Base, get_db
from app.main import app
from app.models.core import User, Role, EventVersion
from app.models.hackathon import Hackathon
from app.models.institution import Institution, Announcement
from app.models.discovery import DiscoverySource, DiscoveryEvidence, DiscoveryLock
from app.schemas.institution import DirectoryImport
from app.schemas.discovery import SourcePolicy
from app.services.institution_service import import_directory, coverage
from app.services.discovery_service import register_source, run_source
from app.services.announcement_extraction import extract
from app.core.security import create_access_token

NOW = datetime.now(timezone.utc)


def export():
    return dict(provider='aishe', source_url='https://dashboard.aishe.gov.in/hedirectory',
        reuse_permitted=True, license_reference='OFFLINE TEST PERMISSION ONLY', reviewed_by='Offline test operator',
        records=[dict(identifier=f'AISHE:TEST-{i}', name=f'Synthetic Pilot College {i}', state=state,
            category='Engineering college', city=city, district=city, website=f'https://pilot{i}.example.org/',
            website_evidence_url=f'https://dashboard.aishe.gov.in/hedirectory?test={i}',
            website_verified_at=NOW.isoformat(), verified_at=NOW.isoformat(),
            event_urls=[f'https://pilot{i}.example.org/events'])
            for i, (state, city) in enumerate([('Telangana', 'Hyderabad'), ('Tamil Nadu', 'Chennai'),
                ('Maharashtra', 'Pune'), ('Assam', 'Guwahati')])])


@pytest.fixture
def db(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'india.db'}", connect_args={'check_same_thread': False})
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


def setup_source(db, index=0, **changes):
    import_directory(db, export()); db.commit()
    inst = db.scalar(select(Institution).where(Institution.identifier == f'AISHE:TEST-{index}'))
    policy = SourcePolicy(key=f'pilot-{index}', name=inst.name, adapter='official-html-v1',
        institution_id=inst.id, url=inst.event_urls[0], enabled=True, owner='Offline test reviewer',
        basis='Test fixtures only; not a real website permission', reference='offline-test',
        reviewed_at=NOW-timedelta(days=1), expires_at=NOW+timedelta(days=10), terms_permit=True,
        **changes)
    register_source(db, policy, NOW)
    return inst, policy


def document(title='Pilot Hackathon', start='2026-11-10T09:00:00+05:30'):
    return '<html><script type="application/ld+json">' + json.dumps({'@type':'Event',
        'name': title, 'description':'A hackathon announcement fixture', 'startDate': start,
        'endDate':'2026-11-11T18:00:00+05:30', 'url':'https://pilot0.example.org/hackathon',
        'eventAttendanceMode':'https://schema.org/OfflineEventAttendanceMode',
        'registrationUrl':'https://pilot0.example.org/register', 'eligibility':'Students', 'prize':'Not a cash-prize claim'}) + '</script></html>'


def collector(policy):
    return [], 0, dict(announcements=extract(document(), policy.adapter, policy.url),
        checksum='a'*64, document_url=policy.url, adapter_version=policy.adapter, transport='offline-test')


def actor(db, admin=True):
    user = User(name='Test reviewer', email=f'{admin}@example.org', password_hash='unused')
    if admin:
        user.roles.append(Role(name='administrator'))
    db.add(user); db.commit()
    return {'Authorization':'Bearer '+create_access_token(subject=str(user.id), role='administrator')}


def test_incremental_directory_atomic_stale_and_revocation(db):
    assert import_directory(db, export())['inserted'] == 4
    db.commit()
    assert import_directory(db, export())['unchanged'] == 4
    inst, policy = setup_source(db)
    updated = export()
    updated['records'] = [updated['records'][0]]
    updated['records'][0].update(name='Changed verified name', verified_at=(NOW+timedelta(microseconds=1)).isoformat())
    assert import_directory(db, updated)['updated'] == 1
    db.commit()
    assert db.scalar(select(DiscoverySource)).enabled is False
    assert import_directory(db, export())['stale'] == 1
    assert coverage(db)['institutions_indexed'] == 4
    assert coverage(db)['approved_sources'] == 0


@pytest.mark.parametrize('bad', ['permission', 'unofficial', 'website', 'private', 'event_origin', 'duplicate', 'future'])
def test_directory_invalid_batches_rejected(db, bad):
    body = export()
    if bad == 'permission': body['reuse_permitted'] = False
    if bad == 'unofficial': body['source_url'] = 'https://unverified.example.org/list'
    if bad == 'website': body['records'][0]['website_evidence_url'] = None
    if bad == 'private': body['records'][0]['website'] = 'https://127.0.0.1/'
    if bad == 'event_origin': body['records'][0]['event_urls'] = ['https://other.example.org/events']
    if bad == 'duplicate': body['records'].append(body['records'][0])
    if bad == 'future': body['records'][0]['verified_at'] = (NOW+timedelta(days=1)).isoformat()
    with pytest.raises(ValueError): import_directory(db, body)
    assert db.scalar(select(func.count()).select_from(Institution)) == 0


def test_extract_formats_missing_dates_and_malicious_xml():
    row = extract(document(), 'official-html-v1', 'https://pilot0.example.org/events')[0]
    assert row['start_date'] == '2026-11-10T09:00:00+05:30'
    assert row['registration_deadline'] is None
    assert row['eligibility'] == 'Students'
    day = extract(document(start='2026-11-10'), 'official-html-v1', 'https://pilot0.example.org/events')[0]
    assert day['start_date'] is None and day['_raw_dates']['startDate'] == '2026-11-10'
    assert 'day_precision_start_date' in day['_issues']
    for adapter, content in [('rss-v1', '<rss><channel><item><title>Campus Hackathon</title><link>https://pilot0.example.org/hack</link></item></channel></rss>'),
        ('rss-v1', '<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Hackathon</title><link href="https://pilot0.example.org/hack"/></entry></feed>'),
        ('sitemap-v1', '<urlset><url><loc>https://pilot0.example.org/hackathon</loc></url></urlset>'),
        ('events-json-v1', '{"events":[{"name":"Campus Hackathon"}]}')]:
        assert len(extract(content, adapter, 'https://pilot0.example.org/feed')) == 1
    with pytest.raises(Exception):
        extract('<!DOCTYPE rss [<!ENTITY x SYSTEM "file:///etc/passwd">]><rss>&x;</rss>', 'rss-v1', 'https://example.org/')
    assert extract('<h1>Admissions open</h1>', 'official-html-v1', 'https://example.org/') == []
    unsafe = extract('<urlset><url><loc>https://127.0.0.1/hackathon</loc></url></urlset>', 'sitemap-v1', 'https://example.org/')
    assert unsafe == []


def test_permission_before_collect_and_explicit_url_scope(db):
    inst, policy = setup_source(db)
    with pytest.raises(ValueError): register_source(db, policy.model_copy(update={'url':'https://pilot0.example.org/not-reviewed'}), NOW)
    assert run_source(db, policy.key, NOW, collector=lambda _: pytest.fail('No implicit live access'))['error_code'] == 'live_collection_disabled'
    assert db.scalar(select(func.count()).select_from(Announcement)) == 0


def test_reviewed_publication_idempotence_filters_history_and_auth(db):
    inst, policy = setup_source(db)
    result = run_source(db, policy.key, NOW, allow_live=True, collector=collector)
    assert result['candidates_inserted'] == 1 and result['inserted'] == 0
    assert run_source(db, policy.key, NOW+timedelta(hours=6), allow_live=True, collector=collector)['candidate_duplicates'] == 1
    assert db.scalar(select(func.count()).select_from(Hackathon)) == 0
    candidate = db.scalar(select(Announcement))
    headers = actor(db)
    ordinary = actor(db, False)
    app.dependency_overrides[get_db] = lambda: db
    try:
        with TestClient(app) as client:
            assert client.get('/admin/discovery/coverage').status_code == 401
            assert client.get('/admin/discovery/announcements', headers=ordinary).status_code == 403
            body = dict(decision='approved', note='Verified all event facts against the offline fixture.', event={
                **candidate.payload, 'state':inst.state, 'start_date':'2026-11-10T09:00:00+05:30'})
            invalid = {**body, 'event':{**body['event'], 'url':'https://other.example.org/event'}}
            assert client.post(f'/admin/discovery/announcements/{candidate.id}/review', headers=headers, json=invalid).status_code == 422
            response = client.post(f'/admin/discovery/announcements/{candidate.id}/review', headers=headers, json=body)
            assert response.status_code == 200, response.text
            assert client.post(f'/admin/discovery/announcements/{candidate.id}/review', headers=headers, json=body).status_code == 409
            page = client.get('/events/', params={'state':'telangana','institution_id':inst.id}).json()
            assert page['total'] == 1 and page['data'][0]['start_date'] == '2026-11-10T03:30:00'
            assert client.get('/events/', params={'state':'Assam'}).json()['total'] == 0
            event_id = response.json()['event_id']
            assert len(client.get(f'/events/{event_id}/discovery').json()['data']['versions']) == 1
            assert client.get('/institutions?state=Telangana').json()['total'] == 1
            assert client.get('/admin/discovery/coverage', headers=headers).json()['validated_events'] == 1
    finally:
        app.dependency_overrides.clear()
    assert db.scalar(select(func.count()).select_from(DiscoveryLock)) == 0


def test_transport_cache_and_denial(db, monkeypatch):
    inst, policy = setup_source(db)
    from app.services import nationwide_collection as module
    calls = []
    result = SimpleNamespace(status='success', robots_allowed=True, content_type='text/html',
        raw_content=document(), final_url=policy.url, fetched_at=NOW.isoformat())
    # Import the governed package through its production factory, then inject offline collection.
    module.manager()
    monkeypatch.setattr(module, 'manager', lambda: SimpleNamespace(collect=lambda source: (calls.append(source) or result)))
    module._cache.clear()
    assert module.collect_announcements(policy)[2]['cache_hit'] is False
    assert module.collect_announcements(policy)[2]['cache_hit'] is True
    assert len(calls) == 1
    module._cache.clear(); result.robots_allowed = False
    with pytest.raises(ValueError): module.collect_announcements(policy)


def test_four_state_offline_pilot_and_reviewed_source_facts(db):
    for index in range(4):
        institution, policy = setup_source(db, index)
        def collect(current):
            html = document().replace('pilot0', f'pilot{index}')
            return [], 0, dict(announcements=extract(html, current.adapter, current.url),
                checksum='b'*64, document_url=current.url, adapter_version=current.adapter, transport='offline-test')
        assert run_source(db, policy.key, NOW, allow_live=True, collector=collect)['candidates_inserted'] == 1
    result = coverage(db)
    assert result['institutions_indexed'] == result['approved_sources'] == result['events_discovered'] == 4
    assert result['validated_events'] == 0
    assert len(result['institutions_by_state']) == 4
    # Re-encode already reviewed real source facts, not a captured HTML page or new live discovery.
    from pathlib import Path
    manifest = json.loads((Path(__file__).resolve().parents[1]/'data'/'curated-mvp-20261013.json').read_text(encoding='utf-8'))
    historical = [dict(name=row['title'], startDate=row['start_date'], endDate=row['end_date'], url=row['url'])
                  for row in manifest if row['title'].startswith('Megathon')]
    extracted = extract(json.dumps({'events':historical}), 'events-json-v1', 'https://www.iiit.ac.in/')
    assert [row['start_date'] for row in extracted] == [row['startDate'] for row in historical]
    assert len(extracted) == 3


def test_csv_explicit_mapping_validation_without_database(tmp_path):
    from workers.import_institutions import load_export
    path = tmp_path / 'export.csv'
    path.write_text('Code,College,State,Category,Verified\nAISHE:TEST-CSV,Synthetic CSV College,Assam,College,'+NOW.isoformat()+'\n')
    metadata = {key:value for key,value in export().items() if key != 'records'}
    mapping = dict(identifier='Code', name='College', state='State', category='Category', verified_at='Verified')
    body = load_export(path, metadata, mapping)
    assert body.records[0].website is None
    assert len(body.records) == 1
    with pytest.raises(ValueError): load_export(path)


@pytest.mark.parametrize('url', ['http://example.org/', 'https://localhost/', 'https://127.0.0.1/',
    'https://169.254.169.254/', 'https://user:pass@example.org/', 'https://example.org:444/', 'file:///etc/passwd'])
def test_source_url_ssrf_validation(url):
    with pytest.raises(ValueError):
        SourcePolicy(key='unsafe', name='Unsafe test', adapter='rss-v1', url=url, owner='Test',
            basis='Test only', reference='Offline', reviewed_at=NOW, expires_at=NOW+timedelta(days=1))


@pytest.mark.parametrize('blocker', ['revoked', 'newer', 'busy', 'reconfigured'])
def test_publication_guards_never_publish_stale_revoked_or_busy(db, blocker):
    from app.services.announcement_review import review
    from app.api.routes.institutions import ReviewDecision
    from fastapi import HTTPException
    from app.models.discovery import DiscoveryRun
    institution, policy = setup_source(db)
    run_source(db, policy.key, NOW, allow_live=True, collector=collector)
    candidate = db.scalar(select(Announcement))
    reviewer = User(name='Reviewer', email='guards@example.org', password_hash='unused')
    db.add(reviewer); db.commit()
    source = db.scalar(select(DiscoverySource))
    if blocker == 'revoked': source.enabled = False
    if blocker == 'reconfigured': source.config = {**source.config, 'url':'https://pilot0.example.org/changed'}
    if blocker == 'newer':
        db.add(Announcement(source_id=candidate.source_id, institution_id=institution.id,
            fingerprint='f'*64, payload=candidate.payload, evidence=candidate.evidence, status='pending',
            observed_at=candidate.observed_at+timedelta(seconds=1), last_seen_at=candidate.last_seen_at))
    if blocker == 'busy':
        run = DiscoveryRun(source_id=candidate.source_id, started_at=NOW.replace(tzinfo=None), status='running', metrics={})
        db.add(run); db.flush(); db.add(DiscoveryLock(id=1, run_id=run.id))
    db.commit()
    body = ReviewDecision.model_validate(dict(decision='approved', note='Verified offline test facts.', event={
        **candidate.payload, 'state':institution.state}))
    with pytest.raises(HTTPException) as exc:
        review(db, candidate.id, body, SimpleNamespace(sub=str(reviewer.id)))
    assert exc.value.status_code == 409
    assert db.scalar(select(func.count()).select_from(Hackathon)) == 0
    db.rollback()
