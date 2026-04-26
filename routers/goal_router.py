"""
AegisAI - Goal Router
POST /goal          – Submit a text-based goal for end-to-end processing.
POST /goal/voice    – Submit a base64-encoded audio goal.
PUT  /goal/outcome  – Record the real-world outcome of a processed task.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from groq import APIStatusError, RateLimitError

from core.pipeline import AegisAIPipeline
from routers.auth import get_current_user, require_current_user_id
from models.schemas import (
    FollowUpRequest,
    FollowUpResponse,
    GoalRequest,
    GoalResponse,
    OutcomeUpdateRequest,
    VoiceGoalRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/goal", tags=["Goal"])


def _get_pipeline() -> AegisAIPipeline:
    """Import here to avoid circular imports — resolved at runtime via app state."""
    from main import get_pipeline
    return get_pipeline()


# ── POST /goal ─────────────────────────────────────────────────────────────────

@router.post(
    "/analyze_task",
    response_model=GoalResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Submit a text-based goal (alias)",
)
@router.post(
    "",
    response_model=GoalResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Submit a text-based goal",
    description=(
        "Submits a natural-language goal for full AegisAI pipeline processing. "
        "Returns the decomposed plan, execution steps, confidence score, risk level, and reasoning."
    ),
)
async def submit_goal(
    request: GoalRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    pipeline: AegisAIPipeline = Depends(_get_pipeline),
) -> GoalResponse:
    """
    End-to-end processing pipeline:
    Commander → Research → Execution → Trust → Memory → Reflection.
    """
    user_id = require_current_user_id(current_user)
    try:
        response = await pipeline.process_goal(request, user_id=user_id)
        return response
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except RateLimitError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The AI service is temporarily rate-limited. Please wait a minute and try again.",
        )
    except APIStatusError as exc:
        msg = str(exc)
        if "rate_limit_exceeded" in msg or "tokens per minute" in msg or "Request too large" in msg:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=(
                    "The request exceeded current AI token limits. "
                    "Please shorten your goal/context and retry in a minute."
                ),
            )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The AI provider returned an error. Please retry shortly.",
        )
    except Exception as exc:
        logger.exception("Unhandled error in POST /goal")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Pipeline processing failed: {exc}",
        )


# ── POST /goal/voice ───────────────────────────────────────────────────────────

@router.post(
    "/voice",
    response_model=GoalResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Submit a voice-based goal",
    description=(
        "Accepts base64-encoded audio (WAV/MP3). The audio is first transcribed "
        "via Sarvam STT, then processed through the full AegisAI pipeline. "
        "A TTS audio response is included in the reply."
    ),
)
async def submit_voice_goal(
    request: VoiceGoalRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    pipeline: AegisAIPipeline = Depends(_get_pipeline),
) -> GoalResponse:
    """Voice → STT → AegisAI pipeline → TTS response."""
    if not request.audio_base64 or not request.audio_base64.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="audio_base64 must not be empty.",
        )
    user_id = require_current_user_id(current_user)
    try:
        response = await pipeline.process_voice_goal(
            audio_base64=request.audio_base64,
            language=request.language.value,
            audio_format=request.audio_format,
            context=request.context,
            user_id=user_id,
        )
        return response
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except RateLimitError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The AI service is temporarily rate-limited. Please wait a minute and try again.",
        )
    except APIStatusError as exc:
        msg = str(exc)
        if "rate_limit_exceeded" in msg or "tokens per minute" in msg or "Request too large" in msg:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=(
                    "The voice request exceeded current AI token limits. "
                    "Please retry with a shorter prompt in a minute."
                ),
            )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The AI provider returned an error. Please retry shortly.",
        )
    except Exception as exc:
        logger.exception("Unhandled error in POST /goal/voice")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Voice pipeline failed: {exc}",
        )


# ── PUT /goal/outcome ──────────────────────────────────────────────────────────

@router.put(
    "/outcome",
    status_code=status.HTTP_200_OK,
    summary="Record the real-world outcome of a task",
    description=(
        "After a task has been acted upon, record whether it COMPLETED or FAILED. "
        "Triggers a per-task reflection for continuous learning."
    ),
)
async def record_outcome(
    request: OutcomeUpdateRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    pipeline: AegisAIPipeline = Depends(_get_pipeline),
) -> Dict[str, Any]:
    """Record outcome and trigger Reflection Agent."""
    user_id = require_current_user_id(current_user)
    success = await pipeline.record_outcome(
        task_id=str(request.task_id),
        status=request.status,
        outcome_notes=request.outcome_notes,
        actual_duration_minutes=request.actual_duration_minutes,
        user_id=user_id,
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {request.task_id} not found or could not be updated.",
        )
    return {
        "task_id": str(request.task_id),
        "status": request.status.value,
        "message": "Outcome recorded successfully. Reflection agent updated.",
    }


# ── POST /goal/followup ───────────────────────────────────────────────────────────────

@router.post(
    "/followup",
    response_model=FollowUpResponse,
    status_code=status.HTTP_200_OK,
    summary="Ask a follow-up question about a processed task",
    description=(
        "Send a text or voice follow-up question about any previously processed task. "
        "AegisAI answers in the user's selected language and returns a TTS audio reply."
    ),
)
async def followup(
    request: FollowUpRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    pipeline: AegisAIPipeline = Depends(_get_pipeline),
) -> FollowUpResponse:
    """Interactive follow-up on an existing task in any supported language."""
    if not request.message.strip() and not request.audio_base64:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either 'message' (text) or 'audio_base64' must be provided.",
        )
    user_id = require_current_user_id(current_user)
    try:
        result = await pipeline.process_followup(
            task_id=request.task_id,
            message=request.message,
            language=request.language.value,
            audio_base64=request.audio_base64,
            audio_format=request.audio_format,
            user_id=user_id,
        )
        return FollowUpResponse(
            task_id=request.task_id,
            reply=result["reply"],
            language=request.language.value,
            audio_base64=result.get("audio_base64"),
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Unhandled error in POST /goal/followup")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Follow-up processing failed: {exc}",
        )
