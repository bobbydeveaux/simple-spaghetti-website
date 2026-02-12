"""
Tests for session management functionality.

This module tests JWT token management, Redis session storage,
rate limiting, and caching functionality.
"""

import pytest
import asyncio
import json
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch

from app.utils.jwt_manager import (
    jwt_manager, JWTError, ExpiredTokenError, InvalidTokenError
)
from app.utils.session_manager import (
    session_manager, UserSession, SessionStatus, SessionError
)
from app.config import settings


class TestJWTManager:
    """Test JWT token management functionality."""

    def test_create_access_token(self, test_user):
        """Test creating an access token."""
        token = jwt_manager.create_access_token(
            user_id=test_user.user_id,
            email=test_user.email
        )

        assert isinstance(token, str)
        assert len(token) > 0

        # Verify token can be decoded
        payload = jwt_manager.decode_token(token)
        assert payload["sub"] == str(test_user.user_id)
        assert payload["email"] == test_user.email
        assert payload["type"] == "access"

    def test_create_refresh_token(self, test_user):
        """Test creating a refresh token."""
        token = jwt_manager.create_refresh_token(
            user_id=test_user.user_id,
            email=test_user.email
        )

        assert isinstance(token, str)
        assert len(token) > 0

        # Verify token can be decoded
        payload = jwt_manager.decode_token(token)
        assert payload["sub"] == str(test_user.user_id)
        assert payload["email"] == test_user.email
        assert payload["type"] == "refresh"

    def test_create_token_pair(self, test_user):
        """Test creating a token pair."""
        tokens = jwt_manager.create_token_pair(
            user_id=test_user.user_id,
            email=test_user.email
        )

        assert isinstance(tokens, dict)
        assert "access_token" in tokens
        assert "refresh_token" in tokens
        assert "token_type" in tokens
        assert tokens["token_type"] == "bearer"

        # Both tokens should be valid
        access_payload = jwt_manager.decode_token(tokens["access_token"])
        refresh_payload = jwt_manager.decode_token(tokens["refresh_token"])

        assert access_payload["type"] == "access"
        assert refresh_payload["type"] == "refresh"

    def test_decode_valid_token(self, valid_jwt_token):
        """Test decoding a valid token."""
        payload = jwt_manager.decode_token(valid_jwt_token)

        assert isinstance(payload, dict)
        assert "sub" in payload
        assert "email" in payload
        assert "type" in payload
        assert "exp" in payload
        assert "iat" in payload

    def test_decode_expired_token(self, expired_jwt_token):
        """Test decoding an expired token."""
        with pytest.raises(ExpiredTokenError):
            jwt_manager.decode_token(expired_jwt_token)

    def test_decode_invalid_token(self):
        """Test decoding an invalid token."""
        with pytest.raises(InvalidTokenError):
            jwt_manager.decode_token("invalid.token.here")

    def test_verify_token_type(self, test_user):
        """Test token type verification."""
        access_token = jwt_manager.create_access_token(
            user_id=test_user.user_id,
            email=test_user.email
        )
        refresh_token = jwt_manager.create_refresh_token(
            user_id=test_user.user_id,
            email=test_user.email
        )

        access_payload = jwt_manager.decode_token(access_token)
        refresh_payload = jwt_manager.decode_token(refresh_token)

        # Valid type verification
        assert jwt_manager.verify_token_type(access_payload, "access")
        assert jwt_manager.verify_token_type(refresh_payload, "refresh")

        # Invalid type verification
        with pytest.raises(InvalidTokenError):
            jwt_manager.verify_token_type(access_payload, "refresh")
        with pytest.raises(InvalidTokenError):
            jwt_manager.verify_token_type(refresh_payload, "access")

    def test_get_user_from_token(self, test_user):
        """Test extracting user information from token."""
        token = jwt_manager.create_access_token(
            user_id=test_user.user_id,
            email=test_user.email,
            additional_claims={"role": "user"}
        )

        user_info = jwt_manager.get_user_from_token(token)

        assert user_info["user_id"] == test_user.user_id
        assert user_info["email"] == test_user.email
        assert isinstance(user_info["expires_at"], datetime)
        assert isinstance(user_info["issued_at"], datetime)
        assert "additional_claims" in user_info
        assert user_info["additional_claims"]["role"] == "user"

    def test_is_token_expired(self, valid_jwt_token, expired_jwt_token):
        """Test token expiration check."""
        assert not jwt_manager.is_token_expired(valid_jwt_token)
        assert jwt_manager.is_token_expired(expired_jwt_token)
        assert jwt_manager.is_token_expired("invalid.token")

    def test_refresh_access_token(self, test_user):
        """Test refreshing an access token."""
        refresh_token = jwt_manager.create_refresh_token(
            user_id=test_user.user_id,
            email=test_user.email
        )

        new_access_token = jwt_manager.refresh_access_token(refresh_token)

        # Verify new token
        payload = jwt_manager.decode_token(new_access_token)
        assert payload["sub"] == str(test_user.user_id)
        assert payload["email"] == test_user.email
        assert payload["type"] == "access"

    def test_get_token_expiration_info(self, valid_jwt_token):
        """Test getting token expiration information."""
        info = jwt_manager.get_token_expiration_info(valid_jwt_token)

        assert isinstance(info, dict)
        assert info["has_expiration"] is True
        assert "expires_at" in info
        assert "issued_at" in info
        assert info["is_expired"] is False
        assert "time_until_expiry" in info

    def test_token_with_additional_claims(self, test_user):
        """Test tokens with additional claims."""
        additional_claims = {
            "role": "admin",
            "permissions": ["read", "write"],
            "custom_field": "test_value"
        }

        token = jwt_manager.create_access_token(
            user_id=test_user.user_id,
            email=test_user.email,
            additional_claims=additional_claims
        )

        user_info = jwt_manager.get_user_from_token(token)
        claims = user_info["additional_claims"]

        assert claims["role"] == "admin"
        assert claims["permissions"] == ["read", "write"]
        assert claims["custom_field"] == "test_value"


