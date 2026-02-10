"""
Token models and schemas for JWT authentication
"""

from pydantic import BaseModel, Field


class TokenResponse(BaseModel):
    """Schema for token response (login/refresh)"""
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")


class RefreshRequest(BaseModel):
    """Schema for token refresh request"""
    refresh_token: str = Field(..., description="JWT refresh token to exchange for new access token")


class ProtectedResponse(BaseModel):
    """Schema for protected endpoint response"""
    message: str = Field(..., description="Success message")
    user: dict = Field(..., description="Authenticated user information")