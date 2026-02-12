"""
User model for F1 Prediction Analytics authentication.

This module defines the User SQLAlchemy model for storing user account information
and authentication data with comprehensive features and validation.
"""

from datetime import datetime, timezone, date
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Index
from sqlalchemy.orm import relationship, validates

from ..database import Base


class User(Base):
    """
    SQLAlchemy model for application users.

    This model stores user authentication information for accessing
    the F1 prediction analytics dashboard and API endpoints. It includes
    comprehensive user management features with validation.

    Attributes:
        user_id: Primary key, unique identifier for user
        email: User's email address (unique, used for login)
        password_hash: Bcrypt hashed password
        username: Optional username for display purposes
        created_at: Timestamp when user account was created
        updated_at: Timestamp when user was last updated
        last_login: Timestamp of user's last login
        is_active: Whether the user account is active
        is_verified: Whether the user's email is verified
        role: User role (user, admin) for authorization
    """

    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    username = Column(String(100), nullable=True)

    # Timestamps with timezone awareness
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

    @validates('email')
    def validate_email(self, key, email):
        """Validate email format and normalize."""
        import re

        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_regex, email):
            raise ValueError("Invalid email format")
        return email.lower()

    @validates('role')
    def validate_role(self, key, role):
        """Validate role is one of allowed values."""
        allowed_roles = ['user', 'admin']
        if role not in allowed_roles:
            raise ValueError(f"Role must be one of: {', '.join(allowed_roles)}")
        return role

    def __repr__(self) -> str:
        """String representation of User instance."""
        return f"<User(user_id={self.user_id}, email='{self.email}', role='{self.role}')>"

    def __str__(self) -> str:
        """Human-readable string representation."""
        return f"{self.email} ({self.role})"

    @property
    def is_admin(self) -> bool:
        """Check if user has admin role."""
        return self.role == "admin"

    @property
    def display_name(self) -> str:
        """Return display-friendly name (username or email prefix)."""
        if self.username:
            return self.username
        return self.email.split('@')[0]

    @property
    def is_new_user(self) -> bool:
        """Check if user is new (never logged in)."""
        return self.last_login is None

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
            "role": self.role,
            "display_name": self.display_name,
            "is_new_user": self.is_new_user,
            "is_admin": self.is_admin
        }

        if not exclude_sensitive:
            data["password_hash"] = self.password_hash

        return data

    def can_access_admin_features(self) -> bool:
        """Check if user can access admin features."""
        return self.is_active and self.is_admin

    def set_password(self, password: str) -> None:
        """
        Hash and set user password.

        Args:
            password: Plain text password to hash
        """
        import bcrypt

        # Validate password strength
        if len(password) < 8:
            raise ValueError("Password must be at least 8 characters long")

        # Hash password with bcrypt
        password_bytes = password.encode('utf-8')
        salt = bcrypt.gensalt(rounds=12)
        self.password_hash = bcrypt.hashpw(password_bytes, salt).decode('utf-8')

    def check_password(self, password: str) -> bool:
        """
        Verify password against stored hash.

        Args:
            password: Plain text password to verify

        Returns:
            bool: True if password matches, False otherwise
        """
        import bcrypt

        if not self.password_hash:
            return False

        password_bytes = password.encode('utf-8')
        hash_bytes = self.password_hash.encode('utf-8')

        return bcrypt.checkpw(password_bytes, hash_bytes)

    def update_last_login(self) -> None:
        """Update last login timestamp to current time."""
        self.last_login = datetime.now(timezone.utc)

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