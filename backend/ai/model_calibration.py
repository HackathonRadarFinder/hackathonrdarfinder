from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import (
    accuracy_score,
    brier_score_loss,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import TimeSeriesSplit


# --------------------------------------------------
# Configuration
# --------------------------------------------------

MODEL_DIR = Path(__file__).parent / "models"

MODEL_PATH = MODEL_DIR / "calibrated_hackathon_model.pkl"

FEATURE_COLUMNS = [
    "event_count",
    "average_gap",
    "median_gap",
    "gap_std",
    "last_gap",
    "gap_trend",
    "days_since_last_event",
    "days_until_expected_event",
    "recurrence_progress",
    "month_sin",
    "month_cos",
]

TARGET_COLUMN = "target"
DATE_COLUMN = "target_date"


# --------------------------------------------------
# Dataset validation
# --------------------------------------------------

def validate_dataset(df: pd.DataFrame):
    required_columns = set(
        FEATURE_COLUMNS
        + [
            TARGET_COLUMN,
            DATE_COLUMN,
        ]
    )

    missing = required_columns - set(df.columns)

    if missing:
        raise ValueError(
            f"Missing required columns: {sorted(missing)}"
        )

    if df.empty:
        raise ValueError("Dataset is empty.")

    if not set(df[TARGET_COLUMN].dropna().unique()).issubset({0, 1}):
        raise ValueError(
            "Target column must contain only 0 and 1."
        )

    return True


# --------------------------------------------------
# Data preparation
# --------------------------------------------------

def prepare_dataset(df: pd.DataFrame):
    df = df.copy()

    df[DATE_COLUMN] = pd.to_datetime(
        df[DATE_COLUMN],
        errors="coerce",
    )

    df = df.dropna(
        subset=FEATURE_COLUMNS
        + [
            TARGET_COLUMN,
            DATE_COLUMN,
        ]
    )

    df = df.sort_values(
        DATE_COLUMN
    ).reset_index(drop=True)

    if len(df) < 30:
        raise ValueError(
            "At least 30 training rows are recommended."
        )

    return df


# --------------------------------------------------
# Time-based split
# --------------------------------------------------

def time_based_split(df: pd.DataFrame):
    """
    Chronological split:

    70% training
    15% validation
    15% final testing
    """

    total = len(df)

    train_end = int(total * 0.70)
    validation_end = int(total * 0.85)

    train_df = df.iloc[:train_end].copy()

    validation_df = df.iloc[
        train_end:validation_end
    ].copy()

    test_df = df.iloc[
        validation_end:
    ].copy()

    if (
        train_df.empty
        or validation_df.empty
        or test_df.empty
    ):
        raise ValueError(
            "Dataset is too small for "
            "train/validation/test splitting."
        )

    return (
        train_df,
        validation_df,
        test_df,
    )


# --------------------------------------------------
# Leakage check
# --------------------------------------------------

def leakage_check(
    train_df,
    validation_df,
    test_df,
):
    train_max = train_df[DATE_COLUMN].max()

    validation_min = validation_df[
        DATE_COLUMN
    ].min()

    validation_max = validation_df[
        DATE_COLUMN
    ].max()

    test_min = test_df[
        DATE_COLUMN
    ].min()

    if train_max >= validation_min:
        raise ValueError(
            "Time leakage detected between "
            "training and validation data."
        )

    if validation_max >= test_min:
        raise ValueError(
            "Time leakage detected between "
            "validation and test data."
        )

    return True


# --------------------------------------------------
# Model
# --------------------------------------------------

def build_model():
    base_model = HistGradientBoostingClassifier(
        learning_rate=0.05,
        max_iter=300,
        max_leaf_nodes=31,
        random_state=42,
    )

    time_cv = TimeSeriesSplit(
        n_splits=3
    )

    calibrated_model = CalibratedClassifierCV(
        estimator=base_model,
        method="sigmoid",
        cv=time_cv,
    )

    return calibrated_model


# --------------------------------------------------
# Confidence threshold selection
# --------------------------------------------------

def find_confidence_threshold(
    y_true,
    probabilities,
    minimum_precision=0.80,
):
    """
    Select confidence threshold using
    validation data only.
    """

    selected_threshold = 0.50

    for threshold in np.arange(
        0.50,
        0.96,
        0.05,
    ):
        predictions = (
            probabilities >= threshold
        ).astype(int)

        precision = precision_score(
            y_true,
            predictions,
            zero_division=0,
        )

        if precision >= minimum_precision:
            selected_threshold = float(
                threshold
            )
            break

    return round(
        selected_threshold,
        2,
    )


# --------------------------------------------------
# Evaluation
# --------------------------------------------------

def calculate_metrics(
    y_true,
    probabilities,
    threshold,
):
    predictions = (
        probabilities >= threshold
    ).astype(int)

    metrics = {
        "accuracy": round(
            accuracy_score(
                y_true,
                predictions,
            ),
            4,
        ),

        "precision": round(
            precision_score(
                y_true,
                predictions,
                zero_division=0,
            ),
            4,
        ),

        "recall": round(
            recall_score(
                y_true,
                predictions,
                zero_division=0,
            ),
            4,
        ),

        "f1": round(
            f1_score(
                y_true,
                predictions,
                zero_division=0,
            ),
            4,
        ),

        "brier_score": round(
            brier_score_loss(
                y_true,
                probabilities,
            ),
            4,
        ),

        "confidence_threshold": threshold,
    }

    if len(np.unique(y_true)) > 1:
        metrics["roc_auc"] = round(
            roc_auc_score(
                y_true,
                probabilities,
            ),
            4,
        )
    else:
        metrics["roc_auc"] = None

    return metrics


# --------------------------------------------------
# Training pipeline
# --------------------------------------------------

def train_calibrated_model(
    dataset_path,
):
    print("Loading ML dataset...")

    df = pd.read_csv(
        dataset_path
    )

    validate_dataset(df)

    df = prepare_dataset(df)

    (
        train_df,
        validation_df,
        test_df,
    ) = time_based_split(df)

    leakage_check(
        train_df,
        validation_df,
        test_df,
    )

    print(
        f"Training rows: {len(train_df)}"
    )

    print(
        f"Validation rows: "
        f"{len(validation_df)}"
    )

    print(
        f"Test rows: {len(test_df)}"
    )

    X_train = train_df[
        FEATURE_COLUMNS
    ]

    y_train = train_df[
        TARGET_COLUMN
    ]

    X_validation = validation_df[
        FEATURE_COLUMNS
    ]

    y_validation = validation_df[
        TARGET_COLUMN
    ]

    X_test = test_df[
        FEATURE_COLUMNS
    ]

    y_test = test_df[
        TARGET_COLUMN
    ]

    print()
    print(
        "Training calibrated "
        "gradient boosting model..."
    )

    model = build_model()

    model.fit(
        X_train,
        y_train,
    )

    # -----------------------------
    # Select threshold on validation
    # -----------------------------

    validation_probabilities = (
        model.predict_proba(
            X_validation
        )[:, 1]
    )

    confidence_threshold = (
        find_confidence_threshold(
            y_validation,
            validation_probabilities,
        )
    )

    print(
        "Selected confidence threshold:",
        confidence_threshold,
    )

    # -----------------------------
    # Final evaluation
    # -----------------------------

    test_probabilities = (
        model.predict_proba(
            X_test
        )[:, 1]
    )

    metrics = calculate_metrics(
        y_test,
        test_probabilities,
        confidence_threshold,
    )

    MODEL_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    artifact = {
        "model": model,
        "features": FEATURE_COLUMNS,
        "confidence_threshold":
            confidence_threshold,
        "metrics": metrics,
    }

    joblib.dump(
        artifact,
        MODEL_PATH,
    )

    print()
    print("=" * 45)
    print("FINAL TEST METRICS")
    print("=" * 45)

    for key, value in metrics.items():
        print(
            f"{key}: {value}"
        )

    print()
    print(
        f"Model saved to: "
        f"{MODEL_PATH}"
    )

    return metrics


# --------------------------------------------------
# Main
# --------------------------------------------------

if __name__ == "__main__":

    dataset_path = (
        Path(__file__).parent.parent
        / "data"
        / "ml_training_dataset.csv"
    )

    if not dataset_path.exists():

        print(
            "Training dataset is "
            "not available yet."
        )

        print()

        print("Expected:")

        print(
            dataset_path
        )

        print()

        print("Required columns:")

        print(
            ",".join(
                FEATURE_COLUMNS
                + [
                    TARGET_COLUMN,
                    DATE_COLUMN,
                ]
            )
        )

    else:

        train_calibrated_model(
            dataset_path
        )