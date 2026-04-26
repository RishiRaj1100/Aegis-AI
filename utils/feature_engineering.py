"""Feature engineering helpers for AegisAI ML pipelines."""

from __future__ import annotations

from typing import Iterable

import numpy as np
import pandas as pd


CANONICAL_COLUMNS = [
    "task",
    "deadline_days",
    "complexity",
    "resources",
    "dependencies",
    "priority",
    "success",
    "delay",
]


def normalize_column_name(name: str) -> str:
    return "_".join(str(name).strip().lower().split())


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out.columns = [normalize_column_name(c) for c in out.columns]
    return out


def ensure_columns(df: pd.DataFrame, required: Iterable[str]) -> pd.DataFrame:
    out = df.copy()
    for col in required:
        if col not in out.columns:
            if col in {"success", "delay", "dependencies"}:
                out[col] = 0
            elif col == "task":
                out[col] = ""
            else:
                out[col] = np.nan
    return out


def harmonize_schema(df: pd.DataFrame) -> pd.DataFrame:
    out = normalize_columns(df)

    alias_map = {
        "title": "task",
        "task_title": "task",
        "description": "task",
        "days_to_deadline": "deadline_days",
        "deadline": "deadline_days",
        "resource_count": "resources",
        "num_resources": "resources",
        "depends_on": "dependencies",
        "blocked_by": "dependencies",
        "label": "success",
        "target": "success",
        "completed": "success",
        "is_success": "success",
        "is_delayed": "delay",
        "delayed": "delay",
        "risk": "complexity",
        "importance": "priority",
    }

    for source, target in alias_map.items():
        if source in out.columns and target not in out.columns:
            out[target] = out[source]

    # Special handling for StudentsPerformance.csv
    if "math_score" in out.columns and "reading_score" in out.columns:
        out["task"] = "Academic performance evaluation for " + out["race/ethnicity"].astype(str)
        out["success"] = ((out["math_score"] + out["reading_score"] + out["writing_score"]) / 3 > 70).astype(int)
        out["complexity"] = out["test_preparation_course"].apply(lambda x: 0.8 if x == "none" else 0.4)
        out["resources"] = out["lunch"].apply(lambda x: 1.0 if x == "standard" else 0.5)
        out["priority"] = out["parental_level_of_education"].apply(lambda x: 5 if "master" in str(x).lower() else 3)
        out["deadline_days"] = 30 # Default observation period

    out = ensure_columns(out, CANONICAL_COLUMNS)

    out["task"] = out["task"].astype(str).fillna("").str.strip()

    numeric_cols = [
        "deadline_days",
        "complexity",
        "resources",
        "dependencies",
        "priority",
        "success",
        "delay",
    ]
    for col in numeric_cols:
        out[col] = pd.to_numeric(out[col], errors="coerce")

    for col in ["deadline_days", "complexity", "resources", "dependencies", "priority"]:
        median_val = float(out[col].median()) if not out[col].dropna().empty else 1.0
        out[col] = out[col].fillna(median_val)

    for col in ["success", "delay"]:
        out[col] = out[col].fillna(0).clip(0, 1).round().astype(int)

    out["deadline_days"] = out["deadline_days"].clip(lower=0)
    out["complexity"] = out["complexity"].clip(lower=0.1)
    out["resources"] = out["resources"].clip(lower=0.1)
    out["dependencies"] = out["dependencies"].clip(lower=0)
    out["priority"] = out["priority"].clip(lower=1)

    return out


def add_core_features(df: pd.DataFrame) -> pd.DataFrame:
    out = harmonize_schema(df)
    out["task_length"] = out["task"].astype(str).str.len().astype(float)
    out["deadline_urgency"] = 1.0 / (out["deadline_days"].astype(float) + 1.0)
    out["resource_efficiency"] = out["resources"].astype(float) / (out["complexity"].astype(float) + 1.0)
    out["dependency_ratio"] = out["dependencies"].astype(float) / (out["resources"].astype(float) + 1.0)
    return out


def add_logistic_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "start_delay" not in out.columns:
        out["start_delay"] = out.get("delay", 0) * np.maximum(0.0, out.get("deadline_days", 1) * 0.2)
    if "completion_time" not in out.columns:
        out["completion_time"] = np.maximum(1.0, out.get("deadline_days", 1).astype(float) * 0.8)
    if "abandoned" not in out.columns:
        out["abandoned"] = ((1 - out.get("success", 0)) * out.get("delay", 0)).clip(0, 1)

    out["start_delay"] = pd.to_numeric(out["start_delay"], errors="coerce").fillna(0.0).clip(lower=0)
    out["completion_time"] = pd.to_numeric(out["completion_time"], errors="coerce").fillna(1.0).clip(lower=1.0)
    out["abandoned"] = pd.to_numeric(out["abandoned"], errors="coerce").fillna(0).clip(0, 1).round().astype(int)

    out["delay_ratio"] = out["start_delay"] / (out["completion_time"] + 1.0)
    out["completion_speed"] = 1.0 / (out["completion_time"] + 1.0)
    return out
