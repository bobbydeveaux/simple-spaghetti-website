"""
PTA Voting System - API Routes
"""
from fastapi import APIRouter, Depends, HTTPException
from typing import Dict

from .middleware import get_current_voter_session, get_voter_id_from_session
from .services import voter_auth_service, voting_service
from .models import (
    VerificationRequest, VerificationResponse,
    VerifyCodeRequest, VerifyCodeResponse,
    VoteRequest, VoteResponse,
    VoterStatusResponse, BallotResponse,
    Position, Session
)


router = APIRouter(prefix="/voting", tags=["voting"])


@router.post("/auth/request-code", response_model=VerificationResponse)
async def request_verification_code(request: VerificationRequest):
    """Request a verification code for email-based authentication"""
    try:
        message = voter_auth_service.request_verification_code(request.email)
        return VerificationResponse(message=message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/auth/verify", response_model=VerifyCodeResponse)
async def verify_code(request: VerifyCodeRequest):
    """Verify the code and get access token"""
    token, voter_id = voter_auth_service.verify_code(request.email, request.code)
    return VerifyCodeResponse(token=token, voter_id=voter_id)


@router.get("/ballot", response_model=BallotResponse)
async def get_ballot(session: Session = Depends(get_current_voter_session)):
    """Get the current ballot with all candidates"""
    # Log ballot view for audit
    from .models import AuditLog, AuditAction
    from .data_store import voting_data_store

    audit_log = AuditLog(session.voter_id, AuditAction.BALLOT_VIEW)
    voting_data_store.add_audit_log(audit_log)

    return voting_service.get_ballot()


@router.get("/status", response_model=VoterStatusResponse)
async def get_voter_status(session: Session = Depends(get_current_voter_session)):
    """Get the current voter's status (what they've voted for)"""
    voter_id = get_voter_id_from_session(session)
    return voter_auth_service.get_voter_status(voter_id)


@router.post("/vote", response_model=VoteResponse)
async def cast_votes(
    request: VoteRequest,
    session: Session = Depends(get_current_voter_session)
):
    """Cast votes for selected candidates"""
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
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "pta-voting-system"}