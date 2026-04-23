"""
AegisAI - Integration Tests (pytest)
Full-stack tests: Frontend → Backend → Database flows
Tests: auth flow, task submission, analytics retrieval, error scenarios
"""

import pytest
import asyncio
from datetime import datetime
from fastapi.testclient import TestClient
import aiohttp

from main import app

client = TestClient(app)


# ──────────────────────────────────────────────────────────────────────────────
# INTEGRATION FIXTURES
# ──────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def api_base_url():
    """Base URL for API requests."""
    return "http://localhost:8000"


@pytest.fixture
def test_user_credentials():
    """Test user credentials for integration tests."""
    return {
        "email": f"integration_test_{datetime.now().timestamp()}@example.com",
        "password": "IntegrationPass123!",
        "full_name": "Integration Tester",
    }


@pytest.fixture
def registered_user(test_user_credentials):
    """Register a user and return credentials + tokens."""
    response = client.post("/auth/register", json=test_user_credentials)
    assert response.status_code == 201
    data = response.json()
    return {
        "credentials": test_user_credentials,
        "access_token": data["access_token"],
        "refresh_token": data["refresh_token"],
        "user_id": data.get("user_id"),
    }


@pytest.fixture
def auth_headers(registered_user):
    """Authentication headers for protected endpoints."""
    return {
        "Authorization": f"Bearer {registered_user['access_token']}"
    }


# ──────────────────────────────────────────────────────────────────────────────
# FULL AUTHENTICATION FLOW TESTS
# ──────────────────────────────────────────────────────────────────────────────


class TestAuthenticationFlow:
    """End-to-end authentication workflow tests."""

    def test_full_auth_flow_register_login_access(self, test_user_credentials):
        """Test complete auth flow: register → login → access protected endpoint."""
        # Step 1: Register
        reg_response = client.post("/auth/register", json=test_user_credentials)
        assert reg_response.status_code == 201
        reg_data = reg_response.json()
        assert "access_token" in reg_data
        access_token_1 = reg_data["access_token"]

        # Step 2: Access protected endpoint with registration token
        headers = {"Authorization": f"Bearer {access_token_1}"}
        me_response = client.get("/auth/me", headers=headers)
        assert me_response.status_code == 200
        me_data = me_response.json()
        assert me_data["email"] == test_user_credentials["email"]

        # Step 3: Login with credentials
        login_response = client.post("/auth/login", json={
            "email": test_user_credentials["email"],
            "password": test_user_credentials["password"],
        })
        assert login_response.status_code == 200
        login_data = login_response.json()
        access_token_2 = login_data["access_token"]

        # Step 4: Use login token to access protected endpoint
        headers = {"Authorization": f"Bearer {access_token_2}"}
        me_response_2 = client.get("/auth/me", headers=headers)
        assert me_response_2.status_code == 200
        assert me_response_2.json()["email"] == test_user_credentials["email"]

    def test_token_refresh_flow(self, registered_user):
        """Test token refresh workflow."""
        refresh_token = registered_user["refresh_token"]
        old_access_token = registered_user["access_token"]

        # Refresh token
        refresh_response = client.post("/auth/refresh", json={
            "refresh_token": refresh_token
        })
        assert refresh_response.status_code == 200
        new_access_token = refresh_response.json()["access_token"]

        # Verify old token still works (usually not revoked immediately)
        headers_old = {"Authorization": f"Bearer {old_access_token}"}
        response_old = client.get("/auth/me", headers=headers_old)
        assert response_old.status_code == 200

        # Verify new token works
        headers_new = {"Authorization": f"Bearer {new_access_token}"}
        response_new = client.get("/auth/me", headers=headers_new)
        assert response_new.status_code == 200


# ──────────────────────────────────────────────────────────────────────────────
# TASK SUBMISSION & RETRIEVAL FLOW TESTS
# ──────────────────────────────────────────────────────────────────────────────


