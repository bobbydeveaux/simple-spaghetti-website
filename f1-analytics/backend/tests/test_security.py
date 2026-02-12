"""
Tests for security module functionality.
"""
import pytest
import os
from unittest.mock import patch, Mock
from fastapi import HTTPException
from app.core.security import (
    validate_jwt_secret,
    generate_secure_secret,
    verify_password,
    get_password_hash,
    create_access_token,
    verify_token,
    validate_environment_security
)


class TestJWTSecretValidation:
    """Test JWT secret validation functionality."""

    def test_validate_jwt_secret_missing(self):
        """Test validation when JWT secret is missing."""
        with patch.dict(os.environ, {"JWT_SECRET_KEY": ""}):
            with pytest.raises(HTTPException) as exc_info:
                validate_jwt_secret()

            assert exc_info.value.status_code == 500
            assert "not configured" in exc_info.value.detail

    def test_validate_jwt_secret_weak_patterns(self):
        """Test validation rejects weak secret patterns."""
        weak_secrets = [
            "dev-secret-key",
            "change-in-production",
            "dev_jwt_key",
            "secret",
            "key",
            "development",
            "<generate_with_openssl_rand_base64_64>",
            "generate_secure_jwt_secret_minimum_64_characters",
            "GENERATE_WITH_OPENSSL_RAND_BASE64_64_MINIMUM_64_CHARACTERS_REQUIRED_FOR_SECURITY",
            "minimum_64_characters_required",
            "please_generate_secure_secret",
            "openssl_rand_base64_64"
        ]

        for weak_secret in weak_secrets:
            with patch.dict(os.environ, {"JWT_SECRET_KEY": weak_secret}):
                with pytest.raises(HTTPException) as exc_info:
                    validate_jwt_secret()

                assert exc_info.value.status_code == 500
                assert "template/development value" in exc_info.value.detail

    def test_validate_jwt_secret_too_short(self):
        """Test validation rejects short secrets."""
        with patch.dict(os.environ, {"JWT_SECRET_KEY": "short"}):
            with pytest.raises(HTTPException) as exc_info:
                validate_jwt_secret()

            assert exc_info.value.status_code == 500
            assert "too short" in exc_info.value.detail

    def test_validate_jwt_secret_low_entropy(self):
        """Test validation rejects low entropy secrets."""
        with patch.dict(os.environ, {"JWT_SECRET_KEY": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"}):
            with pytest.raises(HTTPException) as exc_info:
                validate_jwt_secret()

            assert exc_info.value.status_code == 500
            assert "insufficient entropy" in exc_info.value.detail

    def test_validate_jwt_secret_strong(self):
        """Test validation passes for strong secrets."""
        strong_secret = "v8K9xB2nF6yU4mZ3qW7tR5eA1sD4gH9jK6xN2bM8vC5z"
        with patch.dict(os.environ, {"JWT_SECRET_KEY": strong_secret}):
            # Should not raise any exception
            validate_jwt_secret()


class TestPasswordHashing:
    """Test password hashing functionality."""

    def test_password_hashing_and_verification(self):
        """Test password hashing and verification."""
        password = "test_password_123"
        hashed = get_password_hash(password)

        assert hashed != password
        assert verify_password(password, hashed) is True
        assert verify_password("wrong_password", hashed) is False

    def test_password_hash_different_each_time(self):
        """Test that password hashing produces different results each time."""
        password = "test_password_123"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)

        assert hash1 != hash2
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True


class TestJWTTokens:
    """Test JWT token creation and verification."""

    def setup_method(self):
        """Set up test environment."""
        self.strong_secret = "v8K9xB2nF6yU4mZ3qW7tR5eA1sD4gH9jK6xN2bM8vC5z"
        self.test_data = {"sub": "test_user", "user_id": 123}

    def test_create_and_verify_token_success(self):
        """Test successful token creation and verification."""
        with patch.dict(os.environ, {"JWT_SECRET_KEY": self.strong_secret}):
            # Create token
            token = create_access_token(self.test_data)
            assert isinstance(token, str)
            assert len(token) > 0

            # Verify token
            payload = verify_token(token)
            assert payload["sub"] == self.test_data["sub"]
            assert payload["user_id"] == self.test_data["user_id"]
            assert "exp" in payload  # Expiration should be added

    def test_create_token_with_weak_secret(self):
        """Test token creation fails with weak secret."""
        with patch.dict(os.environ, {"JWT_SECRET_KEY": "weak"}):
            with pytest.raises(HTTPException) as exc_info:
                create_access_token(self.test_data)

            assert exc_info.value.status_code == 500

    def test_verify_invalid_token(self):
        """Test verification of invalid token."""
        with patch.dict(os.environ, {"JWT_SECRET_KEY": self.strong_secret}):
            with pytest.raises(HTTPException) as exc_info:
                verify_token("invalid_token")

            assert exc_info.value.status_code == 401
            assert "Could not validate credentials" in exc_info.value.detail

    def test_verify_token_with_weak_secret(self):
        """Test token verification fails with weak secret."""
        with patch.dict(os.environ, {"JWT_SECRET_KEY": "weak"}):
            with pytest.raises(HTTPException) as exc_info:
                verify_token("any_token")

            assert exc_info.value.status_code == 500


class TestSecureSecretGeneration:
    """Test secure secret generation."""

    def test_generate_secure_secret_default_length(self):
        """Test secure secret generation with default length."""
        secret = generate_secure_secret()
        assert len(secret) >= 64
        assert secret.isalnum() or '_' in secret or '-' in secret

    def test_generate_secure_secret_custom_length(self):
        """Test secure secret generation with custom length."""
        secret = generate_secure_secret(32)
        assert len(secret) >= 32

    def test_generate_secure_secret_uniqueness(self):
        """Test that generated secrets are unique."""
        secret1 = generate_secure_secret(32)
        secret2 = generate_secure_secret(32)
        assert secret1 != secret2


class TestEnvironmentSecurityValidation:
    """Test environment security validation."""

    def test_validate_environment_security_clean(self):
        """Test security validation with clean environment."""
        env_vars = {
            "JWT_SECRET_KEY": "v8K9xB2nF6yU4mZ3qW7tR5eA1sD4gH9jK6xN2bM8vC5z",
            "ENVIRONMENT": "test",
            "DEBUG": "false",
            "DATABASE_URL": "postgresql://user:secure_password@localhost/db",
            "REDIS_URL": "redis://:secure_password@localhost:6379"
        }

        with patch.dict(os.environ, env_vars):
            results = validate_environment_security()

            assert results["jwt_secret_secure"] is True
            assert results["environment"] == "test"
            assert results["debug_enabled"] is False
            assert len(results["issues"]) == 0

    def test_validate_environment_security_jwt_issues(self):
        """Test security validation with JWT issues."""
        env_vars = {
            "JWT_SECRET_KEY": "weak",
            "ENVIRONMENT": "production",
            "DEBUG": "false"
        }

        with patch.dict(os.environ, env_vars):
            results = validate_environment_security()

            assert results["jwt_secret_secure"] is False
            assert len(results["issues"]) > 0
            assert any("JWT" in issue for issue in results["issues"])

    def test_validate_environment_security_debug_in_production(self):
        """Test security validation with debug enabled in production."""
        env_vars = {
            "JWT_SECRET_KEY": "v8K9xB2nF6yU4mZ3qW7tR5eA1sD4gH9jK6xN2bM8vC5z",
            "ENVIRONMENT": "production",
            "DEBUG": "true"
        }

        with patch.dict(os.environ, env_vars):
            results = validate_environment_security()

            assert results["debug_enabled"] is True
            assert any("Debug mode" in issue for issue in results["issues"])

    def test_validate_environment_security_weak_credentials(self):
        """Test security validation detects weak credentials."""
        env_vars = {
            "JWT_SECRET_KEY": "v8K9xB2nF6yU4mZ3qW7tR5eA1sD4gH9jK6xN2bM8vC5z",
            "ENVIRONMENT": "test",
            "DEBUG": "false",
            "DATABASE_URL": "postgresql://user:f1password@localhost/db",
            "REDIS_URL": "redis://:f1redis@localhost:6379"
        }

        with patch.dict(os.environ, env_vars):
            results = validate_environment_security()

            assert len(results["issues"]) >= 2
            assert any("Database" in issue for issue in results["issues"])
            assert any("Redis" in issue for issue in results["issues"])

    def test_validate_environment_security_template_credentials(self):
        """Test security validation detects template placeholder credentials."""
        env_vars = {
            "JWT_SECRET_KEY": "v8K9xB2nF6yU4mZ3qW7tR5eA1sD4gH9jK6xN2bM8vC5z",
            "ENVIRONMENT": "test",
            "DEBUG": "false",
            "DATABASE_URL": "postgresql://user:<generate_secure_24_char_password>@localhost/db",
            "REDIS_URL": "redis://:<generate_production_redis_password>@localhost:6379"
        }

        with patch.dict(os.environ, env_vars):
            results = validate_environment_security()

            assert len(results["issues"]) >= 2
            assert any("Database" in issue and "generate_" in issue for issue in results["issues"])
            assert any("Redis" in issue and "generate_" in issue for issue in results["issues"])

    def test_validate_environment_security_production_placeholders(self):
        """Test security validation detects production template placeholders."""
        env_vars = {
            "JWT_SECRET_KEY": "v8K9xB2nF6yU4mZ3qW7tR5eA1sD4gH9jK6xN2bM8vC5z",
            "ENVIRONMENT": "test",
            "DEBUG": "false",
            "DATABASE_URL": "postgresql://user:use_a_very_strong_production_password_here@localhost/db",
            "REDIS_URL": "redis://:use_a_very_strong_redis_password_here@localhost:6379"
        }

        with patch.dict(os.environ, env_vars):
            results = validate_environment_security()

            assert len(results["issues"]) >= 2
            assert any("Database" in issue and "use_a_very_strong" in issue for issue in results["issues"])
            assert any("Redis" in issue and "use_a_very_strong" in issue for issue in results["issues"])