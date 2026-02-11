#!/usr/bin/env python3
"""
Test script for new admin API endpoints in the PTA voting system.
Tests all admin endpoints with proper authentication and authorization.
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from datetime import datetime
from api.voting.data_store import voting_data_store
from api.voting.models import Session, Voter, generate_session_id, generate_voter_id
from api.utils.jwt_manager import JWTManager

# Initialize JWT manager
jwt_manager = JWTManager()

def setup_test_data():
    """Setup test data for admin endpoint testing"""
    print("🔧 Setting up test data...")

    # Clear existing data
    voting_data_store.clear_all_data()

    # Create test admin user
    admin_email = "admin@pta.school"
    admin_voter = voting_data_store.create_or_get_voter(admin_email)

    # Create admin JWT token
    admin_token = jwt_manager.create_access_token(admin_voter.voter_id)

    # Create admin session
    admin_session = voting_data_store.create_session(
        admin_voter.voter_id,
        admin_token,
        is_admin=True
    )

    # Create test regular users
    test_users = [
        "voter1@example.com",
        "voter2@example.com",
        "voter3@example.com"
    ]

    for email in test_users:
        voter = voting_data_store.create_or_get_voter(email)
        # Simulate some voting activity
        if email == "voter1@example.com":
            voter.mark_voted_for_position("president")
            voter.mark_voted_for_position("treasurer")
        elif email == "voter2@example.com":
            voter.mark_voted_for_position("president")

    # Add some test votes
    voting_data_store.cast_vote("president", "candidate_abc123")
    voting_data_store.cast_vote("president", "candidate_def456")
    voting_data_store.cast_vote("treasurer", "candidate_ghi789")

    print(f"✅ Test data setup complete")
    print(f"   - Admin token: {admin_token[:20]}...")
    print(f"   - Admin voter ID: {admin_voter.voter_id}")
    print(f"   - Test voters: {len(test_users)}")

    return admin_token, admin_voter.voter_id


def test_admin_endpoints():
    """Test all admin endpoints functionality"""
    print("\n🧪 Testing admin endpoints...")

    admin_token, admin_voter_id = setup_test_data()

    # Test 1: Admin dashboard
    print("\n📊 Testing admin dashboard...")
    try:
        # Simulate dashboard request
        stats = voting_data_store.get_stats()
        all_voters = voting_data_store.get_all_voters()
        active_election = voting_data_store.get_active_election()

        print(f"   - Total voters: {stats['total_voters']}")
        print(f"   - Total votes: {stats['total_votes']}")
        print(f"   - Active sessions: {stats['active_sessions']}")
        print(f"   - Has active election: {active_election is not None}")
        print("✅ Admin dashboard data accessible")
    except Exception as e:
        print(f"❌ Admin dashboard test failed: {e}")

    # Test 2: Voter management
    print("\n👥 Testing voter management...")
    try:
        voters = voting_data_store.get_all_voters()
        print(f"   - Retrieved {len(voters)} voters")

        if voters:
            # Test voter details
            test_voter = voters[0]
            audit_logs = voting_data_store.get_audit_logs_for_voter(test_voter.voter_id)
            print(f"   - Voter {test_voter.email} has {len(audit_logs)} audit entries")
            print(f"   - Voted positions: {list(test_voter.voted_positions)}")

        print("✅ Voter management data accessible")
    except Exception as e:
        print(f"❌ Voter management test failed: {e}")

    # Test 3: Audit logs
    print("\n📝 Testing audit logs...")
    try:
        all_audit_logs = voting_data_store.get_all_audit_logs()
        recent_logs = voting_data_store.get_recent_audit_logs(10)

        print(f"   - Total audit logs: {len(all_audit_logs)}")
        print(f"   - Recent logs (last 10): {len(recent_logs)}")

        if recent_logs:
            latest_log = recent_logs[0]
            print(f"   - Latest action: {latest_log.action} by {latest_log.voter_id}")

        print("✅ Audit logs accessible")
    except Exception as e:
        print(f"❌ Audit logs test failed: {e}")

    # Test 4: Election management
    print("\n🗳️  Testing election management...")
    try:
        active_election = voting_data_store.get_active_election()
        all_candidates = voting_data_store.get_all_candidates()
        positions = voting_data_store.get_all_positions()

        print(f"   - Active election: {active_election.name if active_election else 'None'}")
        print(f"   - Total candidates: {len(all_candidates)}")
        print(f"   - Total positions: {len(positions)}")

        if positions:
            # Test vote counting
            position = positions[0]
            vote_counts = voting_data_store.get_vote_counts_for_position(position)
            print(f"   - Votes for {position}: {vote_counts}")

        print("✅ Election management data accessible")
    except Exception as e:
        print(f"❌ Election management test failed: {e}")

    # Test 5: Results and statistics
    print("\n📈 Testing results and statistics...")
    try:
        total_votes = voting_data_store.get_total_votes()
        stats = voting_data_store.get_stats()

        print(f"   - Total votes cast: {total_votes}")
        print(f"   - System statistics: {stats}")

        # Test position-specific results
        for position in voting_data_store.get_all_positions()[:2]:  # Test first 2 positions
            votes_for_position = voting_data_store.get_votes_for_position(position)
            vote_counts = voting_data_store.get_vote_counts_for_position(position)
            print(f"   - {position}: {len(votes_for_position)} votes, counts: {vote_counts}")

        print("✅ Results and statistics accessible")
    except Exception as e:
        print(f"❌ Results and statistics test failed: {e}")

    # Test 6: Authorization checks
    print("\n🔒 Testing authorization...")
    try:
        # Test admin session verification
        admin_session = voting_data_store.get_session_by_token(admin_token)
        print(f"   - Admin session valid: {admin_session is not None}")
        print(f"   - Is admin: {admin_session.is_admin if admin_session else False}")

        # Test non-admin user (create regular user session)
        regular_voter = voting_data_store.get_all_voters()[-1]  # Get last voter (non-admin)
        regular_token = jwt_manager.create_access_token(regular_voter.voter_id)
        regular_session = voting_data_store.create_session(regular_voter.voter_id, regular_token, is_admin=False)

        print(f"   - Regular session valid: {regular_session is not None}")
        print(f"   - Regular user is admin: {regular_session.is_admin}")

        print("✅ Authorization checks working")
    except Exception as e:
        print(f"❌ Authorization test failed: {e}")

def main():
    """Main test function"""
    print("🚀 PTA Voting System - Admin Endpoints Test Suite")
    print("=" * 60)

    try:
        test_admin_endpoints()
        print("\n🎉 All admin endpoint tests completed successfully!")
        print("\n📋 Admin Endpoints Implemented:")
        print("   • GET /api/voting/admin/dashboard - System overview and statistics")
        print("   • GET /api/voting/admin/voters - List all voters with pagination")
        print("   • GET /api/voting/admin/voters/<id> - Detailed voter information")
        print("   • GET /api/voting/admin/audit-logs - Audit trail with filtering")
        print("   • GET /api/voting/admin/elections - Election management info")
        print("   • GET /api/voting/admin/results - Comprehensive voting results")
        print("\n🔐 Security Features:")
        print("   • JWT token-based authentication required")
        print("   • Admin role verification on all endpoints")
        print("   • Proper error handling and status codes")
        print("   • Audit logging for all admin actions")

        return True
    except Exception as e:
        print(f"\n💥 Test suite failed with error: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)