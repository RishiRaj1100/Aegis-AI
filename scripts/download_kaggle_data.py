"""Download selected Kaggle datasets into data/raw with automatic unzip."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Iterable, List

from utils.data_validation import validate_output_file

logger = logging.getLogger(__name__)

DEFAULT_DATASETS = [
    "spscientist/students-performance-in-exams",
    "joebeachcapital/productivity-prediction",
    "anthonypino/machine-learning-datasets",
]


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download Kaggle datasets for AegisAI")
    parser.add_argument(
        "--datasets",
        nargs="*",
        default=DEFAULT_DATASETS,
        help="Kaggle datasets in owner/name format",
    )
    parser.add_argument("--output-dir", default="data/raw", help="Directory to store raw datasets")
    return parser.parse_args()


def _load_kaggle_api():
    try:
        from kaggle.api.kaggle_api_extended import KaggleApi
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("Kaggle package is not installed. Install it with: pip install kaggle") from exc

    api = KaggleApi()
    try:
        api.authenticate()
    except Exception as exc:
        raise RuntimeError(
            "Kaggle authentication failed. Ensure kaggle.json is available in ~/.kaggle/ or env vars are set."
        ) from exc
    return api


def _download_dataset(api, dataset: str, output_dir: Path) -> Path:
    target = output_dir / dataset.replace("/", "__")
    target.mkdir(parents=True, exist_ok=True)
    logger.info("Downloading Kaggle dataset: %s", dataset)
    api.dataset_download_files(dataset=dataset, path=str(target), unzip=True, quiet=False)

    csv_files = list(target.rglob("*.csv"))
    if not csv_files:
        logger.warning("No CSV files found in downloaded dataset %s", dataset)
    else:
        for file_path in csv_files:
            validate_output_file(file_path)
    return target


def download_all(datasets: Iterable[str], output_dir: str) -> List[Path]:
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    api = _load_kaggle_api()
    completed: List[Path] = []

    for dataset in datasets:
        try:
            completed.append(_download_dataset(api, dataset, out_dir))
        except Exception as exc:
            logger.error("Failed downloading %s: %s", dataset, exc)

    if not completed:
        raise RuntimeError("No Kaggle datasets were downloaded successfully")
    return completed


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
    args = _parse_args()
    paths = download_all(args.datasets, args.output_dir)
    logger.info("Downloaded %d dataset groups into %s", len(paths), args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
