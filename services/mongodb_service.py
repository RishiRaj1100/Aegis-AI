"""
AegisAI - MongoDB Service
Async CRUD layer over Motor (async PyMongo driver).
Handles all persistent storage: tasks, outcomes, and reflections.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import DESCENDING

from config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class MongoDBService:
    """
    Async MongoDB client wrapper.
    Call `connect()` on application startup and `close()` on shutdown.
    """

    def __init__(self) -> None:
        self._client: Optional[AsyncIOMotorClient] = None
        self._db: Optional[AsyncIOMotorDatabase] = None

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def connect(self) -> None:
        logger.info("Connecting to MongoDB at %s …", settings.MONGODB_URI)
        self._client = AsyncIOMotorClient(settings.MONGODB_URI)
        self._db = self._client[settings.MONGODB_DB_NAME]
        # Ensure indexes
        await self._ensure_indexes()
        logger.info("MongoDB connected → db=%s", settings.MONGODB_DB_NAME)

    async def close(self) -> None:
        if self._client:
            self._client.close()
            logger.info("MongoDB connection closed.")

    async def _ensure_indexes(self) -> None:
        tasks_col = self._db[settings.MONGODB_TASKS_COLLECTION]
        await tasks_col.create_index("task_id", unique=True)
        await tasks_col.create_index("user_id")
        await tasks_col.create_index([("user_id", DESCENDING), ("created_at", DESCENDING)])
        await tasks_col.create_index([("created_at", DESCENDING)])

        reflections_col = self._db[settings.MONGODB_REFLECTIONS_COLLECTION]
        await reflections_col.create_index("task_id")
        await reflections_col.create_index([("created_at", DESCENDING)])

        models_col = self._db[settings.MONGODB_INTELLIGENCE_MODELS_COLLECTION]
        await models_col.create_index("model_id", unique=True)
        await models_col.create_index([("active", DESCENDING), ("updated_at", DESCENDING)])

        reports_col = self._db[settings.MONGODB_INTELLIGENCE_REPORTS_COLLECTION]
        await reports_col.create_index([("created_at", DESCENDING)])

    # ── Internal helpers ──────────────────────────────────────────────────────

    @property
    def db(self) -> AsyncIOMotorDatabase:
        if self._db is None:
            raise RuntimeError("MongoDB not connected. Call connect() first.")
        return self._db

    def _tasks(self):
        return self.db[settings.MONGODB_TASKS_COLLECTION]

    def _reflections(self):
        return self.db[settings.MONGODB_REFLECTIONS_COLLECTION]

    def _intelligence_models(self):
        return self.db[settings.MONGODB_INTELLIGENCE_MODELS_COLLECTION]

    def _intelligence_reports(self):
        return self.db[settings.MONGODB_INTELLIGENCE_REPORTS_COLLECTION]

    # ── Task CRUD ─────────────────────────────────────────────────────────────

    async def insert_task(self, task_doc: Dict[str, Any]) -> str:
        """Insert a new task document. Returns the task_id."""
        result = await self._tasks().insert_one(task_doc)
        logger.debug("Inserted task %s (_id=%s)", task_doc.get("task_id"), result.inserted_id)
        return task_doc["task_id"]

    async def get_task(self, task_id: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Retrieve a task document by task_id."""
        query: Dict[str, Any] = {"task_id": task_id}
        if user_id:
            query["user_id"] = user_id
        doc = await self._tasks().find_one(query, {"_id": 0})
        return doc

    async def update_task(self, task_id: str, updates: Dict[str, Any], user_id: Optional[str] = None) -> bool:
        """Partially update a task document."""
        updates["updated_at"] = datetime.utcnow()
        query: Dict[str, Any] = {"task_id": task_id}
        if user_id:
            query["user_id"] = user_id
        result = await self._tasks().update_one(
            query,
            {"$set": updates},
        )
        return result.modified_count > 0

    async def list_tasks(
        self,
        limit: int = 50,
        skip: int = 0,
        status: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Return a paginated list of task documents."""
        query: Dict[str, Any] = {}
        if status:
            query["status"] = status
        if user_id:
            query["user_id"] = user_id
        cursor = self._tasks().find(query, {"_id": 0}).sort("created_at", DESCENDING).skip(skip).limit(limit)
        return await cursor.to_list(length=limit)

    # ── Outcome helpers ───────────────────────────────────────────────────────

    async def record_outcome(
        self,
        task_id: str,
        status: str,
        outcome_notes: Optional[str] = None,
        actual_duration_minutes: Optional[int] = None,
        user_id: Optional[str] = None,
    ) -> bool:
        """Update the outcome fields on an existing task document."""
        updates: Dict[str, Any] = {
            "status": status,
            "updated_at": datetime.utcnow(),
        }
        if outcome_notes is not None:
            updates["outcome_notes"] = outcome_notes
        if actual_duration_minutes is not None:
            updates["actual_duration_minutes"] = actual_duration_minutes
        query: Dict[str, Any] = {"task_id": task_id}
        if user_id:
            query["user_id"] = user_id
        result = await self._tasks().update_one(query, {"$set": updates})
        return result.modified_count > 0

    # ── Intelligence registry/report helpers ─────────────────────────────────

    async def upsert_intelligence_model(self, model_doc: Dict[str, Any]) -> Dict[str, Any]:
        await self._intelligence_models().update_one(
            {"model_id": model_doc["model_id"]},
            {"$set": model_doc},
            upsert=True,
        )
        return model_doc

    async def list_intelligence_models(self) -> List[Dict[str, Any]]:
        cursor = self._intelligence_models().find({}, {"_id": 0}).sort([("active", DESCENDING), ("updated_at", DESCENDING)])
        return await cursor.to_list(length=100)

    async def save_intelligence_report(self, report_doc: Dict[str, Any]) -> Dict[str, Any]:
        await self._intelligence_reports().insert_one(report_doc)
        return report_doc

    async def list_intelligence_reports(self, limit: int = 20) -> List[Dict[str, Any]]:
        cursor = self._intelligence_reports().find({}, {"_id": 0}).sort("created_at", DESCENDING).limit(limit)
        return await cursor.to_list(length=limit)

    # ── Reflection CRUD ───────────────────────────────────────────────────────

    async def insert_reflection(self, reflection_doc: Dict[str, Any]) -> str:
        """Store a reflection document."""
        await self._reflections().insert_one(reflection_doc)
        return reflection_doc["reflection_id"]

    async def get_reflections_for_task(self, task_id: str) -> List[Dict[str, Any]]:
        cursor = self._reflections().find({"task_id": task_id}, {"_id": 0}).sort("created_at", DESCENDING)
        return await cursor.to_list(length=100)

    # ── Analytics helpers for the Reflection Agent ───────────────────────────

    async def compute_past_success_rate(self, limit: int = 100) -> float:
        """
        Returns proportion of COMPLETED tasks out of the last `limit` resolved tasks.
        Returns 0.5 (neutral) when no history exists.
        """
        query = {"status": {"$in": ["COMPLETED", "FAILED"]}}
        cursor = (
            self._tasks()
            .find(query, {"status": 1, "_id": 0})
            .sort("updated_at", DESCENDING)
            .limit(limit)
        )
        docs = await cursor.to_list(length=limit)
        if not docs:
            return 0.5
        completed = sum(1 for d in docs if d["status"] == "COMPLETED")
        return completed / len(docs)

    async def get_recent_tasks(self, limit: int = 20) -> List[Dict[str, Any]]:
        cursor = (
            self._tasks()
            .find({}, {"_id": 0})
            .sort("created_at", DESCENDING)
            .limit(limit)
        )
        return await cursor.to_list(length=limit)


# ── Singleton ─────────────────────────────────────────────────────────────────

_mongodb_service: Optional[MongoDBService] = None


def get_mongodb_service() -> MongoDBService:
    global _mongodb_service
    if _mongodb_service is None:
        _mongodb_service = MongoDBService()
    return _mongodb_service
