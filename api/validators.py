"""
Input validation functions for the Library API

Contains validation functions for book, member, and loan data.
Returns tuples of (is_valid, error_message).
"""
import re
from typing import Dict, Tuple, Optional
from .data_store import AUTHORS, BOOKS, MEMBERS


def validate_book(data: Dict) -> Tuple[bool, Optional[str]]:
    """
    Validate book data for creation/update.

    Args:
        data: Dictionary containing book data

    Returns:
        Tuple of (is_valid, error_message)
        - is_valid: True if data is valid, False otherwise
        - error_message: None if valid, error string if invalid
    """
    if not isinstance(data, dict):
        return False, "Data must be a dictionary"

    # Check required fields
    required_fields = ["title", "author_id", "isbn"]
    for field in required_fields:
        if field not in data or not data[field]:
            return False, f"Missing required field: {field}"

    # Validate title
    title = data["title"]
    if not isinstance(title, str) or len(title.strip()) == 0:
        return False, "Title must be a non-empty string"
    if len(title) > 200:
        return False, "Title must be 200 characters or less"

    # Validate author_id
    author_id = data["author_id"]
    if not isinstance(author_id, int) or author_id <= 0:
        return False, "Author ID must be a positive integer"
    if author_id not in AUTHORS:
        return False, "Author with this ID does not exist"

    # Validate ISBN
    isbn = data["isbn"]
    if not isinstance(isbn, str):
        return False, "ISBN must be a string"

    # ISBN format validation (simple check for ISBN-10 or ISBN-13)
    isbn_clean = re.sub(r'[-\s]', '', isbn)
    if not (len(isbn_clean) == 10 or len(isbn_clean) == 13):
        return False, "ISBN must be 10 or 13 digits"
    if not isbn_clean.replace('X', '').isdigit():
        return False, "ISBN must contain only digits and optionally 'X'"

    # Validate available flag if provided
    if "available" in data:
        if not isinstance(data["available"], bool):
            return False, "Available must be a boolean value"

    return True, None


def validate_member(data: Dict) -> Tuple[bool, Optional[str]]:
    """
    Validate member data for registration/update.

    Args:
        data: Dictionary containing member data

    Returns:
        Tuple of (is_valid, error_message)
        - is_valid: True if data is valid, False otherwise
        - error_message: None if valid, error string if invalid
    """
    if not isinstance(data, dict):
        return False, "Data must be a dictionary"

    # Check required fields
    required_fields = ["name", "email"]
    for field in required_fields:
        if field not in data or not data[field]:
            return False, f"Missing required field: {field}"

    # Validate name
    name = data["name"]
    if not isinstance(name, str) or len(name.strip()) == 0:
        return False, "Name must be a non-empty string"
    if len(name) > 100:
        return False, "Name must be 100 characters or less"

    # Validate email
    email = data["email"]
    if not isinstance(email, str):
        return False, "Email must be a string"

    # Basic email format validation
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, email):
        return False, "Invalid email format"

    if len(email) > 255:
        return False, "Email must be 255 characters or less"

    # Check for duplicate email (excluding the member being updated)
    member_id = data.get("id")
    for existing_id, member in MEMBERS.items():
        if member["email"].lower() == email.lower() and existing_id != member_id:
            return False, "Email already exists"

    # Validate password if provided (for registration)
    if "password" in data:
        password = data["password"]
        if not isinstance(password, str):
            return False, "Password must be a string"
        if len(password) < 8:
            return False, "Password must be at least 8 characters long"
        if len(password) > 128:
            return False, "Password must be 128 characters or less"

    return True, None


def validate_loan(data: Dict) -> Tuple[bool, Optional[str]]:
    """
    Validate loan data for creation.

    Args:
        data: Dictionary containing loan data

    Returns:
        Tuple of (is_valid, error_message)
        - is_valid: True if data is valid, False otherwise
        - error_message: None if valid, error string if invalid
    """
    if not isinstance(data, dict):
        return False, "Data must be a dictionary"

    # Check required fields
    required_fields = ["book_id", "member_id"]
    for field in required_fields:
        if field not in data or data[field] is None:
            return False, f"Missing required field: {field}"

    # Validate book_id
    book_id = data["book_id"]
    if not isinstance(book_id, int) or book_id <= 0:
        return False, "Book ID must be a positive integer"
    if book_id not in BOOKS:
        return False, "Book with this ID does not exist"

    # Check if book is available
    book = BOOKS[book_id]
    if not book.get("available", False):
        return False, "Book is not available for borrowing"

    # Validate member_id
    member_id = data["member_id"]
    if not isinstance(member_id, int) or member_id <= 0:
        return False, "Member ID must be a positive integer"
    if member_id not in MEMBERS:
        return False, "Member with this ID does not exist"

    return True, None


def validate_loan_return(loan_id: int) -> Tuple[bool, Optional[str]]:
    """
    Validate loan return operation.

    Args:
        loan_id: ID of the loan to return

    Returns:
        Tuple of (is_valid, error_message)
        - is_valid: True if operation is valid, False otherwise
        - error_message: None if valid, error string if invalid
    """
    if not isinstance(loan_id, int) or loan_id <= 0:
        return False, "Loan ID must be a positive integer"

    if loan_id not in LOANS:
        return False, "Loan with this ID does not exist"

    from .data_store import LOANS
    loan = LOANS[loan_id]
    if loan.get("status") == "returned":
        return False, "Loan has already been returned"

    return True, None