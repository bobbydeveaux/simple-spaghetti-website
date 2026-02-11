"""
Input validation functions for library API data.
Validates book, member, and loan data according to business rules.
"""

import re
from datetime import datetime
from typing import Dict, Tuple, Any, Optional
from api.data_store import BOOKS, AUTHORS, MEMBERS, ELECTIONS, VOTES

def validate_book(data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Validate book data for creation or update.

    Args:
        data: Dictionary containing book data

    Returns:
        Tuple of (is_valid, error_message)
        - is_valid: True if data is valid, False otherwise
        - error_message: None if valid, error string if invalid
    """
    if not isinstance(data, dict):
        return False, "Invalid data format"

    # Check required fields
    required_fields = ["title", "author_id", "isbn"]
    for field in required_fields:
        if field not in data or not data[field]:
            return False, f"Missing required field: {field}"

    # Validate title
    title = data["title"].strip()
    if len(title) < 1 or len(title) > 200:
        return False, "Title must be between 1 and 200 characters"

    # Validate author_id
    try:
        author_id = int(data["author_id"])
        if author_id not in AUTHORS:
            return False, "Invalid author_id: author does not exist"
    except (ValueError, TypeError):
        return False, "author_id must be a valid integer"

    # Validate ISBN format (comprehensive check)
    isbn = str(data["isbn"]).strip().replace("-", "")
    if not re.match(r"^(978|979)?[\d]{9}[\dX]$", isbn):
        return False, "Invalid ISBN format"

    # Validate optional fields
    if "available_copies" in data:
        try:
            available_copies = int(data["available_copies"])
            if available_copies < 0:
                return False, "available_copies must be non-negative"
        except (ValueError, TypeError):
            return False, "available_copies must be a valid integer"

    if "total_copies" in data:
        try:
            total_copies = int(data["total_copies"])
            if total_copies < 0:
                return False, "total_copies must be non-negative"
            if "available_copies" in data and total_copies < int(data["available_copies"]):
                return False, "total_copies cannot be less than available_copies"
        except (ValueError, TypeError):
            return False, "total_copies must be a valid integer"

    return True, None

def validate_member(data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Validate member data for registration or update.

    Args:
        data: Dictionary containing member data

    Returns:
        Tuple of (is_valid, error_message)
        - is_valid: True if data is valid, False otherwise
        - error_message: None if valid, error string if invalid
    """
    if not isinstance(data, dict):
        return False, "Invalid data format"

    # Check required fields
    required_fields = ["name", "email", "password"]
    for field in required_fields:
        if field not in data or not data[field]:
            return False, f"Missing required field: {field}"

    # Validate name
    name = data["name"].strip()
    if len(name) < 2 or len(name) > 100:
        return False, "Name must be between 2 and 100 characters"

    # Validate email format
    email = data["email"].strip().lower()
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, email):
        return False, "Invalid email format"

    # Check for duplicate email (exclude current member for updates)
    exclude_id = data.get("id")
    for member_id, member in MEMBERS.items():
        if member["email"].lower() == email and member_id != exclude_id:
            return False, "Email already exists"

    # Validate password
    password = data["password"]
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"

    return True, None

