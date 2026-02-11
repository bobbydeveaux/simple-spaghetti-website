"""
PTA Voting System - Business Logic Services
"""
import random
import string
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from fastapi import HTTPException
import jwt

from ..utils.jwt_manager import JWTManager
from .data_store import voting_data_store
from .models import (
    Voter, Vote, Session, AuditLog, Position, ElectionStatus,
    AuditAction, CandidateResponse, BallotResponse, VoterStatusResponse
)


class VoterAuthService:
    """Service for voter authentication and verification"""

    def __init__(self):
        self.data_store = voting_data_store
        self.jwt_manager = JWTManager()

    def request_verification_code(self, email: str) -> str:
        """
        Generate and store a verification code for the email.
        Creates voter record if doesn't exist.
        """
        # Generate 6-digit verification code
        code = ''.join(random.choices(string.digits, k=6))

        # Get or create voter
        voter = self.data_store.get_voter_by_email(email)
        if not voter:
            voter = Voter(email)
            self.data_store.add_voter(voter)

        # Store verification code
        voter.verification_code = code
        self.data_store.update_voter(voter)
        self.data_store.set_verification_code(email, code)

        # In a real implementation, you would send the code via email
        # For development, we'll just store it
        print(f"DEBUG: Verification code for {email}: {code}")

        return "Verification code sent to your email"

    def verify_code(self, email: str, code: str) -> tuple[str, str]:
        """
        Verify the code and create a session with JWT token.
        Returns (token, voter_id)
        """
        # Get voter
        voter = self.data_store.get_voter_by_email(email)
        if not voter:
            raise HTTPException(status_code=400, detail="Invalid email or code")

        # Get stored verification code
        stored_code = self.data_store.get_verification_code(email)
        if not stored_code or stored_code != code:
            raise HTTPException(status_code=400, detail="Invalid verification code")

        # Verify the code matches
        if voter.verification_code != code:
            raise HTTPException(status_code=400, detail="Invalid verification code")

        # Clear verification code
        voter.verification_code = None
        self.data_store.update_voter(voter)
        self.data_store.remove_verification_code(email)

        # Create JWT token for voter session
        token_data = {
            "voter_id": voter.voter_id,
            "email": voter.email,
            "type": "voter_access"
        }

        expires_at = datetime.now() + timedelta(hours=2)  # 2-hour voting session
        token = self.jwt_manager.generate_access_token(token_data)

        # Create session
        session = Session(
            voter_id=voter.voter_id,
            token=token,
            expires_at=expires_at
        )
        self.data_store.add_session(session)

        # Log the login
        audit_log = AuditLog(voter.voter_id, AuditAction.LOGIN)
        self.data_store.add_audit_log(audit_log)

        return token, voter.voter_id

    def validate_session(self, token: str) -> Optional[Session]:
        """Validate JWT token and return session if valid"""
        try:
            payload = self.jwt_manager.verify_token(token)

            # Check token type
            if payload.get("type") != "voter_access":
                return None

            voter_id = payload.get("voter_id")
            if not voter_id:
                return None

            # Find active session
            for session in self.data_store.sessions.values():
                if (session.voter_id == voter_id and
                    session.token == token and
                    session.expires_at > datetime.now()):
                    return session

            return None
        except jwt.InvalidTokenError:
            return None

    def get_voter_status(self, voter_id: str) -> VoterStatusResponse:
        """Get voting status for a voter"""
        voter = self.data_store.get_voter_by_id(voter_id)
        if not voter:
            raise HTTPException(status_code=404, detail="Voter not found")

        election = self.data_store.get_election()
        if not election:
            raise HTTPException(status_code=500, detail="No active election")

        # Determine which positions the voter can still vote for
        can_vote = [pos for pos in election.positions if pos not in voter.voted_positions]

        return VoterStatusResponse(
            voter_id=voter.voter_id,
            voted_positions=list(voter.voted_positions),
            can_vote=can_vote
        )


class VotingService:
    """Service for handling voting operations"""

    def __init__(self):
        self.data_store = voting_data_store

    def get_ballot(self) -> BallotResponse:
        """Get the complete ballot with all candidates by position"""
        election = self.data_store.get_election()
        if not election:
            raise HTTPException(status_code=500, detail="No active election")

        if election.status != ElectionStatus.OPEN:
            raise HTTPException(status_code=400, detail="Election is not open for voting")

        # Group candidates by position
        positions_candidates = {}
        for position in election.positions:
            candidates = self.data_store.get_candidates_by_position(position)
            positions_candidates[position] = [
                CandidateResponse(
                    candidate_id=c.candidate_id,
                    name=c.name,
                    bio=c.bio,
                    photo_url=c.photo_url,
                    position=c.position
                )
                for c in candidates
            ]

        return BallotResponse(
            positions=positions_candidates,
            election_status=election.status
        )

    def cast_votes(self, voter_id: str, votes: Dict[Position, str]) -> tuple[str, int]:
        """
        Cast votes for the voter. Returns (message, votes_cast_count)
        Votes are anonymous - no voter_id stored with votes
        """
        voter = self.data_store.get_voter_by_id(voter_id)
        if not voter:
            raise HTTPException(status_code=404, detail="Voter not found")

        election = self.data_store.get_election()
        if not election or election.status != ElectionStatus.OPEN:
            raise HTTPException(status_code=400, detail="Election is not open for voting")

        # Validate votes
        votes_cast = 0
        new_votes = []

        for position, candidate_id in votes.items():
            # Check if voter already voted for this position
            if position in voter.voted_positions:
                raise HTTPException(
                    status_code=400,
                    detail=f"You have already voted for {position.value}"
                )

            # Validate candidate exists and is for this position
            candidate = self.data_store.get_candidate(candidate_id)
            if not candidate:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid candidate ID: {candidate_id}"
                )

            if candidate.position != position:
                raise HTTPException(
                    status_code=400,
                    detail=f"Candidate {candidate.name} is not running for {position.value}"
                )

            # Create anonymous vote (no voter_id stored)
            vote = Vote(position, candidate_id)
            new_votes.append(vote)
            votes_cast += 1

        # Store all votes atomically
        for vote in new_votes:
            self.data_store.add_vote(vote)

        # Update voter's voted positions
        for position in votes.keys():
            voter.voted_positions.add(position)
        self.data_store.update_voter(voter)

        # Log voting action (log voter_id + action, but NOT vote choices)
        for position in votes.keys():
            audit_log = AuditLog(voter_id, AuditAction.VOTE_CAST, position)
            self.data_store.add_audit_log(audit_log)

        return f"Successfully cast {votes_cast} votes", votes_cast

    def calculate_results(self) -> Dict[Position, Dict[str, int]]:
        """Calculate voting results by position (admin function)"""
        results = {}
        election = self.data_store.get_election()

        if not election:
            return results

        for position in election.positions:
            position_votes = self.data_store.get_votes_for_position(position)
            candidate_counts = {}

            # Count votes for each candidate
            for vote in position_votes:
                candidate = self.data_store.get_candidate(vote.candidate_id)
                if candidate:
                    candidate_name = candidate.name
                    candidate_counts[candidate_name] = candidate_counts.get(candidate_name, 0) + 1

            results[position] = candidate_counts

        return results


# Global service instances
voter_auth_service = VoterAuthService()
voting_service = VotingService()