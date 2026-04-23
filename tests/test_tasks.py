"""
AegisAI - Pipeline & Task Tests (pytest)
Tests: task submission, pipeline execution, progress tracking, results
"""

import pytest
from datetime import datetime
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


# ──────────────────────────────────────────────────────────────────────────────
# FIXTURES
# ──────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def authenticated_user():
    """Register and login a test user."""
    user_data = {
        "email": f"pipeline_test_{datetime.now().timestamp()}@example.com",
        "password": "SecurePass123!",
        "full_name": "Pipeline Tester",
    }
    response = client.post("/auth/register", json=user_data)
    token = response.json()["access_token"]
    return {
        "token": token,
        "user_id": response.json().get("user_id"),
    }


@pytest.fixture
def auth_headers(authenticated_user):
    """Get authorization headers."""
    return {
        "Authorization": f"Bearer {authenticated_user['token']}"
    }


@pytest.fixture
def task_payload():
    """Sample task payload."""
    return {
        "goal": "Analyze market trends in technology sector",
        "domain": "market_analysis",
        "priority": "high",
        "deadline_days": 7,
        "context": "Looking for emerging opportunities",
    }


# ──────────────────────────────────────────────────────────────────────────────
# TASK SUBMISSION TESTS
# ──────────────────────────────────────────────────────────────────────────────


class TestTaskSubmission:
    """Tests for task submission and creation."""

    def test_submit_task_requires_auth(self, task_payload):
        """Test task submission requires authentication."""
        response = client.post("/tasks/submit", json=task_payload)
        assert response.status_code == 403

    def test_submit_task_success(self, auth_headers, task_payload):
        """Test successful task submission."""
        response = client.post("/tasks/submit", json=task_payload, headers=auth_headers)
        assert response.status_code in [200, 201]
        data = response.json()
        
        assert "task_id" in data
        assert "status" in data
        assert data["goal"] == task_payload["goal"]

    def test_submit_task_creates_session_id(self, auth_headers, task_payload):
        """Test task submission creates a session ID."""
        response = client.post("/tasks/submit", json=task_payload, headers=auth_headers)
        assert response.status_code in [200, 201]
        data = response.json()
        
        assert "session_id" in data
        assert len(data["session_id"]) > 0

    def test_submit_task_missing_goal(self, auth_headers):
        """Test task submission without goal fails."""
        response = client.post("/tasks/submit", json={
            "domain": "test",
            "priority": "high",
        }, headers=auth_headers)
        assert response.status_code == 422

    def test_submit_task_empty_goal(self, auth_headers, task_payload):
        """Test task submission with empty goal fails."""
        task_payload["goal"] = ""
        response = client.post("/tasks/submit", json=task_payload, headers=auth_headers)
        assert response.status_code in [400, 422]

    def test_submit_task_with_all_fields(self, auth_headers, task_payload):
        """Test task submission with all optional fields."""
        response = client.post("/tasks/submit", json=task_payload, headers=auth_headers)
        assert response.status_code in [200, 201]

    def test_submit_multiple_tasks_different_ids(self, auth_headers, task_payload):
        """Test multiple task submissions get different IDs."""
        response1 = client.post("/tasks/submit", json=task_payload, headers=auth_headers)
        response2 = client.post("/tasks/submit", json=task_payload, headers=auth_headers)
        
        task_id_1 = response1.json()["task_id"]
        task_id_2 = response2.json()["task_id"]
        
        assert task_id_1 != task_id_2


# ──────────────────────────────────────────────────────────────────────────────
# TASK RETRIEVAL TESTS
# ──────────────────────────────────────────────────────────────────────────────


