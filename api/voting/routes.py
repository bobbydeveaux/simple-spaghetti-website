"""
PTA Voting System Routes
Authentication endpoints for voter code-based authentication.
"""

from flask import Blueprint, request, jsonify
from typing import Dict, Any, Tuple
import re

# Import existing JWT utilities
from api.utils.jwt_manager import JWTManager
from .data_store import voting_data_store
from .models import generate_session_id


# Create Blueprint for voting routes
voting_bp = Blueprint('voting', __name__, url_prefix='/api/voting')

# Initialize JWT manager
jwt_manager = JWTManager()

# Mock admin credentials for Sprint 1 (hardcoded for prototype)
ADMIN_CREDENTIALS = {
    "admin@pta.school": "admin123"  # In production, this would be properly secured
}


def validate_email(email: str) -> bool:
    """Validate email format."""
    if not email or len(email) > 254:
        return False

    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(email_pattern, email))


@voting_bp.route('/auth/request-code', methods=['POST'])
def request_verification_code() -> Tuple[Dict[str, Any], int]:
    """
    Request a verification code for voter authentication.

    Request body:
        {
            "email": "voter@example.com"
        }

    Returns:
        200: {"message": "Verification code sent", "code": "123456"} (for testing)
        400: {"error": "validation message"}
    """
    try:
        data = request.get_json()
        if not data:
            return {"error": "Request body required"}, 400

        email = data.get("email", "").strip()
        if not email:
            return {"error": "Email is required"}, 400

        if not validate_email(email):
            return {"error": "Invalid email format"}, 400

        # Create or get voter
        voter = voting_data_store.create_or_get_voter(email)

        # Create verification code
        verification_code = voting_data_store.create_verification_code(email, voter.voter_id)

        # In a real system, this code would be sent via email
        # For Sprint 1 testing, we return the code directly
        response = {
            "message": f"Verification code sent to {email}",
            "voter_id": voter.voter_id,  # For testing purposes
        }

        # Include code in response for development/testing
        # In production, this would be sent via email and not returned
        response["code"] = verification_code.code

        return response, 200

    except Exception as e:
        print(f"Request verification code error: {str(e)}")
        return {"error": "Failed to send verification code"}, 500


@voting_bp.route('/auth/verify', methods=['POST'])
def verify_code() -> Tuple[Dict[str, Any], int]:
    """
    Verify authentication code and create session.

    Request body:
        {
            "email": "voter@example.com",
            "code": "123456"
        }

    Returns:
        200: {"token": "jwt_token", "voter_id": "voter_abc123", "session_id": "session_xyz789"}
        400: {"error": "validation message"}
        401: {"error": "Invalid or expired code"}
    """
    try:
        data = request.get_json()
        if not data:
            return {"error": "Request body required"}, 400

        email = data.get("email", "").strip()
        code = data.get("code", "").strip()

        if not email or not code:
            return {"error": "Email and code are required"}, 400

        if not validate_email(email):
            return {"error": "Invalid email format"}, 400

        # Get and use verification code
        voter_id = voting_data_store.use_verification_code(code)
        if not voter_id:
            return {"error": "Invalid or expired verification code"}, 401

        # Verify voter matches email
        voter = voting_data_store.get_voter_by_id(voter_id)
        if not voter or voter.email != email.lower():
            return {"error": "Verification code does not match email"}, 401

        # Create JWT token with voter_id
        token = jwt_manager.create_access_token(voter_id)

        # Create session
        session = voting_data_store.create_session(voter_id, token)

        # Update voter's last login
        voter.last_login = session.created_at

        return {
            "token": token,
            "voter_id": voter_id,
            "session_id": session.session_id,
            "expires_at": session.expires_at.isoformat(),
            "message": f"Successfully authenticated voter {email}"
        }, 200

    except Exception as e:
        print(f"Verify code error: {str(e)}")
        return {"error": "Failed to verify code"}, 500


