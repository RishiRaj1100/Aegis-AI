"""
AegisAI - Memory Agent
Orchestrates persistence across MongoDB (long-term) and Redis (short-term).
Provides a single unified interface for all agent state read/write operations.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from services.mongodb_service import MongoDBService
from services.redis_service import RedisService
from models.schemas import TaskDocument, TaskStatus

logger = logging.getLogger(__name__)


class MemoryAgent:
    """
    Unified memory interface.

    Long-term  → MongoDB  (task documents, reflections, outcome history)
    Short-term → Redis    (live task context, session state, confidence cache)
    """

    def __init__(self, mongo: MongoDBService, redis: RedisService) -> None:
        self.mongo = mongo
        self.redis = redis

    # ══════════════════════════════════════════════════════════════════════════
    # Task lifecycle
    # ══════════════════════════════════════════════════════════════════════════

    async def create_task(self, task_doc: TaskDocument) -> str:
        """
        Persist a new task to MongoDB and prime its Redis context.

        Returns:
            task_id string.
        """
        doc = task_doc.model_dump()
        task_id = await self.mongo.insert_task(doc)

        # Prime short-term cache with lightweight context
        await self.redis.cache_task_context(
            task_id,
            {
                "task_id": task_id,
                "goal": task_doc.goal,
                "language": task_doc.language,
                "status": task_doc.status,
                "created_at": doc["created_at"].isoformat(),
            },
        )
        logger.info("MemoryAgent: task %s created and cached.", task_id)
        return task_id

    async def update_task(self, task_id: str, updates: Dict[str, Any], user_id: Optional[str] = None) -> bool:
        """Update MongoDB document and invalidate / refresh Redis context."""
        success = await self.mongo.update_task(task_id, updates, user_id=user_id)
        if success:
            await self.redis.update_task_context(task_id, updates)
            logger.debug("MemoryAgent: task %s updated.", task_id)
        return success

    async def get_task(self, task_id: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Read task — Redis-first (fast path), fall back to MongoDB.
        Re-populates Redis on a cache miss.
        """
        cached = await self.redis.get_task_context(task_id)
        if cached and cached.get("execution_plan"):
            # If user_id is provided, verify it
            if user_id and cached.get("user_id") != user_id:
                logger.warning("MemoryAgent: user_id mismatch for cached task %s", task_id)
                # Fall through to Mongo to be sure
            else:
                return cached

        # Cache miss or partial hit → read from Mongo
        doc = await self.mongo.get_task(task_id, user_id=user_id)
        if doc:
            await self.redis.cache_task_context(task_id, doc)
        return doc

    async def record_outcome(
        self,
        task_id: str,
        status: TaskStatus,
        outcome_notes: Optional[str] = None,
        actual_duration_minutes: Optional[int] = None,
        user_id: Optional[str] = None,
    ) -> bool:
        """Persist task outcome and evict Redis context."""
        success = await self.mongo.record_outcome(
            task_id=task_id,
            status=status.value,
            outcome_notes=outcome_notes,
            actual_duration_minutes=actual_duration_minutes,
            user_id=user_id,
        )
        if success:
            await self.redis.cache_confidence(task_id, {"status": status.value})
            logger.info("MemoryAgent: outcome recorded for task %s → %s", task_id, status.value)
        return success

    # ══════════════════════════════════════════════════════════════════════════
    # Confidence cache
    # ══════════════════════════════════════════════════════════════════════════

    async def cache_confidence(self, task_id: str, confidence_data: Dict[str, Any]) -> None:
        await self.redis.cache_confidence(task_id, confidence_data)

    async def get_cached_confidence(self, task_id: str) -> Optional[Dict[str, Any]]:
        return await self.redis.get_confidence(task_id)

    # ══════════════════════════════════════════════════════════════════════════
    # Historical analytics (used by Reflection Agent + Trust Agent)
    # ══════════════════════════════════════════════════════════════════════════

    async def get_past_success_rate(self, limit: int = 100) -> float:
        """Historical success rate across the last `limit` completed/failed tasks."""
        rate = await self.mongo.compute_past_success_rate(limit)
        logger.debug("Past success rate (last %d tasks): %.3f", limit, rate)
        return rate

    async def get_recent_tasks(self, limit: int = 20, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        return await self.mongo.get_recent_tasks(limit, user_id=user_id)

    # ══════════════════════════════════════════════════════════════════════════
    # Reflection documents
    # ══════════════════════════════════════════════════════════════════════════

    async def save_reflection(self, reflection_doc: Dict[str, Any]) -> str:
        reflection_id = await self.mongo.insert_reflection(reflection_doc)
        logger.debug("MemoryAgent: reflection %s saved.", reflection_id)
        return reflection_id

    async def get_reflections(self, task_id: str) -> List[Dict[str, Any]]:
        return await self.mongo.get_reflections_for_task(task_id)

    # ══════════════════════════════════════════════════════════════════════════
    # Session helpers
    # ══════════════════════════════════════════════════════════════════════════

    async def set_session(self, session_id: str, data: Dict[str, Any]) -> None:
        await self.redis.set_session(session_id, data)

    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        return await self.redis.get_session(session_id)
