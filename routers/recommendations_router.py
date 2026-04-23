"""
Recommendations API Router
Endpoints for personalized task recommendations
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List, Optional
import asyncio

from services.recommendations_service import RecommendationsEngine, Recommendation

router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])


def _require_user_id(user_id: str) -> str:
    user_id = (user_id or "").strip()
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id is required.")
    return user_id


async def get_db() -> AsyncIOMotorDatabase:
    """Get database instance."""
    from core.pipeline import get_database

    result = get_database()
    if asyncio.iscoroutinefunction(get_database):
        return await result
    return result


async def get_recommendations_service(
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> RecommendationsEngine:
    """Get recommendations service."""
    return RecommendationsEngine(db)


@router.get("/for-user")
async def get_recommendations_for_user(
    user_id: str,
    strategy: str = Query("hybrid", description="Strategy: hybrid, content, collaborative, historical"),
    top_k: int = Query(10, ge=1, le=50),
    service: RecommendationsEngine = Depends(get_recommendations_service),
):
    """
    Get personalized recommendations for user.
    
    Strategies:
    - hybrid: Combine all strategies (best results)
    - content: Text-based similarity
    - historical: User's past patterns
    - collaborative: Similar users' tasks
    """
    try:
        user_id = _require_user_id(user_id)
        recommendations = await service.get_recommendations_for_user(
            user_id=user_id,
            top_k=top_k,
            strategy=strategy,
        )

        return {
            "status": "success",
            "strategy": strategy,
            "count": len(recommendations),
            "recommendations": [
                {
                    "task_id": rec.task_id,
                    "goal": rec.goal,
                    "domain": rec.domain,
                    "similarity_score": rec.similarity_score,
                    "reason": rec.reason,
                }
                for rec in recommendations
            ],
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/similar/{task_id}")
async def get_similar_tasks(
    user_id: str,
    task_id: str,
    top_k: int = Query(5, ge=1, le=20),
    service: RecommendationsEngine = Depends(get_recommendations_service),
):
    """Get tasks similar to a specific task."""
    try:
        user_id = _require_user_id(user_id)
        recommendations = await service.get_similar_tasks(
            user_id=user_id,
            task_id=task_id,
            top_k=top_k,
        )

        return {
            "status": "success",
            "source_task_id": task_id,
            "count": len(recommendations),
            "similar_tasks": [
                {
                    "task_id": rec.task_id,
                    "goal": rec.goal,
                    "similarity_score": rec.similarity_score,
                }
                for rec in recommendations
            ],
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/check-duplicate")
async def check_duplicate_task(
    user_id: str,
    goal: str,
    service: RecommendationsEngine = Depends(get_recommendations_service),
):
    """Check if task is duplicate."""
    try:
        user_id = _require_user_id(user_id)
        duplicate = await service.detect_duplicate_task(user_id=user_id, goal=goal)

        return {
            "status": "success",
            "is_duplicate": duplicate is not None,
            "duplicate": duplicate,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/log-click")
async def log_recommendation_click(
    user_id: str,
    recommended_task_id: str,
    clicked: bool = True,
    service: RecommendationsEngine = Depends(get_recommendations_service),
):
    """Log recommendation interaction."""
    try:
        user_id = _require_user_id(user_id)
        await service.log_recommendation(
            user_id=user_id,
            recommended_task_id=recommended_task_id,
            clicked=clicked,
        )

        return {
            "status": "success",
            "message": "Recommendation logged",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_recommendation_stats(
    user_id: str,
    service: RecommendationsEngine = Depends(get_recommendations_service),
):
    """Get recommendation statistics."""
    try:
        user_id = _require_user_id(user_id)
        stats = await service.get_recommendation_stats(user_id=user_id)

        return {
            "status": "success",
            "stats": stats,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
