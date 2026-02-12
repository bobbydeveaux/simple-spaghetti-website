"""
JWT token management for F1 Prediction Analytics.

This module provides comprehensive JWT token creation, validation, and management
for the F1 analytics authentication system.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, Any

import jwt
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError

from ..config import settings

logger = logging.getLogger(__name__)


class JWTManager:
    """JWT token manager for F1 analytics authentication."""

    def __init__(self):
        self.secret_key = settings.jwt.secret_key
        self.algorithm = settings.jwt.algorithm
        self.access_token_expire_minutes = settings.jwt.access_token_expire_minutes
        self.refresh_token_expire_days = settings.jwt.refresh_token_expire_days

    def create_access_token(self, user_id: int, email: str, additional_claims: Optional[Dict] = None) -> str:
        """
        Create an access token for authenticated users.

        Args:
            user_id: User's database ID
            email: User's email address
            additional_claims: Optional additional JWT claims

        Returns:
            str: Encoded JWT access token

        Example:
            token = jwt_manager.create_access_token(
                user_id=123,
                email="user@example.com",
                additional_claims={"role": "admin"}
            )
        """
        now = datetime.now(timezone.utc)
        expire = now + timedelta(minutes=self.access_token_expire_minutes)

        payload = {
            "sub": str(user_id),  # Subject (user ID)
            "email": email,
            "type": "access",
            "exp": expire,
            "iat": now,
            "nbf": now  # Not before
        }

        if additional_claims:
            payload.update(additional_claims)

        try:
            token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
            logger.debug(f"Access token created for user {user_id}")
            return token
        except Exception as e:
            logger.error(f"Failed to create access token: {e}")
            raise JWTError(f"Token creation failed: {e}")

    def create_refresh_token(self, user_id: int, email: str) -> str:
        """
        Create a refresh token for token renewal.

        Args:
            user_id: User's database ID
            email: User's email address

        Returns:
            str: Encoded JWT refresh token
        """
        now = datetime.now(timezone.utc)
        expire = now + timedelta(days=self.refresh_token_expire_days)

        payload = {
            "sub": str(user_id),
            "email": email,
            "type": "refresh",
            "exp": expire,
            "iat": now,
            "nbf": now
        }

        try:
            token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
            logger.debug(f"Refresh token created for user {user_id}")
            return token
        except Exception as e:
            logger.error(f"Failed to create refresh token: {e}")
            raise JWTError(f"Refresh token creation failed: {e}")

    def create_token_pair(self, user_id: int, email: str, additional_claims: Optional[Dict] = None) -> Dict[str, str]:
        """
        Create both access and refresh tokens.

        Args:
            user_id: User's database ID
            email: User's email address
            additional_claims: Optional additional claims for access token

        Returns:
            dict: Dictionary with 'access_token' and 'refresh_token' keys
        """
        return {
            "access_token": self.create_access_token(user_id, email, additional_claims),
            "refresh_token": self.create_refresh_token(user_id, email),
            "token_type": "bearer"
        }

    def decode_token(self, token: str) -> Dict[str, Any]:
        """
        Decode and validate a JWT token.

        Args:
            token: JWT token string

        Returns:
            dict: Decoded token payload

        Raises:
            ExpiredTokenError: If token has expired
            InvalidTokenError: If token is invalid or malformed
        """
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                options={"verify_exp": True, "verify_nbf": True}
            )
            logger.debug(f"Token decoded successfully for user {payload.get('sub')}")
            return payload

        except ExpiredSignatureError:
            logger.warning("Token has expired")
            raise ExpiredTokenError("Token has expired")

        except InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            raise InvalidTokenError(f"Invalid token: {e}")

        except Exception as e:
            logger.error(f"Token decoding error: {e}")
            raise JWTError(f"Token decoding failed: {e}")

    def verify_token_type(self, payload: Dict[str, Any], expected_type: str) -> bool:
        """
        Verify that a token has the expected type.

        Args:
            payload: Decoded token payload
            expected_type: Expected token type ('access' or 'refresh')

        Returns:
            bool: True if token type matches

        Raises:
            InvalidTokenError: If token type doesn't match
        """
        token_type = payload.get("type")
        if token_type != expected_type:
            logger.warning(f"Token type mismatch. Expected: {expected_type}, Got: {token_type}")
            raise InvalidTokenError(f"Expected {expected_type} token, got {token_type}")
        return True

    def get_user_from_token(self, token: str, token_type: str = "access") -> Dict[str, Any]:
        """
        Extract user information from a token.

        Args:
            token: JWT token string
            token_type: Expected token type ('access' or 'refresh')

        Returns:
            dict: User information from token

        Example:
            user_info = jwt_manager.get_user_from_token(token)
            print(f"User ID: {user_info['user_id']}")
            print(f"Email: {user_info['email']}")
        """
        payload = self.decode_token(token)
        self.verify_token_type(payload, token_type)

        return {
            "user_id": int(payload["sub"]),
            "email": payload["email"],
            "expires_at": datetime.fromtimestamp(payload["exp"], tz=timezone.utc),
            "issued_at": datetime.fromtimestamp(payload["iat"], tz=timezone.utc),
            "additional_claims": {
                key: value for key, value in payload.items()
                if key not in ["sub", "email", "type", "exp", "iat", "nbf"]
            }
        }

    def is_token_expired(self, token: str) -> bool:
        """
        Check if a token is expired without raising an exception.

        Args:
            token: JWT token string

        Returns:
            bool: True if token is expired
        """
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                options={"verify_exp": False}  # Don't verify expiration
            )
            exp_timestamp = payload.get("exp")
            if exp_timestamp:
                exp_datetime = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
                return datetime.now(timezone.utc) > exp_datetime
            return True  # No expiration claim means we treat as expired
        except Exception:
            return True  # Invalid tokens are considered expired

    def refresh_access_token(self, refresh_token: str, additional_claims: Optional[Dict] = None) -> str:
        """
        Create a new access token using a refresh token.

        Args:
            refresh_token: Valid refresh token
            additional_claims: Optional additional claims for new access token

        Returns:
            str: New access token

        Raises:
            ExpiredTokenError: If refresh token has expired
            InvalidTokenError: If refresh token is invalid
        """
        user_info = self.get_user_from_token(refresh_token, token_type="refresh")

        return self.create_access_token(
            user_id=user_info["user_id"],
            email=user_info["email"],
            additional_claims=additional_claims
        )

    def get_token_expiration_info(self, token: str) -> Dict[str, Any]:
        """
        Get token expiration information.

        Args:
            token: JWT token string

        Returns:
            dict: Token expiration information
        """
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                options={"verify_exp": False}
            )

            exp_timestamp = payload.get("exp")
            iat_timestamp = payload.get("iat")

            if not exp_timestamp:
                return {"has_expiration": False}

            exp_datetime = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
            iat_datetime = datetime.fromtimestamp(iat_timestamp, tz=timezone.utc) if iat_timestamp else None
            now = datetime.now(timezone.utc)

            return {
                "has_expiration": True,
                "expires_at": exp_datetime.isoformat(),
                "issued_at": iat_datetime.isoformat() if iat_datetime else None,
                "is_expired": now > exp_datetime,
                "time_until_expiry": str(exp_datetime - now) if now < exp_datetime else "expired",
                "token_type": payload.get("type", "unknown")
            }

        except Exception as e:
            return {
                "error": f"Could not parse token: {e}",
                "has_expiration": False
            }


# JWT-specific exceptions
class JWTError(Exception):
    """Base exception for JWT operations."""
    pass


class ExpiredTokenError(JWTError):
    """Raised when a JWT token has expired."""
    pass


class InvalidTokenError(JWTError):
    """Raised when a JWT token is invalid."""
    pass


# Global JWT manager instance
jwt_manager = JWTManager()