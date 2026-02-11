"""
PTA Voting System - Data Models
"""
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Set, Optional
from uuid import uuid4
import uuid


class Position(Enum):
    """Available PTA positions for voting"""
    PRESIDENT = "president"
    VICE_PRESIDENT = "vice_president"
    SECRETARY = "secretary"
    TREASURER = "treasurer"


class ElectionStatus(Enum):
    """Election status states"""
    SETUP = "setup"
    OPEN = "open"
    CLOSED = "closed"


class AuditAction(Enum):
    """Actions that get logged for audit trail"""
    LOGIN = "login"
    VOTE_CAST = "vote_cast"
    BALLOT_VIEW = "ballot_view"


@dataclass
class Voter:
    """Represents a voter in the system"""
    voter_id: str
    email: str
    verification_code: Optional[str]
    created_at: datetime
    voted_positions: Set[Position]

    def __init__(self, email: str):
        self.voter_id = str(uuid4())
        self.email = email
        self.verification_code = None
        self.created_at = datetime.now()
        self.voted_positions = set()


@dataclass
class Candidate:
    """Represents a candidate running for a position"""
    candidate_id: str
    name: str
    bio: str
    photo_url: Optional[str]
    position: Position

    def __init__(self, name: str, bio: str, position: Position, photo_url: Optional[str] = None):
        self.candidate_id = str(uuid4())
        self.name = name
        self.bio = bio
        self.photo_url = photo_url
        self.position = position


@dataclass
class Vote:
    """Represents an anonymous vote (no voter_id for privacy)"""
    vote_id: str
    position: Position
    candidate_id: str
    timestamp: datetime

    def __init__(self, position: Position, candidate_id: str):
        self.vote_id = str(uuid4())
        self.position = position
        self.candidate_id = candidate_id
        self.timestamp = datetime.now()


@dataclass
class Session:
    """Represents an active voter session"""
    session_id: str
    voter_id: str
    token: str
    created_at: datetime
    expires_at: datetime
    is_admin: bool

    def __init__(self, voter_id: str, token: str, expires_at: datetime, is_admin: bool = False):
        self.session_id = str(uuid4())
        self.voter_id = voter_id
        self.token = token
        self.created_at = datetime.now()
        self.expires_at = expires_at
        self.is_admin = is_admin


@dataclass
class AuditLog:
    """Audit log entry for tracking voter actions"""
    log_id: str
    voter_id: str
    action: AuditAction
    position: Optional[Position]
    timestamp: datetime

    def __init__(self, voter_id: str, action: AuditAction, position: Optional[Position] = None):
        self.log_id = str(uuid4())
        self.voter_id = voter_id
        self.action = action
        self.position = position
        self.timestamp = datetime.now()


@dataclass
class Election:
    """Represents the election configuration"""
    election_id: str
    positions: list[Position]
    status: ElectionStatus
    created_at: datetime

    def __init__(self, positions: list[Position]):
        self.election_id = str(uuid4())
        self.positions = positions
        self.status = ElectionStatus.SETUP
        self.created_at = datetime.now()


# Pydantic models for API requests/responses
from pydantic import BaseModel, EmailStr


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
    votes: dict[Position, str]  # position -> candidate_id


class VoteResponse(BaseModel):
    """Response model for vote submission"""
    message: str
    votes_cast: int


class VoterStatusResponse(BaseModel):
    """Response model for voter status"""
    voter_id: str
    voted_positions: list[Position]
    can_vote: list[Position]


class CandidateResponse(BaseModel):
    """Response model for candidate information"""
    candidate_id: str
    name: str
    bio: str
    photo_url: Optional[str]
    position: Position


class BallotResponse(BaseModel):
    """Response model for ballot information"""
    positions: dict[Position, list[CandidateResponse]]
    election_status: ElectionStatus