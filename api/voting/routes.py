"""
PTA Voting System Routes
Authentication endpoints for voter code-based authentication with FastAPI legacy support.
"""

from flask import Blueprint, request, jsonify
from typing import Dict, Any, Tuple
import re
from datetime import datetime

# Import existing JWT utilities
from api.utils.jwt_manager import JWTManager
from api.utils.password import verify_password
from api.utils.rate_limiter import auth_rate_limit, admin_rate_limit, code_request_limit
from api.utils.csrf_protection import csrf_required, get_csrf_token
from api.utils.sanitizer import (
    sanitize_email, sanitize_password, sanitize_verification_code,
    sanitize_position_name, sanitize_text_input
)
from api.config import settings
from .data_store import voting_data_store

# FastAPI legacy support
try:
    from fastapi import APIRouter, Depends, HTTPException
    from .middleware import get_current_voter_session, get_voter_id_from_session
    from .services import voter_auth_service, voting_service
    from .models import (
        VerificationRequest, VerificationResponse,
        VerifyCodeRequest, VerifyCodeResponse,
        VoteRequest, VoteResponse,
        VoterStatusResponse, BallotResponse,
        Position, Session
    )
    FASTAPI_SUPPORT = True
except ImportError:
    FASTAPI_SUPPORT = False

# Create Blueprint for voting routes
voting_bp = Blueprint('voting', __name__, url_prefix='/api/voting')

# Initialize JWT manager
jwt_manager = JWTManager()




@voting_bp.route('/auth/request-code', methods=['POST'])
@code_request_limit
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

        raw_email = data.get("email", "")

        # Sanitize and validate email
        try:
            email = sanitize_email(raw_email)
        except ValueError as e:
            return {"error": str(e)}, 400

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

        # Only include code in response for development/testing
        # In production, this code would be sent via email and not returned
        if settings.DEBUG and settings.ENVIRONMENT == "development":
            response["code"] = verification_code.code
            response["debug_message"] = "Code included for development only"

        return response, 200

    except Exception as e:
        print(f"Request verification code error: {str(e)}")
        return {"error": "Failed to send verification code"}, 500


@voting_bp.route('/auth/verify', methods=['POST'])
@auth_rate_limit
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

        raw_email = data.get("email", "")
        raw_code = data.get("code", "")

        # Sanitize and validate email
        try:
            email = sanitize_email(raw_email)
        except ValueError as e:
            return {"error": str(e)}, 400

        # Sanitize and validate verification code
        try:
            code = sanitize_verification_code(raw_code)
        except ValueError as e:
            return {"error": str(e)}, 400

        # Get and use verification code
        voter_id = voting_data_store.use_verification_code(code)
        if not voter_id:
            return {"error": "Invalid or expired verification code"}, 401

        # Verify voter matches email
        voter = voting_data_store.get_voter_by_id(voter_id)
        if not voter or voter.email != email.lower():
            return {"error": "Verification code does not match email"}, 401

        # Create JWT token with voter email
        token = jwt_manager.create_access_token(voter.email)

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
@admin_rate_limit
def admin_login() -> Tuple[Dict[str, Any], int]:
    """
    Secure admin authentication endpoint.

    Request body:
        {
            "email": "admin@example.com",
            "password": "your_admin_password"
        }

    Returns:
        200: {"token": "jwt_token", "admin_id": "admin_id", "session_id": "session_id", "is_admin": true}
        401: {"error": "Invalid credentials"}
        423: {"error": "Account temporarily locked"}
    """
    try:
        data = request.get_json()
        if not data:
            return {"error": "Request body required"}, 400

        raw_email = data.get("email", "")
        raw_password = data.get("password", "")

        # Sanitize and validate email
        try:
            email = sanitize_email(raw_email)
        except ValueError as e:
            return {"error": str(e)}, 400

        # Sanitize password (basic validation only)
        try:
            password = sanitize_password(raw_password)
        except ValueError as e:
            return {"error": str(e)}, 400

        # Get admin from database
        admin = voting_data_store.get_admin_by_email(email)
        if not admin:
            return {"error": "Invalid admin credentials"}, 401

        # Check if account is active
        if not admin.is_active:
            return {"error": "Account is disabled"}, 401

        # Check if account is temporarily locked
        if voting_data_store.is_admin_locked(admin.admin_id):
            return {"error": "Account temporarily locked due to failed login attempts"}, 423

        # Verify password
        if not verify_password(password, admin.password_hash):
            # Update failed login attempts
            voting_data_store.update_admin_login(admin.admin_id, success=False)
            return {"error": "Invalid admin credentials"}, 401

        # Successful login - update admin record
        voting_data_store.update_admin_login(admin.admin_id, success=True)

        # Create JWT token with admin email
        token = jwt_manager.create_access_token(admin.email)

        # Create admin session (use admin_id as voter_id for compatibility)
        session = voting_data_store.create_session(admin.admin_id, token, is_admin=True)

        return {
            "token": token,
            "admin_id": admin.admin_id,
            "voter_id": admin.admin_id,  # For compatibility with frontend
            "session_id": session.session_id,
            "is_admin": True,
            "email": admin.email,
            "full_name": admin.full_name,
            "expires_at": session.expires_at.isoformat(),
            "message": "Admin authentication successful"
        }, 200

    except Exception as e:
        print(f"Admin login error: {str(e)}")
        return {"error": "Failed to process admin login"}, 500


