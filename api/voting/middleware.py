"""
PTA Voting System - Authentication Middleware
"""
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional

from .services import voter_auth_service
from .models import Session


# Security scheme for JWT tokens
security = HTTPBearer()


async def get_current_voter_session(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Session:
    """
    Dependency to get current voter session from JWT token.
    Raises 401 if token is invalid or session expired.
    """
    token = credentials.credentials

    session = voter_auth_service.validate_session(token)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return session


async def get_optional_voter_session(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))
) -> Optional[Session]:
    """
    Dependency to optionally get current voter session.
    Returns None if no token provided or token invalid.
    """
    if not credentials:
        return None

    token = credentials.credentials
    return voter_auth_service.validate_session(token)


async def require_admin_session(
    session: Session = Depends(get_current_voter_session)
) -> Session:
    """
    Dependency that requires an admin session.
    Raises 403 if session is not admin.
    """
    if not session.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    return session


# Convenience function for extracting voter ID from session
def get_voter_id_from_session(session: Session) -> str:
    """Extract voter ID from session"""
    return session.voter_id