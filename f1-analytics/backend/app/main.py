"""
F1 Analytics Backend API
FastAPI application entry point with health checks and basic routing.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import logging
from typing import Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI application
app = FastAPI(
    title="F1 Analytics API",
    description="Formula One Prediction Analytics Backend",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://frontend:3000",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


@app.get("/")
async def root() -> Dict[str, Any]:
    """Root endpoint with API information."""
    return {
        "message": "F1 Analytics API",
        "version": "1.0.0",
        "description": "Formula One Prediction Analytics Backend",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """Health check endpoint for container orchestration."""
    try:
        # Here you would typically check:
        # - Database connectivity
        # - Redis connectivity
        # - External API availability
        # For now, return a simple health status

        return {
            "status": "healthy",
            "service": "f1-analytics-backend",
            "version": "1.0.0",
            "timestamp": "2026-02-12T00:00:00Z",
            "checks": {
                "api": "ok",
                "database": "ok",  # TODO: Add actual DB check
                "redis": "ok",     # TODO: Add actual Redis check
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unhealthy")


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
        "environment": "development"
    }


# Placeholder routes for F1 Analytics features
# These would be implemented in separate route modules

@app.get("/api/v1/predictions/next-race")
async def get_next_race_predictions():
    """Get predictions for the next scheduled race."""
    # Placeholder implementation
    return {
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


@app.get("/api/v1/races/calendar")
async def get_race_calendar():
    """Get the race calendar for the current season."""
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


if __name__ == "__main__":
    # This is for development only
    # In production, use uvicorn command from Dockerfile
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )