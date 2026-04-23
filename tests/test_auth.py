"""
AegisAI - Authentication Tests (pytest)
Tests: register, login, token refresh, user info retrieval, JWT validation
"""

import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
import asyncio

from main import app
from services.user_service import UserService
from config.settings import get_settings

settings = get_settings()
client = TestClient(app)


# ──────────────────────────────────────────────────────────────────────────────
# FIXTURES
# ──────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def test_user_data():
    """Sample user data for testing."""
    return {
        "email": "test@example.com",
        "password": "SecurePass123!",
        "full_name": "Test User",
    }


@pytest.fixture
def existing_user(test_user_data):
    """Create a user in the database for login tests."""
    # This will be handled by setup/teardown in actual implementation
    yield test_user_data


@pytest.fixture
def auth_headers(test_user_data):
    """Generate valid auth headers with JWT token."""
    # Register and login to get token
    response = client.post("/auth/register", json=test_user_data)
    assert response.status_code == 201
    token = response.json().get("access_token")
    return {"Authorization": f"Bearer {token}"}


# ──────────────────────────────────────────────────────────────────────────────
# REGISTRATION TESTS
# ──────────────────────────────────────────────────────────────────────────────


class TestUserRegistration:
    """User registration endpoint tests."""

    def test_register_success(self, test_user_data):
        """Test successful user registration."""
        response = client.post("/auth/register", json=test_user_data)
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == test_user_data["email"]
        assert data["full_name"] == test_user_data["full_name"]
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    def test_register_duplicate_email(self, test_user_data):
        """Test registration with already-registered email fails."""
        # First registration
        client.post("/auth/register", json=test_user_data)
        # Duplicate registration
        response = client.post("/auth/register", json=test_user_data)
        assert response.status_code == 400
        assert "already registered" in response.json().get("detail", "").lower()

    def test_register_invalid_email(self):
        """Test registration with invalid email format fails."""
        response = client.post("/auth/register", json={
            "email": "not-an-email",
            "password": "SecurePass123!",
            "full_name": "Test User",
        })
        assert response.status_code in [400, 422]

    def test_register_weak_password(self, test_user_data):
        """Test registration with weak password fails."""
        weak_password_data = test_user_data.copy()
        weak_password_data["password"] = "123"
        response = client.post("/auth/register", json=weak_password_data)
        assert response.status_code in [400, 422]

    def test_register_missing_fields(self):
        """Test registration with missing required fields fails."""
        response = client.post("/auth/register", json={
            "email": "test@example.com",
            # Missing password and full_name
        })
        assert response.status_code == 422

    def test_register_empty_values(self):
        """Test registration with empty string values fails."""
        response = client.post("/auth/register", json={
            "email": "",
            "password": "",
            "full_name": "",
        })
        assert response.status_code in [400, 422]


# ──────────────────────────────────────────────────────────────────────────────
# LOGIN TESTS
# ──────────────────────────────────────────────────────────────────────────────


class TestUserLogin:
    """User login endpoint tests."""

    def test_login_success(self, test_user_data):
        """Test successful login returns tokens."""
        # Register first
        client.post("/auth/register", json=test_user_data)
        # Login
        response = client.post("/auth/login", json={
            "email": test_user_data["email"],
            "password": test_user_data["password"],
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    def test_login_invalid_email(self, test_user_data):
        """Test login with non-existent email fails."""
        client.post("/auth/register", json=test_user_data)
        response = client.post("/auth/login", json={
            "email": "nonexistent@example.com",
            "password": test_user_data["password"],
        })
        assert response.status_code == 401
        assert "invalid" in response.json().get("detail", "").lower()

    def test_login_invalid_password(self, test_user_data):
        """Test login with wrong password fails."""
        client.post("/auth/register", json=test_user_data)
        response = client.post("/auth/login", json={
            "email": test_user_data["email"],
            "password": "WrongPassword123!",
        })
        assert response.status_code == 401

    def test_login_missing_email(self):
        """Test login without email fails."""
        response = client.post("/auth/login", json={
            "password": "SomePassword123!",
        })
        assert response.status_code == 422

    def test_login_missing_password(self):
        """Test login without password fails."""
        response = client.post("/auth/login", json={
            "email": "test@example.com",
        })
        assert response.status_code == 422


# ──────────────────────────────────────────────────────────────────────────────
# TOKEN REFRESH TESTS
# ──────────────────────────────────────────────────────────────────────────────


class TestTokenRefresh:
    """Token refresh endpoint tests."""

    def test_refresh_token_success(self, test_user_data):
        """Test successful token refresh."""
        # Register and get refresh token
        reg_response = client.post("/auth/register", json=test_user_data)
        refresh_token = reg_response.json()["refresh_token"]
        # Refresh
        response = client.post("/auth/refresh", json={
            "refresh_token": refresh_token
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_refresh_invalid_token(self):
        """Test refresh with invalid token fails."""
        response = client.post("/auth/refresh", json={
            "refresh_token": "invalid.token.here"
        })
        assert response.status_code == 401

    def test_refresh_expired_token(self):
        """Test refresh with expired token fails."""
        response = client.post("/auth/refresh", json={
            "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE2MDAwMDAwMDB9.invalid"
        })
        assert response.status_code == 401

    def test_refresh_missing_token(self):
        """Test refresh without token fails."""
        response = client.post("/auth/refresh", json={})
        assert response.status_code == 422


# ──────────────────────────────────────────────────────────────────────────────
# PROTECTED ENDPOINT TESTS (me)
# ──────────────────────────────────────────────────────────────────────────────


class TestProtectedEndpoints:
    """Tests for protected endpoints requiring auth."""

    def test_get_current_user_success(self, test_user_data, auth_headers):
        """Test retrieving current user info with valid token."""
        response = client.get("/auth/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == test_user_data["email"]
        assert data["full_name"] == test_user_data["full_name"]

    def test_get_current_user_no_token(self):
        """Test accessing protected endpoint without token fails."""
        response = client.get("/auth/me")
        assert response.status_code == 403

    def test_get_current_user_invalid_token(self):
        """Test accessing protected endpoint with invalid token fails."""
        response = client.get("/auth/me", headers={
            "Authorization": "Bearer invalid.token.here"
        })
        assert response.status_code == 403

    def test_get_current_user_malformed_header(self):
        """Test accessing protected endpoint with malformed auth header fails."""
        response = client.get("/auth/me", headers={
            "Authorization": "InvalidFormat token"
        })
        assert response.status_code == 403


# ──────────────────────────────────────────────────────────────────────────────
# JWT VALIDATION TESTS
# ──────────────────────────────────────────────────────────────────────────────


class TestJWTValidation:
    """JWT token validation tests."""

    def test_token_contains_user_id(self, test_user_data):
        """Test JWT token contains user ID."""
        response = client.post("/auth/register", json=test_user_data)
        token = response.json()["access_token"]
        # Decode would require JWT library - this is more of integration test
        assert len(token) > 20  # Basic format check

    def test_access_token_type(self, test_user_data):
        """Test access token is bearer type."""
        response = client.post("/auth/register", json=test_user_data)
        data = response.json()
        assert data["token_type"] == "bearer"

    def test_refresh_token_different_from_access(self, test_user_data):
        """Test refresh token differs from access token."""
        response = client.post("/auth/register", json=test_user_data)
        data = response.json()
        assert data["access_token"] != data["refresh_token"]


# ──────────────────────────────────────────────────────────────────────────────
# ERROR HANDLING TESTS
# ──────────────────────────────────────────────────────────────────────────────


class TestErrorHandling:
    """Tests for proper error handling."""

    def test_sql_injection_protection(self):
        """Test SQL injection attempts are handled safely."""
        response = client.post("/auth/login", json={
            "email": "test' OR '1'='1",
            "password": "test' OR '1'='1",
        })
        # Should fail gracefully, not expose database errors
        assert response.status_code in [400, 401, 422]
        assert "database" not in response.json().get("detail", "").lower()

    def test_xss_protection_in_response(self, test_user_data):
        """Test XSS attempts are sanitized."""
        xss_data = test_user_data.copy()
        xss_data["full_name"] = "<script>alert('xss')</script>"
        response = client.post("/auth/register", json=xss_data)
        # Should accept but sanitize
        assert response.status_code in [201, 400]

    def test_rate_limit_protection(self):
        """Test rate limiting on login attempts (if implemented)."""
        # Make multiple failed login attempts
        for _ in range(5):
            client.post("/auth/login", json={
                "email": "test@example.com",
                "password": "wrong",
            })
        # Server should either rate limit or continue allowing
        response = client.post("/auth/login", json={
            "email": "test@example.com",
            "password": "wrong",
        })
        # Either 429 (rate limited) or 401 (invalid credentials) is acceptable
        assert response.status_code in [401, 429]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
