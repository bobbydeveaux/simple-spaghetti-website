#!/usr/bin/env python3
"""
Test script to validate Library API implementation
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

def test_imports():
    """Test that all modules import correctly"""
    print("Testing module imports...")

    try:
        from api.data_store import BOOKS, AUTHORS, MEMBERS, LOANS
        from api.validators import validate_book, validate_member, validate_loan
        from api.auth import generate_token, verify_token, token_required
        from api.app import app
        print("✓ All modules import successfully")
        return True
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False

def test_data_store():
    """Test data store contains required data"""
    print("\nTesting data store...")

    from api.data_store import BOOKS, AUTHORS, MEMBERS, LOANS

    # Check books
    assert len(BOOKS) == 5, f"Expected 5 books, got {len(BOOKS)}"
    assert 1 in BOOKS, "Book ID 1 missing"
    assert BOOKS[1]["title"] == "The Great Gatsby"
    print("✓ Books data correct")

    # Check authors
    assert len(AUTHORS) == 3, f"Expected 3 authors, got {len(AUTHORS)}"
    assert AUTHORS[1]["name"] == "F. Scott Fitzgerald"
    print("✓ Authors data correct")

    # Check members
    assert len(MEMBERS) == 2, f"Expected 2 members, got {len(MEMBERS)}"
    assert MEMBERS[1]["email"] == "john.doe@email.com"
    print("✓ Members data correct")

    # Check loans
    assert len(LOANS) == 1, f"Expected 1 loan, got {len(LOANS)}"
    assert LOANS[1]["book_id"] == 3
    print("✓ Loans data correct")

def test_validators():
    """Test validation functions"""
    print("\nTesting validators...")

    from api.validators import validate_book, validate_member, validate_loan

    # Test book validation
    valid_book = {
        "title": "Test Book",
        "author_id": 1,
        "isbn": "9780123456789"
    }
    is_valid, error = validate_book(valid_book)
    assert is_valid, f"Valid book failed validation: {error}"
    print("✓ Book validation works")

    # Test invalid book
    invalid_book = {"title": "Test"}  # missing required fields
    is_valid, error = validate_book(invalid_book)
    assert not is_valid, "Invalid book passed validation"
    print("✓ Book validation catches errors")

    # Test member validation
    valid_member = {
        "name": "Test User",
        "email": "test@example.com",
        "password": "password123"
    }
    is_valid, error = validate_member(valid_member)
    assert is_valid, f"Valid member failed validation: {error}"
    print("✓ Member validation works")

def test_auth():
    """Test authentication functions"""
    print("\nTesting authentication...")

    from api.auth import generate_token, verify_token

    # Test token generation and verification
    member_id = 1
    token = generate_token(member_id)
    assert token, "Token generation failed"
    print("✓ Token generation works")

    # Test token verification
    payload = verify_token(token)
    assert payload, "Token verification failed"
    assert payload["member_id"] == member_id
    print("✓ Token verification works")

def test_flask_app():
    """Test Flask app creation"""
    print("\nTesting Flask application...")

    from api.app import app

    # Test app exists and is configured
    assert app, "Flask app not created"
    assert app.name == "api.app"
    print("✓ Flask app created successfully")

    # Test with test client
    with app.test_client() as client:
        # Test health endpoint
        response = client.get('/health')
        assert response.status_code == 200
        print("✓ Health endpoint works")

        # Test root endpoint
        response = client.get('/')
        assert response.status_code == 200
        print("✓ Root endpoint works")

        # Test books endpoint (GET - no auth required)
        response = client.get('/books')
        assert response.status_code == 200
        print("✓ Books list endpoint works")

        # Test specific book endpoint
        response = client.get('/books/1')
        assert response.status_code == 200
        print("✓ Book detail endpoint works")

        # Test book search
        response = client.get('/books?title=gatsby')
        assert response.status_code == 200
        print("✓ Book search works")

if __name__ == "__main__":
    print("Running Library API validation tests...\n")

    try:
        # Run all tests
        if not test_imports():
            sys.exit(1)

        test_data_store()
        test_validators()
        test_auth()
        test_flask_app()

        print("\n🎉 All tests passed! Library API implementation is working correctly.")
        print("\nAPI Endpoints implemented:")
        print("  GET  /health                 - Health check")
        print("  GET  /                       - API information")
        print("  POST /auth/login             - Member authentication")
        print("  GET  /books                  - List books (with search)")
        print("  POST /books                  - Create book (auth required)")
        print("  GET  /books/<id>             - Get book details")
        print("  PUT  /books/<id>             - Update book (auth required)")
        print("  DELETE /books/<id>           - Delete book (auth required)")

        print("\nSample authentication:")
        print("  Email: john.doe@email.com")
        print("  Password: password123")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)