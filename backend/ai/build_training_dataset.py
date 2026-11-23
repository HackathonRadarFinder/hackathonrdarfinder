from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import math
import sys

import numpy as np
import pandas as pd

from ai.temporal_prediction import readiness_gates, timestamp


HORIZON_DAYS = 90
SNAPSHOT_INTERVAL_DAYS = 30

DATA_DIR = Path(__file__).parent.parent / "data"

SOURCE_PATH = DATA_DIR / "historical_hackathons.csv"
OUTPUT_PATH = DATA_DIR / "ml_training_dataset.csv"


def calculate_features(history, snapshot_date):
    dates = pd.DatetimeIndex(history).sort_values()

    if len(dates) < 2:
        return None

    gaps = (
        np.diff(dates.values)
        .astype("timedelta64[D]")
        .astype(int)
    )

    average_gap = float(np.mean(gaps))
    median_gap = float(np.median(gaps))
    gap_std = float(np.std(gaps))
    last_gap = float(gaps[-1])

    days_since_last_event = float(
        (snapshot_date - dates[-1]).days
    )

    expected_next_gap = average_gap

    days_until_expected_event = (
        expected_next_gap
        - days_since_last_event
    )

    recurrence_progress = (
        days_since_last_event / average_gap
        if average_gap > 0
        else 0.0
    )

    if len(gaps) >= 2:
        gap_trend = float(
            gaps[-1] - gaps[-2]
        )
    else:
        gap_trend = 0.0

    month = snapshot_date.month

    month_sin = math.sin(
        2 * math.pi * month / 12
    )

    month_cos = math.cos(
        2 * math.pi * month / 12
    )

    return {
        "event_count": len(dates),
        "average_gap": round(average_gap, 4),
        "median_gap": round(median_gap, 4),
        "gap_std": round(gap_std, 4),
        "last_gap": round(last_gap, 4),
        "gap_trend": round(gap_trend, 4),
        "days_since_last_event": round(
            days_since_last_event, 4
        ),
        "days_until_expected_event": round(
            days_until_expected_event, 4
        ),
        "recurrence_progress": round(
            recurrence_progress, 6
        ),
        "month_sin": round(month_sin, 6),
        "month_cos": round(month_cos, 6),
    }


def build_training_dataset(source_path):
    df = pd.read_csv(source_path)

    required = {
        "organization",
        "start_date",
    }

    missing = required - set(df.columns)

    if missing:
        raise ValueError(
            f"Missing columns: {sorted(missing)}"
        )

    df["start_date"] = pd.to_datetime(
        df["start_date"],
        errors="coerce",
    )

    df = df.dropna(
        subset=[
            "organization",
            "start_date",
        ]
    )

    df = df.sort_values(
        [
            "organization",
            "start_date",
        ]
    )

    rows = []

    for organization, group in df.groupby("organization"):
        event_dates = (
            pd.DatetimeIndex(
                group["start_date"]
            )
            .sort_values()
            .unique()
        )

        if len(event_dates) < 3:
            continue

        first_snapshot = (
            event_dates[1]
            + pd.Timedelta(days=1)
        )

        last_snapshot = (
            event_dates[-1]
            - pd.Timedelta(days=1)
        )

        snapshot_dates = pd.date_range(
            start=first_snapshot,
            end=last_snapshot,
            freq=f"{SNAPSHOT_INTERVAL_DAYS}D",
        )

        for snapshot_date in snapshot_dates:
            historical = event_dates[
                event_dates < snapshot_date
            ]

            future = event_dates[
                event_dates >= snapshot_date
            ]

            if len(historical) < 2:
                continue

            if len(future) == 0:
                continue

            features = calculate_features(
                historical,
                snapshot_date,
            )

            if features is None:
                continue

            next_event = future[0]

            days_until_next = (
                next_event - snapshot_date
            ).days

            target = int(
                0 <= days_until_next <= HORIZON_DAYS
            )

            rows.append(
                {
                    "organization": organization,
                    **features,
                    "target": target,
                    "target_date": snapshot_date.date(),
                    "days_until_next_event":
                        days_until_next,
                }
            )

    result = pd.DataFrame(rows)

    if result.empty:
        raise ValueError(
            "No training rows could be generated."
        )

    return result


# --- INT-05: historical editions with real, evidenced observation times --------
# A historical edition is admitted only if it proves WHEN its dates were first
# publicly visible (e.g. a web-archive capture). Bad rows are rejected and
# counted with a reason; they are never repaired, defaulted to today, or backdated.

OBSERVATION_METHODS = {"web_archive_capture", "official_announcement_page", "organizer_press_release"}
REQUIRED_INTAKE_FIELDS = (
    "title", "organization", "source", "url", "family", "edition", "start_date",
    "observed_at", "observation_method", "evidence_url",
)
INTAKE_ADAPTER_VERSION = "history-intake-v1"
INTAKE_SOURCE_ID = "reviewed-history-intake"


