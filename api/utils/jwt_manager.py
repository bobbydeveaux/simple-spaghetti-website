"""JWT token management utilities for authentication."""

import jwt
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional
from api.config import settings


class JWTManager:
    """Handles JWT token creation, validation, and decoding."""

    def __init__(self):
        """Initialize JWT manager with configuration settings."""
        self.secret_key = settings.JWT_SECRET_KEY
        self.algorithm = settings.JWT_ALGORITHM
        self.access_token_expire_minutes = settings.ACCESS_TOKEN_EXPIRE_MINUTES
        self.refresh_token_expire_days = settings.REFRESH_TOKEN_EXPIRE_DAYS

    def create_access_token(self, email: str) -> str:
        """
        Create an access token with 15-minute expiry.

        Args:
            email: User's email address

        Returns:
            JWT access token string
        """
        now = datetime.now(timezone.utc)
        expiry = now + timedelta(minutes=self.access_token_expire_minutes)

        payload = {
            "email": email,
            "type": "access",
            "exp": expiry,
            "iat": now
        }

        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def create_refresh_token(self, email: str) -> str:
        """
        Create a refresh token with 7-day expiry.

        Args:
            email: User's email address

        Returns:
            JWT refresh token string
        """
        now = datetime.now(timezone.utc)
        expiry = now + timedelta(days=self.refresh_token_expire_days)

        payload = {
            "email": email,
            "type": "refresh",
            "exp": expiry,
            "iat": now
        }

        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def decode_token(self, token: str) -> Dict:
        """
        Decode and validate a JWT token.

        Args:
            token: JWT token string

        Returns:
            Token payload dictionary

        Raises:
            jwt.ExpiredSignatureError: If token has expired
            jwt.InvalidTokenError: If token is invalid
        """
        return jwt.decode(token, self.secret_key, algorithms=[self.algorithm])

    def verify_token_type(self, payload: Dict, expected_type: str) -> bool:
        """
        Verify that the token type matches expected type.

        Args:
            payload: Decoded token payload
            expected_type: Expected token type ('access' or 'refresh')

        Returns:
            True if token type matches, False otherwise
        """
        return payload.get("type") == expected_type


# Global JWT manager instance
jwt_manager = JWTManager()