# ============================================================================
# Admin Election Management Routes
# ============================================================================

def require_admin_session():
    """Helper to validate admin session for protected routes"""
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return None, ({"error": "Authorization header missing or invalid"}, 401)

        # Safely extract token
        header_parts = auth_header.split(' ')
        if len(header_parts) != 2:
            return None, ({"error": "Invalid Authorization header format"}, 401)

        token = header_parts[1]

        # Extract email from JWT token
        email = jwt_manager.get_email_from_token(token)
        if not email:
            return None, ({"error": "Invalid or expired token"}, 401)

        # Get admin by email to validate admin status
        admin = voting_data_store.get_admin_by_email(email)
        if not admin or not admin.is_active:
            return None, ({"error": "Admin access required"}, 403)

        # Check if admin is locked
        if voting_data_store.is_admin_locked(admin.admin_id):
            return None, ({"error": "Account temporarily locked"}, 423)

        # Get session by admin_id (used as voter_id for compatibility)
        session = voting_data_store.get_session_by_voter(admin.admin_id)
        if not session or not session.is_admin:
            return None, ({"error": "Admin session required"}, 403)

        # Check if session token matches
        if session.token != token:
            return None, ({"error": "Session token mismatch"}, 401)

        # Check if session has expired
        if datetime.now() > session.expires_at:
            return None, ({"error": "Session expired"}, 401)

        return session, None

    except Exception as e:
        print(f"Admin session validation error: {str(e)}")
        return None, ({"error": "Failed to validate admin session"}, 500)

@voting_bp.route('/admin/csrf-token', methods=['GET'])
def get_csrf_token_endpoint():
    """Get CSRF token for admin operations"""
    session, error_response = require_admin_session()
    if error_response:
        return error_response

    try:
        token = get_csrf_token()
        return {"csrf_token": token}, 200
    except Exception as e:
        return {"error": f"Failed to generate CSRF token: {str(e)}"}, 500

