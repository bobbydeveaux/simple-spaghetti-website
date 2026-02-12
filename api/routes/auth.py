"""Authentication endpoints for user registration, login, and token refresh."""

from fastapi import APIRouter, HTTPException, status
from pydantic import ValidationError

from api.models.user import RegisterRequest, LoginRequest, RegisterResponse
from api.models.token import TokenResponse, RefreshRequest
from api.services.auth_service import auth_service

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(request: RegisterRequest):
    """
    Register a new user with email, password, and username.

    Args:
        request: RegisterRequest containing email, password, and username

    Returns:
        RegisterResponse with success message and user details

    Raises:
        HTTPException: 409 if user already exists, 400 for validation errors
    """
    try:
        user = auth_service.register_user(
            email=request.email,
            password=request.password,
            username=request.username
        )

        return RegisterResponse(
            message="User registered successfully",
            email=user.email,
            username=user.username,
            user_id=user.id
        )

    except ValueError as e:
        # User already exists
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
    except ValidationError as e:
        # Pydantic validation error
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Validation error: {str(e)}"
        )
    except Exception as e:
        # Unexpected error
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    """
    Authenticate user and return access and refresh tokens.

    Args:
        request: LoginRequest containing email and password

    Returns:
        TokenResponse with access_token, refresh_token, and token_type

    Raises:
        HTTPException: 401 for invalid credentials, 400 for validation errors
    """
    try:
        # Authenticate user
        user = auth_service.authenticate_user(
            email=request.email,
            password=request.password
        )

        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )

        # Generate tokens
        tokens = auth_service.generate_tokens(user.email)

        return TokenResponse(
            access_token=tokens["access_token"],
            refresh_token=tokens["refresh_token"],
            token_type="bearer"
        )

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except ValidationError as e:
        # Pydantic validation error
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Validation error: {str(e)}"
        )
    except Exception as e:
        # Unexpected error
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: RefreshRequest):
    """
    Generate a new access token using a valid refresh token.

    Args:
        request: RefreshRequest containing refresh_token

    Returns:
        TokenResponse with new access_token (refresh_token unchanged)

    Raises:
        HTTPException: 401 for invalid/expired refresh token, 400 for validation errors
    """
    try:
        # Generate new access token
        new_access_token = auth_service.refresh_access_token(request.refresh_token)

        return TokenResponse(
            access_token=new_access_token,
            refresh_token=request.refresh_token,  # Return original refresh token
            token_type="bearer"
        )

    except ValueError as e:
        # Invalid or expired refresh token
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    except ValidationError as e:
        # Pydantic validation error
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Validation error: {str(e)}"
        )
    except Exception as e:
        # Unexpected error
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )