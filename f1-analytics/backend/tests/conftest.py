"""
Pytest configuration and fixtures for F1 Analytics backend tests.
"""
import os
import pytest
import asyncio
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch

# Set test environment
os.environ["ENVIRONMENT"] = "test"
os.environ["DEBUG"] = "false"
os.environ["JWT_SECRET_KEY"] = "test_jwt_secret_key_for_testing_minimum_32_chars_required"
os.environ["DATABASE_URL"] = "postgresql://test:test@localhost/test_db"
os.environ["REDIS_URL"] = "redis://localhost:6379/1"


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_redis():
    """Mock Redis connection for testing."""
    with patch('redis.Redis') as mock:
        mock_instance = Mock()
        mock_instance.ping.return_value = True
        mock.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_postgres():
    """Mock PostgreSQL connection for testing."""
    with patch('psycopg2.connect') as mock_connect:
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = (1,)
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        yield mock_conn


@pytest.fixture
def client():
    """Create a test client for the FastAPI application."""
    # Import after setting environment variables
    from app.main import app

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def healthy_services(mock_redis, mock_postgres):
    """Mock all services as healthy for testing."""
    return {
        'redis': mock_redis,
        'postgres': mock_postgres
    }


@pytest.fixture
def security_validation_mock():
    """Mock security validation to return clean results."""
    mock_result = {
        "jwt_secret_secure": True,
        "environment": "test",
        "debug_enabled": False,
        "issues": []
    }

    with patch('app.core.security.validate_environment_security', return_value=mock_result):
        yield mock_result