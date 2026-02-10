"""
Password hashing and verification utilities.

Provides secure password hashing using bcrypt with configurable rounds.
"""

import os
from passlib.context import CryptContext
from passlib.exc import VerifyError


class PasswordHasher:
    """
    Password hashing and verification utility using bcrypt.
    """

    def __init__(self):
        # Get bcrypt rounds from environment or use secure default (12 rounds minimum)
        bcrypt_rounds = int(os.getenv("BCRYPT_ROUNDS", "12"))

        # Ensure minimum security level
        if bcrypt_rounds < 12:
            bcrypt_rounds = 12

        # Initialize passlib context with bcrypt
        self.pwd_context = CryptContext(
            schemes=["bcrypt"],
            deprecated="auto",
            bcrypt__rounds=bcrypt_rounds
        )

    def hash_password(self, password: str) -> str:
        """
        Hash a plain text password using bcrypt.

        Args:
            password: Plain text password to hash

        Returns:
            Hashed password string

        Raises:
            ValueError: If password is empty or None
        """
        if not password:
            raise ValueError("Password cannot be empty")

        try:
            return self.pwd_context.hash(password)
        except Exception as e:
            raise PasswordError(f"Failed to hash password: {str(e)}")

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """
        Verify a plain text password against its hash.

        Args:
            plain_password: Plain text password to verify
            hashed_password: Previously hashed password

        Returns:
            True if password matches, False otherwise

        Raises:
            ValueError: If either parameter is empty or None
        """
        if not plain_password or not hashed_password:
            raise ValueError("Password and hash cannot be empty")

        try:
            return self.pwd_context.verify(plain_password, hashed_password)
        except VerifyError:
            # Invalid hash format or verification failed
            return False
        except Exception as e:
            raise PasswordError(f"Failed to verify password: {str(e)}")

    def needs_update(self, hashed_password: str) -> bool:
        """
        Check if a hashed password needs to be updated due to algorithm changes.

        Args:
            hashed_password: Previously hashed password

        Returns:
            True if password needs rehashing, False otherwise
        """
        try:
            return self.pwd_context.needs_update(hashed_password)
        except Exception:
            # If we can't determine, assume it needs updating for safety
            return True


class PasswordError(Exception):
    """Custom exception for password-related errors."""
    pass


# Global password hasher instance
password_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    """
    Convenience function to hash a password.

    Args:
        password: Plain text password

    Returns:
        Hashed password string
    """
    return password_hasher.hash_password(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Convenience function to verify a password.

    Args:
        plain_password: Plain text password
        hashed_password: Hashed password

    Returns:
        True if password matches, False otherwise
    """
    return password_hasher.verify_password(plain_password, hashed_password)