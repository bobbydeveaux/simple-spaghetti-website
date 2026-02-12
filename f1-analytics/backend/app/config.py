"""
Configuration management for F1 Prediction Analytics.

This module provides centralized configuration management for the F1 analytics backend,
including database connection settings, JWT configuration, and external API settings.
"""

import os
from functools import lru_cache
from typing import Optional, List

try:
    from pydantic_settings import BaseSettings
    from pydantic import Field, validator
except ImportError:
    # Fallback for older Pydantic versions
    from pydantic import BaseSettings, Field, validator


class DatabaseConfig(BaseSettings):
    """Database configuration settings."""

    # PostgreSQL connection settings
    db_host: str = Field(default="localhost", env="F1_DB_HOST")
    db_port: int = Field(default=5432, env="F1_DB_PORT")
    db_name: str = Field(default="f1_analytics", env="F1_DB_NAME")
    db_user: str = Field(default="f1_user", env="F1_DB_USER")
    db_password: str = Field(default="f1_password", env="F1_DB_PASSWORD")

    # Connection pool settings
    pool_size: int = Field(default=20, env="F1_DB_POOL_SIZE")
    max_overflow: int = Field(default=10, env="F1_DB_MAX_OVERFLOW")
    pool_timeout: int = Field(default=30, env="F1_DB_POOL_TIMEOUT")
    pool_recycle: int = Field(default=3600, env="F1_DB_POOL_RECYCLE")  # 1 hour

    # SSL and connection settings
    ssl_mode: str = Field(default="prefer", env="F1_DB_SSL_MODE")
    echo_sql: bool = Field(default=False, env="F1_DB_ECHO_SQL")

    @property
    def database_url(self) -> str:
        """Generate the complete database URL."""
        return (
            f"postgresql://{self.db_user}:{self.db_password}@"
            f"{self.db_host}:{self.db_port}/{self.db_name}"
        )

    @property
    def async_database_url(self) -> str:
        """Generate the async database URL."""
        return (
            f"postgresql+asyncpg://{self.db_user}:{self.db_password}@"
            f"{self.db_host}:{self.db_port}/{self.db_name}"
        )

    # Backward compatibility properties
    @property
    def DATABASE_URL(self) -> str:
        """Backward compatibility property for main branch."""
        return self.database_url

    class Config:
        env_file = ".env"
        case_sensitive = False


class RedisConfig(BaseSettings):
    """Redis configuration for caching and session management."""

    redis_host: str = Field(default="localhost", env="F1_REDIS_HOST")
    redis_port: int = Field(default=6379, env="F1_REDIS_PORT")
    redis_password: Optional[str] = Field(default=None, env="F1_REDIS_PASSWORD")
    redis_db: int = Field(default=0, env="F1_REDIS_DB")

    # Connection pool settings
    redis_max_connections: int = Field(default=50, env="F1_REDIS_MAX_CONNECTIONS")
    redis_retry_on_timeout: bool = Field(default=True, env="F1_REDIS_RETRY_ON_TIMEOUT")
    redis_socket_timeout: int = Field(default=5, env="F1_REDIS_SOCKET_TIMEOUT")

    # Cache TTL settings (in seconds)
    prediction_cache_ttl: int = Field(default=604800, env="F1_PREDICTION_CACHE_TTL")  # 7 days
    race_calendar_ttl: int = Field(default=86400, env="F1_RACE_CALENDAR_TTL")  # 24 hours
    driver_rankings_ttl: int = Field(default=3600, env="F1_DRIVER_RANKINGS_TTL")  # 1 hour

    @property
    def redis_url(self) -> str:
        """Generate the complete Redis URL."""
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    class Config:
        env_file = ".env"
        case_sensitive = False


