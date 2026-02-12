"""
Custom exception handlers and error responses for F1 Analytics API.
"""
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging
from typing import Union
import traceback

logger = logging.getLogger(__name__)


class F1AnalyticsException(Exception):
    """Base exception for F1 Analytics application."""

    def __init__(self, message: str, status_code: int = 500, details: dict = None):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class DatabaseConnectionError(F1AnalyticsException):
    """Exception raised when database connection fails."""

    def __init__(self, message: str = "Database connection failed", details: dict = None):
        super().__init__(message, status_code=503, details=details)


class RedisConnectionError(F1AnalyticsException):
    """Exception raised when Redis connection fails."""

    def __init__(self, message: str = "Redis connection failed", details: dict = None):
        super().__init__(message, status_code=503, details=details)


class ExternalAPIError(F1AnalyticsException):
    """Exception raised when external API calls fail."""

    def __init__(self, message: str = "External API call failed", details: dict = None):
        super().__init__(message, status_code=502, details=details)


class PredictionModelError(F1AnalyticsException):
    """Exception raised when prediction model fails."""

    def __init__(self, message: str = "Prediction model error", details: dict = None):
        super().__init__(message, status_code=500, details=details)


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors with detailed error messages."""
    logger.warning(f"Validation error for {request.url}: {exc.errors()}")

    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "type": "validation_error",
                "message": "Request validation failed",
                "details": exc.errors(),
                "url": str(request.url),
                "method": request.method
            }
        }
    )


async def http_exception_handler(request: Request, exc: Union[HTTPException, StarletteHTTPException]):
    """Handle HTTP exceptions with consistent error format."""
    logger.warning(f"HTTP error {exc.status_code} for {request.url}: {exc.detail}")

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "type": "http_error",
                "status_code": exc.status_code,
                "message": exc.detail,
                "url": str(request.url),
                "method": request.method
            }
        }
    )


async def f1_analytics_exception_handler(request: Request, exc: F1AnalyticsException):
    """Handle custom F1 Analytics exceptions."""
    logger.error(f"F1 Analytics error {exc.status_code} for {request.url}: {exc.message}")

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "type": "f1_analytics_error",
                "status_code": exc.status_code,
                "message": exc.message,
                "details": exc.details,
                "url": str(request.url),
                "method": request.method
            }
        }
    )


async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions with proper logging."""
    logger.error(
        f"Unhandled exception for {request.url}: {str(exc)}\n{traceback.format_exc()}"
    )

    # Don't expose internal error details in production
    import os
    debug_mode = os.getenv("DEBUG", "false").lower() == "true"

    error_details = {
        "type": "internal_error",
        "status_code": 500,
        "message": "Internal server error occurred",
        "url": str(request.url),
        "method": request.method
    }

    if debug_mode:
        error_details["debug"] = {
            "exception_type": type(exc).__name__,
            "exception_message": str(exc),
            "traceback": traceback.format_exc().split("\n")
        }

    return JSONResponse(
        status_code=500,
        content={"error": error_details}
    )


def configure_exception_handlers(app):
    """Configure all exception handlers for the FastAPI app."""
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(F1AnalyticsException, f1_analytics_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)