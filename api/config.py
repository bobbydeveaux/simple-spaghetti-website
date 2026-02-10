"""Configuration settings for the authentication API."""

import os
from typing import Optional


class Settings:
    """Application configuration settings."""

    # JWT Configuration
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "dev_secret_key_change_in_production")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

    # Password Hashing Configuration
    BCRYPT_ROUNDS: int = int(os.getenv("BCRYPT_ROUNDS", "12"))

    # API Configuration
    API_TITLE: str = "Python Authentication API"
    API_VERSION: str = "1.0.0"
    API_DESCRIPTION: str = "FastAPI-based authentication service with JWT tokens"

    # CORS Configuration
    ALLOWED_ORIGINS: list = [
        "http://localhost:3000",  # React development server
        "http://localhost:5173",  # Vite development server
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]

    # Development/Debug Settings
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")

    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.ENVIRONMENT.lower() == "production"

    def validate_config(self) -> None:
        """Validate configuration settings and warn about insecure defaults."""
        if self.is_production() and self.JWT_SECRET_KEY == "dev_secret_key_change_in_production":
            raise ValueError(
                "JWT_SECRET_KEY must be set to a secure value in production. "
                "Use a long, random string."
            )

        if self.BCRYPT_ROUNDS < 10:
            print("WARNING: BCRYPT_ROUNDS is set to less than 10. "
                  "Consider using 12 or higher for better security.")

        if self.ACCESS_TOKEN_EXPIRE_MINUTES > 60:
            print("WARNING: ACCESS_TOKEN_EXPIRE_MINUTES is set to more than 60 minutes. "
                  "Consider using shorter expiration times for better security.")


# Global settings instance
settings = Settings()

# Validate configuration on import
settings.validate_config()