"""Train XGBoost model for task success prediction.

Dataset columns:
    task, deadline_days, complexity, resources, dependencies, priority, success
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, Tuple

import joblib
import numpy as np
import pandas as pd
import shap
from sklearn.compose import ColumnTransformer
from sklearn.metrics import accuracy_score, confusion_matrix, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import MinMaxScaler
from xgboost import XGBClassifier


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    data = df.copy()
    data["task_length"] = data["task"].astype(str).str.len()
    data["deadline_urgency"] = data["priority"] / (data["deadline_days"].clip(lower=1.0))
    data["resource_efficiency"] = data["resources"] / (data["complexity"] + 0.1)
    return data


def train_xgboost(dataset_path: str, output_path: str = "models/pretrained/catalyst_success_predictor.pkl") -> Dict[str, float]:
    df = pd.read_csv(dataset_path)
    required = {"task", "deadline_days", "complexity", "resources", "dependencies", "priority", "success"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns: {sorted(missing)}")

    df = build_features(df)
    y = df["success"].astype(int)

    feature_cols = [
        "deadline_days",
        "complexity",
        "resources",
        "dependencies",
        "priority",
        "task_length",
        "deadline_urgency",
        "resource_efficiency",
    ]
    X = df[feature_cols]

    numeric_transformer = Pipeline(steps=[("scale", MinMaxScaler())])
    preprocessor = ColumnTransformer(
        transformers=[("num", numeric_transformer, feature_cols)],
        remainder="drop",
    )

    model = XGBClassifier(
        objective="binary:logistic",
        eval_metric="logloss",
        n_estimators=300,
        max_depth=5,
        learning_rate=0.05,
        subsample=0.9,
        colsample_bytree=0.9,
        random_state=42,
    )

    clf = Pipeline(steps=[("preprocessor", preprocessor), ("model", model)])

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
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

    transformed_test = clf.named_steps["preprocessor"].transform(X_test)
    explainer = shap.TreeExplainer(clf.named_steps["model"])
    shap_values = explainer.shap_values(transformed_test)
    mean_abs = np.abs(shap_values).mean(axis=0)
    feature_importance = sorted(
        zip(feature_cols, mean_abs.tolist()), key=lambda item: item[1], reverse=True
    )
    print("Top SHAP feature importance:")
    for name, score in feature_importance[:10]:
        print(f"  - {name}: {score:.6f}")

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(clf, output)
    print(f"Saved model to {output}")

    return metrics


def predict_success(task_data: Dict[str, float], model_path: str = "models/pretrained/catalyst_success_predictor.pkl") -> float:
    model = joblib.load(model_path)
    record = pd.DataFrame([task_data])
    record["task_length"] = record["task"].astype(str).str.len()
    record["deadline_urgency"] = record.get("priority", 3) / (record["deadline_days"].clip(lower=1.0))
    record["resource_efficiency"] = record.get("resources", 1.0) / (record["complexity"] + 0.1)
    features = record[
        ["deadline_days", "complexity", "resources", "dependencies", "priority", "task_length", "deadline_urgency", "resource_efficiency"]
    ]
    return float(model.predict_proba(features)[0][1])


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True, help="Path to CSV dataset")
    parser.add_argument("--output", default="models/pretrained/catalyst_success_predictor.pkl")
    args = parser.parse_args()
    train_xgboost(args.dataset, args.output)
