"""Optional end-to-end pipeline runner for AegisAI data and model workflow."""

from __future__ import annotations

import argparse
import logging
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run full AegisAI ML pipeline")
    parser.add_argument("--skip-download", action="store_true", help="Skip Kaggle download stage")
    parser.add_argument("--synthetic-rows", type=int, default=350)
    return parser.parse_args()


def _run_step(script_path: Path, args: list[str] | None = None) -> None:
    cmd = [sys.executable, str(script_path)]
    if args:
        cmd.extend(args)
    logger.info("Running step: %s", " ".join(cmd))
    proc = subprocess.run(cmd, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"Step failed: {script_path.name}")


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
    args = _parse_args()

    root = Path(__file__).resolve().parents[1]
    scripts_dir = root / "scripts"

    if not args.skip_download:
        _run_step(scripts_dir / "download_kaggle_data.py")

    _run_step(scripts_dir / "generate_synthetic_data.py", ["--rows", str(args.synthetic_rows)])
    _run_step(scripts_dir / "preprocess_data.py")
    _run_step(scripts_dir / "merge_datasets.py")
    _run_step(scripts_dir / "train_xgboost.py")
    _run_step(scripts_dir / "train_logistic.py")
    _run_step(scripts_dir / "build_faiss_index.py")

    logger.info("Pipeline completed successfully")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
