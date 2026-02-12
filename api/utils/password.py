"""
Password hashing utilities using bcrypt.
"""
from passlib.context import CryptContext

# Create password context with bcrypt and 12 rounds (as required by PRD)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt with 12 rounds.

    Args:
        password: Plain text password to hash

    Returns:
        Hashed password string

    Raises:
        ValueError: If password is empty or None
    """
    if not password:
        raise ValueError("Password cannot be empty")

    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.

    Args:
        plain_password: Plain text password to verify
        hashed_password: Hashed password to verify against

    Returns:
        True if password matches, False otherwise

    Raises:
        ValueError: If either password is empty or None
    """
    if not plain_password or not hashed_password:
        raise ValueError("Passwords cannot be empty")

    return pwd_context.verify(plain_password, hashed_password)