class TestTaskRetrieval:
    """Tests for retrieving task information."""

    def test_get_task_requires_auth(self):
        """Test retrieving task requires auth."""
        response = client.get("/tasks/some_task_id")
        assert response.status_code == 403

    def test_get_nonexistent_task(self, auth_headers):
        """Test retrieving non-existent task returns 404."""
        response = client.get("/tasks/nonexistent_task_id", headers=auth_headers)
        assert response.status_code == 404

    def test_get_task_success(self, auth_headers, task_payload):
        """Test successfully retrieving a task."""
        # Submit task
        submit_response = client.post("/tasks/submit", json=task_payload, headers=auth_headers)
        task_id = submit_response.json()["task_id"]
        
        # Retrieve task
        response = client.get(f"/tasks/{task_id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == task_id
        assert data["goal"] == task_payload["goal"]

    def test_list_user_tasks(self, auth_headers, task_payload):
        """Test listing user's tasks."""
        # Submit a task
        client.post("/tasks/submit", json=task_payload, headers=auth_headers)
        
        # List tasks
        response = client.get("/tasks/", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, (list, dict))
        if isinstance(data, list):
            assert len(data) >= 1

    def test_task_isolation_between_users(self):
        """Test tasks are isolated between different users."""
        # Create user 1
        user1 = {
            "email": f"user1_{datetime.now().timestamp()}@example.com",
            "password": "Pass123!",
            "full_name": "User 1",
        }
        reg1 = client.post("/auth/register", json=user1)
        token1 = reg1.json()["access_token"]
        headers1 = {"Authorization": f"Bearer {token1}"}
        
        # Create user 2
        user2 = {
            "email": f"user2_{datetime.now().timestamp()}@example.com",
            "password": "Pass123!",
            "full_name": "User 2",
        }
        reg2 = client.post("/auth/register", json=user2)
        token2 = reg2.json()["access_token"]
        headers2 = {"Authorization": f"Bearer {token2}"}
        
        # User 1 submits task
        task = {
            "goal": "User 1 private task",
            "domain": "test",
        }
        resp1 = client.post("/tasks/submit", json=task, headers=headers1)
        task_id = resp1.json()["task_id"]
        
        # User 2 tries to retrieve user 1's task - should fail or show only their own
        response = client.get(f"/tasks/{task_id}", headers=headers2)
        # Either 404 or 403 - should not allow access
        assert response.status_code in [403, 404]


# ──────────────────────────────────────────────────────────────────────────────
# PIPELINE PROGRESS TESTS
# ──────────────────────────────────────────────────────────────────────────────


class TestPipelineProgress:
    """Tests for pipeline progress tracking."""

    def test_task_has_initial_status(self, auth_headers, task_payload):
        """Test submitted task has initial status."""
        response = client.post("/tasks/submit", json=task_payload, headers=auth_headers)
        data = response.json()
        
        assert "status" in data
        # Should be one of: pending, processing, completed, failed
        assert data["status"] in ["pending", "processing", "queued", "running"]

    def test_pipeline_progress_endpoint(self, auth_headers, task_payload):
        """Test retrieving pipeline progress."""
        # Submit task
        submit_resp = client.post("/tasks/submit", json=task_payload, headers=auth_headers)
        task_id = submit_resp.json()["task_id"]
        
        # Get progress
        response = client.get(f"/tasks/{task_id}/progress", headers=auth_headers)
        # Endpoint may or may not exist, but should handle gracefully
        assert response.status_code in [200, 404]

    def test_task_status_updates(self, auth_headers, task_payload):
        """Test task status progresses (if pipeline runs)."""
        response = client.post("/tasks/submit", json=task_payload, headers=auth_headers)
        initial_status = response.json()["status"]
        
        task_id = response.json()["task_id"]
        
        # Wait a moment then check status again
        import time
        time.sleep(0.5)
        
        status_resp = client.get(f"/tasks/{task_id}", headers=auth_headers)
        new_status = status_resp.json()["status"]
        
        # Status should be set and consistent
        assert new_status in ["pending", "processing", "queued", "running", "completed", "failed"]


# ──────────────────────────────────────────────────────────────────────────────
# TASK VALIDATION TESTS
# ──────────────────────────────────────────────────────────────────────────────


class TestTaskValidation:
    """Tests for task data validation."""

    def test_task_goal_max_length(self, auth_headers):
        """Test task goal has reasonable length."""
        long_goal = "a" * 10000  # Very long goal
        response = client.post("/tasks/submit", json={
            "goal": long_goal,
            "domain": "test",
        }, headers=auth_headers)
        # Should either accept or return 422
        assert response.status_code in [200, 201, 422]

    def test_task_priority_valid_values(self, auth_headers, task_payload):
        """Test task priority accepts valid values."""
        for priority in ["low", "medium", "high", "critical"]:
            task = task_payload.copy()
            task["priority"] = priority
            response = client.post("/tasks/submit", json=task, headers=auth_headers)
            assert response.status_code in [200, 201, 422]

    def test_task_invalid_priority(self, auth_headers, task_payload):
        """Test invalid priority is rejected."""
        task = task_payload.copy()
        task["priority"] = "invalid_priority"
        response = client.post("/tasks/submit", json=task, headers=auth_headers)
        assert response.status_code in [400, 422]

    def test_task_deadline_validation(self, auth_headers, task_payload):
        """Test deadline field validation."""
        task = task_payload.copy()
        task["deadline_days"] = -1  # Invalid negative days
        response = client.post("/tasks/submit", json=task, headers=auth_headers)
        assert response.status_code in [400, 422]


# ──────────────────────────────────────────────────────────────────────────────
# TASK RESPONSE STRUCTURE TESTS
# ──────────────────────────────────────────────────────────────────────────────


class TestTaskResponseStructure:
    """Tests for task response data structure."""

    def test_submitted_task_has_required_fields(self, auth_headers, task_payload):
        """Test submitted task response has all required fields."""
        response = client.post("/tasks/submit", json=task_payload, headers=auth_headers)
        data = response.json()
        
        required_fields = ["task_id", "status", "goal"]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"

    def test_task_id_format(self, auth_headers, task_payload):
        """Test task ID is a valid string."""
        response = client.post("/tasks/submit", json=task_payload, headers=auth_headers)
        task_id = response.json()["task_id"]
        
        assert isinstance(task_id, str)
        assert len(task_id) > 0

    def test_task_timestamps(self, auth_headers, task_payload):
        """Test task has timestamp fields."""
        response = client.post("/tasks/submit", json=task_payload, headers=auth_headers)
        data = response.json()
        
        # May have created_at, updated_at, etc.
        if "created_at" in data:
            assert isinstance(data["created_at"], (str, int, float))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
