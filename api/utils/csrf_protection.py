"""
CSRF (Cross-Site Request Forgery) protection utilities.
"""

import secrets
import time
import hashlib
from typing import Dict, Optional
from flask import session, request


class CSRFProtection:
    """CSRF token generation and validation."""

    def __init__(self, secret_key: str):
        """Initialize with app secret key."""
        self.secret_key = secret_key
        self.token_lifetime = 3600  # 1 hour

    def generate_token(self) -> str:
        """Generate a CSRF token."""
        # Create a unique token with timestamp
        timestamp = str(int(time.time()))
        random_data = secrets.token_urlsafe(32)

        # Create token with timestamp and signature
        token_data = f"{timestamp}:{random_data}"
        signature = hashlib.sha256(
            f"{self.secret_key}:{token_data}".encode()
        ).hexdigest()

        return f"{token_data}:{signature}"

    def validate_token(self, token: str) -> bool:
        """Validate a CSRF token."""
        if not token:
            return False

        try:
            # Split token parts
            parts = token.split(':')
            if len(parts) != 3:
                return False

            timestamp_str, random_data, signature = parts
            timestamp = int(timestamp_str)

            # Check if token has expired
            current_time = int(time.time())
            if current_time - timestamp > self.token_lifetime:
                return False

            # Verify signature
            token_data = f"{timestamp_str}:{random_data}"
            expected_signature = hashlib.sha256(
                f"{self.secret_key}:{token_data}".encode()
            ).hexdigest()

            return secrets.compare_digest(signature, expected_signature)

        except (ValueError, IndexError):
            return False


def get_csrf_token() -> str:
    """Get or create CSRF token for current session."""
    from api.config import settings

    csrf = CSRFProtection(settings.JWT_SECRET_KEY)

    # Generate new token for each request (stateless approach)
    token = csrf.generate_token()
    return token


def validate_csrf_token(token: str) -> bool:
    """Validate CSRF token."""
    from api.config import settings

    csrf = CSRFProtection(settings.JWT_SECRET_KEY)
    return csrf.validate_token(token)


def csrf_required(f):
    """Decorator to require CSRF token for POST/PUT/DELETE requests."""
    def wrapper(*args, **kwargs):
        # Only check CSRF for state-changing methods
        if request.method in ['POST', 'PUT', 'DELETE']:
            # Get token from header or form data
            token = request.headers.get('X-CSRF-Token') or request.form.get('csrf_token')

            if not token or not validate_csrf_token(token):
                return {"error": "Invalid or missing CSRF token"}, 403

        return f(*args, **kwargs)

    # Preserve function name for Flask routing
    wrapper.__name__ = f.__name__
    return wrapper