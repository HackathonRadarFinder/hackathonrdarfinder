"""Synthetic fixtures test arithmetic only; real evidence asserts unavailable metrics."""
from datetime import datetime, timedelta, timezone
import json
import pytest
from ai.temporal_prediction import (evaluate, load_review, offline_observations, prepare_dataset,
    calibrated_radius, historical_observations, readiness)
from test_discovery import db, NOW


def fixture_records(years=range(2000, 2006)):
    observations, review = [], {}
    for year in years:
        url = f'https://example.com/research-fixture/{year}'
        entry = {'family': 'synthetic-series', 'edition': str(year), 'organization': 'Synthetic test organizer',
            'title': f'Synthetic {year}', 'source': 'Synthetic fixture'}
        review[url] = entry
        observations.append({'event_id': str(year), 'observed_at': f'{year}-05-01T00:00:00',
            'checksum': 'a'*64, 'document_url': url, 'source_id': 'test', 'adapter_version': 'test',
            'snapshot': {'title': entry['title'], 'source': entry['source'], 'url': url,
                'scraped_at': f'{year}-05-01', 'start_date': f'{year}-06-01'}})
    return observations, review


def test_real_manifest_patterns_without_invented_backtest():
    review, checksum = load_review()
    report = evaluate(offline_observations(), review, datetime(2026, 10, 13, 23))
    assert len(checksum) == 64
    assert report['dataset']['editions'] == 5 and report['dataset']['recurring_series'] == 1
    series = next(row for row in report['series'] if row['family'] == 'megathon-iiit-hyderabad')
    assert series['interval_days'] == [1085, 364]
    assert series['seasonal_month_counts'] == {'10': 3}
    assert series['observed_year_gaps'] == [3, 1]
    assert report['folds'] == [] and report['status'] == 'insufficient_history'
    for metric in report['metrics'].values():
        assert metric['announced_date_mae_days'] is None
        assert metric['date_window_coverage'] is None and metric['confidence'] is None
    assert readiness(report)['public_predictions_enabled'] is False
    assert all(row['confidence'] is None and not row['public_eligible'] for row in report['internal_candidates'])


