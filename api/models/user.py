"""
User data models and Pydantic schemas.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr


@dataclass
class User:
    """User dataclass for internal representation."""
    email: str
    password_hash: str
    created_at: datetime

    def __post_init__(self):
        """Validate email format and ensure created_at is set."""
        if not self.email or "@" not in self.email:
            raise ValueError("Invalid email format")
        if not self.password_hash:
            raise ValueError("Password hash cannot be empty")


# Pydantic models for API requests and responses

class RegisterRequest(BaseModel):
    """Request model for user registration."""
    email: EmailStr
    password: str

    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "password": "securepassword123"
            }
        }


class LoginRequest(BaseModel):
    """Request model for user login."""
    email: EmailStr
    password: str

    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "password": "securepassword123"
            }
        }


class UserResponse(BaseModel):
    """Response model for user data (excluding sensitive information)."""
    email: str
    created_at: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "created_at": "2024-01-01T12:00:00Z"
            }
        }