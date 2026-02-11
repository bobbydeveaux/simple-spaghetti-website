"""
PTA Voting System Data Store
Thread-safe in-memory storage for all voting system data.

This follows the same pattern as the existing library API data store
but is specifically designed for the voting system with anonymity guarantees.
"""

import threading
from typing import Dict, List, Optional, Set
from datetime import datetime

from .models import (
    Voter, Session, VerificationCode, Candidate, Vote, AuditLog, Election,
    generate_voter_id, generate_session_id, generate_verification_code,
    generate_candidate_id, generate_vote_id, generate_audit_log_id,
    generate_election_id
)


class VotingDataStore:
    """
    Thread-safe in-memory data store for the PTA voting system.

    Maintains separate collections for:
    - Voters (identity tracking, NOT linked to votes)
    - Sessions (authentication state)
    - Verification codes (temporary auth codes)
    - Candidates (election candidates)
    - Votes (anonymous, no voter_id)
    - Audit logs (actions with voter_id but no vote choices)
    - Elections (metadata and configuration)

    Critical design: Voter identity is separate from vote records to ensure anonymity.
    """

    def __init__(self):
        """Initialize empty data store with thread lock."""
        self._lock = threading.Lock()

        # Core data collections
        self._voters: Dict[str, Voter] = {}
        self._sessions: Dict[str, Session] = {}
        self._verification_codes: Dict[str, VerificationCode] = {}
        self._candidates: Dict[str, Candidate] = {}
        self._votes: Dict[str, Vote] = {}
        self._audit_logs: Dict[str, AuditLog] = {}
        self._elections: Dict[str, Election] = {}

        # Email-to-voter-id mapping for quick lookup
        self._email_to_voter_id: Dict[str, str] = {}

        # Initialize default election for Sprint 1
        self._initialize_default_election()

    def _initialize_default_election(self):
        """Initialize a default PTA election with common positions."""
        with self._lock:
            election_id = generate_election_id()
            election = Election(
                election_id=election_id,
                name="PTA Board Election 2026",
                description="Annual election for PTA board positions",
                positions={"president", "vice_president", "treasurer", "secretary"},
                is_active=True
            )
            self._elections[election_id] = election

            # Add sample candidates for testing
            positions_candidates = {
                "president": [("Alice Johnson", "Experienced parent volunteer with 5 years of PTA involvement."),
                             ("Bob Smith", "Local business owner committed to improving our school.")],
                "vice_president": [("Carol Davis", "Former teacher with deep understanding of educational needs."),
                                  ("David Wilson", "Parent of three students, active in school committees.")],
                "treasurer": [("Eva Brown", "Professional accountant with non-profit experience."),
                             ("Frank Miller", "Financial advisor passionate about school funding.")],
                "secretary": [("Grace Lee", "Administrative professional with excellent organizational skills."),
                             ("Henry Taylor", "Parent volunteer experienced in record-keeping.")]
            }

            for position, candidates in positions_candidates.items():
                for name, bio in candidates:
                    candidate_id = generate_candidate_id()
                    candidate = Candidate(
                        candidate_id=candidate_id,
                        position=position,
                        name=name,
                        bio=bio
                    )
                    self._candidates[candidate_id] = candidate

    # Voter operations

    def get_voter_by_email(self, email: str) -> Optional[Voter]:
        """Get voter by email address."""
        email = email.lower().strip()
        with self._lock:
            voter_id = self._email_to_voter_id.get(email)
            return self._voters.get(voter_id) if voter_id else None

    def get_voter_by_id(self, voter_id: str) -> Optional[Voter]:
        """Get voter by voter_id."""
        with self._lock:
            return self._voters.get(voter_id)

    def create_or_get_voter(self, email: str) -> Voter:
        """
        Create a new voter or get existing one by email.
        This is used when a voter requests a verification code.
        """
        email = email.lower().strip()
        with self._lock:
            # Check if voter already exists
            existing_voter = self.get_voter_by_email(email)
            if existing_voter:
                existing_voter.last_login = datetime.now()
                return existing_voter

            # Create new voter
            voter_id = generate_voter_id()
            voter = Voter(voter_id=voter_id, email=email)
            self._voters[voter_id] = voter
            self._email_to_voter_id[email] = voter_id

            # Log voter creation
            self._create_audit_log(voter_id, "voter_created")

            return voter

    def mark_voter_voted(self, voter_id: str, position: str) -> bool:
        """
        Mark that a voter has voted for a specific position.
        Returns True if successful, False if voter doesn't exist.
        """
        with self._lock:
            voter = self._voters.get(voter_id)
            if not voter:
                return False

            voter.mark_voted_for_position(position)
            self._create_audit_log(voter_id, "vote_cast", position=position)
            return True

    # Session operations

    def create_session(self, voter_id: str, token: str, is_admin: bool = False) -> Session:
        """Create a new session for a voter."""
        with self._lock:
            session_id = generate_session_id()
            session = Session(
                session_id=session_id,
                voter_id=voter_id,
                token=token,
                is_admin=is_admin
            )
            self._sessions[session_id] = session

            # Log session creation
            action = "admin_session_created" if is_admin else "session_created"
            self._create_audit_log(voter_id, action)

            return session

    def get_session_by_token(self, token: str) -> Optional[Session]:
        """Get session by token."""
        with self._lock:
            for session in self._sessions.values():
                if session.token == token and session.is_valid():
                    return session
            return None

    def get_session_by_id(self, session_id: str) -> Optional[Session]:
        """Get session by session_id."""
        with self._lock:
            session = self._sessions.get(session_id)
            return session if session and session.is_valid() else None

    def invalidate_session(self, session_id: str) -> bool:
        """Invalidate (delete) a session."""
        with self._lock:
            if session_id in self._sessions:
                session = self._sessions[session_id]
                del self._sessions[session_id]
                self._create_audit_log(session.voter_id, "session_invalidated")
                return True
            return False

    def cleanup_expired_sessions(self):
        """Remove all expired sessions."""
        with self._lock:
            expired_sessions = [
                session_id for session_id, session in self._sessions.items()
                if session.is_expired()
            ]
            for session_id in expired_sessions:
                del self._sessions[session_id]

    # Verification code operations

    def create_verification_code(self, email: str, voter_id: str) -> VerificationCode:
        """Create a new verification code for voter authentication."""
        with self._lock:
            # Remove any existing codes for this email (one active code per email)
            self._cleanup_codes_for_email(email)

            code = generate_verification_code()
            verification_code = VerificationCode(
                code=code,
                email=email,
                voter_id=voter_id
            )
            self._verification_codes[code] = verification_code

            # Log code creation
            self._create_audit_log(voter_id, "verification_code_requested")

            return verification_code

    def get_verification_code(self, code: str) -> Optional[VerificationCode]:
        """Get verification code if it exists and is valid."""
        with self._lock:
            verification_code = self._verification_codes.get(code)
            return verification_code if verification_code and verification_code.is_valid() else None

    def use_verification_code(self, code: str) -> Optional[str]:
        """
        Use a verification code and return the voter_id if successful.
        Returns None if code is invalid, expired, or already used.
        """
        with self._lock:
            verification_code = self._verification_codes.get(code)
            if verification_code and verification_code.use_code():
                # Log successful code usage
                self._create_audit_log(verification_code.voter_id, "verification_code_used")
                return verification_code.voter_id
            return None

    def _cleanup_codes_for_email(self, email: str):
        """Remove existing verification codes for an email."""
        codes_to_remove = [
            code for code, vc in self._verification_codes.items()
            if vc.email == email
        ]
        for code in codes_to_remove:
            del self._verification_codes[code]

    def cleanup_expired_codes(self):
        """Remove all expired verification codes."""
        with self._lock:
            expired_codes = [
                code for code, vc in self._verification_codes.items()
                if vc.is_expired()
            ]
            for code in expired_codes:
                del self._verification_codes[code]

    # Election and candidate operations

    def get_active_election(self) -> Optional[Election]:
        """Get the currently active election."""
        with self._lock:
            for election in self._elections.values():
                if election.is_active and election.is_voting_period_active():
                    return election
            return None

    def get_candidates_for_position(self, position: str) -> List[Candidate]:
        """Get all candidates for a specific position."""
        with self._lock:
            candidates = [
                candidate for candidate in self._candidates.values()
                if candidate.position == position
            ]
            return sorted(candidates, key=lambda c: c.name)

    def get_all_positions(self) -> List[str]:
        """Get all available positions in the active election."""
        election = self.get_active_election()
        return election.get_positions_list() if election else []

    def get_candidate_by_id(self, candidate_id: str) -> Optional[Candidate]:
        """Get candidate by ID."""
        with self._lock:
            return self._candidates.get(candidate_id)

    # Vote operations (anonymous)

    def cast_vote(self, position: str, candidate_id: str) -> bool:
        """
        Cast an anonymous vote.

        CRITICAL: No voter_id is stored to maintain anonymity.
        The caller must separately track that the voter has voted using mark_voter_voted().
        """
        with self._lock:
            # Verify candidate exists and is for the correct position
            candidate = self._candidates.get(candidate_id)
            if not candidate or candidate.position != position:
                return False

            # Create anonymous vote
            vote_id = generate_vote_id()
            vote = Vote(
                vote_id=vote_id,
                position=position,
                candidate_id=candidate_id
            )
            self._votes[vote_id] = vote
            return True

    def get_vote_counts_for_position(self, position: str) -> Dict[str, int]:
        """Get vote counts for all candidates in a position."""
        with self._lock:
            counts = {}
            for vote in self._votes.values():
                if vote.position == position:
                    counts[vote.candidate_id] = counts.get(vote.candidate_id, 0) + 1
            return counts

    def get_total_votes_count(self) -> int:
        """Get total number of votes cast."""
        with self._lock:
            return len(self._votes)

    # Audit log operations

    def _create_audit_log(self, voter_id: str, action: str, position: Optional[str] = None, **metadata):
        """Create an audit log entry (internal method)."""
        log_id = generate_audit_log_id()
        audit_log = AuditLog(
            log_id=log_id,
            voter_id=voter_id,
            action=action,
            position=position,
            metadata=metadata
        )
        self._audit_logs[log_id] = audit_log

    def get_audit_logs_for_voter(self, voter_id: str) -> List[AuditLog]:
        """Get all audit logs for a specific voter."""
        with self._lock:
            logs = [
                log for log in self._audit_logs.values()
                if log.voter_id == voter_id
            ]
            return sorted(logs, key=lambda l: l.timestamp)

    def get_recent_audit_logs(self, limit: int = 100) -> List[AuditLog]:
        """Get recent audit logs (admin function)."""
        with self._lock:
            logs = list(self._audit_logs.values())
            logs.sort(key=lambda l: l.timestamp, reverse=True)
            return logs[:limit]

    # Admin and testing utilities

    def get_all_voters(self) -> List[Voter]:
        """Get all voters (admin/testing function)."""
        with self._lock:
            return list(self._voters.values())

    def get_all_sessions(self) -> List[Session]:
        """Get all sessions (admin/testing function)."""
        with self._lock:
            return list(self._sessions.values())

    def clear_all_data(self):
        """Clear all data (testing function)."""
        with self._lock:
            self._voters.clear()
            self._sessions.clear()
            self._verification_codes.clear()
            self._candidates.clear()
            self._votes.clear()
            self._audit_logs.clear()
            self._elections.clear()
            self._email_to_voter_id.clear()
            self._initialize_default_election()

    def get_stats(self) -> Dict[str, int]:
        """Get system statistics."""
        with self._lock:
            return {
                "total_voters": len(self._voters),
                "active_sessions": len([s for s in self._sessions.values() if s.is_valid()]),
                "pending_codes": len([c for c in self._verification_codes.values() if c.is_valid()]),
                "total_votes": len(self._votes),
                "total_candidates": len(self._candidates),
                "audit_log_entries": len(self._audit_logs)
            }


# Global instance
voting_data_store = VotingDataStore()