def validate_loan(data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
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
        return False, "Invalid data format"

    # Check required fields
    required_fields = ["book_id", "member_id"]
    for field in required_fields:
        if field not in data or data[field] is None:
            return False, f"Missing required field: {field}"

    # Validate book_id
    try:
        book_id = int(data["book_id"])
        if book_id not in BOOKS:
            return False, "Invalid book_id: book does not exist"
    except (ValueError, TypeError):
        return False, "book_id must be a valid integer"

    # Validate member_id
    try:
        member_id = int(data["member_id"])
        if member_id not in MEMBERS:
            return False, "Invalid member_id: member does not exist"
    except (ValueError, TypeError):
        return False, "member_id must be a valid integer"

    # Check book availability
    book = BOOKS[book_id]
    if book.get("available_copies", 0) <= 0:
        return False, "Book is not available for loan"

    return True, None

def validate_book_update(book_id: int, data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Validate book data for update operations.

    Args:
        book_id: ID of the book being updated
        data: Dictionary containing update data

    Returns:
        Tuple of (is_valid, error_message)
    """
    if book_id not in BOOKS:
        return False, "Book not found"

    # For updates, we allow partial data
    if not isinstance(data, dict) or len(data) == 0:
        return False, "No update data provided"

    # Validate only provided fields
    if "title" in data:
        title = str(data["title"]).strip()
        if len(title) < 1 or len(title) > 200:
            return False, "Title must be between 1 and 200 characters"

    if "author_id" in data:
        try:
            author_id = int(data["author_id"])
            if author_id not in AUTHORS:
                return False, "Invalid author_id: author does not exist"
        except (ValueError, TypeError):
            return False, "author_id must be a valid integer"

    if "isbn" in data:
        isbn = str(data["isbn"]).strip().replace("-", "")
        if not re.match(r"^(978|979)?[\d]{9}[\dX]$", isbn):
            return False, "Invalid ISBN format"

    if "available_copies" in data:
        try:
            available_copies = int(data["available_copies"])
            if available_copies < 0:
                return False, "available_copies must be non-negative"
        except (ValueError, TypeError):
            return False, "available_copies must be a valid integer"

    if "total_copies" in data:
        try:
            total_copies = int(data["total_copies"])
            if total_copies < 0:
                return False, "total_copies must be non-negative"

            # Check against current available_copies if not being updated
            current_book = BOOKS[book_id]
            check_available = data.get("available_copies", current_book.get("available_copies", 0))
            if total_copies < check_available:
                return False, "total_copies cannot be less than available_copies"
        except (ValueError, TypeError):
            return False, "total_copies must be a valid integer"

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

    from api.data_store import LOANS
    loan = LOANS[loan_id]
    if loan.get("status") == "returned":
        return False, "Loan has already been returned"

    return True, None

def validate_election(data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Validate election data for creation.

    Args:
        data: Dictionary containing election data

    Returns:
        Tuple of (is_valid, error_message)
        - is_valid: True if data is valid, False otherwise
        - error_message: None if valid, error string if invalid
    """
    if not isinstance(data, dict):
        return False, "Invalid data format"

    # Check required fields
    required_fields = ["title", "description", "candidates", "start_date", "end_date"]
    for field in required_fields:
        if field not in data or not data[field]:
            return False, f"Missing required field: {field}"

    # Validate title
    title = data["title"].strip()
    if len(title) < 3 or len(title) > 200:
        return False, "Title must be between 3 and 200 characters"

    # Validate description
    description = data["description"].strip()
    if len(description) < 10 or len(description) > 1000:
        return False, "Description must be between 10 and 1000 characters"

    # Validate candidates
    candidates = data["candidates"]
    if not isinstance(candidates, list) or len(candidates) < 2:
        return False, "Must provide at least 2 candidates"

    for candidate in candidates:
        if not isinstance(candidate, str) or len(candidate.strip()) < 2:
            return False, "Each candidate name must be at least 2 characters"

    # Validate dates
    try:
        start_date = datetime.strptime(data["start_date"], "%Y-%m-%d")
        end_date = datetime.strptime(data["end_date"], "%Y-%m-%d")

        if end_date <= start_date:
            return False, "End date must be after start date"

        # Election should start in the future or today
        today = datetime.now().date()
        if start_date.date() < today:
            return False, "Start date cannot be in the past"

    except ValueError:
        return False, "Invalid date format. Use YYYY-MM-DD format"

    return True, None

def validate_vote(data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Validate vote data for casting a vote.

    Args:
        data: Dictionary containing vote data

    Returns:
        Tuple of (is_valid, error_message)
        - is_valid: True if data is valid, False otherwise
        - error_message: None if valid, error string if invalid
    """
    if not isinstance(data, dict):
        return False, "Invalid data format"

    # Check required fields
    required_fields = ["election_id", "member_id", "candidate"]
    for field in required_fields:
        if field not in data or data[field] is None:
            return False, f"Missing required field: {field}"

    # Validate election_id
    try:
        election_id = int(data["election_id"])
        if election_id not in ELECTIONS:
            return False, "Invalid election_id: election does not exist"
    except (ValueError, TypeError):
        return False, "election_id must be a valid integer"

    # Validate member_id
    try:
        member_id = int(data["member_id"])
        if member_id not in MEMBERS:
            return False, "Invalid member_id: member does not exist"
    except (ValueError, TypeError):
        return False, "member_id must be a valid integer"

    # Check if election is active
    election = ELECTIONS[election_id]
    if election.get("status") != "active":
        return False, "Election is not currently active"

    # Check if election voting period is valid
    try:
        today = datetime.now().date()
        start_date = datetime.strptime(election["start_date"], "%Y-%m-%d").date()
        end_date = datetime.strptime(election["end_date"], "%Y-%m-%d").date()

        if today < start_date:
            return False, "Voting has not started yet"
        if today > end_date:
            return False, "Voting period has ended"
    except (ValueError, KeyError):
        return False, "Invalid election date configuration"

    # Validate candidate
    candidate = str(data["candidate"]).strip()
    if candidate not in election.get("candidates", []):
        return False, "Invalid candidate for this election"

    # Check if member has already voted in this election
    for vote in VOTES.values():
        if vote["election_id"] == election_id and vote["member_id"] == member_id:
            return False, "Member has already voted in this election"

    return True, None

def validate_election_results(election_id: int) -> Tuple[bool, Optional[str]]:
    """
    Validate if election results can be retrieved.

    Args:
        election_id: ID of the election

    Returns:
        Tuple of (is_valid, error_message)
        - is_valid: True if results can be retrieved, False otherwise
        - error_message: None if valid, error string if invalid
    """
    if not isinstance(election_id, int) or election_id <= 0:
        return False, "Election ID must be a positive integer"

    if election_id not in ELECTIONS:
        return False, "Election with this ID does not exist"

    # Results can be viewed anytime, but include status info in the response
    return True, None