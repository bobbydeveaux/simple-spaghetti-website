"""
Database and application configuration management.
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
    DB_USER: str = "postgres"
    DB_PASSWORD: str = "password"

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