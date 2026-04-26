"""Background retraining orchestration for autonomous feedback loops."""

from __future__ import annotations

import asyncio
import logging
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict

logger = logging.getLogger(__name__)


class ModelRetrainingService:
    """Schedules non-blocking retraining jobs with cooldown safeguards."""

    def __init__(self) -> None:
        self._is_running = False
        self._last_run_at: datetime | None = None
        self._cooldown = timedelta(hours=6)

    def _cooldown_active(self) -> bool:
        if self._last_run_at is None:
            return False
        return datetime.now(timezone.utc) - self._last_run_at < self._cooldown

    @property
    def is_running(self) -> bool:
        return self._is_running

    @property
    def last_run_iso(self) -> str | None:
        if self._last_run_at is None:
            return None
        return self._last_run_at.isoformat()

    async def trigger_if_needed(self, *, sample_count: int, min_samples: int = 20) -> Dict[str, str]:
        if sample_count < min_samples:
            return {"status": "skipped", "reason": "insufficient-samples"}
        if self._is_running:
            return {"status": "skipped", "reason": "already-running"}
        if self._cooldown_active():
            return {"status": "skipped", "reason": "cooldown-active"}

        self._is_running = True
        self._last_run_at = datetime.now(timezone.utc)
        asyncio.create_task(self._run_retraining())
        return {"status": "started", "reason": "threshold-met"}

    async def _run_retraining(self) -> None:
        try:
            await asyncio.to_thread(self._run_script_jobs)
        except Exception:
            logger.exception("Model retraining job failed")
        finally:
            self._is_running = False

    def _run_script_jobs(self) -> None:
        root = Path(__file__).resolve().parents[1]
        feedback_dataset = root / "data" / "feedback_outcomes.csv"
        synthetic_dataset = root / "aegis_training_dataset.csv"

        if not feedback_dataset.exists():
            logger.warning("Retraining skipped: %s is missing", feedback_dataset)
            return
        if not synthetic_dataset.exists():
            logger.warning("Retraining skipped: %s is missing", synthetic_dataset)
            return

        success_script = root / "scripts" / "train_success_xgboost.py"
        delay_script = root / "scripts" / "train_delay_logistic.py"

        logger.info("Retraining started using %s and %s", synthetic_dataset, feedback_dataset)

        subprocess.run(
            [
                sys.executable,
                str(success_script),
                "--dataset",
                str(synthetic_dataset),
                "--output",
                str(root / "models" / "pretrained" / "catalyst_success_predictor.pkl"),
            ],
            cwd=str(root),
            check=False,
        )

        subprocess.run(
            [
                sys.executable,
                str(delay_script),
                "--dataset",
                str(feedback_dataset),
                "--output",
                str(root / "models" / "pretrained" / "behavior_model.pkl"),
            ],
            cwd=str(root),
            check=False,
        )

        logger.info("Retraining completed")


_retraining_service: ModelRetrainingService | None = None


def get_model_retraining_service() -> ModelRetrainingService:
    global _retraining_service
    if _retraining_service is None:
        _retraining_service = ModelRetrainingService()
    return _retraining_service
