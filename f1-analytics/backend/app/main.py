"""
F1 Analytics Backend API - Main FastAPI application.

This module combines comprehensive security features with clean database modeling
for Formula 1 prediction analytics. It includes health checks, middleware setup,
Prometheus metrics collection, and basic API routing with placeholder endpoints
for future development.
"""

import os
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import logging
from typing import Dict, Any
from datetime import datetime
import psycopg2
import redis

# Import database setup
from app.config import app_config
from app.database import create_tables

# Import all models to ensure they are registered
from app.models import *  # noqa: F401, F403

# Import Prometheus metrics
from app.monitoring import (
    instrument_fastapi_app,
    PrometheusMiddleware,
    get_metrics_summary,
    initialize_metrics,
    track_prediction_generated,
    track_ml_inference,
    track_cache_operation,
    update_race_data_freshness,
    update_driver_elo_rating
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import security validation (if available)
try:
    from core.security import validate_environment_security
    from core.exceptions import configure_exception_handlers, DatabaseConnectionError, RedisConnectionError
    from core.middleware import setup_middleware
    from core.config import get_settings
    SECURITY_MODULE_AVAILABLE = True
except ImportError:
    SECURITY_MODULE_AVAILABLE = False
    logger.warning("Security module not available - using basic configuration")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown events."""
    # Startup
    logger.info("Starting F1 Analytics Backend API...")

    # Initialize Prometheus metrics
    initialize_metrics()
    logger.info("Prometheus metrics initialized")

    # Create database tables on startup (for development)
    if app_config.DEBUG:
        create_tables()

    # Validate security configuration on startup (if available)
    if SECURITY_MODULE_AVAILABLE:
        security_results = validate_environment_security()
        if security_results["issues"]:
            for issue in security_results["issues"]:
                logger.error(f"Security Issue: {issue}")
            if os.getenv("ENVIRONMENT") == "production":
                logger.critical("Security issues detected in production environment!")
        else:
            logger.info("Security validation passed")

    yield

    # Shutdown
    logger.info("Shutting down F1 Analytics Backend API...")

# Create FastAPI application
app = FastAPI(
    title="F1 Analytics API",
    description="Formula 1 Prediction Analytics API - Advanced ML-powered race predictions with enterprise security",
    version="1.0.0",
    docs_url="/docs" if app_config.DEBUG else None,
    redoc_url="/redoc" if app_config.DEBUG else None,
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# Configure exception handlers and middleware if security module available
if SECURITY_MODULE_AVAILABLE:
    configure_exception_handlers(app)
    settings = get_settings()
    setup_middleware(app, settings)
    cors_origins = settings.cors_origins
else:
    cors_origins = app_config.CORS_ORIGINS if not app_config.DEBUG else ["*"]

# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "Origin", "X-Requested-With"],
)

# Add Prometheus metrics middleware
app.add_middleware(
    PrometheusMiddleware,
    app_name="f1-analytics-api",
    skip_paths=["/metrics", "/health", "/docs", "/redoc", "/openapi.json"]
)

# Instrument the FastAPI app for Prometheus
instrument_fastapi_app(app)


@app.get("/")
async def root() -> Dict[str, Any]:
    """Root endpoint with API information."""
    return {
        "message": "F1 Analytics API",
        "version": "1.0.0",
        "description": "Formula One Prediction Analytics Backend",
        "docs": "/docs" if app_config.DEBUG else None,
        "health": "/health",
        "status": "operational"
    }


async def check_database_connectivity() -> bool:
    """Check PostgreSQL database connectivity."""
    try:
        database_url = os.getenv("DATABASE_URL") or str(app_config.DATABASE_URL)
        if not database_url:
            logger.warning("DATABASE_URL not configured")
            return False

        # Parse connection details from URL
        import urllib.parse
        parsed = urllib.parse.urlparse(database_url)

        conn = psycopg2.connect(
            host=parsed.hostname,
            port=parsed.port or 5432,
            database=parsed.path.lstrip('/'),
            user=parsed.username,
            password=parsed.password,
            connect_timeout=5
        )

        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        cursor.close()
        conn.close()

        return True
    except psycopg2.OperationalError as e:
        logger.error(f"Database operational error: {e}")
        return False
    except psycopg2.Error as e:
        logger.error(f"Database error: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected database connectivity error: {e}")
        return False


async def check_redis_connectivity() -> bool:
    """Check Redis connectivity."""
    try:
        redis_url = os.getenv("REDIS_URL")
        if not redis_url:
            logger.warning("REDIS_URL not configured")
            return False

        # Parse Redis URL
        import urllib.parse
        parsed = urllib.parse.urlparse(redis_url)

        r = redis.Redis(
            host=parsed.hostname,
            port=parsed.port or 6379,
            password=parsed.password,
            socket_timeout=5,
            socket_connect_timeout=5
        )

        r.ping()
        return True
    except redis.ConnectionError as e:
        logger.error(f"Redis connection error: {e}")
        return False
    except redis.TimeoutError as e:
        logger.error(f"Redis timeout error: {e}")
        return False
    except redis.RedisError as e:
        logger.error(f"Redis error: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected Redis connectivity error: {e}")
        return False


@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    Comprehensive health check endpoint for container orchestration.
    Verifies actual connectivity to dependent services.
    """
    timestamp = datetime.utcnow().isoformat() + "Z"
    health_status = "healthy"
    checks = {}

    try:
        # Check API service (always healthy if we reach this point)
        checks["api"] = "ok"

        # Check database connectivity
        db_healthy = await check_database_connectivity()
        checks["database"] = "ok" if db_healthy else "error"
        if not db_healthy:
            health_status = "unhealthy"

        # Check Redis connectivity
        redis_healthy = await check_redis_connectivity()
        checks["redis"] = "ok" if redis_healthy else "error"
        if not redis_healthy:
            health_status = "unhealthy"

        # Check security configuration (if available)
        if SECURITY_MODULE_AVAILABLE:
            security_results = validate_environment_security()
            checks["security"] = "ok" if not security_results["issues"] else "warning"
            if security_results["issues"]:
                checks["security_issues"] = security_results["issues"]
                if os.getenv("ENVIRONMENT") == "production":
                    health_status = "unhealthy"

        # Check Prometheus metrics
        metrics_summary = get_metrics_summary()
        checks["metrics"] = "ok" if metrics_summary.get("metrics_enabled", False) else "warning"
        if not metrics_summary.get("metrics_enabled", False):
            checks["metrics_error"] = metrics_summary.get("error", "Unknown metrics error")

        response = {
            "status": health_status,
            "service": "f1-analytics-backend",
            "version": "1.0.0",
            "timestamp": timestamp,
            "environment": os.getenv("ENVIRONMENT", "development"),
            "checks": checks
        }

        if health_status == "unhealthy":
            # Return 503 Service Unavailable if any critical checks fail
            return JSONResponse(
                status_code=503,
                content=response
            )

        return response

    except Exception as e:
        logger.error(f"Health check failed with exception: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "service": "f1-analytics-backend",
                "version": "1.0.0",
                "timestamp": timestamp,
                "error": str(e),
                "checks": {"api": "error"}
            }
        )


@app.get("/api/v1/info")
async def api_info() -> Dict[str, Any]:
    """API information endpoint."""
    return {
        "api_version": "v1",
        "features": [
            "predictions",
            "race_calendar",
            "driver_rankings",
            "analytics",
            "authentication",
            "data_export"
        ],
        "status": "active",
        "environment": os.getenv("ENVIRONMENT", "development")
    }


# Placeholder routes for F1 Analytics features
# These will be moved to separate route modules in future sprints

@app.get("/api/v1/predictions/next-race")
async def get_next_race_predictions():
    """Get predictions for the next scheduled race."""
    # Track prediction generation metrics
    try:
        # Simulate ML inference tracking
        with track_ml_inference("random_forest", "race_prediction"):
            # Simulate some processing time
            import asyncio
            await asyncio.sleep(0.1)

        # Track successful prediction generation
        track_prediction_generated(
            model_type="random_forest",
            race_type="grand_prix",
            success=True
        )

        # Check cache for data (simulate cache miss for demo)
        track_cache_operation(
            operation="get",
            cache_type="race_predictions",
            status="miss"
        )

        # Placeholder implementation
        predictions_data = {
            "race_id": 1,
            "race_name": "Monaco Grand Prix 2026",
            "race_date": "2026-05-24",
            "circuit": "Circuit de Monaco",
            "predictions": [
                {
                    "driver_id": 1,
                    "driver_name": "Max Verstappen",
                    "driver_code": "VER",
                    "team": "Red Bull Racing",
                    "win_probability": 35.2,
                    "team_color": "#0600EF"
                },
                {
                    "driver_id": 2,
                    "driver_name": "Charles Leclerc",
                    "driver_code": "LEC",
                    "team": "Ferrari",
                    "win_probability": 28.7,
                    "team_color": "#DC143C"
                },
                {
                    "driver_id": 3,
                    "driver_name": "Lewis Hamilton",
                    "driver_code": "HAM",
                    "team": "Mercedes",
                    "win_probability": 22.1,
                    "team_color": "#00D2BE"
                }
            ],
            "model_version": "v1.0.0",
            "generated_at": "2026-02-12T10:00:00Z"
        }

        # Update cache with new data (simulate cache set)
        track_cache_operation(
            operation="set",
            cache_type="race_predictions",
            status="success"
        )

        return predictions_data

    except Exception as e:
        # Track failed prediction generation
        track_prediction_generated(
            model_type="random_forest",
            race_type="grand_prix",
            success=False
        )
        logger.error(f"Failed to generate predictions: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate predictions")


