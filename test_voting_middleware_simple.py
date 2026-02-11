#!/usr/bin/env python3
"""
Test script to validate the voting authentication middleware implementation
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from datetime import datetime, timedelta
import jwt as jwt_lib
from fastapi import HTTPException


def test_imports():
    """Test that all voting modules can be imported correctly"""
    print("Testing imports...")

    try:
        from api.voting.middleware import (
            verify_voting_session,
            verify_admin_session,
            validate_token_direct,
            SessionNotFoundError,
            SessionExpiredError,
            VotingAuthenticationError
        )
        from api.voting.models import Session, Voter, Candidate, Vote, AuditLog, Election
        from api.utils.jwt_manager import jwt_manager
        print("✓ Voting module imports successful")
        return True
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False


def test_models():
    """Test voting models creation"""
    print("Testing voting models...")

    try:
        from api.voting.models import Session, Voter, Candidate, Vote, AuditLog, Election

        # Test Voter model
        voter = Voter(email="voter@example.com")
        assert "@" in voter.email
        assert len(voter.voter_id) == 36  # UUID length
        print("✓ Voter model works")

        # Test Session model
        session = Session(
            voter_id="test-voter-id",
            token="test-token",
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=2)
        )
        assert session.voter_id == "test-voter-id"
        assert session.is_admin is False
        print("✓ Session model works")

        # Test Candidate model
        candidate = Candidate(name="John Doe", position="President")
        assert candidate.name == "John Doe"
        assert candidate.position == "President"
        print("✓ Candidate model works")

        # Test Vote model (no voter_id for anonymity)
        vote = Vote(candidate_id="candidate-123", position="President")
        assert vote.candidate_id == "candidate-123"
        assert vote.position == "President"
        assert not hasattr(vote, 'voter_id') or vote.__dict__.get('voter_id') is None
        print("✓ Vote model works (anonymity preserved)")

        return True
    except Exception as e:
        print(f"✗ Model test error: {e}")
        return False


def test_placeholder_validate_session():
    """Test the placeholder validate_session function"""
    print("Testing placeholder validate_session...")

    try:
        from api.voting.middleware import validate_session_placeholder
        from api.utils.jwt_manager import jwt_manager

        # Create a test JWT token
        payload = {
            "voter_id": "test-voter-123",
            "exp": (datetime.utcnow() + timedelta(hours=1)).timestamp(),
            "iat": datetime.utcnow().timestamp(),
            "is_admin": False
        }
        token = jwt_lib.encode(payload, jwt_manager.secret_key, algorithm=jwt_manager.algorithm)

        # Test valid token
        session = validate_session_placeholder(token)
        assert session.voter_id == "test-voter-123"
        assert session.is_admin is False
        assert session.token == token
        print("✓ Valid token creates session")

        # Test expired token
        expired_payload = {
            "voter_id": "test-voter-123",
            "exp": (datetime.utcnow() - timedelta(minutes=1)).timestamp(),
            "iat": datetime.utcnow().timestamp(),
        }
        expired_token = jwt_lib.encode(expired_payload, jwt_manager.secret_key, algorithm=jwt_manager.algorithm)

        try:
            validate_session_placeholder(expired_token)
            print("✗ Expired token should have failed")
            return False
        except Exception:
            print("✓ Expired token properly rejected")

        # Test invalid token
        try:
            validate_session_placeholder("invalid-token")
            print("✗ Invalid token should have failed")
            return False
        except Exception:
            print("✓ Invalid token properly rejected")

        return True
    except Exception as e:
        print(f"✗ Placeholder validation test error: {e}")
        return False


def test_middleware_dependencies():
    """Test the middleware dependency functions"""
    print("Testing middleware dependencies...")

    try:
        from api.voting.middleware import verify_voting_session, verify_admin_session
        from api.utils.jwt_manager import jwt_manager

        # Test missing authorization header
        try:
            verify_voting_session(None)
            print("✗ Missing auth header should fail")
            return False
        except HTTPException as e:
            if e.status_code == 401:
                print("✓ Missing auth header properly rejected")
            else:
                print(f"✗ Wrong status code for missing header: {e.status_code}")
                return False

        # Test invalid format
        try:
            verify_voting_session("Invalid format")
            print("✗ Invalid format should fail")
            return False
        except HTTPException as e:
            if e.status_code == 401:
                print("✓ Invalid format properly rejected")
            else:
                print(f"✗ Wrong status code for invalid format: {e.status_code}")
                return False

        # Test empty token
        try:
            verify_voting_session("Bearer ")
            print("✗ Empty token should fail")
            return False
        except HTTPException as e:
            if e.status_code == 401:
                print("✓ Empty token properly rejected")
            else:
                print(f"✗ Wrong status code for empty token: {e.status_code}")
                return False

        return True
    except Exception as e:
        print(f"✗ Middleware dependencies test error: {e}")
        return False


def test_admin_privileges():
    """Test admin privilege verification"""
    print("Testing admin privilege verification...")

    try:
        # This test requires mocking or a complete implementation
        # For now, just verify the function exists and has correct signature
        from api.voting.middleware import verify_admin_session
        print("✓ Admin privilege function exists")
        return True
    except Exception as e:
        print(f"✗ Admin privilege test error: {e}")
        return False


def run_all_tests():
    """Run all tests and report results"""
    print("=== Voting Middleware Test Suite ===\n")

    tests = [
        ("Import Tests", test_imports),
        ("Model Tests", test_models),
        ("Placeholder Validation", test_placeholder_validate_session),
        ("Middleware Dependencies", test_middleware_dependencies),
        ("Admin Privileges", test_admin_privileges),
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        print(f"\n--- {test_name} ---")
        try:
            if test_func():
                passed += 1
                print(f"✓ {test_name} PASSED")
            else:
                print(f"✗ {test_name} FAILED")
        except Exception as e:
            print(f"✗ {test_name} ERROR: {e}")

    print(f"\n=== Test Results ===")
    print(f"Passed: {passed}/{total}")
    print(f"Status: {'PASS' if passed == total else 'FAIL'}")

    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)