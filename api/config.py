"""
Configuration settings for the Python Auth API.
"""
import os
from typing import Optional

class Settings:
    """Application configuration settings."""

    # JWT Settings
    JWT_SECRET: str = os.getenv("JWT_SECRET", "your-super-secret-jwt-key-change-in-production")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # App Settings
    API_VERSION: str = "v1"
    APP_NAME: str = "Python Auth API"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

settings = Settings()