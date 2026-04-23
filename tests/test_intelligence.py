from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

import pytest
from fastapi import FastAPI, Header, HTTPException, status
from fastapi.testclient import TestClient

from routers.auth import get_current_user
from routers import intelligence_router


class _FakeIntelligence:
    def __init__(self) -> None:
        self.calls: List[Dict[str, Any]] = []

    async def overview(self, user_id: str | None = None):
        self.calls.append({"method": "overview", "user_id": user_id})
        return {
            "total_tasks": 3,
            "total_models": 1,
            "total_reports": 2,
            "active_model": "Catalyst Heuristic v1",
            "average_confidence": 67.5,
            "recent_success_rate": 0.66,
            "drift_score": 0.12,
            "scheduled_reflection_status": "active",
            "human_review_queue_size": 1,
        }

    async def build_execution_graph(self, task_id: str, user_id: str | None = None):
        self.calls.append({"method": "build_execution_graph", "task_id": task_id, "user_id": user_id})
        return {
            "task_id": task_id,
            "goal": "Ship a feature",
            "nodes": [{"id": "goal", "label": "Ship a feature", "type": "goal", "status": "IN_PROGRESS"}],
            "edges": [],
            "mermaid": "graph TD\n  goal[\"Ship a feature\"]",
        }

    async def find_similar_tasks(self, task_id: str | None = None, goal: str | None = None, user_id: str | None = None, limit: int = 5):
        self.calls.append({"method": "find_similar_tasks", "task_id": task_id, "goal": goal, "user_id": user_id, "limit": limit})
        return [
            {
                "task_id": "task-2",
                "goal": "Ship a similar feature",
                "confidence": 73.0,
                "risk_level": "LOW",
                "similarity": 0.8,
                "status": "COMPLETED",
            }
        ]

    async def build_strategy_profile(self, user_id: str | None = None):
        self.calls.append({"method": "build_strategy_profile", "user_id": user_id})
        return {
            "user_id": user_id,
            "profile_name": "Balanced Operator",
            "strengths": ["Balanced risk management"],
            "watchouts": ["Confidence and execution depth are fairly even"],
            "preferred_approach": "Use short milestone loops.",
            "success_rate": 0.5,
            "average_confidence": 67.0,
            "recent_domains": ["engineering"],
        }

    async def predict_outcome(self, goal: str, context: Dict[str, Any] | None = None, user_id: str | None = None, task_id: str | None = None):
        self.calls.append({"method": "predict_outcome", "goal": goal, "context": context, "user_id": user_id, "task_id": task_id})
        return {
            "task_id": task_id,
            "predicted_success_probability": 0.71,
            "predicted_risk_level": "MEDIUM",
            "confidence_band": "medium",
            "human_review_required": False,
            "likely_failure_modes": ["Scope creep"],
            "recommended_safeguards": ["Use checkpoints"],
            "rationale": "Heuristic baseline",
        }

    async def simulate_execution(self, goal: str, context: Dict[str, Any] | None = None, scenario: str = "baseline", user_id: str | None = None):
        self.calls.append({"method": "simulate_execution", "goal": goal, "context": context, "scenario": scenario, "user_id": user_id})
        return {
            "scenario": scenario,
            "predicted_confidence": 71.0,
            "predicted_risk_level": "MEDIUM",
            "success_probability": 0.71,
            "bottlenecks": ["Dependencies"],
            "mitigation_steps": ["Validate dependencies early"],
        }

    async def parse_workflow(self, workflow: str, title: str = "Workflow"):
        self.calls.append({"method": "parse_workflow", "workflow": workflow, "title": title})
        return {
            "title": title,
            "nodes": [{"id": "start", "label": "Start"}],
            "edges": [],
            "mermaid": "graph TD\n  start[\"Start\"]",
        }

    async def upsert_default_model(self):
        self.calls.append({"method": "upsert_default_model"})
        return {
            "model_id": "model-1",
            "name": "Catalyst Heuristic v1",
            "version": "1.0.0",
            "description": "Baseline heuristic predictor",
            "status": "active",
            "metrics": {"source": "heuristic"},
            "active": True,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }

    async def list_models(self):
        self.calls.append({"method": "list_models"})
        return [
            {
                "model_id": "model-1",
                "name": "Catalyst Heuristic v1",
                "version": "1.0.0",
                "description": "Baseline heuristic predictor",
                "status": "active",
                "metrics": {"source": "heuristic"},
                "active": True,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            }
        ]

    async def register_model(self, payload: Dict[str, Any]):
        self.calls.append({"method": "register_model", "payload": payload})
        return {"model_id": "model-2", **payload, "active": True}

    async def rollback_model(self, model_id: str):
        self.calls.append({"method": "rollback_model", "model_id": model_id})
        return {"model_id": model_id, "status": "rolled_back", "active": True}

    async def compute_drift(self, user_id: str | None = None):
        self.calls.append({"method": "compute_drift", "user_id": user_id})
        return {
            "drift_score": 0.12,
            "baseline_confidence": 66.0,
            "recent_confidence": 69.0,
            "baseline_success_rate": 0.6,
            "recent_success_rate": 0.7,
            "retraining_recommended": False,
            "notes": ["No significant drift detected."],
        }

    async def refresh_reflection_report(self, sample_size: int = 20):
        self.calls.append({"method": "refresh_reflection_report", "sample_size": sample_size})
        return {
            "generated_at": datetime.now(timezone.utc),
            "lessons": ["Keep scopes narrow"],
            "pattern_summary": "Heuristic summary",
            "confidence_calibration_note": "Stable",
            "suggested_weight_adjustments": {"goal_clarity": 0.1},
            "updated_confidence_bias": 0.05,
        }

    async def save_manual_override(self, task_id: str, decision: str, notes: str | None = None):
        self.calls.append({"method": "save_manual_override", "task_id": task_id, "decision": decision, "notes": notes})
        return {"task_id": task_id, "decision": decision, "notes": notes}


