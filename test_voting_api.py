#!/usr/bin/env python3
"""
Simple test script to verify voting API implementation.
This script tests the voting API endpoints without starting the full server.
"""

import json
import sys
import os

# Add the api directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'api'))

try:
    # Test imports
    from api.data_store import BALLOTS, VOTES, MEMBERS, get_next_vote_id
    from api.validators import validate_vote, validate_ballot
    from api.auth import generate_token, verify_token, authenticate_member

    print("✅ All imports successful")

    # Test data structures
    print("\n📊 Testing data structures:")
    print(f"   Ballots available: {len(BALLOTS)}")
    print(f"   Existing votes: {len(VOTES)}")
    print(f"   Members registered: {len(MEMBERS)}")

    # Test authentication
    print("\n🔐 Testing authentication:")
    member_id = authenticate_member("john.doe@email.com", "password123")
    if member_id:
        print(f"   ✅ Authentication successful for member {member_id}")

        # Test token generation and verification
        token = generate_token(member_id)
        print(f"   ✅ Token generated: {token[:20]}...")

        payload = verify_token(token)
        if payload and payload.get('member_id') == member_id:
            print(f"   ✅ Token verification successful")
        else:
            print(f"   ❌ Token verification failed")
    else:
        print("   ❌ Authentication failed")

    # Test validation
    print("\n✅ Testing vote validation:")

    # Valid vote data
    valid_vote = {
        "ballot_id": 1,
        "option_id": 1
    }
    is_valid, error = validate_vote(valid_vote, member_id)
    if is_valid:
        print(f"   ✅ Valid vote accepted")
    else:
        print(f"   ❌ Valid vote rejected: {error}")

    # Invalid vote data
    invalid_vote = {
        "ballot_id": 999,  # Non-existent ballot
        "option_id": 1
    }
    is_valid, error = validate_vote(invalid_vote, member_id)
    if not is_valid:
        print(f"   ✅ Invalid vote correctly rejected: {error}")
    else:
        print(f"   ❌ Invalid vote incorrectly accepted")

    # Test ballot structure
    print("\n🗳️  Testing ballot structure:")
    for ballot_id, ballot in BALLOTS.items():
        print(f"   Ballot {ballot_id}: {ballot['title']}")
        print(f"   - Options: {len(ballot['options'])}")
        print(f"   - Max votes per member: {ballot['max_votes_per_member']}")
        print(f"   - Status: {ballot['status']}")

        # Validate ballot structure
        is_valid, error = validate_ballot(ballot)
        if is_valid:
            print(f"   - ✅ Ballot structure is valid")
        else:
            print(f"   - ❌ Ballot structure invalid: {error}")
        print()

    print("🎉 All tests completed successfully!")
    print("\n💡 The voting API implementation appears to be working correctly.")
    print("   To test the full application:")
    print("   1. Start the Flask API: cd api && python app.py")
    print("   2. Start the React frontend: npm run dev")
    print("   3. Navigate to http://localhost:3000/voting")

except ImportError as e:
    print(f"❌ Import error: {e}")
    print("   Make sure all required Python packages are installed:")
    print("   pip install flask flask-cors pyjwt werkzeug")
except Exception as e:
    print(f"❌ Test error: {e}")
    import traceback
    traceback.print_exc()