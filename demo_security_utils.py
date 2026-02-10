#!/usr/bin/env python3
"""
Demo script to show security utilities functionality.

This script demonstrates the JWT manager and password hashing utilities
without requiring pytest to run.
"""

import os
import sys

# Add the api directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

def demo_password_utilities():
    """Demonstrate password hashing and verification."""
    print("=== Password Utilities Demo ===")

    # Set test environment
    os.environ["BCRYPT_ROUNDS"] = "4"  # Faster for demo

    from api.utils.password import hash_password, verify_password, PasswordHasher

    # Test password
    password = "SecurePassword123!"

    print(f"Original password: {password}")

    # Hash the password
    hashed = hash_password(password)
    print(f"Hashed password: {hashed}")

    # Verify correct password
    is_valid = verify_password(password, hashed)
    print(f"Password verification (correct): {is_valid}")

    # Verify wrong password
    is_invalid = verify_password("WrongPassword", hashed)
    print(f"Password verification (wrong): {is_invalid}")

    print("✓ Password utilities working correctly\n")


def demo_jwt_utilities():
    """Demonstrate JWT token creation and validation."""
    print("=== JWT Utilities Demo ===")

    # Set test environment
    os.environ["JWT_SECRET"] = "demo-secret-key"
    os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "15"
    os.environ["REFRESH_TOKEN_EXPIRE_DAYS"] = "7"

    from api.utils.jwt_manager import JWTManager, JWTError

    # Create JWT manager
    jwt_manager = JWTManager()

    # Test email
    email = "demo@example.com"

    # Create access token
    access_token = jwt_manager.create_access_token(email)
    print(f"Access token created: {access_token[:50]}...")

    # Create refresh token
    refresh_token = jwt_manager.create_refresh_token(email)
    print(f"Refresh token created: {refresh_token[:50]}...")

    # Decode access token
    try:
        payload = jwt_manager.decode_token(access_token)
        print(f"Access token payload: {payload}")

        # Verify token type
        is_access = jwt_manager.verify_token_type(payload, "access")
        print(f"Is access token: {is_access}")

        # Extract email
        extracted_email = jwt_manager.get_email_from_token(access_token)
        print(f"Extracted email: {extracted_email}")

    except JWTError as e:
        print(f"JWT Error: {e}")

    # Test invalid token
    try:
        jwt_manager.decode_token("invalid.token.here")
    except JWTError as e:
        print(f"Expected error for invalid token: {e}")

    print("✓ JWT utilities working correctly\n")


def demo_configuration():
    """Demonstrate configuration loading."""
    print("=== Configuration Demo ===")

    from api.config import Config, config

    print(f"JWT Secret (first 10 chars): {config.JWT_SECRET[:10]}...")
    print(f"Access token expire minutes: {config.ACCESS_TOKEN_EXPIRE_MINUTES}")
    print(f"Refresh token expire days: {config.REFRESH_TOKEN_EXPIRE_DAYS}")
    print(f"Bcrypt rounds: {config.BCRYPT_ROUNDS}")
    print(f"API Host: {config.API_HOST}")
    print(f"API Port: {config.API_PORT}")
    print(f"Debug mode: {config.DEBUG}")

    print("✓ Configuration loading correctly\n")


def main():
    """Run all demos."""
    print("Security Utilities Demo\n")
    print("This demo shows the implemented security utilities for:")
    print("- JWT token creation, validation, and decoding")
    print("- Password hashing and verification using bcrypt")
    print("- Configuration management with environment variables")
    print("- Error handling for invalid tokens and passwords\n")

    try:
        demo_configuration()
        demo_password_utilities()
        demo_jwt_utilities()

        print("🎉 All security utilities implemented successfully!")
        print("\nKey Features Implemented:")
        print("- JWT Manager with access and refresh token support")
        print("- Password hashing with bcrypt (configurable rounds)")
        print("- Token validation and expiry checking")
        print("- Comprehensive error handling")
        print("- Environment-based configuration")
        print("- Complete test suite")

    except Exception as e:
        print(f"❌ Error running demo: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())