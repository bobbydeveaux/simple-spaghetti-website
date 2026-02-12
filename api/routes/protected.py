"""Protected endpoints that require JWT authentication."""

from fastapi import APIRouter, Depends

from api.models.token import ProtectedResponse
from api.middleware.auth_middleware import verify_access_token

router = APIRouter(prefix="/protected", tags=["protected"])


@router.get("/", response_model=ProtectedResponse)
async def get_protected_data(current_user_email: str = Depends(verify_access_token)):
    """
    Protected endpoint that requires a valid JWT access token.

    Args:
        current_user_email: User email extracted from JWT token by middleware

    Returns:
        ProtectedResponse with success message and user information

    Note:
        This endpoint requires a valid JWT access token in the Authorization header.
        Format: "Authorization: Bearer <access_token>"
    """
    return ProtectedResponse(
        message="Access granted to protected resource",
        user={
            "email": current_user_email
        }
    )