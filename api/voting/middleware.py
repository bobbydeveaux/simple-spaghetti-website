"""
PTA Voting System Middleware
Authentication and authorization middleware for voter sessions.
"""

from functools import wraps
from flask import request, jsonify, g
from typing import Optional, Callable, Any

from .data_store import voting_data_store
from .models import Session, Voter


def get_token_from_request() -> Optional[str]:
    """Extract JWT token from Authorization header."""
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return None
    return auth_header.split(' ', 1)[1] if len(auth_header.split(' ', 1)) == 2 else None


def validate_voter_session(token: str) -> tuple[Optional[Session], Optional[Voter]]:
    """
    Validate voter session token and return session and voter objects.

    Args:
        token: JWT token from Authorization header

    Returns:
        tuple: (session, voter) if valid, (None, None) if invalid
    """
    try:
        # Find session by token
        session = voting_data_store.get_session_by_token(token)
        if not session:
            return None, None

        # Get voter
        voter = voting_data_store.get_voter_by_id(session.voter_id)
        if not voter:
            return None, None

        return session, voter

    except Exception as e:
        print(f"Session validation error: {str(e)}")
        return None, None


def voter_required(f: Callable) -> Callable:
    """
    Decorator to require valid voter authentication.

    Sets g.session and g.voter for use in the decorated function.
    Returns 401 if authentication fails.

    Usage:
        @voter_required
        def protected_endpoint():
            voter_id = g.voter.voter_id
            is_admin = g.session.is_admin
            # ... endpoint logic
    """
    @wraps(f)
    def decorated_function(*args, **kwargs) -> Any:
        token = get_token_from_request()
        if not token:
            return jsonify({
                "error": "Missing Authorization header",
                "details": "Please provide 'Authorization: Bearer <token>' header"
            }), 401

        session, voter = validate_voter_session(token)
        if not session or not voter:
            return jsonify({
                "error": "Invalid or expired authentication token",
                "details": "Please log in again to get a valid token"
            }), 401

        # Store session and voter in Flask's g object for use in the endpoint
        g.session = session
        g.voter = voter

        return f(*args, **kwargs)

    return decorated_function


def admin_required(f: Callable) -> Callable:
    """
    Decorator to require admin authentication.

    Combines voter authentication with admin role check.
    Sets g.session and g.voter for use in the decorated function.
    Returns 401 if authentication fails, 403 if not admin.

    Usage:
        @admin_required
        def admin_endpoint():
            voter_id = g.voter.voter_id
            # ... admin endpoint logic
    """
    @wraps(f)
    def decorated_function(*args, **kwargs) -> Any:
        token = get_token_from_request()
        if not token:
            return jsonify({
                "error": "Missing Authorization header",
                "details": "Please provide 'Authorization: Bearer <token>' header"
            }), 401

        session, voter = validate_voter_session(token)
        if not session or not voter:
            return jsonify({
                "error": "Invalid or expired authentication token",
                "details": "Please log in again to get a valid token"
            }), 401

        if not session.is_admin:
            return jsonify({
                "error": "Admin access required",
                "details": "This endpoint requires administrator privileges"
            }), 403

        # Store session and voter in Flask's g object for use in the endpoint
        g.session = session
        g.voter = voter

        return f(*args, **kwargs)

    return decorated_function


def optional_voter_auth(f: Callable) -> Callable:
    """
    Decorator that provides optional voter authentication.

    If authentication is present and valid, sets g.session and g.voter.
    If authentication is missing or invalid, sets g.session = None and g.voter = None.
    Never returns authentication errors - always proceeds to the endpoint.

    Useful for endpoints that behave differently for authenticated vs anonymous users.

    Usage:
        @optional_voter_auth
        def public_endpoint():
            if g.voter:
                # Authenticated user logic
                voter_id = g.voter.voter_id
            else:
                # Anonymous user logic
            # ... endpoint logic
    """
    @wraps(f)
    def decorated_function(*args, **kwargs) -> Any:
        token = get_token_from_request()

        if token:
            session, voter = validate_voter_session(token)
            g.session = session
            g.voter = voter
        else:
            g.session = None
            g.voter = None

        return f(*args, **kwargs)

    return decorated_function


def check_voting_allowed(position: str) -> tuple[bool, Optional[str]]:
    """
    Check if voting is allowed for a given position.

    Args:
        position: The position to check (e.g., "president")

    Returns:
        tuple: (is_allowed, error_message)
            - is_allowed: True if voting is allowed, False otherwise
            - error_message: None if allowed, error message if not allowed
    """
    # Check if there's an active election
    active_election = voting_data_store.get_active_election()
    if not active_election:
        return False, "No active election"

    if not active_election.is_voting_period_active():
        return False, "Voting period is not active"

    # Check if position exists in the election
    if position not in active_election.positions:
        return False, f"Position '{position}' not found in election"

    # Check if there are candidates for this position
    candidates = voting_data_store.get_candidates_for_position(position)
    if not candidates:
        return False, f"No candidates available for position '{position}'"

    return True, None


def validate_vote_eligibility(voter: Voter, position: str) -> tuple[bool, Optional[str]]:
    """
    Validate if a voter is eligible to vote for a specific position.

    Args:
        voter: The voter object
        position: The position to vote for

    Returns:
        tuple: (is_eligible, error_message)
    """
    # Check if voter has already voted for this position
    if voter.has_voted_for_position(position):
        return False, f"You have already voted for the position '{position}'"

    # Check if voting is allowed for this position
    voting_allowed, error_msg = check_voting_allowed(position)
    if not voting_allowed:
        return False, error_msg

    return True, None


# Utility functions for session management

def cleanup_expired_data():
    """Clean up expired sessions and verification codes."""
    voting_data_store.cleanup_expired_sessions()
    voting_data_store.cleanup_expired_codes()


def get_current_voter() -> Optional[Voter]:
    """Get the current authenticated voter from Flask's g object."""
    return getattr(g, 'voter', None)


def get_current_session() -> Optional[Session]:
    """Get the current session from Flask's g object."""
    return getattr(g, 'session', None)


def is_current_user_admin() -> bool:
    """Check if the current user is an admin."""
    session = get_current_session()
    return session.is_admin if session else False