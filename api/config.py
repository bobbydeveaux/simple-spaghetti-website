"""
Configuration settings for the Python Auth API.
"""
import os
from typing import Optional

class Settings:
    """Application configuration settings."""

    # JWT Settings
    JWT_SECRET: str = os.getenv("JWT_SECRET")

    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # App Settings
    API_VERSION: str = "v1"
    APP_NAME: str = "Python Auth API"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

    # CORS Settings
    ALLOWED_ORIGINS: list = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8080").split(",")

    def __post_init__(self):
        """Validate required environment variables."""
        if not self.JWT_SECRET:
            raise ValueError("JWT_SECRET environment variable is required and cannot be empty")

settings = Settings()
settings.__post_init__()