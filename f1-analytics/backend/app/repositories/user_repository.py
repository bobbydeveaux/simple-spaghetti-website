"""
User repository for F1 Analytics authentication.

This module provides database operations for user management,
extending the base repository with user-specific functionality.
"""

import logging
from typing import Optional, List
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from .base import BaseRepository
from ..models.user import User

logger = logging.getLogger(__name__)


class UserRepository(BaseRepository[User]):
    """Repository for User model with authentication-specific methods."""

    def __init__(self, db_session: Session):
        super().__init__(User, db_session)

    def get_by_email(self, email: str) -> Optional[User]:
        """
        Get user by email address.

        Args:
            email: User email address

        Returns:
            User instance or None if not found
        """
        try:
            return self.db.query(User).filter(
                User.email == email,
                User.is_active == True
            ).first()
        except Exception as e:
            logger.error(f"Error getting user by email {email}: {e}")
            return None

    def get_active_users(self, skip: int = 0, limit: int = 100) -> List[User]:
        """
        Get all active users.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of active users
        """
        return self.get_by_fields(is_active=True)

    def get_admin_users(self) -> List[User]:
        """
        Get all admin users.

        Returns:
            List of admin users
        """
        return self.get_by_fields(role="admin", is_active=True)

    def create_user(
        self,
        email: str,
        password_hash: str,
        username: Optional[str] = None,
        role: str = "user"
    ) -> Optional[User]:
        """
        Create a new user with validation.

        Args:
            email: User email address
            password_hash: Hashed password
            username: Optional username
            role: User role (default: "user")

        Returns:
            Created user or None if creation failed
        """
        try:
            # Check if email already exists
            existing_user = self.get_by_email(email)
            if existing_user:
                logger.warning(f"Attempted to create user with existing email: {email}")
                return None

            user_data = {
                "email": email.lower().strip(),
                "password_hash": password_hash,
                "username": username.strip() if username else None,
                "role": role,
                "is_active": True,
                "is_verified": False,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
            }

            return self.create(user_data)

        except Exception as e:
            logger.error(f"Error creating user with email {email}: {e}")
            return None

    def update_last_login(self, user_id: int) -> bool:
        """
        Update user's last login timestamp.

        Args:
            user_id: User ID

        Returns:
            True if update was successful
        """
        try:
            return self.update(user_id, {
                "last_login": datetime.now(timezone.utc)
            }) is not None
        except Exception as e:
            logger.error(f"Error updating last login for user {user_id}: {e}")
            return False

    def verify_user(self, user_id: int) -> bool:
        """
        Mark user as verified.

        Args:
            user_id: User ID

        Returns:
            True if verification was successful
        """
        try:
            return self.update(user_id, {"is_verified": True}) is not None
        except Exception as e:
            logger.error(f"Error verifying user {user_id}: {e}")
            return False

    def deactivate_user(self, user_id: int) -> bool:
        """
        Deactivate a user account.

        Args:
            user_id: User ID

        Returns:
            True if deactivation was successful
        """
        try:
            return self.update(user_id, {"is_active": False}) is not None
        except Exception as e:
            logger.error(f"Error deactivating user {user_id}: {e}")
            return False

    def change_password(self, user_id: int, new_password_hash: str) -> bool:
        """
        Change user's password.

        Args:
            user_id: User ID
            new_password_hash: New hashed password

        Returns:
            True if password change was successful
        """
        try:
            return self.update(user_id, {
                "password_hash": new_password_hash
            }) is not None
        except Exception as e:
            logger.error(f"Error changing password for user {user_id}: {e}")
            return False

    def update_user_role(self, user_id: int, new_role: str) -> bool:
        """
        Update user's role.

        Args:
            user_id: User ID
            new_role: New role ("user" or "admin")

        Returns:
            True if role update was successful
        """
        if new_role not in ["user", "admin"]:
            logger.error(f"Invalid role: {new_role}")
            return False

        try:
            return self.update(user_id, {"role": new_role}) is not None
        except Exception as e:
            logger.error(f"Error updating role for user {user_id}: {e}")
            return False

    def search_users(self, search_term: str, limit: int = 50) -> List[User]:
        """
        Search users by email or username.

        Args:
            search_term: Search term to match against email/username
            limit: Maximum number of results

        Returns:
            List of matching users
        """
        try:
            search_pattern = f"%{search_term.lower()}%"
            return self.db.query(User).filter(
                User.is_active == True
            ).filter(
                (User.email.ilike(search_pattern)) |
                (User.username.ilike(search_pattern))
            ).limit(limit).all()

        except Exception as e:
            logger.error(f"Error searching users with term '{search_term}': {e}")
            return []

    def get_user_stats(self) -> dict:
        """
        Get user statistics.

        Returns:
            Dictionary with user statistics
        """
        try:
            total_users = self.count()
            active_users = self.count(is_active=True)
            verified_users = self.count(is_verified=True, is_active=True)
            admin_users = self.count(role="admin", is_active=True)

            return {
                "total_users": total_users,
                "active_users": active_users,
                "verified_users": verified_users,
                "admin_users": admin_users,
                "inactive_users": total_users - active_users
            }

        except Exception as e:
            logger.error(f"Error getting user stats: {e}")
            return {
                "total_users": 0,
                "active_users": 0,
                "verified_users": 0,
                "admin_users": 0,
                "inactive_users": 0
            }