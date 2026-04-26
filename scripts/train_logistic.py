"""Train logistic regression model for delay risk prediction."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

import joblib
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

from utils.data_validation import assert_binary, assert_columns, assert_file_exists, assert_non_empty, validate_output_file

logger = logging.getLogger(__name__)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train logistic delay predictor")
    parser.add_argument("--dataset", default="aegis_training_dataset.csv")
    parser.add_argument("--output", default="models/pretrained/logistic_delay.pkl")
    return parser.parse_args()


def train_logistic(dataset: str, output: str) -> dict:
    dataset_path = Path(dataset)
    assert_file_exists(dataset_path)

    frame = pd.read_csv(dataset_path)
    assert_non_empty(frame, "final_dataset")

    assert_columns(
        frame,
        [
            "task_length",
            "deadline_days",
            "complexity",
            "resources",
            "dependencies",
            "priority",
            "deadline_urgency",
            "resource_efficiency",
            "delay",
        ],
        "final_dataset",
    )
    assert_binary(frame, "delay", "final_dataset")

    feature_cols = [
        "task_length",
        "deadline_days",
        "complexity",
        "resources",
        "dependencies",
        "priority",
        "deadline_urgency",
        "resource_efficiency",
    ]

    X = frame[feature_cols]
    y = frame["delay"].astype(int)

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42,
        stratify=y,
    )

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    model = LogisticRegression(random_state=42, max_iter=1000)
    model.fit(X_train_scaled, y_train)

    y_pred = model.predict(X_test_scaled)
    y_prob = model.predict_proba(X_test_scaled)[:, 1]

    metrics = {
        "accuracy": float(accuracy_score(y_test, y_pred)),
        "roc_auc": float(roc_auc_score(y_test, y_prob)),
        "confusion_matrix": confusion_matrix(y_test, y_pred).tolist(),
    }

    logger.info("Logistic accuracy=%.4f roc_auc=%.4f", metrics["accuracy"], metrics["roc_auc"])
    logger.info("Confusion matrix=%s", metrics["confusion_matrix"])

    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {
            "model": model,
            "scaler": scaler,
            "features": feature_cols,
            "metrics": metrics,
        },
        output_path,
    )

    validate_output_file(output_path)
    return metrics


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
    args = _parse_args()
    train_logistic(args.dataset, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
