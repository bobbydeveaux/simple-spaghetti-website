"""
Main FastAPI application for F1 Prediction Analytics.

This module initializes the FastAPI application, configures middleware,
and sets up the basic API structure for the F1 analytics system.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import create_tables

# Create FastAPI application instance
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Formula 1 Prediction Analytics API - Advanced ML-powered race predictions",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.DEBUG else ["https://your-frontend-domain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Application startup event handler."""
    # Create database tables on startup (for development)
    if settings.DEBUG:
        create_tables()


@app.get("/")
async def root():
    """Root endpoint with basic API information."""
    return {
        "message": "F1 Prediction Analytics API",
        "version": settings.APP_VERSION,
        "status": "operational",
        "docs_url": "/docs" if settings.DEBUG else None,
    }


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {
        "status": "healthy",
        "timestamp": "2026-02-12T15:43:00Z",
        "version": settings.APP_VERSION,
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
        reload=settings.DEBUG,
        log_level="debug" if settings.DEBUG else "info",
    )