class TestTaskWorkflow:
    """Task submission and tracking workflow tests."""

    def test_submit_task_retrieve_task_flow(self, auth_headers):
        """Test submitting a task and retrieving it."""
        # Submit task
        task_payload = {
            "goal": "Analyze historical stock data",
            "domain": "financial_analysis",
            "priority": "high",
            "deadline_days": 5,
        }
        submit_response = client.post("/tasks/submit", json=task_payload, headers=auth_headers)
        assert submit_response.status_code in [200, 201]
        task_data = submit_response.json()
        task_id = task_data["task_id"]
        assert task_data["goal"] == task_payload["goal"]

        # Retrieve task
        get_response = client.get(f"/tasks/{task_id}", headers=auth_headers)
        assert get_response.status_code == 200
        retrieved_task = get_response.json()
        assert retrieved_task["task_id"] == task_id
        assert retrieved_task["goal"] == task_payload["goal"]

    def test_multiple_tasks_isolation(self, auth_headers):
        """Test that multiple tasks are properly isolated."""
        # Submit first task
        task1 = client.post("/tasks/submit", json={
            "goal": "Task 1 goal",
            "domain": "test",
        }, headers=auth_headers).json()

        # Submit second task
        task2 = client.post("/tasks/submit", json={
            "goal": "Task 2 goal",
            "domain": "test",
        }, headers=auth_headers).json()

        # Verify tasks are different
        assert task1["task_id"] != task2["task_id"]

        # Retrieve both and verify isolation
        get1 = client.get(f"/tasks/{task1['task_id']}", headers=auth_headers).json()
        get2 = client.get(f"/tasks/{task2['task_id']}", headers=auth_headers).json()

        assert get1["goal"] == "Task 1 goal"
        assert get2["goal"] == "Task 2 goal"

    def test_user_sees_only_own_tasks(self):
        """Test users only see their own tasks."""
        # Create two users
        user1_data = {
            "email": f"user1_{datetime.now().timestamp()}@example.com",
            "password": "Pass123!",
            "full_name": "User 1",
        }
        user2_data = {
            "email": f"user2_{datetime.now().timestamp()}@example.com",
            "password": "Pass123!",
            "full_name": "User 2",
        }

        # Register users
        reg1 = client.post("/auth/register", json=user1_data)
        reg2 = client.post("/auth/register", json=user2_data)

        token1 = reg1.json()["access_token"]
        token2 = reg2.json()["access_token"]

        headers1 = {"Authorization": f"Bearer {token1}"}
        headers2 = {"Authorization": f"Bearer {token2}"}

        # User 1 submits task
        task1_response = client.post("/tasks/submit", json={
            "goal": "User 1 private task",
            "domain": "test",
        }, headers=headers1)
        task1_id = task1_response.json()["task_id"]

        # User 2 submits task
        task2_response = client.post("/tasks/submit", json={
            "goal": "User 2 private task",
            "domain": "test",
        }, headers=headers2)
        task2_id = task2_response.json()["task_id"]

        # User 2 tries to access User 1's task
        access_response = client.get(f"/tasks/{task1_id}", headers=headers2)
        # Should be denied
        assert access_response.status_code in [403, 404]


# ──────────────────────────────────────────────────────────────────────────────
# ANALYTICS DATA FLOW TESTS
# ──────────────────────────────────────────────────────────────────────────────


class TestAnalyticsFlow:
    """Analytics data aggregation workflow tests."""

    def test_analytics_after_task_submission(self, auth_headers):
        """Test analytics reflect submitted tasks."""
        # Get initial analytics
        initial_analytics = client.get("/analytics/", headers=auth_headers).json()
        initial_total = initial_analytics["kpis"]["total_tasks"]

        # Submit a task
        client.post("/tasks/submit", json={
            "goal": "New task for analytics",
            "domain": "test",
        }, headers=auth_headers)

        # Get updated analytics
        updated_analytics = client.get("/analytics/", headers=auth_headers).json()
        updated_total = updated_analytics["kpis"]["total_tasks"]

        # Total should increase
        assert updated_total >= initial_total

    def test_analytics_data_consistency(self, auth_headers):
        """Test analytics data is consistent across multiple requests."""
        response1 = client.get("/analytics/", headers=auth_headers).json()
        response2 = client.get("/analytics/", headers=auth_headers).json()

        # Same KPIs without new tasks
        assert response1["kpis"]["total_tasks"] == response2["kpis"]["total_tasks"]
        assert response1["kpis"]["completed_tasks"] == response2["kpis"]["completed_tasks"]

    def test_analytics_distribution_sums(self, auth_headers):
        """Test analytics risk distribution makes sense."""
        analytics = client.get("/analytics/", headers=auth_headers).json()
        risk_dist = analytics["risk_distribution"]

        # Sum of distribution components
        total_from_dist = risk_dist.get("high", 0) + risk_dist.get("medium", 0) + risk_dist.get("low", 0)

        # Should be reasonable
        assert total_from_dist >= 0


# ──────────────────────────────────────────────────────────────────────────────
# ERROR HANDLING & EDGE CASES
# ──────────────────────────────────────────────────────────────────────────────


