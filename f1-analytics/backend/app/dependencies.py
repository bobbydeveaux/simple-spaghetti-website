"""
FastAPI dependency injection providers for F1 Analytics.

This module provides dependency injection functions for FastAPI endpoints,
including database sessions, authentication, and service instances.
"""

import logging
from typing import Generator, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from .database import get_db, Session
from .utils.jwt_manager import jwt_manager, ExpiredTokenError, InvalidTokenError
from .utils.session_manager import session_manager
from .repositories.user_repository import UserRepository
from .models.user import User

logger = logging.getLogger(__name__)

# Security scheme for JWT token authentication
security = HTTPBearer()


def get_user_repository(db: Session = Depends(get_db)) -> UserRepository:
    """
    Get user repository instance.

    Args:
        db: Database session

    Returns:
        UserRepository: User repository instance
    """
    return UserRepository(db)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    user_repo: UserRepository = Depends(get_user_repository)
) -> User:
    """
    Get current authenticated user from JWT token.

    Args:
        credentials: JWT credentials from Authorization header
        user_repo: User repository instance

    Returns:
        User: Current authenticated user

    Raises:
        HTTPException: If authentication fails
    """
    try:
        # Extract token from credentials
        token = credentials.credentials

        # Decode and validate JWT token
        user_info = jwt_manager.get_user_from_token(token, token_type="access")

        # Get user from database
        user = user_repo.get_by_id(user_info["user_id"])
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Update session access time
        await session_manager.update_session_access(user.user_id)

        return user

    except ExpiredTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_admin_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get current authenticated admin user.

    Args:
        current_user: Current authenticated user

    Returns:
        User: Current authenticated admin user

    Raises:
        HTTPException: If user is not an admin
    """
    if not current_user.is_admin():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )

    return current_user


def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    user_repo: UserRepository = Depends(get_user_repository)
) -> Optional[User]:
    """
    Get current user if authenticated, otherwise return None.

    This is useful for endpoints that work for both authenticated
    and anonymous users but provide different functionality.

    Args:
        credentials: Optional JWT credentials
        user_repo: User repository instance

    Returns:
        User or None: Current user if authenticated, None otherwise
    """
    if not credentials:
        return None

    try:
        token = credentials.credentials
        user_info = jwt_manager.get_user_from_token(token, token_type="access")
        user = user_repo.get_by_id(user_info["user_id"])

        if user and user.is_active:
            return user

    except (ExpiredTokenError, InvalidTokenError):
        pass
    except Exception as e:
        logger.debug(f"Optional authentication failed: {e}")

    return None


async def validate_rate_limit(
    current_user: Optional[User] = Depends(get_optional_current_user)
) -> bool:
    """
    Validate rate limiting for current user.

    Args:
        current_user: Current user (None for anonymous users)

    Returns:
        bool: Always True (raises exception if rate limit exceeded)

    Raises:
        HTTPException: If rate limit is exceeded
    """
    try:
        user_id = current_user.user_id if current_user else 0  # Use 0 for anonymous users

        rate_limit_info = await session_manager.check_rate_limit(user_id)

        if not rate_limit_info.get("allowed", True):
            remaining = rate_limit_info.get("remaining_requests", 0)
            reset_time = rate_limit_info.get("reset_time")

            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded",
                headers={
                    "X-RateLimit-Remaining": str(remaining),
                    "X-RateLimit-Reset": reset_time.isoformat() if reset_time else "",
                    "Retry-After": str(rate_limit_info.get("window_seconds", 60))
                }
            )

        return True

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Rate limiting error: {e}")
        # Fail open - allow request if rate limiting fails
        return True