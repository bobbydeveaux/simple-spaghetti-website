"""
JWT authentication utilities and decorators for the library API.
Provides token generation, validation, and password verification.
"""

import jwt
import os
from datetime import datetime, timedelta, timezone
from functools import wraps
from werkzeug.security import check_password_hash
from flask import request, jsonify, current_app
from typing import Callable, Dict, Any, Optional

# Default secret key for development (should be set via environment variable)
DEFAULT_SECRET_KEY = "library-api-secret-key-change-in-production"

def get_secret_key() -> str:
    """Get JWT secret key from environment or use default"""
    return os.getenv("SECRET_KEY", DEFAULT_SECRET_KEY)

def generate_token(member_id: int) -> str:
    """
    Generate JWT token for authenticated member.

    Args:
        member_id: ID of the authenticated member

    Returns:
        JWT token string
    """
    payload = {
        "member_id": member_id,
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),  # 1-hour expiration
        "iat": datetime.now(timezone.utc)
    }

    return jwt.encode(payload, get_secret_key(), algorithm="HS256")

def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Verify and decode JWT token.

    Args:
        token: JWT token string

    Returns:
        Decoded token payload or None if invalid
    """
    try:
        payload = jwt.decode(token, get_secret_key(), algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def token_required(f: Callable) -> Callable:
    """
    Decorator to require JWT authentication on routes.

    Extracts and validates JWT token from Authorization header.
    Adds current_member_id to request context.

    Args:
        f: Route function to protect

    Returns:
        Decorated function
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = None

        # Get token from Authorization header
        auth_header = request.headers.get("Authorization")
        if auth_header:
            try:
                # Expected format: "Bearer <token>"
                token = auth_header.split(" ")[1]
            except IndexError:
                return jsonify({"error": "Invalid authorization header format"}), 401

        if not token:
            return jsonify({"error": "Authentication token is missing"}), 401

        # Verify token
        payload = verify_token(token)
        if payload is None:
            return jsonify({"error": "Invalid or expired token"}), 401

        # Add member_id to request context for use in route handlers
        request.current_member_id = payload["member_id"]

        return f(*args, **kwargs)

    return decorated_function

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify plain password against hashed password using werkzeug.

    Args:
        plain_password: Plain text password
        hashed_password: Hashed password from database

    Returns:
        True if passwords match, False otherwise
    """
    return check_password_hash(hashed_password, plain_password)

def authenticate_member(email: str, password: str) -> Optional[int]:
    """
    Authenticate member by email and password.

    Args:
        email: Member's email address
        password: Plain text password

    Returns:
        Member ID if authentication successful, None otherwise
    """
    from api.data_store import MEMBERS

    email = email.lower().strip()

    for member_id, member in MEMBERS.items():
        if member["email"].lower() == email:
            if verify_password(password, member["password_hash"]):
                return member_id
            break  # Email found but password incorrect

    return None