@voting_bp.route('/admin/election', methods=['GET'])
def get_election_config():
    """Get current election configuration"""
    session, error_response = require_admin_session()
    if error_response:
        return error_response

    try:
        election = voting_data_store.get_active_election()
        if not election:
            return {"error": "No active election found"}, 404

        # Convert to dict for JSON response
        election_data = {
            "election_id": election.election_id,
            "name": election.name,
            "description": election.description,
            "positions": list(election.positions) if hasattr(election, 'positions') else [],
            "status": getattr(election, 'status', 'SETUP'),
            "start_time": election.start_time.isoformat() if election.start_time else None,
            "end_time": election.end_time.isoformat() if election.end_time else None,
            "is_active": election.is_active,
            "created_at": election.created_at.isoformat() if election.created_at else None
        }

        return {"election": election_data}, 200

    except Exception as e:
        return {"error": f"Failed to get election configuration: {str(e)}"}, 500

@voting_bp.route('/admin/election/status', methods=['PUT'])
@csrf_required
def update_election_status():
    """Update election status (SETUP/ACTIVE/CLOSED)"""
    session, error_response = require_admin_session()
    if error_response:
        return error_response

    try:
        data = request.get_json()
        new_status = data.get('status')

        if new_status not in ['SETUP', 'ACTIVE', 'CLOSED']:
            return {"error": "Invalid status. Must be SETUP, ACTIVE, or CLOSED"}, 400

        election = voting_data_store.get_active_election()
        if not election:
            return {"error": "No active election found"}, 404

        # Update election status
        if hasattr(election, 'status'):
            election.status = new_status

        # Set start time when moving to ACTIVE
        if new_status == 'ACTIVE' and not election.start_time:
            election.start_time = datetime.utcnow()

        # Set end time when moving to CLOSED
        if new_status == 'CLOSED' and not election.end_time:
            election.end_time = datetime.utcnow()
            election.is_active = False

        return {
            "message": f"Election status updated to {new_status}",
            "election": {
                "election_id": election.election_id,
                "status": new_status,
                "start_time": election.start_time.isoformat() if election.start_time else None,
                "end_time": election.end_time.isoformat() if election.end_time else None
            }
        }, 200

    except Exception as e:
        return {"error": f"Failed to update election status: {str(e)}"}, 500

@voting_bp.route('/admin/election/positions', methods=['POST'])
@csrf_required
def add_election_position():
    """Add a new position to the election"""
    session, error_response = require_admin_session()
    if error_response:
        return error_response

    try:
        data = request.get_json()
        raw_position = data.get('position', '')

        if not raw_position:
            return {"error": "Position name is required"}, 400

        # Sanitize position name to prevent XSS and validate format
        try:
            position = sanitize_position_name(raw_position)
        except ValueError as e:
            return {"error": f"Invalid position name: {str(e)}"}, 400

        election = voting_data_store.get_active_election()
        if not election:
            return {"error": "No active election found"}, 404

        # Check if position already exists
        if position in election.positions:
            return {"error": f"Position '{position}' already exists"}, 409

        # Add position to election
        election.add_position(position)

        return {
            "message": f"Position '{position}' added successfully",
            "positions": list(election.positions)
        }, 200

    except Exception as e:
        return {"error": f"Failed to add position: {str(e)}"}, 500

@voting_bp.route('/admin/election/positions/<position>', methods=['DELETE'])
@csrf_required
def remove_election_position(position: str):
    """Remove a position from the election"""
    session, error_response = require_admin_session()
    if error_response:
        return error_response

    try:
        # Sanitize position parameter from URL
        try:
            sanitized_position = sanitize_position_name(position)
        except ValueError as e:
            return {"error": f"Invalid position name: {str(e)}"}, 400

        election = voting_data_store.get_active_election()
        if not election:
            return {"error": "No active election found"}, 404

        # Check if position exists
        if sanitized_position not in election.positions:
            return {"error": f"Position '{sanitized_position}' not found"}, 404

        # Remove position from election
        if hasattr(election, 'positions'):
            if isinstance(election.positions, set):
                election.positions.discard(sanitized_position)
            elif isinstance(election.positions, list):
                if sanitized_position in election.positions:
                    election.positions.remove(sanitized_position)

        return {
            "message": f"Position '{sanitized_position}' removed successfully",
            "positions": list(election.positions)
        }, 200

    except Exception as e:
        return {"error": f"Failed to remove position: {str(e)}"}, 500


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