def validate_historical_row(row, now):
    """Return a rejection reason, or None if the row is acceptable."""
    if not isinstance(row, dict):
        return "not_an_object"
    for field in REQUIRED_INTAKE_FIELDS:
        value = row.get(field)
        if value is None or (isinstance(value, str) and not value.strip()):
            return f"missing_{field}"
    if row["observation_method"] not in OBSERVATION_METHODS:
        return "unknown_observation_method"
    if not str(row["evidence_url"]).startswith("https://"):
        return "evidence_url_not_https"
    try:
        started = timestamp(row["start_date"])
        observed = timestamp(row["observed_at"])
        collected = timestamp(row["collected_at"]) if row.get("collected_at") else observed
    except (ValueError, TypeError):
        return "unparseable_date"
    if str(started.year) != str(row["edition"]):
        return "edition_year_mismatch"
    if observed > now or collected > now:
        return "observation_in_future"
    if observed < collected:
        return "observed_before_collection"
    if observed >= started:
        return "observed_after_event_start"
    return None


def ingest_historical_editions(rows, now=None):
    """Split rows into accepted observations, review entries and counted rejections."""
    now = timestamp(now) if now is not None else datetime.now(timezone.utc).replace(tzinfo=None)
    observations, review, rejected, seen = [], {}, [], set()
    for row in rows:
        reason = validate_historical_row(row, now)
        if reason is None and row["url"] in seen:
            reason = "duplicate_url"
        if reason:
            rejected.append({"url": row.get("url") if isinstance(row, dict) else None, "reason": reason})
            continue
        seen.add(row["url"])
        observed = timestamp(row["observed_at"])
        snapshot = {"title": row["title"], "organization": row["organization"], "source": row["source"],
                    "url": row["url"], "start_date": timestamp(row["start_date"]).isoformat(),
                    "scraped_at": observed.isoformat()}
        # Hash of this intake record, not of the archived page itself.
        digest = hashlib.sha256(json.dumps(
            {**snapshot, "evidence_url": row["evidence_url"], "method": row["observation_method"]},
            sort_keys=True).encode()).hexdigest()
        observations.append({
            "event_id": row["url"], "observed_at": observed.isoformat(), "checksum": digest,
            "checksum_kind": "intake_record_hash", "document_url": row["evidence_url"],
            "source_id": INTAKE_SOURCE_ID, "adapter_version": INTAKE_ADAPTER_VERSION,
            "observation_method": row["observation_method"], "snapshot": snapshot})
        review[row["url"]] = {"family": row["family"], "organization": row["organization"],
                              "edition": str(row["edition"]), "title": row["title"], "source": row["source"]}
    return {"observations": observations, "review_entries": review, "rejected": rejected,
            "rejection_counts": dict(Counter(item["reason"] for item in rejected))}


def prediction_readiness(report):
    """Honest readiness verdict from temporal_prediction.evaluate(); fails closed (see readiness_gates)."""
    return readiness_gates(report)


def intake_main(input_path, out_dir):
    rows = json.loads(Path(input_path).read_text(encoding="utf-8"))
    if not isinstance(rows, list):
        raise SystemExit("Input must be a JSON list of editions")
    result = ingest_historical_editions(rows)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=False)  # never overwrite earlier output
    (out / "observations.json").write_text(
        json.dumps({"schema_version": 1, "observations": result["observations"]}, indent=2), encoding="utf-8")
    (out / "families-fragment.json").write_text(json.dumps(result["review_entries"], indent=2), encoding="utf-8")
    (out / "rejected.json").write_text(json.dumps(result["rejected"], indent=2), encoding="utf-8")
    print(json.dumps({"accepted": len(result["observations"]), "rejected": len(result["rejected"]),
                      "rejection_counts": result["rejection_counts"]}))
    print("Next: review families-fragment.json, merge it into data/prediction-families-v1.json,")
    print("then run workers.evaluate_predictions with --input observations.json")


def main():
    if not SOURCE_PATH.exists():
        print(
            "Historical dataset is not available yet."
        )
        print()
        print("Expected:")
        print(SOURCE_PATH)
        return

    dataset = build_training_dataset(
        SOURCE_PATH
    )

    DATA_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    dataset.to_csv(
        OUTPUT_PATH,
        index=False,
    )

    print("ML training dataset created.")
    print()
    print(f"Rows: {len(dataset)}")

    print(
        "Positive samples:",
        int(dataset["target"].sum()),
    )

    print(
        "Negative samples:",
        int(
            len(dataset)
            - dataset["target"].sum()
        ),
    )

    print()
    print(
        f"Prediction horizon: "
        f"{HORIZON_DAYS} days"
    )

    print(
        f"Saved to: {OUTPUT_PATH}"
    )


if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == "intake":
        intake_main(sys.argv[2], sys.argv[3])
    else:
        main()
