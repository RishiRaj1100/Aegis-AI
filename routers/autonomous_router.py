"""Unified autonomous decision intelligence endpoints."""

from __future__ import annotations

import logging
from csv import DictWriter
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Query

from core.autonomous_pipeline import AutonomousDecisionPipeline
from models.autonomous_schemas import (
    AnalyzeTaskRequest,
    DebateRequest,
    DebateResponse,
    ExplainabilityResponse,
    FeedbackRequest,
    FeedbackResponse,
    FinalDecisionResponse,
    ModelStatusResponse,
    SimilarTasksResponse,
)
from services.model_retraining_service import get_model_retraining_service
from services.mongodb_service import get_mongodb_service

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Autonomous Decision Intelligence"])

_recent_feedback: List[Dict[str, Any]] = []
_last_results: Dict[str, Dict[str, Any]] = {}
_feedback_store_path = Path("data") / "feedback_outcomes.csv"
_retrain_threshold = 100


def _extract_subtask_titles(result: Dict[str, Any]) -> List[str]:
    plan = result.get("execution_plan")
    if isinstance(plan, list):
        return [str(item) for item in plan if str(item).strip()]
    return []


def _append_feedback_row(row: Dict[str, Any]) -> None:
    _feedback_store_path.parent.mkdir(parents=True, exist_ok=True)
    file_exists = _feedback_store_path.exists()
    with _feedback_store_path.open("a", encoding="utf-8", newline="") as fh:
        writer = DictWriter(
            fh,
            fieldnames=["task_id", "predicted_success", "actual_outcome", "notes", "ts"],
        )
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)


def _read_feedback_file_count() -> int:
    if not _feedback_store_path.exists():
        return 0
    try:
        with _feedback_store_path.open("r", encoding="utf-8") as fh:
            lines = fh.readlines()
        return max(0, len(lines) - 1)
    except Exception:
        return 0


def _get_pipeline() -> AutonomousDecisionPipeline:
    from main import get_pipeline

    return AutonomousDecisionPipeline(get_pipeline())


@router.post("/analyze_task", response_model=FinalDecisionResponse)
async def analyze_task(request: AnalyzeTaskRequest, pipeline: AutonomousDecisionPipeline = Depends(_get_pipeline)):
    try:
        result = await pipeline.run(
            task=request.task,
            language=request.language,
            context=request.context,
            user_id=request.user_id,
        )
        _last_results[result["task_id"]] = result

        # Persist autonomous runs into task history for consistent dashboard retrieval.
        mongo = get_mongodb_service()
        now = datetime.utcnow()
        try:
            await mongo.insert_task(
                {
                    "task_id": result["task_id"],
                    "user_id": request.user_id,
                    "goal": request.task,
                    "status": "READY" if result.get("success_probability", 0.0) >= 0.5 else "AT_RISK",
                    "risk_level": result.get("risk_level", "UNKNOWN"),
                    "confidence": result.get("confidence", 0.0),
                    "execution_plan": result.get("execution_plan", []),
                    "subtasks": _extract_subtask_titles(result),
                    "decision": result.get("final_decision", ""),
                    "created_at": now,
                    "updated_at": now,
                }
            )
        except Exception:
            logger.debug("Task %s was not inserted into history (possibly duplicate).", result["task_id"])

        return result
    except Exception as exc:
        logger.exception("/analyze_task failed")
        raise HTTPException(status_code=500, detail=f"Analyze task failed: {exc}")


@router.post("/debate", response_model=DebateResponse)
async def debate(request: DebateRequest):
    from agents.debate_system import get_debate_system

    try:
        result = await get_debate_system().run_debate(request.task)
        return {
            "optimist": result.get("optimist", ""),
            "risk": result.get("risk", ""),
            "executor": result.get("executor", ""),
            "final_decision": result.get("final_decision", ""),
            "confidence": float(result.get("confidence", 0.5)),
        }
    except Exception as exc:
        logger.exception("/debate failed")
        raise HTTPException(status_code=500, detail=f"Debate failed: {exc}")


