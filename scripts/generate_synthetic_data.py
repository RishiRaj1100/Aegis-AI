"""Generate synthetic AegisAI task records with realistic correlations."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

import numpy as np
import pandas as pd

from utils.data_validation import validate_output_file

logger = logging.getLogger(__name__)

TASK_TEMPLATES = [
    "Plan sprint backlog",
    "Run QA for release",
    "Deploy API service",
    "Create stakeholder report",
    "Refactor auth pipeline",
    "Review production incident",
    "Optimize query performance",
]


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate synthetic task dataset")
    parser.add_argument("--rows", type=int, default=350, help="Rows to generate (200-500 recommended)")
    parser.add_argument("--output", default="data/raw/synthetic_tasks.csv")
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def generate(rows: int, output_path: str, seed: int = 42) -> Path:
    if rows < 1:
        raise ValueError("rows must be positive")

    rng = np.random.default_rng(seed)
    tasks = rng.choice(TASK_TEMPLATES, size=rows)
    deadline_days = rng.integers(1, 30, size=rows)
    complexity = rng.uniform(1.0, 10.0, size=rows)
    resources = rng.uniform(1.0, 12.0, size=rows)
    dependencies = rng.integers(0, 8, size=rows)
    priority = rng.integers(1, 6, size=rows)

    # Realistic success probability signal.
    score = (
        0.32 * resources
        - 0.28 * complexity
        - 0.15 * dependencies
        - 0.12 * priority
        + 0.20 * np.log1p(deadline_days)
    )
    score = score + rng.normal(0, 0.9, size=rows)
    success_prob = 1.0 / (1.0 + np.exp(-score / 3.0))
    success = rng.binomial(1, np.clip(success_prob, 0.02, 0.98))

    delay_score = (
        0.35 * complexity
        + 0.22 * dependencies
        + 0.20 * priority
        - 0.25 * resources
        - 0.10 * deadline_days
    ) + rng.normal(0, 0.7, size=rows)
    delay_prob = 1.0 / (1.0 + np.exp(-delay_score / 3.0))
    delay = rng.binomial(1, np.clip(delay_prob, 0.02, 0.98))

    start_delay = np.clip(delay_prob * rng.uniform(0, 6, size=rows), 0, None)
    completion_time = np.clip(deadline_days * rng.uniform(0.5, 1.4, size=rows), 1, None)
    abandoned = rng.binomial(1, np.clip((1 - success_prob) * 0.4 + delay_prob * 0.2, 0.01, 0.9))

    frame = pd.DataFrame(
        {
            "task_id": [f"SYN-{idx:05d}" for idx in range(rows)],
            "task": tasks,
            "deadline_days": deadline_days,
            "complexity": np.round(complexity, 3),
            "resources": np.round(resources, 3),
            "dependencies": dependencies,
            "priority": priority,
            "success": success.astype(int),
            "delay": delay.astype(int),
            "start_delay": np.round(start_delay, 3),
            "completion_time": np.round(completion_time, 3),
            "abandoned": abandoned.astype(int),
        }
    )

    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(out_path, index=False)
    validate_output_file(out_path)

    logger.info("Generated synthetic dataset rows=%d path=%s", len(frame), out_path)
    logger.info("Success rate=%.3f Delay rate=%.3f", float(frame["success"].mean()), float(frame["delay"].mean()))
    return out_path


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
    args = _parse_args()
    generate(rows=args.rows, output_path=args.output, seed=args.seed)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
