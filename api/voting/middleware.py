"""Authentication middleware for PTA voting system."""

from fastapi import HTTPException, Header, Depends
from typing import Optional
import jwt
from datetime import datetime

from api.utils.jwt_manager import jwt_manager
from api.voting.models import Session


class VotingAuthenticationError(Exception):
    """Base exception for voting authentication errors."""
    pass


class SessionNotFoundError(VotingAuthenticationError):
    """Raised when session is not found in data store."""
    pass


class SessionExpiredError(VotingAuthenticationError):
    """Raised when JWT token or session has expired."""
    pass


# Placeholder for validate_session function - will be replaced when services.py is implemented
def validate_session_placeholder(token: str) -> Session:
    """
    Placeholder for validate_session function.

    This is a temporary implementation until api/voting/services.py is created
    with the actual validate_session function. The real implementation should:
    1. Decode JWT using jwt_manager
    2. Lookup session in data store
    3. Check expiration
    4. Return session or raise appropriate errors

    Args:
        token: JWT token string

    Returns:
        Session object if valid

    Raises:
        SessionNotFoundError: If session not found in data store
        SessionExpiredError: If token or session has expired
        VotingAuthenticationError: For other validation errors
    """
    try:
        # Decode JWT token
        payload = jwt_manager.decode_token(token)

        # Check if it's a voting session token (you may want to add a specific type)
        # For now, we'll accept any valid JWT token

        # Extract session information
        # In real implementation, this would lookup the session in data store
        # For now, create a mock session from JWT payload
        session = Session(
            session_id="mock-session-id",
            voter_id=payload.get("voter_id", "mock-voter-id"),
            token=token,
            created_at=datetime.utcnow(),
            expires_at=datetime.fromtimestamp(payload["exp"]),
            is_admin=payload.get("is_admin", False)
        )

        # Check if session is expired
        if datetime.utcnow() > session.expires_at:
            raise SessionExpiredError("Session has expired")

        return session

    except jwt.ExpiredSignatureError:
        raise SessionExpiredError("Token has expired")
    except jwt.InvalidTokenError as e:
        raise VotingAuthenticationError(f"Invalid token: {str(e)}")


# This will be replaced with actual import when services.py is implemented
# from api.voting.services import validate_session
validate_session = validate_session_placeholder


def verify_voting_session(authorization: Optional[str] = Header(None)) -> Session:
    """
    FastAPI dependency to verify voting session JWT tokens.

    Extracts the Authorization header, validates the Bearer token format,
    and validates the session using the validate_session function.

    Args:
        authorization: Authorization header value (automatically injected by FastAPI)

    Returns:
        Session object containing voter context

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

    if not token:
        raise HTTPException(
            status_code=401,
            detail="Token is required",
            headers={"WWW-Authenticate": "Bearer"}
        )

    try:
        # Validate session using the voting services
        session = validate_session(token)
        return session

    except SessionNotFoundError:
        raise HTTPException(
            status_code=401,
            detail="Session not found or invalid",
            headers={"WWW-Authenticate": "Bearer"}
        )
    except SessionExpiredError:
        raise HTTPException(
            status_code=401,
            detail="Session has expired",
            headers={"WWW-Authenticate": "Bearer"}
        )
    except VotingAuthenticationError as e:
        raise HTTPException(
            status_code=401,
            detail=f"Authentication failed: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"}
        )
    except Exception as e:
        raise HTTPException(
            status_code=401,
            detail=f"Token validation failed: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"}
        )


def verify_admin_session(authorization: Optional[str] = Header(None)) -> Session:
    """
    FastAPI dependency to verify admin session JWT tokens.

    Similar to verify_voting_session but also checks the is_admin flag.

    Args:
        authorization: Authorization header value (automatically injected by FastAPI)

    Returns:
        Session object containing admin voter context

    Raises:
        HTTPException: 401 if token is missing/invalid, 403 if not admin
    """
    # First verify it's a valid voting session
    session = verify_voting_session(authorization)

    # Then verify admin privileges
    if not session.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Admin privileges required"
        )

    return session


# Convenience function for direct token validation (not a FastAPI dependency)
def validate_token_direct(token: str) -> Session:
    """
    Directly validate a token without FastAPI dependency injection.

    Useful for internal use or testing.

    Args:
        token: JWT token string

    Returns:
        Session object if valid

    Raises:
        VotingAuthenticationError: If token is invalid or expired
    """
    return validate_session(token)