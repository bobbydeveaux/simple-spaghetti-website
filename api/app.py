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
    BOOKS, AUTHORS, MEMBERS, LOANS,
    get_next_book_id, get_next_loan_id, get_next_member_id
)
from api.validators import validate_book, validate_book_update, validate_loan, validate_loan_return, validate_member, validate_role_update, validate_member_status_update, validate_admin_member_update
from api.auth import token_required, authenticate_member, generate_token, admin_required
from api.audit_service import AuditService

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
            # Log failed login attempt
            AuditService.log_authentication(
                user_email=email,
                action="LOGIN",
                status="failed",
                details="Invalid credentials"
            )
            return {"error": "Invalid credentials"}, 401

        # Log successful login
        AuditService.log_authentication(
            user_email=email,
            action="LOGIN",
            status="success",
            details="Successful login"
        )

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

        # Log member registration
        AuditService.log_member_action(
            action="CREATE",
            member_id=member_id,
            new_member=new_member,
            status="success"
        )

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

        # Log book creation
        AuditService.log_book_action(
            action="CREATE",
            book_id=book_id,
            new_book=new_book,
            status="success"
        )

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

        # Store old book data for audit log
        old_book = BOOKS[book_id].copy()
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

        # Log book update
        AuditService.log_book_action(
            action="UPDATE",
            book_id=book_id,
            old_book=old_book,
            new_book=book,
            status="success"
        )

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

        # Store book data for audit log before deletion
        deleted_book = BOOKS[book_id].copy()

        # Delete the book
        del BOOKS[book_id]

        # Log book deletion
        AuditService.log_book_action(
            action="DELETE",
            book_id=book_id,
            old_book=deleted_book,
            status="success"
        )

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

        # Log loan creation
        AuditService.log_loan_action(
            action="BORROW",
            loan_id=loan_id,
            new_loan=new_loan,
            status="success"
        )

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

        # Store old loan data for audit log
        old_loan = loan.copy()

        # Update the loan
        return_date = datetime.now().strftime("%Y-%m-%d")
        loan["return_date"] = return_date
        loan["status"] = "returned"

        # Increase available copies of the book
        book["available_copies"] += 1

        # Log loan return
        AuditService.log_loan_action(
            action="RETURN",
            loan_id=loan_id,
            old_loan=old_loan,
            new_loan=loan,
            status="success"
        )

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


# ADMIN ENDPOINTS

@app.route("/admin/dashboard", methods=["GET"])
@token_required
@admin_required
def admin_dashboard() -> Tuple[Dict[str, Any], int]:
    """
    Get admin dashboard statistics and system overview.

    Returns:
        200: Dashboard data with system statistics
        401: Unauthorized
        403: Admin access required
    """
    try:
        # Get system statistics
        total_books = len(BOOKS)
        total_authors = len(AUTHORS)
        total_members = len(MEMBERS)
        total_loans = len(LOANS)

        # Count active loans
        active_loans = sum(1 for loan in LOANS.values() if loan["status"] == "borrowed")

        # Count users by role
        admin_count = sum(1 for member in MEMBERS.values() if member.get("role") == "admin")
        user_count = total_members - admin_count

        # Count members by status
        active_members = sum(1 for member in MEMBERS.values() if member.get("status") == "active")
        suspended_members = total_members - active_members

        # Get audit log statistics
        audit_stats = AuditService.get_audit_log_stats()

        dashboard_data = {
            "system_overview": {
                "total_books": total_books,
                "total_authors": total_authors,
                "total_members": total_members,
                "total_loans": total_loans,
                "active_loans": active_loans
            },
            "member_statistics": {
                "admin_count": admin_count,
                "user_count": user_count,
                "active_members": active_members,
                "suspended_members": suspended_members
            },
            "audit_statistics": audit_stats
        }

        # Log admin dashboard access
        AuditService.log_action(
            action="VIEW",
            resource_type="admin_dashboard",
            status="success"
        )

        return dashboard_data, 200

    except Exception as e:
        print(f"Admin dashboard error: {str(e)}")
        return {"error": "Failed to retrieve dashboard data"}, 500

