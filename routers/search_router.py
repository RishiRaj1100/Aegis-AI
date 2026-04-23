"""
Hybrid Search API Router
Combines keyword and semantic search
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import Optional, List
import asyncio

from services.hybrid_search_service import (
    HybridSearchService,
    get_hybrid_search_service,
)

router = APIRouter(prefix="/api/search", tags=["search"])


async def get_db() -> AsyncIOMotorDatabase:
    """Get database instance."""
    from core.pipeline import get_database

    result = get_database()
    if asyncio.iscoroutinefunction(get_database):
        return await result
    return result


@router.get("/")
async def search(
    user_id: str,
    q: str = Query(..., description="Search query"),
    search_type: str = Query("hybrid", description="keyword, semantic, hybrid"),
    domain: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    top_k: int = Query(10, ge=1, le=50),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Search tasks with optional filters.
    
    Types:
    - keyword: MongoDB full-text search
    - semantic: Pinecone embeddings
    - hybrid: Combined approach
    """
    try:
        service = get_hybrid_search_service(db)

        # Build filters
        filters = {}
        if domain:
            filters["domain"] = domain
        if status:
            filters["status"] = status
        if priority:
            filters["priority"] = priority

        # Perform search
        if search_type == "keyword":
            results = await service.keyword_search(user_id, q, filters, top_k)
        elif search_type == "semantic":
            results = await service.semantic_search(user_id, q, filters, top_k)
        else:  # hybrid
            results = await service.hybrid_search(user_id, q, filters, top_k)

        # Log search
        await service.log_search(user_id, q, search_type, len(results))

        return {
            "status": "success",
            "query": q,
            "search_type": search_type,
            "count": len(results),
            "results": [
                {
                    "task_id": r.task_id,
                    "goal": r.goal,
                    "domain": r.domain,
                    "priority": r.priority,
                    "relevance_score": r.relevance_score,
                    "matched_fields": r.matched_fields,
                }
                for r in results
            ],
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/faceted")
async def search_faceted(
    user_id: str,
    q: str = Query(...),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Search with faceted results."""
    try:
        service = get_hybrid_search_service(db)

        results = await service.faceted_search(user_id, q)

        return {
            "status": "success",
            "query": q,
            "results": [
                {
                    "task_id": r.task_id,
                    "goal": r.goal,
                    "domain": r.domain,
                    "relevance_score": r.relevance_score,
                }
                for r in results["results"]
            ],
            "facets": results["facets"],
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/suggest")
async def search_suggestions(
    user_id: str,
    prefix: str = Query(..., description="Query prefix for autocomplete"),
    top_k: int = Query(5, ge=1, le=20),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Get search suggestions."""
    try:
        service = get_hybrid_search_service(db)

        suggestions = await service.get_search_suggestions(user_id, prefix, top_k)

        return {
            "status": "success",
            "prefix": prefix,
            "suggestions": suggestions,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/popular")
async def get_popular_searches(
    user_id: str,
    days: int = Query(30, ge=1, le=365),
    top_k: int = Query(10, ge=1, le=50),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Get user's popular searches."""
    try:
        service = get_hybrid_search_service(db)

        searches = await service.get_popular_searches(user_id, days, top_k)

        return {
            "status": "success",
            "period_days": days,
            "searches": searches,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
