"""
AegisAI - Confidence Router
GET /confidence/{task_id}            – Retrieve the full trust score for a task.
GET /confidence/{task_id}/components – Individual trust formula components.
GET /confidence/stats                – Aggregate stats across all tasks.
POST /confidence/{task_id}/refresh   – Re-evaluate confidence using fresh history.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status

from config.settings import get_settings
from models.schemas import ConfidenceResponse, TrustComponents
from routers.auth import get_current_user, require_current_user_id
from utils.helpers import utcnow

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/confidence", tags=["Confidence"])

settings = get_settings()

_TRUST_COMPONENT_WEIGHTS = {
    "goal_clarity": settings.TRUST_WEIGHT_GOAL_CLARITY,
    "information_quality": settings.TRUST_WEIGHT_INFORMATION_QUALITY,
    "execution_feasibility": settings.TRUST_WEIGHT_EXECUTION_FEASIBILITY,
    "risk_manageability": settings.TRUST_WEIGHT_RISK_MANAGEABILITY,
    "resource_adequacy": settings.TRUST_WEIGHT_RESOURCE_ADEQUACY,
    "external_uncertainty": settings.TRUST_WEIGHT_EXTERNAL_UNCERTAINTY,
}


def _get_pipeline():
    from main import get_pipeline
    return get_pipeline()


def _clamp_component(value: Any, default: float = 0.5) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return default


def _normalise_trust_components(raw: Dict[str, Any]) -> TrustComponents:
    """
    Normalise trust components to the current six-dimension schema.

    Supports legacy 4D payloads stored before the trust-model upgrade.
    """
    source = raw or {}
    return TrustComponents(
        goal_clarity=_clamp_component(source.get("goal_clarity", 0.5)),
        information_quality=_clamp_component(
            source.get("information_quality", source.get("data_completeness", 0.5))
        ),
        execution_feasibility=_clamp_component(
            source.get("execution_feasibility", source.get("task_feasibility", 0.5))
        ),
        risk_manageability=_clamp_component(source.get("risk_manageability", 0.5)),
        resource_adequacy=_clamp_component(source.get("resource_adequacy", 0.5)),
        external_uncertainty=_clamp_component(
            source.get("external_uncertainty", source.get("complexity_inverse", 0.5))
        ),
    )


# ── GET /confidence/{task_id} ──────────────────────────────────────────────────

@router.get(
    "/{task_id}",
    response_model=ConfidenceResponse,
    status_code=status.HTTP_200_OK,
    summary="Get confidence score for a task",
    description=(
        "Returns the full trust score: confidence percentage (0–100), "
        "risk level (LOW/MEDIUM/HIGH), individual trust components, and LLM reasoning."
    ),
)
async def get_confidence(
    task_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    pipeline=Depends(_get_pipeline),
) -> ConfidenceResponse:
    # Fast path: Redis cache
    cached = await pipeline.memory.get_cached_confidence(task_id)

    if cached and "confidence" in cached and cached.get("components"):
        components = _normalise_trust_components(cached["components"])
        return ConfidenceResponse(
            task_id=task_id,
            confidence=cached["confidence"],
            risk_level=cached["risk_level"],
            components=components,
            reasoning=cached.get("reasoning", ""),
            updated_at=utcnow(),
        )

    # Slow path: MongoDB
    user_id = require_current_user_id(current_user)
    task_doc = await pipeline.memory.get_task(task_id, user_id=user_id)
    if not task_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task '{task_id}' not found.",
        )

    trust_components_raw = task_doc.get("trust_components", {})
    components = _normalise_trust_components(trust_components_raw)

    return ConfidenceResponse(
        task_id=task_id,
        confidence=task_doc.get("confidence", 0.0),
        risk_level=task_doc.get("risk_level", "MEDIUM"),
        components=components,
        reasoning=task_doc.get("reasoning", ""),
        updated_at=task_doc.get("updated_at", utcnow()),
    )


# ── GET /confidence/{task_id}/components ──────────────────────────────────────

@router.get(
    "/{task_id}/components",
    status_code=status.HTTP_200_OK,
    summary="Get individual trust components",
    description="Returns the six trust dimensions and their weighted contributions.",
)
async def get_confidence_components(
    task_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    pipeline=Depends(_get_pipeline),
) -> Dict[str, Any]:
    user_id = require_current_user_id(current_user)
    task_doc = await pipeline.memory.get_task(task_id, user_id=user_id)
    if not task_doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Task '{task_id}' not found.")

    tc = task_doc.get("trust_components", {})
    confidence = float(task_doc.get("confidence", 0.0))

    normalised = _normalise_trust_components(tc)
    components = normalised.model_dump()
    weights = dict(_TRUST_COMPONENT_WEIGHTS)
    contributions = {
        k: round(components[k] * weights[k] * 100, 2)
        for k in components
    }

    uses_legacy_keys = any(
        key in tc for key in ["past_success_rate", "data_completeness", "task_feasibility", "complexity_inverse"]
    )

    return {
        "task_id": task_id,
        "final_confidence": confidence,
        "risk_level": task_doc.get("risk_level", "MEDIUM"),
        "formula": (
            "confidence = (goal_clarity×0.15) + (information_quality×0.20) + "
            "(execution_feasibility×0.25) + (risk_manageability×0.15) + "
            "(resource_adequacy×0.15) + (external_uncertainty×0.10)"
        ),
        "legacy_component_mapping_applied": uses_legacy_keys,
        "components": components,
        "weights": weights,
        "weighted_contributions_to_100": contributions,
    }


# ── GET /confidence/stats ──────────────────────────────────────────────────────

@router.get(
    "/stats/summary",
    status_code=status.HTTP_200_OK,
    summary="Aggregate confidence statistics",
    description="Returns system-wide confidence statistics across all stored tasks.",
)
async def confidence_stats(
    current_user: Dict[str, Any] = Depends(get_current_user),
    pipeline=Depends(_get_pipeline),
) -> Dict[str, Any]:
    user_id = require_current_user_id(current_user)
    tasks = await pipeline.memory.mongo.list_tasks(limit=200, user_id=user_id)
    if not tasks:
        return {"message": "No tasks found.", "total_tasks": 0}

    confidences = [float(t.get("confidence", 0)) for t in tasks]
    risk_counts: Dict[str, int] = {"LOW": 0, "MEDIUM": 0, "HIGH": 0}
    for t in tasks:
        rl = t.get("risk_level", "MEDIUM")
        risk_counts[rl] = risk_counts.get(rl, 0) + 1

    avg_conf = sum(confidences) / len(confidences)
    past_success_rate = await pipeline.memory.get_past_success_rate()

    return {
        "total_tasks": len(tasks),
        "average_confidence": round(avg_conf, 2),
        "max_confidence": round(max(confidences), 2),
        "min_confidence": round(min(confidences), 2),
        "past_success_rate_pct": round(past_success_rate * 100, 1),
        "risk_distribution": risk_counts,
    }


# ── POST /confidence/{task_id}/refresh ────────────────────────────────────────

@router.post(
    "/{task_id}/refresh",
    status_code=status.HTTP_200_OK,
    summary="Refresh confidence score using latest history",
    description=(
        "Re-evaluates the confidence score for an existing task using the most recent "
        "past success rate from the MongoDB outcome history, then updates the stored score."
    ),
)
async def refresh_confidence(
    task_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    pipeline=Depends(_get_pipeline),
) -> Dict[str, Any]:
    user_id = require_current_user_id(current_user)
    task_doc = await pipeline.memory.get_task(task_id, user_id=user_id)
    if not task_doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Task '{task_id}' not found.")

    tc = task_doc.get("trust_components", {})
    fresh_success_rate = await pipeline.memory.get_past_success_rate()

    information_quality = tc.get("information_quality", tc.get("data_completeness", 0.5))
    execution_feasibility = tc.get("execution_feasibility", tc.get("task_feasibility", 0.5))
    external_uncertainty = tc.get("external_uncertainty", tc.get("complexity_inverse", 0.5))

    trust_score = await pipeline.trust.evaluate(
        past_success_rate=fresh_success_rate,
        data_completeness=information_quality,
        task_feasibility=execution_feasibility,
        complexity_score=1.0 - external_uncertainty,
        goal=task_doc.get("goal", ""),
        goal_summary=task_doc.get("goal", "")[:120],
    )

    await pipeline.memory.update_task(
        task_id,
        {
            "confidence": trust_score.confidence,
            "risk_level": trust_score.risk_level.value,
            "trust_components": trust_score.components.model_dump(),
            "reasoning": trust_score.reasoning,
        },
    )
    await pipeline.memory.cache_confidence(
        task_id,
        {
            "task_id": task_id,
            "confidence": trust_score.confidence,
            "risk_level": trust_score.risk_level.value,
            "components": trust_score.components.model_dump(),
            "reasoning": trust_score.reasoning,
            "updated_at": utcnow().isoformat(),
        },
    )

    return {
        "task_id": task_id,
        "previous_confidence": task_doc.get("confidence", 0.0),
        "updated_confidence": trust_score.confidence,
        "risk_level": trust_score.risk_level.value,
        "message": "Confidence score refreshed with latest outcome history.",
    }
