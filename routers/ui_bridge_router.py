"""
UI bridge routes for the new aegisai-source frontend.
These endpoints preserve the frontend API contract without changing UI code.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel, Field

from models.schemas import GoalRequest, InputModality, SupportedLanguage

logger = logging.getLogger(__name__)

router = APIRouter(tags=["UI Bridge"])


class TaskInput(BaseModel):
    task: str = Field(min_length=5, max_length=2000)
    language: Literal["en", "hi"] = "en"


class SimilarTaskOut(BaseModel):
    id: str
    title: str
    outcome: Literal["success", "partial", "failed"]
    similarity: float


class AgentDebateOut(BaseModel):
    optimist: str
    risk: str
    final_decision: str


class LogOut(BaseModel):
    ts: str
    level: Literal["info", "warn", "error", "success"]
    source: str
    message: str


class MemoryNodeOut(BaseModel):
    id: str
    label: str
    weight: float
    group: Literal["task", "context", "outcome"]


class TaskOutput(BaseModel):
    decision: str
    success_probability: float
    risk_level: Literal["low", "medium", "high"]
    explanation: str
    similar_tasks: List[SimilarTaskOut]
    agent_debate: AgentDebateOut
    workflow: str
    logs: List[LogOut]
    memory_nodes: List[MemoryNodeOut]
    subtasks: List[str]


class FeedbackInput(BaseModel):
    decision: str
    rating: Literal["up", "down"]
    note: Optional[str] = None


def _get_pipeline():
    # Runtime import avoids circular import on app startup.
    from main import get_pipeline

    return get_pipeline()


def _map_language(lang: Literal["en", "hi"]) -> SupportedLanguage:
    return SupportedLanguage.EN if lang == "en" else SupportedLanguage.HI


def _map_risk_level(risk_level: Any) -> Literal["low", "medium", "high"]:
    value = str(risk_level).upper()
    if value.endswith("LOW"):
        return "low"
    if value.endswith("HIGH"):
        return "high"
    return "medium"


@router.post("/task", response_model=TaskOutput, status_code=status.HTTP_200_OK)
async def ui_task(request: TaskInput):
    pipeline = _get_pipeline()

    try:
        goal_request = GoalRequest(
            goal=request.task,
            language=_map_language(request.language),
            modality=InputModality.TEXT,
            context=None,
        )
        goal_response = await pipeline.process_goal(goal_request, user_id=None)
    except Exception as exc:
        logger.exception("UI bridge /task failed")
        raise HTTPException(status_code=500, detail=f"Task processing failed: {exc}")

    plan = goal_response.plan
    if plan is None:
        raise HTTPException(status_code=500, detail="Task completed without plan payload")

    probability = max(0.0, min(1.0, float(plan.confidence) / 100.0))

    decision_text = plan.execution_plan.strip() or plan.research_insights.strip() or plan.reasoning.strip()

    subtasks = [s.title for s in plan.subtasks]
    now_iso = plan.created_at.isoformat()

    return TaskOutput(
        decision=decision_text,
        success_probability=probability,
        risk_level=_map_risk_level(plan.risk_level),
        explanation=plan.reasoning,
        similar_tasks=[],
        agent_debate=AgentDebateOut(
            optimist="Execution indicators are favorable for a staged rollout.",
            risk="Primary risks are manageable with guardrails and monitoring.",
            final_decision=decision_text,
        ),
        workflow=(
            "flowchart TD\n"
            "  A([Goal Intake]) --> B[Commander]\n"
            "  B --> C[Research]\n"
            "  C --> D[Execution Plan]\n"
            "  D --> E[Trust Evaluation]\n"
            "  E --> F[Memory + Reflection]\n"
            "  F --> G([Decision Output])"
        ),
        logs=[
            LogOut(ts=now_iso, level="info", source="goal", message="Goal accepted"),
            LogOut(ts=now_iso, level="success", source="pipeline", message="Decision synthesized"),
        ],
        memory_nodes=[
            MemoryNodeOut(id="n1", label="Goal", weight=1.0, group="task"),
            MemoryNodeOut(id="n2", label="Research", weight=0.8, group="context"),
            MemoryNodeOut(id="n3", label="Risk", weight=0.75, group="context"),
            MemoryNodeOut(id="n4", label="Outcome", weight=probability, group="outcome"),
        ],
        subtasks=subtasks,
    )


@router.post("/voice-input", status_code=status.HTTP_200_OK)
async def ui_voice_input(
    audio: UploadFile = File(...),
    language: Literal["en", "hi"] = Form("en"),
):
    audio_bytes = await audio.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Audio payload is empty")

    try:
        from services.sarvam_service import get_sarvam_service

        sarvam = get_sarvam_service()
        transcript = await sarvam.speech_to_text(
            audio_bytes=audio_bytes,
            language_code="hi-IN" if language == "hi" else "en-IN",
            audio_format=(audio.content_type or "audio/webm").split("/")[-1],
        )
    except Exception as exc:
        logger.warning("UI bridge /voice-input failed, returning empty transcript: %s", exc)
        transcript = ""

    return {
        "transcript": transcript,
        "detected_language": language,
    }


@router.post("/feedback", status_code=status.HTTP_204_NO_CONTENT)
async def ui_feedback(payload: FeedbackInput):
    logger.info("UI feedback received | rating=%s | note=%s", payload.rating, bool(payload.note))
    return None
