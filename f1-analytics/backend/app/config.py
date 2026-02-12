"""
Configuration module for F1 Prediction Analytics application.

This module defines application configuration including database settings,
environment variables, and other configuration parameters needed for the
F1 analytics system.
"""

import os
from typing import Optional

try:
    from pydantic_settings import BaseSettings
except ImportError:
    # Fallback for older Pydantic versions
    from pydantic import BaseSettings


class DatabaseConfig(BaseSettings):
    """Database configuration settings."""

    # Database connection settings
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "f1_analytics"
    DB_USER: str = "f1_user"  # Use consistent user from main branch
    DB_PASSWORD: str = "f1_password"  # Use consistent password from main branch

    # Connection pool settings
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30

    # SQLAlchemy settings
    DB_ECHO: bool = False  # Set to True for SQL query logging

    class Config:
        env_file = ".env"
        case_sensitive = True

    @property
    def database_url(self) -> str:
        """Construct PostgreSQL database URL."""
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @property
    def async_database_url(self) -> str:
        """Construct async PostgreSQL database URL."""
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"


class AppConfig(BaseSettings):
    """Application configuration settings."""

    # Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Application metadata
    APP_NAME: str = "F1 Prediction Analytics"
    APP_VERSION: str = "1.0.0"

    # Security
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    JWT_SECRET_KEY: str = "jwt-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRY_HOURS: int = 24

    # Redis configuration
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None

    # API settings
    API_V1_PREFIX: str = "/api/v1"
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    # Rate limiting
    RATE_LIMIT_PER_MINUTE: int = 100

    # External API settings
    ERGAST_API_BASE_URL: str = "http://ergast.com/api/f1"
    WEATHER_API_KEY: Optional[str] = None
    WEATHER_API_BASE_URL: str = "https://api.openweathermap.org/data/2.5"

    # Cache TTL settings (in seconds)
    PREDICTION_CACHE_TTL: int = 604800  # 7 days
    RACE_CALENDAR_CACHE_TTL: int = 86400  # 24 hours
    DRIVER_RANKINGS_CACHE_TTL: int = 3600  # 1 hour

    class Config:
        env_file = ".env"
        case_sensitive = True

    @property
    def redis_url(self) -> str:
        """Construct Redis URL."""
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"


class MLConfig(BaseSettings):
    """Machine Learning configuration settings."""

    # Model settings
    MODEL_VERSION: str = "v1"
    ELO_K_FACTOR: int = 32
    ELO_BASE_RATING: int = 1500

    # Model storage settings
    MODEL_STORAGE_BUCKET: str = "f1-models"
    MODEL_STORAGE_PREFIX: str = "models"

    # Training settings
    RANDOM_FOREST_N_ESTIMATORS: int = 100
    XGBOOST_MAX_DEPTH: int = 6
    XGBOOST_LEARNING_RATE: float = 0.1

    # Feature engineering
    HISTORICAL_RACES_LOOKBACK: int = 5  # Number of races to look back for driver performance

    class Config:
        env_file = ".env"
        case_sensitive = True


# Global configuration instances
db_config = DatabaseConfig()
app_config = AppConfig()
ml_config = MLConfig()

# For backward compatibility with main branch naming
settings = app_config
