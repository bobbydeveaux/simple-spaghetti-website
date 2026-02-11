"""
PTA Voting System Data Models
Unified models supporting both Pydantic (FastAPI) and dataclass patterns.
"""

from datetime import datetime, timedelta
from typing import Optional, Set, Dict, Any, List, Literal, Union
from uuid import uuid4
import secrets

# Conditional imports
try:
    from pydantic import BaseModel, Field, EmailStr
    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False
    BaseModel = object  # Fallback
    EmailStr = str

try:
    from dataclasses import dataclass, field
    DATACLASSES_AVAILABLE = True
except ImportError:
    DATACLASSES_AVAILABLE = False


# ============================================================================
# Base Classes and Mixins
# ============================================================================

class VoterMixin:
    """Common voter functionality."""

    def has_voted_for_position(self, position: str) -> bool:
        """Check if voter has already voted for a specific position."""
        return position in getattr(self, 'voted_positions', set())

    def mark_voted_for_position(self, position: str):
        """Mark that voter has voted for a position (no vote choice stored)."""
        if not hasattr(self, 'voted_positions'):
            self.voted_positions = set()
        self.voted_positions.add(position)


class SessionMixin:
    """Common session functionality."""

    def is_expired(self) -> bool:
        """Check if session has expired."""
        expires_at = getattr(self, 'expires_at', None)
        if expires_at is None:
            return False
        return datetime.now() > expires_at

    def is_valid(self) -> bool:
        """Check if session is still valid (not expired)."""
        return not self.is_expired()


# ============================================================================
# Pydantic Models (for FastAPI)
# ============================================================================

if PYDANTIC_AVAILABLE:

    class Voter(BaseModel, VoterMixin):
        voter_id: str = Field(default_factory=lambda: str(uuid4()))
        email: EmailStr
        verification_code: Optional[str] = None
        code_expires_at: Optional[datetime] = None
        voted_positions: Set[str] = Field(default_factory=set)
        created_at: datetime = Field(default_factory=datetime.utcnow)
        last_login: Optional[datetime] = None


    class Session(BaseModel, SessionMixin):
        session_id: str = Field(default_factory=lambda: str(uuid4()))
        voter_id: str
        token: str
        created_at: datetime
        expires_at: datetime
        is_admin: bool = False

        def __init__(self, **data):
            super().__init__(**data)
            # Set default expiration if not provided
            if 'expires_at' not in data or data['expires_at'] is None:
                self.expires_at = self.created_at + timedelta(hours=2)


    class Candidate(BaseModel):
        candidate_id: str = Field(default_factory=lambda: str(uuid4()))
        name: str
        position: str
        bio: Optional[str] = None
        photo_url: Optional[str] = None
        created_at: datetime = Field(default_factory=datetime.utcnow)

        def to_dict(self) -> Dict[str, Any]:
            """Convert candidate to dictionary for API responses."""
            return {
                "candidate_id": self.candidate_id,
                "position": self.position,
                "name": self.name,
                "bio": self.bio or ""
            }


    class Vote(BaseModel):
        vote_id: str = Field(default_factory=lambda: str(uuid4()))
        candidate_id: str
        position: str
        timestamp: datetime = Field(default_factory=datetime.utcnow)
        # Note: No voter_id to maintain anonymity


    class AuditLog(BaseModel):
        log_id: str = Field(default_factory=lambda: str(uuid4()))
        voter_id: str
        action: Literal["LOGIN", "VOTE_CAST", "ADMIN_ACTION"]
        position: Optional[str] = None  # Only for VOTE_CAST
        timestamp: datetime = Field(default_factory=datetime.utcnow)
        metadata: Dict[str, Any] = Field(default_factory=dict)


    class Election(BaseModel):
        election_id: str = Field(default_factory=lambda: str(uuid4()))
        name: str = "PTA Election"
        description: str = ""
        positions: Union[List[str], Set[str]] = Field(default_factory=list)
        status: Literal["SETUP", "ACTIVE", "CLOSED"] = "SETUP"
        start_time: Optional[datetime] = None
        end_time: Optional[datetime] = None
        is_active: bool = True
        created_at: datetime = Field(default_factory=datetime.utcnow)

        def is_voting_period_active(self) -> bool:
            """Check if voting is currently allowed based on start/end times."""
            if not self.is_active:
                return False

            now = datetime.utcnow()
            if self.start_time and now < self.start_time:
                return False
            if self.end_time and now > self.end_time:
                return False

            return True

        def add_position(self, position: str):
            """Add a position to the election."""
            if isinstance(self.positions, list):
                if position not in self.positions:
                    self.positions.append(position)
            else:
                self.positions.add(position)


    # Request/Response models for API
    class VoteSubmission(BaseModel):
        position: str
        candidate_id: str


    class CandidateResult(BaseModel):
        candidate_id: str
        candidate_name: str
        vote_count: int
        percentage: float


    class VerificationCode(BaseModel):
        code: str
        email: EmailStr
        voter_id: str
        created_at: datetime = Field(default_factory=datetime.utcnow)
        expires_at: datetime = Field(default=None)
        used: bool = False

        def __init__(self, **data):
            super().__init__(**data)
            if self.expires_at is None:
                # Default code expiry: 15 minutes
                self.expires_at = self.created_at + timedelta(minutes=15)

        def is_expired(self) -> bool:
            """Check if verification code has expired."""
            return datetime.utcnow() > self.expires_at

        def is_valid(self) -> bool:
            """Check if code is still valid (not expired and not used)."""
            return not self.used and not self.is_expired()

        def use_code(self) -> bool:
            """Mark code as used. Returns True if successful, False if already used/expired."""
            if not self.is_valid():
                return False
            self.used = True
            return True


# ============================================================================
# Dataclass Models (for Flask/general use)
# ============================================================================

if DATACLASSES_AVAILABLE:

    @dataclass
    class VoterDataclass(VoterMixin):
        """
        Dataclass version of Voter for Flask applications.
        """
        voter_id: str
        email: str
        voted_positions: Set[str] = field(default_factory=set)
        created_at: datetime = field(default_factory=datetime.now)
        last_login: Optional[datetime] = None

        def __post_init__(self):
            """Ensure email is lowercase for consistency."""
            self.email = self.email.lower().strip()


    @dataclass
    class SessionDataclass(SessionMixin):
        """
        Dataclass version of Session for Flask applications.
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


    @dataclass
    class CandidateDataclass:
        """
        Dataclass version of Candidate for Flask applications.
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


# ============================================================================
# Dynamic Model Selection
# ============================================================================

# Use Pydantic models if available, otherwise fall back to dataclasses
if PYDANTIC_AVAILABLE:
    # Export Pydantic models as the primary interface
    pass  # Models already defined above
elif DATACLASSES_AVAILABLE:
    # Use dataclasses as fallback
    Voter = VoterDataclass
    Session = SessionDataclass
    Candidate = CandidateDataclass

    # Create simple classes for other models
    @dataclass
    class Vote:
        vote_id: str
        position: str
        candidate_id: str
        timestamp: datetime = field(default_factory=datetime.now)


    @dataclass
    class AuditLog:
        log_id: str
        voter_id: str
        action: str
        position: Optional[str] = None
        timestamp: datetime = field(default_factory=datetime.now)
        metadata: Dict[str, Any] = field(default_factory=dict)


    @dataclass
    class Election:
        election_id: str
        name: str
        description: str = ""
        positions: Set[str] = field(default_factory=set)
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


# ============================================================================
# Utility Functions
# ============================================================================

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
