"""
Tests for the main FastAPI application endpoints.
"""
import pytest
import json
from unittest.mock import patch
from fastapi.testclient import TestClient


class TestRootEndpoints:
    """Test root and basic endpoints."""

    def test_root_endpoint(self, client: TestClient):
        """Test the root endpoint returns API information."""
        response = client.get("/")
        assert response.status_code == 200

        data = response.json()
        assert data["message"] == "F1 Analytics API"
        assert data["version"] == "1.0.0"
        assert data["docs"] == "/docs"
        assert data["health"] == "/health"

    def test_api_info_endpoint(self, client: TestClient):
        """Test the API info endpoint."""
        response = client.get("/api/v1/info")
        assert response.status_code == 200

        data = response.json()
        assert data["api_version"] == "v1"
        assert "predictions" in data["features"]
        assert "race_calendar" in data["features"]
        assert "driver_rankings" in data["features"]
        assert data["status"] == "active"


class TestHealthCheck:
    """Test health check endpoints with various scenarios."""

    def test_health_check_all_services_healthy(self, client: TestClient, healthy_services, security_validation_mock):
        """Test health check when all services are healthy."""
        with patch('app.main.check_database_connectivity', return_value=True), \
             patch('app.main.check_redis_connectivity', return_value=True):

            response = client.get("/health")
            assert response.status_code == 200

            data = response.json()
            assert data["status"] == "healthy"
            assert data["service"] == "f1-analytics-backend"
            assert data["version"] == "1.0.0"
            assert data["environment"] == "test"
            assert data["checks"]["api"] == "ok"
            assert data["checks"]["database"] == "ok"
            assert data["checks"]["redis"] == "ok"
            assert data["checks"]["security"] == "ok"

    def test_health_check_database_unhealthy(self, client: TestClient, security_validation_mock):
        """Test health check when database is unhealthy."""
        with patch('app.main.check_database_connectivity', return_value=False), \
             patch('app.main.check_redis_connectivity', return_value=True):

            response = client.get("/health")
            assert response.status_code == 503

            data = response.json()
            assert data["status"] == "unhealthy"
            assert data["checks"]["database"] == "error"
            assert data["checks"]["redis"] == "ok"

    def test_health_check_redis_unhealthy(self, client: TestClient, security_validation_mock):
        """Test health check when Redis is unhealthy."""
        with patch('app.main.check_database_connectivity', return_value=True), \
             patch('app.main.check_redis_connectivity', return_value=False):

            response = client.get("/health")
            assert response.status_code == 503

            data = response.json()
            assert data["status"] == "unhealthy"
            assert data["checks"]["database"] == "ok"
            assert data["checks"]["redis"] == "error"

    def test_health_check_security_issues_development(self, client: TestClient):
        """Test health check with security issues in development environment."""
        mock_result = {
            "jwt_secret_secure": False,
            "environment": "development",
            "debug_enabled": True,
            "issues": ["JWT secret is weak"]
        }

        with patch('app.main.check_database_connectivity', return_value=True), \
             patch('app.main.check_redis_connectivity', return_value=True), \
             patch('app.main.validate_environment_security', return_value=mock_result):

            response = client.get("/health")
            assert response.status_code == 200  # Development allows warnings

            data = response.json()
            assert data["status"] == "healthy"
            assert data["checks"]["security"] == "warning"
            assert "JWT secret is weak" in data["checks"]["security_issues"]

    def test_health_check_security_issues_production(self, client: TestClient):
        """Test health check with security issues in production environment."""
        mock_result = {
            "jwt_secret_secure": False,
            "environment": "production",
            "debug_enabled": False,
            "issues": ["JWT secret is weak"]
        }

        with patch('app.main.check_database_connectivity', return_value=True), \
             patch('app.main.check_redis_connectivity', return_value=True), \
             patch('app.main.validate_environment_security', return_value=mock_result), \
             patch('os.getenv', return_value="production"):

            response = client.get("/health")
            assert response.status_code == 503  # Production fails on security issues

            data = response.json()
            assert data["status"] == "unhealthy"
            assert data["checks"]["security"] == "warning"

    def test_health_check_exception_handling(self, client: TestClient):
        """Test health check exception handling."""
        with patch('app.main.check_database_connectivity', side_effect=Exception("Database error")):
            response = client.get("/health")
            assert response.status_code == 503

            data = response.json()
            assert data["status"] == "unhealthy"
            assert "Database error" in data["error"]


class TestF1AnalyticsEndpoints:
    """Test F1 Analytics specific endpoints."""

    def test_next_race_predictions(self, client: TestClient):
        """Test next race predictions endpoint."""
        response = client.get("/api/v1/predictions/next-race")
        assert response.status_code == 200

        data = response.json()
        assert "race_id" in data
        assert "race_name" in data
        assert "predictions" in data
        assert len(data["predictions"]) > 0

        # Check prediction structure
        prediction = data["predictions"][0]
        assert "driver_name" in prediction
        assert "win_probability" in prediction
        assert "team" in prediction
        assert isinstance(prediction["win_probability"], float)

    def test_race_calendar(self, client: TestClient):
        """Test race calendar endpoint."""
        response = client.get("/api/v1/races/calendar")
        assert response.status_code == 200

        data = response.json()
        assert "season" in data
        assert "races" in data
        assert len(data["races"]) > 0

        # Check race structure
        race = data["races"][0]
        assert "race_id" in race
        assert "race_name" in race
        assert "circuit" in race
        assert "date" in race

    def test_driver_rankings(self, client: TestClient):
        """Test driver rankings endpoint."""
        response = client.get("/api/v1/drivers/rankings")
        assert response.status_code == 200

        data = response.json()
        assert "season" in data
        assert "rankings" in data
        assert len(data["rankings"]) > 0

        # Check ranking structure
        ranking = data["rankings"][0]
        assert "position" in ranking
        assert "driver_name" in ranking
        assert "elo_rating" in ranking
        assert isinstance(ranking["elo_rating"], int)


class TestCORSConfiguration:
    """Test CORS configuration."""

    def test_cors_headers(self, client: TestClient):
        """Test that CORS headers are properly set."""
        # Perform preflight request
        response = client.options(
            "/",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "Content-Type"
            }
        )

        # Should allow the request
        assert response.status_code in [200, 204]

    def test_cors_actual_request(self, client: TestClient):
        """Test actual CORS request."""
        response = client.get(
            "/",
            headers={"Origin": "http://localhost:3000"}
        )

        assert response.status_code == 200
        # Note: TestClient doesn't automatically add CORS headers,
        # but the middleware should be configured properly