"""
Library Management API - Flask application with book CRUD and search endpoints.
Provides REST API for managing books, authors, members, and loans.
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import traceback
from datetime import datetime
from werkzeug.security import generate_password_hash
from typing import Dict, List, Any, Tuple
from datetime import datetime

# Import our modules
from api.data_store import (
    BOOKS, AUTHORS, MEMBERS, LOANS, BALLOTS, VOTES,
    get_next_book_id, get_next_loan_id, get_next_member_id, get_next_ballot_id, get_next_vote_id
)
from api.validators import validate_book, validate_book_update, validate_loan, validate_loan_return, validate_member, validate_vote
from api.auth import token_required, authenticate_member, generate_token

# Create Flask application
app = Flask(__name__)

# Enable CORS for development
CORS(app)

# Global error handler
@app.errorhandler(Exception)
def handle_exception(e):
    """Global exception handler"""
    print(f"Unhandled exception: {str(e)}")
    print(traceback.format_exc())
    return jsonify({"error": "Internal server error"}), 500

@app.errorhandler(404)
def handle_not_found(e):
    """Handle 404 errors"""
    return jsonify({"error": "Resource not found"}), 404

@app.errorhandler(400)
def handle_bad_request(e):
    """Handle 400 errors"""
    return jsonify({"error": "Bad request"}), 400

@app.errorhandler(401)
def handle_unauthorized(e):
    """Handle 401 errors"""
    return jsonify({"error": "Unauthorized"}), 401

# Authentication endpoint
@app.route("/auth/login", methods=["POST"])
def login() -> Tuple[Dict[str, Any], int]:
    """
    Authenticate member and return JWT token.

    Request body:
        {
            "email": "string",
            "password": "string"
        }

    Returns:
        200: {"token": "jwt_token", "member_id": int}
        401: {"error": "Invalid credentials"}
    """
    try:
        data = request.get_json()
        if not data:
            return {"error": "Request body required"}, 400

        email = data.get("email")
        password = data.get("password")

        if not email or not password:
            return {"error": "Email and password are required"}, 400

        member_id = authenticate_member(email, password)
        if member_id is None:
            return {"error": "Invalid credentials"}, 401

        token = generate_token(member_id)
        return {"token": token, "member_id": member_id}, 200

    except Exception as e:
        print(f"Login error: {str(e)}")
        return {"error": "Login failed"}, 500

# Member endpoints
@app.route("/members", methods=["POST"])
def register_member() -> Tuple[Dict[str, Any], int]:
    """
    Register a new member.

    Request body:
        {
            "name": "string",
            "email": "string",
            "password": "string"
        }

    Returns:
        201: {"id": int, "name": "string", "email": "string", "registration_date": "string"}
        400: {"error": "string"} - Validation error
        500: {"error": "string"} - Server error
    """
    try:
        data = request.get_json()
        if not data:
            return {"error": "Request body required"}, 400

        # Validate input
        is_valid, error_msg = validate_member(data)
        if not is_valid:
            return {"error": error_msg}, 400

        # Create new member
        member_id = get_next_member_id()
        new_member = {
            "id": member_id,
            "name": data["name"].strip(),
            "email": data["email"].strip().lower(),
            "password_hash": generate_password_hash(data["password"]),
            "registration_date": datetime.now().strftime("%Y-%m-%d")
        }

        MEMBERS[member_id] = new_member

        # Return member data without password_hash
        response_data = {
            "id": new_member["id"],
            "name": new_member["name"],
            "email": new_member["email"],
            "registration_date": new_member["registration_date"]
        }

        return response_data, 201

    except Exception as e:
        print(f"Register member error: {str(e)}")
        return {"error": "Failed to register member"}, 500

# Book endpoints
@app.route("/books", methods=["GET"])
def list_books() -> Tuple[List[Dict[str, Any]], int]:
    """
    List books with optional search filtering.

    Query parameters:
        - title: Filter by title (partial match, case-insensitive)
        - author: Filter by author name (partial match, case-insensitive)

    Returns:
        200: List of books with author information
    """
    try:
        # Get query parameters
        title_filter = request.args.get("title", "").lower().strip()
        author_filter = request.args.get("author", "").lower().strip()

        books_with_authors = []

        for book in BOOKS.values():
            # Get author information
            author = AUTHORS.get(book["author_id"])
            if not author:
                continue

            # Apply filters
            if title_filter and title_filter not in book["title"].lower():
                continue

            if author_filter and author_filter not in author["name"].lower():
                continue

            # Add book with author info
            book_data = {
                "id": book["id"],
                "title": book["title"],
                "author_id": book["author_id"],
                "author_name": author["name"],
                "isbn": book["isbn"],
                "available_copies": book["available_copies"],
                "total_copies": book["total_copies"]
            }
            books_with_authors.append(book_data)

        # Sort by title for consistent ordering
        books_with_authors.sort(key=lambda x: x["title"])

        return books_with_authors, 200

    except Exception as e:
        print(f"List books error: {str(e)}")
        return {"error": "Failed to retrieve books"}, 500

@app.route("/books", methods=["POST"])
@token_required
def create_book() -> Tuple[Dict[str, Any], int]:
    """
    Create a new book.

    Request body:
        {
            "title": "string",
            "author_id": int,
            "isbn": "string",
            "available_copies": int (optional, default: 1),
            "total_copies": int (optional, default: 1)
        }

    Returns:
        201: Created book
        400: Validation error
        401: Authentication required
    """
    try:
        data = request.get_json()
        if not data:
            return {"error": "Request body required"}, 400

        # Set defaults for optional fields
        if "available_copies" not in data:
            data["available_copies"] = 1
        if "total_copies" not in data:
            data["total_copies"] = 1

        # Validate input
        is_valid, error_msg = validate_book(data)
        if not is_valid:
            return {"error": error_msg}, 400

        # Create new book
        book_id = get_next_book_id()
        new_book = {
            "id": book_id,
            "title": data["title"].strip(),
            "author_id": int(data["author_id"]),
            "isbn": data["isbn"].strip(),
            "available_copies": int(data["available_copies"]),
            "total_copies": int(data["total_copies"])
        }

        BOOKS[book_id] = new_book

        # Return book with author info
        author = AUTHORS.get(new_book["author_id"])
        response_data = new_book.copy()
        if author:
            response_data["author_name"] = author["name"]

        return response_data, 201

    except Exception as e:
        print(f"Create book error: {str(e)}")
        return {"error": "Failed to create book"}, 500

@app.route("/books/<int:book_id>", methods=["GET"])
def get_book(book_id: int) -> Tuple[Dict[str, Any], int]:
    """
    Get a specific book by ID.

    Returns:
        200: Book with author information
        404: Book not found
    """
    try:
        book = BOOKS.get(book_id)
        if not book:
            return {"error": "Book not found"}, 404

        # Get author information
        author = AUTHORS.get(book["author_id"])

        response_data = {
            "id": book["id"],
            "title": book["title"],
            "author_id": book["author_id"],
            "isbn": book["isbn"],
            "available_copies": book["available_copies"],
            "total_copies": book["total_copies"]
        }

        if author:
            response_data["author_name"] = author["name"]
            response_data["author_bio"] = author["bio"]

        return response_data, 200

    except Exception as e:
        print(f"Get book error: {str(e)}")
        return {"error": "Failed to retrieve book"}, 500

@app.route("/books/<int:book_id>", methods=["PUT"])
@token_required
def update_book(book_id: int) -> Tuple[Dict[str, Any], int]:
    """
    Update an existing book.

    Request body (partial updates allowed):
        {
            "title": "string",
            "author_id": int,
            "isbn": "string",
            "available_copies": int,
            "total_copies": int
        }

    Returns:
        200: Updated book
        400: Validation error
        401: Authentication required
        404: Book not found
    """
    try:
        data = request.get_json()
        if not data:
            return {"error": "Request body required"}, 400

        # Validate input
        is_valid, error_msg = validate_book_update(book_id, data)
        if not is_valid:
            return {"error": error_msg}, 400

        book = BOOKS[book_id]

        # Update provided fields
        if "title" in data:
            book["title"] = data["title"].strip()
        if "author_id" in data:
            book["author_id"] = int(data["author_id"])
        if "isbn" in data:
            book["isbn"] = data["isbn"].strip()
        if "available_copies" in data:
            book["available_copies"] = int(data["available_copies"])
        if "total_copies" in data:
            book["total_copies"] = int(data["total_copies"])

        # Return updated book with author info
        author = AUTHORS.get(book["author_id"])
        response_data = book.copy()
        if author:
            response_data["author_name"] = author["name"]

        return response_data, 200

    except Exception as e:
        print(f"Update book error: {str(e)}")
        return {"error": "Failed to update book"}, 500

@app.route("/books/<int:book_id>", methods=["DELETE"])
@token_required
def delete_book(book_id: int) -> Tuple[Dict[str, str], int]:
    """
    Delete a book.

    Returns:
        200: Success message
        401: Authentication required
        404: Book not found
    """
    try:
        if book_id not in BOOKS:
            return {"error": "Book not found"}, 404

        # Check if book has active loans
        active_loans = [loan for loan in LOANS.values()
                       if loan["book_id"] == book_id and loan["status"] == "borrowed"]

        if active_loans:
            return {"error": "Cannot delete book with active loans"}, 400

        # Delete the book
        del BOOKS[book_id]

        return {"message": "Book deleted successfully"}, 200

    except Exception as e:
        print(f"Delete book error: {str(e)}")
        return {"error": "Failed to delete book"}, 500


# LOAN ENDPOINTS

@app.route("/loans/borrow", methods=["POST"])
@token_required
def borrow_book() -> Tuple[Dict[str, Any], int]:
    """
    Borrow a book by creating a new loan record.

    Request body:
        {
            "book_id": int,
            "member_id": int
        }

    Returns:
        201: Loan created successfully
        400: Validation error
        401: Unauthorized
        404: Book or member not found
        500: Internal server error
    """
    try:
        data = request.get_json()
        if not data:
            return {"error": "Request body required"}, 400

        # Validate loan data
        is_valid, error_msg = validate_loan(data)
        if not is_valid:
            return {"error": error_msg}, 400

        # Get book and member details for response
        book_id = int(data["book_id"])
        member_id = int(data["member_id"])

        book = BOOKS[book_id]
        member = MEMBERS[member_id]

        # Create the loan
        loan_id = get_next_loan_id()
        borrow_date = datetime.now().strftime("%Y-%m-%d")

        new_loan = {
            "id": loan_id,
            "book_id": book_id,
            "member_id": member_id,
            "borrow_date": borrow_date,
            "return_date": None,
            "status": "borrowed"
        }

        # Add loan to data store
        LOANS[loan_id] = new_loan

        # Decrease available copies of the book
        book["available_copies"] -= 1

        # Return loan details
        return {
            "loan_id": loan_id,
            "book_id": book_id,
            "member_id": member_id,
            "borrow_date": borrow_date,
            "book_title": book["title"],
            "member_name": member["name"],
            "status": "borrowed",
            "message": f"Book '{book['title']}' successfully borrowed by {member['name']}"
        }, 201

    except KeyError as e:
        return {"error": f"Resource not found: {str(e)}"}, 404
    except Exception as e:
        print(f"Borrow book error: {str(e)}")
        return {"error": "Failed to borrow book"}, 500


@app.route("/loans/return", methods=["POST"])
@token_required
def return_book() -> Tuple[Dict[str, Any], int]:
    """
    Return a borrowed book by updating the loan record.

    Request body:
        {
            "loan_id": int
        }

    Returns:
        200: Book returned successfully
        400: Validation error
        401: Unauthorized
        404: Loan not found
        500: Internal server error
    """
    try:
        data = request.get_json()
        if not data:
            return {"error": "Request body required"}, 400

        if "loan_id" not in data:
            return {"error": "Missing required field: loan_id"}, 400

        loan_id = int(data["loan_id"])

        # Validate loan return
        is_valid, error_msg = validate_loan_return(loan_id)
        if not is_valid:
            return {"error": error_msg}, 400

        # Get loan, book, and member details
        loan = LOANS[loan_id]
        book = BOOKS[loan["book_id"]]
        member = MEMBERS[loan["member_id"]]

        # Update the loan
        return_date = datetime.now().strftime("%Y-%m-%d")
        loan["return_date"] = return_date
        loan["status"] = "returned"

        # Increase available copies of the book
        book["available_copies"] += 1

        return {
            "loan_id": loan_id,
            "book_id": loan["book_id"],
            "member_id": loan["member_id"],
            "borrow_date": loan["borrow_date"],
            "return_date": return_date,
            "book_title": book["title"],
            "member_name": member["name"],
            "status": "returned",
            "message": f"Book '{book['title']}' successfully returned by {member['name']}"
        }, 200

    except KeyError as e:
        return {"error": f"Resource not found: {str(e)}"}, 404
    except ValueError as e:
        return {"error": f"Invalid loan_id: {str(e)}"}, 400
    except Exception as e:
        print(f"Return book error: {str(e)}")
        return {"error": "Failed to return book"}, 500


@app.route("/loans/<int:loan_id>", methods=["GET"])
@token_required
def get_loan_details(loan_id: int) -> Tuple[Dict[str, Any], int]:
    """
    Get details of a specific loan by ID.

    Returns:
        200: Loan details
        401: Unauthorized
        404: Loan not found
        500: Internal server error
    """
    try:
        if loan_id not in LOANS:
            return {"error": f"Loan with ID {loan_id} not found"}, 404

        loan = LOANS[loan_id]
        book = BOOKS[loan["book_id"]]
        member = MEMBERS[loan["member_id"]]

        return {
            "loan_id": loan["id"],
            "book_id": loan["book_id"],
            "member_id": loan["member_id"],
            "borrow_date": loan["borrow_date"],
            "return_date": loan.get("return_date"),
            "book_title": book["title"],
            "member_name": member["name"],
            "status": loan["status"]
        }, 200

    except KeyError as e:
        return {"error": f"Related resource not found: {str(e)}"}, 404
    except Exception as e:
        print(f"Get loan error: {str(e)}")
        return {"error": "Failed to retrieve loan details"}, 500


# VOTING ENDPOINTS

@app.route("/ballots", methods=["GET"])
def list_ballots() -> Tuple[List[Dict[str, Any]], int]:
    """
    List all active ballots available for voting.

    Returns:
        200: List of active ballots with options
    """
    try:
        active_ballots = []
        current_time = datetime.now().isoformat()

        for ballot in BALLOTS.values():
            # Only include active ballots that are within voting period
            if ballot["status"] == "active" and ballot["start_date"] <= current_time <= ballot["end_date"]:
                active_ballots.append(ballot)

        # Sort by start date
        active_ballots.sort(key=lambda x: x["start_date"])

        return active_ballots, 200

    except Exception as e:
        print(f"List ballots error: {str(e)}")
        return {"error": "Failed to retrieve ballots"}, 500


@app.route("/ballots/<int:ballot_id>", methods=["GET"])
def get_ballot(ballot_id: int) -> Tuple[Dict[str, Any], int]:
    """
    Get a specific ballot by ID.

    Returns:
        200: Ballot details with options
        404: Ballot not found
    """
    try:
        ballot = BALLOTS.get(ballot_id)
        if not ballot:
            return {"error": "Ballot not found"}, 404

        return ballot, 200

    except Exception as e:
        print(f"Get ballot error: {str(e)}")
        return {"error": "Failed to retrieve ballot"}, 500


@app.route("/votes", methods=["POST"])
@token_required
def submit_vote() -> Tuple[Dict[str, Any], int]:
    """
    Submit a vote for a ballot option.

    Request body:
        {
            "ballot_id": int,
            "option_id": int
        }

    Returns:
        201: Vote submitted successfully
        400: Validation error
        401: Authentication required
        404: Ballot or option not found
        409: Already voted
    """
    try:
        data = request.get_json()
        if not data:
            return {"error": "Request body required"}, 400

        # Get current user ID from the token (this is set by the @token_required decorator)
        member_id = getattr(request, 'current_member_id', None)
        if not member_id:
            return {"error": "Authentication required"}, 401

        # Validate vote data
        is_valid, error_msg = validate_vote(data, member_id)
        if not is_valid:
            return {"error": error_msg}, 400

        ballot_id = int(data["ballot_id"])
        option_id = int(data["option_id"])
        ballot = BALLOTS[ballot_id]  # We know it exists from validation

        # Create the vote
        vote_id = get_next_vote_id()
        new_vote = {
            "id": vote_id,
            "ballot_id": ballot_id,
            "member_id": member_id,
            "option_id": option_id,
            "timestamp": datetime.now().isoformat()
        }

        VOTES[vote_id] = new_vote

        # Get option title for response
        option_title = next((opt["title"] for opt in ballot["options"] if opt["id"] == option_id), "Unknown option")

        return {
            "vote_id": vote_id,
            "ballot_id": ballot_id,
            "ballot_title": ballot["title"],
            "option_id": option_id,
            "option_title": option_title,
            "timestamp": new_vote["timestamp"],
            "message": f"Vote successfully submitted for '{option_title}'"
        }, 201

    except ValueError as e:
        return {"error": f"Invalid data format: {str(e)}"}, 400
    except Exception as e:
        print(f"Submit vote error: {str(e)}")
        return {"error": "Failed to submit vote"}, 500


@app.route("/votes/my-votes", methods=["GET"])
@token_required
def get_my_votes() -> Tuple[List[Dict[str, Any]], int]:
    """
    Get all votes submitted by the current user.

    Returns:
        200: List of user's votes with ballot and option details
        401: Authentication required
    """
    try:
        # Get current user ID from the token
        member_id = getattr(request, 'current_member_id', None)
        if not member_id:
            return {"error": "Authentication required"}, 401

        user_votes = []
        for vote in VOTES.values():
            if vote["member_id"] == member_id:
                # Get ballot and option details
                ballot = BALLOTS.get(vote["ballot_id"])
                if ballot:
                    option = next((opt for opt in ballot["options"] if opt["id"] == vote["option_id"]), None)

                    vote_details = {
                        "vote_id": vote["id"],
                        "ballot_id": vote["ballot_id"],
                        "ballot_title": ballot["title"],
                        "option_id": vote["option_id"],
                        "option_title": option["title"] if option else "Unknown option",
                        "timestamp": vote["timestamp"]
                    }
                    user_votes.append(vote_details)

        # Sort by timestamp (newest first)
        user_votes.sort(key=lambda x: x["timestamp"], reverse=True)

        return user_votes, 200

    except Exception as e:
        print(f"Get my votes error: {str(e)}")
        return {"error": "Failed to retrieve votes"}, 500


@app.route("/ballots/<int:ballot_id>/results", methods=["GET"])
def get_ballot_results(ballot_id: int) -> Tuple[Dict[str, Any], int]:
    """
    Get voting results for a specific ballot.

    Returns:
        200: Ballot results with vote counts
        404: Ballot not found
    """
    try:
        ballot = BALLOTS.get(ballot_id)
        if not ballot:
            return {"error": "Ballot not found"}, 404

        # Count votes for each option
        vote_counts = {}
        total_votes = 0

        for vote in VOTES.values():
            if vote["ballot_id"] == ballot_id:
                option_id = vote["option_id"]
                vote_counts[option_id] = vote_counts.get(option_id, 0) + 1
                total_votes += 1

        # Build results with option details
        results = []
        for option in ballot["options"]:
            option_id = option["id"]
            vote_count = vote_counts.get(option_id, 0)
            percentage = (vote_count / total_votes * 100) if total_votes > 0 else 0

            results.append({
                "option_id": option_id,
                "option_title": option["title"],
                "option_description": option["description"],
                "vote_count": vote_count,
                "percentage": round(percentage, 1)
            })

        # Sort by vote count (highest first)
        results.sort(key=lambda x: x["vote_count"], reverse=True)

        return {
            "ballot_id": ballot_id,
            "ballot_title": ballot["title"],
            "ballot_description": ballot["description"],
            "total_votes": total_votes,
            "results": results,
            "voting_period": {
                "start_date": ballot["start_date"],
                "end_date": ballot["end_date"]
            }
        }, 200

    except Exception as e:
        print(f"Get ballot results error: {str(e)}")
        return {"error": "Failed to retrieve ballot results"}, 500


# Health check endpoint
@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "library-api"}, 200

# Root endpoint
@app.route("/", methods=["GET"])
def root():
    """Root endpoint with API information"""
    return {
        "service": "Library Management & PTA Voting API",
        "version": "1.0",
        "endpoints": {
            "authentication": "/auth/login",
            "member_registration": "/members",
            "books": "/books",
            "book_detail": "/books/{id}",
            "borrow_book": "/loans/borrow",
            "return_book": "/loans/return",
            "loan_details": "/loans/{id}",
            "ballots": "/ballots",
            "ballot_detail": "/ballots/{id}",
            "submit_vote": "/votes",
            "my_votes": "/votes/my-votes",
            "ballot_results": "/ballots/{id}/results",
            "health": "/health"
        }
    }, 200

if __name__ == "__main__":
    print("Starting Library Management API...")
    print("Sample login credentials:")
    print("  Email: john.doe@email.com, Password: password123")
    print("  Email: jane.smith@email.com, Password: securepass456")

    # Run development server
    app.run(debug=True, host="0.0.0.0", port=5000)