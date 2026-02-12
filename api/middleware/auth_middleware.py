"""JWT authentication middleware for FastAPI route protection."""

from fastapi import HTTPException, Header
from typing import Optional
import jwt

from api.utils.jwt_manager import jwt_manager
from api.services.user_repository import user_repository


def verify_access_token(authorization: Optional[str] = Header(None)) -> str:
    """
    FastAPI dependency to verify JWT access tokens.

    Args:
        authorization: Authorization header value

    Returns:
        User's email address from validated token

    Raises:
        HTTPException: 401 if token is missing, invalid, or expired
    """
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Authorization header required",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # Check if it's a Bearer token
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Invalid authorization header format. Must be 'Bearer <token>'",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # Extract token from "Bearer <token>"
    token = authorization[7:]  # Remove "Bearer " prefix

    try:
        # Decode and validate token
        payload = jwt_manager.decode_token(token)

        # Verify it's an access token
        if not jwt_manager.verify_token_type(payload, "access"):
            raise HTTPException(
                status_code=401,
                detail="Invalid token type",
                headers={"WWW-Authenticate": "Bearer"}
            )

        # Extract email from payload
        email = payload.get("email")
        if not email:
            raise HTTPException(
                status_code=401,
                detail="Invalid token payload",
                headers={"WWW-Authenticate": "Bearer"}
            )

        # Verify user still exists
        if not user_repository.user_exists(email):
            raise HTTPException(
                status_code=401,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"}
            )

        return email

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=401,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"}
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=401,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"}
        )
    except Exception as e:
        raise HTTPException(
            status_code=401,
            detail=f"Token validation failed: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"}
        )