"""Train Logistic Regression model for delay probability prediction.

Dataset columns:
    task_length, deadline_days, complexity, resources, dependencies, priority, deadline_urgency, resource_efficiency, delay
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


def train_logistic(dataset_path: str, output_path: str = "models/pretrained/behavior_model.pkl") -> Dict[str, float]:
    df = pd.read_csv(dataset_path)
    required = {"task_length", "deadline_days", "complexity", "resources", "dependencies", "priority", "deadline_urgency", "resource_efficiency", "delay"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns: {sorted(missing)}")

    y = df["delay"].astype(int)
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
    X = df[feature_cols]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    clf = Pipeline(
        steps=[
            ("scaler", StandardScaler()),
            ("model", LogisticRegression(max_iter=1000, random_state=42)),
        ]
    )
    clf.fit(X_train, y_train)

    y_pred = clf.predict(X_test)
    y_prob = clf.predict_proba(X_test)[:, 1]

    metrics = {
        "accuracy": float(accuracy_score(y_test, y_pred)),
        "roc_auc": float(roc_auc_score(y_test, y_prob)),
    }
    print("Accuracy:", metrics["accuracy"])
    print("ROC-AUC:", metrics["roc_auc"])
    print("Confusion matrix:\n", confusion_matrix(y_test, y_pred))

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(clf, output)
    print(f"Saved model to {output}")

    return metrics


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True, help="Path to CSV dataset")
    parser.add_argument("--output", default="models/pretrained/behavior_model.pkl")
    args = parser.parse_args()
    train_logistic(args.dataset, args.output)