# ============================================================================
# Admin API Endpoints
# ============================================================================

@voting_bp.route('/admin/dashboard', methods=['GET'])
def get_admin_dashboard() -> Tuple[Dict[str, Any], int]:
    """
    Get admin dashboard with system statistics and overview.

    Request headers:
        Authorization: Bearer <admin_token>

    Returns:
        200: Dashboard data with system overview, voter statistics, and audit statistics
        401: {"error": "Missing or invalid Authorization header"}
        403: {"error": "Admin privileges required"}
    """
    try:
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return {"error": "Missing or invalid Authorization header"}, 401

        token = auth_header.split(' ', 1)[1]

        # Find session and verify admin status
        session = voting_data_store.get_session_by_token(token)
        if not session:
            return {"error": "Invalid or expired session"}, 401

        if not session.is_admin:
            return {"error": "Admin privileges required"}, 403

        # Get system statistics
        stats = voting_data_store.get_stats()

        # Get active election info
        active_election = voting_data_store.get_active_election()

        # Get voting progress
        all_voters = voting_data_store.get_all_voters()
        total_eligible_votes = len(all_voters)

        # Calculate voting participation
        votes_cast_by_position = {}
        positions = voting_data_store.get_all_positions()
        for position in positions:
            votes_count = len(voting_data_store.get_votes_for_position(position))
            votes_cast_by_position[position] = votes_count

        total_possible_votes = total_eligible_votes * len(positions) if positions else 0
        total_actual_votes = sum(votes_cast_by_position.values())
        participation_rate = (total_actual_votes / total_possible_votes * 100) if total_possible_votes > 0 else 0

        return {
            "system_overview": {
                "total_voters": stats["total_voters"],
                "active_sessions": stats["active_sessions"],
                "total_votes": stats["total_votes"],
                "total_candidates": stats["total_candidates"],
                "total_positions": len(positions),
                "participation_rate": round(participation_rate, 2)
            },
            "election_info": {
                "has_active_election": active_election is not None,
                "election_name": active_election.name if active_election else None,
                "is_voting_active": active_election.is_voting_period_active() if active_election else False,
                "positions": positions
            },
            "voter_statistics": {
                "pending_verification_codes": stats["pending_codes"],
                "voters_who_voted": len([v for v in all_voters if v.voted_positions]),
                "voters_not_voted": len([v for v in all_voters if not v.voted_positions])
            },
            "audit_statistics": {
                "total_audit_entries": stats["audit_log_entries"],
                "recent_activity_count": len(voting_data_store.get_recent_audit_logs(24))
            }
        }, 200

    except Exception as e:
        print(f"Get admin dashboard error: {str(e)}")
        return {"error": "Failed to get admin dashboard"}, 500


