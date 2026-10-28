from pathlib import Path
from datetime import datetime, timedelta
import math
import joblib
import numpy as np
import pandas as pd

from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.metrics import mean_absolute_error


MODEL_PATH = Path(__file__).parent / "models" / "hackathon_mlp.pkl"

FEATURES = [
    "event_count",
    "average_gap",
    "median_gap",
    "gap_std",
    "last_gap",
    "gap_trend",
    "month_sin",
    "month_cos",
]


def _date_features(history):
    dates = pd.DatetimeIndex(pd.to_datetime(history)).sort_values()

    if len(dates) < 2:
        raise ValueError("At least two historical events are required.")

    gaps = np.diff(dates.values).astype("timedelta64[D]").astype(int)

    average_gap = float(np.mean(gaps))
    median_gap = float(np.median(gaps))
    gap_std = float(np.std(gaps))
    last_gap = float(gaps[-1])

    if len(gaps) >= 2:
        gap_trend = float(gaps[-1] - gaps[-2])
    else:
        gap_trend = 0.0

    month = dates[-1].month

    month_sin = math.sin(2 * math.pi * month / 12)
    month_cos = math.cos(2 * math.pi * month / 12)

    return {
        "event_count": len(dates),
        "average_gap": average_gap,
        "median_gap": median_gap,
        "gap_std": gap_std,
        "last_gap": last_gap,
        "gap_trend": gap_trend,
        "month_sin": month_sin,
        "month_cos": month_cos,
    }


def build_training_data(df):
    required = {"organization", "start_date"}

    if not required.issubset(df.columns):
        raise ValueError(
            "Dataset must contain organization and start_date columns."
        )

    df = df.copy()

    df["start_date"] = pd.to_datetime(
        df["start_date"],
        errors="coerce"
    )

    df = df.dropna(subset=["organization", "start_date"])
    df = df.sort_values(["organization", "start_date"])

    rows = []

    for organization, group in df.groupby("organization"):

        dates = list(group["start_date"])

        # Need at least 3 events:
        # 2 historical events + 1 target event.
        if len(dates) < 3:
            continue

        for target_index in range(2, len(dates)):

            history = dates[:target_index]
            target_date = dates[target_index]

            feature_values = _date_features(history)

            days_to_next_event = (
                target_date - history[-1]
            ).days

            if days_to_next_event <= 0:
                continue

            rows.append({
                "organization": organization,
                **feature_values,
                "days_to_next_event": days_to_next_event,
                "target_date": target_date,
            })

    return pd.DataFrame(rows)


def create_model():
    return Pipeline([
        (
            "scaler",
            StandardScaler()
        ),
        (
            "neural_network",
            MLPRegressor(
                hidden_layer_sizes=(128, 64, 32),
                activation="relu",
                solver="adam",
                learning_rate_init=0.001,
                max_iter=2000,
                early_stopping=True,
                validation_fraction=0.15,
                random_state=42
            )
        )
    ])


def train_model(dataset_path):
    df = pd.read_csv(dataset_path)

    training_data = build_training_data(df)

    if len(training_data) < 20:
        raise ValueError(
            f"Only {len(training_data)} training samples available. "
            "Collect more historical hackathon data before training."
        )

    training_data = training_data.sort_values("target_date")

    split_index = int(len(training_data) * 0.8)

    train = training_data.iloc[:split_index]
    test = training_data.iloc[split_index:]

    X_train = train[FEATURES]
    y_train = train["days_to_next_event"]

    X_test = test[FEATURES]
    y_test = test["days_to_next_event"]

    model = create_model()

    model.fit(X_train, y_train)

    predictions = model.predict(X_test)

    predictions = np.maximum(predictions, 1)

    mae = mean_absolute_error(
        y_test,
        predictions
    )

    within_7 = np.mean(
        np.abs(predictions - y_test) <= 7
    ) * 100

    within_14 = np.mean(
        np.abs(predictions - y_test) <= 14
    ) * 100

    within_30 = np.mean(
        np.abs(predictions - y_test) <= 30
    ) * 100

    MODEL_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    joblib.dump(model, MODEL_PATH)

    print("Neural network trained successfully")
    print(f"Training samples: {len(train)}")
    print(f"Testing samples: {len(test)}")
    print(f"MAE: {mae:.2f} days")
    print(f"Within +/- 7 days: {within_7:.2f}%")
    print(f"Within +/- 14 days: {within_14:.2f}%")
    print(f"Within +/- 30 days: {within_30:.2f}%")

    return {
        "mae": round(mae, 2),
        "within_7_days": round(within_7, 2),
        "within_14_days": round(within_14, 2),
        "within_30_days": round(within_30, 2),
    }


def predict_next_hackathon(
    organization,
    historical_dates
):
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            "Neural network model has not been trained yet."
        )

    features = _date_features(
        historical_dates
    )

    model = joblib.load(MODEL_PATH)

    X = pd.DataFrame(
        [features],
        columns=FEATURES
    )

    predicted_days = float(
        model.predict(X)[0]
    )

    predicted_days = max(
        1,
        round(predicted_days)
    )

    last_date = max(
        datetime.strptime(date, "%Y-%m-%d")
        for date in historical_dates
    )

    predicted_date = (
        last_date +
        timedelta(days=predicted_days)
    )

    return {
        "organization": organization,
        "predicted_date":
            predicted_date.strftime("%Y-%m-%d"),
        "predicted_gap_days":
            predicted_days,
        "model":
            "MLP Neural Network"
    }


if __name__ == "__main__":

    dataset = (
        Path(__file__).parent.parent /
        "data" /
        "historical_hackathons.csv"
    )

    if not dataset.exists():
        print(
            "Dataset not available yet.\n"
            "Expected file:\n"
            f"{dataset}\n\n"
            "Required columns:\n"
            "organization,start_date"
        )
    else:
        train_model(dataset)

