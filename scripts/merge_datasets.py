"""Merge Kaggle, real, and synthetic datasets into a balanced final dataset."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import List

import pandas as pd

from utils.data_validation import assert_binary, assert_non_empty, log_dataset_summary, validate_output_file
from utils.feature_engineering import harmonize_schema

logger = logging.getLogger(__name__)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Merge cleaned datasets into final training data")
    parser.add_argument("--processed-dir", default="data/processed")
    parser.add_argument("--raw-dir", default="data/raw")
    parser.add_argument("--output", default="data/processed/final_dataset.csv")
    parser.add_argument("--max-class-ratio", type=float, default=1.2)
    return parser.parse_args()


def _ensure_real_tasks_template(path: Path) -> None:
    if path.exists():
        return
    template = pd.DataFrame(
        columns=[
            "task_id",
            "task",
            "deadline_days",
            "complexity",
            "resources",
            "dependencies",
            "priority",
            "success",
            "delay",
            "start_delay",
            "completion_time",
            "abandoned",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    template.to_csv(path, index=False)


def _balance_binary(frame: pd.DataFrame, target_col: str, max_ratio: float) -> pd.DataFrame:
    if target_col not in frame.columns:
        return frame

    class_counts = frame[target_col].value_counts(dropna=False)
    if len(class_counts) < 2:
        return frame

    major_class = class_counts.idxmax()
    minor_class = class_counts.idxmin()
    major_count = int(class_counts[major_class])
    minor_count = int(class_counts[minor_class])

    if minor_count == 0 or major_count / minor_count <= max_ratio:
        return frame

    keep_major = int(minor_count * max_ratio)
    major_sample = frame[frame[target_col] == major_class].sample(n=keep_major, random_state=42)
    minor_sample = frame[frame[target_col] == minor_class]
    balanced = pd.concat([major_sample, minor_sample], ignore_index=True).sample(frac=1.0, random_state=42)
    return balanced.reset_index(drop=True)


def merge(processed_dir: str, raw_dir: str, output: str, max_class_ratio: float) -> Path:
    processed_path = Path(processed_dir)
    raw_path = Path(raw_dir)

    _ensure_real_tasks_template(raw_path / "real_tasks.csv")

    candidate_files: List[Path] = list(processed_path.glob("*_clean.csv"))
    if (raw_path / "synthetic_tasks.csv").exists():
        candidate_files.append(raw_path / "synthetic_tasks.csv")
    if Path("aegis_training_dataset.csv").exists():
        candidate_files.append(Path("aegis_training_dataset.csv"))
    if (raw_path / "real_tasks.csv").exists():
        candidate_files.append(raw_path / "real_tasks.csv")

    if not candidate_files:
        raise RuntimeError("No datasets found for merge")

    merged_frames: List[pd.DataFrame] = []
    for file_path in candidate_files:
        try:
            df = pd.read_csv(file_path)
            merged_frames.append(harmonize_schema(df))
            logger.info("Included dataset: %s", file_path)
        except Exception as exc:
            logger.error("Skipping %s due to error: %s", file_path, exc)

    if not merged_frames:
        raise RuntimeError("No valid datasets available to merge")

    final_df = pd.concat(merged_frames, ignore_index=True)
    final_df = final_df.drop_duplicates(subset=["task", "deadline_days", "complexity", "resources", "priority"])

    if "task_id" not in final_df.columns:
        final_df["task_id"] = [f"TASK-{idx:06d}" for idx in range(len(final_df))]

    if "start_delay" not in final_df.columns:
        final_df["start_delay"] = final_df["delay"] * (final_df["deadline_days"] * 0.2)
    if "completion_time" not in final_df.columns:
        final_df["completion_time"] = final_df["deadline_days"].clip(lower=1.0)
    if "abandoned" not in final_df.columns:
        final_df["abandoned"] = ((1 - final_df["success"]) * final_df["delay"]).clip(0, 1)

    final_df = _balance_binary(final_df, target_col="success", max_ratio=max_class_ratio)
    final_df = _balance_binary(final_df, target_col="delay", max_ratio=max_class_ratio)

    assert_non_empty(final_df, "final_dataset")
    assert_binary(final_df, "success", "final_dataset")
    assert_binary(final_df, "delay", "final_dataset")

    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    final_df.to_csv(output_path, index=False)
    validate_output_file(output_path)
    log_dataset_summary(final_df, "final_dataset")
    return output_path


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
    args = _parse_args()
    out = merge(args.processed_dir, args.raw_dir, args.output, args.max_class_ratio)
    logger.info("Merged dataset saved to %s", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
