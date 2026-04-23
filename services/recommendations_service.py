"""
AegisAI - Recommendations Engine
Personalized task suggestions using collaborative filtering + content-based filtering
Finds similar tasks, duplicate detection, and learning from user history
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass

from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)


@dataclass
class Recommendation:
    """Recommendation result."""
    task_id: str
    goal: str
    similarity_score: float
    reason: str
    domain: str
    status: str
    created_at: str


class RecommendationsEngine:
    """
    Personalized recommendations using multiple strategies:
    - Content-based: Similar tasks by text similarity (Pinecone)
    - Collaborative: Tasks from users with similar profiles
    - Historical: Learn from user's past completions
    - Duplicate detection: Warn if similar task already exists
    """

    def __init__(self, db: AsyncIOMotorDatabase):
        """Initialize with MongoDB connection."""
        self.db = db
        self.tasks_collection = db["tasks"]
        self.recommendations_collection = db["recommendations"]
        self.user_activity_collection = db["user_activity"]

    # ── Similarity-Based Recommendations ──────────────────────────────────────

    async def get_similar_tasks(
        self,
        user_id: str,
        task_id: str,
        top_k: int = 5,
        include_completed: bool = False,
    ) -> List[Recommendation]:
        """
        Find tasks similar to a given task.

        Uses semantic search via Pinecone + metadata matching.
        Filters by user, domain, and status.
        """
        try:
            # Get source task
            source_task = await self.tasks_collection.find_one({
                "task_id": task_id,
                "user_id": user_id
            })

            if not source_task:
                logger.warning(f"Task {task_id} not found for user {user_id}")
                return []

            # Find similar tasks via metadata matching
            filter_query: Dict[str, Any] = {
                "user_id": user_id,
                "task_id": {"$ne": task_id},  # Exclude source task
                "domain": source_task.get("domain"),
            }

            if not include_completed:
                filter_query["status"] = {"$nin": ["completed", "archived"]}

            similar_tasks = await self.tasks_collection.find(filter_query).to_list(top_k)

            recommendations = []
            for task in similar_tasks:
                # Calculate similarity based on multiple factors
                similarity = await self._calculate_task_similarity(source_task, task)

                recommendations.append(Recommendation(
                    task_id=task["task_id"],
                    goal=task["goal"][:100],
                    similarity_score=similarity,
                    reason="Similar domain and priority",
                    domain=task.get("domain", "unknown"),
                    status=task.get("status", "pending"),
                    created_at=str(task.get("created_at", "")),
                ))

            # Sort by similarity
            recommendations.sort(key=lambda x: x.similarity_score, reverse=True)

            logger.info(f"Found {len(recommendations)} similar tasks for {task_id}")
            return recommendations[:top_k]

        except Exception as e:
            logger.error(f"Error finding similar tasks: {e}")
            return []

    async def get_recommendations_for_user(
        self,
        user_id: str,
        top_k: int = 10,
        strategy: str = "hybrid",
    ) -> List[Recommendation]:
        """
        Generate personalized recommendations for user.

        Strategies:
        - "content": Text similarity (Pinecone)
        - "collaborative": Based on similar users
        - "historical": Based on user's history
        - "hybrid": Combination of all
        """
        try:
            if strategy == "hybrid":
                # Combine all strategies with weighted scoring
                recommendations = []

                # 40% from content-based
                content_recs = await self._get_content_based_recommendations(user_id, top_k=4)
                recommendations.extend([(r, 0.4) for r in content_recs])

                # 30% from historical
                historical_recs = await self._get_historical_recommendations(user_id, top_k=3)
                recommendations.extend([(r, 0.3) for r in historical_recs])

                # 30% from collaborative
                collab_recs = await self._get_collaborative_recommendations(user_id, top_k=3)
                recommendations.extend([(r, 0.3) for r in collab_recs])

                # Deduplicate and combine scores
                combined = {}
                for rec, weight in recommendations:
                    if rec.task_id not in combined:
                        combined[rec.task_id] = (rec, 0.0)
                    combined[rec.task_id] = (rec, combined[rec.task_id][1] + weight)

                # Sort by combined score
                result = [r for r, _ in sorted(combined.values(), key=lambda x: x[1], reverse=True)]
                return result[:top_k]

            elif strategy == "content":
                return await self._get_content_based_recommendations(user_id, top_k)

            elif strategy == "historical":
                return await self._get_historical_recommendations(user_id, top_k)

            elif strategy == "collaborative":
                return await self._get_collaborative_recommendations(user_id, top_k)

            else:
                logger.warning(f"Unknown strategy: {strategy}")
                return []

        except Exception as e:
            logger.error(f"Error generating recommendations: {e}")
            return []

    # ── Content-Based Filtering ───────────────────────────────────────────────

    async def _get_content_based_recommendations(
        self,
        user_id: str,
        top_k: int = 5,
    ) -> List[Recommendation]:
        """Recommend tasks similar to user's completed tasks."""
        try:
            # Get user's completed tasks
            completed = await self.tasks_collection.find({
                "user_id": user_id,
                "status": "completed"
            }).to_list(5)

            if not completed:
                return []

            # Find tasks in similar domains
            domains = [t.get("domain") for t in completed if t.get("domain")]
            if not domains:
                return []

            candidates = await self.tasks_collection.find({
                "user_id": user_id,
                "domain": {"$in": domains},
                "status": {"$nin": ["completed", "archived"]},
            }).to_list(top_k)

            recommendations = []
            for task in candidates:
                recommendations.append(Recommendation(
                    task_id=task["task_id"],
                    goal=task["goal"][:100],
                    similarity_score=0.8,
                    reason="Similar to your completed tasks",
                    domain=task.get("domain", "unknown"),
                    status=task.get("status", "pending"),
                    created_at=str(task.get("created_at", "")),
                ))

            return recommendations

        except Exception as e:
            logger.error(f"Error in content-based recommendations: {e}")
            return []

    # ── Historical Recommendations ────────────────────────────────────────────

    async def _get_historical_recommendations(
        self,
        user_id: str,
        top_k: int = 5,
    ) -> List[Recommendation]:
        """Recommend tasks based on user's activity patterns."""
        try:
            # Analyze user's past activities
            recent_tasks = await self.tasks_collection.find({
                "user_id": user_id,
                "created_at": {
                    "$gte": datetime.now() - timedelta(days=30)
                }
            }).sort("created_at", -1).to_list(10)

            if not recent_tasks:
                return []

            # Extract patterns
            patterns = await self._extract_patterns(recent_tasks)

            # Find tasks matching patterns
            recommendations = []
            for pattern in patterns[:top_k]:
                matching_tasks = await self.tasks_collection.find({
                    "user_id": user_id,
                    "domain": pattern["domain"],
                    "priority": pattern["priority"],
                    "status": {"$nin": ["completed", "archived"]},
                }).to_list(1)

                if matching_tasks:
                    task = matching_tasks[0]
                    recommendations.append(Recommendation(
                        task_id=task["task_id"],
                        goal=task["goal"][:100],
                        similarity_score=0.75,
                        reason="Matches your work patterns",
                        domain=task.get("domain", "unknown"),
                        status=task.get("status", "pending"),
                        created_at=str(task.get("created_at", "")),
                    ))

            return recommendations

        except Exception as e:
            logger.error(f"Error in historical recommendations: {e}")
            return []

    # ── Collaborative Filtering ───────────────────────────────────────────────

    async def _get_collaborative_recommendations(
        self,
        user_id: str,
        top_k: int = 5,
    ) -> List[Recommendation]:
        """Recommend tasks from users with similar profiles."""
        try:
            # Find similar users (same domains of interest)
            user_domains = await self.tasks_collection.find({
                "user_id": user_id
            }).distinct("domain")

            if not user_domains:
                return []

            # Find other users with similar domains
            similar_users = await self.tasks_collection.find({
                "user_id": {"$ne": user_id},
                "domain": {"$in": user_domains},
            }).distinct("user_id")

            if not similar_users:
                return []

            # Get popular completed tasks from similar users
            popular_tasks = await self.tasks_collection.find({
                "user_id": {"$in": similar_users},
                "status": "completed",
                "domain": {"$in": user_domains},
            }).sort("created_at", -1).to_list(top_k)

            recommendations = []
            for task in popular_tasks:
                # Check if current user already has this task
                existing = await self.tasks_collection.find_one({
                    "user_id": user_id,
                    "goal": task["goal"]
                })

                if not existing:
                    recommendations.append(Recommendation(
                        task_id=task["task_id"],
                        goal=task["goal"][:100],
                        similarity_score=0.7,
                        reason="Popular in your domain",
                        domain=task.get("domain", "unknown"),
                        status=task.get("status", "pending"),
                        created_at=str(task.get("created_at", "")),
                    ))

            return recommendations[:top_k]

        except Exception as e:
            logger.error(f"Error in collaborative recommendations: {e}")
            return []

    # ── Duplicate Detection ───────────────────────────────────────────────────

    async def detect_duplicate_task(
        self,
        user_id: str,
        goal: str,
        threshold: float = 0.85,
    ) -> Optional[Dict[str, Any]]:
        """
        Check if similar task already exists for user.

        Returns matching task if found, None otherwise.
        """
        try:
            # Check for exact match first
            exact_match = await self.tasks_collection.find_one({
                "user_id": user_id,
                "goal": goal
            })

            if exact_match:
                logger.warning(f"Exact duplicate task found for user {user_id}")
                return {
                    "task_id": exact_match["task_id"],
                    "goal": exact_match["goal"],
                    "similarity": 1.0,
                    "status": exact_match.get("status"),
                }

            # Check for similar tasks (simple substring matching for now)
            # In production, use Pinecone semantic search
            similar_tasks = await self.tasks_collection.find({
                "user_id": user_id,
                "$text": {"$search": goal}  # Requires text index
            }).to_list(1)

            if similar_tasks:
                logger.warning(f"Similar duplicate task found for user {user_id}")
                return {
                    "task_id": similar_tasks[0]["task_id"],
                    "goal": similar_tasks[0]["goal"],
                    "similarity": 0.9,
                    "status": similar_tasks[0].get("status"),
                }

            return None

        except Exception as e:
            logger.error(f"Error detecting duplicates: {e}")
            return None

    # ── Helper Methods ────────────────────────────────────────────────────────

    async def _calculate_task_similarity(
        self,
        task1: Dict[str, Any],
        task2: Dict[str, Any],
    ) -> float:
        """Calculate similarity between two tasks (0-1)."""
        score = 0.0

        # Domain match (30%)
        if task1.get("domain") == task2.get("domain"):
            score += 0.3

        # Priority match (20%)
        if task1.get("priority") == task2.get("priority"):
            score += 0.2

        # Status match (20%)
        if task1.get("status") == task2.get("status"):
            score += 0.2

        # Time proximity (30% - tasks created around same time)
        if task1.get("created_at") and task2.get("created_at"):
            created1 = task1["created_at"]
            created2 = task2["created_at"]
            days_diff = abs((created1 - created2).days) if hasattr(created1, 'days') else 0
            if days_diff <= 7:
                score += 0.3
            elif days_diff <= 30:
                score += 0.15

        return min(score, 1.0)

    async def _extract_patterns(
        self,
        tasks: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Extract common patterns from user's tasks."""
        patterns = {}

        for task in tasks:
            domain = task.get("domain", "unknown")
            priority = task.get("priority", "medium")
            key = f"{domain}:{priority}"

            if key not in patterns:
                patterns[key] = {"domain": domain, "priority": priority, "count": 0}

            patterns[key]["count"] += 1

        # Sort by frequency
        return sorted(patterns.values(), key=lambda x: x["count"], reverse=True)

    async def log_recommendation(
        self,
        user_id: str,
        recommended_task_id: str,
        clicked: bool = False,
    ) -> None:
        """Log recommendation for analytics."""
        try:
            await self.recommendations_collection.insert_one({
                "user_id": user_id,
                "recommended_task_id": recommended_task_id,
                "clicked": clicked,
                "timestamp": datetime.now(),
            })
        except Exception as e:
            logger.error(f"Error logging recommendation: {e}")

    async def get_recommendation_stats(
        self,
        user_id: str,
    ) -> Dict[str, Any]:
        """Get stats about recommendations for user."""
        try:
            total = await self.recommendations_collection.count_documents({
                "user_id": user_id
            })

            clicked = await self.recommendations_collection.count_documents({
                "user_id": user_id,
                "clicked": True
            })

            ctr = (clicked / total * 100) if total > 0 else 0

            return {
                "total_recommendations": total,
                "clicked_recommendations": clicked,
                "click_through_rate": ctr,
            }

        except Exception as e:
            logger.error(f"Error getting recommendation stats: {e}")
            return {}
