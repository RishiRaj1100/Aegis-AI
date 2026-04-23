"""
AegisAI - Redis Caching Service
Query result caching, session caching, rate limiting, TTL management
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional
from datetime import datetime, timedelta

from redis.asyncio import Redis

logger = logging.getLogger(__name__)


class CacheConfig:
    """Cache configuration with TTLs."""

    # Time-to-live in seconds
    TASK_CACHE_TTL = 300  # 5 minutes
    ANALYTICS_CACHE_TTL = 600  # 10 minutes
    RECOMMENDATIONS_CACHE_TTL = 1800  # 30 minutes
    SEARCH_CACHE_TTL = 300  # 5 minutes
    USER_SESSION_TTL = 86400  # 24 hours
    RATE_LIMIT_WINDOW = 60  # 1 minute


class RedisCacheService:
    """
    Redis caching for performance optimization.

    Features:
    - Query result caching
    - Session caching
    - Rate limiting
    - TTL management
    - Batch operations
    """

    def __init__(self, redis_client: Redis):
        """Initialize with Redis client."""
        self.redis = redis_client
        self.config = CacheConfig()

    # ── Basic Cache Operations ────────────────────────────────────────────────

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        try:
            value = await self.redis.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: int = 300,
    ) -> bool:
        """Set value in cache with TTL."""
        try:
            await self.redis.setex(
                key,
                ttl,
                json.dumps(value)
            )
            return True
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        try:
            await self.redis.delete(key)
            return True
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            return False

    async def clear_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern."""
        try:
            cursor = 0
            deleted = 0

            while True:
                cursor, keys = await self.redis.scan(cursor, match=pattern)
                if keys:
                    deleted += await self.redis.delete(*keys)
                if cursor == 0:
                    break

            return deleted
        except Exception as e:
            logger.error(f"Cache clear pattern error: {e}")
            return 0

    # ── Task Caching ──────────────────────────────────────────────────────────

    def _task_cache_key(self, user_id: str, task_id: str) -> str:
        """Generate cache key for task."""
        return f"task:{user_id}:{task_id}"

    def _user_tasks_cache_key(self, user_id: str) -> str:
        """Generate cache key for user's tasks list."""
        return f"user_tasks:{user_id}"

    async def cache_task(self, user_id: str, task_id: str, task_data: Dict[str, Any]) -> bool:
        """Cache task data."""
        key = self._task_cache_key(user_id, task_id)
        return await self.set(key, task_data, self.config.TASK_CACHE_TTL)

    async def get_cached_task(self, user_id: str, task_id: str) -> Optional[Dict[str, Any]]:
        """Get cached task data."""
        key = self._task_cache_key(user_id, task_id)
        return await self.get(key)

    async def invalidate_task_cache(self, user_id: str, task_id: str) -> bool:
        """Invalidate task cache."""
        key = self._task_cache_key(user_id, task_id)
        await self.delete(key)
        # Also invalidate user's task list
        await self.delete(self._user_tasks_cache_key(user_id))
        return True

    async def cache_user_tasks(self, user_id: str, tasks: list) -> bool:
        """Cache user's tasks list."""
        key = self._user_tasks_cache_key(user_id)
        return await self.set(key, tasks, self.config.TASK_CACHE_TTL)

    async def get_cached_user_tasks(self, user_id: str) -> Optional[list]:
        """Get cached user tasks."""
        key = self._user_tasks_cache_key(user_id)
        return await self.get(key)

    # ── Analytics Caching ─────────────────────────────────────────────────────

    def _analytics_cache_key(self, user_id: str, period: str = "month") -> str:
        """Generate cache key for analytics."""
        return f"analytics:{user_id}:{period}"

    async def cache_analytics(
        self,
        user_id: str,
        analytics_data: Dict[str, Any],
        period: str = "month",
    ) -> bool:
        """Cache analytics data."""
        key = self._analytics_cache_key(user_id, period)
        return await self.set(key, analytics_data, self.config.ANALYTICS_CACHE_TTL)

    async def get_cached_analytics(
        self,
        user_id: str,
        period: str = "month",
    ) -> Optional[Dict[str, Any]]:
        """Get cached analytics."""
        key = self._analytics_cache_key(user_id, period)
        return await self.get(key)

    async def invalidate_analytics_cache(self, user_id: str) -> int:
        """Invalidate all analytics for user."""
        return await self.clear_pattern(f"analytics:{user_id}:*")

    # ── Recommendations Caching ───────────────────────────────────────────────

    def _recommendations_cache_key(self, user_id: str, strategy: str = "hybrid") -> str:
        """Generate cache key for recommendations."""
        return f"recommendations:{user_id}:{strategy}"

    async def cache_recommendations(
        self,
        user_id: str,
        recommendations: list,
        strategy: str = "hybrid",
    ) -> bool:
        """Cache recommendations."""
        key = self._recommendations_cache_key(user_id, strategy)
        return await self.set(key, recommendations, self.config.RECOMMENDATIONS_CACHE_TTL)

    async def get_cached_recommendations(
        self,
        user_id: str,
        strategy: str = "hybrid",
    ) -> Optional[list]:
        """Get cached recommendations."""
        key = self._recommendations_cache_key(user_id, strategy)
        return await self.get(key)

    async def invalidate_recommendations_cache(self, user_id: str) -> int:
        """Invalidate recommendations for user."""
        return await self.clear_pattern(f"recommendations:{user_id}:*")

    # ── Search Caching ────────────────────────────────────────────────────────

    def _search_cache_key(self, user_id: str, query: str, search_type: str = "hybrid") -> str:
        """Generate cache key for search results."""
        return f"search:{user_id}:{search_type}:{query.lower()}"

    async def cache_search_results(
        self,
        user_id: str,
        query: str,
        results: list,
        search_type: str = "hybrid",
    ) -> bool:
        """Cache search results."""
        key = self._search_cache_key(user_id, query, search_type)
        return await self.set(key, results, self.config.SEARCH_CACHE_TTL)

    async def get_cached_search_results(
        self,
        user_id: str,
        query: str,
        search_type: str = "hybrid",
    ) -> Optional[list]:
        """Get cached search results."""
        key = self._search_cache_key(user_id, query, search_type)
        return await self.get(key)

    # ── Rate Limiting ─────────────────────────────────────────────────────────

    def _rate_limit_key(self, user_id: str, action: str) -> str:
        """Generate rate limit key."""
        return f"rate_limit:{user_id}:{action}"

    async def check_rate_limit(
        self,
        user_id: str,
        action: str,
        limit: int = 10,
        window: int = 60,
    ) -> bool:
        """
        Check if user has exceeded rate limit.

        Returns True if within limits, False if exceeded.
        """
        try:
            key = self._rate_limit_key(user_id, action)
            current = await self.redis.incr(key)

            # Set expiry on first request
            if current == 1:
                await self.redis.expire(key, window)

            return current <= limit

        except Exception as e:
            logger.error(f"Rate limit check error: {e}")
            return True  # Allow on error

    async def get_rate_limit_status(
        self,
        user_id: str,
        action: str,
        limit: int = 10,
    ) -> Dict[str, Any]:
        """Get user's current rate limit status."""
        try:
            key = self._rate_limit_key(user_id, action)
            current = await self.redis.get(key)
            ttl = await self.redis.ttl(key)

            current_int = int(current) if current else 0

            return {
                "action": action,
                "current": current_int,
                "limit": limit,
                "remaining": max(0, limit - current_int),
                "reset_in_seconds": ttl if ttl > 0 else 0,
            }

        except Exception as e:
            logger.error(f"Rate limit status error: {e}")
            return {}

    # ── Session Caching ───────────────────────────────────────────────────────

    def _session_cache_key(self, user_id: str) -> str:
        """Generate cache key for user session."""
        return f"session:{user_id}"

    async def cache_session(self, user_id: str, session_data: Dict[str, Any]) -> bool:
        """Cache user session data."""
        key = self._session_cache_key(user_id)
        return await self.set(key, session_data, self.config.USER_SESSION_TTL)

    async def get_cached_session(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get cached session data."""
        key = self._session_cache_key(user_id)
        return await self.get(key)

    async def invalidate_session(self, user_id: str) -> bool:
        """Invalidate user session."""
        key = self._session_cache_key(user_id)
        return await self.delete(key)

    # ── Cache Statistics ──────────────────────────────────────────────────────

    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get Redis cache statistics."""
        try:
            info = await self.redis.info()
            return {
                "used_memory": info.get("used_memory_human", "unknown"),
                "used_memory_peak": info.get("used_memory_peak_human", "unknown"),
                "connected_clients": info.get("connected_clients", 0),
                "total_commands_processed": info.get("total_commands_processed", 0),
                "instantaneous_ops_per_sec": info.get("instantaneous_ops_per_sec", 0),
                "keys": await self.redis.dbsize(),
            }
        except Exception as e:
            logger.error(f"Cache stats error: {e}")
            return {}

    async def flush_all(self) -> bool:
        """Flush all cache (use with caution)."""
        try:
            await self.redis.flushall()
            logger.warning("All cache flushed")
            return True
        except Exception as e:
            logger.error(f"Cache flush error: {e}")
            return False

    # ── Batch Operations ──────────────────────────────────────────────────────

    async def mget(self, keys: list) -> Dict[str, Optional[Any]]:
        """Get multiple values."""
        try:
            values = await self.redis.mget(keys)
            return {
                key: json.loads(val) if val else None
                for key, val in zip(keys, values)
            }
        except Exception as e:
            logger.error(f"Cache mget error: {e}")
            return {}

    async def mset(self, data: Dict[str, Any], ttl: int = 300) -> bool:
        """Set multiple values."""
        try:
            pipe = self.redis.pipeline()
            for key, value in data.items():
                pipe.setex(key, ttl, json.dumps(value))
            await pipe.execute()
            return True
        except Exception as e:
            logger.error(f"Cache mset error: {e}")
            return False


def get_redis_cache_service(redis_client: Redis) -> RedisCacheService:
    """Get Redis cache service instance."""
    return RedisCacheService(redis_client)