@voting_bp.route('/admin/voters', methods=['GET'])
def get_admin_voters() -> Tuple[Dict[str, Any], int]:
    """
    Get list of all voters for admin management.

    Request headers:
        Authorization: Bearer <admin_token>

    Query parameters:
        limit: Maximum number of voters to return (default: all)
        offset: Number of voters to skip (default: 0)

    Returns:
        200: List of voters with voting status
        401: {"error": "Missing or invalid Authorization header"}
        403: {"error": "Admin privileges required"}
    """
    try:
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return {"error": "Missing or invalid Authorization header"}, 401

        token = auth_header.split(' ', 1)[1]

        # Find session and verify admin status
        session = voting_data_store.get_session_by_token(token)
        if not session:
            return {"error": "Invalid or expired session"}, 401

        if not session.is_admin:
            return {"error": "Admin privileges required"}, 403

        # Get query parameters
        limit = request.args.get('limit', type=int)
        offset = request.args.get('offset', type=int, default=0)

        # Get all voters
        all_voters = voting_data_store.get_all_voters()

        # Apply pagination
        if limit:
            paginated_voters = all_voters[offset:offset + limit]
        else:
            paginated_voters = all_voters[offset:]

        # Format voter data for admin view
        voter_list = []
        for voter in paginated_voters:
            voter_data = {
                "voter_id": voter.voter_id,
                "email": voter.email,
                "created_at": voter.created_at.isoformat() if voter.created_at else None,
                "last_login": voter.last_login.isoformat() if voter.last_login else None,
                "voted_positions": list(voter.voted_positions),
                "has_voted": len(voter.voted_positions) > 0,
                "voting_completion": f"{len(voter.voted_positions)}/{len(voting_data_store.get_all_positions())} positions"
            }
            voter_list.append(voter_data)

        return {
            "voters": voter_list,
            "pagination": {
                "total": len(all_voters),
                "offset": offset,
                "limit": limit,
                "returned": len(voter_list)
            }
        }, 200

    except Exception as e:
        print(f"Get admin voters error: {str(e)}")
        return {"error": "Failed to get voters list"}, 500


@voting_bp.route('/admin/voters/<voter_id>', methods=['GET'])
def get_admin_voter_details(voter_id: str) -> Tuple[Dict[str, Any], int]:
    """
    Get detailed information about a specific voter.

    Request headers:
        Authorization: Bearer <admin_token>

    Returns:
        200: Detailed voter information including audit history
        404: {"error": "Voter not found"}
        401: {"error": "Missing or invalid Authorization header"}
        403: {"error": "Admin privileges required"}
    """
    try:
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return {"error": "Missing or invalid Authorization header"}, 401

        token = auth_header.split(' ', 1)[1]

        # Find session and verify admin status
        session = voting_data_store.get_session_by_token(token)
        if not session:
            return {"error": "Invalid or expired session"}, 401

        if not session.is_admin:
            return {"error": "Admin privileges required"}, 403

        # Get voter details
        voter = voting_data_store.get_voter_by_id(voter_id)
        if not voter:
            return {"error": "Voter not found"}, 404

        # Get voter's audit history
        audit_logs = voting_data_store.get_audit_logs_for_voter(voter_id)

        # Get voter's active sessions
        all_sessions = voting_data_store.get_all_sessions()
        voter_sessions = [s for s in all_sessions if s.voter_id == voter_id and s.is_valid()]

        voter_details = {
            "voter_id": voter.voter_id,
            "email": voter.email,
            "created_at": voter.created_at.isoformat() if voter.created_at else None,
            "last_login": voter.last_login.isoformat() if voter.last_login else None,
            "voted_positions": list(voter.voted_positions),
            "voting_progress": {
                "positions_voted": list(voter.voted_positions),
                "total_positions": len(voting_data_store.get_all_positions()),
                "remaining_positions": [pos for pos in voting_data_store.get_all_positions() if pos not in voter.voted_positions],
                "completion_percentage": round((len(voter.voted_positions) / max(len(voting_data_store.get_all_positions()), 1)) * 100, 2)
            },
            "session_info": {
                "active_sessions": len(voter_sessions),
                "sessions": [
                    {
                        "session_id": s.session_id,
                        "created_at": s.created_at.isoformat(),
                        "expires_at": s.expires_at.isoformat(),
                        "is_admin": s.is_admin
                    }
                    for s in voter_sessions
                ]
            },
            "audit_history": [
                {
                    "log_id": log.log_id,
                    "action": log.action,
                    "position": log.position,
                    "timestamp": log.timestamp.isoformat(),
                    "metadata": log.metadata if hasattr(log, 'metadata') else {}
                }
                for log in sorted(audit_logs, key=lambda x: x.timestamp, reverse=True)[:20]  # Last 20 actions
            ]
        }

        return voter_details, 200

    except Exception as e:
        print(f"Get admin voter details error: {str(e)}")
        return {"error": "Failed to get voter details"}, 500


