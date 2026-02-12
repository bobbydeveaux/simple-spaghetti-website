"""
User model for F1 Prediction Analytics.

This module defines the User SQLAlchemy model for authentication
and user management in the F1 analytics dashboard.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import validates

from app.database import Base


class User(Base):
    """
    SQLAlchemy model for application users.

    This model stores user authentication information for accessing
    the F1 prediction analytics dashboard and API endpoints.

    Attributes:
        user_id: Primary key, unique identifier for user
        email: User's email address (unique, used for login)
        password_hash: Bcrypt hashed password
        created_at: Timestamp when user account was created
        last_login: Timestamp of user's last login
        role: User role (user, admin) for authorization
    """

    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    role = Column(String(20), default="user")  # user, admin

    @validates('email')
    def validate_email(self, key, email):
        """Validate email format."""
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
        return (
            f"<User(id={self.user_id}, email='{self.email}', "
            f"role='{self.role}', created_at='{self.created_at}')>"
        )

    def __str__(self) -> str:
        """Human-readable string representation."""
        return f"{self.email} ({self.role})"

    @property
    def is_admin(self) -> bool:
        """Check if user has admin role."""
        return self.role == "admin"

    @property
    def display_name(self) -> str:
        """Return display-friendly name (email prefix)."""
        return self.email.split('@')[0]

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
        self.last_login = datetime.utcnow()

    @property
    def is_new_user(self) -> bool:
        """Check if user is new (never logged in)."""
        return self.last_login is None