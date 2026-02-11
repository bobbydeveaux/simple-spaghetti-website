"""
Rate limiting utilities for authentication endpoints.
"""

import time
import threading
from collections import defaultdict, deque
from typing import Dict, Deque, Optional
from flask import request


class RateLimiter:
    """
    Simple in-memory rate limiter with sliding window approach.
    """

    def __init__(self):
        """Initialize rate limiter with thread-safe storage."""
        self._requests: Dict[str, Deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def is_rate_limited(self, identifier: str, max_requests: int, window_seconds: int) -> bool:
        """
        Check if an identifier (IP address, email, etc.) is rate limited.

        Args:
            identifier: Unique identifier for the requester
            max_requests: Maximum number of requests allowed
            window_seconds: Time window in seconds

        Returns:
            True if rate limited, False otherwise
        """
        current_time = time.time()
        window_start = current_time - window_seconds

        with self._lock:
            # Get request history for this identifier
            request_times = self._requests[identifier]

            # Remove old requests outside the window
            while request_times and request_times[0] < window_start:
                request_times.popleft()

            # Check if rate limit exceeded
            if len(request_times) >= max_requests:
                return True

            # Record this request
            request_times.append(current_time)
            return False

    def get_remaining_requests(self, identifier: str, max_requests: int, window_seconds: int) -> int:
        """
        Get number of remaining requests for an identifier.

        Args:
            identifier: Unique identifier for the requester
            max_requests: Maximum number of requests allowed
            window_seconds: Time window in seconds

        Returns:
            Number of remaining requests
        """
        current_time = time.time()
        window_start = current_time - window_seconds

        with self._lock:
            request_times = self._requests[identifier]

            # Remove old requests outside the window
            while request_times and request_times[0] < window_start:
                request_times.popleft()

            return max(0, max_requests - len(request_times))

    def reset_limit(self, identifier: str) -> None:
        """
        Reset rate limit for a specific identifier.

        Args:
            identifier: Unique identifier to reset
        """
        with self._lock:
            if identifier in self._requests:
                del self._requests[identifier]

    def cleanup_old_entries(self, max_age_seconds: int = 3600) -> None:
        """
        Clean up old entries to prevent memory bloat.
        Should be called periodically.

        Args:
            max_age_seconds: Maximum age of entries to keep
        """
        current_time = time.time()
        cutoff_time = current_time - max_age_seconds

        with self._lock:
            # Find identifiers with no recent requests
            to_remove = []
            for identifier, request_times in self._requests.items():
                # Remove old requests
                while request_times and request_times[0] < cutoff_time:
                    request_times.popleft()

                # Mark for removal if no recent requests
                if not request_times:
                    to_remove.append(identifier)

            # Remove empty entries
            for identifier in to_remove:
                del self._requests[identifier]


# Global rate limiter instance
rate_limiter = RateLimiter()


def get_client_ip() -> str:
    """
    Get client IP address from Flask request.
    Handles proxy headers for accurate IP detection.

    Returns:
        Client IP address
    """
    # Check for proxy headers first
    if request.headers.get('X-Forwarded-For'):
        # Get first IP if multiple (before proxy chain)
        return request.headers['X-Forwarded-For'].split(',')[0].strip()
    elif request.headers.get('X-Real-IP'):
        return request.headers['X-Real-IP'].strip()
    elif request.headers.get('X-Client-IP'):
        return request.headers['X-Client-IP'].strip()
    else:
        # Fall back to direct connection
        return request.remote_addr or 'unknown'


def rate_limit_decorator(max_requests: int, window_seconds: int, per_ip: bool = True):
    """
    Decorator for rate limiting Flask routes.

    Args:
        max_requests: Maximum requests allowed
        window_seconds: Time window in seconds
        per_ip: If True, rate limit per IP. If False, rate limit globally.

    Returns:
        Decorator function
    """
    def decorator(f):
        def wrapper(*args, **kwargs):
            if per_ip:
                identifier = get_client_ip()
            else:
                identifier = "global"

            if rate_limiter.is_rate_limited(identifier, max_requests, window_seconds):
                remaining = rate_limiter.get_remaining_requests(identifier, max_requests, window_seconds)
                return {
                    "error": "Too many requests",
                    "retry_after": window_seconds,
                    "remaining_requests": remaining
                }, 429

            return f(*args, **kwargs)

        # Preserve function name for Flask routing
        wrapper.__name__ = f.__name__
        return wrapper

    return decorator


# Pre-configured rate limit decorators for common use cases
auth_rate_limit = rate_limit_decorator(max_requests=5, window_seconds=300, per_ip=True)  # 5 requests per 5 minutes per IP
admin_rate_limit = rate_limit_decorator(max_requests=3, window_seconds=600, per_ip=True)  # 3 requests per 10 minutes per IP
code_request_limit = rate_limit_decorator(max_requests=3, window_seconds=60, per_ip=True)  # 3 requests per minute per IP