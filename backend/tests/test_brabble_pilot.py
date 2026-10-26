import copy
import json
from pathlib import Path

import pytest
from app.services.development_target import inspect_target, require_development_target
from app.services.review_evidence import validate_review
from workers.import_reviewed_public import load_approved, validate_approved
from workers.prepare_brabble_pilot import prepare_pilot
from workers.accept_brabble_pilot import accept

BASE = Path(__file__).resolve().parents[1] / 'radar_collector/fixtures/reviewed_snapshot_20261025'
PILOT = BASE / 'brabble-pilot'


def test_pilot_contains_explicit_review_not_schema_approvals(tmp_path):
    result = prepare_pilot(BASE / 'brabble-review/review_queue.json', PILOT / 'review_decisions.json', tmp_path)
    assert result == {'selected': 25, 'approved': 1, 'pending': 24,
                      'automatic_approvals': False, 'database_writes': False}
    approved, skipped = load_approved(tmp_path / 'reviewed.csv')
    assert len(approved) == 1 and skipped == 0
    event = approved[0].event
    assert event.title == 'Hacknauts 2.0' and event.organization == 'Causmic Club'
    assert event.registration_deadline is None and event.prize is None
    assert approved[0].acquisition_evidence['review']['reviewer_type'] == 'ai_assistant'
    assert approved[0].source_hash == ''
    assert load_approved(tmp_path / 'pilot_candidates.csv')[1] == 24


def test_no_explicit_decisions_means_no_approvals(tmp_path):
    ledger = json.loads((PILOT / 'review_decisions.json').read_text(encoding='utf-8'))
    ledger['decisions'] = {}
    path = tmp_path / 'no-decisions.json'
    path.write_text(json.dumps(ledger), encoding='utf-8')
    assert prepare_pilot(BASE / 'brabble-review/review_queue.json', path, tmp_path)['approved'] == 0
    assert load_approved(tmp_path / 'reviewed.csv') == ([], 0)


@pytest.mark.parametrize('change', ['no_review', 'tampered_prize', 'missing_check', 'unresolved_conflict', 'date_precision'])
def test_approved_record_requires_bound_complete_review(change):
    row = load_approved(PILOT / 'reviewed.csv')[0][0]
    evidence = copy.deepcopy(row.acquisition_evidence)
    event = row.event
    if change == 'no_review':
        evidence.pop('review')
    elif change == 'tampered_prize':
        event = event.model_copy(update={'prize': 'Unverified new amount'})
    elif change == 'missing_check':
        evidence['review']['checks'].pop('organization')
    elif change == 'unresolved_conflict':
        evidence['review']['unresolved_conflicts'] = ['Conflicting deadline']
    else:
        row = row._replace(date_precision='exact')
    with pytest.raises(ValueError):
        validate_approved(row._replace(event=event, acquisition_evidence=evidence))


@pytest.mark.parametrize('url,environment,expected', [
    ('postgresql://u:p@production.example/hackathons', 'production', 'hackathons'),
    ('postgresql://u:p@production.example/hackathons', 'development', 'hackathons'),
    ('postgresql://u:p@localhost/hackathon_radar', 'development', 'different_database'),
    ('postgresql://u:p@localhost/production', 'development', 'production'),
    ('sqlite://', 'development', ':memory:'),
])
def test_production_or_ambiguous_target_refused(url, environment, expected):
    with pytest.raises(ValueError):
        require_development_target(url, environment, expected)


def test_development_target_report_never_exposes_credentials():
    result = inspect_target('postgresql://privateuser:privatesecret@db/hackathon_radar', 'development', 'hackathon_radar')
    assert result['development_config_verified'] and not result['connected']
    assert not result['server_identity_verified']
    assert 'private' not in json.dumps(result)
    with pytest.raises(ValueError, match='--expect-database'):
        require_development_target('postgresql://u:p@db/hackathon_radar', 'development', None)


def test_real_reviewed_pilot_acceptance(tmp_path):
    report = accept(PILOT / 'reviewed.csv', tmp_path)
    assert report['dry_run'] == {'inserted': 1, 'duplicate_urls': 0}
    assert report['imported'] == {'inserted': 1, 'duplicate_urls': 0}
    assert report['repeat'] == {'inserted': 0, 'duplicate_urls': 1}
    assert report['pagination'] == report['detail_endpoints'] == 'passed'
    assert report['disposable_database_removed']
    assert not report['configured_database_connected']


def test_ai_factual_review_is_not_human_approval():
    from app.services.review_evidence import require_human_approval
    row = load_approved(PILOT / 'reviewed.csv')[0][0]
    with pytest.raises(ValueError, match='AI verification is not human approval'):
        require_human_approval(row)
    assert row.acquisition_evidence['review']['reviewer_type'] == 'ai_assistant'


def test_separate_human_attestation_preserves_ai_identity_and_binds_facts():
    from app.services.review_evidence import require_human_approval, event_digest
    row = load_approved(PILOT / 'reviewed.csv')[0][0]
    evidence = copy.deepcopy(row.acquisition_evidence)
    # Pure test object, never persisted as actual human approval.
    evidence['human_approval'] = {'reviewer_type': 'human', 'decision': 'approved',
        'reviewer': 'Synthetic human signoff example for unit test', 'note': 'Test only',
        'approved_at': '2026-10-25T18:02:28+00:00', 'date_precision': row.date_precision,
        'event_sha256': event_digest(row.event)}
    candidate = row._replace(acquisition_evidence=evidence)
    require_human_approval(candidate)
    assert candidate.acquisition_evidence['review']['reviewer_type'] == 'ai_assistant'
    evidence['human_approval']['event_sha256'] = '0' * 64
    with pytest.raises(ValueError, match='bound to the reviewed facts'):
        require_human_approval(candidate)


def test_cli_apply_rejects_ai_only_before_opening_database(monkeypatch, capsys):
    from app.core.config import settings
    import workers.import_reviewed_public as importer
    import sys
    monkeypatch.setattr(settings, 'DATABASE_URL', 'postgresql+psycopg://u:p@localhost/hackathon_radar')
    monkeypatch.setattr(settings, 'ENVIRONMENT', 'development')
    opened = []
    class ForbiddenSession:
        @staticmethod
        def begin():
            opened.append(True)
            raise AssertionError('No database connection is permitted')
    monkeypatch.setattr(importer, 'SessionLocal', ForbiddenSession)
    monkeypatch.setattr(sys, 'argv', ['importer', str(PILOT / 'reviewed.csv'), '--apply',
        '--reviewed-by', 'An operator name is not human signoff', '--expect-database', 'hackathon_radar'])
    assert importer.main() == 1
    assert 'Human approval is required' in capsys.readouterr().out
    assert opened == []


def test_review_attestation_survives_absent_optional_fields_but_binds_new_facts():
    from app.services.review_evidence import event_digest
    row = load_approved(PILOT / 'reviewed.csv')[0][0]
    assert event_digest(row.event) == row.acquisition_evidence['review']['event_sha256']
    changed = row.event.model_copy(update={'state': 'Punjab'})
    assert event_digest(changed) != event_digest(row.event)
    with pytest.raises(ValueError, match='Reviewed facts changed'):
        validate_approved(row._replace(event=changed))
