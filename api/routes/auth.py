"""
Authentication routes for user registration, login, and token management.
"""
from fastapi import APIRouter, HTTPException, Depends, status
from datetime import datetime, timezone
from ..models.user import User, RegisterRequest, LoginRequest, UserResponse
from ..models.token import TokenResponse, RefreshRequest, TokenData
from ..services.user_repository import user_repository
from ..utils.password import hash_password, verify_password
from ..utils.jwt import create_access_token, create_refresh_token, refresh_access_token, JWTError, verify_token
from ..middleware.auth import get_current_user

router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(request: RegisterRequest):
    """
    Register a new user.

    Args:
        request: User registration data

    Returns:
        User information (excluding password)

    Raises:
        HTTPException: If user already exists or registration fails
    """
    # Check if user already exists
    if user_repository.user_exists(request.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists"
        )

    try:
        # Hash the password
        password_hash = hash_password(request.password)

        # Create user
        user = User(
            email=request.email,
            password_hash=password_hash,
            created_at=datetime.now(timezone.utc)
        )

        # Add user to repository
        user_repository.add_user(user)

        # Return user response (excluding password)
        return UserResponse(
            email=user.email,
            created_at=user.created_at
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )


@router.post("/login", response_model=TokenResponse)
async def login_user(request: LoginRequest):
    """
    Authenticate user and return JWT tokens.

    Args:
        request: User login credentials

    Returns:
        JWT access and refresh tokens

    Raises:
        HTTPException: If credentials are invalid
    """
    # Get user from repository
    user = user_repository.get_user_by_email(request.email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify password
    try:
        if not verify_password(request.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        # Create tokens
        access_token = create_access_token(email=user.email)
        refresh_token = create_refresh_token(email=user.email)

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token
        )

    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token creation failed"
        )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_tokens(request: RefreshRequest):
    """
    Refresh access token using refresh token.

    Args:
        request: Refresh token request

    Returns:
        New access and refresh tokens

    Raises:
        HTTPException: If refresh token is invalid or expired
    """
    try:
        # Generate new access token
        access_token = refresh_access_token(request.refresh_token)

        # Verify the refresh token to get email for new refresh token
        token_data = verify_token(request.refresh_token, expected_type="refresh")

        # Create new refresh token
        new_refresh_token = create_refresh_token(email=token_data.email)

        return TokenResponse(
            access_token=access_token,
            refresh_token=new_refresh_token
        )

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed"
        )


@router.get("/profile", response_model=UserResponse)
async def get_user_profile(current_user: TokenData = Depends(get_current_user)):
    """
    Get current user profile information.

    Args:
        current_user: Current authenticated user from JWT token

    Returns:
        User profile information

    Raises:
        HTTPException: If user not found
    """
    user = user_repository.get_user_by_email(current_user.email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return UserResponse(
        email=user.email,
        created_at=user.created_at
    )


@router.get("/protected")
async def protected_endpoint(current_user: TokenData = Depends(get_current_user)):
    """
    Example protected endpoint that requires authentication.

    Args:
        current_user: Current authenticated user from JWT token

    Returns:
        Success message with user email
    """
    return {
        "message": f"Hello {current_user.email}, this is a protected endpoint!",
        "user": current_user.email
    }