@router.post("/feedback", response_model=FeedbackResponse)
async def feedback(request: FeedbackRequest):
    feedback_row = {
        "task_id": request.task_id,
        "predicted_success": request.predicted_success,
        "actual_outcome": request.actual_outcome,
        "notes": request.notes,
        "ts": datetime.utcnow().isoformat(),
    }
    _recent_feedback.append(feedback_row)
    _append_feedback_row(feedback_row)

    mongo = get_mongodb_service()
    was_success = request.actual_outcome == "success"
    try:
        await mongo.record_outcome(
            task_id=request.task_id,
            status="COMPLETED" if was_success else "FAILED",
            outcome_notes=request.notes,
        )
    except Exception:
        logger.debug("Outcome persistence skipped for task_id=%s", request.task_id)

    # Keep only recent samples for trigger checks.
    cutoff = datetime.utcnow() - timedelta(days=30)
    retained = []
    for row in _recent_feedback:
        try:
            if datetime.fromisoformat(row["ts"]) >= cutoff:
                retained.append(row)
        except Exception:
            retained.append(row)
    _recent_feedback[:] = retained

    sample_count = max(len(_recent_feedback), _read_feedback_file_count())
    retrain_state = await get_model_retraining_service().trigger_if_needed(
        sample_count=sample_count,
        min_samples=_retrain_threshold,
    )
    retrain_triggered = retrain_state.get("status") == "started"
    return {
        "accepted": True,
        "retrain_triggered": retrain_triggered,
        "samples_count": sample_count,
    }


@router.get("/model_status", response_model=ModelStatusResponse)
async def model_status():
    retraining = get_model_retraining_service()
    samples_collected = max(len(_recent_feedback), _read_feedback_file_count())
    next_trigger_in = max(0, _retrain_threshold - samples_collected)
    return {
        "status": "running" if retraining.is_running else "idle",
        "last_run": retraining.last_run_iso,
        "samples_collected": samples_collected,
        "threshold": _retrain_threshold,
        "next_trigger_in": next_trigger_in,
    }


@router.get("/task_history")
async def task_history(limit: int = Query(default=20, ge=1, le=200)):
    mongo = get_mongodb_service()
    try:
        tasks = await mongo.list_tasks(limit=limit, skip=0)
        return {
            "items": tasks,
            "count": len(tasks),
            "cache_control": "no-store",
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Task history failed: {exc}")


@router.get("/execution_graph")
async def execution_graph(task_id: str):
    cached = _last_results.get(task_id)
    if cached is not None:
        return {
            "task_id": task_id,
            "graph": cached.get("execution_graph", {}),
            "cache_control": "no-store",
        }

    mongo = get_mongodb_service()
    task = await mongo.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    subtasks = task.get("subtasks", [])
    graph = {
        "nodes": [
            {"id": "task", "label": task.get("goal", "Task"), "type": "task"},
            {"id": "decision", "label": "Decision", "type": "decision"},
            {"id": "reflection", "label": "Reflection", "type": "reflection"},
        ]
        + [
            {"id": f"sub_{idx+1}", "label": (st.get("title") if isinstance(st, dict) else str(st)), "type": "task"}
            for idx, st in enumerate(subtasks)
        ],
        "edges": [
            {"source": "task", "target": f"sub_{idx+1}", "label": "decompose"}
            for idx, _ in enumerate(subtasks)
        ]
        + [{"source": "decision", "target": "reflection", "label": "learn"}],
    }
    return {"task_id": task_id, "graph": graph, "cache_control": "no-store"}


@router.get("/explainability", response_model=ExplainabilityResponse)
async def explainability(task_id: str):
    cached = _last_results.get(task_id)
    if cached is None:
        return {
            "task_id": task_id,
            "shap_values": {},
            "positive_factors": [],
            "negative_factors": [],
        }
    explain = cached.get("explainability", {})
    return {
        "task_id": task_id,
        "shap_values": explain.get("shap_values", {}),
        "positive_factors": explain.get("positive_factors", []),
        "negative_factors": explain.get("negative_factors", []),
    }


@router.get("/similar_tasks", response_model=SimilarTasksResponse)
async def similar_tasks(task: str = Query(min_length=3), top_k: int = Query(default=5, ge=1, le=20)):
    from services.retrieval_service import get_retrieval_service

    results = get_retrieval_service().search_similar(task, top_k=top_k)
    return {
        "tasks": [
            {
                "task": r.get("task", ""),
                "outcome": r.get("outcome", "unknown"),
                "similarity": float(r.get("similarity", 0.0)),
            }
            for r in results
        ]
    }
