"""FAISS + sentence-transformers retrieval service for similar task lookup."""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


class RetrievalService:
    def __init__(
        self,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        index_path: str = "models/pretrained/tasks.faiss",
        metadata_path: str = "models/pretrained/tasks_metadata.pkl",
    ) -> None:
        self.model = SentenceTransformer(model_name)
        self.index_path = index_path
        self.metadata_path = metadata_path
        self.dimension = 384
        self.index = faiss.IndexFlatIP(self.dimension)
        self.metadata: List[Dict[str, Any]] = []
        if os.path.exists(self.index_path):
            try:
                self.index = faiss.read_index(self.index_path)
            except Exception as exc:
                logger.warning("Failed loading FAISS index %s: %s", self.index_path, exc)
        if os.path.exists(self.metadata_path):
            try:
                import joblib
                self.metadata = joblib.load(self.metadata_path)
            except Exception as exc:
                logger.warning("Failed loading FAISS metadata %s: %s", self.metadata_path, exc)

    def _embed(self, text: str) -> np.ndarray:
        vec = self.model.encode([text], normalize_embeddings=True)
        return np.asarray(vec, dtype=np.float32)

    def add_task(self, task_text: str, metadata: Dict[str, Any]) -> None:
        emb = self._embed(task_text)
        self.index.add(emb)
        self.metadata.append({"task": task_text, **metadata})

    def search_similar(self, task_text: str, top_k: int = 5) -> List[Dict[str, Any]]:
        if self.index.ntotal == 0:
            return []
        query = self._embed(task_text)
        k = min(top_k, self.index.ntotal)
        scores, indices = self.index.search(query, k)
        results: List[Dict[str, Any]] = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0 or idx >= len(self.metadata):
                continue
            item = dict(self.metadata[idx])
            # Map keys to match frontend schemas
            item["id"] = str(item.get("task_id", idx))
            item["goal"] = item.get("task", "Unknown Task")
            item["success"] = bool(item.get("success", True))
            item["confidence"] = round(float(item.get("confidence", score * 100)), 1)
            item["similarity"] = float(max(0.0, min(1.0, score)))
            results.append(item)
        return results

    def save(self) -> None:
        os.makedirs(os.path.dirname(self.index_path), exist_ok=True)
        faiss.write_index(self.index, self.index_path)
        # Also save metadata
        import joblib
        joblib.dump(self.metadata, self.metadata_path)
        logger.info("Retrieval index and metadata saved to disk.")


_retrieval_service: RetrievalService | None = None


def get_retrieval_service() -> RetrievalService:
    global _retrieval_service
    if _retrieval_service is None:
        _retrieval_service = RetrievalService()
    return _retrieval_service
