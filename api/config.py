"""
Configuration settings for the API.

Environment-based configuration management for JWT secrets, token expiry, and app settings.
"""

import os
from typing import Optional


class Config:
    """
    Application configuration loaded from environment variables.
    """

    # JWT Configuration
    JWT_SECRET: str = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

    # Password Configuration
    BCRYPT_ROUNDS: int = int(os.getenv("BCRYPT_ROUNDS", "12"))

    # API Configuration
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"

    # CORS Configuration
    CORS_ORIGINS: list = os.getenv("CORS_ORIGINS", "*").split(",")
    CORS_ALLOW_CREDENTIALS: bool = os.getenv("CORS_ALLOW_CREDENTIALS", "True").lower() == "true"
    CORS_ALLOW_METHODS: list = os.getenv("CORS_ALLOW_METHODS", "GET,POST,PUT,DELETE").split(",")
    CORS_ALLOW_HEADERS: list = os.getenv("CORS_ALLOW_HEADERS", "*").split(",")

    @classmethod
    def validate_config(cls) -> None:
        """
        Validate configuration settings and raise warnings for insecure defaults.
        """
        if cls.JWT_SECRET == "your-secret-key-change-in-production":
            print("WARNING: Using default JWT secret key. Set JWT_SECRET environment variable in production!")

        if cls.BCRYPT_ROUNDS < 12:
            print(f"WARNING: Bcrypt rounds ({cls.BCRYPT_ROUNDS}) is below recommended minimum of 12!")

        if cls.DEBUG:
            print("WARNING: Debug mode is enabled. Disable in production!")


# Create global config instance
config = Config()

# Validate configuration on import
config.validate_config()