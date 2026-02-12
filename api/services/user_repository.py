"""In-memory user repository for storing and retrieving users."""

from typing import Dict, Optional
from api.models.user import User


class UserRepository:
    """In-memory user storage using a dictionary."""

    # Class-level dict to store users across all instances
    _users: Dict[str, User] = {}

    def add_user(self, user: User) -> None:
        """
        Add a user to the repository.

        Args:
            user: User object to store

        Raises:
            ValueError: If user with the same email already exists
        """
        if user.email in self._users:
            raise ValueError(f"User with email {user.email} already exists")

        self._users[user.email] = user

    def get_user_by_email(self, email: str) -> Optional[User]:
        """
        Retrieve a user by email address.

        Args:
            email: User's email address

        Returns:
            User object if found, None otherwise
        """
        return self._users.get(email)

    def user_exists(self, email: str) -> bool:
        """
        Check if a user exists by email address.

        Args:
            email: User's email address

        Returns:
            True if user exists, False otherwise
        """
        return email in self._users

    def get_all_users(self) -> Dict[str, User]:
        """
        Get all users for debugging/testing purposes.

        Returns:
            Dictionary of all users keyed by email
        """
        return self._users.copy()

    def clear_all_users(self) -> None:
        """
        Clear all users from repository (for testing).
        """
        self._users.clear()


# Global repository instance
user_repository = UserRepository()