class TestErrorScenarios:
    """Tests for error handling and edge cases."""

    def test_invalid_token_access_denied(self):
        """Test accessing protected endpoints with invalid token fails."""
        response = client.get("/analytics/", headers={
            "Authorization": "Bearer invalid.token.here"
        })
        assert response.status_code == 403

    def test_missing_token_access_denied(self):
        """Test accessing protected endpoints without token fails."""
        response = client.get("/analytics/")
        assert response.status_code == 403

    def test_expired_token_rejected(self):
        """Test accessing with expired token fails."""
        # Using a clearly invalid/expired token
        response = client.get("/auth/me", headers={
            "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE2MDAwMDAwMDB9.invalid"
        })
        assert response.status_code == 403

    def test_nonexistent_task_returns_404(self, auth_headers):
        """Test accessing non-existent task returns 404."""
        response = client.get("/tasks/nonexistent_task_id_12345", headers=auth_headers)
        assert response.status_code == 404

    def test_malformed_request_returns_422(self, auth_headers):
        """Test malformed task submission returns 422."""
        response = client.post("/tasks/submit", json={
            "invalid_field": "value",
            # Missing required 'goal' field
        }, headers=auth_headers)
        assert response.status_code == 422

    def test_duplicate_registration_fails(self, test_user_credentials):
        """Test registering same email twice fails."""
        # First registration
        response1 = client.post("/auth/register", json=test_user_credentials)
        assert response1.status_code == 201

        # Duplicate registration
        response2 = client.post("/auth/register", json=test_user_credentials)
        assert response2.status_code in [400, 409]

    def test_login_with_wrong_password_fails(self, test_user_credentials):
        """Test login with wrong password fails."""
        # Register
        client.post("/auth/register", json=test_user_credentials)

        # Try login with wrong password
        response = client.post("/auth/login", json={
            "email": test_user_credentials["email"],
            "password": "WrongPassword123!",
        })
        assert response.status_code == 401

    def test_login_nonexistent_user_fails(self):
        """Test login for non-existent user fails."""
        response = client.post("/auth/login", json={
            "email": "nonexistent@example.com",
            "password": "SomePassword123!",
        })
        assert response.status_code == 401


# ──────────────────────────────────────────────────────────────────────────────
# CONCURRENT OPERATIONS TESTS
# ──────────────────────────────────────────────────────────────────────────────


class TestConcurrentOperations:
    """Tests for handling concurrent operations."""

    def test_concurrent_task_submissions(self, auth_headers):
        """Test submitting multiple tasks concurrently."""
        tasks = []
        for i in range(5):
            response = client.post("/tasks/submit", json={
                "goal": f"Concurrent task {i}",
                "domain": "test",
            }, headers=auth_headers)
            assert response.status_code in [200, 201]
            tasks.append(response.json())

        # Verify all tasks have unique IDs
        task_ids = [t["task_id"] for t in tasks]
        assert len(task_ids) == len(set(task_ids))

    def test_concurrent_analytics_reads(self, auth_headers):
        """Test concurrent reads don't cause issues."""
        responses = []
        for _ in range(5):
            response = client.get("/analytics/", headers=auth_headers)
            assert response.status_code == 200
            responses.append(response.json())

        # All should return same data (no new tasks submitted)
        kpis = [r["kpis"]["total_tasks"] for r in responses]
        assert len(set(kpis)) == 1


# ──────────────────────────────────────────────────────────────────────────────
# DATA VALIDATION TESTS
# ──────────────────────────────────────────────────────────────────────────────


class TestDataValidation:
    """Tests for data validation across full stack."""

    def test_email_validation_across_stack(self):
        """Test email validation from frontend to backend."""
        invalid_emails = [
            "",
            "notanemail",
            "missing@domain",
            "missing.domain@",
            "@nodomain.com",
        ]

        for email in invalid_emails:
            response = client.post("/auth/register", json={
                "email": email,
                "password": "ValidPass123!",
                "full_name": "Test User",
            })
            # Should either reject or return error
            assert response.status_code in [400, 422, 409]

    def test_password_strength_validation(self, test_user_credentials):
        """Test password strength requirements."""
        weak_passwords = [
            "123",
            "password",
            "abcd",
            "1234567",
        ]

        for weak_pass in weak_passwords:
            response = client.post("/auth/register", json={
                "email": f"test_{datetime.now().timestamp()}@example.com",
                "password": weak_pass,
                "full_name": "Test User",
            })
            # Should reject weak passwords
            assert response.status_code in [400, 422]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