@app.route("/admin/members", methods=["GET"])
@token_required
@admin_required
def admin_list_members() -> Tuple[List[Dict[str, Any]], int]:
    """
    Get all members for admin management.

    Query parameters:
        - role: Filter by role (user, admin)
        - status: Filter by status (active, suspended)
        - limit: Number of members to return (default: 50)
        - offset: Number of members to skip (default: 0)

    Returns:
        200: List of members without password hashes
        401: Unauthorized
        403: Admin access required
    """
    try:
        # Get query parameters
        role_filter = request.args.get("role", "").strip()
        status_filter = request.args.get("status", "").strip()
        limit = int(request.args.get("limit", 50))
        offset = int(request.args.get("offset", 0))

        members_list = []

        for member in MEMBERS.values():
            # Apply filters
            if role_filter and member.get("role") != role_filter:
                continue
            if status_filter and member.get("status") != status_filter:
                continue

            # Remove password_hash for security
            safe_member = {
                "id": member["id"],
                "name": member["name"],
                "email": member["email"],
                "registration_date": member["registration_date"],
                "role": member.get("role", "user"),
                "status": member.get("status", "active")
            }
            members_list.append(safe_member)

        # Sort by registration date (newest first)
        members_list.sort(key=lambda x: x["registration_date"], reverse=True)

        # Apply pagination
        paginated_members = members_list[offset:offset + limit]

        # Log admin action
        AuditService.log_action(
            action="VIEW",
            resource_type="admin_members",
            status="success",
            details=f"Viewed members list with filters: role={role_filter}, status={status_filter}"
        )

        return paginated_members, 200

    except ValueError:
        return {"error": "Invalid limit or offset parameter"}, 400
    except Exception as e:
        print(f"Admin list members error: {str(e)}")
        return {"error": "Failed to retrieve members"}, 500

@app.route("/admin/members/<int:member_id>", methods=["GET"])
@token_required
@admin_required
def admin_get_member(member_id: int) -> Tuple[Dict[str, Any], int]:
    """
    Get detailed information about a specific member.

    Returns:
        200: Member details without password hash
        401: Unauthorized
        403: Admin access required
        404: Member not found
    """
    try:
        if member_id not in MEMBERS:
            return {"error": "Member not found"}, 404

        member = MEMBERS[member_id]

        # Get member's loan history
        member_loans = []
        for loan in LOANS.values():
            if loan["member_id"] == member_id:
                book = BOOKS.get(loan["book_id"], {})
                loan_info = {
                    "loan_id": loan["id"],
                    "book_id": loan["book_id"],
                    "book_title": book.get("title", "Unknown"),
                    "borrow_date": loan["borrow_date"],
                    "return_date": loan.get("return_date"),
                    "status": loan["status"]
                }
                member_loans.append(loan_info)

        member_loans.sort(key=lambda x: x["borrow_date"], reverse=True)

        # Return member details without password
        member_details = {
            "id": member["id"],
            "name": member["name"],
            "email": member["email"],
            "registration_date": member["registration_date"],
            "role": member.get("role", "user"),
            "status": member.get("status", "active"),
            "loan_history": member_loans
        }

        # Log admin action
        AuditService.log_action(
            action="VIEW",
            resource_type="member",
            resource_id=member_id,
            status="success"
        )

        return member_details, 200

    except Exception as e:
        print(f"Admin get member error: {str(e)}")
        return {"error": "Failed to retrieve member details"}, 500

@app.route("/admin/members/<int:member_id>", methods=["PUT"])
@token_required
@admin_required
def admin_update_member(member_id: int) -> Tuple[Dict[str, Any], int]:
    """
    Update a member's information (admin only).

    Request body (all fields optional):
        {
            "name": "string",
            "email": "string",
            "role": "user|admin",
            "status": "active|suspended"
        }

    Returns:
        200: Updated member details
        400: Validation error
        401: Unauthorized
        403: Admin access required
        404: Member not found
    """
    try:
        data = request.get_json()
        if not data:
            return {"error": "Request body required"}, 400

        # Validate the update data
        is_valid, error_msg = validate_admin_member_update(member_id, data)
        if not is_valid:
            AuditService.log_action(
                action="UPDATE",
                resource_type="member",
                resource_id=member_id,
                status="failed",
                details=f"Validation failed: {error_msg}"
            )
            return {"error": error_msg}, 400

        # Store old member data for audit log
        old_member = MEMBERS[member_id].copy()
        member = MEMBERS[member_id]

        # Update provided fields
        if "name" in data:
            member["name"] = data["name"].strip()
        if "email" in data:
            member["email"] = data["email"].strip().lower()
        if "role" in data:
            member["role"] = data["role"].strip()
        if "status" in data:
            member["status"] = data["status"].strip()

        # Return updated member without password
        updated_member = {
            "id": member["id"],
            "name": member["name"],
            "email": member["email"],
            "registration_date": member["registration_date"],
            "role": member.get("role", "user"),
            "status": member.get("status", "active")
        }

        # Log admin action
        AuditService.log_member_action(
            action="UPDATE",
            member_id=member_id,
            old_member=old_member,
            new_member=member,
            status="success"
        )

        return updated_member, 200

    except Exception as e:
        print(f"Admin update member error: {str(e)}")
        AuditService.log_action(
            action="UPDATE",
            resource_type="member",
            resource_id=member_id,
            status="failed",
            details=f"Server error: {str(e)}"
        )
        return {"error": "Failed to update member"}, 500

