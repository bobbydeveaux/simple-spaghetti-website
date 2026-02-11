"""
In-memory data store with dictionaries for books, authors, members, loans, and PTA voting data.
Pre-populated with sample data for development and testing.
Includes thread-safe operations for concurrent access to voting data.
"""

import threading
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash

# Auto-increment ID generators
BOOK_ID_COUNTER = 5
AUTHOR_ID_COUNTER = 3
MEMBER_ID_COUNTER = 2
LOAN_ID_COUNTER = 1
BALLOT_ID_COUNTER = 2
PROPOSAL_ID_COUNTER = 2
VOTE_ID_COUNTER = 3

# Thread-safety locks for concurrent access
DATA_LOCK = threading.RLock()
PROPOSAL_LOCK = threading.RLock()
VOTE_LOCK = threading.RLock()

# In-memory data dictionaries
BOOKS = {
    1: {
        "id": 1,
        "title": "The Great Gatsby",
        "author_id": 1,
        "isbn": "978-0-7432-7356-5",
        "available_copies": 3,
        "total_copies": 3
    },
    2: {
        "id": 2,
        "title": "To Kill a Mockingbird",
        "author_id": 2,
        "isbn": "978-0-06-112008-4",
        "available_copies": 2,
        "total_copies": 2
    },
    3: {
        "id": 3,
        "title": "1984",
        "author_id": 3,
        "isbn": "978-0-452-28423-4",
        "available_copies": 0,
        "total_copies": 1
    },
    4: {
        "id": 4,
        "title": "Pride and Prejudice",
        "author_id": 2,
        "isbn": "978-0-14-143951-8",
        "available_copies": 1,
        "total_copies": 1
    },
    5: {
        "id": 5,
        "title": "The Catcher in the Rye",
        "author_id": 1,
        "isbn": "978-0-316-76948-0",
        "available_copies": 2,
        "total_copies": 2
    }
}

AUTHORS = {
    1: {
        "id": 1,
        "name": "F. Scott Fitzgerald",
        "bio": "American novelist and short story writer, widely regarded as one of the greatest American writers of the 20th century."
    },
    2: {
        "id": 2,
        "name": "Harper Lee",
        "bio": "American novelist best known for her 1960 novel To Kill a Mockingbird, which won the Pulitzer Prize for Fiction."
    },
    3: {
        "id": 3,
        "name": "George Orwell",
        "bio": "English novelist, essayist, journalist, and critic best known for his dystopian novel 1984 and allegorical novella Animal Farm."
    }
}

MEMBERS = {
    1: {
        "id": 1,
        "name": "John Doe",
        "email": "john.doe@email.com",
        "password_hash": generate_password_hash("password123"),
        "registration_date": "2024-01-15"
    },
    2: {
        "id": 2,
        "name": "Jane Smith",
        "email": "jane.smith@email.com",
        "password_hash": generate_password_hash("securepass456"),
        "registration_date": "2024-01-20"
    }
}

LOANS = {
    1: {
        "id": 1,
        "book_id": 3,
        "member_id": 1,
        "borrow_date": "2024-02-01",
        "return_date": None,
        "status": "borrowed"
    }
}

# Ballot-based voting system (for elections with multiple candidate options)
BALLOTS = {
    1: {
        "id": 1,
        "title": "PTA Board Election 2024",
        "description": "Annual election for PTA board positions including President, Vice President, Secretary, and Treasurer.",
        "options": [
            {"id": 1, "title": "President: Sarah Johnson", "description": "Parent volunteer with 5 years PTA experience"},
            {"id": 2, "title": "President: Michael Chen", "description": "Local business owner and education advocate"},
            {"id": 3, "title": "Vice President: Lisa Rodriguez", "description": "Former teacher and current parent liaison"},
            {"id": 4, "title": "Secretary: David Kim", "description": "Organization specialist with nonprofit background"},
            {"id": 5, "title": "Treasurer: Amanda Williams", "description": "CPA with financial management expertise"}
        ],
        "start_date": "2024-03-01T00:00:00",
        "end_date": "2024-03-15T23:59:59",
        "max_votes_per_member": 3,
        "status": "active"
    },
    2: {
        "id": 2,
        "title": "School Fundraising Initiative",
        "description": "Choose the primary fundraising activity for this school year.",
        "options": [
            {"id": 6, "title": "Spring Carnival", "description": "Traditional carnival with games and food booths"},
            {"id": 7, "title": "Silent Auction", "description": "Online auction featuring donated items and services"},
            {"id": 8, "title": "Fun Run", "description": "Community fun run with sponsorship opportunities"}
        ],
        "start_date": "2024-02-15T00:00:00",
        "end_date": "2024-02-28T23:59:59",
        "max_votes_per_member": 1,
        "status": "active"
    }
}

