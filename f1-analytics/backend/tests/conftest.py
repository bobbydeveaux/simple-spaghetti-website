"""
Pytest configuration and fixtures for F1 Analytics tests.

This module provides comprehensive test fixtures including database setup,
test data factories, security testing configuration, and test environment management.
Combines comprehensive testing features with security validation and clean test data management.
"""

import pytest
import asyncio
import os
import tempfile
from datetime import datetime, timezone, date
from typing import Generator
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import redis.asyncio as redis

from app.database import Base, db_manager
from app.config import settings
from app.models.user import User
from app.models import (
    Driver, Team, Circuit, Race, RaceResult,
    QualifyingResult, WeatherData, Prediction,
    PredictionAccuracy
)
from app.repositories.user_repository import UserRepository

# Set test environment variables
os.environ["ENVIRONMENT"] = "test"
os.environ["DEBUG"] = "false"
os.environ["JWT_SECRET_KEY"] = "test_jwt_secret_key_for_testing_minimum_32_chars_required"
os.environ["DATABASE_URL"] = "postgresql://test:test@localhost/test_db"
os.environ["REDIS_URL"] = "redis://localhost:6379/1"

# Use SQLite for testing
TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_engine():
    """Create a test database engine using SQLite in-memory."""
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def db_session(test_engine):
    """Create a fresh database session for each test."""
    TestingSessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=test_engine
    )
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        # Clean up all tables after each test
        for table in reversed(Base.metadata.sorted_tables):
            test_engine.execute(table.delete())


