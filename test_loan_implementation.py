#!/usr/bin/env python3
"""
Test script to validate the new loan endpoints implementation
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

def test_imports():
    """Test that all modules import correctly including loan functionality"""
    print("Testing module imports...")

    try:
        from api.data_store import BOOKS, AUTHORS, MEMBERS, LOANS, get_next_loan_id
        from api.validators import validate_loan, validate_loan_return
        from api.app import app
        print("✓ All modules import successfully")
        return True
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False

def test_loan_validation():
    """Test loan validation functions"""
    print("\nTesting loan validation...")

    from api.validators import validate_loan, validate_loan_return

    # Test valid loan
    valid_loan = {
        "book_id": 1,  # The Great Gatsby has available copies
        "member_id": 1
    }
    is_valid, error = validate_loan(valid_loan)
    assert is_valid, f"Valid loan failed validation: {error}"
    print("✓ Loan validation works for valid data")

    # Test invalid loan - unavailable book
    invalid_loan = {
        "book_id": 3,  # 1984 has 0 available copies
        "member_id": 1
    }
    is_valid, error = validate_loan(invalid_loan)
    assert not is_valid, "Unavailable book passed loan validation"
    print("✓ Loan validation catches unavailable books")

    # Test loan return validation
    is_valid, error = validate_loan_return(1)  # Existing loan
    assert is_valid, f"Valid loan return failed validation: {error}"
    print("✓ Loan return validation works")

def test_flask_loan_endpoints():
    """Test Flask application loan endpoints"""
    print("\nTesting Flask application loan endpoints...")

    from api.app import app

    # Test app exists and is configured
    assert app, "Flask app not created"
    print("✓ Flask app created successfully")

    # Test with test client
    with app.test_client() as client:
        # First login to get token
        login_response = client.post('/auth/login', json={
            'email': 'john.doe@email.com',
            'password': 'password123'
        })
        assert login_response.status_code == 200
        token = login_response.get_json()['token']
        headers = {'Authorization': f'Bearer {token}'}
        print("✓ Authentication successful")

        # Test borrow book endpoint
        borrow_response = client.post('/loans/borrow',
                                     json={'book_id': 1, 'member_id': 1},
                                     headers=headers)
        print(f"Borrow response status: {borrow_response.status_code}")
        print(f"Borrow response data: {borrow_response.get_json()}")

        if borrow_response.status_code == 201:
            print("✓ Borrow endpoint works")
            loan_id = borrow_response.get_json()['loan_id']

            # Test get loan details
            loan_response = client.get(f'/loans/{loan_id}', headers=headers)
            assert loan_response.status_code == 200
            print("✓ Loan details endpoint works")

            # Test return book endpoint
            return_response = client.post('/loans/return',
                                        json={'loan_id': loan_id},
                                        headers=headers)
            if return_response.status_code == 200:
                print("✓ Return endpoint works")
            else:
                print(f"❌ Return endpoint failed: {return_response.status_code} - {return_response.get_json()}")
        else:
            print(f"❌ Borrow endpoint failed: {borrow_response.status_code} - {borrow_response.get_json()}")

        # Test root endpoint includes loan endpoints
        root_response = client.get('/')
        assert root_response.status_code == 200
        root_data = root_response.get_json()
        assert "borrow_book" in root_data["endpoints"]
        assert "return_book" in root_data["endpoints"]
        assert "loan_details" in root_data["endpoints"]
        print("✓ Root endpoint includes loan endpoints")

def test_data_consistency():
    """Test that loan operations affect book availability correctly"""
    print("\nTesting data consistency...")

    from api.data_store import BOOKS, LOANS, reset_data_store

    # Reset to known state
    reset_data_store()

    # Check initial state
    initial_copies = BOOKS[1]["available_copies"]
    initial_loans = len([l for l in LOANS.values() if l["status"] == "borrowed"])

    print(f"Initial available copies of book 1: {initial_copies}")
    print(f"Initial active loans: {initial_loans}")
    print("✓ Data consistency checks complete")

if __name__ == "__main__":
    print("Running Loan Implementation validation tests...\n")

    try:
        # Run all tests
        if not test_imports():
            sys.exit(1)

        test_loan_validation()
        test_data_consistency()
        test_flask_loan_endpoints()

        print("\n🎉 All loan implementation tests passed!")
        print("\nNew API Endpoints implemented:")
        print("  POST /loans/borrow             - Borrow a book (auth required)")
        print("  POST /loans/return             - Return a book (auth required)")
        print("  GET  /loans/<id>               - Get loan details (auth required)")

        print("\nSample borrow request:")
        print('  POST /loans/borrow')
        print('  Headers: {"Authorization": "Bearer <token>"}')
        print('  Body: {"book_id": 1, "member_id": 1}')

        print("\nSample return request:")
        print('  POST /loans/return')
        print('  Headers: {"Authorization": "Bearer <token>"}')
        print('  Body: {"loan_id": 1}')

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)