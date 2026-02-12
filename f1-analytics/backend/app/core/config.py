"""
Configuration management for F1 Analytics application.
Handles environment-specific settings and security configurations.
"""
import os
import secrets
from typing import List, Optional, Union
from pydantic import BaseSettings, validator
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings with validation."""

    # Application
    app_name: str = "F1 Analytics API"
    version: str = "1.0.0"
    environment: str = "development"
    debug: bool = False
    log_level: str = "INFO"

    # Security
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440
    cors_origins: List[str] = ["http://localhost:3000"]
    allowed_hosts: List[str] = ["localhost", "127.0.0.1"]

    # Database
    database_url: str
    database_pool_size: int = 5
    database_max_overflow: int = 10

    # Redis
    redis_url: str
    redis_max_connections: int = 20

    # External APIs
    ergast_api_url: str = "https://ergast.com/api/f1"
    weather_api_key: Optional[str] = None
    weather_api_url: str = "https://api.openweathermap.org/data/2.5"

    # Rate limiting
    rate_limit_per_minute: int = 60
    rate_limit_burst: int = 120

    # Monitoring
    enable_metrics: bool = True
    metrics_port: int = 9090

    class Config:
        env_file = ".env"
        case_sensitive = False

        # Environment variable mappings
        fields = {
            'secret_key': {'env': 'JWT_SECRET_KEY'},
            'algorithm': {'env': 'JWT_ALGORITHM'},
            'access_token_expire_minutes': {'env': 'JWT_EXPIRE_MINUTES'},
            'cors_origins': {'env': 'CORS_ORIGINS'},
            'allowed_hosts': {'env': 'ALLOWED_HOSTS'},
        }

    @validator('cors_origins', pre=True)
    def parse_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(',')]
        return v

    @validator('allowed_hosts', pre=True)
    def parse_allowed_hosts(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            return [host.strip() for host in v.split(',')]
        return v

    @validator('secret_key')
    def validate_secret_key(cls, v: str, values: dict) -> str:
        if not v:
            raise ValueError('JWT_SECRET_KEY is required')

        # Check for development/weak secrets
        weak_patterns = ['dev', 'secret', 'key', 'test', 'change']
        if values.get('environment') == 'production':
            if any(pattern in v.lower() for pattern in weak_patterns):
                raise ValueError(
                    'JWT_SECRET_KEY appears to be a development value. '
                    'Use a cryptographically secure secret in production.'
                )

            if len(v) < 32:
                raise ValueError(
                    'JWT_SECRET_KEY must be at least 32 characters in production'
                )

        return v

    @validator('debug')
    def validate_debug(cls, v: bool, values: dict) -> bool:
        if values.get('environment') == 'production' and v:
            raise ValueError('Debug mode cannot be enabled in production')
        return v

    @validator('cors_origins')
    def validate_cors_origins(cls, v: List[str], values: dict) -> List[str]:
        if values.get('environment') == 'production':
            # Ensure production doesn't allow localhost or wildcard origins
            forbidden_origins = ['http://localhost', 'http://127.0.0.1', '*']
            for origin in v:
                if any(forbidden in origin for forbidden in forbidden_origins):
                    raise ValueError(
                        f'CORS origin {origin} is not allowed in production. '
                        'Use specific domain names only.'
                    )
        return v

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == 'production'

    @property
    def is_development(self) -> bool:
        return self.environment.lower() == 'development'


class SecurityConfig:
    """Security configuration constants and validators."""

    # HTTPS settings
    REQUIRE_HTTPS_PRODUCTION = True
    SECURE_HEADERS = {
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
        'X-XSS-Protection': '1; mode=block',
        'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
        'Referrer-Policy': 'strict-origin-when-cross-origin',
    }

    # Rate limiting
    DEFAULT_RATE_LIMITS = {
        '/api/v1/predictions': '30/minute',
        '/api/v1/drivers': '60/minute',
        '/api/v1/races': '60/minute',
        '/health': '300/minute'
    }

    # Content Security Policy
    CSP_POLICY = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:; "
        "font-src 'self' https://fonts.gstatic.com; "
        "connect-src 'self' https://ergast.com https://api.openweathermap.org; "
        "frame-ancestors 'none';"
    )

    @staticmethod
    def get_security_headers(environment: str) -> dict:
        """Get security headers based on environment."""
        headers = SecurityConfig.SECURE_HEADERS.copy()

        if environment == 'production':
            headers['Content-Security-Policy'] = SecurityConfig.CSP_POLICY
        else:
            # More relaxed CSP for development
            headers['Content-Security-Policy'] = (
                "default-src 'self' 'unsafe-inline' 'unsafe-eval' http: https: data: blob:; "
                "frame-ancestors 'self';"
            )

        return headers


@lru_cache()
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()


def generate_production_secret() -> str:
    """Generate a cryptographically secure secret for production."""
    return secrets.token_urlsafe(64)


def validate_production_config(settings: Settings) -> List[str]:
    """Validate production configuration and return any issues."""
    issues = []

    if settings.environment == 'production':
        # Check database URL
        if 'localhost' in settings.database_url or '127.0.0.1' in settings.database_url:
            issues.append("Database URL should not use localhost in production")

        # Check Redis URL
        if 'localhost' in settings.redis_url or '127.0.0.1' in settings.redis_url:
            issues.append("Redis URL should not use localhost in production")

        # Check API keys
        if not settings.weather_api_key or 'your_' in settings.weather_api_key:
            issues.append("Weather API key is not configured for production")

        # Check CORS origins
        if any('localhost' in origin for origin in settings.cors_origins):
            issues.append("CORS origins should not include localhost in production")

    return issues