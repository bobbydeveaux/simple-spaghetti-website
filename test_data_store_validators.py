#!/usr/bin/env python3
"""
Test script for data store and validators implementation.

Tests all components to ensure they work correctly according to
the acceptance criteria.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from api.data_store import (
    BOOKS, AUTHORS, MEMBERS, LOANS,
    get_next_book_id, get_next_author_id, get_next_member_id, get_next_loan_id,
    initialize_data
)
from api.validators import validate_book, validate_member, validate_loan, validate_loan_return


def test_data_store():
    """Test data store initialization and ID generators"""
    print("Testing data store...")

    # Test that data was pre-populated
    assert len(BOOKS) == 5, f"Expected 5 books, got {len(BOOKS)}"
    assert len(AUTHORS) == 3, f"Expected 3 authors, got {len(AUTHORS)}"
    assert len(MEMBERS) == 2, f"Expected 2 members, got {len(MEMBERS)}"
    assert len(LOANS) == 1, f"Expected 1 loan, got {len(LOANS)}"

    print(f"✓ Data store contains {len(BOOKS)} books, {len(AUTHORS)} authors, {len(MEMBERS)} members, {len(LOANS)} loans")

    # Test ID generators
    next_book = get_next_book_id()
    assert next_book == 6, f"Expected next book ID to be 6, got {next_book}"

    next_author = get_next_author_id()
    assert next_author == 4, f"Expected next author ID to be 4, got {next_author}"

    next_member = get_next_member_id()
    assert next_member == 3, f"Expected next member ID to be 3, got {next_member}"

    next_loan = get_next_loan_id()
    assert next_loan == 2, f"Expected next loan ID to be 2, got {next_loan}"

    print("✓ Auto-increment ID generators work correctly")

    # Test data structure
    book1 = BOOKS[1]
    assert "id" in book1
    assert "title" in book1
    assert "author_id" in book1
    assert "isbn" in book1
    assert "available" in book1

    author1 = AUTHORS[1]
    assert "id" in author1
    assert "name" in author1
    assert "bio" in author1

    member1 = MEMBERS[1]
    assert "id" in member1
    assert "name" in member1
    assert "email" in member1
    assert "password_hash" in member1
    assert "registration_date" in member1

    loan1 = LOANS[1]
    assert "id" in loan1
    assert "book_id" in loan1
    assert "member_id" in loan1
    assert "borrow_date" in loan1
    assert "status" in loan1

    print("✓ Data structures contain all required fields")

    # Test that one book is marked as unavailable (borrowed)
    unavailable_books = [book for book in BOOKS.values() if not book["available"]]
    assert len(unavailable_books) == 1, f"Expected 1 unavailable book, got {len(unavailable_books)}"

    print("✓ Sample loan properly marks book as unavailable")


def test_book_validation():
    """Test book validation function"""
    print("Testing book validation...")

    # Valid book
    valid_book = {
        "title": "Test Book",
        "author_id": 1,
        "isbn": "978-0-123456-78-9",
        "available": True
    }
    is_valid, error = validate_book(valid_book)
    assert is_valid, f"Valid book failed validation: {error}"
    print("✓ Valid book passes validation")

    # Missing title
    invalid_book = {
        "author_id": 1,
        "isbn": "978-0-123456-78-9"
    }
    is_valid, error = validate_book(invalid_book)
    assert not is_valid, "Book without title should fail validation"
    assert "title" in error.lower(), f"Error should mention title: {error}"
    print("✓ Missing title fails validation")

    # Invalid author ID
    invalid_book = {
        "title": "Test Book",
        "author_id": 999,  # Non-existent author
        "isbn": "978-0-123456-78-9"
    }
    is_valid, error = validate_book(invalid_book)
    assert not is_valid, "Book with invalid author ID should fail validation"
    assert "author" in error.lower(), f"Error should mention author: {error}"
    print("✓ Invalid author ID fails validation")

    # Invalid ISBN format
    invalid_book = {
        "title": "Test Book",
        "author_id": 1,
        "isbn": "invalid-isbn"
    }
    is_valid, error = validate_book(invalid_book)
    assert not is_valid, "Book with invalid ISBN should fail validation"
    assert "isbn" in error.lower(), f"Error should mention ISBN: {error}"
    print("✓ Invalid ISBN fails validation")


def test_member_validation():
    """Test member validation function"""
    print("Testing member validation...")

    # Valid member
    valid_member = {
        "name": "Test User",
        "email": "test@example.com",
        "password": "password123"
    }
    is_valid, error = validate_member(valid_member)
    assert is_valid, f"Valid member failed validation: {error}"
    print("✓ Valid member passes validation")

    # Missing email
    invalid_member = {
        "name": "Test User",
        "password": "password123"
    }
    is_valid, error = validate_member(invalid_member)
    assert not is_valid, "Member without email should fail validation"
    assert "email" in error.lower(), f"Error should mention email: {error}"
    print("✓ Missing email fails validation")

    # Invalid email format
    invalid_member = {
        "name": "Test User",
        "email": "invalid-email",
        "password": "password123"
    }
    is_valid, error = validate_member(invalid_member)
    assert not is_valid, "Member with invalid email should fail validation"
    assert "email" in error.lower(), f"Error should mention email: {error}"
    print("✓ Invalid email format fails validation")

    # Duplicate email
    invalid_member = {
        "name": "Test User",
        "email": "john@example.com",  # Existing email
        "password": "password123"
    }
    is_valid, error = validate_member(invalid_member)
    assert not is_valid, "Member with duplicate email should fail validation"
    assert "email" in error.lower() and "exists" in error.lower(), f"Error should mention duplicate email: {error}"
    print("✓ Duplicate email fails validation")

    # Short password
    invalid_member = {
        "name": "Test User",
        "email": "test2@example.com",
        "password": "short"
    }
    is_valid, error = validate_member(invalid_member)
    assert not is_valid, "Member with short password should fail validation"
    assert "password" in error.lower(), f"Error should mention password: {error}"
    print("✓ Short password fails validation")


def test_loan_validation():
    """Test loan validation function"""
    print("Testing loan validation...")

    # Valid loan (book 1 should be available)
    valid_loan = {
        "book_id": 1,
        "member_id": 1
    }
    is_valid, error = validate_loan(valid_loan)
    assert is_valid, f"Valid loan failed validation: {error}"
    print("✓ Valid loan passes validation")

    # Missing book_id
    invalid_loan = {
        "member_id": 1
    }
    is_valid, error = validate_loan(invalid_loan)
    assert not is_valid, "Loan without book_id should fail validation"
    assert "book_id" in error.lower(), f"Error should mention book_id: {error}"
    print("✓ Missing book_id fails validation")

    # Non-existent book
    invalid_loan = {
        "book_id": 999,
        "member_id": 1
    }
    is_valid, error = validate_loan(invalid_loan)
    assert not is_valid, "Loan with non-existent book should fail validation"
    assert "book" in error.lower(), f"Error should mention book: {error}"
    print("✓ Non-existent book fails validation")

    # Unavailable book (book 4 is already borrowed)
    invalid_loan = {
        "book_id": 4,
        "member_id": 1
    }
    is_valid, error = validate_loan(invalid_loan)
    assert not is_valid, "Loan with unavailable book should fail validation"
    assert "available" in error.lower(), f"Error should mention availability: {error}"
    print("✓ Unavailable book fails validation")

    # Non-existent member
    invalid_loan = {
        "book_id": 1,
        "member_id": 999
    }
    is_valid, error = validate_loan(invalid_loan)
    assert not is_valid, "Loan with non-existent member should fail validation"
    assert "member" in error.lower(), f"Error should mention member: {error}"
    print("✓ Non-existent member fails validation")


def test_loan_return_validation():
    """Test loan return validation function"""
    print("Testing loan return validation...")

    # Valid return (loan 1 exists and is not returned)
    is_valid, error = validate_loan_return(1)
    assert is_valid, f"Valid loan return failed validation: {error}"
    print("✓ Valid loan return passes validation")

    # Non-existent loan
    is_valid, error = validate_loan_return(999)
    assert not is_valid, "Return of non-existent loan should fail validation"
    assert "loan" in error.lower(), f"Error should mention loan: {error}"
    print("✓ Non-existent loan return fails validation")


def main():
    """Run all tests"""
    print("Running tests for data store and validators implementation...\n")

    try:
        test_data_store()
        print()
        test_book_validation()
        print()
        test_member_validation()
        print()
        test_loan_validation()
        print()
        test_loan_return_validation()
        print()
        print("🎉 All tests passed!")

        # Print sample data for verification
        print("\nSample data verification:")
        print(f"Books: {len(BOOKS)} items")
        for book_id, book in BOOKS.items():
            author_name = AUTHORS[book["author_id"]]["name"]
            status = "Available" if book["available"] else "Borrowed"
            print(f"  - {book['title']} by {author_name} ({status})")

        print(f"\nAuthors: {len(AUTHORS)} items")
        for author in AUTHORS.values():
            print(f"  - {author['name']}")

        print(f"\nMembers: {len(MEMBERS)} items")
        for member in MEMBERS.values():
            print(f"  - {member['name']} ({member['email']})")

        print(f"\nLoans: {len(LOANS)} items")
        for loan in LOANS.values():
            book_title = BOOKS[loan["book_id"]]["title"]
            member_name = MEMBERS[loan["member_id"]]["name"]
            print(f"  - {member_name} borrowed '{book_title}' (Status: {loan['status']})")

        return True

    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)