#!/usr/bin/env python3
"""
Test script to validate data models and schemas
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from api.models.user import User, RegisterRequest, RegisterResponse, LoginRequest
from api.models.token import TokenResponse, RefreshRequest, ProtectedResponse
import json


def test_user_model():
    """Test User dataclass"""
    print("Testing User dataclass...")
    user = User(
        email="test@example.com",
        hashed_password="$2b$12$hashedpassword",
        username="testuser"
    )

    assert user.email == "test@example.com"
    assert user.username == "testuser"
    assert user.hashed_password == "$2b$12$hashedpassword"
    assert len(user.id) == 36  # UUID4 length
    print("✓ User dataclass works correctly")


def test_register_request():
    """Test RegisterRequest schema"""
    print("\nTesting RegisterRequest schema...")

    # Valid request
    valid_request = RegisterRequest(
        email="test@example.com",
        password="password123",
        username="testuser"
    )
    assert valid_request.email == "test@example.com"
    assert valid_request.password == "password123"
    assert valid_request.username == "testuser"
    print("✓ Valid RegisterRequest works")

    # Test validation - short password
    try:
        RegisterRequest(
            email="test@example.com",
            password="short",
            username="testuser"
        )
        assert False, "Should have failed validation"
    except Exception as e:
        print("✓ Short password validation works")

    # Test validation - invalid email
    try:
        RegisterRequest(
            email="invalid-email",
            password="password123",
            username="testuser"
        )
        assert False, "Should have failed validation"
    except Exception as e:
        print("✓ Email validation works")


def test_login_request():
    """Test LoginRequest schema"""
    print("\nTesting LoginRequest schema...")
    login_req = LoginRequest(
        email="test@example.com",
        password="password123"
    )
    assert login_req.email == "test@example.com"
    assert login_req.password == "password123"
    print("✓ LoginRequest works correctly")


def test_register_response():
    """Test RegisterResponse schema"""
    print("\nTesting RegisterResponse schema...")
    response = RegisterResponse(
        message="User registered successfully",
        email="test@example.com",
        username="testuser",
        user_id="123e4567-e89b-12d3-a456-426614174000"
    )
    assert response.message == "User registered successfully"
    assert response.email == "test@example.com"
    assert response.username == "testuser"
    assert response.user_id == "123e4567-e89b-12d3-a456-426614174000"
    print("✓ RegisterResponse works correctly")


def test_token_response():
    """Test TokenResponse schema"""
    print("\nTesting TokenResponse schema...")
    token_resp = TokenResponse(
        access_token="eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
        refresh_token="eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
    )
    assert token_resp.access_token.startswith("eyJ")
    assert token_resp.refresh_token.startswith("eyJ")
    assert token_resp.token_type == "bearer"
    print("✓ TokenResponse works correctly")


def test_refresh_request():
    """Test RefreshRequest schema"""
    print("\nTesting RefreshRequest schema...")
    refresh_req = RefreshRequest(
        refresh_token="eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
    )
    assert refresh_req.refresh_token.startswith("eyJ")
    print("✓ RefreshRequest works correctly")


def test_protected_response():
    """Test ProtectedResponse schema"""
    print("\nTesting ProtectedResponse schema...")
    protected_resp = ProtectedResponse(
        message="Access granted to protected resource",
        user="test@example.com"
    )
    assert protected_resp.message == "Access granted to protected resource"
    assert protected_resp.user == "test@example.com"
    print("✓ ProtectedResponse works correctly")


def test_json_serialization():
    """Test JSON serialization of all models"""
    print("\nTesting JSON serialization...")

    # Test RegisterRequest
    register_req = RegisterRequest(
        email="test@example.com",
        password="password123",
        username="testuser"
    )
    register_json = register_req.model_dump_json()
    assert "test@example.com" in register_json
    print("✓ RegisterRequest JSON serialization works")

    # Test TokenResponse
    token_resp = TokenResponse(
        access_token="access_token_here",
        refresh_token="refresh_token_here"
    )
    token_json = token_resp.model_dump_json()
    assert "bearer" in token_json
    print("✓ TokenResponse JSON serialization works")


if __name__ == "__main__":
    print("Running model validation tests...\n")

    try:
        test_user_model()
        test_register_request()
        test_login_request()
        test_register_response()
        test_token_response()
        test_refresh_request()
        test_protected_response()
        test_json_serialization()

        print("\n🎉 All tests passed! Data models and schemas are working correctly.")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)