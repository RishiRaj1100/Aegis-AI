"""Build FAISS semantic retrieval index.

Dataset columns:
    task, description, outcome, tags
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

import faiss
import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer


class FaissTaskRetriever:
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2") -> None:
        self.model = SentenceTransformer(model_name)
        self.index = None
        self.metadata: List[Dict[str, Any]] = []

    def _embed(self, texts: List[str]) -> np.ndarray:
        embeddings = self.model.encode(texts, normalize_embeddings=True)
        return np.asarray(embeddings, dtype=np.float32)

    def add_task(self, task_text: str, metadata: Dict[str, Any]) -> None:
        vec = self._embed([task_text])
        if self.index is None:
            self.index = faiss.IndexFlatIP(vec.shape[1])
        self.index.add(vec)
        self.metadata.append({"task": task_text, **metadata})

    def search_similar(self, task_text: str, top_k: int = 5) -> List[Dict[str, Any]]:
        if self.index is None or self.index.ntotal == 0:
            return []
        query = self._embed([task_text])
        k = min(top_k, self.index.ntotal)
        scores, indices = self.index.search(query, k)

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0 or idx >= len(self.metadata):
                continue
            item = dict(self.metadata[idx])
            item["similarity"] = float(max(0.0, min(1.0, score)))
            results.append(item)
        return results

    def save(self, index_path: str, metadata_path: str) -> None:
        if self.index is None:
            raise RuntimeError("No index to save")
        Path(index_path).parent.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self.index, index_path)
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(self.metadata, f, ensure_ascii=True, indent=2)


def build_index(dataset_path: str, index_path: str, metadata_path: str) -> None:
    df = pd.read_csv(dataset_path)
    required = {"task", "description", "outcome", "tags"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns: {sorted(missing)}")

    retriever = FaissTaskRetriever()
    for row in df.to_dict(orient="records"):
        text = f"{row['task']} {row['description']}"
        retriever.add_task(
            task_text=text,
            metadata={
                "outcome": row.get("outcome", "unknown"),
                "tags": row.get("tags", ""),
            },
        )

    retriever.save(index_path=index_path, metadata_path=metadata_path)
    print(f"Saved FAISS index to {index_path}")
    print(f"Saved metadata to {metadata_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--index", default="models/pretrained/tasks.faiss")
    parser.add_argument("--metadata", default="models/pretrained/tasks_metadata.json")
    args = parser.parse_args()
    build_index(args.dataset, args.index, args.metadata)