@pytest.fixture(scope="function")
async def redis_client():
    """Create a test Redis client."""
    try:
        # Use a test Redis database
        client = redis.Redis.from_url("redis://localhost:6379/1", decode_responses=True)

        # Clear the test database
        await client.flushdb()

        yield client

        # Clean up
        await client.flushdb()
        await client.close()
    except Exception:
        # Redis not available, yield None
        yield None


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
def sample_user_data():
    """Sample user data for testing."""
    return {
        "email": "test@example.com",
        "password_hash": "$2b$12$examplehashedpassword",
        "username": "testuser",
        "role": "user",
        "is_active": True,
        "is_verified": False
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


@pytest.fixture
def sample_admin_data():
    """Sample admin user data for testing."""
    return {
        "email": "admin@example.com",
        "password_hash": "$2b$12$examplehashedpassword",
        "username": "admin",
        "role": "admin",
        "is_active": True,
        "is_verified": True
    }


@pytest.fixture
def sample_driver_data():
    """Sample driver data for testing."""
    return {
        "driver_code": "TST",
        "driver_name": "Test Driver",
        "nationality": "Test Country",
        "date_of_birth": date(1990, 1, 1),
        "current_elo_rating": 1500
    }


@pytest.fixture
def sample_team_data():
    """Sample team data for testing."""
    return {
        "team_name": "Test Team",
        "nationality": "Test Country",
        "current_elo_rating": 1500,
        "team_color": "#FF0000"
    }


@pytest.fixture
def sample_circuit_data():
    """Sample circuit data for testing."""
    return {
        "circuit_name": "Test Circuit",
        "location": "Test Location",
        "country": "Test Country",
        "track_length_km": 5.0,
        "track_type": "PERMANENT"  # Use string instead of enum for compatibility
    }


@pytest.fixture
def sample_race_data():
    """Sample race data for testing."""
    return {
        "season_year": 2026,
        "round_number": 1,
        "race_date": date(2026, 3, 15),
        "race_name": "Test Grand Prix",
        "status": "SCHEDULED"  # Use string instead of enum for compatibility
    }


@pytest.fixture
def test_user(db_session, sample_user_data):
    """Create a test user in the database."""
    user = User(**sample_user_data)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_admin_user(db_session, sample_admin_data):
    """Create a test admin user in the database."""
    admin = User(**sample_admin_data)
    db_session.add(admin)
    db_session.commit()
    db_session.refresh(admin)
    return admin


@pytest.fixture
def test_team(db_session, sample_team_data):
    """Create a test team in the database."""
    team = Team(**sample_team_data)
    db_session.add(team)
    db_session.commit()
    db_session.refresh(team)
    return team


@pytest.fixture
def test_driver(db_session, sample_driver_data, test_team):
    """Create a test driver in the database."""
    driver_data = sample_driver_data.copy()
    driver_data["current_team_id"] = test_team.team_id
    driver = Driver(**driver_data)
    db_session.add(driver)
    db_session.commit()
    db_session.refresh(driver)
    return driver


@pytest.fixture
def test_circuit(db_session, sample_circuit_data):
    """Create a test circuit in the database."""
    circuit = Circuit(**sample_circuit_data)
    db_session.add(circuit)
    db_session.commit()
    db_session.refresh(circuit)
    return circuit


@pytest.fixture
def test_race(db_session, sample_race_data, test_circuit):
    """Create a test race in the database."""
    race_data = sample_race_data.copy()
    race_data["circuit_id"] = test_circuit.circuit_id
    race = Race(**race_data)
    db_session.add(race)
    db_session.commit()
    db_session.refresh(race)
    return race


@pytest.fixture
def test_race_result(db_session, test_race, test_driver, test_team):
    """Create a test race result in the database."""
    result_data = {
        "race_id": test_race.race_id,
        "driver_id": test_driver.driver_id,
        "team_id": test_team.team_id,
        "grid_position": 1,
        "final_position": 1,
        "points": 25.0,
        "fastest_lap_time": "1:23.456"
    }
    result = RaceResult(**result_data)
    db_session.add(result)
    db_session.commit()
    db_session.refresh(result)
    return result


@pytest.fixture
def test_prediction(db_session, test_race, test_driver):
    """Create a test prediction in the database."""
    prediction_data = {
        "race_id": test_race.race_id,
        "driver_id": test_driver.driver_id,
        "predicted_win_probability": 35.5,
        "model_version": "v1.0.0",
        "prediction_timestamp": datetime.now(timezone.utc)
    }
    prediction = Prediction(**prediction_data)
    db_session.add(prediction)
    db_session.commit()
    db_session.refresh(prediction)
    return prediction


@pytest.fixture
def user_repository(db_session):
    """Create a user repository instance."""
    return UserRepository(db_session)


@pytest.fixture
def valid_jwt_token(test_user):
    """Create a valid JWT token for testing."""
    try:
        from app.utils.jwt_manager import jwt_manager
        return jwt_manager.create_access_token(
            user_id=test_user.user_id,
            email=test_user.email
        )
    except ImportError:
        # JWT manager not available, return a mock token
        return "mock_jwt_token"


@pytest.fixture
def admin_jwt_token(test_admin_user):
    """Create a valid admin JWT token for testing."""
    try:
        from app.utils.jwt_manager import jwt_manager
        return jwt_manager.create_access_token(
            user_id=test_admin_user.user_id,
            email=test_admin_user.email,
            additional_claims={"role": "admin"}
        )
    except ImportError:
        # JWT manager not available, return a mock token
        return "mock_admin_jwt_token"


@pytest.fixture
def expired_jwt_token():
    """Create an expired JWT token for testing."""
    import jwt
    from datetime import timedelta

    payload = {
        "sub": "123",
        "email": "test@example.com",
        "type": "access",
        "exp": datetime.now(timezone.utc) - timedelta(hours=1),
        "iat": datetime.now(timezone.utc) - timedelta(hours=2)
    }

    try:
        return jwt.encode(payload, "test_secret", algorithm="HS256")
    except Exception:
        # JWT not available, return mock expired token
        return "mock_expired_token"


@pytest.fixture
def mock_session_data():
    """Mock session data for testing."""
    return {
        "user_id": 123,
        "email": "test@example.com",
        "created_at": datetime.now(timezone.utc),
        "last_accessed": datetime.now(timezone.utc),
        "ip_address": "127.0.0.1",
        "user_agent": "Test Agent"
    }


# Test database health check
@pytest.fixture(autouse=True)
def check_test_environment():
    """Ensure we're running in test environment."""
    if not TEST_DATABASE_URL:
        pytest.fail("Test database URL not configured")

    # Ensure we don't accidentally connect to production database
    try:
        if "production" in str(settings.database.database_url).lower():
            pytest.fail("Cannot run tests against production database")
    except Exception:
        # Settings not available, continue with tests
        pass


class TestDataBuilder:
    """Helper class to build test data."""

    def __init__(self, db_session):
        self.db_session = db_session

    def create_season_data(self, season_year: int = 2026, num_races: int = 3):
        """Create a full season of test data."""
        # Create teams
        teams = []
        for i in range(2):
            team = Team(
                team_name=f"Test Team {i+1}",
                nationality=f"Country {i+1}",
                current_elo_rating=1500 + i * 100,
                team_color=f"#{'FF' if i == 0 else '00'}0000"
            )
            self.db_session.add(team)
            teams.append(team)

        # Create drivers
        drivers = []
        for i, team in enumerate(teams):
            for j in range(2):  # 2 drivers per team
                driver = Driver(
                    driver_code=f"T{i+1}{j+1}",
                    driver_name=f"Test Driver {i+1}-{j+1}",
                    nationality=team.nationality,
                    date_of_birth=date(1990 + i, j+1, 1),
                    current_team_id=team.team_id,
                    current_elo_rating=1500 + i * 50 + j * 25
                )
                self.db_session.add(driver)
                drivers.append(driver)

        # Create circuits
        circuits = []
        for i in range(num_races):
            circuit = Circuit(
                circuit_name=f"Test Circuit {i+1}",
                location=f"Test City {i+1}",
                country=f"Test Country {i+1}",
                track_length_km=4.0 + i * 0.5,
                track_type="PERMANENT"
            )
            self.db_session.add(circuit)
            circuits.append(circuit)

        # Create races
        races = []
        for i, circuit in enumerate(circuits):
            race = Race(
                season_year=season_year,
                round_number=i + 1,
                circuit_id=circuit.circuit_id,
                race_date=date(season_year, 3, 15 + i * 14),  # Every 2 weeks
                race_name=f"Test Grand Prix {i+1}",
                status="COMPLETED" if i < num_races - 1 else "SCHEDULED"
            )
            self.db_session.add(race)
            races.append(race)

        self.db_session.commit()

        # Refresh all objects
        for obj in teams + drivers + circuits + races:
            self.db_session.refresh(obj)

        return {
            "teams": teams,
            "drivers": drivers,
            "circuits": circuits,
            "races": races
        }


@pytest.fixture
def test_data_builder(db_session):
    """Create a test data builder instance."""
    return TestDataBuilder(db_session)
