"""
In-memory data store with dictionaries for books, authors, members, and loans.
Pre-populated with sample data for development and testing.
"""

from datetime import datetime
from werkzeug.security import generate_password_hash

# Auto-increment ID generators
BOOK_ID_COUNTER = 5
AUTHOR_ID_COUNTER = 3
MEMBER_ID_COUNTER = 2
LOAN_ID_COUNTER = 1

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

def reset_data_store():
    """Reset data store to initial state (useful for testing)"""
    global BOOK_ID_COUNTER, AUTHOR_ID_COUNTER, MEMBER_ID_COUNTER, LOAN_ID_COUNTER
    global BOOKS, AUTHORS, MEMBERS, LOANS

    BOOK_ID_COUNTER = 5
    AUTHOR_ID_COUNTER = 3
    MEMBER_ID_COUNTER = 2
    LOAN_ID_COUNTER = 1

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