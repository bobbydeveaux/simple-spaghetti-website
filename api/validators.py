"""
Input validation functions for library API data.
Validates book, member, and loan data according to business rules.
"""

import re
from datetime import datetime
from typing import Dict, Tuple, Any, Optional
from api.data_store import BOOKS, AUTHORS, MEMBERS, BALLOTS, PROPOSALS, VOTES

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

    loan = LOANS[loan_id]
    if loan.get("status") == "returned":
        return False, "Loan has already been returned"

    return True, None

# Ballot System Validator (for elections with multiple candidates)
def validate_ballot_vote(data: Dict[str, Any], member_id: int) -> Tuple[bool, Optional[str]]:
    """
    Validate vote data for ballot submission.

    Args:
        data: Dictionary containing vote data
        member_id: ID of the member submitting the vote

    Returns:
        Tuple of (is_valid, error_message)
        - is_valid: True if data is valid, False otherwise
        - error_message: None if valid, error string if invalid
    """
    if not isinstance(data, dict):
        return False, "Invalid data format"

    # Check required fields
    required_fields = ["ballot_id", "option_id"]
    for field in required_fields:
        if field not in data or data[field] is None:
            return False, f"Missing required field: {field}"

    # Validate ballot_id
    try:
        ballot_id = int(data["ballot_id"])
        if ballot_id not in BALLOTS:
            return False, "Invalid ballot_id: ballot does not exist"
    except (ValueError, TypeError):
        return False, "ballot_id must be a valid integer"

    # Validate option_id
    try:
        option_id = int(data["option_id"])
    except (ValueError, TypeError):
        return False, "option_id must be a valid integer"

    # Get ballot and validate option belongs to ballot
    ballot = BALLOTS[ballot_id]
    valid_option_ids = [opt["id"] for opt in ballot["options"]]
    if option_id not in valid_option_ids:
        return False, "Invalid option_id for this ballot"

    # Check if ballot is active
    if ballot["status"] != "active":
        return False, "Ballot is not active"

    # Check voting period
    current_time = datetime.now().isoformat()
    if not (ballot["start_date"] <= current_time <= ballot["end_date"]):
        return False, "Voting period has expired or not yet started"

    # Check if member has already used all votes for this ballot
    existing_votes = [vote for vote in VOTES.values()
                     if vote.get("ballot_id") == ballot_id and vote["member_id"] == member_id]

    if len(existing_votes) >= ballot["max_votes_per_member"]:
        return False, "Maximum votes per member exceeded for this ballot"

    return True, None