class TestSessionManager:
    """Test Redis session management functionality."""

    @pytest.fixture(autouse=True)
    async def setup_session_manager(self, redis_client):
        """Setup session manager with test Redis client."""
        session_manager.redis_client = redis_client
        session_manager._connection_pool = None  # Mock connection pool
        yield
        await session_manager.close()

    @pytest.mark.asyncio
    async def test_create_session(self, mock_session_data):
        """Test creating a user session."""
        session = await session_manager.create_session(
            user_id=mock_session_data["user_id"],
            email=mock_session_data["email"],
            ip_address=mock_session_data["ip_address"],
            user_agent=mock_session_data["user_agent"]
        )

        assert isinstance(session, UserSession)
        assert session.user_id == mock_session_data["user_id"]
        assert session.email == mock_session_data["email"]
        assert session.ip_address == mock_session_data["ip_address"]
        assert session.user_agent == mock_session_data["user_agent"]
        assert isinstance(session.created_at, datetime)
        assert isinstance(session.last_accessed, datetime)

    @pytest.mark.asyncio
    async def test_get_session(self, mock_session_data):
        """Test retrieving a user session."""
        # Create a session first
        await session_manager.create_session(
            user_id=mock_session_data["user_id"],
            email=mock_session_data["email"]
        )

        # Retrieve the session
        session = await session_manager.get_session(mock_session_data["user_id"])

        assert session is not None
        assert session.user_id == mock_session_data["user_id"]
        assert session.email == mock_session_data["email"]

    @pytest.mark.asyncio
    async def test_get_nonexistent_session(self):
        """Test retrieving a non-existent session."""
        session = await session_manager.get_session(999)
        assert session is None

    @pytest.mark.asyncio
    async def test_update_session_access(self, mock_session_data):
        """Test updating session access time."""
        # Create a session
        original_session = await session_manager.create_session(
            user_id=mock_session_data["user_id"],
            email=mock_session_data["email"]
        )

        # Wait a bit to ensure timestamp difference
        await asyncio.sleep(0.1)

        # Update access time
        success = await session_manager.update_session_access(
            mock_session_data["user_id"]
        )
        assert success

        # Verify access time was updated
        updated_session = await session_manager.get_session(
            mock_session_data["user_id"]
        )
        assert updated_session.last_accessed > original_session.last_accessed

    @pytest.mark.asyncio
    async def test_delete_session(self, mock_session_data):
        """Test deleting a user session."""
        # Create a session
        await session_manager.create_session(
            user_id=mock_session_data["user_id"],
            email=mock_session_data["email"]
        )

        # Delete the session
        success = await session_manager.delete_session(mock_session_data["user_id"])
        assert success

        # Verify session is deleted
        session = await session_manager.get_session(mock_session_data["user_id"])
        assert session is None

    @pytest.mark.asyncio
    async def test_check_rate_limit(self, mock_session_data):
        """Test rate limiting functionality."""
        user_id = mock_session_data["user_id"]

        # First request should be allowed
        rate_limit = await session_manager.check_rate_limit(user_id)
        assert rate_limit["allowed"] is True
        assert rate_limit["current_requests"] == 1
        assert rate_limit["remaining_requests"] == settings.app.rate_limit_requests - 1

        # Make multiple requests
        for i in range(5):
            await session_manager.check_rate_limit(user_id)

        # Check final rate limit status
        rate_limit = await session_manager.check_rate_limit(user_id)
        assert rate_limit["current_requests"] == 7  # 1 + 5 + 1

    @pytest.mark.asyncio
    async def test_cache_data(self):
        """Test caching data functionality."""
        cache_type = "test"
        identifier = "test_data"
        test_data = {"key": "value", "number": 123}

        # Cache the data
        success = await session_manager.cache_data(
            cache_type, identifier, test_data, ttl_seconds=60
        )
        assert success

        # Retrieve the cached data
        cached_data = await session_manager.get_cached_data(cache_type, identifier)
        assert cached_data == test_data

    @pytest.mark.asyncio
    async def test_get_nonexistent_cached_data(self):
        """Test retrieving non-existent cached data."""
        cached_data = await session_manager.get_cached_data("nonexistent", "data")
        assert cached_data is None

    @pytest.mark.asyncio
    async def test_invalidate_cache(self):
        """Test cache invalidation."""
        cache_type = "test"
        identifier = "test_invalidate"
        test_data = {"test": "data"}

        # Cache some data
        await session_manager.cache_data(cache_type, identifier, test_data)

        # Verify data is cached
        cached_data = await session_manager.get_cached_data(cache_type, identifier)
        assert cached_data == test_data

        # Invalidate the cache
        success = await session_manager.invalidate_cache(cache_type, identifier)
        assert success

        # Verify data is no longer cached
        cached_data = await session_manager.get_cached_data(cache_type, identifier)
        assert cached_data is None

    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test session manager health check."""
        health_status = await session_manager.health_check()

        assert isinstance(health_status, dict)
        assert "status" in health_status
        assert health_status["status"] in ["healthy", "unhealthy"]

        if health_status["status"] == "healthy":
            assert "redis_connected" in health_status
            assert "active_sessions" in health_status
            assert "timestamp" in health_status


class TestUserSession:
    """Test UserSession data structure."""

    def test_user_session_creation(self, mock_session_data):
        """Test creating a UserSession object."""
        session = UserSession(
            user_id=mock_session_data["user_id"],
            email=mock_session_data["email"],
            created_at=mock_session_data["created_at"],
            last_accessed=mock_session_data["last_accessed"],
            ip_address=mock_session_data["ip_address"],
            user_agent=mock_session_data["user_agent"]
        )

        assert session.user_id == mock_session_data["user_id"]
        assert session.email == mock_session_data["email"]
        assert session.ip_address == mock_session_data["ip_address"]
        assert session.user_agent == mock_session_data["user_agent"]

    def test_user_session_to_dict(self, mock_session_data):
        """Test converting UserSession to dictionary."""
        session = UserSession(
            user_id=mock_session_data["user_id"],
            email=mock_session_data["email"],
            created_at=mock_session_data["created_at"],
            last_accessed=mock_session_data["last_accessed"]
        )

        session_dict = session.to_dict()

        assert isinstance(session_dict, dict)
        assert session_dict["user_id"] == mock_session_data["user_id"]
        assert session_dict["email"] == mock_session_data["email"]
        # Timestamps should be converted to ISO strings
        assert isinstance(session_dict["created_at"], str)
        assert isinstance(session_dict["last_accessed"], str)

    def test_user_session_from_dict(self, mock_session_data):
        """Test creating UserSession from dictionary."""
        # First create and convert to dict
        original_session = UserSession(
            user_id=mock_session_data["user_id"],
            email=mock_session_data["email"],
            created_at=mock_session_data["created_at"],
            last_accessed=mock_session_data["last_accessed"]
        )
        session_dict = original_session.to_dict()

        # Then recreate from dict
        recreated_session = UserSession.from_dict(session_dict)

        assert recreated_session.user_id == original_session.user_id
        assert recreated_session.email == original_session.email
        assert recreated_session.created_at == original_session.created_at
        assert recreated_session.last_accessed == original_session.last_accessed


class TestSessionIntegration:
    """Test integration between JWT and session management."""

    @pytest.fixture(autouse=True)
    async def setup_session_manager(self, redis_client):
        """Setup session manager with test Redis client."""
        session_manager.redis_client = redis_client
        session_manager._connection_pool = None
        yield
        await session_manager.close()

    @pytest.mark.asyncio
    async def test_login_flow_integration(self, test_user):
        """Test complete login flow with JWT and session creation."""
        # Create JWT tokens
        tokens = jwt_manager.create_token_pair(
            user_id=test_user.user_id,
            email=test_user.email
        )

        # Create session
        session = await session_manager.create_session(
            user_id=test_user.user_id,
            email=test_user.email,
            ip_address="127.0.0.1",
            user_agent="Test Browser"
        )

        # Verify token is valid
        user_info = jwt_manager.get_user_from_token(tokens["access_token"])
        assert user_info["user_id"] == test_user.user_id

        # Verify session exists
        stored_session = await session_manager.get_session(test_user.user_id)
        assert stored_session is not None
        assert stored_session.email == test_user.email

    @pytest.mark.asyncio
    async def test_logout_flow_integration(self, test_user):
        """Test complete logout flow."""
        # Create session
        await session_manager.create_session(
            user_id=test_user.user_id,
            email=test_user.email
        )

        # Verify session exists
        session = await session_manager.get_session(test_user.user_id)
        assert session is not None

        # Logout (delete session)
        success = await session_manager.delete_session(test_user.user_id)
        assert success

        # Verify session is deleted
        session = await session_manager.get_session(test_user.user_id)
        assert session is None

    @pytest.mark.asyncio
    async def test_token_refresh_with_session_update(self, test_user):
        """Test token refresh with session access update."""
        # Create initial tokens and session
        initial_tokens = jwt_manager.create_token_pair(
            user_id=test_user.user_id,
            email=test_user.email
        )

        session = await session_manager.create_session(
            user_id=test_user.user_id,
            email=test_user.email
        )
        original_access_time = session.last_accessed

        # Wait a bit
        await asyncio.sleep(0.1)

        # Refresh access token
        new_access_token = jwt_manager.refresh_access_token(
            initial_tokens["refresh_token"]
        )

        # Update session access
        await session_manager.update_session_access(test_user.user_id)

        # Verify new token is valid
        user_info = jwt_manager.get_user_from_token(new_access_token)
        assert user_info["user_id"] == test_user.user_id

        # Verify session access time was updated
        updated_session = await session_manager.get_session(test_user.user_id)
        assert updated_session.last_accessed > original_access_time