"""
PTA Voting System Data Models
Defines all data structures for voters, sessions, elections, candidates, votes, and audit logs.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, Set, Dict, Any
from uuid import uuid4
import secrets


@dataclass
class Voter:
    """
    Represents a voter in the PTA voting system.

    Note: voter_id is NOT linked to actual vote records to maintain anonymity.
    The voted_positions set tracks which positions the voter has voted on,
    but not their actual choices.
    """
    voter_id: str
    email: str
    voted_positions: Set[str] = field(default_factory=set)
    created_at: datetime = field(default_factory=datetime.now)
    last_login: Optional[datetime] = None

    def __post_init__(self):
        """Ensure email is lowercase for consistency."""
        self.email = self.email.lower().strip()

    def has_voted_for_position(self, position: str) -> bool:
        """Check if voter has already voted for a specific position."""
        return position in self.voted_positions

    def mark_voted_for_position(self, position: str):
        """Mark that voter has voted for a position (no vote choice stored)."""
        self.voted_positions.add(position)


@dataclass
class Session:
    """
    Represents an active voter session.
    Sessions are used to maintain authenticated state without storing credentials.
    """
    session_id: str
    voter_id: str
    token: str
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: datetime = field(default=None)
    is_admin: bool = False

    def __post_init__(self):
        """Set default expiration if not provided."""
        if self.expires_at is None:
            # Default session expiry: 2 hours
            self.expires_at = self.created_at + timedelta(hours=2)

    def is_expired(self) -> bool:
        """Check if session has expired."""
        return datetime.now() > self.expires_at

    def is_valid(self) -> bool:
        """Check if session is still valid (not expired)."""
        return not self.is_expired()


@dataclass
class VerificationCode:
    """
    Represents a temporary verification code for voter authentication.
    Codes expire after 15 minutes for security.
    """
    code: str
    email: str
    voter_id: str
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: datetime = field(default=None)
    used: bool = False

    def __post_init__(self):
        """Set default expiration if not provided."""
        if self.expires_at is None:
            # Default code expiry: 15 minutes
            self.expires_at = self.created_at + timedelta(minutes=15)

    def is_expired(self) -> bool:
        """Check if verification code has expired."""
        return datetime.now() > self.expires_at

    def is_valid(self) -> bool:
        """Check if code is still valid (not expired and not used)."""
        return not self.used and not self.is_expired()

    def use_code(self) -> bool:
        """Mark code as used. Returns True if successful, False if already used/expired."""
        if not self.is_valid():
            return False
        self.used = True
        return True


@dataclass
class Candidate:
    """
    Represents a candidate for a specific position in the election.
    """
    candidate_id: str
    position: str  # e.g., "president", "vice_president", "treasurer"
    name: str
    bio: str = ""
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert candidate to dictionary for API responses."""
        return {
            "candidate_id": self.candidate_id,
            "position": self.position,
            "name": self.name,
            "bio": self.bio
        }


@dataclass
class Vote:
    """
    Represents an anonymous vote.

    CRITICAL: No voter_id is stored to maintain voter anonymity.
    Votes cannot be traced back to specific voters.
    """
    vote_id: str
    position: str  # e.g., "president", "vice_president"
    candidate_id: str
    timestamp: datetime = field(default_factory=datetime.now)

    # Explicitly NO voter_id field to ensure anonymity


@dataclass
class AuditLog:
    """
    Represents an audit log entry for tracking system actions.

    Note: Contains voter_id and action but NOT vote choices to maintain
    the separation between voter tracking and actual votes.
    """
    log_id: str
    voter_id: str
    action: str  # e.g., "login", "vote_cast", "session_created"
    position: Optional[str] = None  # Position voted on (but not choice)
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Election:
    """
    Represents election configuration and metadata.
    """
    election_id: str
    name: str
    description: str = ""
    positions: Set[str] = field(default_factory=set)  # Available positions
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.now)

    def is_voting_period_active(self) -> bool:
        """Check if voting is currently allowed based on start/end times."""
        if not self.is_active:
            return False

        now = datetime.now()
        if self.start_time and now < self.start_time:
            return False
        if self.end_time and now > self.end_time:
            return False

        return True

    def add_position(self, position: str):
        """Add a position to the election."""
        self.positions.add(position)

    def get_positions_list(self) -> list:
        """Get positions as a sorted list."""
        return sorted(list(self.positions))


# Utility functions for generating IDs and codes

def generate_voter_id() -> str:
    """Generate a unique voter ID."""
    return f"voter_{uuid4().hex[:12]}"


def generate_session_id() -> str:
    """Generate a unique session ID."""
    return f"session_{uuid4().hex[:16]}"


def generate_verification_code() -> str:
    """Generate a 6-digit verification code."""
    return f"{secrets.randbelow(900000) + 100000:06d}"


def generate_candidate_id() -> str:
    """Generate a unique candidate ID."""
    return f"candidate_{uuid4().hex[:12]}"


def generate_vote_id() -> str:
    """Generate a unique vote ID."""
    return f"vote_{uuid4().hex[:12]}"


def generate_audit_log_id() -> str:
    """Generate a unique audit log ID."""
    return f"audit_{uuid4().hex[:12]}"


def generate_election_id() -> str:
    """Generate a unique election ID."""
    return f"election_{uuid4().hex[:12]}"