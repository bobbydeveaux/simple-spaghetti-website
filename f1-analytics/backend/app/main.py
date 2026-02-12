"""
F1 Analytics Backend FastAPI Application.

Main entry point for the F1 prediction analytics API server.
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
        title="F1 Analytics API",
        description="Formula One prediction analytics and data platform",
        version="1.0.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=app_config.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    return app


# Create application instance
app = create_app()


@app.get("/")
async def root():
    """Root endpoint for health check."""
    return {
        "message": "F1 Analytics API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True if app_config.DEBUG else False,
        log_level="debug" if app_config.DEBUG else "info",
    )