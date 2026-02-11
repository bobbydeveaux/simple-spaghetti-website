#!/usr/bin/env python3
"""
Test script to validate voting and election endpoints implementation
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

def test_voting_implementation():
    """Test all voting and election endpoints"""
    print("Testing voting and election implementation...")

    from api.app import app
    from api.data_store import ELECTIONS, VOTES, MEMBERS, reset_data_store
    from api.auth import generate_token
    from datetime import datetime, timedelta

    # Reset data store to known state
    reset_data_store()

    # Test with test client
    with app.test_client() as client:
        # Get auth token for member 1
        login_response = client.post('/auth/login', json={
            "email": "john.doe@email.com",
            "password": "password123"
        })
        assert login_response.status_code == 200, f"Login failed: {login_response.status_code}"

        token = login_response.get_json()["token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Test 1: List elections (no auth required)
        print("Testing list elections...")
        response = client.get('/elections')
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"

        data = response.get_json()
        assert "elections" in data, "Response should contain elections list"
        assert len(data["elections"]) >= 1, "Should have sample elections"

        # Test 2: Get specific election
        print("Testing get election by ID...")
        response = client.get('/elections/1')
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"

        election_data = response.get_json()
        assert "id" in election_data, "Response should contain election ID"
        assert election_data["id"] == 1, "Should return correct election"
        assert "candidates" in election_data, "Should contain candidates list"

        # Test 3: Create new election (auth required)
        print("Testing create election...")
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        next_week = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")

        new_election_data = {
            "title": "Test Election for PTA Treasurer",
            "description": "Annual election for the PTA Treasurer position at our school",
            "candidates": ["Alice Johnson", "Bob Smith", "Carol Davis"],
            "start_date": tomorrow,
            "end_date": next_week
        }

        response = client.post('/elections', json=new_election_data, headers=headers)
        assert response.status_code == 201, f"Expected 201, got {response.status_code}"

        created_election = response.get_json()
        new_election_id = created_election["id"]
        assert "id" in created_election, "Response should contain election ID"
        assert created_election["title"] == new_election_data["title"], "Title should match"
        assert len(created_election["candidates"]) == 3, "Should have 3 candidates"

        # Test 4: Create election with validation errors
        print("Testing election validation...")

        # Missing required fields
        response = client.post('/elections', json={}, headers=headers)
        assert response.status_code == 400, "Should reject empty data"

        # Invalid date range
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        invalid_election = {
            "title": "Invalid Election",
            "description": "This election has invalid dates",
            "candidates": ["Candidate A", "Candidate B"],
            "start_date": tomorrow,
            "end_date": yesterday  # End before start
        }

        response = client.post('/elections', json=invalid_election, headers=headers)
        assert response.status_code == 400, "Should reject invalid date range"

        # Test 5: Cast vote in existing election
        print("Testing cast vote...")

        # Use election ID 1 (from sample data) which should be active
        vote_data = {
            "election_id": 1,
            "member_id": 1,
            "candidate": "Sarah Johnson"  # From sample election data
        }

        response = client.post('/votes/cast', json=vote_data, headers=headers)
        assert response.status_code == 201, f"Expected 201, got {response.status_code}"

        vote_response = response.get_json()
        assert "id" in vote_response, "Response should contain vote ID"
        assert vote_response["election_id"] == 1, "Should reference correct election"
        assert vote_response["candidate"] == "Sarah Johnson", "Should record correct candidate"

        # Test 6: Prevent duplicate voting
        print("Testing duplicate vote prevention...")

        # Try to vote again in same election with same member
        response = client.post('/votes/cast', json=vote_data, headers=headers)
        assert response.status_code == 400, "Should prevent duplicate voting"

        error_data = response.get_json()
        assert "already voted" in error_data["error"].lower(), "Should mention already voted"

        # Test 7: Vote validation errors
        print("Testing vote validation...")

        # Invalid election ID
        invalid_vote = {
            "election_id": 9999,  # Non-existent election
            "member_id": 1,
            "candidate": "Test Candidate"
        }

        response = client.post('/votes/cast', json=invalid_vote, headers=headers)
        assert response.status_code == 400, "Should reject invalid election ID"

        # Invalid candidate
        invalid_candidate_vote = {
            "election_id": 1,
            "member_id": 1,
            "candidate": "Non-Existent Candidate"
        }

        # Get token for member 2 to avoid duplicate vote error
        login_response_2 = client.post('/auth/login', json={
            "email": "jane.smith@email.com",
            "password": "securepass456"
        })
        assert login_response_2.status_code == 200
        token_2 = login_response_2.get_json()["token"]
        headers_2 = {"Authorization": f"Bearer {token_2}"}

        response = client.post('/votes/cast', json=invalid_candidate_vote, headers=headers_2)
        assert response.status_code == 400, "Should reject invalid candidate"

        # Test 8: Get election results
        print("Testing election results...")

        response = client.get('/elections/1/results')
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"

        results_data = response.get_json()
        assert "election_id" in results_data, "Should contain election ID"
        assert "total_votes" in results_data, "Should contain total votes count"
        assert "results" in results_data, "Should contain results array"
        assert results_data["total_votes"] >= 1, "Should have at least one vote"

        # Test results structure
        results = results_data["results"]
        assert len(results) >= 1, "Should have results for candidates"

        for result in results:
            assert "candidate" in result, "Each result should have candidate name"
            assert "votes" in result, "Each result should have vote count"
            assert "percentage" in result, "Each result should have percentage"
            assert isinstance(result["votes"], int), "Vote count should be integer"
            assert isinstance(result["percentage"], (int, float)), "Percentage should be numeric"

        # Test 9: Get results for non-existent election
        print("Testing results for invalid election...")

        response = client.get('/elections/9999/results')
        assert response.status_code == 400, "Should reject invalid election ID"

        # Test 10: Authentication requirement
        print("Testing authentication requirements...")

        # Try to create election without auth
        response = client.post('/elections', json=new_election_data)
        assert response.status_code == 401, "Should require auth for creating elections"

        # Try to cast vote without auth
        response = client.post('/votes/cast', json=vote_data)
        assert response.status_code == 401, "Should require auth for casting votes"

        print("✅ All voting implementation tests passed!")
        return True

def test_data_consistency():
    """Test data consistency across voting operations"""
    print("Testing data consistency...")

    from api.data_store import ELECTIONS, VOTES, reset_data_store

    # Reset to clean state
    reset_data_store()

    # Verify initial data
    assert len(ELECTIONS) == 2, "Should have 2 sample elections"
    assert len(VOTES) == 2, "Should have 2 sample votes"

    # Check election data structure
    for election_id, election in ELECTIONS.items():
        required_fields = ["id", "title", "description", "candidates", "start_date", "end_date", "status"]
        for field in required_fields:
            assert field in election, f"Election should have {field} field"

        assert isinstance(election["candidates"], list), "Candidates should be a list"
        assert len(election["candidates"]) >= 2, "Should have at least 2 candidates"

    # Check vote data structure
    for vote_id, vote in VOTES.items():
        required_fields = ["id", "election_id", "member_id", "candidate", "vote_date", "timestamp"]
        for field in required_fields:
            assert field in vote, f"Vote should have {field} field"

        # Verify referential integrity
        assert vote["election_id"] in ELECTIONS, "Vote should reference valid election"

        election = ELECTIONS[vote["election_id"]]
        assert vote["candidate"] in election["candidates"], "Vote should reference valid candidate"

    print("✅ Data consistency tests passed!")
    return True

def test_validation_functions():
    """Test validation functions directly"""
    print("Testing validation functions...")

    from api.validators import validate_election, validate_vote, validate_election_results
    from datetime import datetime, timedelta

    # Test election validation
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    next_week = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")

    valid_election = {
        "title": "Valid Election",
        "description": "This is a valid election with proper data",
        "candidates": ["Alice", "Bob", "Charlie"],
        "start_date": tomorrow,
        "end_date": next_week
    }

    is_valid, error = validate_election(valid_election)
    assert is_valid, f"Valid election should pass: {error}"

    # Test invalid election - missing fields
    invalid_election = {"title": "Incomplete"}
    is_valid, error = validate_election(invalid_election)
    assert not is_valid, "Incomplete election should fail validation"

    # Test vote validation
    valid_vote = {
        "election_id": 1,  # Should exist in sample data
        "member_id": 1,    # Should exist in sample data
        "candidate": "Sarah Johnson"  # Should be valid candidate
    }

    is_valid, error = validate_vote(valid_vote)
    assert is_valid, f"Valid vote should pass: {error}"

    # Test election results validation
    is_valid, error = validate_election_results(1)
    assert is_valid, f"Valid election ID should pass: {error}"

    is_valid, error = validate_election_results(9999)
    assert not is_valid, "Invalid election ID should fail"

    print("✅ Validation function tests passed!")
    return True

def run_all_tests():
    """Run all voting system tests"""
    print("🗳️  Starting PTA Voting System Tests")
    print("=" * 50)

    try:
        # Run all test suites
        test_data_consistency()
        test_validation_functions()
        test_voting_implementation()

        print("=" * 50)
        print("🎉 All PTA Voting System tests completed successfully!")
        return True

    except AssertionError as e:
        print(f"❌ Test failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error during testing: {e}")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)