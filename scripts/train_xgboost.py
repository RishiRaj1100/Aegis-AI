"""Train XGBoost success model from merged hybrid dataset."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import shap
from sklearn.metrics import accuracy_score, confusion_matrix, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

from utils.data_validation import assert_binary, assert_columns, assert_file_exists, assert_non_empty, validate_output_file

logger = logging.getLogger(__name__)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train XGBoost success predictor")
    parser.add_argument("--dataset", default="aegis_training_dataset.csv")
    parser.add_argument("--model-output", default="models/pretrained/xgboost_success.pkl")
    parser.add_argument("--scaler-output", default="models/pretrained/xgboost_scaler.pkl")
    return parser.parse_args()


def train_xgboost(dataset: str, model_output: str, scaler_output: str) -> dict:
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
            "success",
        ],
        "final_dataset",
    )
    assert_binary(frame, "success", "final_dataset")

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
    y = frame["success"].astype(int)

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

    model = XGBClassifier(
        n_estimators=300,
        max_depth=5,
        learning_rate=0.05,
        subsample=0.9,
        colsample_bytree=0.9,
        random_state=42,
        eval_metric="logloss",
    )
    model.fit(X_train_scaled, y_train)

    y_pred = model.predict(X_test_scaled)
    y_prob = model.predict_proba(X_test_scaled)[:, 1]

    metrics = {
        "accuracy": float(accuracy_score(y_test, y_pred)),
        "roc_auc": float(roc_auc_score(y_test, y_prob)),
        "confusion_matrix": confusion_matrix(y_test, y_pred).tolist(),
    }

    logger.info("XGBoost accuracy=%.4f roc_auc=%.4f", metrics["accuracy"], metrics["roc_auc"])
    logger.info("Confusion matrix=%s", metrics["confusion_matrix"])

    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X_test_scaled)
    mean_abs = np.abs(shap_values).mean(axis=0)
    sorted_importance = sorted(
        zip(feature_cols, mean_abs.tolist()),
        key=lambda item: item[1],
        reverse=True,
    )
    logger.info("Top SHAP features=%s", sorted_importance[:5])

    model_path = Path(model_output)
    scaler_path = Path(scaler_output)
    model_path.parent.mkdir(parents=True, exist_ok=True)

    bundle = {
        "model": model,
        "features": feature_cols,
        "metrics": metrics,
        "shap_top_features": sorted_importance[:10],
    }
    joblib.dump(bundle, model_path)
    joblib.dump(scaler, scaler_path)

    validate_output_file(model_path)
    validate_output_file(scaler_path)

    return metrics


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
    args = _parse_args()
    train_xgboost(args.dataset, args.model_output, args.scaler_output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
