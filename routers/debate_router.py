"""Debate API router for structured multi-agent reasoning."""

from __future__ import annotations

import logging
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from agents.debate_system import get_debate_system

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Debate"])


class DebateRequest(BaseModel):
    task: str = Field(min_length=5, max_length=2000, description="Task or goal to debate")


class DebateResponse(BaseModel):
    optimist: str
    risk: str
    executor: str
    critic: str
    final_decision: str
    confidence: float = Field(ge=0.0, le=1.0)


@router.post(
    "/debate",
    response_model=DebateResponse,
    status_code=status.HTTP_200_OK,
    summary="Run structured multi-agent debate",
)
async def debate_task(request: DebateRequest) -> Dict[str, Any]:
    try:
        system = get_debate_system()
        result = await system.run_debate(request.task)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.exception("POST /debate failed")
        raise HTTPException(status_code=500, detail=f"Debate failed: {exc}")
