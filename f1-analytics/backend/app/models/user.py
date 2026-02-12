"""
User Model

Represents users of the F1 prediction analytics system.
Handles authentication and role-based access control.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import Column, Integer, String, DateTime, Index, CheckConstraint
from sqlalchemy.orm import validates

from ..database import Base


class User(Base):
    """
    User model for F1 prediction analytics system.

    Represents system users with authentication credentials and role-based access.
    Supports both regular users and administrators.

    Attributes:
        user_id: Primary key
        email: User email address (unique, used for login)
        password_hash: Bcrypt hashed password
        role: User role ('user' or 'admin')
        created_at: Account creation timestamp
        last_login: Last successful login timestamp

    Authentication:
        - Uses bcrypt for password hashing
        - Email serves as username
        - JWT tokens for session management
        - Role-based access control
    """

    __tablename__ = "users"

    # Primary key
    user_id = Column(Integer, primary_key=True, autoincrement=True)

    # Authentication information
    email = Column(String(255), nullable=False, unique=True, index=True)
    password_hash = Column(String(255), nullable=False)

    # Authorization
    role = Column(String(20), nullable=False, default="user", index=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True, index=True)

    # Constraints and indexes
    __table_args__ = (
        # Check constraints
        CheckConstraint(
            "role IN ('user', 'admin')",
            name="ck_users_role"
        ),
        CheckConstraint(
            "email LIKE '%@%'",
            name="ck_users_email_format"
        ),
        CheckConstraint(
            "length(email) >= 5",
            name="ck_users_email_min_length"
        ),
        # Performance indexes
        Index("idx_users_email", "email"),
        Index("idx_users_role", "role"),
        Index("idx_users_last_login", "last_login"),
        Index("idx_users_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<User(id={self.user_id}, email='{self.email}', role='{self.role}')>"

    def __str__(self) -> str:
        return f"{self.email} ({self.role})"

    @validates('email')
    def validate_email(self, key, email):
        """Validate email format"""
        if not email or '@' not in email or len(email) < 5:
            raise ValueError("Invalid email format")
        return email.lower().strip()

    @validates('role')
    def validate_role(self, key, role):
        """Validate user role"""
        valid_roles = ['user', 'admin']
        if role not in valid_roles:
            raise ValueError(f"Role must be one of: {valid_roles}")
        return role

    @property
    def is_admin(self) -> bool:
        """Check if user has admin role"""
        return self.role == "admin"

    @property
    def is_user(self) -> bool:
        """Check if user has regular user role"""
        return self.role == "user"

    @property
    def days_since_created(self) -> int:
        """Calculate days since account creation"""
        delta = datetime.utcnow() - self.created_at
        return delta.days

    @property
    def days_since_last_login(self) -> Optional[int]:
        """Calculate days since last login"""
        if self.last_login:
            delta = datetime.utcnow() - self.last_login
            return delta.days
        return None

    @property
    def is_active_user(self) -> bool:
        """Check if user has logged in within the last 30 days"""
        days_since = self.days_since_last_login
        return days_since is not None and days_since <= 30

    @property
    def is_new_user(self) -> bool:
        """Check if user account is new (created within last 7 days)"""
        return self.days_since_created <= 7

    def update_last_login(self) -> None:
        """Update the last login timestamp to current time"""
        self.last_login = datetime.utcnow()

    def to_dict(self, include_sensitive: bool = False) -> dict:
        """
        Convert user to dictionary for API responses.

        Args:
            include_sensitive: Whether to include sensitive fields like password_hash
        """
        data = {
            "user_id": self.user_id,
            "email": self.email,
            "role": self.role,
            "created_at": self.created_at.isoformat(),
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "is_admin": self.is_admin,
            "is_active_user": self.is_active_user,
            "is_new_user": self.is_new_user,
            "days_since_created": self.days_since_created,
            "days_since_last_login": self.days_since_last_login
        }

        if include_sensitive:
            data["password_hash"] = self.password_hash

        return data

    @classmethod
    def create_admin_user(cls, email: str, password_hash: str) -> 'User':
        """
        Create an admin user.

        Args:
            email: Admin email address
            password_hash: Bcrypt hashed password

        Returns:
            User: New admin user instance
        """
        return cls(
            email=email,
            password_hash=password_hash,
            role="admin"
        )

    @classmethod
    def create_regular_user(cls, email: str, password_hash: str) -> 'User':
        """
        Create a regular user.

        Args:
            email: User email address
            password_hash: Bcrypt hashed password

        Returns:
            User: New user instance
        """
        return cls(
            email=email,
            password_hash=password_hash,
            role="user"
        )