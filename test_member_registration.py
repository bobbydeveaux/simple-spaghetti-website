#!/usr/bin/env python3
"""
Test script to validate member registration endpoint implementation
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

def test_member_registration():
    """Test member registration endpoint"""
    print("Testing member registration endpoint...")

    from api.app import app
    from api.data_store import MEMBERS

    # Test with test client
    with app.test_client() as client:
        # Test successful member registration
        new_member_data = {
            "name": "Test User",
            "email": "test.user@example.com",
            "password": "password123"
        }

        response = client.post('/members', json=new_member_data)
        assert response.status_code == 201, f"Expected 201, got {response.status_code}"

        response_data = response.get_json()
        assert "id" in response_data, "Response should contain member ID"
        assert response_data["name"] == "Test User"
        assert response_data["email"] == "test.user@example.com"
        assert response_data["registration_date"], "Registration date should be set"
        assert "password" not in response_data, "Password should not be in response"
        assert "password_hash" not in response_data, "Password hash should not be in response"
        print("✓ Member registration works")

        # Verify member was added to data store
        new_member_id = response_data["id"]
        assert new_member_id in MEMBERS, "Member should be added to data store"
        stored_member = MEMBERS[new_member_id]
        assert stored_member["name"] == "Test User"
        assert stored_member["email"] == "test.user@example.com"
        assert "password_hash" in stored_member, "Password should be hashed and stored"
        print("✓ Member data correctly stored")

        # Test duplicate email
        duplicate_data = {
            "name": "Another User",
            "email": "test.user@example.com",  # Same email
            "password": "password456"
        }

        response = client.post('/members', json=duplicate_data)
        assert response.status_code == 400, "Duplicate email should return 400"
        error_data = response.get_json()
        assert "Email already exists" in error_data.get("error", "")
        print("✓ Duplicate email validation works")

        # Test missing required fields
        incomplete_data = {"name": "Incomplete User"}

        response = client.post('/members', json=incomplete_data)
        assert response.status_code == 400, "Missing fields should return 400"
        error_data = response.get_json()
        assert "error" in error_data
        print("✓ Missing field validation works")

        # Test invalid email format
        invalid_email_data = {
            "name": "Invalid Email User",
            "email": "not-an-email",
            "password": "password123"
        }

        response = client.post('/members', json=invalid_email_data)
        assert response.status_code == 400, "Invalid email should return 400"
        error_data = response.get_json()
        assert "Invalid email format" in error_data.get("error", "")
        print("✓ Email format validation works")

        # Test password too short
        short_password_data = {
            "name": "Short Password User",
            "email": "short@example.com",
            "password": "short"
        }

        response = client.post('/members', json=short_password_data)
        assert response.status_code == 400, "Short password should return 400"
        error_data = response.get_json()
        assert "Password must be at least 8 characters" in error_data.get("error", "")
        print("✓ Password length validation works")

def test_member_login_after_registration():
    """Test that registered member can login"""
    print("\nTesting member login after registration...")

    from api.app import app

    with app.test_client() as client:
        # First register a member
        new_member_data = {
            "name": "Login Test User",
            "email": "login.test@example.com",
            "password": "loginpassword123"
        }

        response = client.post('/members', json=new_member_data)
        assert response.status_code == 201, "Member registration should succeed"
        print("✓ Member registered successfully")

        # Then try to login with the same credentials
        login_data = {
            "email": "login.test@example.com",
            "password": "loginpassword123"
        }

        response = client.post('/auth/login', json=login_data)
        assert response.status_code == 200, f"Login should succeed, got {response.status_code}"

        response_data = response.get_json()
        assert "token" in response_data, "Login should return JWT token"
        assert "member_id" in response_data, "Login should return member ID"
        print("✓ Registered member can login successfully")

def test_api_root_documentation():
    """Test that root endpoint includes member registration"""
    print("\nTesting API documentation...")

    from api.app import app

    with app.test_client() as client:
        response = client.get('/')
        assert response.status_code == 200

        response_data = response.get_json()
        assert "endpoints" in response_data
        assert "member_registration" in response_data["endpoints"]
        assert response_data["endpoints"]["member_registration"] == "/members"
        print("✓ API documentation includes member registration")

if __name__ == "__main__":
    print("Running member registration tests...\n")

    try:
        test_member_registration()
        test_member_login_after_registration()
        test_api_root_documentation()

        print("\n🎉 All member registration tests passed!")
        print("\nNew endpoint implemented:")
        print("  POST /members                - Member registration")
        print("\nExample registration request:")
        print('  POST /members')
        print('  {')
        print('    "name": "John Smith",')
        print('    "email": "john.smith@example.com",')
        print('    "password": "securepassword123"')
        print('  }')

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)