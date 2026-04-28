"""Model loading and inference helpers for success and delay predictors."""

from __future__ import annotations

import logging
import os
from typing import Any, Dict

import joblib
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class ModelService:
    def __init__(
        self,
        success_model_path: str = "models/pretrained/catalyst_success_predictor.pkl",
        delay_model_path: str = "models/pretrained/behavior_model.pkl",
    ) -> None:
        self.success_model = self._safe_load(success_model_path)
        self.delay_model = self._safe_load(delay_model_path)
        self.scaler = self._safe_load("models/pretrained/xgboost_scaler.pkl")

        # Extract actual models if bundled in dicts
        if isinstance(self.success_model, dict) and "model" in self.success_model:
            self.success_model = self.success_model["model"]
        if isinstance(self.delay_model, dict) and "model" in self.delay_model:
            self.delay_model = self.delay_model["model"]

    def _safe_load(self, model_path: str) -> Any:
        if not os.path.exists(model_path):
            logger.warning("Model file not found: %s", model_path)
            return None
        try:
            return joblib.load(model_path)
        except Exception as exc:
            logger.warning("Could not load model %s: %s", model_path, exc)
            return None

    _FEATURE_COLS = [
        "deadline_days",
        "complexity",
        "resources",
        "dependencies",
        "priority",
        "task_length",
        "deadline_urgency",
        "resource_efficiency",
    ]

    def _to_frame(self, features: Dict[str, Any]) -> pd.DataFrame:
        data = {}
        for col in self._FEATURE_COLS:
            val = features.get(col, 0.0)
            if isinstance(val, (int, float, bool, np.number)):
                data[col] = float(val)
            elif isinstance(val, (list, dict, tuple)):
                data[col] = float(len(val))
            else:
                data[col] = 0.0
        return pd.DataFrame([data], columns=self._FEATURE_COLS)

    def predict_success(self, features: Dict[str, Any]) -> float:
        if self.success_model is None:
            return 0.5
        frame = self._to_frame(features)
        try:
            # Scale features if scaler is available
            X_input = frame
            if self.scaler:
                try:
                    X_input = self.scaler.transform(frame)
                except Exception as e:
                    logger.warning("Scaling failed: %s", e)

            if hasattr(self.success_model, "predict_proba"):
                return float(self.success_model.predict_proba(X_input)[0][1])
            return float(self.success_model.predict(X_input)[0])
        except Exception as exc:
            logger.warning("Success inference failed: %s", exc)
            return 0.5

    def predict_delay(self, features: Dict[str, Any]) -> float:
        if self.delay_model is None:
            return 0.5
        frame = self._to_frame(features)
        try:
            # Scale features if scaler is available
            X_input = frame
            if self.scaler:
                try:
                    X_input = self.scaler.transform(frame)
                except Exception as e:
                    logger.warning("Scaling failed: %s", e)

            if hasattr(self.delay_model, "predict_proba"):
                return float(self.delay_model.predict_proba(X_input)[0][1])
            return float(self.delay_model.predict(X_input)[0])
        except Exception as exc:
            logger.warning("Delay inference failed: %s", exc)
            return 0.5


_model_service: ModelService | None = None


def get_model_service() -> ModelService:
    global _model_service
    if _model_service is None:
        _model_service = ModelService()
    return _model_service