def test_historical_dataset_exactly_matches_source_records():
    from pathlib import Path
    import hashlib
    root = Path(__file__).resolve().parents[1]
    original = json.loads((root/'data/curated-mvp-20261013.json').read_text(encoding='utf-8'))
    historical = json.loads((root/'data/prediction-editions-v1.json').read_text(encoding='utf-8'))
    canonical = json.dumps(original, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()
    assert historical['source_manifest_canonical_sha256'] == hashlib.sha256(canonical).hexdigest()
    assert len(historical['historical_editions']) == 3
    assert len(historical_observations(historical)) == 3
    for edition in historical['historical_editions']:
        source = next(row for row in original if row['url'] == edition['url'])
        assert all(edition[key] == value for key, value in source.items())
        assert edition['observed_at'] == source['scraped_at']
        assert edition['actual_occurrence_confirmed'] is False
    corrupted = json.loads(json.dumps(historical))
    corrupted['historical_editions'][0]['observed_at'] = '2020-01-01'
    with pytest.raises(ValueError):
        historical_observations(corrupted)


def test_unreviewed_bad_provenance_future_and_duplicate_editions_quarantined():
    rows, review = fixture_records()
    duplicate = {**rows[0], 'event_id': 'duplicate'}
    bad = {**rows[1], 'checksum': 'not-a-checksum'}
    future = {**rows[2], 'observed_at': '2030-01-01'}
    unreviewed = {**rows[3], 'snapshot': {**rows[3]['snapshot'], 'url': 'https://example.com/unreviewed'}}
    accepted, rejected = prepare_dataset([rows[0], duplicate, bad, future, unreviewed], review, datetime(2006, 1, 1))
    assert accepted == []
    assert rejected['future_observation'] == rejected['unreviewed_series'] == 1
    assert rejected['invalid_or_conflicting_record'] == 2


def test_model_comparison_has_only_past_features_and_no_heuristic_confidence():
    rows, review = fixture_records()
    report = evaluate(rows, review, datetime(2007, 1, 1))
    assert set(report['metrics']) == {'existing_mean_gap', 'median_gap', 'last_gap', 'seasonal_anniversary', 'neural'}
    assert report['metrics']['existing_mean_gap']['held_out_editions'] == 4
    assert report['metrics']['seasonal_anniversary']['announced_date_mae_days'] == 0
    for fold in report['folds']:
        assert fold['event_id'] not in fold['history_event_ids']
        assert all(int(event) < int(fold['event_id']) for event in fold['history_event_ids'])
        assert fold['window'] is None and fold['covered'] is None
    assert report['metrics']['existing_mean_gap']['actual_occurrence_mae_days'] is None
    assert report['public_predictions_enabled'] is False


def test_neural_refits_receive_only_earlier_available_labels(monkeypatch):
    from ai import neural_prediction_model as neural
    fits = []
    class TestModel:
        def set_params(self, **values):
            assert values == {'neural_network__early_stopping': False}
        def fit(self, features, labels):
            fits.append(len(labels))
            assert len(features) == len(labels) and len(labels) >= 30
        def predict(self, features):
            return [365]
    monkeypatch.setattr(neural, 'create_model', TestModel)
    rows, review = fixture_records(range(1970, 2005))
    report = evaluate(rows, review, datetime(2006, 1, 1), neural=True)
    assert fits == [30, 31, 32]
    assert report['metrics']['neural']['held_out_editions'] == 3
    assert report['metrics']['neural']['confidence'] is None


def test_late_observed_history_and_date_revisions_cannot_leak():
    rows, review = fixture_records()
    future_revision = {**rows[0], 'observed_at': '2007-01-01',
        'snapshot': {**rows[0]['snapshot'], 'start_date': '2000-12-31'}}
    original = evaluate(rows, review, datetime(2006, 12, 31))
    assert evaluate([*rows, future_revision], review, datetime(2006, 12, 31))['folds'] == original['folds']
    late = [{**row, 'observed_at': '2006-12-01'} for row in rows]
    assert evaluate(late, review, datetime(2006, 12, 31))['folds'] == []


def test_residual_calibration_and_coverage_are_out_of_sample():
    assert calibrated_radius([1]*29) is None
    assert calibrated_radius(list(range(30))) == 24
    rows, review = fixture_records(range(1970, 2025))
    report = evaluate(rows, review, datetime(2026, 1, 1))
    metric = report['metrics']['seasonal_anniversary']
    assert metric['coverage_test_editions'] == 23 and metric['date_window_coverage'] == 1
    assert metric['confidence'] is None and report['publication_approved'] is False
    for fold in report['folds']:
        if fold['window']:
            assert fold['calibration_samples'] >= 30


def test_already_announced_target_not_scored_and_no_duplicate_cutoff_inflation():
    rows, review = fixture_records()
    report = evaluate(rows, review, datetime(2007, 1, 1), ['2004-04-01', '2004-04-02'])
    assert report['metrics']['existing_mean_gap']['held_out_editions'] == 1
    early = [{**row, 'observed_at': '1999-01-01', 'snapshot': {**row['snapshot'], 'scraped_at': '1999-01-01'}} for row in rows]
    assert evaluate(early, review, datetime(2007, 1, 1))['folds'] == []


def test_curated_export_cannot_backdate_or_change_reviewed_source_facts():
    rows = offline_observations()
    review, _ = load_review()
    backdated = [{**row, 'observed_at': '2020-01-01'} for row in rows]
    assert evaluate(backdated, review, datetime(2026, 10, 13, 23))['dataset']['editions'] == 0
    changed = [{**row, 'snapshot': {**row['snapshot'], 'scraped_at': '2020-01-01'}} for row in rows]
    assert evaluate(changed, review, datetime(2026, 10, 13, 23))['dataset']['editions'] == 0


def test_actual_errors_require_confirmed_reviewed_outcomes():
    rows, review = fixture_records()
    outcome = {'source_url': rows[2]['snapshot']['url'], 'confirmed_actual': True,
        'review_basis': 'Synthetic test-only occurrence evidence', 'actual_start_date': '2002-06-05',
        'observed_at': '2002-06-06'}
    report = evaluate(rows, review, datetime(2007, 1, 1), actual_outcomes=[outcome])
    metric = report['metrics']['seasonal_anniversary']
    assert metric['actual_occurrence_mae_days'] == 4 and metric['actual_test_editions'] == 1
    assert metric['announced_date_mae_days'] == 0
    assert metric['actual_date_window_coverage'] is None
    with pytest.raises(ValueError):
        evaluate(rows, review, datetime(2007, 1, 1), actual_outcomes=[{**outcome, 'confirmed_actual': False}])
    with pytest.raises(ValueError):
        evaluate(rows, review, datetime(2007, 1, 1), actual_outcomes=[{**outcome, 'observed_at': '2030-01-01'}])


def test_actual_window_coverage_is_distinct_from_announced_date_coverage():
    rows, review = fixture_records(range(1970, 2025))
    outcomes = [{'source_url': row['snapshot']['url'], 'confirmed_actual': True,
        'review_basis': 'Synthetic fixture only', 'actual_start_date': f"{row['event_id']}-06-02",
        'observed_at': f"{row['event_id']}-06-03"} for row in rows]
    report = evaluate(rows, review, datetime(2026, 1, 1), actual_outcomes=outcomes)
    metric = report['metrics']['seasonal_anniversary']
    assert metric['date_window_coverage'] == 1 and metric['actual_date_window_coverage'] == 0
    assert metric['actual_occurrence_mae_days'] == 1 and metric['confidence'] is None
    assert not report['public_predictions_enabled']


def test_offline_evaluation_does_not_require_database_configuration(tmp_path):
    import os
    from pathlib import Path
    import subprocess
    import sys
    environment = {key: value for key, value in os.environ.items() if key not in {'DATABASE_URL', 'SECRET_KEY'}}
    environment['DEBUG'] = 'unusable-setting-proves-app-config-is-not-loaded'
    root = Path(__file__).resolve().parents[1]
    output = tmp_path/'independent-research.json'
    result = subprocess.run([sys.executable, '-B', '-m', 'workers.evaluate_predictions', '--output', str(output)],
        cwd=root, env=environment, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert json.loads(output.read_text())['evaluation']['status'] == 'insufficient_history'


def test_offline_cli_outputs_real_data_without_db_or_overwrite(monkeypatch, tmp_path, capsys):
    from workers.evaluate_predictions import main
    output = tmp_path / 'research.json'
    monkeypatch.setattr('sys.argv', ['evaluate', '--output', str(output)])
    assert main() == 0
    artifact = json.loads(output.read_text())
    assert artifact['evaluation']['dataset']['editions'] == 5
    assert artifact['evaluation']['metrics']['existing_mean_gap']['held_out_editions'] == 0
    with pytest.raises(FileExistsError):
        main()


def test_temporal_api_protected_and_public_readiness_no_forecasts(db):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.core.database import get_db
    from app.core.security import create_access_token
    from app.models.core import User, Role
    from app.services.discovery_service import run_source
    run_source(db, 'curated-mvp', NOW)
    user = User(name='Research reviewer', email='reviewer@example.com', password_hash='test')
    db.add(user); db.commit()
    headers = {'Authorization': 'Bearer '+create_access_token(subject=str(user.id), role='administrator')}
    app.dependency_overrides[get_db] = lambda: db
    try:
        with TestClient(app) as client:
            assert client.get('/predictions/research').status_code == 401
            assert client.get('/predictions/research', headers=headers).status_code == 403
            user.roles.append(Role(name='data_scientist')); db.commit()
            response = client.get('/predictions/research', headers=headers)
            assert response.status_code == 200
            report = response.json()['data']
            assert report['dataset']['editions'] == 5 and report['folds'] == []
            public = client.get('/predictions/readiness').json()['data']
            assert public['reviewed_editions'] == 5 and public['recurring_series'] == 1
            assert 'predicted_date' not in public and 'confidence' not in public
            assert client.get('/predictions/catalog').json()['data'] == []
    finally:
        app.dependency_overrides.clear()
