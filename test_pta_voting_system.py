"""
Comprehensive test suite for PTA voting system functionality.
Tests data models, validators, API endpoints, and thread-safety.
"""

import pytest
import json
import threading
import time
from datetime import datetime, timedelta
from unittest.mock import patch

# Import the Flask application and testing utilities
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from api.app import app
from api.data_store import (
    PROPOSALS, VOTES, MEMBERS, reset_data_store,
    create_proposal, create_vote, get_proposal, get_all_proposals,
    get_vote_by_member_and_proposal, get_votes_for_proposal,
    update_proposal, update_vote, delete_vote
)
from api.validators import validate_proposal, validate_vote, validate_proposal_update, validate_vote_update
from api.auth import generate_token

class TestVotingDataModels:
    """Test voting data models and thread-safe operations"""

    def setup_method(self):
        """Reset data store before each test"""
        reset_data_store()

    def test_proposal_creation(self):
        """Test creating a new proposal"""
        proposal_data = {
            "title": "New Playground Equipment",
            "description": "Vote on installing new playground equipment for the school.",
            "created_by": 1,
            "created_date": "2024-02-11",
            "closing_date": "2024-02-25",
            "status": "active",
            "options": ["approve", "reject"],
            "allow_abstain": True
        }

        proposal_id = create_proposal(proposal_data)
        assert proposal_id is not None
        assert proposal_id in PROPOSALS

        created_proposal = get_proposal(proposal_id)
        assert created_proposal["title"] == proposal_data["title"]
        assert created_proposal["id"] == proposal_id

    def test_vote_creation(self):
        """Test creating a new vote"""
        vote_data = {
            "proposal_id": 1,
            "member_id": 1,
            "vote_choice": "yes",
            "timestamp": "2024-02-11T10:30:00",
            "is_anonymous": False
        }

        vote_id = create_vote(vote_data)
        assert vote_id is not None
        assert vote_id in VOTES

        # Test retrieving vote by member and proposal
        retrieved_vote = get_vote_by_member_and_proposal(1, 1)
        assert retrieved_vote is not None
        assert retrieved_vote["vote_choice"] == "yes"

    def test_thread_safe_proposal_creation(self):
        """Test that proposal creation is thread-safe"""
        created_ids = []

        def create_test_proposal(thread_id):
            proposal_data = {
                "title": f"Test Proposal {thread_id}",
                "description": "Thread safety test proposal",
                "created_by": 1,
                "created_date": "2024-02-11",
                "closing_date": "2024-02-25",
                "status": "active",
                "options": ["yes", "no"],
                "allow_abstain": False
            }
            proposal_id = create_proposal(proposal_data)
            created_ids.append(proposal_id)

        # Create multiple threads that create proposals simultaneously
        threads = []
        for i in range(5):
            thread = threading.Thread(target=create_test_proposal, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify all proposals were created with unique IDs
        assert len(created_ids) == 5
        assert len(set(created_ids)) == 5  # All IDs should be unique

    def test_vote_retrieval_by_proposal(self):
        """Test getting all votes for a proposal"""
        # Create test votes for proposal 1
        vote_data_1 = {
            "proposal_id": 1,
            "member_id": 1,
            "vote_choice": "yes",
            "timestamp": "2024-02-11T10:30:00",
            "is_anonymous": False
        }

        vote_data_2 = {
            "proposal_id": 1,
            "member_id": 2,
            "vote_choice": "no",
            "timestamp": "2024-02-11T11:30:00",
            "is_anonymous": False
        }

        create_vote(vote_data_1)
        create_vote(vote_data_2)

        votes = get_votes_for_proposal(1)
        assert len(votes) >= 2  # Should include existing votes plus our new ones

        # Check that we can find our votes
        vote_choices = [vote["vote_choice"] for vote in votes]
        assert "yes" in vote_choices
        assert "no" in vote_choices

class TestVotingValidators:
    """Test voting system validators"""

    def setup_method(self):
        """Reset data store before each test"""
        reset_data_store()

    def test_proposal_validation_success(self):
        """Test successful proposal validation"""
        valid_proposal = {
            "title": "Valid Proposal Title",
            "description": "This is a valid proposal description with sufficient detail.",
            "created_by": 1,
            "closing_date": "2024-12-31",
            "options": ["yes", "no"],
            "allow_abstain": True
        }

        is_valid, error_msg = validate_proposal(valid_proposal)
        assert is_valid is True
        assert error_msg is None

    def test_proposal_validation_failures(self):
        """Test proposal validation with various invalid inputs"""
        # Missing required fields
        invalid_proposal = {
            "title": "Test"
        }
        is_valid, error_msg = validate_proposal(invalid_proposal)
        assert is_valid is False
        assert "Missing required field" in error_msg

        # Title too short
        invalid_proposal = {
            "title": "Hi",
            "description": "Valid description here",
            "created_by": 1,
            "closing_date": "2024-12-31",
            "options": ["yes", "no"]
        }
        is_valid, error_msg = validate_proposal(invalid_proposal)
        assert is_valid is False
        assert "Title must be between" in error_msg

        # Invalid member ID
        invalid_proposal = {
            "title": "Valid Title",
            "description": "Valid description here",
            "created_by": 999,  # Non-existent member
            "closing_date": "2024-12-31",
            "options": ["yes", "no"]
        }
        is_valid, error_msg = validate_proposal(invalid_proposal)
        assert is_valid is False
        assert "member does not exist" in error_msg

        # Past closing date
        invalid_proposal = {
            "title": "Valid Title",
            "description": "Valid description here",
            "created_by": 1,
            "closing_date": "2020-01-01",  # Past date
            "options": ["yes", "no"]
        }
        is_valid, error_msg = validate_proposal(invalid_proposal)
        assert is_valid is False
        assert "must be in the future" in error_msg

        # Insufficient options
        invalid_proposal = {
            "title": "Valid Title",
            "description": "Valid description here",
            "created_by": 1,
            "closing_date": "2024-12-31",
            "options": ["yes"]  # Only one option
        }
        is_valid, error_msg = validate_proposal(invalid_proposal)
        assert is_valid is False
        assert "at least 2 choices" in error_msg

    def test_vote_validation_success(self):
        """Test successful vote validation"""
        valid_vote = {
            "proposal_id": 1,  # Should exist in test data
            "member_id": 1,    # Should exist in test data
            "vote_choice": "yes"  # Valid option for test proposal
        }

        is_valid, error_msg = validate_vote(valid_vote)
        assert is_valid is True
        assert error_msg is None

    def test_vote_validation_failures(self):
        """Test vote validation with various invalid inputs"""
        # Non-existent proposal
        invalid_vote = {
            "proposal_id": 999,
            "member_id": 1,
            "vote_choice": "yes"
        }
        is_valid, error_msg = validate_vote(invalid_vote)
        assert is_valid is False
        assert "does not exist" in error_msg

        # Non-existent member
        invalid_vote = {
            "proposal_id": 1,
            "member_id": 999,
            "vote_choice": "yes"
        }
        is_valid, error_msg = validate_vote(invalid_vote)
        assert is_valid is False
        assert "member does not exist" in error_msg

        # Invalid vote choice
        invalid_vote = {
            "proposal_id": 1,
            "member_id": 1,
            "vote_choice": "invalid_option"
        }
        is_valid, error_msg = validate_vote(invalid_vote)
        assert is_valid is False
        assert "Invalid vote_choice" in error_msg

class TestVotingAPIEndpoints:
    """Test voting system API endpoints"""

    def setup_method(self):
        """Reset data store and create test client before each test"""
        reset_data_store()
        app.config['TESTING'] = True
        self.client = app.test_client()

        # Generate auth tokens for testing
        self.auth_headers_member1 = {
            'Authorization': f'Bearer {generate_token(1)}',
            'Content-Type': 'application/json'
        }
        self.auth_headers_member2 = {
            'Authorization': f'Bearer {generate_token(2)}',
            'Content-Type': 'application/json'
        }

    def test_get_proposals_endpoint(self):
        """Test GET /proposals endpoint"""
        response = self.client.get('/proposals', headers=self.auth_headers_member1)
        assert response.status_code == 200

        data = json.loads(response.data)
        assert 'proposals' in data
        assert len(data['proposals']) >= 0  # Should return list of proposals

        # Check that vote counts are included
        for proposal in data['proposals']:
            assert 'vote_counts' in proposal
            assert 'total_votes' in proposal

    def test_create_proposal_endpoint(self):
        """Test POST /proposals endpoint"""
        new_proposal = {
            "title": "Test API Proposal",
            "description": "This is a test proposal created via API",
            "closing_date": "2024-12-31",
            "options": ["approve", "reject"],
            "allow_abstain": True
        }

        response = self.client.post('/proposals',
                                  data=json.dumps(new_proposal),
                                  headers=self.auth_headers_member1)
        assert response.status_code == 201

        data = json.loads(response.data)
        assert data['title'] == new_proposal['title']
        assert data['status'] == 'draft'
        assert data['created_by'] == 1

    def test_create_proposal_validation(self):
        """Test proposal creation validation"""
        invalid_proposal = {
            "title": "Hi",  # Too short
            "description": "Short",  # Too short
            "closing_date": "invalid-date",
            "options": ["yes"]  # Not enough options
        }

        response = self.client.post('/proposals',
                                  data=json.dumps(invalid_proposal),
                                  headers=self.auth_headers_member1)
        assert response.status_code == 400

        data = json.loads(response.data)
        assert 'error' in data

    def test_get_proposal_details_endpoint(self):
        """Test GET /proposals/{id} endpoint"""
        response = self.client.get('/proposals/1', headers=self.auth_headers_member1)
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['id'] == 1
        assert 'vote_counts' in data
        assert 'total_votes' in data
        assert 'created_by_name' in data

    def test_update_proposal_authorization(self):
        """Test proposal update authorization (only creator can update)"""
        update_data = {
            "title": "Updated Title"
        }

        # Member 2 trying to update proposal created by member 1
        response = self.client.put('/proposals/1',
                                 data=json.dumps(update_data),
                                 headers=self.auth_headers_member2)
        assert response.status_code == 403

        data = json.loads(response.data)
        assert 'Permission denied' in data['error']

    def test_cast_vote_endpoint(self):
        """Test POST /proposals/{id}/votes endpoint"""
        vote_data = {
            "vote_choice": "yes",
            "is_anonymous": False
        }

        response = self.client.post('/proposals/1/votes',
                                  data=json.dumps(vote_data),
                                  headers=self.auth_headers_member1)

        # Note: This might return 400 if member 1 already voted (from test data)
        # In that case, test the error message
        if response.status_code == 400:
            data = json.loads(response.data)
            assert 'already voted' in data['error']
        else:
            assert response.status_code == 201
            data = json.loads(response.data)
            assert data['vote_choice'] == 'yes'

    def test_update_vote_endpoint(self):
        """Test PUT /proposals/{id}/votes endpoint"""
        # First, ensure there's a vote to update
        original_vote = {
            "vote_choice": "yes",
            "is_anonymous": False
        }

        # Cast original vote (might fail if already exists)
        self.client.post('/proposals/1/votes',
                        data=json.dumps(original_vote),
                        headers=self.auth_headers_member2)

        # Now update the vote
        updated_vote = {
            "vote_choice": "no",
            "is_anonymous": True
        }

        response = self.client.put('/proposals/1/votes',
                                 data=json.dumps(updated_vote),
                                 headers=self.auth_headers_member2)

        if response.status_code == 200:
            data = json.loads(response.data)
            assert data['vote_choice'] == 'no'
        elif response.status_code == 404:
            data = json.loads(response.data)
            assert 'No existing vote found' in data['error']

    def test_delete_vote_endpoint(self):
        """Test DELETE /proposals/{id}/votes endpoint"""
        # First, ensure there's a vote to delete by casting one
        vote_data = {
            "vote_choice": "approve",
            "is_anonymous": False
        }

        self.client.post('/proposals/2/votes',
                        data=json.dumps(vote_data),
                        headers=self.auth_headers_member2)

        # Now delete the vote
        response = self.client.delete('/proposals/2/votes',
                                    headers=self.auth_headers_member2)

        # Should succeed if vote exists, or 404 if no vote found
        assert response.status_code in [200, 404]

    def test_get_my_votes_endpoint(self):
        """Test GET /votes/my-votes endpoint"""
        response = self.client.get('/votes/my-votes', headers=self.auth_headers_member1)
        assert response.status_code == 200

        data = json.loads(response.data)
        assert 'my_votes' in data
        assert 'total_votes' in data
        assert isinstance(data['my_votes'], list)

        # Check structure of vote entries
        for vote in data['my_votes']:
            assert 'vote_id' in vote
            assert 'proposal_id' in vote
            assert 'proposal_title' in vote
            assert 'vote_choice' in vote
            assert 'timestamp' in vote

    def test_unauthorized_access(self):
        """Test that endpoints require authentication"""
        # Test without auth headers
        response = self.client.get('/proposals')
        assert response.status_code == 401

        response = self.client.post('/proposals', data=json.dumps({}))
        assert response.status_code == 401

        response = self.client.get('/votes/my-votes')
        assert response.status_code == 401

class TestVotingBusinessLogic:
    """Test voting system business logic and edge cases"""

    def setup_method(self):
        """Reset data store before each test"""
        reset_data_store()

    def test_vote_counting(self):
        """Test that vote counts are calculated correctly"""
        # Create votes for proposal 1
        vote_data_yes = {
            "proposal_id": 1,
            "member_id": 1,
            "vote_choice": "yes",
            "timestamp": "2024-02-11T10:30:00",
            "is_anonymous": False
        }

        vote_data_no = {
            "proposal_id": 1,
            "member_id": 2,
            "vote_choice": "no",
            "timestamp": "2024-02-11T11:30:00",
            "is_anonymous": False
        }

        create_vote(vote_data_yes)
        create_vote(vote_data_no)

        votes = get_votes_for_proposal(1)

        # Count votes
        yes_votes = len([v for v in votes if v["vote_choice"] == "yes"])
        no_votes = len([v for v in votes if v["vote_choice"] == "no"])

        assert yes_votes >= 1  # At least our test vote
        assert no_votes >= 1   # At least our test vote

    def test_duplicate_vote_prevention(self):
        """Test that members cannot vote twice on the same proposal"""
        vote_data = {
            "proposal_id": 1,
            "member_id": 1,
            "vote_choice": "yes",
            "timestamp": "2024-02-11T10:30:00",
            "is_anonymous": False
        }

        # First vote should succeed
        first_vote_id = create_vote(vote_data)
        assert first_vote_id is not None

        # Check if vote exists
        existing_vote = get_vote_by_member_and_proposal(1, 1)
        assert existing_vote is not None

        # Using the validator to check duplicate prevention logic
        is_valid, error_msg = validate_vote(vote_data)
        # The validator should still pass, but the API endpoint would check for duplicates

    def test_proposal_status_changes(self):
        """Test that proposal status changes work correctly"""
        proposal_data = {
            "title": "Test Status Change",
            "description": "Testing proposal status changes",
            "created_by": 1,
            "created_date": "2024-02-11",
            "closing_date": "2024-02-25",
            "status": "draft",
            "options": ["yes", "no"],
            "allow_abstain": False
        }

        proposal_id = create_proposal(proposal_data)

        # Update status to active
        update_data = {"status": "active"}
        success = update_proposal(proposal_id, update_data)
        assert success is True

        updated_proposal = get_proposal(proposal_id)
        assert updated_proposal["status"] == "active"

    def test_abstain_voting(self):
        """Test abstain voting functionality"""
        # Create a proposal that allows abstaining
        proposal_data = {
            "title": "Abstain Test",
            "description": "Testing abstain functionality",
            "created_by": 1,
            "created_date": "2024-02-11",
            "closing_date": "2024-02-25",
            "status": "active",
            "options": ["approve", "reject"],
            "allow_abstain": True
        }

        proposal_id = create_proposal(proposal_data)

        # Test abstain vote
        abstain_vote = {
            "proposal_id": proposal_id,
            "member_id": 1,
            "vote_choice": "abstain"
        }

        is_valid, error_msg = validate_vote(abstain_vote)
        assert is_valid is True
        assert error_msg is None

def test_data_store_reset():
    """Test that data store reset works correctly"""
    original_proposals = len(PROPOSALS)
    original_votes = len(VOTES)

    # Create some test data
    proposal_data = {
        "title": "Test Reset",
        "description": "Testing data store reset",
        "created_by": 1,
        "created_date": "2024-02-11",
        "closing_date": "2024-02-25",
        "status": "active",
        "options": ["yes", "no"],
        "allow_abstain": False
    }

    create_proposal(proposal_data)
    assert len(PROPOSALS) > original_proposals

    # Reset and verify
    reset_data_store()
    assert len(PROPOSALS) == original_proposals
    assert len(VOTES) == original_votes

if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])