@voting_bp.route('/admin/audit-logs', methods=['GET'])
def get_admin_audit_logs() -> Tuple[Dict[str, Any], int]:
    """
    Get audit logs for admin monitoring.

    Request headers:
        Authorization: Bearer <admin_token>

    Query parameters:
        limit: Maximum number of logs to return (default: 50)
        offset: Number of logs to skip (default: 0)
        action: Filter by specific action type
        voter_id: Filter by specific voter

    Returns:
        200: List of audit log entries
        401: {"error": "Missing or invalid Authorization header"}
        403: {"error": "Admin privileges required"}
    """
    try:
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return {"error": "Missing or invalid Authorization header"}, 401

        token = auth_header.split(' ', 1)[1]

        # Find session and verify admin status
        session = voting_data_store.get_session_by_token(token)
        if not session:
            return {"error": "Invalid or expired session"}, 401

        if not session.is_admin:
            return {"error": "Admin privileges required"}, 403

        # Get query parameters
        limit = request.args.get('limit', type=int, default=50)
        offset = request.args.get('offset', type=int, default=0)
        action_filter = request.args.get('action')
        voter_id_filter = request.args.get('voter_id')

        # Get all audit logs
        all_logs = voting_data_store.get_all_audit_logs()

        # Apply filters
        filtered_logs = all_logs
        if action_filter:
            filtered_logs = [log for log in filtered_logs if log.action == action_filter]
        if voter_id_filter:
            filtered_logs = [log for log in filtered_logs if log.voter_id == voter_id_filter]

        # Sort by timestamp (newest first)
        sorted_logs = sorted(filtered_logs, key=lambda x: x.timestamp, reverse=True)

        # Apply pagination
        paginated_logs = sorted_logs[offset:offset + limit]

        # Format logs for response
        log_list = []
        for log in paginated_logs:
            # Get voter email for context
            voter = voting_data_store.get_voter_by_id(log.voter_id)
            log_data = {
                "log_id": log.log_id,
                "voter_id": log.voter_id,
                "voter_email": voter.email if voter else "Unknown",
                "action": log.action,
                "position": log.position,
                "timestamp": log.timestamp.isoformat(),
                "metadata": log.metadata if hasattr(log, 'metadata') else {}
            }
            log_list.append(log_data)

        return {
            "audit_logs": log_list,
            "pagination": {
                "total": len(filtered_logs),
                "offset": offset,
                "limit": limit,
                "returned": len(log_list)
            },
            "filters_applied": {
                "action": action_filter,
                "voter_id": voter_id_filter
            }
        }, 200

    except Exception as e:
        print(f"Get admin audit logs error: {str(e)}")
        return {"error": "Failed to get audit logs"}, 500


