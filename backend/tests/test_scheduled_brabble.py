"""Mocked authorized API -> immutable evidence -> pending review; no live requests."""
import copy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import Session
import pytest

from app.core.database import Base
from app.models.discovery import DiscoveryRun
from app.models.hackathon import Hackathon
from app.models.institution import Announcement
from app.schemas.discovery import SourcePolicy
from app.services.discovery_service import register_source, run_source
from app.services.scheduled_brabble import collect_brabble

NOW = datetime.now(timezone.utc)
FIXTURE = Path(__file__).resolve().parents[1] / 'radar_collector/fixtures/reviewed_snapshot_20261025/brabble-live'


def policy(**changes):
    return SourcePolicy(key='brabble-test', name='Brabble test API', adapter='brabble-api-v1',
        url='https://brabble.ai/api/listings', owner='Synthetic test owner', basis='Unit-test permission only',
        reference='unit-test-only', reviewed_at=NOW-timedelta(days=1), expires_at=NOW+timedelta(days=1),
        enabled=True, terms_permit=True, **changes)


@pytest.fixture
def db(tmp_path):
    engine = create_engine(f'sqlite:///{tmp_path / "scheduled.db"}')
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        register_source(session, policy(), NOW)
        yield session
    engine.dispose()


@pytest.mark.parametrize('platform', ['unstop', 'devfolio'])
def test_collection_stages_idempotently_and_never_overwrites_acquisition(db, tmp_path, monkeypatch, platform):
    import app.services.scheduled_brabble as module
    raw = json.loads((FIXTURE / (platform + '.json')).read_text(encoding='utf-8-sig'))[0]
    def fake_collect(directory, key):
        assert key == 'mock-key'
        directory.mkdir(parents=True)
        (directory / 'response_envelopes.json').write_text(json.dumps([{'acquired_at': NOW.isoformat(),
            'response': {'refreshedAt': NOW.isoformat(), 'listings': [raw]}}]), encoding='utf-8')
        return {'requests': 2, 'records': 1}
    monkeypatch.setattr(module, 'collect_api', fake_collect)
    monkeypatch.setenv('BRABBLE_API_KEY', 'mock-key')
    monkeypatch.setenv('COLLECTOR_SNAPSHOT_DIR', str(tmp_path / 'snapshots'))
    assert run_source(db, policy().key, NOW, allow_live=True)['candidates_inserted'] == 1
    candidate = db.scalar(select(Announcement))
    evidence = copy.deepcopy(candidate.evidence)
    assert candidate.status == 'pending' and candidate.payload['start_date'] is None
    assert evidence['acquisition']['raw_record'] == raw
    assert run_source(db, policy().key, NOW+timedelta(hours=6), allow_live=True)['candidate_duplicates'] == 1
    db.refresh(candidate)
    assert candidate.evidence == evidence
    assert db.scalar(select(func.count()).select_from(Hackathon)) == 0
    assert db.scalar(select(func.count()).select_from(Announcement)) == 1
    assert len(list((tmp_path / 'snapshots').iterdir())) == 2
    # Explicit synthetic reviewer decision; no publication happens in the scheduler.
    from types import SimpleNamespace
    import uuid
    from app.schemas.event import EventCreate
    from app.services.announcement_review import review
    from app.models.core import EventVersion
    actor = SimpleNamespace(sub=str(uuid.uuid4()))
    values = {**candidate.payload, 'start_date': '2027-01-20T10:00:00+00:00', 'organization': candidate.payload.get('organization') or 'Synthetic reviewed organizer only'}
    body = SimpleNamespace(decision='approved', note='Synthetic unit-test review only', event=EventCreate.model_validate(values))
    review(db, candidate.id, body, actor)
    first_version = db.scalar(select(EventVersion))
    original_changes = copy.deepcopy(first_version.changes)
    assert original_changes['acquisition'] == evidence['acquisition']
    # A changed provider counter creates a separate review revision. Republishing
    # identical event facts must append evidence rather than rewrite old history.
    raw['registered'] = (raw.get('registered') or 0) + 1
    assert run_source(db, policy().key, NOW+timedelta(hours=12), allow_live=True)['candidates_inserted'] == 1
    second = db.scalar(select(Announcement).where(Announcement.status == 'pending'))
    review(db, second.id, body, actor)
    db.refresh(first_version)
    assert first_version.changes == original_changes
    assert db.scalar(select(func.count()).select_from(EventVersion)) == 2
    assert db.scalar(select(func.count()).select_from(Hackathon)) == 1



def test_missing_credentials_logs_failure_without_publication(db, monkeypatch):
    monkeypatch.delenv('BRABBLE_API_KEY', raising=False)
    outcome = run_source(db, policy().key, NOW, allow_live=True)
    assert outcome['status'] == 'failed'
    assert outcome['error_code'] == 'api_credentials_missing'
    assert db.scalar(select(func.count()).select_from(Announcement)) == 0
    assert db.scalar(select(DiscoveryRun)).finished_at is not None


def test_live_disabled_never_calls_transport(db, monkeypatch):
    monkeypatch.setattr('app.services.scheduled_brabble.collect_api', lambda *a: pytest.fail('No transport permitted'))
    assert run_source(db, policy().key, NOW)['status'] == 'paused'


@pytest.mark.parametrize('changes', [{'url': 'https://elsewhere.example/api'}, {'institution_id': 1}, {'interval_seconds': 300}])
def test_fixed_api_endpoint_and_no_guessed_college(changes):
    values = policy().model_dump()
    values.update(changes)
    with pytest.raises(ValueError):
        SourcePolicy.model_validate(values)
