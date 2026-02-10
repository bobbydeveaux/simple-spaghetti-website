"""Password hashing and verification utilities using bcrypt."""

import bcrypt
from api.config import settings


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt with configurable rounds.

    Args:
        password: Plain text password

    Returns:
        Bcrypt hash string
    """
    # Generate salt with configured rounds
    salt = bcrypt.gensalt(rounds=settings.BCRYPT_ROUNDS)
    # Hash the password with the salt
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    # Return as string for storage
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against a bcrypt hash.

    Args:
        plain_password: Plain text password to verify
        hashed_password: Bcrypt hash string from storage

    Returns:
        True if password matches hash, False otherwise
    """
    return bcrypt.checkpw(
        plain_password.encode('utf-8'),
        hashed_password.encode('utf-8')
    )