# Proposal-based voting system (for yes/no decisions and simple choices)
PROPOSALS = {
    1: {
        "id": 1,
        "title": "Increase School Library Budget",
        "description": "Proposal to increase the annual library budget by $5,000 to purchase new books and educational materials.",
        "created_by": 1,  # member_id
        "created_date": "2024-02-10",
        "closing_date": "2024-02-24",
        "status": "active",  # active, closed, draft
        "options": ["yes", "no"],
        "allow_abstain": True
    },
    2: {
        "id": 2,
        "title": "New Playground Equipment Installation",
        "description": "Vote on installing new playground equipment including swing sets, slides, and safety surfacing. Total estimated cost: $15,000.",
        "created_by": 2,  # member_id
        "created_date": "2024-02-11",
        "closing_date": "2024-02-25",
        "status": "active",
        "options": ["approve", "reject"],
        "allow_abstain": False
    }
}

VOTES = {
    1: {
        "id": 1,
        "ballot_id": 2,  # Ballot vote
        "member_id": 1,
        "option_id": 6,
        "timestamp": "2024-02-16T10:30:00"
    },
    2: {
        "id": 2,
        "proposal_id": 1,  # Proposal vote
        "member_id": 1,
        "vote_choice": "yes",
        "timestamp": "2024-02-11T10:30:00",
        "is_anonymous": False
    },
    3: {
        "id": 3,
        "proposal_id": 1,
        "member_id": 2,
        "vote_choice": "no",
        "timestamp": "2024-02-11T11:15:00",
        "is_anonymous": False
    },
    4: {
        "id": 4,
        "proposal_id": 2,
        "member_id": 1,
        "vote_choice": "approve",
        "timestamp": "2024-02-11T14:20:00",
        "is_anonymous": False
    }
}

def get_next_book_id():
    """Generate next auto-increment ID for books"""
    global BOOK_ID_COUNTER
    BOOK_ID_COUNTER += 1
    return BOOK_ID_COUNTER

def get_next_author_id():
    """Generate next auto-increment ID for authors"""
    global AUTHOR_ID_COUNTER
    AUTHOR_ID_COUNTER += 1
    return AUTHOR_ID_COUNTER

def get_next_member_id():
    """Generate next auto-increment ID for members"""
    global MEMBER_ID_COUNTER
    MEMBER_ID_COUNTER += 1
    return MEMBER_ID_COUNTER

def get_next_loan_id():
    """Generate next auto-increment ID for loans"""
    global LOAN_ID_COUNTER
    LOAN_ID_COUNTER += 1
    return LOAN_ID_COUNTER

def get_next_ballot_id():
    """Generate next auto-increment ID for ballots"""
    global BALLOT_ID_COUNTER
    BALLOT_ID_COUNTER += 1
    return BALLOT_ID_COUNTER

def get_next_proposal_id():
    """Generate next auto-increment ID for proposals (thread-safe)"""
    with DATA_LOCK:
        global PROPOSAL_ID_COUNTER
        PROPOSAL_ID_COUNTER += 1
        return PROPOSAL_ID_COUNTER

def get_next_vote_id():
    """Generate next auto-increment ID for votes (thread-safe)"""
    with DATA_LOCK:
        global VOTE_ID_COUNTER
        VOTE_ID_COUNTER += 1
        return VOTE_ID_COUNTER

# Thread-safe voting data access functions
def create_proposal(proposal_data):
    """Create a new proposal (thread-safe)"""
    with PROPOSAL_LOCK:
        proposal_id = get_next_proposal_id()
        proposal_data["id"] = proposal_id
        PROPOSALS[proposal_id] = proposal_data.copy()
        return proposal_id