@app.route("/admin/members/<int:member_id>", methods=["DELETE"])
@token_required
@admin_required
def admin_delete_member(member_id: int) -> Tuple[Dict[str, str], int]:
    """
    Delete a member (admin only).

    Returns:
        200: Success message
        400: Cannot delete member with active loans
        401: Unauthorized
        403: Admin access required
        404: Member not found
    """
    try:
        if member_id not in MEMBERS:
            return {"error": "Member not found"}, 404

        member = MEMBERS[member_id]

        # Prevent self-deletion
        if hasattr(request, 'current_member_id') and request.current_member_id == member_id:
            AuditService.log_action(
                action="DELETE",
                resource_type="member",
                resource_id=member_id,
                status="failed",
                details="Admin attempted to delete their own account"
            )
            return {"error": "Cannot delete your own account"}, 400

        # Check if member has active loans
        active_loans = [loan for loan in LOANS.values()
                       if loan["member_id"] == member_id and loan["status"] == "borrowed"]

        if active_loans:
            AuditService.log_action(
                action="DELETE",
                resource_type="member",
                resource_id=member_id,
                status="failed",
                details="Member has active loans"
            )
            return {"error": "Cannot delete member with active loans"}, 400

        # Store member data for audit log before deletion
        deleted_member = member.copy()

        # Delete the member
        del MEMBERS[member_id]

        # Log admin action
        AuditService.log_member_action(
            action="DELETE",
            member_id=member_id,
            old_member=deleted_member,
            status="success"
        )

        return {"message": f"Member '{deleted_member['name']}' deleted successfully"}, 200

    except Exception as e:
        print(f"Admin delete member error: {str(e)}")
        AuditService.log_action(
            action="DELETE",
            resource_type="member",
            resource_id=member_id,
            status="failed",
            details=f"Server error: {str(e)}"
        )
        return {"error": "Failed to delete member"}, 500

@app.route("/admin/audit-logs", methods=["GET"])
@token_required
@admin_required
def admin_get_audit_logs() -> Tuple[List[Dict[str, Any]], int]:
    """
    Get audit logs for admin review.

    Query parameters:
        - limit: Number of logs to return (default: 100, max: 1000)
        - offset: Number of logs to skip (default: 0)
        - user_id: Filter by user ID
        - action: Filter by action type
        - resource_type: Filter by resource type
        - status: Filter by status (success/failed)
        - start_date: Filter by start date (YYYY-MM-DD)
        - end_date: Filter by end date (YYYY-MM-DD)

    Returns:
        200: List of audit logs
        400: Invalid parameters
        401: Unauthorized
        403: Admin access required
    """
    try:
        # Get and validate query parameters
        limit = min(int(request.args.get("limit", 100)), 1000)  # Max 1000
        offset = int(request.args.get("offset", 0))
        user_id = request.args.get("user_id")
        action = request.args.get("action")
        resource_type = request.args.get("resource_type")
        status = request.args.get("status")
        start_date = request.args.get("start_date")
        end_date = request.args.get("end_date")

        # Convert user_id to int if provided
        if user_id:
            try:
                user_id = int(user_id)
            except ValueError:
                return {"error": "Invalid user_id parameter"}, 400

        # Get filtered audit logs
        audit_logs = AuditService.get_audit_logs(
            limit=limit,
            offset=offset,
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            status=status,
            start_date=start_date,
            end_date=end_date
        )

        # Log admin action (but don't log viewing of audit logs to avoid infinite recursion)
        # AuditService.log_action(action="VIEW", resource_type="audit_logs", status="success")

        return audit_logs, 200

    except ValueError as e:
        return {"error": f"Invalid parameter: {str(e)}"}, 400
    except Exception as e:
        print(f"Admin get audit logs error: {str(e)}")
        return {"error": "Failed to retrieve audit logs"}, 500

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
        "service": "Library Management API",
        "version": "1.1",
        "endpoints": {
            "authentication": "/auth/login",
            "member_registration": "/members",
            "books": "/books",
            "book_detail": "/books/{id}",
            "borrow_book": "/loans/borrow",
            "return_book": "/loans/return",
            "loan_details": "/loans/{id}",
            "health": "/health"
        },
        "admin_endpoints": {
            "admin_dashboard": "/admin/dashboard",
            "admin_members": "/admin/members",
            "admin_member_detail": "/admin/members/{id}",
            "admin_audit_logs": "/admin/audit-logs"
        },
        "new_features": [
            "Admin user management",
            "Role-based access control",
            "Comprehensive audit logging",
            "Admin dashboard with statistics"
        ]
    }, 200

if __name__ == "__main__":
    print("Starting Library Management API...")
    print("Sample login credentials:")
    print("  Email: john.doe@email.com, Password: password123")
    print("  Email: jane.smith@email.com, Password: securepass456")

    # Run development server
    app.run(debug=True, host="0.0.0.0", port=5000)