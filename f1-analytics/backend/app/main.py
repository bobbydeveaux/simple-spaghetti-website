"""
Main FastAPI application for F1 Prediction Analytics.

This module initializes the FastAPI application, configures middleware,
and sets up the basic API structure for the F1 analytics system.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import app_config
from app.database import create_tables

# Import all models to ensure they are registered
from app.models import *  # noqa: F401, F403


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    app = FastAPI(
        title=app_config.APP_NAME,
        description="Formula 1 Prediction Analytics API - Advanced ML-powered race predictions",
        version=app_config.APP_VERSION,
        docs_url="/docs" if app_config.DEBUG else None,
        redoc_url="/redoc" if app_config.DEBUG else None,
    )

    # Configure CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=app_config.CORS_ORIGINS if not app_config.DEBUG else ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    return app


# Create application instance
app = create_app()


@app.on_event("startup")
async def startup_event():
    """Application startup event handler."""
    # Create database tables on startup (for development)
    if app_config.DEBUG:
        create_tables()


@app.get("/")
async def root():
    """Root endpoint with basic API information."""
    return {
        "message": "F1 Prediction Analytics API",
        "version": app_config.APP_VERSION,
        "status": "operational",
        "docs_url": "/docs" if app_config.DEBUG else None,
    }


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    import datetime
    return {
        "status": "healthy",
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "version": app_config.APP_VERSION,
    }


# Note: Additional route modules will be added in future sprints:
# - Authentication routes (/api/v1/auth)
# - Race data routes (/api/v1/races)
# - Prediction routes (/api/v1/predictions)
# - Analytics routes (/api/v1/analytics)
# - Export routes (/api/v1/export)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=app_config.DEBUG,
        log_level="debug" if app_config.DEBUG else "info",
    )