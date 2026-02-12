"""
Tests for authentication routes.
"""
import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timezone
from unittest.mock import patch
import os

# Set required environment variable for testing
os.environ["JWT_SECRET"] = "test-jwt-secret-for-testing-only-do-not-use-in-production"

from api.main import app
from api.services.user_repository import user_repository
from api.models.user import User


@pytest.fixture
def client():
    """Test client fixture."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def cleanup_users():
    """Clean up users before and after each test."""
    user_repository.clear_all_users()
    yield
    user_repository.clear_all_users()


class TestAuthRoutes:
    """Test suite for authentication routes."""

    def test_register_user_success(self, client):
        """Test successful user registration."""
        response = client.post("/api/v1/auth/register", json={
            "email": "test@example.com",
            "password": "password123"
        })

        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "test@example.com"
        assert "created_at" in data
        assert "password" not in data  # Should not return password

        # Verify user was actually created
        assert user_repository.user_exists("test@example.com")

    def test_register_user_duplicate_email(self, client):
        """Test registration with duplicate email fails."""
        # Register first user
        client.post("/api/v1/auth/register", json={
            "email": "test@example.com",
            "password": "password123"
        })

        # Try to register with same email
        response = client.post("/api/v1/auth/register", json={
            "email": "test@example.com",
            "password": "different123"
        })

        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    def test_register_user_invalid_email(self, client):
        """Test registration with invalid email fails."""
        response = client.post("/api/v1/auth/register", json={
            "email": "invalid-email",
            "password": "password123"
        })

        assert response.status_code == 422

    def test_register_user_weak_password(self, client):
        """Test registration with weak password fails."""
        # Too short
        response = client.post("/api/v1/auth/register", json={
            "email": "test@example.com",
            "password": "short1"
        })
        assert response.status_code == 422

        # No letters
        response = client.post("/api/v1/auth/register", json={
            "email": "test@example.com",
            "password": "12345678"
        })
        assert response.status_code == 422

        # No digits
        response = client.post("/api/v1/auth/register", json={
            "email": "test@example.com",
            "password": "password"
        })
        assert response.status_code == 422

    def test_login_user_success(self, client):
        """Test successful user login."""
        # First register a user
        client.post("/api/v1/auth/register", json={
            "email": "test@example.com",
            "password": "password123"
        })

        # Then login
        response = client.post("/api/v1/auth/login", json={
            "email": "test@example.com",
            "password": "password123"
        })

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    def test_login_user_invalid_email(self, client):
        """Test login with non-existent email fails."""
        response = client.post("/api/v1/auth/login", json={
            "email": "nonexistent@example.com",
            "password": "password123"
        })

        assert response.status_code == 401
        assert "Invalid email or password" in response.json()["detail"]

    def test_login_user_wrong_password(self, client):
        """Test login with wrong password fails."""
        # First register a user
        client.post("/api/v1/auth/register", json={
            "email": "test@example.com",
            "password": "password123"
        })

        # Try login with wrong password
        response = client.post("/api/v1/auth/login", json={
            "email": "test@example.com",
            "password": "wrongpassword"
        })

        assert response.status_code == 401
        assert "Invalid email or password" in response.json()["detail"]

    def test_refresh_token_success(self, client):
        """Test successful token refresh."""
        # Register and login to get tokens
        client.post("/api/v1/auth/register", json={
            "email": "test@example.com",
            "password": "password123"
        })

        login_response = client.post("/api/v1/auth/login", json={
            "email": "test@example.com",
            "password": "password123"
        })

        refresh_token = login_response.json()["refresh_token"]

        # Use refresh token to get new tokens
        response = client.post("/api/v1/auth/refresh", json={
            "refresh_token": refresh_token
        })

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    def test_refresh_token_invalid(self, client):
        """Test refresh with invalid token fails."""
        response = client.post("/api/v1/auth/refresh", json={
            "refresh_token": "invalid.refresh.token"
        })

        assert response.status_code == 401
        assert "Invalid or expired refresh token" in response.json()["detail"]

    def test_refresh_token_wrong_type(self, client):
        """Test refresh with access token (wrong type) fails."""
        # Register and login to get tokens
        client.post("/api/v1/auth/register", json={
            "email": "test@example.com",
            "password": "password123"
        })

        login_response = client.post("/api/v1/auth/login", json={
            "email": "test@example.com",
            "password": "password123"
        })

        access_token = login_response.json()["access_token"]

        # Try to use access token for refresh (should fail)
        response = client.post("/api/v1/auth/refresh", json={
            "refresh_token": access_token
        })

        assert response.status_code == 401

    def test_get_user_profile_success(self, client):
        """Test getting user profile with valid token."""
        # Register and login
        client.post("/api/v1/auth/register", json={
            "email": "test@example.com",
            "password": "password123"
        })

        login_response = client.post("/api/v1/auth/login", json={
            "email": "test@example.com",
            "password": "password123"
        })

        access_token = login_response.json()["access_token"]

        # Get profile
        response = client.get("/api/v1/auth/profile", headers={
            "Authorization": f"Bearer {access_token}"
        })

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "test@example.com"
        assert "created_at" in data

    def test_get_user_profile_no_token(self, client):
        """Test getting profile without token fails."""
        response = client.get("/api/v1/auth/profile")

        assert response.status_code == 403  # FastAPI HTTPBearer returns 403 for missing token

    def test_get_user_profile_invalid_token(self, client):
        """Test getting profile with invalid token fails."""
        response = client.get("/api/v1/auth/profile", headers={
            "Authorization": "Bearer invalid.token.here"
        })

        assert response.status_code == 401

    def test_protected_endpoint_success(self, client):
        """Test accessing protected endpoint with valid token."""
        # Register and login
        client.post("/api/v1/auth/register", json={
            "email": "test@example.com",
            "password": "password123"
        })

        login_response = client.post("/api/v1/auth/login", json={
            "email": "test@example.com",
            "password": "password123"
        })

        access_token = login_response.json()["access_token"]

        # Access protected endpoint
        response = client.get("/api/v1/auth/protected", headers={
            "Authorization": f"Bearer {access_token}"
        })

        assert response.status_code == 200
        data = response.json()
        assert "test@example.com" in data["message"]
        assert data["user"] == "test@example.com"

    def test_protected_endpoint_no_token(self, client):
        """Test accessing protected endpoint without token fails."""
        response = client.get("/api/v1/auth/protected")

        assert response.status_code == 403

    def test_health_endpoint_public(self, client):
        """Test that health endpoint is publicly accessible."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"