@voting_bp.route('/admin/elections', methods=['GET'])
def get_admin_elections() -> Tuple[Dict[str, Any], int]:
    """
    Get election management information for admins.

    Request headers:
        Authorization: Bearer <admin_token>

    Returns:
        200: Election information with candidates and voting statistics
        401: {"error": "Missing or invalid Authorization header"}
        403: {"error": "Admin privileges required"}
    """
    try:
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return {"error": "Missing or invalid Authorization header"}, 401

        token = auth_header.split(' ', 1)[1]

        # Find session and verify admin status
        session = voting_data_store.get_session_by_token(token)
        if not session:
            return {"error": "Invalid or expired session"}, 401

        if not session.is_admin:
            return {"error": "Admin privileges required"}, 403

        # Get active election
        active_election = voting_data_store.get_active_election()
        if not active_election:
            return {"error": "No active election found"}, 404

        # Get all candidates and organize by position
        all_candidates = voting_data_store.get_all_candidates()
        candidates_by_position = {}
        for candidate in all_candidates:
            position = candidate.position
            if position not in candidates_by_position:
                candidates_by_position[position] = []
            candidates_by_position[position].append({
                "candidate_id": candidate.candidate_id,
                "name": candidate.name,
                "bio": candidate.bio,
                "position": candidate.position
            })

        # Get voting statistics for each position
        position_stats = {}
        for position in active_election.get_positions_list():
            vote_counts = voting_data_store.get_vote_counts_for_position(position)
            total_votes_for_position = sum(vote_counts.values())
            position_stats[position] = {
                "total_votes": total_votes_for_position,
                "candidate_vote_counts": vote_counts,
                "candidates_count": len(candidates_by_position.get(position, [])),
                "voter_turnout": f"{total_votes_for_position}/{voting_data_store.get_stats()['total_voters']}"
            }

        election_data = {
            "election_id": active_election.election_id,
            "name": active_election.name,
            "description": active_election.description,
            "status": "ACTIVE" if active_election.is_voting_period_active() else "SETUP",
            "is_active": active_election.is_voting_period_active(),
            "start_time": active_election.start_time.isoformat() if active_election.start_time else None,
            "end_time": active_election.end_time.isoformat() if active_election.end_time else None,
            "positions": active_election.get_positions_list(),
            "candidates_by_position": candidates_by_position,
            "voting_statistics": position_stats,
            "overall_statistics": {
                "total_candidates": len(all_candidates),
                "total_positions": len(active_election.get_positions_list()),
                "total_votes_cast": voting_data_store.get_total_votes(),
                "eligible_voters": voting_data_store.get_stats()["total_voters"]
            }
        }

        return election_data, 200

    except Exception as e:
        print(f"Get admin elections error: {str(e)}")
        return {"error": "Failed to get election information"}, 500


@voting_bp.route('/admin/results', methods=['GET'])
def get_admin_results() -> Tuple[Dict[str, Any], int]:
    """
    Get detailed voting results for admin analysis.

    Request headers:
        Authorization: Bearer <admin_token>

    Query parameters:
        position: Get results for specific position only

    Returns:
        200: Comprehensive voting results and analytics
        401: {"error": "Missing or invalid Authorization header"}
        403: {"error": "Admin privileges required"}
    """
    try:
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return {"error": "Missing or invalid Authorization header"}, 401

        token = auth_header.split(' ', 1)[1]

        # Find session and verify admin status
        session = voting_data_store.get_session_by_token(token)
        if not session:
            return {"error": "Invalid or expired session"}, 401

        if not session.is_admin:
            return {"error": "Admin privileges required"}, 403

        # Get query parameters
        position_filter = request.args.get('position')

        # Get active election
        active_election = voting_data_store.get_active_election()
        if not active_election:
            return {"error": "No active election found"}, 404

        positions_to_analyze = [position_filter] if position_filter else active_election.get_positions_list()

        results = {}
        overall_stats = {
            "total_eligible_voters": voting_data_store.get_stats()["total_voters"],
            "total_votes_cast": voting_data_store.get_total_votes(),
            "positions_analyzed": len(positions_to_analyze)
        }

        for position in positions_to_analyze:
            # Get candidates for this position
            candidates = voting_data_store.get_candidates_for_position(position)
            candidate_lookup = {c.candidate_id: c for c in candidates}

            # Get vote counts
            vote_counts = voting_data_store.get_vote_counts_for_position(position)
            total_position_votes = sum(vote_counts.values())

            # Calculate percentages and ranking
            candidate_results = []
            for candidate_id, vote_count in vote_counts.items():
                candidate = candidate_lookup.get(candidate_id)
                percentage = (vote_count / total_position_votes * 100) if total_position_votes > 0 else 0

                candidate_results.append({
                    "candidate_id": candidate_id,
                    "candidate_name": candidate.name if candidate else "Unknown",
                    "vote_count": vote_count,
                    "percentage": round(percentage, 2),
                    "candidate_bio": candidate.bio if candidate else ""
                })

            # Sort by vote count (descending)
            candidate_results.sort(key=lambda x: x["vote_count"], reverse=True)

            # Add ranking
            for i, result in enumerate(candidate_results):
                result["rank"] = i + 1

            # Calculate voter turnout for this position
            eligible_voters = overall_stats["total_eligible_voters"]
            turnout_percentage = (total_position_votes / eligible_voters * 100) if eligible_voters > 0 else 0

            results[position] = {
                "position_name": position,
                "total_votes": total_position_votes,
                "eligible_voters": eligible_voters,
                "turnout_percentage": round(turnout_percentage, 2),
                "candidates_count": len(candidates),
                "winner": candidate_results[0] if candidate_results else None,
                "results": candidate_results
            }

        return {
            "election": {
                "election_id": active_election.election_id,
                "name": active_election.name,
                "is_active": active_election.is_voting_period_active()
            },
            "overall_statistics": overall_stats,
            "position_results": results,
            "generated_at": datetime.now().isoformat()
        }, 200

    except Exception as e:
        print(f"Get admin results error: {str(e)}")
        return {"error": "Failed to get voting results"}, 500