def validate_ballot(data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Validate ballot data for creation or update.

    Args:
        data: Dictionary containing ballot data

    Returns:
        Tuple of (is_valid, error_message)
        - is_valid: True if data is valid, False otherwise
        - error_message: None if valid, error string if invalid
    """
    if not isinstance(data, dict):
        return False, "Invalid data format"

    # Check required fields
    required_fields = ["title", "description", "options", "start_date", "end_date", "max_votes_per_member"]
    for field in required_fields:
        if field not in data or data[field] is None:
            return False, f"Missing required field: {field}"

    # Validate title
    title = str(data["title"]).strip()
    if len(title) < 1 or len(title) > 200:
        return False, "Title must be between 1 and 200 characters"

    # Validate description
    description = str(data["description"]).strip()
    if len(description) < 1 or len(description) > 1000:
        return False, "Description must be between 1 and 1000 characters"

    # Validate options
    options = data["options"]
    if not isinstance(options, list) or len(options) < 2:
        return False, "At least 2 options are required"

    if len(options) > 20:
        return False, "Maximum 20 options allowed"

    # Validate each option
    option_ids = []
    for i, option in enumerate(options):
        if not isinstance(option, dict):
            return False, f"Option {i + 1} must be a dictionary"

        if "id" not in option or "title" not in option or "description" not in option:
            return False, f"Option {i + 1} must have id, title, and description fields"

        try:
            option_id = int(option["id"])
            if option_id in option_ids:
                return False, f"Duplicate option ID: {option_id}"
            option_ids.append(option_id)
        except (ValueError, TypeError):
            return False, f"Option {i + 1} ID must be a valid integer"

        option_title = str(option["title"]).strip()
        if len(option_title) < 1 or len(option_title) > 100:
            return False, f"Option {i + 1} title must be between 1 and 100 characters"

        option_desc = str(option["description"]).strip()
        if len(option_desc) > 500:
            return False, f"Option {i + 1} description must be 500 characters or less"

    # Validate dates
    try:
        start_date = datetime.fromisoformat(data["start_date"].replace('Z', '+00:00'))
        end_date = datetime.fromisoformat(data["end_date"].replace('Z', '+00:00'))

        if start_date >= end_date:
            return False, "End date must be after start date"

        # Check if start date is too far in the past (more than 1 year)
        if (datetime.now() - start_date).days > 365:
            return False, "Start date cannot be more than 1 year in the past"

    except ValueError:
        return False, "Invalid date format. Use ISO format (YYYY-MM-DDTHH:MM:SS)"

    # Validate max_votes_per_member
    try:
        max_votes = int(data["max_votes_per_member"])
        if max_votes < 1 or max_votes > len(options):
            return False, "max_votes_per_member must be between 1 and the number of options"
    except (ValueError, TypeError):
        return False, "max_votes_per_member must be a valid integer"

    return True, None

# Proposal System Validators (for yes/no decisions and simple choices)

def validate_proposal(data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Validate proposal data for creation.

    Args:
        data: Dictionary containing proposal data

    Returns:
        Tuple of (is_valid, error_message)
        - is_valid: True if data is valid, False otherwise
        - error_message: None if valid, error string if invalid
    """
    if not isinstance(data, dict):
        return False, "Invalid data format"

    # Check required fields
    required_fields = ["title", "description", "created_by", "closing_date", "options"]
    for field in required_fields:
        if field not in data or data[field] is None:
            return False, f"Missing required field: {field}"

    # Validate title
    title = str(data["title"]).strip()
    if len(title) < 3 or len(title) > 200:
        return False, "Title must be between 3 and 200 characters"

    # Validate description
    description = str(data["description"]).strip()
    if len(description) < 10 or len(description) > 2000:
        return False, "Description must be between 10 and 2000 characters"

    # Validate created_by (member_id)
    try:
        created_by = int(data["created_by"])
        if created_by not in MEMBERS:
            return False, "Invalid created_by: member does not exist"
    except (ValueError, TypeError):
        return False, "created_by must be a valid integer"

    # Validate closing_date format
    from datetime import datetime
    try:
        closing_date = str(data["closing_date"])
        datetime.strptime(closing_date, "%Y-%m-%d")

        # Check closing date is in the future
        today = datetime.now().strftime("%Y-%m-%d")
        if closing_date <= today:
            return False, "Closing date must be in the future"
    except ValueError:
        return False, "Invalid closing_date format, must be YYYY-MM-DD"

    # Validate options
    options = data["options"]
    if not isinstance(options, list) or len(options) < 2:
        return False, "Options must be a list with at least 2 choices"

    for option in options:
        if not isinstance(option, str) or len(option.strip()) < 1:
            return False, "Each option must be a non-empty string"
        if len(option.strip()) > 100:
            return False, "Each option must be 100 characters or less"

    # Validate optional fields
    if "status" in data:
        valid_statuses = ["active", "closed", "draft"]
        if data["status"] not in valid_statuses:
            return False, f"Status must be one of: {', '.join(valid_statuses)}"

    if "allow_abstain" in data:
        if not isinstance(data["allow_abstain"], bool):
            return False, "allow_abstain must be a boolean value"

    return True, None

def validate_vote(data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Validate vote data for creation.

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
    required_fields = ["proposal_id", "member_id", "vote_choice"]
    for field in required_fields:
        if field not in data or data[field] is None:
            return False, f"Missing required field: {field}"

    # Validate proposal_id
    try:
        proposal_id = int(data["proposal_id"])
    except (ValueError, TypeError):
        return False, "proposal_id must be a valid integer"

    from api.data_store import get_proposal
    proposal = get_proposal(proposal_id)
    if proposal is None:
        return False, "Invalid proposal_id: proposal does not exist"

    # Check if proposal is active
    if proposal.get("status") != "active":
        return False, "Cannot vote on inactive proposals"

    # Check if proposal is still open (not past closing date)
    from datetime import datetime
    closing_date = proposal.get("closing_date")
    if closing_date:
        try:
            close_date = datetime.strptime(closing_date, "%Y-%m-%d")
            if datetime.now() > close_date:
                return False, "Voting period has ended for this proposal"
        except ValueError:
            pass  # If date parsing fails, allow voting (better to err on permissive side)

    # Validate member_id
    try:
        member_id = int(data["member_id"])
        if member_id not in MEMBERS:
            return False, "Invalid member_id: member does not exist"
    except (ValueError, TypeError):
        return False, "member_id must be a valid integer"

    # Validate vote_choice
    vote_choice = str(data["vote_choice"]).strip().lower()
    valid_choices = [option.lower() for option in proposal.get("options", [])]

    # Add abstain option if allowed
    if proposal.get("allow_abstain", False):
        valid_choices.append("abstain")

    if vote_choice not in valid_choices:
        return False, f"Invalid vote_choice. Valid options: {', '.join(proposal.get('options', []))}" +
                      (" (or 'abstain')" if proposal.get("allow_abstain", False) else "")

    # Validate optional fields
    if "is_anonymous" in data:
        if not isinstance(data["is_anonymous"], bool):
            return False, "is_anonymous must be a boolean value"

    return True, None

def validate_proposal_update(proposal_id: int, data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Validate proposal data for update operations.

    Args:
        proposal_id: ID of the proposal being updated
        data: Dictionary containing update data

    Returns:
        Tuple of (is_valid, error_message)
    """
    from api.data_store import get_proposal

    proposal = get_proposal(proposal_id)
    if proposal is None:
        return False, "Proposal not found"

    # For updates, we allow partial data
    if not isinstance(data, dict) or len(data) == 0:
        return False, "No update data provided"

    # Don't allow updating certain fields
    readonly_fields = ["id", "created_by", "created_date"]
    for field in readonly_fields:
        if field in data:
            return False, f"Field '{field}' cannot be updated"

    # Validate provided fields
    if "title" in data:
        title = str(data["title"]).strip()
        if len(title) < 3 or len(title) > 200:
            return False, "Title must be between 3 and 200 characters"

    if "description" in data:
        description = str(data["description"]).strip()
        if len(description) < 10 or len(description) > 2000:
            return False, "Description must be between 10 and 2000 characters"

    if "closing_date" in data:
        from datetime import datetime
        try:
            closing_date = str(data["closing_date"])
            datetime.strptime(closing_date, "%Y-%m-%d")

            # Check closing date is in the future
            today = datetime.now().strftime("%Y-%m-%d")
            if closing_date <= today:
                return False, "Closing date must be in the future"
        except ValueError:
            return False, "Invalid closing_date format, must be YYYY-MM-DD"

    if "status" in data:
        valid_statuses = ["active", "closed", "draft"]
        if data["status"] not in valid_statuses:
            return False, f"Status must be one of: {', '.join(valid_statuses)}"

    if "options" in data:
        options = data["options"]
        if not isinstance(options, list) or len(options) < 2:
            return False, "Options must be a list with at least 2 choices"

        for option in options:
            if not isinstance(option, str) or len(option.strip()) < 1:
                return False, "Each option must be a non-empty string"
            if len(option.strip()) > 100:
                return False, "Each option must be 100 characters or less"

    if "allow_abstain" in data:
        if not isinstance(data["allow_abstain"], bool):
            return False, "allow_abstain must be a boolean value"

    return True, None

def validate_vote_update(vote_id: int, data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Validate vote data for update operations (mainly for changing vote choice).

    Args:
        vote_id: ID of the vote being updated
        data: Dictionary containing update data

    Returns:
        Tuple of (is_valid, error_message)
    """
    from api.data_store import VOTES, get_proposal

    if vote_id not in VOTES:
        return False, "Vote not found"

    vote = VOTES[vote_id]
    proposal = get_proposal(vote["proposal_id"])

    if proposal is None:
        return False, "Associated proposal not found"

    # Check if proposal is still active and open for voting
    if proposal.get("status") != "active":
        return False, "Cannot modify vote on inactive proposals"

    # For updates, we allow partial data
    if not isinstance(data, dict) or len(data) == 0:
        return False, "No update data provided"

    # Don't allow updating certain fields
    readonly_fields = ["id", "proposal_id", "member_id", "timestamp"]
    for field in readonly_fields:
        if field in data:
            return False, f"Field '{field}' cannot be updated"

    # Validate vote_choice if being updated
    if "vote_choice" in data:
        vote_choice = str(data["vote_choice"]).strip().lower()
        valid_choices = [option.lower() for option in proposal.get("options", [])]

        # Add abstain option if allowed
        if proposal.get("allow_abstain", False):
            valid_choices.append("abstain")

        if vote_choice not in valid_choices:
            return False, f"Invalid vote_choice. Valid options: {', '.join(proposal.get('options', []))}" +
                          (" (or 'abstain')" if proposal.get("allow_abstain", False) else "")

    if "is_anonymous" in data:
        if not isinstance(data["is_anonymous"], bool):
            return False, "is_anonymous must be a boolean value"

    return True, None