"""
In-memory user repository implementation.

This repository provides thread-safe storage and retrieval of users using
a dictionary-based approach. Suitable for development and testing with
up to ~1000 users.
"""
import threading
from typing import Dict, Optional
from datetime import datetime

from ..models.user import User


class UserRepository:
    """
    In-memory user repository using dictionary storage.

    This implementation stores users in a class-level dictionary with email
    as the key for O(1) lookup performance. Thread safety is ensured using
    a threading lock for concurrent access scenarios.

    Features:
    - O(1) user lookup by email
    - Thread-safe operations
    - Duplicate email prevention
    - Basic CRUD operations (Create, Read, Exists check)

    Note: Data is not persisted and will be lost when the process restarts.
    """

    # Class-level storage - shared across all instances
    _users: Dict[str, User] = {}
    _lock = threading.Lock()

    def add_user(self, user: User) -> None:
        """
        Add a new user to the repository.

        Args:
            user: User instance to store

        Raises:
            ValueError: If user with this email already exists
            TypeError: If user is not a User instance
        """
        if not isinstance(user, User):
            raise TypeError("user must be an instance of User")

        with self._lock:
            if user.email in self._users:
                raise ValueError(f"User with email {user.email} already exists")

            self._users[user.email] = user

    def get_user_by_email(self, email: str) -> Optional[User]:
        """
        Retrieve a user by their email address.

        Args:
            email: Email address to search for

        Returns:
            User instance if found, None otherwise

        Raises:
            TypeError: If email is not a string
        """
        if not isinstance(email, str):
            raise TypeError("email must be a string")

        with self._lock:
            return self._users.get(email)

    def user_exists(self, email: str) -> bool:
        """
        Check if a user exists with the given email.

        Args:
            email: Email address to check

        Returns:
            True if user exists, False otherwise

        Raises:
            TypeError: If email is not a string
        """
        if not isinstance(email, str):
            raise TypeError("email must be a string")

        with self._lock:
            return email in self._users

    def get_user_count(self) -> int:
        """
        Get the total number of users in the repository.

        Returns:
            Number of stored users
        """
        with self._lock:
            return len(self._users)

    def clear_all_users(self) -> None:
        """
        Remove all users from the repository.

        Warning: This operation is irreversible and will delete all stored users.
        Primarily intended for testing purposes.
        """
        with self._lock:
            self._users.clear()


# Singleton instance for application-wide use
user_repository = UserRepository()