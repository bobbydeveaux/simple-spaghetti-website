"""
In-memory data store for the Library API

Contains dictionaries for books, authors, members, and loans with
auto-increment ID generators and pre-populated sample data.
"""
from datetime import datetime

# Note: werkzeug.security import will be added when requirements.txt is updated in task 3
def generate_password_hash(password):
    """Temporary placeholder for password hashing - will be replaced with werkzeug version"""
    return f"hashed_{password}"

# Global dictionaries for data storage
BOOKS = {}
AUTHORS = {}
MEMBERS = {}
LOANS = {}

# Auto-increment ID generators
_next_book_id = 1
_next_author_id = 1
_next_member_id = 1
_next_loan_id = 1


def get_next_book_id():
    """Generate next book ID"""
    global _next_book_id
    book_id = _next_book_id
    _next_book_id += 1
    return book_id


def get_next_author_id():
    """Generate next author ID"""
    global _next_author_id
    author_id = _next_author_id
    _next_author_id += 1
    return author_id


def get_next_member_id():
    """Generate next member ID"""
    global _next_member_id
    member_id = _next_member_id
    _next_member_id += 1
    return member_id


def get_next_loan_id():
    """Generate next loan ID"""
    global _next_loan_id
    loan_id = _next_loan_id
    _next_loan_id += 1
    return loan_id


def initialize_data():
    """Initialize data store with sample data"""
    global _next_book_id, _next_author_id, _next_member_id, _next_loan_id

    # Clear existing data
    BOOKS.clear()
    AUTHORS.clear()
    MEMBERS.clear()
    LOANS.clear()

    # Reset ID generators
    _next_book_id = 1
    _next_author_id = 1
    _next_member_id = 1
    _next_loan_id = 1

    # Create sample authors
    for i in range(3):
        author_id = get_next_author_id()
        AUTHORS[author_id] = {
            "id": author_id,
            "name": f"Author {author_id}",
            "bio": f"Biography for Author {author_id}"
        }

    # Create sample books
    book_data = [
        {"title": "The Great Library", "author_id": 1, "isbn": "978-0-123456-78-9", "available": True},
        {"title": "Python Programming", "author_id": 2, "isbn": "978-0-234567-89-0", "available": True},
        {"title": "Data Structures", "author_id": 1, "isbn": "978-0-345678-90-1", "available": True},
        {"title": "Web Development", "author_id": 3, "isbn": "978-0-456789-01-2", "available": False},
        {"title": "Machine Learning", "author_id": 2, "isbn": "978-0-567890-12-3", "available": True}
    ]

    for book_info in book_data:
        book_id = get_next_book_id()
        BOOKS[book_id] = {
            "id": book_id,
            **book_info
        }

    # Create sample members
    member_data = [
        {"name": "John Doe", "email": "john@example.com", "password": "password123"},
        {"name": "Jane Smith", "email": "jane@example.com", "password": "password456"}
    ]

    for member_info in member_data:
        member_id = get_next_member_id()
        MEMBERS[member_id] = {
            "id": member_id,
            "name": member_info["name"],
            "email": member_info["email"],
            "password_hash": generate_password_hash(member_info["password"]),
            "registration_date": datetime.now().isoformat()
        }

    # Create sample loan
    loan_id = get_next_loan_id()
    LOANS[loan_id] = {
        "id": loan_id,
        "book_id": 4,  # Web Development book (marked as not available)
        "member_id": 1,  # John Doe
        "borrow_date": datetime.now().isoformat(),
        "return_date": None,
        "status": "borrowed"
    }


# Initialize data on module import
initialize_data()