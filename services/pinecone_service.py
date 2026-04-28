"""
AegisAI - Pinecone Vector Database Service
Semantic search for task goals, research summaries, and insights
Handles: embeddings, indexing, similarity search, metadata filtering
"""

from __future__ import annotations

import logging
import os
from functools import lru_cache
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

from pinecone import Pinecone, ServerlessSpec
from sentence_transformers import SentenceTransformer

from config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class PineconeService:
    """
    Async wrapper for Pinecone vector database operations.
    Handles embeddings, indexing, and semantic search.

    Features:
    - Automatic text-to-embedding conversion (via Groq or external service)
    - Namespace isolation per user
    - Metadata filtering (domain, priority, status, date range)
    - Batch operations for performance
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        index_name: Optional[str] = None,
        index_host: Optional[str] = None,
        region: Optional[str] = None,
        cloud: Optional[str] = None,
        embedding_model: Optional[str] = None,
        embedding_dimension: Optional[int] = None,
    ) -> None:
        """Initialize Pinecone client."""
        self.api_key = api_key or settings.PINECONE_API_KEY or os.getenv("PINECONE_API_KEY")
        self.index_name = index_name or settings.PINECONE_INDEX_NAME
        self.index_host = index_host or settings.PINECONE_HOST or os.getenv("PINECONE_HOST")
        self.region = region or settings.PINECONE_REGION
        self.cloud = cloud or settings.PINECONE_CLOUD
        self.embedding_dimension = embedding_dimension or settings.PINECONE_DIMENSION
        self.metric = settings.PINECONE_METRIC
        self.local_embedding_model_name = embedding_model or settings.LOCAL_EMBEDDING_MODEL
        self.pc: Optional[Pinecone] = None
        self.index = None
        self._local_encoder: Optional[SentenceTransformer] = None

        if not api_key:
            logger.warning("Pinecone API key not provided. Vector search disabled.")
            self.enabled = False
        else:
            self.enabled = True

    # ── Lifecycle ────────────────────────────────────────────────────────────────

    def connect(self) -> None:
        """Initialize Pinecone connection and index."""
        if not self.enabled:
            logger.info("Pinecone disabled - skipping connection")
            return

        try:
            logger.info(f"Connecting to Pinecone (index: {self.index_name})…")
            self.pc = Pinecone(api_key=self.api_key)

            # Prefer the provided host for an existing index.
            if self.index_host:
                self.index = self.pc.Index(host=self.index_host)
            else:
                if self.index_name not in self.pc.list_indexes().names():
                    logger.info(f"Creating index: {self.index_name}")
                    self.pc.create_index(
                        name=self.index_name,
                        dimension=self.embedding_dimension,
                        metric=self.metric,
                        spec=ServerlessSpec(cloud=self.cloud, region=self.region),
                    )

                self.index = self.pc.Index(self.index_name)

            logger.info(f"Pinecone connected → index={self.index_name}")

        except Exception as e:
            logger.error(f"Failed to connect to Pinecone: {e}")
            self.enabled = False

    def close(self) -> None:
        """Close Pinecone connection."""
        if self.pc:
            logger.info("Closing Pinecone connection")
            # Pinecone client handles cleanup automatically
            self.index = None
            self.pc = None

    # ── Embedding Operations ─────────────────────────────────────────────────────

    def _get_local_encoder(self) -> SentenceTransformer:
        if self._local_encoder is None:
            logger.info("Loading local embedding model: %s", self.local_embedding_model_name)
            self._local_encoder = SentenceTransformer(self.local_embedding_model_name)
        return self._local_encoder

    def _embed_locally(self, texts: List[str]) -> List[List[float]]:
        encoder = self._get_local_encoder()
        vectors = encoder.encode(
            texts,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        return [vector.tolist() for vector in vectors]

    async def embed_text(self, text: str, input_type: str = "query") -> List[float]:
        """Create a semantic embedding locally, then store/search it in Pinecone."""
        vectors = self._embed_locally([text])
        return vectors[0]

    async def embed_texts(self, texts: List[str], input_type: str = "passage") -> List[List[float]]:
        """Create embeddings for multiple texts locally."""
        return self._embed_locally(texts)

    async def index_task(
        self,
        task_id: str,
        goal: str,
        user_id: str,
        embedding: List[float],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Index a task's embedding in Pinecone.

        Args:
            task_id: Unique task identifier
            goal: Task goal/description text
            user_id: Task owner user ID
            embedding: Vector embedding (1536 dimensions for OpenAI)
            metadata: Optional metadata (domain, priority, status, created_at)

        Returns:
            Vector ID in Pinecone
        """
        if not self.enabled or not self.index:
            logger.debug(f"Pinecone disabled - skipping index for task {task_id}")
            return f"{user_id}#{task_id}"

        try:
            vector_id = f"{user_id}#{task_id}"
            meta = metadata or {}
            meta.update({
                "task_id": task_id,
                "user_id": user_id,
                "goal": goal[:200],  # Truncate for storage
                "indexed_at": datetime.now().isoformat(),
            })

            self.index.upsert(
                vectors=[
                    {
                        "id": vector_id,
                        "values": embedding,
                        "metadata": meta,
                    }
                ],
                namespace=user_id,
            )

            logger.debug(f"Indexed task {task_id} for user {user_id}")
            return vector_id

        except Exception as e:
            logger.error(f"Failed to index task {task_id}: {e}")
            raise

    async def search_similar_tasks(
        self,
        query_embedding: List[float],
        user_id: str,
        top_k: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search for semantically similar tasks.

        Args:
            query_embedding: Query vector (same dimension as indexed vectors)
            user_id: Namespace (tasks from this user only)
            top_k: Number of results to return
            filter_metadata: Optional metadata filters (e.g., domain, priority, status)

        Returns:
            List of matching tasks with scores
        """
        if not self.enabled or not self.index:
            logger.debug(f"Pinecone disabled - skipping search for user {user_id}")
            return []

        try:
            results = self.index.query(
                vector=query_embedding,
                top_k=top_k,
                namespace=user_id,
                include_metadata=True,
                filter=filter_metadata,
            )

            tasks = []
            for match in results.get("matches", []):
                task = match.get("metadata", {})
                task["score"] = match.get("score")
                tasks.append(task)

            logger.debug(f"Found {len(tasks)} similar tasks for user {user_id}")
            return tasks

        except Exception as e:
            logger.error(f"Search failed for user {user_id}: {e}")
            return []

    async def update_task_embedding(
        self,
        task_id: str,
        user_id: str,
        new_embedding: List[float],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Update a task's embedding vector."""
        if not self.enabled or not self.index:
            return

        try:
            vector_id = f"{user_id}#{task_id}"
            meta = metadata or {}
            meta.update({
                "task_id": task_id,
                "user_id": user_id,
                "updated_at": datetime.now().isoformat(),
            })

            self.index.upsert(
                vectors=[
                    {
                        "id": vector_id,
                        "values": new_embedding,
                        "metadata": meta,
                    }
                ],
                namespace=user_id,
            )

            logger.debug(f"Updated embedding for task {task_id}")

        except Exception as e:
            logger.error(f"Failed to update embedding for task {task_id}: {e}")

    async def delete_task_embedding(self, task_id: str, user_id: str) -> None:
        """Delete a task's embedding from Pinecone."""
        if not self.enabled or not self.index:
            return

        try:
            vector_id = f"{user_id}#{task_id}"
            self.index.delete(ids=[vector_id], namespace=user_id)
            logger.debug(f"Deleted embedding for task {task_id}")

        except Exception as e:
            logger.error(f"Failed to delete embedding for task {task_id}: {e}")

    # ── Batch Operations ─────────────────────────────────────────────────────────

    async def batch_index_tasks(
        self,
        tasks: List[Dict[str, Any]],
        user_id: str,
    ) -> int:
        """
        Batch index multiple tasks efficiently.

        Args:
            tasks: List of task dicts with 'task_id', 'goal', 'embedding', 'metadata'
            user_id: Namespace for isolation

        Returns:
            Number of successfully indexed tasks
        """
        if not self.enabled or not self.index:
            return 0

        try:
            vectors = []
            for task in tasks:
                vector_id = f"{user_id}#{task['task_id']}"
                meta = task.get("metadata", {})
                meta.update({
                    "task_id": task["task_id"],
                    "user_id": user_id,
                    "goal": task.get("goal", "")[:200],
                    "indexed_at": datetime.now().isoformat(),
                })

                vectors.append({
                    "id": vector_id,
                    "values": task["embedding"],
                    "metadata": meta,
                })

            # Upsert in batches (Pinecone has limits)
            batch_size = 100
            total_indexed = 0

            for i in range(0, len(vectors), batch_size):
                batch = vectors[i : i + batch_size]
                self.index.upsert(vectors=batch, namespace=user_id)
                total_indexed += len(batch)

            logger.info(f"Batch indexed {total_indexed} tasks for user {user_id}")
            return total_indexed

        except Exception as e:
            logger.error(f"Batch indexing failed for user {user_id}: {e}")
            return 0

    # ── Statistics & Management ──────────────────────────────────────────────────

    async def get_index_stats(self, user_id: str) -> Dict[str, Any]:
        """Get statistics about a user's vector index."""
        if not self.enabled or not self.index:
            return {}

        try:
            stats = self.index.describe_index_stats()
            namespace_stats = stats.get("namespaces", {}).get(user_id, {})

            return {
                "vector_count": namespace_stats.get("vector_count", 0),
                "dimension": stats.get("dimension", 0),
                "indexed_at": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to get stats for user {user_id}: {e}")
            return {}

    async def delete_user_namespace(self, user_id: str) -> None:
        """Delete all vectors for a user (GDPR compliance)."""
        if not self.enabled or not self.index:
            return

        try:
            self.index.delete(delete_all=True, namespace=user_id)
            logger.info(f"Deleted all embeddings for user {user_id}")

        except Exception as e:
            logger.error(f"Failed to delete namespace {user_id}: {e}")


# ── Singleton Instance ───────────────────────────────────────────────────────────

_pinecone_instance: Optional[PineconeService] = None


def get_pinecone_service() -> PineconeService:
    """Get or create Pinecone service singleton."""
    global _pinecone_instance

    if _pinecone_instance is None:
        _pinecone_instance = PineconeService(api_key=settings.PINECONE_API_KEY)

    return _pinecone_instance


async def initialize_pinecone() -> None:
    """Initialize Pinecone on app startup."""
    service = get_pinecone_service()
    service.connect()


async def shutdown_pinecone() -> None:
    """Shutdown Pinecone on app shutdown."""
    global _pinecone_instance
    if _pinecone_instance:
        _pinecone_instance.close()
        _pinecone_instance = None
