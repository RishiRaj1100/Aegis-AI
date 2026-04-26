"""Reusable data validation helpers for pipeline scripts."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterable

import pandas as pd

logger = logging.getLogger(__name__)


class ValidationError(ValueError):
    """Validation-specific error type for clear script failure messages."""


def assert_file_exists(path: Path) -> None:
    if not path.exists() or not path.is_file():
        raise ValidationError(f"Required file does not exist: {path}")


def assert_columns(df: pd.DataFrame, required: Iterable[str], dataset_name: str) -> None:
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValidationError(f"{dataset_name} missing required columns: {missing}")


def assert_non_empty(df: pd.DataFrame, dataset_name: str) -> None:
    if df.empty:
        raise ValidationError(f"{dataset_name} is empty after processing")


def assert_binary(df: pd.DataFrame, column: str, dataset_name: str) -> None:
    if column not in df.columns:
        raise ValidationError(f"{dataset_name} missing binary column: {column}")
    bad = sorted(set(df[column].dropna().astype(int).unique()) - {0, 1})
    if bad:
        raise ValidationError(f"{dataset_name}.{column} has non-binary values: {bad}")


def validate_output_file(path: Path) -> None:
    if not path.exists() or path.stat().st_size == 0:
        raise ValidationError(f"Expected output file missing/empty: {path}")


def log_dataset_summary(df: pd.DataFrame, dataset_name: str) -> None:
    logger.info("%s rows=%d cols=%d", dataset_name, len(df), len(df.columns))
    if "success" in df.columns:
        logger.info("%s success_rate=%.3f", dataset_name, float(df["success"].mean()))
    if "delay" in df.columns:
        logger.info("%s delay_rate=%.3f", dataset_name, float(df["delay"].mean()))
