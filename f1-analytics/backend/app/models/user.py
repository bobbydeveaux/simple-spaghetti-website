"""User ORM model."""
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, Integer, String, DateTime, Index, CheckConstraint
from sqlalchemy.orm import relationship

from app.database import Base


class User(Base):
    """
    User entity for authentication and authorization.

    Stores user credentials and role information for accessing the F1 analytics platform.
    Supports both regular users and administrators.
    """

    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_login = Column(DateTime)
    role = Column(String(20), default="user")

    # Constraints
    __table_args__ = (
        CheckConstraint(
            role.in_(["user", "admin"]),
            name="ck_users_role"
        ),
        Index("idx_users_email", "email"),
    )

    def __repr__(self) -> str:
        return f"<User(user_id={self.user_id}, email='{self.email}', role='{self.role}')>"

    @property
    def is_admin(self) -> bool:
        """Check if user has admin privileges."""
        return self.role == "admin"

    @property
    def is_active_user(self) -> bool:
        """Check if user has logged in recently (within last 30 days)."""
        if not self.last_login:
            return False

        from datetime import timedelta
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        return self.last_login >= thirty_days_ago

    @property
    def account_age_days(self) -> int:
        """Get account age in days."""
        return (datetime.utcnow() - self.created_at).days

    @property
    def display_name(self) -> str:
        """Get display name (username part of email)."""
        return self.email.split('@')[0] if '@' in self.email else self.email

    def update_last_login(self):
        """Update last login timestamp to current time."""
        self.last_login = datetime.utcnow()

    def has_permission(self, permission: str) -> bool:
        """Check if user has specific permission."""
        # Simple role-based permissions
        if self.role == "admin":
            return True  # Admins have all permissions

        # Regular users have limited permissions
        user_permissions = ["view_predictions", "view_analytics", "export_data"]
        return permission in user_permissions