def update_proposal(proposal_id, update_data):
    """Update an existing proposal (thread-safe)"""
    with PROPOSAL_LOCK:
        if proposal_id in PROPOSALS:
            PROPOSALS[proposal_id].update(update_data)
            return True
        return False

def get_proposal(proposal_id):
    """Get a proposal by ID (thread-safe read)"""
    with PROPOSAL_LOCK:
        return PROPOSALS.get(proposal_id, {}).copy() if proposal_id in PROPOSALS else None

def get_all_proposals():
    """Get all proposals (thread-safe read)"""
    with PROPOSAL_LOCK:
        return {pid: proposal.copy() for pid, proposal in PROPOSALS.items()}

def create_vote(vote_data):
    """Create a new vote (thread-safe)"""
    with VOTE_LOCK:
        vote_id = get_next_vote_id()
        vote_data["id"] = vote_id
        VOTES[vote_id] = vote_data.copy()
        return vote_id

def get_vote_by_member_and_proposal(member_id, proposal_id):
    """Get existing vote by member and proposal (thread-safe)"""
    with VOTE_LOCK:
        for vote in VOTES.values():
            if vote.get("member_id") == member_id and vote.get("proposal_id") == proposal_id:
                return vote.copy()
        return None

def get_votes_for_proposal(proposal_id):
    """Get all votes for a specific proposal (thread-safe)"""
    with VOTE_LOCK:
        return [vote.copy() for vote in VOTES.values() if vote.get("proposal_id") == proposal_id]

def update_vote(vote_id, update_data):
    """Update an existing vote (thread-safe)"""
    with VOTE_LOCK:
        if vote_id in VOTES:
            VOTES[vote_id].update(update_data)
            return True
        return False

def delete_vote(vote_id):
    """Delete a vote (thread-safe)"""
    with VOTE_LOCK:
        if vote_id in VOTES:
            del VOTES[vote_id]
            return True
        return False

