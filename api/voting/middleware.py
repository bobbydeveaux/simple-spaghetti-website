"""
PTA Voting System Middleware
Unified authentication and authorization middleware supporting both FastAPI and Flask.
"""

# Standard library imports
from functools import wraps
from datetime import datetime
from typing import Optional, Callable, Any, Union, Tuple
import jwt

# Framework-specific imports (conditional)
try:
    from fastapi import HTTPException, Header, Depends
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

try:
    from flask import request, jsonify, g
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False

# Local imports
from api.voting.models import Session, Voter


# ============================================================================
# Exception Classes
# ============================================================================

class VotingAuthenticationError(Exception):
    """Base exception for voting authentication errors."""
    pass


class SessionNotFoundError(VotingAuthenticationError):
    """Raised when session is not found in data store."""
    pass


class SessionExpiredError(VotingAuthenticationError):
    """Raised when JWT token or session has expired."""
    pass


# ============================================================================
# Token Extraction and Session Validation
# ============================================================================

def get_token_from_header(authorization: Optional[str] = None) -> Optional[str]:
    """
    Extract JWT token from Authorization header.

    Works with both FastAPI (via parameter) and Flask (via request).
    """
    if authorization is None:
        # Flask mode - get from request
        if FLASK_AVAILABLE:
            authorization = request.headers.get('Authorization', '')
        else:
            return None

    if not authorization or not authorization.startswith('Bearer '):
        return None

    parts = authorization.split(' ', 1)
    return parts[1] if len(parts) == 2 else None


def validate_session_from_token(token: str) -> Union[Session, Tuple[Optional[Session], Optional[Voter]]]:
    """
    Validate session from JWT token.

    Returns Session object for FastAPI mode, or (Session, Voter) tuple for Flask mode.
    """
    try:
        # Import here to avoid circular imports
        from api.utils.jwt_manager import jwt_manager

        # Try Flask data store first
        if FLASK_AVAILABLE:
            try:
                from .data_store import voting_data_store

                # Find session by token
                session = voting_data_store.get_session_by_token(token)
                if session:
                    voter = voting_data_store.get_voter_by_id(session.voter_id)
                    if voter:
                        return session, voter
            except (ImportError, AttributeError):
                pass

        # Fallback to JWT validation (FastAPI mode)
        payload = jwt_manager.decode_token(token)

        session = Session(
            session_id="jwt-session-" + payload.get("voter_id", "unknown"),
            voter_id=payload.get("voter_id", "unknown"),
            token=token,
            created_at=datetime.utcnow(),
            expires_at=datetime.fromtimestamp(payload["exp"]),
            is_admin=payload.get("is_admin", False)
        )

        # Check if session is expired
        if datetime.utcnow() > session.expires_at:
            raise SessionExpiredError("Session has expired")

        return session

    except jwt.ExpiredSignatureError:
        raise SessionExpiredError("Token has expired")
    except jwt.InvalidTokenError as e:
        raise VotingAuthenticationError(f"Invalid token: {str(e)}")
    except Exception as e:
        print(f"Session validation error: {str(e)}")
        if FLASK_AVAILABLE:
            return None, None
        raise VotingAuthenticationError(f"Token validation failed: {str(e)}")


# ============================================================================
# FastAPI Dependencies (when FastAPI is available)
# ============================================================================

if FASTAPI_AVAILABLE:

    def verify_voting_session(authorization: Optional[str] = Header(None)) -> Session:
        """
        FastAPI dependency to verify voting session JWT tokens.
        """
        if not authorization:
            raise HTTPException(
                status_code=401,
                detail="Authorization header required",
                headers={"WWW-Authenticate": "Bearer"}
            )

        token = get_token_from_header(authorization)
        if not token:
            raise HTTPException(
                status_code=401,
                detail="Invalid authorization header format. Must be 'Bearer <token>'",
                headers={"WWW-Authenticate": "Bearer"}
            )

        try:
            result = validate_session_from_token(token)
            if isinstance(result, tuple):
                session, voter = result
                if not session or not voter:
                    raise SessionNotFoundError("Session validation failed")
                return session
            else:
                return result

        except SessionNotFoundError:
            raise HTTPException(
                status_code=401,
                detail="Session not found or invalid",
                headers={"WWW-Authenticate": "Bearer"}
            )
        except SessionExpiredError:
            raise HTTPException(
                status_code=401,
                detail="Session has expired",
                headers={"WWW-Authenticate": "Bearer"}
            )
        except VotingAuthenticationError as e:
            raise HTTPException(
                status_code=401,
                detail=f"Authentication failed: {str(e)}",
                headers={"WWW-Authenticate": "Bearer"}
            )


    def verify_admin_session(authorization: Optional[str] = Header(None)) -> Session:
        """
        FastAPI dependency to verify admin session JWT tokens.
        """
        session = verify_voting_session(authorization)

        if not session.is_admin:
            raise HTTPException(
                status_code=403,
                detail="Admin privileges required"
            )

        return session


    def validate_token_direct(token: str) -> Session:
        """
        Directly validate a token without FastAPI dependency injection.
        """
        result = validate_session_from_token(token)
        if isinstance(result, tuple):
            session, voter = result
            if not session or not voter:
                raise VotingAuthenticationError("Session validation failed")
            return session
        else:
            return result


