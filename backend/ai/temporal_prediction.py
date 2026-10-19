"""Reviewed edition data and prequential date evaluation; publication stays disabled."""
from calendar import monthrange
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
from pathlib import Path
from statistics import mean, median, pstdev

from ai.discovery_history import as_of
from ai.prediction_model import predict_next_hackathon

BACKEND = Path(__file__).resolve().parents[1]
MODELS = ('existing_mean_gap', 'median_gap', 'last_gap', 'seasonal_anniversary', 'neural')
MIN_CALIBRATION = 30
MIN_COVERAGE_TEST = 20
TARGET_COVERAGE = 0.8


def timestamp(value):
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00')) if isinstance(value, str) else value
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


def load_review():
    raw = (BACKEND / 'data' / 'prediction-families-v1.json').read_bytes()
    return json.loads(raw)['entries'], hashlib.sha256(raw).hexdigest()


def offline_observations():
    """Validate the fixed existing source-backed manifest; no HTTP or database writes."""
    from app.services.curated_validation import validate_records
    raw = (BACKEND / 'data' / 'curated-mvp-20261013.json').read_bytes()
    records = validate_records(json.loads(raw))
    checksum = hashlib.sha256(raw).hexdigest()
    return [{'event_id': str(item.url), 'observed_at': item.scraped_at.isoformat(),
        'checksum': checksum, 'document_url': str(item.url), 'source_id': 'reviewed-offline-manifest',
        'adapter_version': 'curated-v1', 'snapshot': item.model_dump(mode='json')} for item in records]


