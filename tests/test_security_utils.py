"""
Tests for security utilities (JWT manager and password hasher).
"""

import os
import time
from datetime import datetime, timezone

import pytest

from api.utils.jwt_manager import JWTManager, JWTError
from api.utils.password import PasswordHasher, PasswordError


class TestJWTManager:
    """Test cases for JWT token management."""

    def setup_method(self):
        """Set up test instance."""
        # Use a test secret key
        os.environ["JWT_SECRET"] = "test-secret-key-for-testing"
        os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "15"
        os.environ["REFRESH_TOKEN_EXPIRE_DAYS"] = "7"
        self.jwt_manager = JWTManager()

    def teardown_method(self):
        """Clean up environment variables."""
        for key in ["JWT_SECRET", "ACCESS_TOKEN_EXPIRE_MINUTES", "REFRESH_TOKEN_EXPIRE_DAYS"]:
            if key in os.environ:
                del os.environ[key]

    def test_create_access_token(self):
        """Test access token creation."""
        email = "test@example.com"
        token = self.jwt_manager.create_access_token(email)

        assert isinstance(token, str)
        assert len(token) > 0

        # Verify token can be decoded
        payload = self.jwt_manager.decode_token(token)
        assert payload["sub"] == email
        assert payload["type"] == "access"

    def test_create_refresh_token(self):
        """Test refresh token creation."""
        email = "test@example.com"
        token = self.jwt_manager.create_refresh_token(email)

        assert isinstance(token, str)
        assert len(token) > 0

        # Verify token can be decoded
        payload = self.jwt_manager.decode_token(token)
        assert payload["sub"] == email
        assert payload["type"] == "refresh"

    def test_decode_valid_token(self):
        """Test decoding a valid token."""
        email = "test@example.com"
        token = self.jwt_manager.create_access_token(email)

        payload = self.jwt_manager.decode_token(token)

        assert payload["sub"] == email
        assert payload["type"] == "access"
        assert "exp" in payload
        assert "iat" in payload

    def test_decode_invalid_token(self):
        """Test decoding an invalid token raises JWTError."""
        with pytest.raises(JWTError, match="Invalid token"):
            self.jwt_manager.decode_token("invalid.token.here")

    def test_verify_token_type(self):
        """Test token type verification."""
        email = "test@example.com"
        access_token = self.jwt_manager.create_access_token(email)
        refresh_token = self.jwt_manager.create_refresh_token(email)

        access_payload = self.jwt_manager.decode_token(access_token)
        refresh_payload = self.jwt_manager.decode_token(refresh_token)

        assert self.jwt_manager.verify_token_type(access_payload, "access") is True
        assert self.jwt_manager.verify_token_type(access_payload, "refresh") is False
        assert self.jwt_manager.verify_token_type(refresh_payload, "refresh") is True
        assert self.jwt_manager.verify_token_type(refresh_payload, "access") is False

    def test_get_email_from_token(self):
        """Test extracting email from token."""
        email = "test@example.com"
        token = self.jwt_manager.create_access_token(email)

        extracted_email = self.jwt_manager.get_email_from_token(token)
        assert extracted_email == email

    def test_get_email_from_invalid_token(self):
        """Test extracting email from invalid token returns None."""
        email = self.jwt_manager.get_email_from_token("invalid.token.here")
        assert email is None


class TestPasswordHasher:
    """Test cases for password hashing and verification."""

    def setup_method(self):
        """Set up test instance."""
        # Use faster rounds for testing
        os.environ["BCRYPT_ROUNDS"] = "4"
        self.password_hasher = PasswordHasher()

    def teardown_method(self):
        """Clean up environment variables."""
        if "BCRYPT_ROUNDS" in os.environ:
            del os.environ["BCRYPT_ROUNDS"]

    def test_hash_password(self):
        """Test password hashing."""
        password = "test_password_123"
        hashed = self.password_hasher.hash_password(password)

        assert isinstance(hashed, str)
        assert len(hashed) > 0
        assert hashed != password  # Hash should be different from plain password
        assert hashed.startswith("$2b$")  # bcrypt hash prefix

    def test_hash_empty_password(self):
        """Test hashing empty password raises ValueError."""
        with pytest.raises(ValueError, match="Password cannot be empty"):
            self.password_hasher.hash_password("")

        with pytest.raises(ValueError, match="Password cannot be empty"):
            self.password_hasher.hash_password(None)

    def test_verify_correct_password(self):
        """Test verifying correct password."""
        password = "test_password_123"
        hashed = self.password_hasher.hash_password(password)

        assert self.password_hasher.verify_password(password, hashed) is True

    def test_verify_incorrect_password(self):
        """Test verifying incorrect password."""
        password = "test_password_123"
        wrong_password = "wrong_password"
        hashed = self.password_hasher.hash_password(password)

        assert self.password_hasher.verify_password(wrong_password, hashed) is False

    def test_verify_empty_parameters(self):
        """Test verifying with empty parameters raises ValueError."""
        with pytest.raises(ValueError, match="Password and hash cannot be empty"):
            self.password_hasher.verify_password("", "hash")

        with pytest.raises(ValueError, match="Password and hash cannot be empty"):
            self.password_hasher.verify_password("password", "")

        with pytest.raises(ValueError, match="Password and hash cannot be empty"):
            self.password_hasher.verify_password(None, "hash")

    def test_verify_invalid_hash_format(self):
        """Test verifying with invalid hash format returns False."""
        result = self.password_hasher.verify_password("password", "invalid_hash")
        assert result is False

    def test_needs_update(self):
        """Test checking if password needs update."""
        password = "test_password_123"
        hashed = self.password_hasher.hash_password(password)

        # Fresh hash should not need update
        assert self.password_hasher.needs_update(hashed) is False

    def test_convenience_functions(self):
        """Test convenience functions work correctly."""
        from api.utils.password import hash_password, verify_password

        password = "test_password_123"
        hashed = hash_password(password)

        assert verify_password(password, hashed) is True
        assert verify_password("wrong", hashed) is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])