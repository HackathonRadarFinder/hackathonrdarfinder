"""Synthetic research fixtures, never seeded into the public catalog."""
from datetime import datetime, timezone
from ai.discovery_history import as_of, backtest, export_observations
from test_discovery import db, NOW
from app.services.discovery_service import run_source

def observation(event, observed, start):
    return {'event_id': event, 'observed_at': observed, 'snapshot': {'start_date': start}}

def test_temporal_cutoff_excludes_future_observation_and_future_edition():
    rows = [observation(1, '2022-01-01', '2022-06-01'), observation(2, '2023-01-01', '2023-06-01'),
        observation(3, '2024-02-01', '2024-05-31'), observation(1, '2024-03-01', '2030-06-01')]
    cutoff = datetime(2024, 1, 1)
    known = as_of(rows, cutoff)
    assert 3 not in known and known[1]['snapshot']['start_date'] == '2022-06-01'
    report = backtest(rows, {'1': 'reviewed', '2': 'reviewed', '3': 'reviewed'}, [cutoff], datetime(2024, 2, 15))
    assert report['fold_count'] == 1 and report['mae_days'] == 0
    assert report['public_predictions_enabled'] is False

def test_current_curated_history_cannot_claim_backtest(db):
    assert run_source(db, 'curated-mvp', NOW)['status'] == 'success'
    rows = export_observations(db)
    assert len(rows) == 5 and all('checksum' in row for row in rows)
    report = backtest(rows, {}, [datetime(2025, 1, 1)], datetime.now(timezone.utc).replace(tzinfo=None))
    assert report['status'] == 'insufficient_history' and report['mae_days'] is None

def test_export_command_reads_only_and_never_overwrites(db, monkeypatch, tmp_path, capsys):
    import json
    from sqlalchemy.orm import Session
    from workers.prepare_prediction_history import main
    run_source(db, 'curated-mvp', NOW)
    output = tmp_path / 'history.json'
    monkeypatch.setattr('app.core.database.SessionLocal', lambda: Session(db.bind))
    monkeypatch.setattr('sys.argv', ['prepare', '--output', str(output),
        '--evaluation-as-of', datetime.now(timezone.utc).replace(tzinfo=None).isoformat(), '--cutoff', '2025-01-01'])
    assert main() == 0
    artifact = json.loads(output.read_text())
    assert len(artifact['observations']) == 5
    assert artifact['evaluation']['status'] == 'insufficient_history'
    import pytest
    with pytest.raises(FileExistsError):
        main()