# ============================================================================
# Flask Decorators (when Flask is available)
# ============================================================================

if FLASK_AVAILABLE:

    def voter_required(f: Callable) -> Callable:
        """
        Flask decorator to require valid voter authentication.
        """
        @wraps(f)
        def decorated_function(*args, **kwargs) -> Any:
            token = get_token_from_header()
            if not token:
                return jsonify({
                    "error": "Missing Authorization header",
                    "details": "Please provide 'Authorization: Bearer <token>' header"
                }), 401

            try:
                result = validate_session_from_token(token)
                if isinstance(result, tuple):
                    session, voter = result
                    if not session or not voter:
                        raise SessionNotFoundError("Session validation failed")
                else:
                    # FastAPI mode result, create voter from session
                    session = result
                    voter = Voter(
                        voter_id=session.voter_id,
                        email="unknown@example.com"  # Placeholder
                    )

                # Store session and voter in Flask's g object
                g.session = session
                g.voter = voter

                return f(*args, **kwargs)

            except (SessionNotFoundError, SessionExpiredError, VotingAuthenticationError):
                return jsonify({
                    "error": "Invalid or expired authentication token",
                    "details": "Please log in again to get a valid token"
                }), 401

        return decorated_function


    def admin_required(f: Callable) -> Callable:
        """
        Flask decorator to require admin authentication.
        """
        @wraps(f)
        def decorated_function(*args, **kwargs) -> Any:
            token = get_token_from_header()
            if not token:
                return jsonify({
                    "error": "Missing Authorization header",
                    "details": "Please provide 'Authorization: Bearer <token>' header"
                }), 401

            try:
                result = validate_session_from_token(token)
                if isinstance(result, tuple):
                    session, voter = result
                    if not session or not voter:
                        raise SessionNotFoundError("Session validation failed")
                else:
                    # FastAPI mode result, create voter from session
                    session = result
                    voter = Voter(
                        voter_id=session.voter_id,
                        email="unknown@example.com"  # Placeholder
                    )

                if not session.is_admin:
                    return jsonify({
                        "error": "Admin access required",
                        "details": "This endpoint requires administrator privileges"
                    }), 403

                # Store session and voter in Flask's g object
                g.session = session
                g.voter = voter

                return f(*args, **kwargs)

            except (SessionNotFoundError, SessionExpiredError, VotingAuthenticationError):
                return jsonify({
                    "error": "Invalid or expired authentication token",
                    "details": "Please log in again to get a valid token"
                }), 401

        return decorated_function


    def optional_voter_auth(f: Callable) -> Callable:
        """
        Flask decorator that provides optional voter authentication.
        """
        @wraps(f)
        def decorated_function(*args, **kwargs) -> Any:
            token = get_token_from_header()

            if token:
                try:
                    result = validate_session_from_token(token)
                    if isinstance(result, tuple):
                        session, voter = result
                        if session and voter:
                            g.session = session
                            g.voter = voter
                        else:
                            g.session = None
                            g.voter = None
                    else:
                        # FastAPI mode result
                        session = result
                        g.session = session
                        g.voter = Voter(
                            voter_id=session.voter_id,
                            email="unknown@example.com"
                        )
                except (SessionNotFoundError, SessionExpiredError, VotingAuthenticationError):
                    g.session = None
                    g.voter = None
            else:
                g.session = None
                g.voter = None

            return f(*args, **kwargs)

        return decorated_function


    # Utility functions for Flask
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


    def check_voting_allowed(position: str) -> tuple[bool, Optional[str]]:
        """
        Check if voting is allowed for a given position.
        """
        try:
            from .data_store import voting_data_store

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

        except ImportError:
            return True, None  # Allow voting if data store not available


    def validate_vote_eligibility(voter: Voter, position: str) -> tuple[bool, Optional[str]]:
        """
        Validate if a voter is eligible to vote for a specific position.
        """
        # Check if voter has already voted for this position
        if hasattr(voter, 'has_voted_for_position') and voter.has_voted_for_position(position):
            return False, f"You have already voted for the position '{position}'"

        # Check if voting is allowed for this position
        voting_allowed, error_msg = check_voting_allowed(position)
        if not voting_allowed:
            return False, error_msg

        return True, None


    def cleanup_expired_data():
        """Clean up expired sessions and verification codes."""
        try:
            from .data_store import voting_data_store
            voting_data_store.cleanup_expired_sessions()
            voting_data_store.cleanup_expired_codes()
        except ImportError:
            pass  # Skip if data store not available
