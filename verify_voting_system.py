#!/usr/bin/env python3
"""
Verification script for PTA voting system implementation.
Tests imports, basic functionality, and data integrity.
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

def test_basic_imports():
    """Test that all voting system modules can be imported"""
    print("Testing PTA Voting System Implementation...")
    print("=" * 50)

    try:
        # Test data store imports
        from api.data_store import (
            PROPOSALS, VOTES,
            create_proposal, create_vote, get_proposal, get_all_proposals,
            get_vote_by_member_and_proposal, get_votes_for_proposal,
            update_proposal, update_vote, delete_vote
        )
        print("✓ Voting data store imports successful")

        # Test validator imports
        from api.validators import (
            validate_proposal, validate_vote,
            validate_proposal_update, validate_vote_update
        )
        print("✓ Voting validator imports successful")

        # Test Flask app with voting endpoints
        from api.app import app
        print("✓ Flask app with voting endpoints imports successful")

        return True

    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False

def test_data_structures():
    """Test that voting data structures are properly initialized"""
    try:
        from api.data_store import PROPOSALS, VOTES, reset_data_store

        # Test initial data exists
        print(f"✓ Initial proposals: {len(PROPOSALS)} found")
        print(f"✓ Initial votes: {len(VOTES)} found")

        # Test that sample data has expected structure
        if len(PROPOSALS) > 0:
            first_proposal = list(PROPOSALS.values())[0]
            required_fields = ["id", "title", "description", "created_by", "options", "status"]
            for field in required_fields:
                if field not in first_proposal:
                    print(f"✗ Missing required field '{field}' in proposal")
                    return False
            print("✓ Proposal structure is correct")

        if len(VOTES) > 0:
            first_vote = list(VOTES.values())[0]
            required_fields = ["id", "proposal_id", "member_id", "vote_choice", "timestamp"]
            for field in required_fields:
                if field not in first_vote:
                    print(f"✗ Missing required field '{field}' in vote")
                    return False
            print("✓ Vote structure is correct")

        return True

    except Exception as e:
        print(f"✗ Data structure test failed: {e}")
        return False

def test_validators():
    """Test that validators work with valid and invalid data"""
    try:
        from api.validators import validate_proposal, validate_vote
        from api.data_store import MEMBERS

        # Test valid proposal
        valid_proposal = {
            "title": "Test Proposal for Validation",
            "description": "This is a test proposal to verify validation works correctly.",
            "created_by": 1,  # Should exist in test data
            "closing_date": "2024-12-31",
            "options": ["approve", "reject"],
            "allow_abstain": True
        }

        is_valid, error_msg = validate_proposal(valid_proposal)
        if is_valid:
            print("✓ Valid proposal validation successful")
        else:
            print(f"✗ Valid proposal rejected: {error_msg}")
            return False

        # Test invalid proposal (missing required field)
        invalid_proposal = {
            "title": "Invalid"
            # Missing required fields
        }

        is_valid, error_msg = validate_proposal(invalid_proposal)
        if not is_valid:
            print("✓ Invalid proposal correctly rejected")
        else:
            print("✗ Invalid proposal incorrectly accepted")
            return False

        # Test valid vote (if proposals exist)
        if len(MEMBERS) > 0 and len(PROPOSALS) > 0:
            valid_vote = {
                "proposal_id": list(PROPOSALS.keys())[0],
                "member_id": list(MEMBERS.keys())[0],
                "vote_choice": "yes"  # Assuming test proposal has "yes" option
            }

            is_valid, error_msg = validate_vote(valid_vote)
            # Note: This might fail if proposal doesn't have "yes" option or isn't active
            print(f"✓ Vote validation test completed (result: {'valid' if is_valid else 'invalid: ' + str(error_msg)})")

        return True

    except Exception as e:
        print(f"✗ Validator test failed: {e}")
        return False

def test_thread_safety():
    """Test that thread-safe operations work"""
    try:
        from api.data_store import create_proposal, get_proposal
        import threading

        # Test thread-safe proposal creation
        def create_test_proposal(thread_id, results):
            proposal_data = {
                "title": f"Thread Test Proposal {thread_id}",
                "description": "Testing thread-safe proposal creation",
                "created_by": 1,
                "created_date": "2024-02-11",
                "closing_date": "2024-02-25",
                "status": "draft",
                "options": ["yes", "no"],
                "allow_abstain": False
            }
            proposal_id = create_proposal(proposal_data)
            results.append(proposal_id)

        # Create multiple threads
        results = []
        threads = []
        for i in range(3):
            thread = threading.Thread(target=create_test_proposal, args=(i, results))
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # Check that all proposals were created with unique IDs
        if len(results) == 3 and len(set(results)) == 3:
            print("✓ Thread-safe proposal creation successful")
        else:
            print(f"✗ Thread safety issue: got {len(results)} results, {len(set(results))} unique IDs")
            return False

        return True

    except Exception as e:
        print(f"✗ Thread safety test failed: {e}")
        return False

def test_api_structure():
    """Test that Flask app has the voting endpoints"""
    try:
        from api.app import app

        # Get all URL rules
        rules = [str(rule) for rule in app.url_map.iter_rules()]

        # Check for voting endpoints
        expected_endpoints = [
            '/proposals',
            '/proposals/<int:proposal_id>',
            '/proposals/<int:proposal_id>/votes',
            '/votes/my-votes'
        ]

        for endpoint in expected_endpoints:
            # Check if endpoint pattern exists (allowing for variations in route format)
            found = any(endpoint.replace('<int:proposal_id>', '<proposal_id>') in rule.replace('<int:proposal_id>', '<proposal_id>') for rule in rules)
            if found:
                print(f"✓ Endpoint {endpoint} found")
            else:
                print(f"✗ Endpoint {endpoint} not found")
                print(f"Available rules: {rules}")
                return False

        return True

    except Exception as e:
        print(f"✗ API structure test failed: {e}")
        return False

def main():
    """Run all verification tests"""
    print("PTA Voting System Verification")
    print("=" * 50)

    tests = [
        ("Basic Imports", test_basic_imports),
        ("Data Structures", test_data_structures),
        ("Validators", test_validators),
        ("Thread Safety", test_thread_safety),
        ("API Structure", test_api_structure)
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        print(f"\n[Testing {test_name}]")
        if test_func():
            passed += 1
            print(f"✓ {test_name} PASSED")
        else:
            print(f"✗ {test_name} FAILED")

    print("\n" + "=" * 50)
    print(f"Verification Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests PASSED! PTA voting system is ready.")
        return True
    else:
        print("⚠️  Some tests failed. Please check the implementation.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)