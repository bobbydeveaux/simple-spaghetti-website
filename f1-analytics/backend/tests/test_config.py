"""
Tests for configuration module functionality.
"""
import pytest
import os
from unittest.mock import patch
from pydantic import ValidationError
from app.core.config import Settings, validate_production_config


class TestSettingsValidation:
    """Test settings validation functionality."""

    def test_settings_valid_development(self):
        """Test settings validation in development environment."""
        env_vars = {
            "JWT_SECRET_KEY": "v8K9xB2nF6yU4mZ3qW7tR5eA1sD4gH9jK6xN2bM8vC5z",
            "DATABASE_URL": "postgresql://user:password@localhost/db",
            "REDIS_URL": "redis://localhost:6379",
            "ENVIRONMENT": "development",
            "DEBUG": "true"
        }

        with patch.dict(os.environ, env_vars):
            settings = Settings()
            assert settings.environment == "development"
            assert settings.debug is True

    def test_settings_valid_production(self):
        """Test settings validation in production environment."""
        env_vars = {
            "JWT_SECRET_KEY": "v8K9xB2nF6yU4mZ3qW7tR5eA1sD4gH9jK6xN2bM8vC5z" + "extra_chars_for_production",
            "DATABASE_URL": "postgresql://user:secure_prod_password@db-server/db",
            "REDIS_URL": "redis://:secure_redis_pass@redis-server:6379",
            "ENVIRONMENT": "production",
            "DEBUG": "false",
            "CORS_ORIGINS": "https://example.com,https://www.example.com",
            "ALLOWED_HOSTS": "example.com,www.example.com"
        }

        with patch.dict(os.environ, env_vars):
            settings = Settings()
            assert settings.environment == "production"
            assert settings.debug is False
            assert "https://example.com" in settings.cors_origins

    def test_settings_weak_jwt_secret_development(self):
        """Test settings validation with weak JWT secret in development."""
        env_vars = {
            "JWT_SECRET_KEY": "dev-secret",  # Short but allowed in dev
            "DATABASE_URL": "postgresql://user:password@localhost/db",
            "REDIS_URL": "redis://localhost:6379",
            "ENVIRONMENT": "development"
        }

        with patch.dict(os.environ, env_vars):
            # Should raise validation error even in development for template patterns
            with pytest.raises(ValidationError) as exc_info:
                Settings()
            assert "template/development value" in str(exc_info.value)

    def test_settings_weak_jwt_secret_production(self):
        """Test settings validation rejects weak JWT secret in production."""
        env_vars = {
            "JWT_SECRET_KEY": "weak-secret-production",
            "DATABASE_URL": "postgresql://user:password@localhost/db",
            "REDIS_URL": "redis://localhost:6379",
            "ENVIRONMENT": "production",
            "DEBUG": "false"
        }

        with patch.dict(os.environ, env_vars):
            with pytest.raises(ValidationError) as exc_info:
                Settings()
            assert "template/development value" in str(exc_info.value)

    def test_settings_short_jwt_secret_production(self):
        """Test settings validation rejects short JWT secret in production."""
        env_vars = {
            "JWT_SECRET_KEY": "x1y2z3a4b5c6d7e8f9",  # Only 19 characters
            "DATABASE_URL": "postgresql://user:password@localhost/db",
            "REDIS_URL": "redis://localhost:6379",
            "ENVIRONMENT": "production",
            "DEBUG": "false"
        }

        with patch.dict(os.environ, env_vars):
            with pytest.raises(ValidationError) as exc_info:
                Settings()
            assert "at least 64 characters" in str(exc_info.value)

    def test_settings_debug_in_production(self):
        """Test settings validation rejects debug mode in production."""
        env_vars = {
            "JWT_SECRET_KEY": "v8K9xB2nF6yU4mZ3qW7tR5eA1sD4gH9jK6xN2bM8vC5z" + "extra_chars_for_production",
            "DATABASE_URL": "postgresql://user:password@localhost/db",
            "REDIS_URL": "redis://localhost:6379",
            "ENVIRONMENT": "production",
            "DEBUG": "true"
        }

        with patch.dict(os.environ, env_vars):
            with pytest.raises(ValidationError) as exc_info:
                Settings()
            assert "Debug mode cannot be enabled in production" in str(exc_info.value)

    def test_settings_localhost_cors_production(self):
        """Test settings validation rejects localhost CORS in production."""
        env_vars = {
            "JWT_SECRET_KEY": "v8K9xB2nF6yU4mZ3qW7tR5eA1sD4gH9jK6xN2bM8vC5z" + "extra_chars_for_production",
            "DATABASE_URL": "postgresql://user:password@db-server/db",
            "REDIS_URL": "redis://redis-server:6379",
            "ENVIRONMENT": "production",
            "DEBUG": "false",
            "CORS_ORIGINS": "http://localhost:3000,https://example.com"
        }

        with patch.dict(os.environ, env_vars):
            with pytest.raises(ValidationError) as exc_info:
                Settings()
            assert "not allowed in production" in str(exc_info.value)

    def test_settings_wildcard_cors_production(self):
        """Test settings validation rejects wildcard CORS in production."""
        env_vars = {
            "JWT_SECRET_KEY": "v8K9xB2nF6yU4mZ3qW7tR5eA1sD4gH9jK6xN2bM8vC5z" + "extra_chars_for_production",
            "DATABASE_URL": "postgresql://user:password@db-server/db",
            "REDIS_URL": "redis://redis-server:6379",
            "ENVIRONMENT": "production",
            "DEBUG": "false",
            "CORS_ORIGINS": "*,https://example.com"
        }

        with patch.dict(os.environ, env_vars):
            with pytest.raises(ValidationError) as exc_info:
                Settings()
            assert "not allowed in production" in str(exc_info.value)

    def test_settings_template_placeholders(self):
        """Test settings validation rejects template placeholders."""
        template_secrets = [
            "<generate_with_openssl_rand_base64_64>",
            "generate_secure_jwt_secret_minimum_64_characters",
            "<generate_secure_24_char_password>",
            "GENERATE_WITH_OPENSSL_RAND_BASE64_64_MINIMUM_64_CHARACTERS_REQUIRED_FOR_SECURITY"
        ]

        for template_secret in template_secrets:
            env_vars = {
                "JWT_SECRET_KEY": template_secret,
                "DATABASE_URL": "postgresql://user:password@localhost/db",
                "REDIS_URL": "redis://localhost:6379",
                "ENVIRONMENT": "development"
            }

            with patch.dict(os.environ, env_vars):
                with pytest.raises(ValidationError) as exc_info:
                    Settings()
                assert "template/development value" in str(exc_info.value)

    def test_settings_low_entropy_jwt_secret(self):
        """Test settings validation rejects low entropy JWT secrets."""
        low_entropy_secrets = [
            "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",  # Only 'a'
            "1111111111111111111111111111111111111111111111111111111111111111",  # Only '1'
            "abababababababababababababababababababababababababababababab",  # Only 'a' and 'b'
        ]

        for low_entropy_secret in low_entropy_secrets:
            env_vars = {
                "JWT_SECRET_KEY": low_entropy_secret,
                "DATABASE_URL": "postgresql://user:password@localhost/db",
                "REDIS_URL": "redis://localhost:6379",
                "ENVIRONMENT": "production",
                "DEBUG": "false"
            }

            with patch.dict(os.environ, env_vars):
                with pytest.raises(ValidationError) as exc_info:
                    Settings()
                assert "insufficient entropy" in str(exc_info.value)


