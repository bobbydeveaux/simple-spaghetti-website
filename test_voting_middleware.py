"""Tests for voting authentication middleware."""

import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException
from datetime import datetime, timedelta
import jwt

from api.voting.middleware import (
    verify_voting_session,
    verify_admin_session,
    validate_token_direct,
    SessionNotFoundError,
    SessionExpiredError,
    VotingAuthenticationError
)
from api.voting.models import Session
from api.utils.jwt_manager import jwt_manager


class TestVotingMiddleware:
    """Test cases for voting authentication middleware."""

    def setup_method(self):
        """Set up test data."""
        self.valid_token = jwt_manager.create_access_token("voter@example.com")
        self.mock_session = Session(
            session_id="test-session-id",
            voter_id="test-voter-id",
            token=self.valid_token,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=2),
            is_admin=False
        )

    @patch('api.voting.middleware.validate_session')
    def test_verify_voting_session_success(self, mock_validate):
        """Test successful session verification."""
        mock_validate.return_value = self.mock_session

        result = verify_voting_session(f"Bearer {self.valid_token}")

        assert result == self.mock_session
        mock_validate.assert_called_once_with(self.valid_token)

    def test_verify_voting_session_missing_header(self):
        """Test missing authorization header."""
        with pytest.raises(HTTPException) as exc_info:
            verify_voting_session(None)

        assert exc_info.value.status_code == 401
        assert "Authorization header required" in exc_info.value.detail

    def test_verify_voting_session_invalid_format(self):
        """Test invalid authorization header format."""
        with pytest.raises(HTTPException) as exc_info:
            verify_voting_session("Invalid header")

        assert exc_info.value.status_code == 401
        assert "Invalid authorization header format" in exc_info.value.detail

    def test_verify_voting_session_empty_token(self):
        """Test empty token after Bearer prefix."""
        with pytest.raises(HTTPException) as exc_info:
            verify_voting_session("Bearer ")

        assert exc_info.value.status_code == 401
        assert "Token is required" in exc_info.value.detail

    @patch('api.voting.middleware.validate_session')
    def test_verify_voting_session_not_found(self, mock_validate):
        """Test session not found error."""
        mock_validate.side_effect = SessionNotFoundError("Session not found")

        with pytest.raises(HTTPException) as exc_info:
            verify_voting_session(f"Bearer {self.valid_token}")

        assert exc_info.value.status_code == 401
        assert "Session not found or invalid" in exc_info.value.detail

    @patch('api.voting.middleware.validate_session')
    def test_verify_voting_session_expired(self, mock_validate):
        """Test expired session error."""
        mock_validate.side_effect = SessionExpiredError("Session expired")

        with pytest.raises(HTTPException) as exc_info:
            verify_voting_session(f"Bearer {self.valid_token}")

        assert exc_info.value.status_code == 401
        assert "Session has expired" in exc_info.value.detail

    @patch('api.voting.middleware.validate_session')
    def test_verify_admin_session_success(self, mock_validate):
        """Test successful admin session verification."""
        admin_session = Session(
            session_id="test-admin-session",
            voter_id="test-admin-voter",
            token=self.valid_token,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=2),
            is_admin=True
        )
        mock_validate.return_value = admin_session

        result = verify_admin_session(f"Bearer {self.valid_token}")

        assert result == admin_session
        assert result.is_admin is True

    @patch('api.voting.middleware.validate_session')
    def test_verify_admin_session_not_admin(self, mock_validate):
        """Test non-admin user trying to access admin endpoint."""
        mock_validate.return_value = self.mock_session  # is_admin=False

        with pytest.raises(HTTPException) as exc_info:
            verify_admin_session(f"Bearer {self.valid_token}")

        assert exc_info.value.status_code == 403
        assert "Admin privileges required" in exc_info.value.detail

    @patch('api.voting.middleware.validate_session')
    def test_validate_token_direct(self, mock_validate):
        """Test direct token validation function."""
        mock_validate.return_value = self.mock_session

        result = validate_token_direct(self.valid_token)

        assert result == self.mock_session
        mock_validate.assert_called_once_with(self.valid_token)

    def test_placeholder_validate_session_basic(self):
        """Test the placeholder validate_session function with basic JWT."""
        # This test verifies the placeholder implementation works
        from api.voting.middleware import validate_session_placeholder

        # Create a token with required payload structure
        payload = {
            "voter_id": "test-voter-123",
            "exp": (datetime.utcnow() + timedelta(hours=1)).timestamp(),
            "iat": datetime.utcnow().timestamp(),
            "is_admin": False
        }
        token = jwt.encode(payload, jwt_manager.secret_key, algorithm=jwt_manager.algorithm)

        session = validate_session_placeholder(token)

        assert session.voter_id == "test-voter-123"
        assert session.is_admin is False
        assert session.token == token

    def test_placeholder_validate_session_expired(self):
        """Test the placeholder function with expired token."""
        from api.voting.middleware import validate_session_placeholder

        # Create an expired token
        payload = {
            "voter_id": "test-voter-123",
            "exp": (datetime.utcnow() - timedelta(minutes=1)).timestamp(),  # Expired
            "iat": datetime.utcnow().timestamp(),
        }
        token = jwt.encode(payload, jwt_manager.secret_key, algorithm=jwt_manager.algorithm)

        with pytest.raises(SessionExpiredError):
            validate_session_placeholder(token)

    def test_placeholder_validate_session_invalid_token(self):
        """Test the placeholder function with invalid token."""
        from api.voting.middleware import validate_session_placeholder

        with pytest.raises(VotingAuthenticationError):
            validate_session_placeholder("invalid-token")


if __name__ == "__main__":
    pytest.main([__file__])