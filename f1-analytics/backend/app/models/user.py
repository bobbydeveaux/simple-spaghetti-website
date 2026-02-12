"""
User model for F1 Prediction Analytics authentication.

This module defines the User SQLAlchemy model for storing user account information
and authentication data.
"""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Index
from sqlalchemy.orm import relationship

from ..database import Base


class User(Base):
    """User model for authentication and user management."""

    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    username = Column(String(100), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    last_login = Column(DateTime(timezone=True), nullable=True)

    # User status and role
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    role = Column(String(20), default="user", nullable=False)  # user, admin

    # Additional indexes for performance
    __table_args__ = (
        Index('idx_users_email_active', 'email', 'is_active'),
        Index('idx_users_role_active', 'role', 'is_active'),
        Index('idx_users_created_at', 'created_at'),
    )

    def __repr__(self) -> str:
        return f"<User(user_id={self.user_id}, email='{self.email}', role='{self.role}')>"

    def to_dict(self, exclude_sensitive: bool = True) -> dict:
        """
        Convert user to dictionary representation.

        Args:
            exclude_sensitive: Whether to exclude sensitive fields like password_hash

        Returns:
            dict: User data as dictionary
        """
        data = {
            "user_id": self.user_id,
            "email": self.email,
            "username": self.username,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "is_active": self.is_active,
            "is_verified": self.is_verified,
            "role": self.role
        }

        if not exclude_sensitive:
            data["password_hash"] = self.password_hash

        return data

    def is_admin(self) -> bool:
        """Check if user has admin role."""
        return self.role == "admin"

    def can_access_admin_features(self) -> bool:
        """Check if user can access admin features."""
        return self.is_active and self.is_admin()

    @classmethod
    def get_by_email(cls, db_session, email: str):
        """
        Get user by email address.

        Args:
            db_session: Database session
            email: User email address

        Returns:
            User or None: User instance if found
        """
        return db_session.query(cls).filter(
            cls.email == email,
            cls.is_active == True
        ).first()

    @classmethod
    def get_by_id(cls, db_session, user_id: int):
        """
        Get user by ID.

        Args:
            db_session: Database session
            user_id: User ID

        Returns:
            User or None: User instance if found
        """
        return db_session.query(cls).filter(
            cls.user_id == user_id,
            cls.is_active == True
        ).first()