class TestProductionConfigValidation:
    """Test production configuration validation."""

    def test_validate_production_config_clean(self):
        """Test production config validation with clean configuration."""
        settings = Settings(
            secret_key="v8K9xB2nF6yU4mZ3qW7tR5eA1sD4gH9jK6xN2bM8vC5z" + "extra_chars_for_production",
            environment="production",
            debug=False,
            database_url="postgresql://user:secure_password@db-server:5432/db",
            redis_url="redis://:secure_password@redis-server:6379/0",
            cors_origins=["https://example.com"],
            weather_api_key="real_api_key_here"
        )

        issues = validate_production_config(settings)
        assert len(issues) == 0

    def test_validate_production_config_localhost_issues(self):
        """Test production config validation detects localhost issues."""
        settings = Settings(
            secret_key="v8K9xB2nF6yU4mZ3qW7tR5eA1sD4gH9jK6xN2bM8vC5z" + "extra_chars_for_production",
            environment="production",
            debug=False,
            database_url="postgresql://user:password@localhost:5432/db",
            redis_url="redis://:password@127.0.0.1:6379/0",
            cors_origins=["http://localhost:3000"],
            weather_api_key="real_api_key_here"
        )

        issues = validate_production_config(settings)
        assert len(issues) >= 3
        assert any("Database URL should not use localhost" in issue for issue in issues)
        assert any("Redis URL should not use localhost" in issue for issue in issues)
        assert any("CORS origins should not include localhost" in issue for issue in issues)

    def test_validate_production_config_api_key_issues(self):
        """Test production config validation detects API key issues."""
        settings = Settings(
            secret_key="v8K9xB2nF6yU4mZ3qW7tR5eA1sD4gH9jK6xN2bM8vC5z" + "extra_chars_for_production",
            environment="production",
            debug=False,
            database_url="postgresql://user:password@db-server:5432/db",
            redis_url="redis://:password@redis-server:6379/0",
            cors_origins=["https://example.com"],
            weather_api_key="your_openweathermap_api_key_here"
        )

        issues = validate_production_config(settings)
        assert len(issues) >= 1
        assert any("Weather API key is not configured" in issue for issue in issues)

    def test_validate_production_config_development_environment(self):
        """Test production config validation passes for development."""
        settings = Settings(
            secret_key="short_key_ok_in_dev",
            environment="development",
            debug=True,
            database_url="postgresql://user:password@localhost:5432/db",
            redis_url="redis://:password@localhost:6379/0",
            cors_origins=["http://localhost:3000"],
            weather_api_key="test_key"
        )

        issues = validate_production_config(settings)
        assert len(issues) == 0  # No issues in development