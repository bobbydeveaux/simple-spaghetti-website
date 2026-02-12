"""
User data models and Pydantic schemas.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
import re
from pydantic import BaseModel, EmailStr, validator


@dataclass
class User:
    """User dataclass for internal representation."""
    email: str
    password_hash: str
    created_at: datetime

    def __post_init__(self):
        """Validate email format and ensure created_at is set."""
        self._validate_email()
        if not self.password_hash:
            raise ValueError("Password hash cannot be empty")

    def _validate_email(self):
        """Validate email format using regex."""
        if not self.email:
            raise ValueError("Email cannot be empty")

        # Improved email validation regex
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, self.email):
            raise ValueError("Invalid email format")


# Pydantic models for API requests and responses

class RegisterRequest(BaseModel):
    """Request model for user registration."""
    email: EmailStr
    password: str

    @validator('password')
    def validate_password_strength(cls, v):
        """Validate password meets security requirements."""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not re.search(r'[A-Za-z]', v):
            raise ValueError('Password must contain at least one letter')
        if not re.search(r'[0-9]', v):
            raise ValueError('Password must contain at least one digit')
        return v

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