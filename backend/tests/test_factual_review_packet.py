import csv
import hashlib
import json
from pathlib import Path

import pytest

from workers.build_factual_review_packet import build_packet, REQUIRED
from workers.import_reviewed_public import load_approved
from workers.prepare_brabble_pilot import prepare_pilot

BASE = Path(__file__).resolve().parents[1] / 'radar_collector/fixtures/reviewed_snapshot_20261025'


@pytest.fixture
def pilot(tmp_path):
    out = tmp_path / 'source'
    prepare_pilot(BASE / 'brabble-review/review_queue.json', BASE / 'brabble-pilot/review_decisions.json', out)
    return out / 'pilot_candidates.csv'


def inputs(tmp_path, pilot):
    rows = list(csv.DictReader(pilot.open(encoding='utf-8-sig')))
    notes = {'observed_at': '2026-10-25T18:02:28+00:00', 'records': {
        json.loads(row['acquisition_evidence'])['provider_id']: {'access': 'unit-test research observation', 'fields': {}}
        for row in rows}}
    path = tmp_path / 'observations.json'
    path.write_text(json.dumps(notes), encoding='utf-8')
    return notes, path


def test_full_worksheet_preserves_evidence_and_cannot_be_imported(tmp_path, pilot):
    before = hashlib.sha256(pilot.read_bytes()).hexdigest()
    _, observations = inputs(tmp_path, pilot)
    result = build_packet(pilot, observations, tmp_path / 'packet')
    assert result['candidate_count'] == 25 and result['field_count'] == 225
    assert result['awaiting_human_approval'] == result['human_approved'] == result['published'] == 0
    assert result['database_connected'] is False
    assert hashlib.sha256(pilot.read_bytes()).hexdigest() == before
    worksheet = tmp_path / 'packet/corrected_worksheet.csv'
    fields = list(csv.DictReader(worksheet.open(encoding='utf-8-sig')))
    assert len(fields) == 225 and {row['human_approved'] for row in fields} == {'NO'}
    assert not any(row['proposed_value'] for row in fields)
    with pytest.raises(ValueError, match='Not a candidate CSV'):
        load_approved(worksheet)
    exported = json.loads((tmp_path / 'packet/field_review.json').read_text(encoding='utf-8'))
    original = {json.loads(row['acquisition_evidence'])['provider_id']: row for row in csv.DictReader(pilot.open(encoding='utf-8-sig'))}
    assert all(row['acquisition_evidence'] == json.loads(original[row['provider_id']]['acquisition_evidence']) for row in exported)


@pytest.mark.parametrize('change', ['conflict_value', 'missing_url', 'reversed_dates', 'missing_candidate', 'future', 'unexpected_field'])
def test_research_notes_fail_closed(tmp_path, pilot, change):
    notes, path = inputs(tmp_path, pilot)
    first = next(iter(notes['records'].values()))
    check = {'status': 'verified', 'value': '2026-11-02', 'evidence_url': 'https://example.org/unit-test-only', 'note': 'Synthetic unit-test finding'}
    first['fields']['start_date'] = dict(check)
    if change == 'conflict_value':
        first['fields']['start_date']['status'] = 'conflict'
    elif change == 'missing_url':
        first['fields']['start_date'].pop('evidence_url')
    elif change == 'reversed_dates':
        first['fields']['end_date'] = dict(check, value='2026-11-01')
    elif change == 'missing_candidate':
        notes['records'].pop(next(iter(notes['records'])))
    elif change == 'future':
        notes['observed_at'] = '2999-01-01T00:00:00+00:00'
    else:
        first['fields']['human_approved'] = dict(check)
    path.write_text(json.dumps(notes), encoding='utf-8')
    with pytest.raises((ValueError, KeyError)):
        build_packet(pilot, path, tmp_path / 'packet')
    assert not (tmp_path / 'packet').exists()


def test_factual_shortlist_never_creates_human_approval(tmp_path, pilot):
    notes, path = inputs(tmp_path, pilot)
    first = next(iter(notes['records'].values()))
    for field in REQUIRED:
        first['fields'][field] = {'status': 'verified', 'value': '2026-11-02' if field.endswith('_date') else 'Synthetic test value',
            'evidence_url': 'https://example.org/unit-test-only', 'note': 'Synthetic unit-test finding'}
    path.write_text(json.dumps(notes), encoding='utf-8')
    result = build_packet(pilot, path, tmp_path / 'packet')
    assert result['awaiting_human_approval'] == 1
    assert result['human_approved'] == result['published'] == 0