def historical_observations(artifact):
    """Validate the derived historical dataset against the original reviewed records."""
    source = json.loads((BACKEND/'data/curated-mvp-20261013.json').read_text(encoding='utf-8'))
    canonical = json.dumps(source, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()
    checksum = hashlib.sha256(canonical).hexdigest()
    if artifact.get('source_manifest_canonical_sha256') != checksum:
        raise ValueError('Historical dataset source checksum does not match the reviewed manifest')
    lookup = {row['url']: row for row in source}
    observations = []
    for edition in artifact['historical_editions']:
        original = lookup.get(edition['url'])
        if (not original or any(edition.get(key) != value for key, value in original.items())
                or edition.get('observed_at') != original['scraped_at']
                or edition.get('actual_occurrence_confirmed') is not False
                or timestamp(original['start_date']) >= timestamp(artifact['observation_ceiling'])):
            raise ValueError('Historical dataset changed source facts or observation timestamps')
        observations.append({'event_id': original['url'], 'observed_at': original['scraped_at'],
            'checksum': checksum, 'document_url': original['url'], 'source_id': 'reviewed-historical-dataset',
            'adapter_version': 'curated-v1', 'snapshot': original})
    return observations


def prepare_dataset(observations, review, now):
    """Quarantine unreviewed identity/provenance; never guess recurrence from an organizer."""
    accepted, rejected = [], Counter()
    identities, editions = {}, {}
    conflicted = set()
    curated = {row['snapshot']['url']: row for row in offline_observations()} if any(
        row.get('adapter_version') == 'curated-v1' for row in observations) else {}
    canonical = json.dumps(json.loads((BACKEND/'data/curated-mvp-20261013.json').read_text(encoding='utf-8')),
        sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode() if curated else b''
    canonical_checksum = hashlib.sha256(canonical).hexdigest()
    # Discovery hashes read_text() output, which normalizes CRLF to LF on checkout.
    # Recognize that exact trusted representation without rewriting stored evidence.
    text_checksum = hashlib.sha256((BACKEND/'data/curated-mvp-20261013.json').read_text(
        encoding='utf-8').encode('utf-8')).hexdigest() if curated else None
    for row in observations:
        try:
            snapshot = row['snapshot']
            entry = review.get(snapshot.get('url'))
            if not entry:
                rejected['unreviewed_series'] += 1
                continue
            if snapshot.get('title') != entry['title'] or snapshot.get('source') != entry['source']:
                raise ValueError('identity_changed')
            if snapshot.get('organization') is not None and snapshot['organization'] != entry['organization']:
                raise ValueError('organization_changed')
            if not row.get('document_url') or not row.get('source_id') or not row.get('adapter_version'):
                raise ValueError('provenance_missing')
            checksum = row.get('checksum', '')
            if len(checksum) != 64 or any(char not in '0123456789abcdef' for char in checksum):
                raise ValueError('checksum_invalid')
            observed = timestamp(row['observed_at'])
            scraped = timestamp(snapshot['scraped_at'])
            if observed < scraped:
                raise ValueError('observation_precedes_collection')
            if row['adapter_version'] == 'curated-v1':
                original = curated.get(snapshot['url'])
                if (not original or checksum not in {original['checksum'], canonical_checksum, text_checksum}
                        or timestamp(snapshot['start_date']) != timestamp(original['snapshot']['start_date'])
                        or scraped != timestamp(original['snapshot']['scraped_at'])):
                    raise ValueError('curated_source_facts_changed')
            started = timestamp(snapshot['start_date']).replace(hour=0, minute=0, second=0, microsecond=0)
            if str(started.year) != entry['edition']:
                raise ValueError('edition_date_conflict')
            if observed > now:
                rejected['future_observation'] += 1
                continue
            event_id = str(row['event_id'])
            identity = (entry['family'], entry['edition'])
            if event_id in identities and identities[event_id] != identity:
                conflicted.add(event_id)
                raise ValueError('edition_identity_conflict')
            if identity in editions and editions[identity] != event_id:
                conflicted.update((event_id, editions[identity]))
                raise ValueError('duplicate_edition')
            identities[event_id], editions[identity] = identity, event_id
            accepted.append({**row, 'event_id': event_id, 'observed_at': observed.isoformat(),
                'family': entry['family'], 'edition': entry['edition'], 'organization': entry['organization'],
                'snapshot': {**snapshot, 'start_date': started.isoformat()}})
        except (KeyError, ValueError, TypeError, AttributeError):
            rejected['invalid_or_conflicting_record'] += 1
    # Conflicting identity must not leave earlier observations eligible.
    return [row for row in accepted if row['event_id'] not in conflicted], dict(rejected)


def patterns(rows):
    dates = sorted({timestamp(row['snapshot']['start_date']) for row in rows})
    gaps = [(right-left).days for left, right in zip(dates, dates[1:])]
    return {'edition_count': len(rows), 'historical_dates': [day.date().isoformat() for day in dates],
        'interval_days': gaps, 'mean_interval_days': mean(gaps) if gaps else None,
        'median_interval_days': median(gaps) if gaps else None,
        'interval_std_days': pstdev(gaps) if gaps else None,
        'seasonal_month_counts': dict(sorted(Counter(str(day.month) for day in dates).items())),
        'observed_year_gaps': [right.year-left.year for left, right in zip(dates, dates[1:])],
        'all_observed_editions_consecutive': bool(gaps) and all(right.year-left.year == 1 for left, right in zip(dates, dates[1:]))}


def forecast_dates(history):
    dates = sorted({timestamp(row['snapshot']['start_date']) for row in history})
    if len(dates) < 2:
        return {}
    gaps = [(right-left).days for left, right in zip(dates, dates[1:])]
    if min(gaps) <= 0:
        return {}
    original = predict_next_hackathon(history[0]['organization'], [day.date().isoformat() for day in dates])
    last = dates[-1]
    anniversary = last.replace(year=last.year+1, day=min(last.day, monthrange(last.year+1, last.month)[1]))
    # Deliberately discard the legacy heuristic confidence; it is not calibration.
    return {'existing_mean_gap': timestamp(original['predicted_date']),
        'median_gap': last + timedelta(days=round(median(gaps))),
        'last_gap': last + timedelta(days=gaps[-1]), 'seasonal_anniversary': anniversary}


def calibrated_radius(errors):
    """Finite-sample residual quantile using only labels available before forecast time."""
    if len(errors) < MIN_CALIBRATION:
        return None
    rank = math.ceil((len(errors)+1)*TARGET_COVERAGE)
    return math.ceil(sorted(errors)[rank-1]) if rank <= len(errors) else None


def neural_candidate(history, training, cutoff):
    """Reuse the existing pipeline, refitted only on earlier available edition labels."""
    eligible = [row for row in training if row['available_at'] < cutoff]
    if len(eligible) < 30:
        return None
    import pandas as pd
    from ai.neural_prediction_model import FEATURES, _date_features, create_model
    model = create_model()
    # The legacy random early-stopping split is inappropriate for temporal evaluation.
    model.set_params(neural_network__early_stopping=False)
    model.fit(pd.DataFrame([row['features'] for row in eligible], columns=FEATURES),
              [row['gap'] for row in eligible])
    dates = sorted({row['snapshot']['start_date'] for row in history})
    value = float(model.predict(pd.DataFrame([_date_features(dates)], columns=FEATURES))[0])
    if not math.isfinite(value) or value <= 0:
        return None
    return timestamp(dates[-1]) + timedelta(days=max(1, round(value)))


def verified_outcomes(records, review, now):
    """Explicit reviewed actual-occurrence evidence; never infer it from scheduled dates."""
    result = {}
    for row in records:
        url = row.get('source_url')
        if (url not in review or row.get('confirmed_actual') is not True
                or not isinstance(row.get('review_basis'), str) or not row['review_basis'].strip()):
            raise ValueError('Actual outcomes require a reviewed source URL and confirmation basis')
        actual, observed = timestamp(row['actual_start_date']), timestamp(row['observed_at'])
        if actual > observed or observed > now or url in result:
            raise ValueError('Actual outcomes require unique, already observed occurrence evidence')
        result[url] = {'date': actual.replace(hour=0, minute=0, second=0, microsecond=0),
            'observed_at': observed, 'source_url': url}
    return result


def evaluate(observations, review, now, cutoffs=None, *, neural=False, actual_outcomes=None):
    now = timestamp(now)
    dataset, rejected = prepare_dataset(observations, review, now)
    outcomes = verified_outcomes(actual_outcomes or [], review, now)
    latest = as_of(dataset, now)
    groups = defaultdict(list)
    for row in latest.values():
        if timestamp(row['snapshot']['start_date']) < now:
            groups[row['family']].append(row)
    series = [{'family': family, 'organization': rows[0]['organization'], **patterns(rows)}
        for family, rows in sorted(groups.items())]
    folds, residuals, training = [], defaultdict(list), defaultdict(list)
    targets = sorted(latest.values(), key=lambda row: row['snapshot']['start_date'])
    for target in targets:
        started = timestamp(target['snapshot']['start_date'])
        if started >= now:
            continue
        choices = [timestamp(value) for value in cutoffs] if cutoffs is not None else [started-timedelta(days=90)]
        choices = [cutoff for cutoff in choices if cutoff < started and cutoff < timestamp(target['observed_at'])]
        if not choices:
            continue
        cutoff = max(choices)  # One forecast per target/model; repeated cutoffs cannot inflate sample counts.
        if any(other['family'] == target['family'] and cutoff < timestamp(other['snapshot']['start_date']) < started
               for other in targets):
            continue  # Score the next edition, never skip an intervening target.
        known = as_of(dataset, cutoff)
        history = [row for event_id, row in known.items() if event_id != target['event_id']
            and row['family'] == target['family'] and timestamp(row['snapshot']['start_date']) < cutoff]
        try:
            candidates = forecast_dates(history)
        except (ValueError, OverflowError):
            candidates = {}
        if candidates and neural:
            center = neural_candidate(history, training[target['family']], cutoff)
            if center is not None:
                candidates['neural'] = center
        for model, center in candidates.items():
            if center <= cutoff:
                continue
            key = (target['family'], model)
            errors = [error for available, error in residuals[key] if available < cutoff]
            radius = calibrated_radius(errors)
            error = abs((center-started).days)
            window = {'start': (center-timedelta(days=radius)).date().isoformat(),
                'end': (center+timedelta(days=radius)).date().isoformat()} if radius is not None else None
            outcome = outcomes.get(target['snapshot']['url'])
            actual_error = abs((center-outcome['date']).days) if outcome and outcome['date'] > cutoff else None
            folds.append({'event_id': target['event_id'], 'family': target['family'], 'model': model,
                'cutoff': cutoff.isoformat(), 'history_count': len(history),
                'history_event_ids': sorted(row['event_id'] for row in history),
                'predicted_date': center.date().isoformat(), 'announced_date': started.date().isoformat(),
                'absolute_error_days': error, 'window': window, 'calibration_samples': len(errors),
                'covered': error <= radius if radius is not None else None,
                'actual_absolute_error_days': actual_error,
                'actual_covered': actual_error <= radius if actual_error is not None and radius is not None else None})
            residuals[key].append((max(started, timestamp(target['observed_at'])), error))
        if candidates and neural:
            from ai.neural_prediction_model import _date_features
            dates = sorted({row['snapshot']['start_date'] for row in history})
            training[target['family']].append({'available_at': max(started, timestamp(target['observed_at'])),
                'features': _date_features(dates), 'gap': (started-timestamp(dates[-1])).days})
    metrics = {}
    for model in MODELS:
        scored = [row for row in folds if row['model'] == model]
        windows = [row for row in scored if row['covered'] is not None]
        actual_scored = [row for row in scored if row['actual_absolute_error_days'] is not None]
        actual_windows = [row for row in scored if row['actual_covered'] is not None]
        metrics[model] = {'held_out_editions': len(scored),
            'announced_date_mae_days': mean(row['absolute_error_days'] for row in scored) if scored else None,
            'actual_occurrence_mae_days': mean(row['actual_absolute_error_days'] for row in actual_scored) if actual_scored else None,
            'actual_test_editions': len(actual_scored),
            'actual_date_window_coverage': mean(row['actual_covered'] for row in actual_windows) if actual_windows else None,
            'date_window_coverage': mean(row['covered'] for row in windows) if windows else None,
            'coverage_test_editions': len(windows), 'target_coverage': TARGET_COVERAGE,
            'calibration_status': ('coverage_below_target' if mean(row['covered'] for row in windows) < TARGET_COVERAGE else 'research_only')
                if len(windows) >= MIN_COVERAGE_TEST else 'insufficient_evaluation',
            'probability': None, 'confidence': None}
    upcoming = []
    for family, history in sorted(groups.items()):
        if any(row['family'] == family and timestamp(row['snapshot']['start_date']) >= now for row in latest.values()):
            continue  # A confirmed catalog edition is not an unsupported predicted event.
        try:
            centers = forecast_dates(history)
        except (ValueError, OverflowError):
            centers = {}
        for model, center in centers.items():
            if center > now:
                upcoming.append({'family': family, 'organization': history[0]['organization'], 'model': model,
                    'predicted_date': center.date().isoformat(), 'window': None, 'confidence': None,
                    'public_eligible': False, 'historical_editions': len(history),
                    'suppression_reason': 'uncalibrated_and_unpromoted', 'label_kind': 'source_announced_start_date'})
    return {'schema_version': 1, 'generated_at': now.isoformat(), 'status': 'research_only' if folds else 'insufficient_history',
        'public_predictions_enabled': False, 'publication_approved': False,
        'label_kind': 'source_announced_start_date', 'actual_occurrence_labels': len(outcomes),
        'dataset': {'observations': len(dataset), 'editions': len(latest), 'rejected': rejected,
            'recurring_series': sum(row['edition_count'] >= 2 for row in series)},
        'series': series, 'metrics': metrics, 'folds': folds, 'internal_candidates': upcoming,
        'model_availability': {'existing_mean_gap': 'evaluated_when_history_allows',
            'neural': 'research_temporal_refit_requested' if neural else 'not_fitted_no_approved_artifact',
            'classifier': 'occurrence_probability_model_requires_verified_positive_and_negative_labels'},
        'blockers': ([] if outcomes else ['No confirmed occurrence labels']) + ['No publication approval',
            'Insufficient temporal evidence or calibration' if not folds else 'Research evaluation requires independent approval']}


def readiness(report):
    return {'status': report['status'], 'reviewed_editions': report['dataset']['editions'],
        'recurring_series': report['dataset']['recurring_series'],
        'evaluated_editions': report['metrics']['existing_mean_gap']['held_out_editions'],
        'public_predictions_enabled': False,
        'reason': 'More dated historical evidence and evaluated outcomes are required before forecasts can be published.'}
