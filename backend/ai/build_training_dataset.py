from pathlib import Path
import math

import numpy as np
import pandas as pd


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
    main()
