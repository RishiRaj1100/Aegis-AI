"""
AegisAI - Plan Router
GET /plan/{task_id}               – Retrieve the full execution plan for a task.
GET /plan/{task_id}/subtasks      – List individual subtasks.
GET /plan/{task_id}/translate     – Get plan translated to a specified language.
GET /plan/list                    – Paginated list of all stored plans.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from models.schemas import PlanResponse, SupportedLanguage
from routers.auth import get_current_user, require_current_user_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/plan", tags=["Plan"])


def _get_pipeline():
    from main import get_pipeline
    return get_pipeline()


def _get_sarvam():
    from services.sarvam_service import get_sarvam_service
    return get_sarvam_service()


# ── GET /plan/list ─────────────────────────────────────────────────────────────

@router.get(
    "/list",
    status_code=status.HTTP_200_OK,
    summary="List all stored plans",
    description="Returns a paginated list of all task plans stored in MongoDB.",
)
async def list_plans(
    limit: int = Query(default=20, ge=1, le=100),
    skip: int = Query(default=0, ge=0),
    status_filter: Optional[str] = Query(default=None, alias="status"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    pipeline=Depends(_get_pipeline),
) -> Dict[str, Any]:
    user_id = require_current_user_id(current_user)
    tasks = await pipeline.memory.mongo.list_tasks(limit=limit, skip=skip, status=status_filter, user_id=user_id)
    return {
        "total_returned": len(tasks),
        "limit": limit,
        "skip": skip,
        "tasks": [
            {
                "task_id": t.get("task_id"),
                "goal": t.get("goal", "")[:120],
                "confidence": t.get("confidence"),
                "risk_level": t.get("risk_level"),
                "status": t.get("status"),
                "created_at": t.get("created_at"),
            }
            for t in tasks
        ],
    }


# ── GET /plan  (alias for list) ────────────────────────────────────────────────

@router.get(
    "",
    status_code=status.HTTP_200_OK,
    summary="List all stored plans (root alias)",
    include_in_schema=False,
)
async def get_plan_root(
    limit: int = Query(default=20, ge=1, le=100),
    skip: int = Query(default=0, ge=0),
    status_filter: Optional[str] = Query(default=None, alias="status"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    pipeline=Depends(_get_pipeline),
):
    user_id = require_current_user_id(current_user)
    tasks = await pipeline.memory.mongo.list_tasks(limit=limit, skip=skip, status=status_filter, user_id=user_id)
    return {
        "total_returned": len(tasks),
        "limit": limit,
        "skip": skip,
        "tasks": [
            {
                "task_id": t.get("task_id"),
                "goal": t.get("goal", "")[:120],
                "confidence": t.get("confidence"),
                "risk_level": t.get("risk_level"),
                "status": t.get("status"),
                "created_at": t.get("created_at"),
            }
            for t in tasks
        ],
    }


# ── GET /plan/{task_id} ────────────────────────────────────────────────────────

@router.get(
    "/{task_id}",
    status_code=status.HTTP_200_OK,
    summary="Get execution plan for a task",
    description="Retrieve the full execution plan, subtasks, confidence score, and reasoning for a previously submitted goal.",
)
async def get_plan(
    task_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    pipeline=Depends(_get_pipeline),
) -> Dict[str, Any]:
    """Fetch a stored task plan from MongoDB (via MemoryAgent Redis/Mongo cache)."""
    user_id = require_current_user_id(current_user)
    task_doc = await pipeline.memory.get_task(task_id, user_id=user_id)
    if not task_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task '{task_id}' not found.",
        )

    return {
        "task_id": task_doc["task_id"],
        "goal": task_doc.get("goal", ""),
        "subtasks": task_doc.get("subtasks", []),
        "research_insights": task_doc.get("research_insights", ""),
        "execution_plan": task_doc.get("execution_plan", ""),
        "confidence": task_doc.get("confidence", 0.0),
        "risk_level": task_doc.get("risk_level", "MEDIUM"),
        "reasoning": task_doc.get("reasoning", ""),
        "status": task_doc.get("status", "PENDING"),
        "language": task_doc.get("language", "en-IN"),
        "explainability": task_doc.get("explainability", {}),
        "reflection": task_doc.get("reflection_data", {}),
        "debate_results": task_doc.get("debate_results", {}),
        "created_at": task_doc.get("created_at", ""),
        "updated_at": task_doc.get("updated_at", ""),
    }


# ── GET /plan/{task_id}/subtasks ───────────────────────────────────────────────

@router.get(
    "/{task_id}/subtasks",
    status_code=status.HTTP_200_OK,
    summary="List subtasks for a task",
    description="Returns the decomposed subtask list with priorities, durations, and dependencies.",
)
async def get_subtasks(
    task_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    pipeline=Depends(_get_pipeline),
) -> Dict[str, Any]:
    user_id = require_current_user_id(current_user)
    task_doc = await pipeline.memory.get_task(task_id, user_id=user_id)
    if not task_doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Task '{task_id}' not found.")

    subtasks = task_doc.get("subtasks", [])
    return {
        "task_id": task_id,
        "goal": task_doc.get("goal", ""),
        "subtask_count": len(subtasks),
        "subtasks": subtasks,
    }


# ── GET /plan/{task_id}/translate ──────────────────────────────────────────────

@router.get(
    "/{task_id}/translate",
    status_code=status.HTTP_200_OK,
    summary="Translate execution plan",
    description="Returns the execution plan and research insights translated into the specified target language via Sarvam AI.",
)
async def translate_plan(
    task_id: str,
    target_language: SupportedLanguage = Query(
        default=SupportedLanguage.HI,
        description="Target language for translation.",
    ),
    current_user: Dict[str, Any] = Depends(get_current_user),
    pipeline=Depends(_get_pipeline),
    sarvam=Depends(_get_sarvam),
) -> Dict[str, Any]:
    user_id = require_current_user_id(current_user)
    task_doc = await pipeline.memory.get_task(task_id, user_id=user_id)
    if not task_doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Task '{task_id}' not found.")

    source_lang = task_doc.get("language", "en-IN")
    target_lang = target_language.value

    execution_plan = task_doc.get("execution_plan", "")
    research_insights = task_doc.get("research_insights", "")

    try:
        translated_plan = await sarvam.translate(
            text=execution_plan[:2000],  # Sarvam has a character limit per request
            source_language_code=source_lang,
            target_language_code=target_lang,
        )
        translated_insights = await sarvam.translate(
            text=research_insights[:1000],
            source_language_code=source_lang,
            target_language_code=target_lang,
        )
    except Exception as exc:
        logger.warning("Translation failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Sarvam translation service error: {exc}",
        )

    return {
        "task_id": task_id,
        "source_language": source_lang,
        "target_language": target_lang,
        "translated_execution_plan": translated_plan,
        "translated_research_insights": translated_insights,
        "confidence": task_doc.get("confidence", 0.0),
        "risk_level": task_doc.get("risk_level", "MEDIUM"),
    }


