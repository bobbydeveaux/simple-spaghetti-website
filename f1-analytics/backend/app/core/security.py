"""
Security utilities for F1 Analytics application.
Includes JWT validation, password hashing, and security checks.
"""
import os
import secrets
import hashlib
from typing import Optional
from datetime import datetime, timedelta
from fastapi import HTTPException, status
from passlib.context import CryptContext
from jose import JWTError, jwt

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT Configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))


def validate_jwt_secret() -> None:
    """
    Validate JWT secret key security.
    Raises HTTPException if the secret is insecure.
    """
    if not SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="JWT_SECRET_KEY is not configured"
        )

    # Check for development/weak secrets and template placeholders
    weak_secrets = [
        "dev-secret-key",
        "change-in-production",
        "dev_jwt_key",
        "secret",
        "key",
        "dev",
        "test",
        "development",
        "please_generate",
        "generate_with_openssl",
        "minimum_32_characters",
        "minimum_64_characters",
        "change_this",
        "f1_secure_password_2024",
        "redis_secure_password_2024",
        "flower_secure_password_2024",
        "<generate_",
        "generate_secure_",
        "generate_production_",
        "secure_24_char_password",
        "secure_16_char_password",
        "base64_64",
        "openssl_rand",
        "CHANGE_THIS_SECURE",
        "GENERATE_WITH_OPENSSL_RAND"
    ]

    secret_lower = SECRET_KEY.lower()
    for weak in weak_secrets:
        if weak in secret_lower:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="JWT secret key appears to be a development/default value. Use a cryptographically secure secret."
            )

    # Check minimum length (should be at least 32 characters for HS256)
    if len(SECRET_KEY) < 32:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="JWT secret key is too short. Minimum 32 characters required for security."
        )

    # Check entropy - should not be repetitive
    if len(set(SECRET_KEY)) < 8:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="JWT secret key has insufficient entropy. Use openssl rand -base64 64 to generate."
        )


def generate_secure_secret(length: int = 64) -> str:
    """Generate a cryptographically secure secret."""
    return secrets.token_urlsafe(length)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """
    Create a JWT access token.

    Args:
        data: The payload to encode in the token
        expires_delta: Optional expiration time delta

    Returns:
        Encoded JWT token
    """
    # Validate secret before creating tokens
    validate_jwt_secret()

    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> dict:
    """
    Verify and decode a JWT token.

    Args:
        token: The JWT token to verify

    Returns:
        Decoded token payload

    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        # Validate secret before verifying tokens
        validate_jwt_secret()

        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


def validate_environment_security() -> dict:
    """
    Validate security configuration on application startup.

    Returns:
        Dictionary with validation results
    """
    results = {
        "jwt_secret_secure": False,
        "environment": os.getenv("ENVIRONMENT", "unknown"),
        "debug_enabled": os.getenv("DEBUG", "false").lower() == "true",
        "issues": []
    }

    try:
        validate_jwt_secret()
        results["jwt_secret_secure"] = True
    except HTTPException as e:
        results["issues"].append(f"JWT Security Issue: {e.detail}")

    # Check for debug mode in production
    if results["environment"] == "production" and results["debug_enabled"]:
        results["issues"].append("Debug mode is enabled in production environment")

    # Check database URL for weak credentials
    db_url = os.getenv("DATABASE_URL", "")
    weak_db_patterns = [
        "f1password", "password123", "f1_secure_password_2024",
        "please_change", "change_this_secure_db_password",
        "CHANGE_THIS_SECURE_DB_PASSWORD", "<generate_",
        "generate_secure_", "generate_production_",
        "use_a_very_strong", "production_password_here",
        "secure_24_char_password", "production_db_password"
    ]
    for pattern in weak_db_patterns:
        if pattern.lower() in db_url.lower():
            results["issues"].append(f"Database URL contains weak/default credentials pattern: {pattern}")

    # Check Redis URL for weak credentials
    redis_url = os.getenv("REDIS_URL", "")
    weak_redis_patterns = [
        "f1redis", "redis_secure_password_2024", "please_change",
        "change_this_secure_redis_password", "CHANGE_THIS_SECURE_REDIS_PASSWORD",
        "<generate_", "generate_secure_", "generate_production_",
        "use_a_very_strong", "redis_password_here",
        "secure_24_char_password", "production_redis_password"
    ]
    for pattern in weak_redis_patterns:
        if pattern.lower() in redis_url.lower():
            results["issues"].append(f"Redis URL contains weak/default credentials pattern: {pattern}")

    return results