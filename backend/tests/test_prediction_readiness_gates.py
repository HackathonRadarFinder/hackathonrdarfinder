"""INT-05 / issue #204: readiness metrics are exposed and forecasts stay suppressed."""
from datetime import datetime

from ai.build_training_dataset import ingest_historical_editions
from ai.temporal_prediction import (MIN_CALIBRATION, MIN_COVERAGE_TEST, evaluate, load_review,
                                    offline_observations, readiness, readiness_gates)


def real_repo_report():
    review, _ = load_review()
    return evaluate(offline_observations(), review, datetime(2026, 10, 13, 23))


def fixture_row(year):
    return {'title': f'Synthetic {year}', 'organization': 'Synthetic test organizer', 'source': 'Synthetic fixture',
            'url': f'https://example.com/research-fixture/{year}', 'family': 'synthetic-series',
            'edition': str(year), 'start_date': f'{year}-06-01', 'observed_at': f'{year}-04-01T00:00:00',
            'observation_method': 'web_archive_capture',
            'evidence_url': f'https://web.archive.org/web/{year}0401000000/https://example.com/{year}'}


def test_readiness_exposes_gate_metrics_and_keeps_old_keys():
    result = readiness(real_repo_report())
    for key in ('status', 'reviewed_editions', 'recurring_series', 'evaluated_editions', 'reason'):
        assert key in result
    assert result['valid_folds'] == 0
    assert result['min_calibration_samples'] == MIN_CALIBRATION
    assert result['min_coverage_test_editions'] == MIN_COVERAGE_TEST
    assert 'zero_valid_folds' in result['blocking_reasons']
    assert result['public_predictions_enabled'] is False


def test_forecasts_are_suppressed_without_calibration():
    report = real_repo_report()
    assert report['public_predictions_enabled'] is False
    for candidate in report['internal_candidates']:
        assert candidate['public_eligible'] is False
        assert candidate['confidence'] is None and candidate['window'] is None
        assert candidate['suppression_reason'] == 'uncalibrated_and_unpromoted'


def test_gates_never_enable_publication_even_with_folds():
    rows = [fixture_row(year) for year in range(2018, 2026)]
    result = ingest_historical_editions(rows, datetime(2026, 11, 30))
    report = evaluate(result['observations'], result['review_entries'], datetime(2026, 11, 30))
    assert report['folds']
    gates = readiness_gates(report)
    assert gates['public_predictions_allowed'] is False
    assert readiness(report)['public_predictions_enabled'] is False
    assert any(reason.startswith('fewer_than_') for reason in gates['blocking_reasons'])
