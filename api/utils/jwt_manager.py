"""
JWT token management utilities.

Handles creation, validation, and decoding of JWT access and refresh tokens.
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

import jwt
from jwt.exceptions import InvalidTokenError, ExpiredSignatureError


class JWTManager:
    """
    JWT token manager for creating and validating access and refresh tokens.
    """

    def __init__(self):
        # Get JWT secret from environment or use default for development
        self.secret_key = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")
        self.algorithm = "HS256"

        # Token expiry times
        self.access_token_expire_minutes = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
        self.refresh_token_expire_days = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

    def create_access_token(self, email: str) -> str:
        """
        Create a new access token for the given user email.

        Args:
            email: User's email address

        Returns:
            Encoded JWT access token
        """
        expires_delta = timedelta(minutes=self.access_token_expire_minutes)
        return self._create_token(
            email=email,
            expires_delta=expires_delta,
            token_type="access"
        )

    def create_refresh_token(self, email: str) -> str:
        """
        Create a new refresh token for the given user email.

        Args:
            email: User's email address

        Returns:
            Encoded JWT refresh token
        """
        expires_delta = timedelta(days=self.refresh_token_expire_days)
        return self._create_token(
            email=email,
            expires_delta=expires_delta,
            token_type="refresh"
        )

    def _create_token(self, email: str, expires_delta: timedelta, token_type: str) -> str:
        """
        Create a JWT token with the specified parameters.

        Args:
            email: User's email address
            expires_delta: Token expiration time
            token_type: Type of token ('access' or 'refresh')

        Returns:
            Encoded JWT token
        """
        now = datetime.now(timezone.utc)
        expire = now + expires_delta

        payload = {
            "sub": email,  # Subject (user email)
            "exp": expire,  # Expiration time
            "iat": now,     # Issued at time
            "type": token_type  # Token type
        }

        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def decode_token(self, token: str) -> Dict:
        """
        Decode and validate a JWT token.

        Args:
            token: The JWT token to decode

        Returns:
            Decoded token payload

        Raises:
            JWTError: If token is invalid or expired
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except ExpiredSignatureError:
            raise JWTError("Token has expired")
        except InvalidTokenError:
            raise JWTError("Invalid token")

    def verify_token_type(self, payload: Dict, expected_type: str) -> bool:
        """
        Verify that the token has the expected type.

        Args:
            payload: Decoded token payload
            expected_type: Expected token type ('access' or 'refresh')

        Returns:
            True if token type matches, False otherwise
        """
        return payload.get("type") == expected_type

    def get_email_from_token(self, token: str) -> Optional[str]:
        """
        Extract email from a valid token.

        Args:
            token: The JWT token

        Returns:
            User email if token is valid, None otherwise
        """
        try:
            payload = self.decode_token(token)
            return payload.get("sub")
        except JWTError:
            return None


class JWTError(Exception):
    """Custom exception for JWT-related errors."""
    pass


# Global JWT manager instance
jwt_manager = JWTManager()