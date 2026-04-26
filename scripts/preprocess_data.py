"""Preprocess raw datasets and normalize them to a consistent schema."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import List

import pandas as pd

from utils.data_validation import assert_non_empty, log_dataset_summary, validate_output_file
from utils.feature_engineering import harmonize_schema

logger = logging.getLogger(__name__)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Preprocess raw datasets into cleaned CSV files")
    parser.add_argument("--raw-dir", default="data/raw")
    parser.add_argument("--processed-dir", default="data/processed")
    return parser.parse_args()


def _load_frame(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path)
    if path.suffix.lower() in {".parquet", ".pq"}:
        return pd.read_parquet(path)
    raise ValueError(f"Unsupported file format: {path}")


def preprocess(raw_dir: str, processed_dir: str) -> List[Path]:
    source_dir = Path(raw_dir)
    out_dir = Path(processed_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if not source_dir.exists():
        raise FileNotFoundError(f"Raw data directory not found: {source_dir}")

    input_files = [
        p
        for p in source_dir.rglob("*")
        if p.is_file() and p.suffix.lower() in {".csv", ".parquet", ".pq"}
    ]
    if not input_files:
        raise RuntimeError(f"No input datasets found in {source_dir}")

    outputs: List[Path] = []
    for file_path in input_files:
        try:
            frame = _load_frame(file_path)
            cleaned = harmonize_schema(frame)
            assert_non_empty(cleaned, file_path.name)

            out_path = out_dir / f"{file_path.stem}_clean.csv"
            cleaned.to_csv(out_path, index=False)
            validate_output_file(out_path)
            log_dataset_summary(cleaned, file_path.name)
            outputs.append(out_path)
        except Exception as exc:
            logger.error("Failed preprocessing %s: %s", file_path, exc)

    if not outputs:
        raise RuntimeError("No files were successfully preprocessed")
    return outputs


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
    args = _parse_args()
    outputs = preprocess(args.raw_dir, args.processed_dir)
    logger.info("Generated %d cleaned files in %s", len(outputs), args.processed_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