class JWTConfig(BaseSettings):
    """JWT configuration for authentication."""

    secret_key: str = Field(default="f1-analytics-dev-secret-key-change-in-production", env="F1_JWT_SECRET_KEY")
    algorithm: str = Field(default="HS256", env="F1_JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(default=15, env="F1_JWT_ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(default=7, env="F1_JWT_REFRESH_TOKEN_EXPIRE_DAYS")

    @validator("secret_key")
    def validate_secret_key(cls, v):
        if v == "f1-analytics-dev-secret-key-change-in-production":
            import warnings
            warnings.warn(
                "Using default JWT secret key! Change F1_JWT_SECRET_KEY in production!",
                UserWarning,
                stacklevel=2
            )
        return v

    class Config:
        env_file = ".env"
        case_sensitive = False


class ExternalAPIConfig(BaseSettings):
    """Configuration for external APIs."""

    # Ergast API settings
    ergast_base_url: str = Field(default="https://ergast.com/api/f1", env="F1_ERGAST_BASE_URL")
    ergast_timeout: int = Field(default=30, env="F1_ERGAST_TIMEOUT")
    ergast_retry_attempts: int = Field(default=3, env="F1_ERGAST_RETRY_ATTEMPTS")

    # Weather API settings (OpenWeatherMap)
    weather_api_key: Optional[str] = Field(default=None, env="F1_WEATHER_API_KEY")
    weather_base_url: str = Field(default="https://api.openweathermap.org/data/2.5", env="F1_WEATHER_BASE_URL")

    class Config:
        env_file = ".env"
        case_sensitive = False


class MLConfig(BaseSettings):
    """Machine Learning configuration."""

    # Model settings
    model_bucket: str = Field(default="f1-analytics-models", env="F1_MODEL_BUCKET")
    model_path_prefix: str = Field(default="models", env="F1_MODEL_PATH_PREFIX")
    model_version: str = Field(default="v1", env="F1_MODEL_VERSION")

    # Training settings
    random_forest_n_estimators: int = Field(default=100, env="F1_RF_N_ESTIMATORS")
    random_forest_max_depth: int = Field(default=10, env="F1_RF_MAX_DEPTH")
    xgboost_learning_rate: float = Field(default=0.1, env="F1_XGB_LEARNING_RATE")
    xgboost_n_estimators: int = Field(default=200, env="F1_XGB_N_ESTIMATORS")
    xgboost_max_depth: int = Field(default=6, env="F1_XGB_MAX_DEPTH")

    # ELO settings
    elo_k_factor: int = Field(default=32, env="F1_ELO_K_FACTOR")
    elo_base_rating: int = Field(default=1500, env="F1_ELO_BASE_RATING")

    # Feature engineering
    historical_races_lookback: int = Field(default=5, env="F1_HISTORICAL_RACES_LOOKBACK")

    class Config:
        env_file = ".env"
        case_sensitive = False


class AppConfig(BaseSettings):
    """Main application configuration."""

    app_name: str = Field(default="F1 Prediction Analytics", env="F1_APP_NAME")
    app_version: str = Field(default="1.0.0", env="F1_APP_VERSION")
    environment: str = Field(default="development", env="F1_ENVIRONMENT")
    debug: bool = Field(default=True, env="F1_DEBUG")

    # API settings
    api_v1_prefix: str = Field(default="/api/v1", env="F1_API_V1_PREFIX")
    allowed_hosts: List[str] = Field(default=["*"], env="F1_ALLOWED_HOSTS")
    cors_origins: List[str] = Field(
        default=[
            "http://localhost:3000",
            "http://localhost:5173",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5173"
        ],
        env="F1_CORS_ORIGINS"
    )

    # Rate limiting
    rate_limit_requests: int = Field(default=100, env="F1_RATE_LIMIT_REQUESTS")
    rate_limit_window: int = Field(default=60, env="F1_RATE_LIMIT_WINDOW")  # seconds

    # Logging
    log_level: str = Field(default="INFO", env="F1_LOG_LEVEL")
    log_format: str = Field(default="json", env="F1_LOG_FORMAT")  # json or text

    @validator("environment")
    def validate_environment(cls, v):
        allowed = ["development", "staging", "production"]
        if v not in allowed:
            raise ValueError(f"Environment must be one of {allowed}")
        return v

    @validator("allowed_hosts", "cors_origins", pre=True)
    def split_string_list(cls, v):
        if isinstance(v, str):
            return [item.strip() for item in v.split(",")]
        return v

    @property
    def is_development(self) -> bool:
        return self.environment == "development"

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    class Config:
        env_file = ".env"
        case_sensitive = False


class Settings:
    """Central settings management."""

    def __init__(self):
        self.app = AppConfig()
        self.database = DatabaseConfig()
        self.redis = RedisConfig()
        self.jwt = JWTConfig()
        self.external_apis = ExternalAPIConfig()
        self.ml = MLConfig()

    def validate_config(self) -> None:
        """Validate configuration and warn about insecure defaults."""
        if self.app.is_production:
            if self.jwt.secret_key == "f1-analytics-dev-secret-key-change-in-production":
                raise ValueError("JWT secret key must be changed in production!")

            if self.database.db_password == "f1_password":
                raise ValueError("Database password must be changed in production!")

            if self.app.debug:
                import warnings
                warnings.warn(
                    "Debug mode is enabled in production! Set F1_DEBUG=false",
                    UserWarning
                )

    def log_config_summary(self) -> None:
        """Log non-sensitive configuration summary."""
        import logging
        logger = logging.getLogger(__name__)

        logger.info(f"F1 Analytics Configuration Summary:")
        logger.info(f"  Environment: {self.app.environment}")
        logger.info(f"  Database Host: {self.database.db_host}:{self.database.db_port}")
        logger.info(f"  Redis Host: {self.redis.redis_host}:{self.redis.redis_port}")
        logger.info(f"  Debug Mode: {self.app.debug}")
        logger.info(f"  API Prefix: {self.app.api_v1_prefix}")


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    settings = Settings()
    settings.validate_config()
    return settings


# Global settings instance
settings = get_settings()

# Backward compatibility exports for main branch
db_config = settings.database
app_config = settings.app
ml_config = settings.ml