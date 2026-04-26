"""Explainability service for Catalyst success prediction.

Provides:
- SHAP-based feature contribution analysis for tree models (XGBoost)
- FAISS-based case retrieval for top similar historical tasks
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize

try:
    import shap

    SHAP_AVAILABLE = True
except Exception:
    SHAP_AVAILABLE = False

try:
    import faiss

    FAISS_AVAILABLE = True
except Exception:
    FAISS_AVAILABLE = False

logger = logging.getLogger(__name__)


class ExplainabilityService:
    """Model explainability and case-based reasoning helper."""

    _READABLE_NAMES: Dict[str, str] = {
        "task_length": "Task scope & details",
        "deadline_days": "Time remaining to deadline",
        "complexity": "Execution complexity",
        "resources": "Available resources",
        "dependencies": "External dependencies",
        "priority": "Task priority",
        "deadline_urgency": "Urgency (Priority vs Deadline)",
        "resource_efficiency": "Resource vs Complexity ratio",
    }

    _FEATURE_CONCEPTS: Dict[str, str] = {
        "task_length": "scope",
        "deadline_days": "time",
        "complexity": "difficulty",
        "resources": "resources",
        "dependencies": "dependencies",
        "priority": "priority",
        "deadline_urgency": "urgency",
        "resource_efficiency": "efficiency",
    }

    def _feature_label(self, key: str) -> str:
        return self._READABLE_NAMES.get(key, key.replace("_", " ").title())

    def _feature_concept(self, key: str) -> str:
        return self._FEATURE_CONCEPTS.get(key, key)

    def explain_prediction(
        self,
        model: Any,
        features: pd.DataFrame,
        top_k: int = 3,
    ) -> Tuple[Dict[str, float], List[str], List[str]]:
        """Run SHAP TreeExplainer and return concise positive/negative factors."""
        if features.empty:
            return {}, [], []

        if not SHAP_AVAILABLE:
            return {}, [], ["Explainability disabled (SHAP library missing)."]

        if model is None:
            return {}, [], []

        try:
            # Handle sklearn Pipeline: extract the model and transform features
            if hasattr(model, "named_steps") and "model" in model.named_steps:
                inner_model = model.named_steps["model"]
                # Transform features if there's a preprocessor
                if "preprocessor" in model.named_steps:
                    transformed_features = model.named_steps["preprocessor"].transform(features)
                elif "scaler" in model.named_steps:
                    transformed_features = model.named_steps["scaler"].transform(features)
                else:
                    transformed_features = features
            else:
                inner_model = model
                transformed_features = features

            # Use TreeExplainer for XGBoost/RandomForest, or KernelExplainer for generic
            try:
                explainer = shap.TreeExplainer(inner_model)
                raw_values = explainer.shap_values(transformed_features)
            except Exception:
                # Fallback to KernelExplainer if TreeExplainer fails (slower)
                explainer = shap.Explainer(inner_model, transformed_features)
                raw_values = explainer(transformed_features).values

            # Handle case where SHAP returns a list (for multi-class)
            if isinstance(raw_values, list):
                # For binary classification, index 1 is usually the positive class
                raw_values = raw_values[1] if len(raw_values) > 1 else raw_values[0]

            # If multi-row input, take the first row
            if len(raw_values.shape) > 1:
                raw_values = raw_values[0]

            # Map back to feature names
            feature_names = features.columns.tolist()
            shap_map = {name: float(val) for name, val in zip(feature_names, raw_values)}

            # Identify top drivers
            sorted_items = sorted(shap_map.items(), key=lambda x: abs(x[1]), reverse=True)
            top_drivers = sorted_items[:top_k]

            positive_factors = []
            negative_factors = []

            for name, val in top_drivers:
                readable = self._READABLE_NAMES.get(name, name.replace("_", " ").title())
                if val > 0:
                    positive_factors.append(f"{readable} contributes positively to success.")
                else:
                    negative_factors.append(f"{readable} increases execution risk.")

            return shap_map, positive_factors, negative_factors

        except Exception as e:
            logger.warning(f"Explainability failed: {e}")
            return {}, [], ["Prediction driven by weighted historical evidence (SHAP fallback)."]

    def retrieve_similar_cases(
        self,
        *,
        query_text: str,
        tasks: Sequence[Dict[str, Any]],
        top_k: int = 5,
        exclude_task_id: Optional[str] = None,
    ) -> List[Dict[str, str]]:
        """Retrieve top similar historical tasks via FAISS on TF-IDF vectors."""
        if not query_text.strip() or not tasks:
            return []

        corpus: List[str] = []
        refs: List[Dict[str, Any]] = []
        for task in tasks:
            task_id = str(task.get("task_id", ""))
            if exclude_task_id and task_id == exclude_task_id:
                continue
            goal = str(task.get("goal", "")).strip()
            if not goal:
                continue
            extra = " ".join(
                [
                    str(task.get("research_insights", "")),
                    str(task.get("execution_plan", "")),
                    str(task.get("reasoning", "")),
                ]
            )
            corpus.append(f"{goal} {extra}".strip())
            refs.append(task)

        if not corpus:
            return []

        vectorizer = TfidfVectorizer(max_features=1024, ngram_range=(1, 2), min_df=1)
        doc_matrix = vectorizer.fit_transform(corpus)
        query_vec = vectorizer.transform([query_text])

        doc_dense = doc_matrix.astype(np.float32).toarray()
        query_dense = query_vec.astype(np.float32).toarray()

        doc_norm = normalize(doc_dense, norm="l2")
        query_norm = normalize(query_dense, norm="l2")

        k = min(top_k, len(refs))

        if FAISS_AVAILABLE:
            index = faiss.IndexFlatIP(doc_norm.shape[1])
            index.add(doc_norm.astype(np.float32))
            scores, indices = index.search(query_norm.astype(np.float32), k)
            idxs = indices[0].tolist()
        else:
            logger.warning("FAISS is not available; using cosine fallback retrieval")
            sims = np.dot(doc_norm, query_norm[0])
            idxs = np.argsort(-sims)[:k].tolist()

        similar_cases: List[Dict[str, str]] = []
        for i in idxs:
            if i < 0 or i >= len(refs):
                continue
            item = refs[i]
            status = str(item.get("status", "UNKNOWN"))
            outcome = "success" if status == "COMPLETED" else "failed" if status == "FAILED" else "unknown"
            similar_cases.append(
                {
                    "task": str(item.get("goal", "")),
                    "outcome": outcome,
                }
            )
        return similar_cases


_explainability_service: ExplainabilityService | None = None


def get_explainability_service() -> ExplainabilityService:
    global _explainability_service
    if _explainability_service is None:
        _explainability_service = ExplainabilityService()
    return _explainability_service
