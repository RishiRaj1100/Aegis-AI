"""
AegisAI - Redis Service
Short-term context caching using redis.asyncio.
Stores intermediate agent results and session context within a configurable TTL window.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

import redis.asyncio as aioredis
from redis.asyncio import Redis

from config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class RedisService:
    """
    Async Redis wrapper for short-term context management.

    Key conventions:
        aegisai:context:{task_id}      – full agent context for a live task
        aegisai:confidence:{task_id}   – latest confidence score
        aegisai:session:{session_id}   – user session state
    """

    _PREFIX = "aegisai"

    def __init__(self) -> None:
        self._redis: Optional[Redis] = None
        self._ttl = settings.REDIS_TTL_SECONDS

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    @property
    def is_connected(self) -> bool:
        return self._redis is not None

    async def connect(self) -> None:
        logger.info("Connecting to Redis at %s:%s …", settings.REDIS_HOST, settings.REDIS_PORT)
        try:
            self._redis = aioredis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                password=settings.REDIS_PASSWORD,
                decode_responses=True,
            )
            await self._redis.ping()
            logger.info("Redis connected.")
        except Exception as exc:
            logger.warning(
                "Redis unavailable (%s). Running without short-term cache — "
                "MongoDB will be used as the sole memory backend.",
                exc,
            )
            self._redis = None

    async def close(self) -> None:
        if self._redis:
            await self._redis.aclose()
            logger.info("Redis connection closed.")

    # ── Internal helpers ──────────────────────────────────────────────────────

    @property
    def client(self) -> Optional[Redis]:
        return self._redis

    def _key(self, namespace: str, identifier: str) -> str:
        return f"{self._PREFIX}:{namespace}:{identifier}"

    # ── Generic JSON KV ───────────────────────────────────────────────────────

    async def set_json(self, namespace: str, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Serialise `value` to JSON and store with TTL. No-op if Redis is unavailable."""
        if self._redis is None:
            return
        redis_key = self._key(namespace, key)
        serialised = json.dumps(value, default=str)
        try:
            await self._redis.setex(redis_key, ttl or self._ttl, serialised)
            logger.debug("Redis SET %s", redis_key)
        except Exception as exc:
            logger.debug("Redis SET failed (%s) — skipping cache.", exc)

    async def get_json(self, namespace: str, key: str) -> Optional[Any]:
        """Retrieve and deserialise a JSON value. Returns None on miss or if Redis is unavailable."""
        if self._redis is None:
            return None
        redis_key = self._key(namespace, key)
        try:
            raw = await self._redis.get(redis_key)
        except Exception as exc:
            logger.debug("Redis GET failed (%s) — falling back to MongoDB.", exc)
            return None
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("Redis GET parse error for key %s", redis_key)
            return None

    async def delete(self, namespace: str, key: str) -> None:
        if self._redis is None:
            return
        try:
            await self._redis.delete(self._key(namespace, key))
        except Exception:
            pass

    async def exists(self, namespace: str, key: str) -> bool:
        if self._redis is None:
            return False
        try:
            return bool(await self._redis.exists(self._key(namespace, key)))
        except Exception:
            return False

    # ── Task-context helpers ──────────────────────────────────────────────────

    async def cache_task_context(self, task_id: str, context: Dict[str, Any]) -> None:
        """Store the full agent context for a task in short-term memory."""
        await self.set_json("context", task_id, context)

    async def get_task_context(self, task_id: str) -> Optional[Dict[str, Any]]:
        return await self.get_json("context", task_id)

    async def update_task_context(self, task_id: str, updates: Dict[str, Any]) -> None:
        """Merge updates into an existing context entry."""
        existing: Dict[str, Any] = await self.get_task_context(task_id) or {}
        existing.update(updates)
        await self.cache_task_context(task_id, existing)

    # ── Confidence cache ──────────────────────────────────────────────────────

    async def cache_confidence(self, task_id: str, confidence_data: Dict[str, Any]) -> None:
        await self.set_json("confidence", task_id, confidence_data)

    async def get_confidence(self, task_id: str) -> Optional[Dict[str, Any]]:
        return await self.get_json("confidence", task_id)

    # ── Session helpers ───────────────────────────────────────────────────────

    async def set_session(self, session_id: str, data: Dict[str, Any]) -> None:
        await self.set_json("session", session_id, data)

    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        return await self.get_json("session", session_id)


# ── Singleton ─────────────────────────────────────────────────────────────────

_redis_service: Optional[RedisService] = None


def get_redis_service() -> RedisService:
    global _redis_service
    if _redis_service is None:
        _redis_service = RedisService()
    return _redis_service
