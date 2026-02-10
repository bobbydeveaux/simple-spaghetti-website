#!/usr/bin/env python3
"""
Test script to validate the JWT authentication and password utilities implementation
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

# Test imports
def test_imports():
    """Test that all modules can be imported correctly"""
    print("Testing imports...")

    try:
        # Test utility imports
        from api.utils.jwt_manager import jwt_manager
        from api.utils.password import hash_password, verify_password
        print("✓ Utils imports successful")

        # Test service imports
        from api.services.user_repository import user_repository
        from api.services.auth_service import auth_service
        print("✓ Services imports successful")

        # Test middleware imports
        from api.middleware.auth_middleware import verify_access_token
        print("✓ Middleware imports successful")

        # Test route imports
        from api.routes.auth import router as auth_router
        from api.routes.protected import router as protected_router
        print("✓ Routes imports successful")

        # Test main app import
        from api.main import app
        print("✓ Main app import successful")

        # Test config import
        from api.config import settings
        print("✓ Config import successful")

        return True

    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


def test_password_utilities():
    """Test password hashing and verification"""
    print("\nTesting password utilities...")

    try:
        from api.utils.password import hash_password, verify_password

        # Test password hashing
        password = "testpassword123"
        hashed = hash_password(password)

        # Verify hash format
        assert hashed.startswith("$2b$"), "Hash should use bcrypt format"
        assert len(hashed) > 50, "Hash should be substantial length"
        print("✓ Password hashing works")

        # Test password verification
        assert verify_password(password, hashed), "Password verification should succeed"
        assert not verify_password("wrongpassword", hashed), "Wrong password should fail"
        print("✓ Password verification works")

        return True

    except Exception as e:
        print(f"❌ Password utilities error: {e}")
        return False


def test_jwt_utilities():
    """Test JWT token creation and validation"""
    print("\nTesting JWT utilities...")

    try:
        from api.utils.jwt_manager import jwt_manager
        import jwt

        # Test token creation
        email = "test@example.com"
        access_token = jwt_manager.create_access_token(email)
        refresh_token = jwt_manager.create_refresh_token(email)

        assert access_token, "Access token should be created"
        assert refresh_token, "Refresh token should be created"
        assert access_token != refresh_token, "Tokens should be different"
        print("✓ Token creation works")

        # Test token decoding
        access_payload = jwt_manager.decode_token(access_token)
        refresh_payload = jwt_manager.decode_token(refresh_token)

        assert access_payload["email"] == email, "Email should be in payload"
        assert access_payload["type"] == "access", "Should be access token type"
        assert refresh_payload["type"] == "refresh", "Should be refresh token type"
        print("✓ Token decoding works")

        # Test token type verification
        assert jwt_manager.verify_token_type(access_payload, "access"), "Access token type should verify"
        assert jwt_manager.verify_token_type(refresh_payload, "refresh"), "Refresh token type should verify"
        assert not jwt_manager.verify_token_type(access_payload, "refresh"), "Wrong type should fail"
        print("✓ Token type verification works")

        return True

    except Exception as e:
        print(f"❌ JWT utilities error: {e}")
        return False


def test_user_repository():
    """Test user repository operations"""
    print("\nTesting user repository...")

    try:
        from api.services.user_repository import user_repository
        from api.models.user import User
        import uuid

        # Clear repository for clean test
        user_repository.clear_all_users()

        # Create test user
        user = User(
            email="test@example.com",
            hashed_password="hashedpass",
            username="testuser",
            id=uuid.uuid4()
        )

        # Test user addition
        user_repository.add_user(user)
        assert user_repository.user_exists("test@example.com"), "User should exist after addition"
        print("✓ User addition works")

        # Test user retrieval
        retrieved_user = user_repository.get_user_by_email("test@example.com")
        assert retrieved_user is not None, "User should be retrievable"
        assert retrieved_user.email == user.email, "Retrieved user should match"
        print("✓ User retrieval works")

        # Test duplicate prevention
        try:
            user_repository.add_user(user)
            assert False, "Duplicate user should raise error"
        except ValueError:
            print("✓ Duplicate prevention works")

        return True

    except Exception as e:
        print(f"❌ User repository error: {e}")
        return False


def test_auth_service():
    """Test authentication service operations"""
    print("\nTesting authentication service...")

    try:
        from api.services.auth_service import auth_service
        from api.services.user_repository import user_repository

        # Clear repository for clean test
        user_repository.clear_all_users()

        # Test user registration
        email = "newuser@example.com"
        password = "password123"
        username = "newuser"

        user = auth_service.register_user(email, password, username)
        assert user.email == email, "User email should match"
        assert user.username == username, "Username should match"
        assert user.hashed_password != password, "Password should be hashed"
        print("✓ User registration works")

        # Test authentication
        auth_user = auth_service.authenticate_user(email, password)
        assert auth_user is not None, "Authentication should succeed"
        assert auth_user.email == email, "Authenticated user should match"

        # Test wrong password
        wrong_auth = auth_service.authenticate_user(email, "wrongpassword")
        assert wrong_auth is None, "Wrong password should fail"
        print("✓ User authentication works")

        # Test token generation
        tokens = auth_service.generate_tokens(email)
        assert "access_token" in tokens, "Access token should be generated"
        assert "refresh_token" in tokens, "Refresh token should be generated"
        print("✓ Token generation works")

        # Test token refresh
        new_access_token = auth_service.refresh_access_token(tokens["refresh_token"])
        assert new_access_token, "New access token should be generated"
        assert new_access_token != tokens["access_token"], "New token should be different"
        print("✓ Token refresh works")

        return True

    except Exception as e:
        print(f"❌ Auth service error: {e}")
        return False


def test_api_structure():
    """Test API structure and configuration"""
    print("\nTesting API structure...")

    try:
        from api.main import app
        from api.config import settings

        # Test app configuration
        assert app.title == "Python Authentication API", "App title should be correct"
        assert settings.JWT_ALGORITHM == "HS256", "JWT algorithm should be HS256"
        assert settings.ACCESS_TOKEN_EXPIRE_MINUTES == 15, "Access token expiry should be 15 minutes"
        print("✓ API configuration works")

        # Test routes are registered
        routes = [route.path for route in app.routes]
        expected_routes = ["/auth/register", "/auth/login", "/auth/refresh", "/protected/"]

        for expected_route in expected_routes:
            assert any(expected_route in route for route in routes), f"Route {expected_route} should be registered"
        print("✓ API routes registered correctly")

        return True

    except Exception as e:
        print(f"❌ API structure error: {e}")
        return False


if __name__ == "__main__":
    print("Running authentication implementation tests...\n")

    tests = [
        test_imports,
        test_password_utilities,
        test_jwt_utilities,
        test_user_repository,
        test_auth_service,
        test_api_structure,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with error: {e}")
            failed += 1

    print(f"\nTest Results: {passed} passed, {failed} failed")

    if failed == 0:
        print("🎉 All tests passed! JWT authentication and password utilities are implemented correctly.")
        sys.exit(0)
    else:
        print("❌ Some tests failed. Please check the implementation.")
        sys.exit(1)