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
        "goal_length_words": "Goal clarity and scope",
        "num_subtasks": "Execution decomposition",
        "clarity": "Goal clarity",
        "info_quality": "Information quality",
        "feasibility": "Execution feasibility",
        "manageability": "Risk manageability",
        "resource_adequacy": "Resource adequacy",
        "uncertainty": "External uncertainty",
        "past_success_rate": "Historical success rate",
        "similarity_score": "Similarity to prior tasks",
    }

    _FEATURE_CONCEPTS: Dict[str, str] = {
        "goal_length_words": "goal_definition",
        "clarity": "goal_definition",
        "num_subtasks": "execution_structure",
        "info_quality": "information_quality",
        "feasibility": "execution_feasibility",
        "manageability": "risk_manageability",
        "resource_adequacy": "resource_adequacy",
        "uncertainty": "external_uncertainty",
        "past_success_rate": "historical_signal",
        "similarity_score": "case_similarity",
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
            logger.warning("SHAP is not available; explainability will be empty")
            return {}, [], []

        explainer = shap.TreeExplainer(model)
        raw_values = explainer.shap_values(features)

        # Binary classification usually returns either:
        # - ndarray shape (n_samples, n_features), or
        # - list[class_idx] -> ndarray
        if isinstance(raw_values, list):
            values = np.array(raw_values[-1], dtype=np.float64)
        else:
            values = np.array(raw_values, dtype=np.float64)

        if values.ndim == 1:
            sample_values = values
        else:
            sample_values = values[0]

        feature_names = list(features.columns)
        shap_map: Dict[str, float] = {
            name: float(sample_values[idx]) for idx, name in enumerate(feature_names)
        }

        ranked = sorted(shap_map.items(), key=lambda kv: abs(kv[1]), reverse=True)

        positive: List[str] = []
        negative: List[str] = []
        used_concepts: set[str] = set()
        for key, val in ranked:
            concept = self._feature_concept(key)
            if concept in used_concepts:
                continue
            label = self._feature_label(key)
            if val > 0 and len(positive) < top_k:
                positive.append(f"{label} supported the success prediction")
                used_concepts.add(concept)
            elif val < 0 and len(negative) < top_k:
                negative.append(f"{label} reduced expected success")
                used_concepts.add(concept)
            if len(positive) >= top_k and len(negative) >= top_k:
                break

        return shap_map, positive, negative

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
