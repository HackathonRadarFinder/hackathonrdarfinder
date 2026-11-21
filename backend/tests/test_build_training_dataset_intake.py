"""INT-05: no backdating; real evidence enables folds; guard fails closed."""
from datetime import datetime
import json
from pathlib import Path

from ai.build_training_dataset import ingest_historical_editions as intake, prediction_readiness as readiness_guard, validate_historical_row as validate_row
from ai.temporal_prediction import evaluate, load_review

NOW = datetime(2026, 11, 30)


def good_row(year, **changes):
    row = {'title': f'Synthetic {year}', 'organization': 'Synthetic test organizer',
           'source': 'Synthetic fixture', 'url': f'https://example.com/research-fixture/{year}',
           'family': 'synthetic-series', 'edition': str(year), 'start_date': f'{year}-06-01',
           'observed_at': f'{year}-04-01T00:00:00', 'observation_method': 'web_archive_capture',
           'evidence_url': f'https://web.archive.org/web/{year}0401000000/https://example.com/{year}'}
    row.update(changes)
    return row


def test_each_rejection_reason():
    assert validate_row(good_row(2020), NOW) is None
    assert validate_row(good_row(2020, evidence_url=''), NOW) == 'missing_evidence_url'
    assert validate_row(good_row(2020, observation_method='guess'), NOW) == 'unknown_observation_method'
    assert validate_row(good_row(2020, evidence_url='http://x.org'), NOW) == 'evidence_url_not_https'
    assert validate_row(good_row(2020, edition='2019'), NOW) == 'edition_year_mismatch'
    assert validate_row(good_row(2020, observed_at='2027-01-01'), NOW) == 'observation_in_future'
    assert validate_row(good_row(2020, collected_at='2020-04-05T00:00:00'), NOW) == 'observed_before_collection'
    assert validate_row(good_row(2020, observed_at=''), NOW) == 'missing_observed_at'
    assert validate_row(good_row(2020, observed_at='2020-06-02'), NOW) == 'observed_after_event_start'


def test_current_repo_history_is_rejected_not_backdated():
    path = Path(__file__).resolve().parents[1] / 'data' / 'prediction-editions-v1.json'
    editions = json.loads(path.read_text(encoding='utf-8'))['historical_editions']
    result = intake(editions, datetime(2026, 11, 30))
    assert result['observations'] == []
    assert len(result['rejected']) == len(editions)


def test_duplicate_url_rejected():
    result = intake([good_row(2020), good_row(2020)], NOW)
    assert len(result['observations']) == 1
    assert result['rejection_counts'] == {'duplicate_url': 1}


def test_real_evidence_produces_folds_but_guard_stays_closed():
    result = intake([good_row(year) for year in range(2018, 2026)], NOW)
    assert not result['rejected']
    report = evaluate(result['observations'], result['review_entries'], NOW)
    assert report['dataset']['editions'] == 8
    assert len(report['folds']) > 0
    verdict = readiness_guard(report)
    assert verdict['status'] == 'research_only'
    assert verdict['public_predictions_allowed'] is False
    assert 'no_human_publication_approval' in verdict['blocking_reasons']
    assert 'no_confirmed_actual_occurrence_labels' in verdict['blocking_reasons']


def test_guard_reports_insufficient_history_on_real_repo_data():
    review, _ = load_review()
    from ai.temporal_prediction import offline_observations
    report = evaluate(offline_observations(), review, datetime(2026, 10, 13, 23))
    verdict = readiness_guard(report)
    assert verdict['status'] == 'insufficient_history'
    assert 'zero_valid_folds' in verdict['blocking_reasons']
    assert verdict['public_predictions_allowed'] is False