@app.get("/api/v1/races/calendar")
async def get_race_calendar():
    """Get the race calendar for the current season."""
    # Check cache for race calendar
    track_cache_operation(
        operation="get",
        cache_type="race_calendar",
        status="hit"  # Simulate cache hit
    )

    # Update race data freshness metrics (simulate data age)
    update_race_data_freshness("race_calendar", 300.0)  # 5 minutes old

    return {
        "season": 2026,
        "races": [
            {
                "race_id": 1,
                "round": 1,
                "race_name": "Bahrain Grand Prix",
                "circuit": "Bahrain International Circuit",
                "date": "2026-03-01",
                "status": "completed"
            },
            {
                "race_id": 2,
                "round": 2,
                "race_name": "Monaco Grand Prix",
                "circuit": "Circuit de Monaco",
                "date": "2026-05-24",
                "status": "scheduled"
            }
        ]
    }


@app.get("/api/v1/drivers/rankings")
async def get_driver_rankings():
    """Get current driver ELO rankings."""
    # Check cache for driver rankings
    track_cache_operation(
        operation="get",
        cache_type="driver_rankings",
        status="hit"  # Simulate cache hit
    )

    # Update driver ELO ratings in metrics
    update_driver_elo_rating("Max Verstappen", "VER", "Red Bull Racing", 2150.0)
    update_driver_elo_rating("Charles Leclerc", "LEC", "Ferrari", 1980.0)

    # Update race data freshness for driver standings
    update_race_data_freshness("driver_standings", 1800.0)  # 30 minutes old

    return {
        "season": 2026,
        "rankings": [
            {
                "position": 1,
                "driver_name": "Max Verstappen",
                "team": "Red Bull Racing",
                "elo_rating": 2150,
                "wins": 15,
                "points": 395
            },
            {
                "position": 2,
                "driver_name": "Charles Leclerc",
                "team": "Ferrari",
                "elo_rating": 1980,
                "wins": 8,
                "points": 308
            }
        ]
    }


# Note: Additional route modules will be added in future sprints:
# - Authentication routes (/api/v1/auth)
# - Race data routes (/api/v1/races)
# - Prediction routes (/api/v1/predictions)
# - Analytics routes (/api/v1/analytics)
# - Export routes (/api/v1/export)

if __name__ == "__main__":
    # This is for development only
    # In production, use uvicorn command from Dockerfile
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=app_config.DEBUG,
        log_level="debug" if app_config.DEBUG else "info",
    )