class _FakePipeline:
    def __init__(self) -> None:
        self.intelligence = _FakeIntelligence()


async def _auth_dependency(authorization: str = Header(default=None)) -> Dict[str, Any]:
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing authorization header")
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authorization header format")
    return {"sub": "user-1"}


def _build_app(pipeline_provider):
    app = FastAPI()
    app.include_router(intelligence_router.router)
    app.dependency_overrides[get_current_user] = _auth_dependency
    app.dependency_overrides[intelligence_router._get_pipeline] = pipeline_provider
    return app


@pytest.mark.parametrize(
    "path,method,payload",
    [
        ("/intelligence/overview", "get", None),
        ("/intelligence/graph/task-1", "get", None),
        ("/intelligence/similar/task-1", "get", None),
        ("/intelligence/profile", "get", None),
        ("/intelligence/predict", "post", {"goal": "Ship a feature", "context": {"team": 4}}),
        ("/intelligence/simulate", "post", {"goal": "Ship a feature", "scenario": "stress-test"}),
        ("/intelligence/workflow/parse", "post", {"workflow": "Start -> Review -> Ship", "title": "Release"}),
        ("/intelligence/models", "get", None),
        ("/intelligence/models", "post", {"name": "Model v2", "version": "2.0.0", "description": "Test", "status": "active"}),
        ("/intelligence/drift", "get", None),
        ("/intelligence/reflection/report", "post", None),
        ("/intelligence/override", "post", {"task_id": "task-1", "decision": "approve", "notes": "ok"}),
        ("/intelligence/health", "get", None),
    ],
)
def test_intelligence_routes_require_auth_and_return_401_without_token(path, method, payload):
    client = TestClient(_build_app(lambda: _FakePipeline()))
    request_fn = getattr(client, method)
    response = request_fn(path, json=payload) if payload is not None else request_fn(path)
    assert response.status_code == 401


def test_intelligence_routes_return_expected_payloads_with_valid_token():
    fake_pipeline = _FakePipeline()
    client = TestClient(_build_app(lambda: fake_pipeline))
    headers = {"Authorization": "Bearer test-token"}

    overview = client.get("/intelligence/overview", headers=headers)
    assert overview.status_code == 200
    assert overview.json()["scheduled_reflection_status"] == "active"

    graph = client.get("/intelligence/graph/task-1", headers=headers)
    assert graph.status_code == 200
    assert graph.json()["task_id"] == "task-1"

    similar = client.get("/intelligence/similar/task-1", headers=headers)
    assert similar.status_code == 200
    assert similar.json()[0]["task_id"] == "task-2"

    profile = client.get("/intelligence/profile", headers=headers)
    assert profile.status_code == 200
    assert profile.json()["profile_name"] == "Balanced Operator"

    predict = client.post("/intelligence/predict", headers=headers, json={"goal": "Ship a feature", "context": {"team": 4}})
    assert predict.status_code == 200
    assert predict.json()["confidence_band"] == "medium"

    simulate = client.post("/intelligence/simulate", headers=headers, json={"goal": "Ship a feature", "scenario": "stress-test"})
    assert simulate.status_code == 200
    assert simulate.json()["scenario"] == "stress-test"

    workflow = client.post("/intelligence/workflow/parse", headers=headers, json={"workflow": "Start -> Review -> Ship", "title": "Release"})
    assert workflow.status_code == 200
    assert workflow.json()["title"] == "Release"

    models = client.get("/intelligence/models", headers=headers)
    assert models.status_code == 200
    assert models.json()[0]["name"] == "Catalyst Heuristic v1"

    register = client.post(
        "/intelligence/models",
        headers=headers,
        json={"name": "Model v2", "version": "2.0.0", "description": "Test", "status": "active"},
    )
    assert register.status_code == 200
    assert register.json()["name"] == "Model v2"

    drift = client.get("/intelligence/drift", headers=headers)
    assert drift.status_code == 200
    assert drift.json()["drift_score"] == 0.12

    reflection = client.post("/intelligence/reflection/report", headers=headers)
    assert reflection.status_code == 200
    assert reflection.json()["pattern_summary"] == "Heuristic summary"

    override = client.post(
        "/intelligence/override",
        headers=headers,
        json={"task_id": "task-1", "decision": "approve", "notes": "ok"},
    )
    assert override.status_code == 200
    assert override.json()["decision"] == "approve"

    health = client.get("/intelligence/health", headers=headers)
    assert health.status_code == 200
    assert health.json()["status"] == "healthy"

    methods = [call["method"] for call in fake_pipeline.intelligence.calls]
    assert "overview" in methods
    assert "predict_outcome" in methods
    assert "refresh_reflection_report" in methods
