"""Authentication service for user registration, login, and token management."""

import uuid
from typing import Optional, Dict
from pydantic import ValidationError

from api.models.user import User
from api.services.user_repository import user_repository
from api.utils.password import hash_password, verify_password
from api.utils.jwt_manager import jwt_manager


class AuthService:
    """Business logic for authentication operations."""

    def __init__(self):
        """Initialize auth service with dependencies."""
        self.user_repo = user_repository
        self.jwt_manager = jwt_manager

    def register_user(self, email: str, password: str, username: str) -> User:
        """
        Register a new user with email and password.

        Args:
            email: User's email address
            password: Plain text password
            username: User's username

        Returns:
            Created User object

        Raises:
            ValueError: If user with email already exists or validation fails
        """
        # Check if user already exists
        if self.user_repo.user_exists(email):
            raise ValueError(f"User with email {email} already exists")

        # Hash the password
        hashed_password = hash_password(password)

        # Create user with UUID
        user = User(
            email=email,
            hashed_password=hashed_password,
            username=username,
            id=uuid.uuid4()
        )

        # Add to repository
        self.user_repo.add_user(user)

        return user

    def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """
        Authenticate a user with email and password.

        Args:
            email: User's email address
            password: Plain text password

        Returns:
            User object if authentication succeeds, None otherwise
        """
        # Get user from repository
        user = self.user_repo.get_user_by_email(email)
        if user is None:
            return None

        # Verify password
        if not verify_password(password, user.hashed_password):
            return None

        return user

    def generate_tokens(self, email: str) -> Dict[str, str]:
        """
        Generate access and refresh tokens for a user.

        Args:
            email: User's email address

        Returns:
            Dictionary containing access_token and refresh_token
        """
        access_token = self.jwt_manager.create_access_token(email)
        refresh_token = self.jwt_manager.create_refresh_token(email)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token
        }

    def refresh_access_token(self, refresh_token: str) -> str:
        """
        Generate a new access token using a valid refresh token.

        Args:
            refresh_token: Valid refresh token string

        Returns:
            New access token string

        Raises:
            ValueError: If refresh token is invalid, expired, or wrong type
        """
        try:
            # Decode the refresh token
            payload = self.jwt_manager.decode_token(refresh_token)

            # Verify it's a refresh token
            if not self.jwt_manager.verify_token_type(payload, "refresh"):
                raise ValueError("Invalid token type")

            # Extract email and verify user still exists
            email = payload.get("email")
            if not email or not self.user_repo.user_exists(email):
                raise ValueError("User not found")

            # Generate new access token
            return self.jwt_manager.create_access_token(email)

        except Exception as e:
            raise ValueError(f"Invalid or expired refresh token: {str(e)}")


# Global auth service instance
auth_service = AuthService()