"""Observation-aware research data; no model publication or guessed event families."""
from datetime import datetime
from statistics import mean, median
from sqlalchemy import select
from app.models.discovery import DiscoveryEvidence


def export_observations(db):
    """Read provenance and event snapshots only; never export accounts or preferences."""
    rows = db.scalars(select(DiscoveryEvidence).order_by(
        DiscoveryEvidence.observed_at, DiscoveryEvidence.id)).all()
    return [{'event_id': row.hackathon_id, 'source_id': str(row.source_id),
        'observed_at': row.observed_at.isoformat(), 'checksum': row.checksum,
        'document_url': row.document_url, 'adapter_version': row.adapter_version,
        'snapshot': row.snapshot} for row in rows]


def as_of(observations, cutoff):
    """Latest version actually observed by cutoff, one row per edition."""
    result = {}
    for row in sorted(observations, key=lambda value: value['observed_at']):
        if datetime.fromisoformat(row['observed_at']) <= cutoff:
            result[row['event_id']] = row
    return result


def backtest(observations, families, cutoffs, evaluation_as_of):
    """Explicit reviewed edition families; labels are source-announced dates.

    No inferred organizer-level grouping, synthetic catalog additions, confidence
    claims or public approval. Latest observed labels are bounded by evaluation time.
    """
    labels = as_of(observations, evaluation_as_of)
    folds = []
    for cutoff in sorted(set(cutoffs)):
        if cutoff >= evaluation_as_of:
            raise ValueError('Cutoff must precede evaluation time')
        known = as_of(observations, cutoff)
        for event_id, target in labels.items():
            if event_id in known:
                continue  # An already announced edition is not an unseen-date forecast.
            family = families.get(str(event_id))
            date = target['snapshot'].get('start_date')
            if not family or not date:
                continue
            target_date = datetime.fromisoformat(date)
            if target_date <= cutoff:
                continue
            history = []
            for previous_id, row in known.items():
                start = row['snapshot'].get('start_date')
                if previous_id != event_id and families.get(str(previous_id)) == family and start:
                    previous_date = datetime.fromisoformat(start)
                    if previous_date < cutoff:
                        history.append(previous_date)
            history = sorted(set(history))
            if len(history) < 2:
                continue
            intervals = [(right-left).total_seconds() for left, right in zip(history, history[1:])]
            from datetime import timedelta
            predicted = history[-1] + timedelta(seconds=median(intervals))
            folds.append({'event_id': event_id, 'family': family, 'cutoff': cutoff.isoformat(),
                'history_count': len(history), 'predicted_date': predicted.isoformat(),
                'announced_date': target_date.isoformat(),
                'absolute_error_days': abs((predicted-target_date).total_seconds()) / 86400})
    return {'status': 'research_only' if folds else 'insufficient_history',
        'public_predictions_enabled': False, 'label_kind': 'source_announced_start_date',
        'folds': folds, 'fold_count': len(folds),
        'mae_days': mean(row['absolute_error_days'] for row in folds) if folds else None}
