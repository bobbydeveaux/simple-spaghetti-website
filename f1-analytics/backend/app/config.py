"""
F1 Prediction Analytics Configuration Module

This module contains configuration settings for the F1 prediction analytics backend.
It handles database connection, environment variables, and application settings.
"""

import os
from typing import Optional


class Settings:
    """Application configuration settings"""

    # Database Configuration
    DATABASE_URL: str = os.getenv(
        "F1_DATABASE_URL",
        "postgresql://f1_user:f1_password@localhost:5432/f1_analytics"
    )

    # Database Connection Pool Settings
    DATABASE_POOL_SIZE: int = int(os.getenv("DATABASE_POOL_SIZE", "10"))
    DATABASE_MAX_OVERFLOW: int = int(os.getenv("DATABASE_MAX_OVERFLOW", "20"))
    DATABASE_POOL_TIMEOUT: int = int(os.getenv("DATABASE_POOL_TIMEOUT", "30"))
    DATABASE_POOL_RECYCLE: int = int(os.getenv("DATABASE_POOL_RECYCLE", "3600"))

    # Application Environment
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = os.getenv("DEBUG", "True").lower() == "true"

    # Testing Configuration
    TEST_DATABASE_URL: Optional[str] = os.getenv("TEST_DATABASE_URL")

    @property
    def is_production(self) -> bool:
        """Check if running in production environment"""
        return self.ENVIRONMENT.lower() == "production"

    @property
    def is_testing(self) -> bool:
        """Check if running in test environment"""
        return self.ENVIRONMENT.lower() == "test"

    @property
    def database_url(self) -> str:
        """Get appropriate database URL based on environment"""
        if self.is_testing and self.TEST_DATABASE_URL:
            return self.TEST_DATABASE_URL
        return self.DATABASE_URL


# Global settings instance
settings = Settings()