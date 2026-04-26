"""Build a FAISS index from final task dataset using sentence-transformers embeddings."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

import faiss
import joblib
import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer

from utils.data_validation import assert_columns, assert_non_empty, assert_file_exists, validate_output_file

logger = logging.getLogger(__name__)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build FAISS retrieval index for task similarity")
    parser.add_argument("--dataset", default="data/processed/final_dataset.csv")
    parser.add_argument("--index-output", default="models/faiss_index.bin")
    parser.add_argument("--metadata-output", default="models/faiss_metadata.pkl")
    parser.add_argument("--model", default="sentence-transformers/all-MiniLM-L6-v2")
    return parser.parse_args()


def build_index(dataset: str, index_output: str, metadata_output: str, model_name: str) -> tuple[Path, Path]:
    dataset_path = Path(dataset)
    assert_file_exists(dataset_path)

    frame = pd.read_csv(dataset_path)
    assert_non_empty(frame, "final_dataset")
    assert_columns(frame, ["task"], "final_dataset")

    texts = frame["task"].astype(str).fillna("").tolist()
    model = SentenceTransformer(model_name)
    embeddings = model.encode(texts, normalize_embeddings=True)
    vectors = np.asarray(embeddings, dtype=np.float32)

    dim = vectors.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(vectors)

    index_path = Path(index_output)
    index_path.parent.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(index_path))

    metadata_path = Path(metadata_output)
    metadata_records = frame[[c for c in frame.columns if c in {"task_id", "task", "success", "delay", "priority"}]].to_dict(orient="records")
    joblib.dump(metadata_records, metadata_path)

    validate_output_file(index_path)
    validate_output_file(metadata_path)
    logger.info("FAISS index built vectors=%d dimension=%d", len(vectors), dim)
    return index_path, metadata_path


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
    args = _parse_args()
    index_path, metadata_path = build_index(
        dataset=args.dataset,
        index_output=args.index_output,
        metadata_output=args.metadata_output,
        model_name=args.model,
    )
    logger.info("Saved index=%s metadata=%s", index_path, metadata_path)
    logger.info("Example retrieval metadata keys: %s", json.dumps(["task_id", "task", "success", "delay", "priority"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
