from datetime import datetime, timezone
import pytest
from pydantic import ValidationError
from app.services.prediction_policy import baseline_evaluation, suppression_reason
from app.schemas.prediction import PredictionRequest
from test_events_services import api


@pytest.mark.parametrize('score', [0, 0.39, float('nan'), float('inf'), -1, 1.01, True])
def test_invalid_or_subthreshold_scores_never_pass_public_policy(score):
    assert suppression_reason(score, sufficient=True, calibrated=True, promoted=True) is not None


@pytest.mark.parametrize('score', [0.40, 0.60, 0.80, 1.0])
def test_threshold_alone_does_not_replace_calibration_or_promotion(score):
    assert suppression_reason(score, sufficient=True, calibrated=False, promoted=True) == 'uncalibrated_model'
    assert suppression_reason(score, sufficient=True, calibrated=True, promoted=False) == 'unpromoted_model'
    assert suppression_reason(score, sufficient=True, calibrated=True, promoted=True) is None


@pytest.mark.parametrize('rule,reason', [('sufficient','insufficient_history'), ('fresh','stale_evidence')])
def test_evidence_quality_gates(rule, reason):
    options = dict(sufficient=True, calibrated=True, promoted=True, fresh=True)
    options[rule] = False
    assert suppression_reason(0.9, **options) == reason
    assert suppression_reason(0.9, sufficient=True, calibrated=True, promoted=True, conflict=True) == 'unresolved_conflict'


def test_calendar_envelope_is_not_exact_date_or_calibrated_probability():
    forecast = {'organization':'Fixture only', 'predicted_date':'2026-01-01', 'confidence':0.65, 'reasoning':'Test'}
    result = baseline_evaluation(forecast, ['2023-01-01','2024-01-01','2025-01-01'], datetime(2026,10,13,tzinfo=timezone.utc))
    assert result['predicted_date'] is None and result['probability'] is None
    assert result['window']['start'] < result['window']['end']
    assert result['generated_at'] == '2026-10-13T00:00:00+00:00'
    assert result['confidence_band'] == 'suppressed' and not result['public_eligible']
    assert result['model_version'].endswith('unpromoted')


def test_anonymous_and_regular_user_cannot_bypass_public_suppression(api):
    assert api.client.get('/predictions/catalog').json()['data'] == []
    for path, method in [('/predictions/evaluation','GET'),('/predictions/baseline','POST'),('/predictions/neural','POST')]:
        kwargs = {'json': {'organization':'Test','historical_dates':['2024-01-01','2025-01-01']}} if method == 'POST' else {}
        assert api.client.request(method, path, **kwargs).status_code == 401
        assert api.client.request(method, path, headers=api.headers['user'], **kwargs).status_code == 403
    assert api.client.get('/predictions/evaluation', headers=api.headers['data_scientist']).status_code == 200


@pytest.mark.parametrize('history', [['2025-02-30'], ['2025-1-1'], ['9999-01-01'], ['not a date']])
def test_invalid_and_future_history_is_rejected(history):
    with pytest.raises(ValidationError):
        PredictionRequest(organization='Test', historical_dates=history)
