"""
Security and performance middleware for F1 Analytics API.
"""
import time
import uuid
import logging
from typing import Callable
from fastapi import Request, Response
from fastapi.middleware.base import BaseHTTPMiddleware
from starlette.middleware.base import BaseHTTPMiddleware as StarletteBaseHTTPMiddleware
from core.config import get_settings, SecurityConfig

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""

    def __init__(self, app, environment: str = "development"):
        super().__init__(app)
        self.environment = environment
        self.security_headers = SecurityConfig.get_security_headers(environment)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        # Add security headers
        for header, value in self.security_headers.items():
            response.headers[header] = value

        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log all requests with timing and basic information."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate unique request ID
        request_id = str(uuid.uuid4())[:8]

        # Add request ID to request state for use in handlers
        request.state.request_id = request_id

        start_time = time.time()

        # Log request
        logger.info(
            f"[{request_id}] {request.method} {request.url} "
            f"- Client: {request.client.host if request.client else 'unknown'}"
        )

        try:
            response = await call_next(request)

            # Calculate processing time
            process_time = time.time() - start_time

            # Log response
            logger.info(
                f"[{request_id}] {response.status_code} "
                f"- {process_time:.3f}s"
            )

            # Add timing header
            response.headers["X-Process-Time"] = str(process_time)
            response.headers["X-Request-ID"] = request_id

            return response

        except Exception as e:
            process_time = time.time() - start_time
            logger.error(
                f"[{request_id}] ERROR {type(e).__name__}: {str(e)} "
                f"- {process_time:.3f}s"
            )
            raise


class RateLimitingMiddleware(BaseHTTPMiddleware):
    """Simple rate limiting middleware (in-memory, for demonstration)."""

    def __init__(self, app, requests_per_minute: int = 60):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.request_counts = {}  # In production, use Redis
        self.last_reset = time.time()

    def _reset_counts_if_needed(self):
        """Reset request counts every minute."""
        current_time = time.time()
        if current_time - self.last_reset >= 60:
            self.request_counts.clear()
            self.last_reset = current_time

    def _get_client_id(self, request: Request) -> str:
        """Get client identifier for rate limiting."""
        # Use X-Forwarded-For if behind proxy, otherwise client IP
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        self._reset_counts_if_needed()

        client_id = self._get_client_id(request)

        # Skip rate limiting for health checks
        if request.url.path == "/health":
            return await call_next(request)

        # Check current request count
        current_count = self.request_counts.get(client_id, 0)

        if current_count >= self.requests_per_minute:
            logger.warning(f"Rate limit exceeded for client: {client_id}")
            return Response(
                content='{"error": {"type": "rate_limit", "message": "Rate limit exceeded"}}',
                status_code=429,
                media_type="application/json",
                headers={
                    "X-RateLimit-Limit": str(self.requests_per_minute),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(self.last_reset + 60)),
                    "Retry-After": "60"
                }
            )

        # Increment counter
        self.request_counts[client_id] = current_count + 1

        response = await call_next(request)

        # Add rate limit headers
        remaining = max(0, self.requests_per_minute - self.request_counts[client_id])
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(self.last_reset + 60))

        return response


class HTTPSRedirectMiddleware(BaseHTTPMiddleware):
    """Redirect HTTP to HTTPS in production."""

    def __init__(self, app, enabled: bool = False):
        super().__init__(app)
        self.enabled = enabled

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if self.enabled:
            # Check if request is HTTP
            if request.headers.get("x-forwarded-proto") == "http":
                url = request.url.replace(scheme="https")
                return Response(
                    status_code=301,
                    headers={"Location": str(url)}
                )

        return await call_next(request)


def setup_middleware(app, settings=None):
    """Setup all middleware for the application."""
    if settings is None:
        settings = get_settings()

    # HTTPS redirect in production
    if settings.is_production:
        app.add_middleware(
            HTTPSRedirectMiddleware,
            enabled=True
        )

    # Security headers
    app.add_middleware(
        SecurityHeadersMiddleware,
        environment=settings.environment
    )

    # Rate limiting
    app.add_middleware(
        RateLimitingMiddleware,
        requests_per_minute=settings.rate_limit_per_minute
    )

    # Request logging
    app.add_middleware(RequestLoggingMiddleware)

    logger.info(f"Middleware configured for {settings.environment} environment")