"""
PTA Voting System - Thread-safe In-Memory Data Store
"""
import threading
from typing import Dict, List, Optional
from .models import Voter, Candidate, Vote, Session, AuditLog, Election, Position, ElectionStatus


class VotingDataStore:
    """Thread-safe singleton data store for voting system"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(VotingDataStore, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if not getattr(self, '_initialized', False):
            # Data storage
            self.voters: Dict[str, Voter] = {}  # voter_id -> Voter
            self.voters_by_email: Dict[str, Voter] = {}  # email -> Voter
            self.candidates: Dict[str, Candidate] = {}  # candidate_id -> Candidate
            self.votes: List[Vote] = []  # Anonymous votes
            self.sessions: Dict[str, Session] = {}  # session_id -> Session
            self.audit_logs: List[AuditLog] = []  # Audit trail
            self.verification_codes: Dict[str, str] = {}  # email -> code
            self.election: Optional[Election] = None

            # Thread locks for each data structure
            self.voters_lock = threading.Lock()
            self.candidates_lock = threading.Lock()
            self.votes_lock = threading.Lock()
            self.sessions_lock = threading.Lock()
            self.audit_logs_lock = threading.Lock()
            self.verification_codes_lock = threading.Lock()
            self.election_lock = threading.Lock()

            self._initialized = True
            self._setup_default_data()

    def _setup_default_data(self):
        """Initialize with default election and candidates for development"""
        # Create default election
        self.election = Election([
            Position.PRESIDENT,
            Position.VICE_PRESIDENT,
            Position.SECRETARY,
            Position.TREASURER
        ])
        self.election.status = ElectionStatus.OPEN

        # Add sample candidates
        candidates_data = [
            ("Sarah Johnson", "Experienced parent leader with 5 years of volunteer work.", Position.PRESIDENT),
            ("Mike Chen", "Financial professional passionate about education funding.", Position.PRESIDENT),
            ("Lisa Rodriguez", "Former teacher with strong organizational skills.", Position.VICE_PRESIDENT),
            ("David Kim", "Active community member and parent advocate.", Position.VICE_PRESIDENT),
            ("Emma Thompson", "Detail-oriented parent with excellent communication skills.", Position.SECRETARY),
            ("James Wilson", "Certified accountant committed to transparency.", Position.TREASURER),
            ("Maria Garcia", "Budget planning expert with nonprofit experience.", Position.TREASURER)
        ]

        for name, bio, position in candidates_data:
            candidate = Candidate(name, bio, position)
            self.candidates[candidate.candidate_id] = candidate

    # Voter operations
    def add_voter(self, voter: Voter) -> None:
        """Add a new voter"""
        with self.voters_lock:
            self.voters[voter.voter_id] = voter
            self.voters_by_email[voter.email.lower()] = voter

    def get_voter_by_id(self, voter_id: str) -> Optional[Voter]:
        """Get voter by ID"""
        with self.voters_lock:
            return self.voters.get(voter_id)

    def get_voter_by_email(self, email: str) -> Optional[Voter]:
        """Get voter by email"""
        with self.voters_lock:
            return self.voters_by_email.get(email.lower())

    def update_voter(self, voter: Voter) -> None:
        """Update existing voter"""
        with self.voters_lock:
            self.voters[voter.voter_id] = voter
            self.voters_by_email[voter.email.lower()] = voter

    # Verification code operations
    def set_verification_code(self, email: str, code: str) -> None:
        """Store verification code for email"""
        with self.verification_codes_lock:
            self.verification_codes[email.lower()] = code

    def get_verification_code(self, email: str) -> Optional[str]:
        """Get verification code for email"""
        with self.verification_codes_lock:
            return self.verification_codes.get(email.lower())

    def remove_verification_code(self, email: str) -> None:
        """Remove verification code after use"""
        with self.verification_codes_lock:
            self.verification_codes.pop(email.lower(), None)

    # Session operations
    def add_session(self, session: Session) -> None:
        """Add a new session"""
        with self.sessions_lock:
            self.sessions[session.session_id] = session

    def get_session(self, session_id: str) -> Optional[Session]:
        """Get session by ID"""
        with self.sessions_lock:
            return self.sessions.get(session_id)

    def remove_session(self, session_id: str) -> None:
        """Remove session"""
        with self.sessions_lock:
            self.sessions.pop(session_id, None)

    # Vote operations
    def add_vote(self, vote: Vote) -> None:
        """Add an anonymous vote"""
        with self.votes_lock:
            self.votes.append(vote)

    def get_votes_for_position(self, position: Position) -> List[Vote]:
        """Get all votes for a specific position"""
        with self.votes_lock:
            return [vote for vote in self.votes if vote.position == position]

    def get_total_votes(self) -> int:
        """Get total number of votes cast"""
        with self.votes_lock:
            return len(self.votes)

    # Candidate operations
    def add_candidate(self, candidate: Candidate) -> None:
        """Add a new candidate"""
        with self.candidates_lock:
            self.candidates[candidate.candidate_id] = candidate

    def get_candidate(self, candidate_id: str) -> Optional[Candidate]:
        """Get candidate by ID"""
        with self.candidates_lock:
            return self.candidates.get(candidate_id)

    def get_candidates_by_position(self, position: Position) -> List[Candidate]:
        """Get all candidates for a specific position"""
        with self.candidates_lock:
            return [candidate for candidate in self.candidates.values()
                   if candidate.position == position]

    def get_all_candidates(self) -> List[Candidate]:
        """Get all candidates"""
        with self.candidates_lock:
            return list(self.candidates.values())

    # Audit log operations
    def add_audit_log(self, audit_log: AuditLog) -> None:
        """Add an audit log entry"""
        with self.audit_logs_lock:
            self.audit_logs.append(audit_log)

    def get_audit_logs_for_voter(self, voter_id: str) -> List[AuditLog]:
        """Get audit logs for a specific voter"""
        with self.audit_logs_lock:
            return [log for log in self.audit_logs if log.voter_id == voter_id]

    def get_all_audit_logs(self) -> List[AuditLog]:
        """Get all audit logs"""
        with self.audit_logs_lock:
            return list(self.audit_logs)

    # Election operations
    def get_election(self) -> Optional[Election]:
        """Get current election"""
        with self.election_lock:
            return self.election

    def update_election_status(self, status: ElectionStatus) -> None:
        """Update election status"""
        with self.election_lock:
            if self.election:
                self.election.status = status

    # Utility methods
    def clear_all_data(self) -> None:
        """Clear all data (for testing)"""
        with (self.voters_lock, self.candidates_lock, self.votes_lock,
              self.sessions_lock, self.audit_logs_lock, self.verification_codes_lock):
            self.voters.clear()
            self.voters_by_email.clear()
            self.candidates.clear()
            self.votes.clear()
            self.sessions.clear()
            self.audit_logs.clear()
            self.verification_codes.clear()
            self._setup_default_data()


# Global instance
voting_data_store = VotingDataStore()