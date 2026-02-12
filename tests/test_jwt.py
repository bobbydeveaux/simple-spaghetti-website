"""
Tests for JWT token utilities.
"""
import pytest
import jwt
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from api.utils.jwt import (
    create_access_token,
    create_refresh_token,
    verify_token,
    refresh_access_token,
    JWTError
)
from api.models.token import TokenData
from api.config import settings


class TestJWTUtils:
    """Test suite for JWT utility functions."""

    def test_create_access_token_success(self):
        """Test creating access token works correctly."""
        email = "test@example.com"
        token = create_access_token(email)

        # Verify token structure
        assert isinstance(token, str)
        assert len(token) > 50

        # Decode and verify content
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        assert payload["sub"] == email
        assert payload["token_type"] == "access"
        assert "exp" in payload

    def test_create_access_token_custom_expiry(self):
        """Test creating access token with custom expiry."""
        email = "test@example.com"
        expires_delta = timedelta(minutes=30)
        token = create_access_token(email, expires_delta)

        # Decode and verify expiry
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        exp_timestamp = payload["exp"]
        exp_datetime = datetime.fromtimestamp(exp_timestamp, timezone.utc)
        now = datetime.now(timezone.utc)

        # Should expire in approximately 30 minutes
        time_diff = exp_datetime - now
        assert 29 <= time_diff.total_seconds() / 60 <= 31

    def test_create_access_token_empty_email_raises_error(self):
        """Test that empty email raises ValueError."""
        with pytest.raises(ValueError, match="Email cannot be empty"):
            create_access_token("")

        with pytest.raises(ValueError, match="Email cannot be empty"):
            create_access_token(None)

    def test_create_refresh_token_success(self):
        """Test creating refresh token works correctly."""
        email = "test@example.com"
        token = create_refresh_token(email)

        # Verify token structure
        assert isinstance(token, str)
        assert len(token) > 50

        # Decode and verify content
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        assert payload["sub"] == email
        assert payload["token_type"] == "refresh"
        assert "exp" in payload

    def test_verify_token_access_success(self):
        """Test verifying valid access token."""
        email = "test@example.com"
        token = create_access_token(email)

        token_data = verify_token(token, expected_type="access")

        assert isinstance(token_data, TokenData)
        assert token_data.email == email
        assert token_data.token_type == "access"

    def test_verify_token_refresh_success(self):
        """Test verifying valid refresh token."""
        email = "test@example.com"
        token = create_refresh_token(email)

        token_data = verify_token(token, expected_type="refresh")

        assert isinstance(token_data, TokenData)
        assert token_data.email == email
        assert token_data.token_type == "refresh"

    def test_verify_token_wrong_type_raises_error(self):
        """Test that wrong token type raises JWTError."""
        email = "test@example.com"
        access_token = create_access_token(email)

        with pytest.raises(JWTError, match="Token type mismatch"):
            verify_token(access_token, expected_type="refresh")

    def test_verify_token_invalid_token_raises_error(self):
        """Test that invalid token raises JWTError."""
        with pytest.raises(JWTError, match="Invalid token"):
            verify_token("invalid.token.here", expected_type="access")

    def test_verify_token_empty_token_raises_error(self):
        """Test that empty token raises ValueError."""
        with pytest.raises(ValueError, match="Token cannot be empty"):
            verify_token("", expected_type="access")

        with pytest.raises(ValueError, match="Token cannot be empty"):
            verify_token(None, expected_type="access")

    def test_verify_token_expired_raises_error(self):
        """Test that expired token raises JWTError."""
        email = "test@example.com"

        # Create token that expires immediately
        with patch('api.utils.jwt.datetime') as mock_datetime:
            # Mock current time
            now = datetime.now(timezone.utc)
            mock_datetime.now.return_value = now
            mock_datetime.fromtimestamp = datetime.fromtimestamp

            # Create token with past expiry
            past_time = now - timedelta(hours=1)
            expires_delta = timedelta(seconds=-3600)  # Negative delta = past expiry
            token = create_access_token(email, expires_delta)

            # Try to verify the expired token
            with pytest.raises(JWTError, match="Token has expired"):
                verify_token(token, expected_type="access")

    def test_refresh_access_token_success(self):
        """Test refreshing access token with valid refresh token."""
        email = "test@example.com"
        refresh_token = create_refresh_token(email)

        new_access_token = refresh_access_token(refresh_token)

        # Verify the new access token
        token_data = verify_token(new_access_token, expected_type="access")
        assert token_data.email == email
        assert token_data.token_type == "access"

    def test_refresh_access_token_invalid_refresh_raises_error(self):
        """Test that invalid refresh token raises JWTError."""
        with pytest.raises(JWTError):
            refresh_access_token("invalid.refresh.token")

    def test_refresh_access_token_access_token_raises_error(self):
        """Test that using access token for refresh raises JWTError."""
        email = "test@example.com"
        access_token = create_access_token(email)

        with pytest.raises(JWTError, match="Token type mismatch"):
            refresh_access_token(access_token)

    def test_token_payload_missing_email_raises_error(self):
        """Test that token without email raises JWTError."""
        # Create malformed token without 'sub' (email) claim
        payload = {
            "token_type": "access",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=15)
        }
        malformed_token = jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

        with pytest.raises(JWTError, match="Token missing email"):
            verify_token(malformed_token, expected_type="access")