"""
Configuration module for F1 Prediction Analytics application.

This module defines application configuration including database settings,
environment variables, and other configuration parameters needed for the
F1 analytics system.
"""

import os
from typing import Optional


class Settings:
    """Application configuration settings."""

    # Database settings
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://f1_user:f1_password@localhost:5432/f1_analytics"
    )

    # Database connection pool settings
    DATABASE_POOL_SIZE: int = int(os.getenv("DATABASE_POOL_SIZE", "20"))
    DATABASE_MAX_OVERFLOW: int = int(os.getenv("DATABASE_MAX_OVERFLOW", "10"))

    # Redis cache settings
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # Security settings
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-here-change-in-production")
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 24

    # External API settings
    ERGAST_API_BASE_URL: str = "http://ergast.com/api/f1"
    WEATHER_API_KEY: Optional[str] = os.getenv("WEATHER_API_KEY")
    WEATHER_API_BASE_URL: str = "https://api.openweathermap.org/data/2.5"

    # Model storage settings
    MODEL_STORAGE_BUCKET: str = os.getenv("MODEL_STORAGE_BUCKET", "f1-models")
    MODEL_STORAGE_PREFIX: str = "models"

    # Application settings
    APP_NAME: str = "F1 Prediction Analytics"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"

    # Rate limiting settings
    RATE_LIMIT_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "100"))

    # Cache TTL settings (in seconds)
    PREDICTION_CACHE_TTL: int = int(os.getenv("PREDICTION_CACHE_TTL", "604800"))  # 7 days
    RACE_CALENDAR_CACHE_TTL: int = int(os.getenv("RACE_CALENDAR_CACHE_TTL", "86400"))  # 24 hours
    DRIVER_RANKINGS_CACHE_TTL: int = int(os.getenv("DRIVER_RANKINGS_CACHE_TTL", "3600"))  # 1 hour


# Global settings instance
settings = Settings()