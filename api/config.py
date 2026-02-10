"""Configuration management for the FastAPI application."""

import os
from typing import Optional


class Config:
    """Application configuration loaded from environment variables."""

    def __init__(self):
        # JWT Configuration
        self.jwt_secret_key: str = os.getenv(
            "JWT_SECRET_KEY",
            "your-secret-key-change-this-in-production"
        )
        self.jwt_algorithm: str = "HS256"

        # Token expiry settings (in seconds)
        self.access_token_expire_minutes: int = int(
            os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15")
        )
        self.refresh_token_expire_days: int = int(
            os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7")
        )

        # Server configuration
        self.host: str = os.getenv("HOST", "0.0.0.0")
        self.port: int = int(os.getenv("PORT", "8000"))

        # CORS configuration
        self.cors_origins: list = os.getenv(
            "CORS_ORIGINS",
            "http://localhost:3000,http://localhost:5173"
        ).split(",")

        # Password hashing configuration
        self.password_hash_rounds: int = int(
            os.getenv("PASSWORD_HASH_ROUNDS", "12")
        )

    @property
    def access_token_expire_seconds(self) -> int:
        """Convert access token expiry from minutes to seconds."""
        return self.access_token_expire_minutes * 60

    @property
    def refresh_token_expire_seconds(self) -> int:
        """Convert refresh token expiry from days to seconds."""
        return self.refresh_token_expire_days * 24 * 60 * 60


# Global configuration instance
config = Config()