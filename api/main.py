"""Main FastAPI application for Python Authentication API."""

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging

from api.config import settings
from api.routes import auth, protected
from api.voting import routes as voting_routes

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    description=settings.API_DESCRIPTION,
    debug=settings.DEBUG
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(protected.router)
app.include_router(voting_routes.router)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """
    Custom HTTP exception handler for consistent error responses.
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "status_code": exc.status_code,
                "detail": exc.detail,
                "path": str(request.url)
            }
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """
    Global exception handler for unexpected errors.
    """
    logger.error(f"Unexpected error on {request.method} {request.url}: {exc}", exc_info=True)

    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "status_code": 500,
                "detail": "Internal server error",
                "path": str(request.url)
            }
        }
    )


@app.get("/")
async def root():
    """
    Root endpoint with API information.
    """
    return {
        "message": "Python Authentication API",
        "version": settings.API_VERSION,
        "environment": settings.ENVIRONMENT,
        "docs": "/docs",
        "endpoints": {
            "register": "/auth/register",
            "login": "/auth/login",
            "refresh": "/auth/refresh",
            "protected": "/protected/",
            "voting": "/voting/"
        }
    }


@app.get("/health")
async def health_check():
    """
    Health check endpoint for monitoring.
    """
    return {
        "status": "healthy",
        "environment": settings.ENVIRONMENT,
        "version": settings.API_VERSION
    }


if __name__ == "__main__":
    import uvicorn

    # Run the application
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info" if not settings.DEBUG else "debug"
    )