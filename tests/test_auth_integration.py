from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any, Dict

import pytest
from fastapi import FastAPI, Header, HTTPException, status
from fastapi.testclient import TestClient

from routers import analytics_router, confidence_router, goal_router, plan_router
from routers.auth import get_current_user


class _FakeMongo:
    def __init__(self, tasks: list[Dict[str, Any]]) -> None:
        self._tasks = tasks

    async def list_tasks(self, limit: int = 20, skip: int = 0, status: str | None = None):
        rows = self._tasks
        if status:
            rows = [t for t in rows if t.get("status") == status]
        return rows[skip : skip + limit]


class _FakeMemory:
    def __init__(self) -> None:
        self._task = {
            "task_id": "task-1",
            "goal": "Ship authenticated API",
            "subtasks": [{"id": "s1", "title": "Implement", "description": "x", "priority": 1, "dependencies": []}],
            "research_insights": "Research complete",
            "execution_plan": "Do steps",
            "confidence": 71.0,
            "risk_level": "MEDIUM",
            "status": "IN_PROGRESS",
            "language": "en-IN",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "trust_components": {
                "goal_clarity": 0.7,
                "information_quality": 0.8,
                "execution_feasibility": 0.7,
                "risk_manageability": 0.6,
                "resource_adequacy": 0.7,
                "external_uncertainty": 0.6,
            },
            "reasoning": "Looks feasible with moderate risk.",
            "domain": "engineering",
        }
        self._legacy_task = {
            "task_id": "task-legacy",
            "goal": "Legacy trust payload",
            "subtasks": [],
            "research_insights": "",
            "execution_plan": "",
            "confidence": 52.0,
            "risk_level": "MEDIUM",
            "status": "IN_PROGRESS",
            "language": "en-IN",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "trust_components": {
                "data_completeness": 0.8,
                "task_feasibility": 0.6,
                "complexity_inverse": 0.4,
            },
            "reasoning": "Legacy format task.",
            "domain": "general",
        }
        self.mongo = _FakeMongo([self._task])
        self.last_update: Dict[str, Any] | None = None
        self.last_cached: Dict[str, Any] | None = None

    async def get_task(self, task_id: str):
        if task_id == self._task["task_id"]:
            return self._task
        if task_id == self._legacy_task["task_id"]:
            return self._legacy_task
        return None

    async def get_cached_confidence(self, task_id: str):
        return None

    async def get_past_success_rate(self):
        return 0.6

    async def update_task(self, task_id: str, patch: Dict[str, Any]):
        if task_id == self._task["task_id"]:
            self._task.update(patch)
        elif task_id == self._legacy_task["task_id"]:
            self._legacy_task.update(patch)
        self.last_update = {"task_id": task_id, "patch": patch}

    async def cache_confidence(self, task_id: str, payload: Dict[str, Any]):
        self.last_cached = {"task_id": task_id, "payload": payload}
        return None


class _FakeComponents:
    def model_dump(self):
        return {
            "goal_clarity": 0.9,
            "information_quality": 0.85,
            "execution_feasibility": 0.8,
            "risk_manageability": 0.75,
            "resource_adequacy": 0.8,
            "external_uncertainty": 0.7,
        }


class _FakeTrustScore:
    confidence = 78.5
    risk_level = SimpleNamespace(value="LOW")
    components = _FakeComponents()
    reasoning = "Re-evaluated with latest history."


class _FakeTrust:
    async def evaluate(self, **kwargs):
        return _FakeTrustScore()


class _FakePipeline:
    def __init__(self) -> None:
        self.memory = _FakeMemory()
        self.trust = _FakeTrust()

    async def process_goal(self, request):
        return {
            "task_id": "task-1",
            "status": "IN_PROGRESS",
            "message": "Goal processed successfully.",
            "plan": None,
        }


async def _auth_dependency(authorization: str = Header(default=None)) -> Dict[str, Any]:
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
        )
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format",
        )
    return {"sub": "user-1", "email": "user@example.com"}


def _build_app(pipeline_provider):
    app = FastAPI()
    app.include_router(goal_router.router)
    app.include_router(plan_router.router)
    app.include_router(confidence_router.router)
    app.include_router(analytics_router.router)

    app.dependency_overrides[get_current_user] = _auth_dependency
    app.dependency_overrides[goal_router._get_pipeline] = pipeline_provider
    app.dependency_overrides[plan_router._get_pipeline] = pipeline_provider
    app.dependency_overrides[confidence_router._get_pipeline] = pipeline_provider
    app.dependency_overrides[analytics_router._get_pipeline] = pipeline_provider
    return app


@pytest.mark.parametrize(
    "method,path,payload",
    [
        ("post", "/goal", {"goal": "Build an authenticated API", "language": "en-IN"}),
        ("get", "/plan", None),
        ("get", "/confidence/stats/summary", None),
        ("get", "/analytics", None),
    ],
)
def test_protected_routes_return_401_without_token_and_do_not_touch_pipeline(method, path, payload):
    def pipeline_must_not_run():
        raise AssertionError("Pipeline dependency should not execute for unauthorized requests")

    client = TestClient(_build_app(pipeline_must_not_run))
    request_fn = getattr(client, method)
    response = request_fn(path, json=payload) if payload is not None else request_fn(path)

    assert response.status_code == 401


def test_protected_routes_work_with_valid_token_and_mocked_pipeline():
    fake_pipeline = _FakePipeline()
    client = TestClient(_build_app(lambda: fake_pipeline))
    headers = {"Authorization": "Bearer test-token"}

    goal_resp = client.post(
        "/goal",
        headers=headers,
        json={"goal": "Build an authenticated API", "language": "en-IN"},
    )
    assert goal_resp.status_code == 202
    assert goal_resp.json()["task_id"] == "task-1"

    plan_resp = client.get("/plan", headers=headers)
    assert plan_resp.status_code == 200
    assert plan_resp.json()["total_returned"] == 1

    conf_resp = client.get("/confidence/stats/summary", headers=headers)
    assert conf_resp.status_code == 200
    assert conf_resp.json()["total_tasks"] == 1
    assert conf_resp.json()["risk_distribution"]["MEDIUM"] == 1

    analytics_resp = client.get("/analytics", headers=headers)
    assert analytics_resp.status_code == 200
    assert analytics_resp.json()["total_goals"] == 1


def test_confidence_endpoint_returns_six_dimension_components():
    fake_pipeline = _FakePipeline()
    client = TestClient(_build_app(lambda: fake_pipeline))
    headers = {"Authorization": "Bearer test-token"}

    response = client.get("/confidence/task-1", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["task_id"] == "task-1"
    assert set(body["components"].keys()) == {
        "goal_clarity",
        "information_quality",
        "execution_feasibility",
        "risk_manageability",
        "resource_adequacy",
        "external_uncertainty",
    }


def test_confidence_components_legacy_mapping_is_reported():
    fake_pipeline = _FakePipeline()
    client = TestClient(_build_app(lambda: fake_pipeline))
    headers = {"Authorization": "Bearer test-token"}

    response = client.get("/confidence/task-legacy/components", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["legacy_component_mapping_applied"] is True
    assert body["components"]["information_quality"] == 0.8
    assert body["components"]["execution_feasibility"] == 0.6
    assert body["components"]["external_uncertainty"] == 0.4


def test_refresh_confidence_updates_memory_and_cache():
    fake_pipeline = _FakePipeline()
    client = TestClient(_build_app(lambda: fake_pipeline))
    headers = {"Authorization": "Bearer test-token"}

    response = client.post("/confidence/task-1/refresh", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["task_id"] == "task-1"
    assert body["updated_confidence"] == 78.5
    assert body["risk_level"] == "LOW"

    assert fake_pipeline.memory.last_update is not None
    assert fake_pipeline.memory.last_update["task_id"] == "task-1"
    assert "confidence" in fake_pipeline.memory.last_update["patch"]

    assert fake_pipeline.memory.last_cached is not None
    assert fake_pipeline.memory.last_cached["task_id"] == "task-1"
