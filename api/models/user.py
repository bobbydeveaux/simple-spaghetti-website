"""
User data models and Pydantic schemas for authentication
"""

from dataclasses import dataclass, field
from typing import Optional
from pydantic import BaseModel, EmailStr, Field
import uuid


@dataclass
class User:
    """User dataclass for internal application use"""
    email: str
    hashed_password: str
    username: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))


# Request schemas
class RegisterRequest(BaseModel):
    """Schema for user registration request"""
    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(..., min_length=8, description="User's password (minimum 8 characters)")
    username: str = Field(..., min_length=3, max_length=50, description="User's username")


class LoginRequest(BaseModel):
    """Schema for user login request"""
    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(..., description="User's password")


# Response schemas
class RegisterResponse(BaseModel):
    """Schema for user registration response"""
    message: str = Field(..., description="Success message")
    email: str = Field(..., description="Registered email address")
    username: str = Field(..., description="Registered username")
    user_id: str = Field(..., description="Generated user ID")