"""
AegisAI - Intelligence Router
Future-facing execution intelligence, graphing, prediction, simulation,
workflow parsing, model registry, and reflection reporting.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, status

from models.schemas import (
    DriftReportResponse,
    ExecutionGraphResponse,
    GoalRequest,
    IntelligenceModelRecord,
    IntelligenceOverviewResponse,
    ManualOverrideRequest,
    ModelRegistryRequest,
    OutcomePredictionRequest,
    OutcomePredictionResponse,
    ReflectionReportResponse,
    SimilarTaskResponse,
    SimulationRequest,
    SimulationResponse,
    StrategyProfileResponse,
    WorkflowDslRequest,
)
from routers.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/intelligence", tags=["Intelligence"])


def _get_pipeline():
    from main import get_pipeline
    return get_pipeline()


def _user_id(payload: Dict[str, Any]) -> Optional[str]:
    return payload.get("sub") if isinstance(payload, dict) else None


@router.get("/overview", response_model=IntelligenceOverviewResponse, summary="Get intelligence overview")
async def overview(
    current_user: Dict[str, Any] = Depends(get_current_user),
    pipeline=Depends(_get_pipeline),
) -> IntelligenceOverviewResponse:
    return await pipeline.intelligence.overview(user_id=_user_id(current_user))


@router.get("/tasks", summary="Get recent tasks for lab feeds")
async def recent_tasks(
    limit: int = 15,
    current_user: Dict[str, Any] = Depends(get_current_user),
    pipeline=Depends(_get_pipeline),
) -> list[Dict[str, Any]]:
    tasks = await pipeline.intelligence._all_tasks(user_id=_user_id(current_user))
    return [{"task_id": str(t.get("task_id", "")), "goal": str(t.get("goal", "")), "status": str(t.get("status", "PENDING"))} for t in tasks[:limit]]


@router.get("/graph/{task_id}", response_model=ExecutionGraphResponse, summary="Get execution graph")
async def execution_graph(
    task_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    pipeline=Depends(_get_pipeline),
) -> ExecutionGraphResponse:
    try:
        return await pipeline.intelligence.build_execution_graph(task_id, user_id=_user_id(current_user))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.get("/similar/{task_id}", response_model=list[SimilarTaskResponse], summary="Find similar tasks")
async def similar_tasks(
    task_id: str,
    limit: int = 5,
    current_user: Dict[str, Any] = Depends(get_current_user),
    pipeline=Depends(_get_pipeline),
) -> list[SimilarTaskResponse]:
    try:
        return await pipeline.intelligence.find_similar_tasks(
            task_id=task_id,
            user_id=_user_id(current_user),
            limit=limit,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.post("/similar", response_model=list[SimilarTaskResponse], summary="Find similar tasks for a goal")
async def similar_for_goal(
    request: OutcomePredictionRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    pipeline=Depends(_get_pipeline),
) -> list[SimilarTaskResponse]:
    return await pipeline.intelligence.find_similar_tasks(
        goal=request.goal,
        user_id=_user_id(current_user),
    )


@router.get("/profile", response_model=StrategyProfileResponse, summary="Get user strategy profile")
async def strategy_profile(
    current_user: Dict[str, Any] = Depends(get_current_user),
    pipeline=Depends(_get_pipeline),
) -> StrategyProfileResponse:
    return await pipeline.intelligence.build_strategy_profile(user_id=_user_id(current_user))


@router.post("/predict", response_model=OutcomePredictionResponse, summary="Predict outcome")
async def predict_outcome(
    request: OutcomePredictionRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    pipeline=Depends(_get_pipeline),
) -> OutcomePredictionResponse:
    return await pipeline.intelligence.predict_outcome(
        goal=request.goal,
        context=request.context,
        user_id=_user_id(current_user),
    )


@router.post("/simulate", response_model=SimulationResponse, summary="Simulate an execution scenario")
async def simulate_execution(
    request: SimulationRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    pipeline=Depends(_get_pipeline),
) -> SimulationResponse:
    return await pipeline.intelligence.simulate_execution(
        goal=request.goal,
        context=request.context,
        scenario=request.scenario,
        user_id=_user_id(current_user),
    )


@router.post("/workflow/parse", summary="Parse workflow DSL")
async def parse_workflow(
    request: WorkflowDslRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    pipeline=Depends(_get_pipeline),
) -> Dict[str, Any]:
    return await pipeline.intelligence.parse_workflow(request.workflow, request.title)


@router.get("/models", response_model=list[IntelligenceModelRecord], summary="List registered models")
async def list_models(
    current_user: Dict[str, Any] = Depends(get_current_user),
    pipeline=Depends(_get_pipeline),
) -> list[Dict[str, Any]]:
    await pipeline.intelligence.upsert_default_model()
    return await pipeline.intelligence.list_models()


@router.post("/models", summary="Register or update a model")
async def register_model(
    request: ModelRegistryRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    pipeline=Depends(_get_pipeline),
) -> Dict[str, Any]:
    return await pipeline.intelligence.register_model(request.model_dump())


@router.post("/models/{model_id}/rollback", summary="Rollback to a registered model")
async def rollback_model(
    model_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    pipeline=Depends(_get_pipeline),
) -> Dict[str, Any]:
    try:
        return await pipeline.intelligence.rollback_model(model_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.get("/drift", response_model=DriftReportResponse, summary="Get drift report")
async def drift_report(
    current_user: Dict[str, Any] = Depends(get_current_user),
    pipeline=Depends(_get_pipeline),
) -> DriftReportResponse:
    return await pipeline.intelligence.compute_drift(user_id=_user_id(current_user))


@router.post("/reflection/report", response_model=ReflectionReportResponse, summary="Generate reflection report")
async def reflection_report(
    current_user: Dict[str, Any] = Depends(get_current_user),
    pipeline=Depends(_get_pipeline),
) -> ReflectionReportResponse:
    return await pipeline.intelligence.refresh_reflection_report(sample_size=20)


@router.post("/override", summary="Record human override decision")
async def manual_override(
    request: ManualOverrideRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    pipeline=Depends(_get_pipeline),
) -> Dict[str, Any]:
    return await pipeline.intelligence.save_manual_override(request.task_id, request.decision, request.notes)


@router.get("/memory-graph", response_model=ExecutionGraphResponse, summary="Get global memory experience graph")
async def memory_graph(
    current_user: Dict[str, Any] = Depends(get_current_user),
    pipeline=Depends(_get_pipeline),
) -> ExecutionGraphResponse:
    return await pipeline.intelligence.build_memory_graph(user_id=_user_id(current_user))


@router.post("/followup", summary="Multimodal follow-up discussion")
async def follow_up(
    request: Dict[str, Any],
    current_user: Dict[str, Any] = Depends(get_current_user),
    pipeline=Depends(_get_pipeline),
) -> Dict[str, Any]:
    task_id = request.get("task_id")
    message = request.get("message")
    language = request.get("language", "en-IN")
    
    if not task_id or not message:
        raise HTTPException(status_code=400, detail="task_id and message are required")
        
    return await pipeline.process_followup(
        task_id=task_id,
        message=message,
        language=language,
        user_id=_user_id(current_user)
    )


@router.get("/health", summary="Intelligence health")
async def intelligence_health(
    current_user: Dict[str, Any] = Depends(get_current_user),
    pipeline=Depends(_get_pipeline),
) -> Dict[str, Any]:
    overview = await pipeline.intelligence.overview(user_id=_user_id(current_user))
    drift = await pipeline.intelligence.compute_drift(user_id=_user_id(current_user))

    def _dump(value: Any) -> Any:
        return value.model_dump() if hasattr(value, "model_dump") else value

    return {
        "status": "healthy",
        "overview": _dump(overview),
        "drift": _dump(drift),
    }
