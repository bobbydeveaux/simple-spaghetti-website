"""Pydantic models for PTA voting system."""

from datetime import datetime
from typing import Optional, Literal, List, Set
from uuid import uuid4
from pydantic import BaseModel, Field, EmailStr


class Voter(BaseModel):
    voter_id: str = Field(default_factory=lambda: str(uuid4()))
    email: EmailStr
    verification_code: Optional[str] = None
    code_expires_at: Optional[datetime] = None
    voted_positions: Set[str] = Field(default_factory=set)


class Candidate(BaseModel):
    candidate_id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    position: str
    bio: Optional[str] = None
    photo_url: Optional[str] = None


class Vote(BaseModel):
    vote_id: str = Field(default_factory=lambda: str(uuid4()))
    candidate_id: str
    position: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    # Note: No voter_id to maintain anonymity


class Session(BaseModel):
    session_id: str = Field(default_factory=lambda: str(uuid4()))
    voter_id: str
    token: str
    created_at: datetime
    expires_at: datetime
    is_admin: bool = False


class AuditLog(BaseModel):
    log_id: str = Field(default_factory=lambda: str(uuid4()))
    voter_id: str
    action: Literal["LOGIN", "VOTE_CAST", "ADMIN_ACTION"]
    position: Optional[str] = None  # Only for VOTE_CAST
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class Election(BaseModel):
    election_id: str = Field(default_factory=lambda: str(uuid4()))
    positions: List[str]
    status: Literal["SETUP", "ACTIVE", "CLOSED"]
    created_at: datetime = Field(default_factory=datetime.utcnow)


# Request/Response models for API
class VoteSubmission(BaseModel):
    position: str
    candidate_id: str


class CandidateResult(BaseModel):
    candidate_id: str
    candidate_name: str
    vote_count: int
    percentage: float