@voting_bp.route('/auth/admin-login', methods=['POST'])
def admin_login() -> Tuple[Dict[str, Any], int]:
    """
    Admin authentication endpoint (mock implementation for Sprint 1).

    Request body:
        {
            "username": "admin@pta.school",
            "password": "admin123"
        }

    Returns:
        200: {"token": "jwt_token", "voter_id": "admin_id", "session_id": "session_id", "is_admin": true}
        401: {"error": "Invalid credentials"}
    """
    try:
        data = request.get_json()
        if not data:
            return {"error": "Request body required"}, 400

        username = data.get("username", "").strip()
        password = data.get("password", "").strip()

        if not username or not password:
            return {"error": "Username and password are required"}, 400

        # Check admin credentials (mock implementation)
        if username not in ADMIN_CREDENTIALS or ADMIN_CREDENTIALS[username] != password:
            return {"error": "Invalid admin credentials"}, 401

        # Create or get admin "voter" (special case)
        admin_voter = voting_data_store.create_or_get_voter(username)

        # Create JWT token
        token = jwt_manager.create_access_token(admin_voter.voter_id)

        # Create admin session
        session = voting_data_store.create_session(admin_voter.voter_id, token, is_admin=True)

        return {
            "token": token,
            "voter_id": admin_voter.voter_id,
            "session_id": session.session_id,
            "is_admin": True,
            "expires_at": session.expires_at.isoformat(),
            "message": "Admin authentication successful"
        }, 200

    except Exception as e:
        print(f"Admin login error: {str(e)}")
        return {"error": "Failed to authenticate admin"}, 500


@voting_bp.route('/auth/logout', methods=['POST'])
def logout() -> Tuple[Dict[str, str], int]:
    """
    Logout by invalidating session.

    Request headers:
        Authorization: Bearer <token>

    Returns:
        200: {"message": "Logged out successfully"}
        401: {"error": "Invalid token"}
    """
    try:
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return {"error": "Missing or invalid Authorization header"}, 401

        token = auth_header.split(' ', 1)[1]

        # Find and invalidate session
        session = voting_data_store.get_session_by_token(token)
        if session:
            voting_data_store.invalidate_session(session.session_id)

        return {"message": "Logged out successfully"}, 200

    except Exception as e:
        print(f"Logout error: {str(e)}")
        return {"error": "Logout failed"}, 500


@voting_bp.route('/auth/session', methods=['GET'])
def get_session_info() -> Tuple[Dict[str, Any], int]:
    """
    Get current session information.

    Request headers:
        Authorization: Bearer <token>

    Returns:
        200: Session and voter information
        401: {"error": "Invalid token"}
    """
    try:
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return {"error": "Missing or invalid Authorization header"}, 401

        token = auth_header.split(' ', 1)[1]

        # Find session
        session = voting_data_store.get_session_by_token(token)
        if not session:
            return {"error": "Invalid or expired session"}, 401

        # Get voter info
        voter = voting_data_store.get_voter_by_id(session.voter_id)
        if not voter:
            return {"error": "Voter not found"}, 404

        # Get voting progress
        active_election = voting_data_store.get_active_election()
        positions = voting_data_store.get_all_positions() if active_election else []
        voted_positions = list(voter.voted_positions)

        return {
            "session_id": session.session_id,
            "voter_id": voter.voter_id,
            "email": voter.email,
            "is_admin": session.is_admin,
            "expires_at": session.expires_at.isoformat(),
            "voting_progress": {
                "total_positions": len(positions),
                "voted_positions": voted_positions,
                "remaining_positions": [pos for pos in positions if pos not in voter.voted_positions]
            }
        }, 200

    except Exception as e:
        print(f"Get session info error: {str(e)}")
        return {"error": "Failed to get session info"}, 500


@voting_bp.route('/election/info', methods=['GET'])
def get_election_info() -> Tuple[Dict[str, Any], int]:
    """
    Get information about the active election.

    Returns:
        200: Election information with positions and candidates
        404: {"error": "No active election"}
    """
    try:
        active_election = voting_data_store.get_active_election()
        if not active_election:
            return {"error": "No active election found"}, 404

        positions = []
        for position in active_election.get_positions_list():
            candidates = voting_data_store.get_candidates_for_position(position)
            positions.append({
                "position": position,
                "candidates": [candidate.to_dict() for candidate in candidates]
            })

        return {
            "election_id": active_election.election_id,
            "name": active_election.name,
            "description": active_election.description,
            "is_active": active_election.is_voting_period_active(),
            "positions": positions,
            "stats": voting_data_store.get_stats()
        }, 200

    except Exception as e:
        print(f"Get election info error: {str(e)}")
        return {"error": "Failed to get election info"}, 500