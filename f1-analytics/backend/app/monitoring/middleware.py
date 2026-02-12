"""
Prometheus Middleware for FastAPI

This middleware automatically tracks HTTP requests, response times, and other
application-level metrics for the F1 Analytics application.
"""

import time
import re
from typing import Callable, Optional
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import structlog

from .metrics import (
    http_requests_total,
    http_request_duration_seconds,
    f1_api_endpoint_usage_total
)

# Configure structured logging
logger = structlog.get_logger(__name__)

class PrometheusMiddleware(BaseHTTPMiddleware):
    """
    Middleware to automatically collect Prometheus metrics for FastAPI applications.

    This middleware tracks:
    - HTTP request count by method, endpoint, and status
    - HTTP request duration by method and endpoint
    - F1-specific API endpoint usage
    """

    def __init__(
        self,
        app,
        app_name: str = "f1-analytics-api",
        skip_paths: Optional[list] = None,
        normalize_path_patterns: Optional[dict] = None
    ):
        super().__init__(app)
        self.app_name = app_name
        self.skip_paths = skip_paths or ["/metrics", "/health"]

        # Default path normalization patterns for F1 API
        self.normalize_patterns = normalize_path_patterns or {
            r'/api/v\d+/drivers/\d+': '/api/v{version}/drivers/{id}',
            r'/api/v\d+/races/\d+': '/api/v{version}/races/{id}',
            r'/api/v\d+/teams/\d+': '/api/v{version}/teams/{id}',
            r'/api/v\d+/predictions/\d+': '/api/v{version}/predictions/{id}',
            r'/api/v\d+/seasons/\d+': '/api/v{version}/seasons/{id}',
            r'/api/v\d+/circuits/\d+': '/api/v{version}/circuits/{id}',
        }

        logger.info(
            "Prometheus middleware initialized",
            app_name=app_name,
            skip_paths=self.skip_paths
        )

    def _normalize_path(self, path: str) -> str:
        """
        Normalize URL paths to reduce cardinality in metrics.

        This replaces dynamic path segments (like IDs) with template variables
        to prevent metrics explosion while still maintaining useful grouping.

        Args:
            path: The original URL path

        Returns:
            Normalized path with dynamic segments replaced
        """
        normalized_path = path

        for pattern, replacement in self.normalize_patterns.items():
            normalized_path = re.sub(pattern, replacement, normalized_path)

        return normalized_path

    def _should_skip_path(self, path: str) -> bool:
        """Check if this path should be skipped for metrics collection."""
        return any(skip_path in path for skip_path in self.skip_paths)

    def _extract_user_type(self, request: Request) -> str:
        """
        Extract user type from request for F1-specific metrics.

        This can be enhanced based on authentication implementation.
        """
        # Default implementation - can be enhanced with actual auth logic
        auth_header = request.headers.get("authorization")
        if auth_header:
            return "authenticated"

        # Check for API key (if implemented)
        api_key = request.headers.get("x-api-key") or request.query_params.get("api_key")
        if api_key:
            return "api_user"

        return "anonymous"

    def _is_f1_api_endpoint(self, path: str) -> bool:
        """Check if this is an F1-specific API endpoint."""
        f1_endpoints = [
            "/api/v1/predictions",
            "/api/v1/drivers",
            "/api/v1/teams",
            "/api/v1/races",
            "/api/v1/seasons",
            "/api/v1/circuits",
            "/api/v1/analytics"
        ]
        return any(endpoint in path for endpoint in f1_endpoints)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process each HTTP request and collect metrics.

        Args:
            request: The incoming HTTP request
            call_next: The next middleware or route handler

        Returns:
            The HTTP response
        """
        # Skip metrics collection for certain paths
        if self._should_skip_path(request.url.path):
            return await call_next(request)

        # Record request start time
        start_time = time.time()

        # Normalize the path for consistent metrics
        normalized_path = self._normalize_path(request.url.path)

        # Extract request metadata
        method = request.method
        user_type = self._extract_user_type(request)

        # Process the request
        try:
            response = await call_next(request)
            status_code = response.status_code

        except Exception as e:
            # Handle exceptions and still record metrics
            logger.error(
                "Request processing failed",
                path=normalized_path,
                method=method,
                error=str(e)
            )
            status_code = 500
            # Re-raise the exception after logging
            raise

        finally:
            # Calculate request duration
            duration = time.time() - start_time

            # Record metrics
            self._record_metrics(
                method=method,
                path=normalized_path,
                status_code=status_code,
                duration=duration,
                user_type=user_type
            )

        return response

    def _record_metrics(
        self,
        method: str,
        path: str,
        status_code: int,
        duration: float,
        user_type: str
    ) -> None:
        """
        Record all relevant metrics for the request.

        Args:
            method: HTTP method
            path: Normalized URL path
            status_code: HTTP status code
            duration: Request duration in seconds
            user_type: Type of user making the request
        """
        try:
            # Status code category for better grouping
            status_category = f"{status_code // 100}xx"

            # Record HTTP request count
            http_requests_total.labels(
                method=method,
                endpoint=path,
                status=status_category
            ).inc()

            # Record HTTP request duration
            http_request_duration_seconds.labels(
                method=method,
                endpoint=path
            ).observe(duration)

            # Record F1-specific API usage if applicable
            if self._is_f1_api_endpoint(path):
                f1_api_endpoint_usage_total.labels(
                    endpoint=path,
                    user_type=user_type
                ).inc()

            # Log request details for debugging
            logger.debug(
                "HTTP request metrics recorded",
                method=method,
                path=path,
                status_code=status_code,
                duration=duration,
                user_type=user_type
            )

        except Exception as e:
            # Don't let metrics collection errors break the application
            logger.error(
                "Failed to record request metrics",
                method=method,
                path=path,
                error=str(e)
            )


class F1MetricsMiddleware(BaseHTTPMiddleware):
    """
    Additional middleware specifically for F1 analytics metrics.

    This middleware can be used to collect more specialized F1-specific
    metrics that require domain knowledge.
    """

    def __init__(self, app):
        super().__init__(app)
        logger.info("F1 Metrics middleware initialized")

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process requests for F1-specific metrics.

        This middleware can be extended to track:
        - Prediction request patterns
        - Popular driver/team queries
        - Race calendar access patterns
        - Analytics dashboard usage
        """
        # For now, just pass through - can be enhanced in future sprints
        response = await call_next(request)

        # Potential F1-specific metrics to add:
        # - Track which drivers/teams are most queried
        # - Monitor prediction accuracy over time
        # - Track race calendar access patterns
        # - Monitor feature usage in analytics dashboard

        return response