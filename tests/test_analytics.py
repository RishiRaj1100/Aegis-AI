"""
AegisAI - Analytics Tests (pytest)
Tests: analytics endpoints, aggregation, risk scores, confidence metrics
"""

import pytest
from datetime import datetime, timedelta
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
        "email": f"analytics_test_{datetime.now().timestamp()}@example.com",
        "password": "SecurePass123!",
        "full_name": "Analytics Tester",
    }
    response = client.post("/auth/register", json=user_data)
    token = response.json()["access_token"]
    return {
        "token": token,
        "email": user_data["email"],
        "user_id": response.json().get("user_id"),
    }


@pytest.fixture
def auth_headers(authenticated_user):
    """Get authorization headers with valid token."""
    return {
        "Authorization": f"Bearer {authenticated_user['token']}"
    }


# ──────────────────────────────────────────────────────────────────────────────
# ANALYTICS ENDPOINT TESTS
# ──────────────────────────────────────────────────────────────────────────────


class TestAnalyticsEndpoints:
    """Tests for analytics aggregation endpoints."""

    def test_get_analytics_requires_auth(self):
        """Test analytics endpoint requires authentication."""
        response = client.get("/analytics/")
        assert response.status_code == 403

    def test_get_analytics_success(self, auth_headers):
        """Test retrieving analytics with valid auth."""
        response = client.get("/analytics/", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "kpis" in data
        assert "risk_distribution" in data
        assert "domain_distribution" in data
        assert "timeline" in data

    def test_analytics_kpis_structure(self, auth_headers):
        """Test KPI structure in analytics response."""
        response = client.get("/analytics/", headers=auth_headers)
        assert response.status_code == 200
        kpis = response.json()["kpis"]
        
        assert "total_tasks" in kpis
        assert "completed_tasks" in kpis
        assert "avg_confidence" in kpis
        assert "avg_trust_score" in kpis
        
        # Verify numeric types
        assert isinstance(kpis["total_tasks"], int)
        assert isinstance(kpis["completed_tasks"], int)
        assert isinstance(kpis["avg_confidence"], (int, float))
        assert isinstance(kpis["avg_trust_score"], (int, float))

    def test_analytics_kpis_valid_ranges(self, auth_headers):
        """Test KPI values are within valid ranges."""
        response = client.get("/analytics/", headers=auth_headers)
        kpis = response.json()["kpis"]
        
        # Confidence should be 0-100
        assert 0 <= kpis["avg_confidence"] <= 100
        # Trust score should be 0-100
        assert 0 <= kpis["avg_trust_score"] <= 100
        # Tasks should be non-negative
        assert kpis["total_tasks"] >= 0
        assert kpis["completed_tasks"] >= 0
        # Completed should not exceed total
        assert kpis["completed_tasks"] <= kpis["total_tasks"]

    def test_analytics_risk_distribution(self, auth_headers):
        """Test risk distribution in analytics."""
        response = client.get("/analytics/", headers=auth_headers)
        assert response.status_code == 200
        risk_dist = response.json()["risk_distribution"]
        
        assert "high" in risk_dist
        assert "medium" in risk_dist
        assert "low" in risk_dist
        
        # All should be non-negative
        assert risk_dist["high"] >= 0
        assert risk_dist["medium"] >= 0
        assert risk_dist["low"] >= 0

    def test_analytics_domain_distribution(self, auth_headers):
        """Test domain distribution in analytics."""
        response = client.get("/analytics/", headers=auth_headers)
        assert response.status_code == 200
        domain_dist = response.json()["domain_distribution"]
        
        # Should be a dictionary (possibly empty initially)
        assert isinstance(domain_dist, dict)

    def test_analytics_timeline_structure(self, auth_headers):
        """Test timeline data structure."""
        response = client.get("/analytics/", headers=auth_headers)
        assert response.status_code == 200
        timeline = response.json()["timeline"]
        
        # Should be a list or dict
        assert isinstance(timeline, (list, dict))


class TestAnalyticsFiltering:
    """Tests for analytics filtering capabilities."""

    def test_analytics_filter_by_date_range(self, auth_headers):
        """Test filtering analytics by date range (if supported)."""
        start_date = (datetime.now() - timedelta(days=30)).isoformat()
        end_date = datetime.now().isoformat()
        
        response = client.get(
            f"/analytics/?start_date={start_date}&end_date={end_date}",
            headers=auth_headers
        )
        # Should handle gracefully - either support or ignore
        assert response.status_code in [200, 422]

    def test_analytics_filter_by_domain(self, auth_headers):
        """Test filtering analytics by domain (if supported)."""
        response = client.get(
            "/analytics/?domain=test_domain",
            headers=auth_headers
        )
        # Should handle gracefully
        assert response.status_code in [200, 422]


class TestAnalyticsDataConsistency:
    """Tests for data consistency in analytics."""

    def test_analytics_no_negative_metrics(self, auth_headers):
        """Test no negative values in metrics."""
        response = client.get("/analytics/", headers=auth_headers)
        data = response.json()
        kpis = data["kpis"]
        risk_dist = data["risk_distribution"]
        
        # No metric should be negative
        for key, value in kpis.items():
            assert value >= 0, f"{key} is negative: {value}"
        
        for key, value in risk_dist.items():
            assert value >= 0, f"risk {key} is negative: {value}"

    def test_analytics_consistency_across_calls(self, auth_headers):
        """Test analytics data is consistent across multiple calls."""
        response1 = client.get("/analytics/", headers=auth_headers)
        response2 = client.get("/analytics/", headers=auth_headers)
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        
        data1 = response1.json()
        data2 = response2.json()
        
        # KPIs should match (no new tasks created between calls)
        assert data1["kpis"]["total_tasks"] == data2["kpis"]["total_tasks"]


class TestAnalyticsPerformance:
    """Tests for analytics performance and limits."""

    def test_analytics_response_time(self, auth_headers):
        """Test analytics endpoint responds in reasonable time."""
        import time
        
        start = time.time()
        response = client.get("/analytics/", headers=auth_headers)
        elapsed = time.time() - start
        
        assert response.status_code == 200
        # Should respond within 5 seconds
        assert elapsed < 5.0

    def test_analytics_response_size(self, auth_headers):
        """Test analytics response is reasonably sized."""
        response = client.get("/analytics/", headers=auth_headers)
        
        assert response.status_code == 200
        # Response should be JSON serializable
        data = response.json()
        assert isinstance(data, dict)


class TestAnalyticsDataTypes:
    """Tests for correct data types in analytics."""

    def test_all_numeric_fields_are_numeric(self, auth_headers):
        """Test all numeric fields have correct types."""
        response = client.get("/analytics/", headers=auth_headers)
        data = response.json()
        
        kpis = data["kpis"]
        for key in ["avg_confidence", "avg_trust_score"]:
            value = kpis.get(key)
            assert isinstance(value, (int, float)), f"{key} is not numeric: {type(value)}"

    def test_all_string_fields_are_strings(self, auth_headers):
        """Test all string fields have correct types."""
        response = client.get("/analytics/", headers=auth_headers)
        data = response.json()
        
        # Any domain keys should be strings
        domain_dist = data["domain_distribution"]
        for key in domain_dist.keys():
            assert isinstance(key, str), f"domain key is not string: {type(key)}"


class TestAnalyticsErrorHandling:
    """Tests for error handling in analytics."""

    def test_analytics_invalid_date_format(self, auth_headers):
        """Test handling of invalid date format."""
        response = client.get(
            "/analytics/?start_date=not-a-date",
            headers=auth_headers
        )
        # Should either accept or return 422
        assert response.status_code in [200, 422]

    def test_analytics_with_invalid_token(self):
        """Test analytics with invalid token."""
        response = client.get("/analytics/", headers={
            "Authorization": "Bearer invalid.token.here"
        })
        assert response.status_code == 403

    def test_analytics_with_expired_token(self):
        """Test analytics with expired token."""
        response = client.get("/analytics/", headers={
            "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE2MDAwMDAwMDB9.invalid"
        })
        assert response.status_code == 403


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
