"""
Authentication middleware for JWT token validation.
"""
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from ..utils.jwt import verify_token, JWTError
from ..models.token import TokenData

security = HTTPBearer()


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> TokenData:
    """
    Dependency to get current authenticated user from JWT token.

    Args:
        credentials: HTTP authorization credentials

    Returns:
        TokenData object containing user information

    Raises:
        HTTPException: If token is invalid or missing
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not credentials:
        raise credentials_exception

    try:
        token_data = verify_token(credentials.credentials, expected_type="access")
        return token_data
    except JWTError:
        raise credentials_exception
    except Exception:
        raise credentials_exception


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[TokenData]:
    """
    Optional dependency to get current user (doesn't require authentication).

    Args:
        credentials: Optional HTTP authorization credentials

    Returns:
        TokenData object if valid token provided, None otherwise
    """
    if not credentials:
        return None

    try:
        return verify_token(credentials.credentials, expected_type="access")
    except (JWTError, Exception):
        return None