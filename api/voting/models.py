"""
PTA Voting System Data Models
Unified models supporting both Pydantic (FastAPI) and dataclass patterns with dual framework support.
"""

from datetime import datetime, timedelta
from typing import Optional, Set, Dict, Any, List, Literal, Union
from uuid import uuid4
import secrets

# Conditional imports for framework flexibility
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

# Legacy enum support for backward compatibility
try:
    from enum import Enum

    class Position(Enum):
        """Available PTA positions for voting (legacy support)"""
        PRESIDENT = "president"
        VICE_PRESIDENT = "vice_president"
        SECRETARY = "secretary"
        TREASURER = "treasurer"

    class ElectionStatus(Enum):
        """Election status states (legacy support)"""
        SETUP = "setup"
        OPEN = "open"
        CLOSED = "closed"

    class AuditAction(Enum):
        """Actions that get logged for audit trail (legacy support)"""
        LOGIN = "login"
        VOTE_CAST = "vote_cast"
        BALLOT_VIEW = "ballot_view"

except ImportError:
    # Fallback classes if enum not available
    class Position:
        PRESIDENT = "president"
        VICE_PRESIDENT = "vice_president"
        SECRETARY = "secretary"
        TREASURER = "treasurer"

    class ElectionStatus:
        SETUP = "setup"
        OPEN = "open"
        CLOSED = "closed"

    class AuditAction:
        LOGIN = "login"
        VOTE_CAST = "vote_cast"
        BALLOT_VIEW = "ballot_view"


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
        """Pydantic voter model for FastAPI applications."""
        voter_id: str = Field(default_factory=lambda: str(uuid4()))
        email: EmailStr
        verification_code: Optional[str] = None
        code_expires_at: Optional[datetime] = None
        voted_positions: Set[str] = Field(default_factory=set)
        created_at: datetime = Field(default_factory=datetime.utcnow)
        last_login: Optional[datetime] = None

        class Config:
            arbitrary_types_allowed = True


    class Session(BaseModel, SessionMixin):
        """Pydantic session model for FastAPI applications."""
        session_id: str = Field(default_factory=lambda: str(uuid4()))
        voter_id: str
        token: str
        created_at: datetime = Field(default_factory=datetime.utcnow)
        expires_at: datetime = Field(default=None)
        is_admin: bool = False

        def __init__(self, **data):
            super().__init__(**data)
            # Set default expiration if not provided
            if not self.expires_at:
                self.expires_at = self.created_at + timedelta(hours=2)

        class Config:
            arbitrary_types_allowed = True


    class Admin(BaseModel):
        """Pydantic admin model for secure admin management."""
        admin_id: str = Field(default_factory=lambda: str(uuid4()))
        email: EmailStr
        password_hash: str
        full_name: str
        created_at: datetime = Field(default_factory=datetime.utcnow)
        last_login: Optional[datetime] = None
        is_active: bool = True
        failed_login_attempts: int = 0
        locked_until: Optional[datetime] = None

        class Config:
            arbitrary_types_allowed = True


    class Candidate(BaseModel):
        """Pydantic candidate model for FastAPI applications."""
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
        """Pydantic vote model for FastAPI applications."""
        vote_id: str = Field(default_factory=lambda: str(uuid4()))
        candidate_id: str
        position: str
        timestamp: datetime = Field(default_factory=datetime.utcnow)
        # Note: No voter_id to maintain anonymity


    class AuditLog(BaseModel):
        """Pydantic audit log model for FastAPI applications."""
        log_id: str = Field(default_factory=lambda: str(uuid4()))
        voter_id: str
        action: Literal["LOGIN", "VOTE_CAST", "ADMIN_ACTION", "BALLOT_VIEW"]
        position: Optional[str] = None  # Only for VOTE_CAST
        timestamp: datetime = Field(default_factory=datetime.utcnow)
        metadata: Dict[str, Any] = Field(default_factory=dict)


    class Election(BaseModel):
        """Pydantic election model for FastAPI applications."""
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

        def get_positions_list(self) -> list:
            """Get positions as a sorted list."""
            return sorted(list(self.positions))


    class VerificationCode(BaseModel):
        """Pydantic verification code model for FastAPI applications."""
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


    # Legacy Pydantic models for backward compatibility with FastAPI approach
    class VerificationRequest(BaseModel):
        """Request model for verification code"""
        email: EmailStr

    class VerificationResponse(BaseModel):
        """Response model for verification code request"""
        message: str

    class VerifyCodeRequest(BaseModel):
        """Request model for code verification"""
        email: EmailStr
        code: str

    class VerifyCodeResponse(BaseModel):
        """Response model for successful verification"""
        token: str
        voter_id: str

    class VoteRequest(BaseModel):
        """Request model for casting votes"""
        votes: dict  # position -> candidate_id

    class VoteResponse(BaseModel):
        """Response model for vote submission"""
        message: str
        votes_cast: int

    class VoterStatusResponse(BaseModel):
        """Response model for voter status"""
        voter_id: str
        voted_positions: list
        can_vote: list

    class CandidateResponse(BaseModel):
        """Response model for candidate information"""
        candidate_id: str
        name: str
        bio: Optional[str]
        photo_url: Optional[str]
        position: str

    class BallotResponse(BaseModel):
        """Response model for ballot information"""
        positions: dict
        election_status: str


# ============================================================================
# Dataclass Models (for Flask/general use)
# ============================================================================

if DATACLASSES_AVAILABLE:

    @dataclass
    class VoterDataclass(VoterMixin):
        """Dataclass version of Voter for Flask applications."""
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
        """Dataclass version of Session for Flask applications."""
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
    class AdminDataclass:
        """Dataclass version of Admin for Flask applications."""
        admin_id: str
        email: str
        password_hash: str
        full_name: str
        created_at: datetime = field(default_factory=datetime.now)
        last_login: Optional[datetime] = None
        is_active: bool = True
        failed_login_attempts: int = 0
        locked_until: Optional[datetime] = None

        def __post_init__(self):
            """Ensure email is lowercase for consistency."""
            self.email = self.email.lower().strip()


    @dataclass
    class CandidateDataclass:
        """Dataclass version of Candidate for Flask applications."""
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
    class VoteDataclass:
        """Dataclass version of Vote for Flask applications."""
        vote_id: str
        position: str
        candidate_id: str
        timestamp: datetime = field(default_factory=datetime.now)


    @dataclass
    class AuditLogDataclass:
        """Dataclass version of AuditLog for Flask applications."""
        log_id: str
        voter_id: str
        action: str
        position: Optional[str] = None
        timestamp: datetime = field(default_factory=datetime.now)
        metadata: Dict[str, Any] = field(default_factory=dict)


    @dataclass
    class ElectionDataclass:
        """Dataclass version of Election for Flask applications."""
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
    Admin = AdminDataclass
    Candidate = CandidateDataclass
    Vote = VoteDataclass
    AuditLog = AuditLogDataclass
    Election = ElectionDataclass


# ============================================================================
# Utility Functions
# ============================================================================

def generate_voter_id() -> str:
    """Generate a unique voter ID."""
    return f"voter_{uuid4().hex[:12]}"


def generate_session_id() -> str:
    """Generate a unique session ID."""
    return f"session_{uuid4().hex[:16]}"


def generate_admin_id() -> str:
    """Generate a unique admin ID."""
    return f"admin_{uuid4().hex[:12]}"


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