def reset_data_store():
    """Reset data store to initial state (useful for testing)"""
    global BOOK_ID_COUNTER, AUTHOR_ID_COUNTER, MEMBER_ID_COUNTER, LOAN_ID_COUNTER, BALLOT_ID_COUNTER
    global PROPOSAL_ID_COUNTER, VOTE_ID_COUNTER
    global BOOKS, AUTHORS, MEMBERS, LOANS, BALLOTS, PROPOSALS, VOTES

    BOOK_ID_COUNTER = 5
    AUTHOR_ID_COUNTER = 3
    MEMBER_ID_COUNTER = 2
    LOAN_ID_COUNTER = 1
    BALLOT_ID_COUNTER = 2
    PROPOSAL_ID_COUNTER = 2
    VOTE_ID_COUNTER = 4

    # Reset to original sample data
    BOOKS.clear()
    BOOKS.update({
        1: {"id": 1, "title": "The Great Gatsby", "author_id": 1, "isbn": "978-0-7432-7356-5", "available_copies": 3, "total_copies": 3},
        2: {"id": 2, "title": "To Kill a Mockingbird", "author_id": 2, "isbn": "978-0-06-112008-4", "available_copies": 2, "total_copies": 2},
        3: {"id": 3, "title": "1984", "author_id": 3, "isbn": "978-0-452-28423-4", "available_copies": 0, "total_copies": 1},
        4: {"id": 4, "title": "Pride and Prejudice", "author_id": 2, "isbn": "978-0-14-143951-8", "available_copies": 1, "total_copies": 1},
        5: {"id": 5, "title": "The Catcher in the Rye", "author_id": 1, "isbn": "978-0-316-76948-0", "available_copies": 2, "total_copies": 2}
    })

    AUTHORS.clear()
    AUTHORS.update({
        1: {"id": 1, "name": "F. Scott Fitzgerald", "bio": "American novelist and short story writer, widely regarded as one of the greatest American writers of the 20th century."},
        2: {"id": 2, "name": "Harper Lee", "bio": "American novelist best known for her 1960 novel To Kill a Mockingbird, which won the Pulitzer Prize for Fiction."},
        3: {"id": 3, "name": "George Orwell", "bio": "English novelist, essayist, journalist, and critic best known for his dystopian novel 1984 and allegorical novella Animal Farm."}
    })

    MEMBERS.clear()
    MEMBERS.update({
        1: {"id": 1, "name": "John Doe", "email": "john.doe@email.com", "password_hash": generate_password_hash("password123"), "registration_date": "2024-01-15"},
        2: {"id": 2, "name": "Jane Smith", "email": "jane.smith@email.com", "password_hash": generate_password_hash("securepass456"), "registration_date": "2024-01-20"}
    })

    LOANS.clear()
    LOANS.update({
        1: {"id": 1, "book_id": 3, "member_id": 1, "borrow_date": "2024-02-01", "return_date": None, "status": "borrowed"}
    })

    BALLOTS.clear()
    BALLOTS.update({
        1: {
            "id": 1,
            "title": "PTA Board Election 2024",
            "description": "Annual election for PTA board positions including President, Vice President, Secretary, and Treasurer.",
            "options": [
                {"id": 1, "title": "President: Sarah Johnson", "description": "Parent volunteer with 5 years PTA experience"},
                {"id": 2, "title": "President: Michael Chen", "description": "Local business owner and education advocate"},
                {"id": 3, "title": "Vice President: Lisa Rodriguez", "description": "Former teacher and current parent liaison"},
                {"id": 4, "title": "Secretary: David Kim", "description": "Organization specialist with nonprofit background"},
                {"id": 5, "title": "Treasurer: Amanda Williams", "description": "CPA with financial management expertise"}
            ],
            "start_date": "2024-03-01T00:00:00",
            "end_date": "2024-03-15T23:59:59",
            "max_votes_per_member": 3,
            "status": "active"
        },
        2: {
            "id": 2,
            "title": "School Fundraising Initiative",
            "description": "Choose the primary fundraising activity for this school year.",
            "options": [
                {"id": 6, "title": "Spring Carnival", "description": "Traditional carnival with games and food booths"},
                {"id": 7, "title": "Silent Auction", "description": "Online auction featuring donated items and services"},
                {"id": 8, "title": "Fun Run", "description": "Community fun run with sponsorship opportunities"}
            ],
            "start_date": "2024-02-15T00:00:00",
            "end_date": "2024-02-28T23:59:59",
            "max_votes_per_member": 1,
            "status": "active"
        }
    })

    PROPOSALS.clear()
    PROPOSALS.update({
        1: {
            "id": 1,
            "title": "Increase School Library Budget",
            "description": "Proposal to increase the annual library budget by $5,000 to purchase new books and educational materials.",
            "created_by": 1,
            "created_date": "2024-02-10",
            "closing_date": "2024-02-24",
            "status": "active",
            "options": ["yes", "no"],
            "allow_abstain": True
        },
        2: {
            "id": 2,
            "title": "New Playground Equipment Installation",
            "description": "Vote on installing new playground equipment including swing sets, slides, and safety surfacing. Total estimated cost: $15,000.",
            "created_by": 2,
            "created_date": "2024-02-11",
            "closing_date": "2024-02-25",
            "status": "active",
            "options": ["approve", "reject"],
            "allow_abstain": False
        }
    })

    VOTES.clear()
    VOTES.update({
        1: {"id": 1, "ballot_id": 2, "member_id": 1, "option_id": 6, "timestamp": "2024-02-16T10:30:00"},
        2: {
            "id": 2,
            "proposal_id": 1,
            "member_id": 1,
            "vote_choice": "yes",
            "timestamp": "2024-02-11T10:30:00",
            "is_anonymous": False
        },
        3: {
            "id": 3,
            "proposal_id": 1,
            "member_id": 2,
            "vote_choice": "no",
            "timestamp": "2024-02-11T11:15:00",
            "is_anonymous": False
        },
        4: {
            "id": 4,
            "proposal_id": 2,
            "member_id": 1,
            "vote_choice": "approve",
            "timestamp": "2024-02-11T14:20:00",
            "is_anonymous": False
        }
    })
