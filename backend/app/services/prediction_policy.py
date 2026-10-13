"""SRS 10.4: eligibility is distinct from a raw model score.

The current baseline has no approved calibration report. Its output is internal
evaluation only, even when its heuristic score exceeds the numerical threshold.
Calendar envelopes describe observed gap variability; they are not probability
intervals and must never be used to label a baseline forecast high-confidence.
"""
from calendar import monthrange
from datetime import datetime, timedelta, timezone
import math

PUBLIC_THRESHOLD = 0.40
MODEL_VERSION = "recurrence-baseline-1.0-unpromoted"


def suppression_reason(score, *, sufficient, calibrated, promoted, fresh=True, conflict=False):
    if not sufficient:
        return "insufficient_history"
    if not fresh:
        return "stale_evidence"
    if conflict:
        return "unresolved_conflict"
    if not isinstance(score, (int, float)) or isinstance(score, bool) or not math.isfinite(score) or not 0 <= score <= 1:
        return "invalid_score"
    if score < PUBLIC_THRESHOLD:
        return "below_public_threshold"
    if not calibrated:
        return "uncalibrated_model"
    if not promoted:
        return "unpromoted_model"
    return None


def baseline_evaluation(forecast, dates, now=None):
    now = now or datetime.now(timezone.utc)
    dates = sorted(set(dates))
    sufficient = len(dates) >= 2
    window = None
    if sufficient and forecast.get("predicted_date"):
        try:
            parsed = [datetime.strptime(value, "%Y-%m-%d") for value in dates]
            gaps = [(right - left).days for left, right in zip(parsed, parsed[1:])]
            center = datetime.strptime(forecast["predicted_date"], "%Y-%m-%d")
            interval = (center - parsed[-1]).days
            if interval <= 0:
                sufficient = False
            else:
                shift = 0
                if center.date() <= now.date():
                    shift = ((now.date() - center.date()).days // interval + 1) * interval
                earliest = parsed[-1] + timedelta(days=min(gaps) + shift)
                latest = parsed[-1] + timedelta(days=max(gaps) + shift)
                # Month precision avoids implying an exact organizer start date.
                start = earliest.replace(day=1).date()
                end = latest.replace(day=monthrange(latest.year, latest.month)[1]).date()
                window = {"start": start.isoformat(), "end": end.isoformat()}
        except (ValueError, OverflowError):
            sufficient = False
    reason = suppression_reason(forecast.get("confidence"), sufficient=sufficient,
                                calibrated=False, promoted=False)
    return {
        **forecast, "predicted_date": None, "window": window,
        "window_kind": "historical_gap_calendar_envelope", "probability": None,
        "confidence_kind": "heuristic", "confidence_band": "suppressed",
        "model_version": MODEL_VERSION, "generated_at": now.isoformat(),
        "public_eligible": False, "suppression_reason": reason,
        "disclaimer": "Prediction - not officially announced. Uncalibrated evaluation only; the date range is not a probability interval.",
        "historical_events": len(dates),
    }