# ============================================================================
# FastAPI Legacy Routes (for compatibility)
# ============================================================================

if FASTAPI_SUPPORT:
    router = APIRouter(prefix="/voting", tags=["voting"])

    @router.post("/auth/request-code", response_model=VerificationResponse)
    async def fastapi_request_verification_code(request: VerificationRequest):
        """Request a verification code for email-based authentication (FastAPI version)"""
        try:
            message = voter_auth_service.request_verification_code(request.email)
            return VerificationResponse(message=message)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/auth/verify", response_model=VerifyCodeResponse)
    async def fastapi_verify_code(request: VerifyCodeRequest):
        """Verify the code and get access token (FastAPI version)"""
        token, voter_id = voter_auth_service.verify_code(request.email, request.code)
        return VerifyCodeResponse(token=token, voter_id=voter_id)

    @router.get("/ballot", response_model=BallotResponse)
    async def fastapi_get_ballot(session: Session = Depends(get_current_voter_session)):
        """Get the current ballot with all candidates (FastAPI version)"""
        # Log ballot view for audit
        from .models import AuditLog, AuditAction
        from .data_store import voting_data_store

        audit_log = AuditLog(session.voter_id, AuditAction.BALLOT_VIEW)
        voting_data_store.add_audit_log(audit_log)

        return voting_service.get_ballot()

    @router.get("/status", response_model=VoterStatusResponse)
    async def fastapi_get_voter_status(session: Session = Depends(get_current_voter_session)):
        """Get the current voter's status (FastAPI version)"""
        voter_id = get_voter_id_from_session(session)
        return voter_auth_service.get_voter_status(voter_id)

    @router.post("/vote", response_model=VoteResponse)
    async def fastapi_cast_votes(
        request: VoteRequest,
        session: Session = Depends(get_current_voter_session)
    ):
        """Cast votes for selected candidates (FastAPI version)"""
        voter_id = get_voter_id_from_session(session)

        # Convert string keys back to Position enums
        votes_dict = {}
        for position_str, candidate_id in request.votes.items():
            try:
                if isinstance(position_str, str):
                    # Handle string position keys
                    position = Position(position_str)
                else:
                    # Handle Position enum keys
                    position = position_str
                votes_dict[position] = candidate_id
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid position: {position_str}"
                )

        message, votes_cast = voting_service.cast_votes(voter_id, votes_dict)
        return VoteResponse(message=message, votes_cast=votes_cast)

    @router.get("/health")
    async def fastapi_health_check():
        """Health check endpoint (FastAPI version)"""
        return {"status": "healthy", "service": "pta-voting-system"}

    # Export the FastAPI router for integration
    __all__ = ['voting_bp', 'router']
else:
    # Only export Flask blueprint if FastAPI not available
    __all__ = ['voting_bp']
