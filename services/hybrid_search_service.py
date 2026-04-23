"""
AegisAI - Hybrid Search Service
Combines MongoDB full-text search with Pinecone semantic search
Better results through dual-strategy searching
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Search result with ranking information."""
    task_id: str
    goal: str
    domain: str
    status: str
    priority: str
    relevance_score: float
    search_type: str  # 'keyword', 'semantic', 'hybrid'
    matched_fields: List[str]


class HybridSearchService:
    """
    Hybrid search combining keyword + semantic search.

    Strategy:
    1. Keyword search (MongoDB) - Fast, exact matches
    2. Semantic search (Pinecone) - Meaning-based results
    3. Hybrid - Combine both with weighted scoring

    Score = 0.4 * keyword_score + 0.6 * semantic_score
    """

    def __init__(
        self,
        db: AsyncIOMotorDatabase,
        pinecone_service: Optional[Any] = None,
        embeddings_service: Optional[Any] = None,
    ):
        """Initialize with MongoDB, Pinecone, and embeddings service."""
        self.db = db
        self.tasks_collection = db["tasks"]
        self.pinecone_svc = pinecone_service
        self.embeddings_svc = embeddings_service

    # ── Keyword Search ────────────────────────────────────────────────────────

    async def keyword_search(
        self,
        user_id: str,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        top_k: int = 10,
    ) -> List[SearchResult]:
        """
        Full-text keyword search using MongoDB.

        Fast, exact matching. Requires text index on goals.
        """
        try:
            search_query: Dict[str, Any] = {
                "user_id": user_id,
                "$text": {"$search": query},
            }

            # Apply optional filters
            if filters:
                if "domain" in filters:
                    search_query["domain"] = filters["domain"]
                if "status" in filters:
                    search_query["status"] = filters["status"]
                if "priority" in filters:
                    search_query["priority"] = filters["priority"]
                if "created_after" in filters:
                    search_query["created_at"] = {"$gte": filters["created_after"]}

            # Search with text score
            results = await self.tasks_collection.find(
                search_query,
                {"score": {"$meta": "textScore"}}
            ).sort([("score", {"$meta": "textScore"})]).to_list(top_k)

            search_results = []
            for task in results:
                search_results.append(SearchResult(
                    task_id=task["task_id"],
                    goal=task["goal"][:100],
                    domain=task.get("domain", "unknown"),
                    status=task.get("status", "pending"),
                    priority=task.get("priority", "medium"),
                    relevance_score=task.get("score", 0),
                    search_type="keyword",
                    matched_fields=["goal"],
                ))

            logger.info(f"Keyword search found {len(search_results)} results for user {user_id}")
            return search_results

        except Exception as e:
            logger.error(f"Keyword search error: {e}")
            return []

    # ── Semantic Search ───────────────────────────────────────────────────────

    async def semantic_search(
        self,
        user_id: str,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        top_k: int = 10,
    ) -> List[SearchResult]:
        """
        Semantic similarity search using Pinecone.

        Meaning-based matching. Requires embeddings service.
        """
        if not self.pinecone_svc or not self.embeddings_svc:
            logger.warning("Semantic search unavailable - missing services")
            return []

        try:
            # Generate embedding for query
            query_embedding = await self.embeddings_svc.embed_text(query)

            # Search in Pinecone
            pinecone_results = await self.pinecone_svc.search_similar_tasks(
                query_embedding=query_embedding,
                user_id=user_id,
                top_k=top_k,
                filter_metadata=filters,
            )

            # Convert to SearchResult objects
            search_results = []
            for idx, result in enumerate(pinecone_results):
                search_results.append(SearchResult(
                    task_id=result.get("task_id", ""),
                    goal=result.get("goal", "")[:100],
                    domain=result.get("domain", "unknown"),
                    status=result.get("status", "pending"),
                    priority=result.get("priority", "medium"),
                    relevance_score=result.get("score", 0),
                    search_type="semantic",
                    matched_fields=["goal (semantic)"],
                ))

            logger.info(f"Semantic search found {len(search_results)} results for user {user_id}")
            return search_results

        except Exception as e:
            logger.error(f"Semantic search error: {e}")
            return []

    # ── Hybrid Search ─────────────────────────────────────────────────────────

    async def hybrid_search(
        self,
        user_id: str,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        top_k: int = 10,
        keyword_weight: float = 0.4,
        semantic_weight: float = 0.6,
    ) -> List[SearchResult]:
        """
        Hybrid search combining keyword and semantic.

        Performs both searches and combines results with weighted scoring.
        """
        try:
            # Run both searches in parallel
            keyword_results = await self.keyword_search(user_id, query, filters, top_k)
            semantic_results = await self.semantic_search(user_id, query, filters, top_k)

            # Combine results by task_id
            combined: Dict[str, SearchResult] = {}

            # Add keyword results
            for result in keyword_results:
                combined[result.task_id] = result
                combined[result.task_id].relevance_score = (
                    result.relevance_score * keyword_weight
                )

            # Add/merge semantic results
            for result in semantic_results:
                if result.task_id in combined:
                    # Average scores
                    existing = combined[result.task_id]
                    combined[result.task_id].relevance_score = (
                        (existing.relevance_score / keyword_weight * keyword_weight) +
                        (result.relevance_score * semantic_weight)
                    ) / 2
                    combined[result.task_id].search_type = "hybrid"
                    combined[result.task_id].matched_fields.extend(
                        ["goal (semantic)"]
                    )
                else:
                    combined[result.task_id] = result
                    combined[result.task_id].relevance_score = (
                        result.relevance_score * semantic_weight
                    )

            # Sort by combined score
            final_results = sorted(
                combined.values(),
                key=lambda x: x.relevance_score,
                reverse=True
            )

            logger.info(f"Hybrid search found {len(final_results)} combined results")
            return final_results[:top_k]

        except Exception as e:
            logger.error(f"Hybrid search error: {e}")
            return []

    # ── Advanced Filtering ────────────────────────────────────────────────────

    async def faceted_search(
        self,
        user_id: str,
        query: str,
        facets: Optional[Dict[str, List[str]]] = None,
    ) -> Dict[str, Any]:
        """
        Search with faceted filtering.

        Returns results grouped by facet values (domain, status, priority).
        """
        try:
            # Perform base search
            results = await self.hybrid_search(user_id, query, top_k=100)

            # Group by facets
            faceted_results = {
                "results": results[:10],
                "facets": {
                    "domains": {},
                    "statuses": {},
                    "priorities": {},
                }
            }

            for result in results:
                # Count by domain
                domain = result.domain
                faceted_results["facets"]["domains"][domain] = (
                    faceted_results["facets"]["domains"].get(domain, 0) + 1
                )

                # Count by status
                status = result.status
                faceted_results["facets"]["statuses"][status] = (
                    faceted_results["facets"]["statuses"].get(status, 0) + 1
                )

                # Count by priority
                priority = result.priority
                faceted_results["facets"]["priorities"][priority] = (
                    faceted_results["facets"]["priorities"].get(priority, 0) + 1
                )

            return faceted_results

        except Exception as e:
            logger.error(f"Faceted search error: {e}")
            return {"results": [], "facets": {}}

    # ── Auto-Suggest ──────────────────────────────────────────────────────────

    async def get_search_suggestions(
        self,
        user_id: str,
        query_prefix: str,
        top_k: int = 5,
    ) -> List[str]:
        """
        Get search suggestions based on query prefix.

        Useful for autocomplete features.
        """
        try:
            # Find tasks with goals starting with prefix
            suggestions = await self.tasks_collection.find({
                "user_id": user_id,
                "goal": {"$regex": f"^{query_prefix}", "$options": "i"}
            }).distinct("goal")

            # Return unique goals (limited)
            return suggestions[:top_k]

        except Exception as e:
            logger.error(f"Suggestions error: {e}")
            return []

    # ── Search Analytics ──────────────────────────────────────────────────────

    async def log_search(
        self,
        user_id: str,
        query: str,
        search_type: str,
        result_count: int,
    ) -> None:
        """Log search query for analytics."""
        try:
            search_log = {
                "user_id": user_id,
                "query": query,
                "search_type": search_type,
                "result_count": result_count,
                "timestamp": datetime.now(),
            }

            await self.db["search_logs"].insert_one(search_log)

        except Exception as e:
            logger.error(f"Error logging search: {e}")

    async def get_popular_searches(
        self,
        user_id: str,
        days: int = 30,
        top_k: int = 10,
    ) -> List[Dict[str, Any]]:
        """Get user's most common searches."""
        try:
            from datetime import datetime, timedelta

            pipeline = [
                {
                    "$match": {
                        "user_id": user_id,
                        "timestamp": {
                            "$gte": datetime.now() - timedelta(days=days)
                        }
                    }
                },
                {
                    "$group": {
                        "_id": "$query",
                        "count": {"$sum": 1},
                        "last_search": {"$max": "$timestamp"}
                    }
                },
                {"$sort": {"count": -1}},
                {"$limit": top_k}
            ]

            results = await self.db["search_logs"].aggregate(pipeline).to_list(top_k)
            return results

        except Exception as e:
            logger.error(f"Error getting popular searches: {e}")
            return []


# ── Initialize Search Indexes ────────────────────────────────────────────────

async def initialize_search_indexes(db: AsyncIOMotorDatabase) -> None:
    """Initialize MongoDB text search indexes."""
    try:
        tasks_col = db["tasks"]

        # Create text index on goal
        await tasks_col.create_index([("goal", "text")])

        # Create compound index for filtering
        await tasks_col.create_index([
            ("user_id", 1),
            ("domain", 1),
            ("status", 1),
        ])

        logger.info("Search indexes initialized")

    except Exception as e:
        logger.error(f"Error initializing search indexes: {e}")


def get_hybrid_search_service(
    db: AsyncIOMotorDatabase,
    pinecone_service: Optional[Any] = None,
    embeddings_service: Optional[Any] = None,
) -> HybridSearchService:
    """Get hybrid search service instance."""
    if pinecone_service is None or embeddings_service is None:
        from services.pinecone_service import get_pinecone_service

        pinecone_service = pinecone_service or get_pinecone_service()
        embeddings_service = embeddings_service or pinecone_service

    return HybridSearchService(db, pinecone_service, embeddings_service)
