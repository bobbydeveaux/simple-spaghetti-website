"""
JWT token utilities for authentication.
"""
import jwt
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from ..config import settings
from ..models.token import TokenData


class JWTError(Exception):
    """Custom exception for JWT-related errors."""
    pass


def create_access_token(email: str, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.

    Args:
        email: User email to include in the token
        expires_delta: Optional custom expiration time

    Returns:
        Encoded JWT token string

    Raises:
        JWTError: If token creation fails
        ValueError: If email is empty or None
    """
    if not email:
        raise ValueError("Email cannot be empty")

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode = {
        "sub": email,
        "exp": expire,
        "token_type": "access"
    }

    try:
        encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
        return encoded_jwt
    except Exception as e:
        raise JWTError(f"Failed to create access token: {str(e)}")


def create_refresh_token(email: str, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT refresh token.

    Args:
        email: User email to include in the token
        expires_delta: Optional custom expiration time

    Returns:
        Encoded JWT token string

    Raises:
        JWTError: If token creation fails
        ValueError: If email is empty or None
    """
    if not email:
        raise ValueError("Email cannot be empty")

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    to_encode = {
        "sub": email,
        "exp": expire,
        "token_type": "refresh"
    }

    try:
        encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
        return encoded_jwt
    except Exception as e:
        raise JWTError(f"Failed to create refresh token: {str(e)}")


def verify_token(token: str, expected_type: str = "access") -> TokenData:
    """
    Verify and decode a JWT token.

    Args:
        token: JWT token string to verify
        expected_type: Expected token type ("access" or "refresh")

    Returns:
        TokenData object containing decoded information

    Raises:
        JWTError: If token is invalid, expired, or wrong type
        ValueError: If token is empty or None
    """
    if not token:
        raise ValueError("Token cannot be empty")

    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        email: str = payload.get("sub")
        token_type: str = payload.get("token_type")

        if not email:
            raise JWTError("Token missing email")

        if token_type != expected_type:
            raise JWTError(f"Token type mismatch. Expected {expected_type}, got {token_type}")

        return TokenData(email=email, token_type=token_type)

    except jwt.ExpiredSignatureError:
        raise JWTError("Token has expired")
    except jwt.JWTError as e:
        raise JWTError(f"Invalid token: {str(e)}")
    except Exception as e:
        raise JWTError(f"Token verification failed: {str(e)}")


def refresh_access_token(refresh_token: str) -> str:
    """
    Generate a new access token from a refresh token.

    Args:
        refresh_token: Valid refresh token

    Returns:
        New access token string

    Raises:
        JWTError: If refresh token is invalid or expired
    """
    token_data = verify_token(refresh_token, expected_type="refresh")
    return create_access_token(email=token_data.email)