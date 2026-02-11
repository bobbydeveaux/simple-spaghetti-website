"""
Test suite for PTA Voting System Authentication
Tests the complete authentication flow from code request to session validation.
"""

import pytest
import json
import sys
import os
from datetime import datetime, timedelta

# Add the api directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'api'))

# Import Flask app and voting system components
from app import app
from voting.data_store import voting_data_store
from voting.models import generate_voter_id


class TestVotingAuthentication:
    """Test class for voting system authentication flow."""

    @classmethod
    def setup_class(cls):
        """Set up test client and clear data store."""
        cls.client = app.test_client()
        cls.client.testing = True
        voting_data_store.clear_all_data()

    def setup_method(self):
        """Clear data before each test."""
        voting_data_store.clear_all_data()

    def test_request_verification_code_success(self):
        """Test successful verification code request."""
        response = self.client.post('/api/voting/auth/request-code',
                                  json={'email': 'test@voter.com'},
                                  content_type='application/json')

        assert response.status_code == 200
        data = json.loads(response.data)

        # Check response structure
        assert 'message' in data
        assert 'voter_id' in data
        assert 'code' in data
        assert 'test@voter.com' in data['message']

        # Verify voter was created in data store
        voter = voting_data_store.get_voter_by_email('test@voter.com')
        assert voter is not None
        assert voter.email == 'test@voter.com'

        # Verify verification code was created
        code = data['code']
        verification_code = voting_data_store.get_verification_code(code)
        assert verification_code is not None
        assert verification_code.email == 'test@voter.com'
        assert verification_code.is_valid()

    def test_request_verification_code_invalid_email(self):
        """Test verification code request with invalid email."""
        response = self.client.post('/api/voting/auth/request-code',
                                  json={'email': 'invalid-email'},
                                  content_type='application/json')

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
        assert 'Invalid email format' in data['error']

    def test_request_verification_code_missing_email(self):
        """Test verification code request without email."""
        response = self.client.post('/api/voting/auth/request-code',
                                  json={},
                                  content_type='application/json')

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
        assert 'Email is required' in data['error']

    def test_verify_code_success(self):
        """Test successful code verification and authentication."""
        # Step 1: Request verification code
        email = 'test@voter.com'
        response = self.client.post('/api/voting/auth/request-code',
                                  json={'email': email},
                                  content_type='application/json')
        assert response.status_code == 200
        request_data = json.loads(response.data)
        code = request_data['code']
        voter_id = request_data['voter_id']

        # Step 2: Verify code
        response = self.client.post('/api/voting/auth/verify',
                                  json={'email': email, 'code': code},
                                  content_type='application/json')

        assert response.status_code == 200
        data = json.loads(response.data)

        # Check response structure
        assert 'token' in data
        assert 'voter_id' in data
        assert 'session_id' in data
        assert 'expires_at' in data
        assert 'message' in data
        assert data['voter_id'] == voter_id

        # Verify session was created
        session = voting_data_store.get_session_by_token(data['token'])
        assert session is not None
        assert session.voter_id == voter_id
        assert session.is_valid()
        assert not session.is_admin

        # Verify code was marked as used
        verification_code = voting_data_store.get_verification_code(code)
        assert verification_code is None or not verification_code.is_valid()

    def test_verify_code_invalid_code(self):
        """Test code verification with invalid code."""
        response = self.client.post('/api/voting/auth/verify',
                                  json={'email': 'test@voter.com', 'code': '999999'},
                                  content_type='application/json')

        assert response.status_code == 401
        data = json.loads(response.data)
        assert 'error' in data
        assert 'Invalid or expired verification code' in data['error']

    def test_verify_code_email_mismatch(self):
        """Test code verification with mismatched email."""
        # Request code for one email
        response = self.client.post('/api/voting/auth/request-code',
                                  json={'email': 'test1@voter.com'},
                                  content_type='application/json')
        assert response.status_code == 200
        request_data = json.loads(response.data)
        code = request_data['code']

        # Try to verify with different email
        response = self.client.post('/api/voting/auth/verify',
                                  json={'email': 'test2@voter.com', 'code': code},
                                  content_type='application/json')

        assert response.status_code == 401
        data = json.loads(response.data)
        assert 'error' in data

    def test_admin_login_success(self):
        """Test successful admin login."""
        response = self.client.post('/api/voting/auth/admin-login',
                                  json={'username': 'admin@pta.school', 'password': 'admin123'},
                                  content_type='application/json')

        assert response.status_code == 200
        data = json.loads(response.data)

        # Check response structure
        assert 'token' in data
        assert 'voter_id' in data
        assert 'session_id' in data
        assert 'is_admin' in data
        assert 'expires_at' in data
        assert data['is_admin'] is True

        # Verify admin session was created
        session = voting_data_store.get_session_by_token(data['token'])
        assert session is not None
        assert session.is_admin is True
        assert session.is_valid()

    def test_admin_login_invalid_credentials(self):
        """Test admin login with invalid credentials."""
        response = self.client.post('/api/voting/auth/admin-login',
                                  json={'username': 'admin@pta.school', 'password': 'wrong'},
                                  content_type='application/json')

        assert response.status_code == 401
        data = json.loads(response.data)
        assert 'error' in data
        assert 'Invalid admin credentials' in data['error']

    def test_session_info_success(self):
        """Test getting session information."""
        # Create authenticated session
        email = 'test@voter.com'
        token = self._create_authenticated_session(email)

        # Get session info
        response = self.client.get('/api/voting/auth/session',
                                 headers={'Authorization': f'Bearer {token}'})

        assert response.status_code == 200
        data = json.loads(response.data)

        # Check response structure
        assert 'session_id' in data
        assert 'voter_id' in data
        assert 'email' in data
        assert 'is_admin' in data
        assert 'expires_at' in data
        assert 'voting_progress' in data
        assert data['email'] == email
        assert data['is_admin'] is False

        # Check voting progress structure
        progress = data['voting_progress']
        assert 'total_positions' in progress
        assert 'voted_positions' in progress
        assert 'remaining_positions' in progress

    def test_session_info_invalid_token(self):
        """Test getting session info with invalid token."""
        response = self.client.get('/api/voting/auth/session',
                                 headers={'Authorization': 'Bearer invalid_token'})

        assert response.status_code == 401
        data = json.loads(response.data)
        assert 'error' in data
        assert 'Invalid or expired session' in data['error']

    def test_session_info_missing_auth_header(self):
        """Test getting session info without authorization header."""
        response = self.client.get('/api/voting/auth/session')

        assert response.status_code == 401
        data = json.loads(response.data)
        assert 'error' in data
        assert 'Missing or invalid Authorization header' in data['error']

    def test_logout_success(self):
        """Test successful logout."""
        # Create authenticated session
        email = 'test@voter.com'
        token = self._create_authenticated_session(email)

        # Logout
        response = self.client.post('/api/voting/auth/logout',
                                  headers={'Authorization': f'Bearer {token}'})

        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'message' in data
        assert 'Logged out successfully' in data['message']

        # Verify session was invalidated
        session = voting_data_store.get_session_by_token(token)
        assert session is None

    def test_election_info_success(self):
        """Test getting election information."""
        response = self.client.get('/api/voting/election/info')

        assert response.status_code == 200
        data = json.loads(response.data)

        # Check response structure
        assert 'election_id' in data
        assert 'name' in data
        assert 'description' in data
        assert 'is_active' in data
        assert 'positions' in data
        assert 'stats' in data

        # Verify default election was created
        assert 'PTA Board Election 2026' in data['name']
        assert data['is_active'] is True
        assert isinstance(data['positions'], list)

        # Check positions have candidates
        for position_data in data['positions']:
            assert 'position' in position_data
            assert 'candidates' in position_data
            assert isinstance(position_data['candidates'], list)

            # Each candidate should have required fields
            for candidate in position_data['candidates']:
                assert 'candidate_id' in candidate
                assert 'name' in candidate
                assert 'position' in candidate

    def test_code_expiration(self):
        """Test that expired verification codes are rejected."""
        # Create a verification code manually with past expiry
        email = 'test@voter.com'
        voter = voting_data_store.create_or_get_voter(email)

        # Create expired code
        from voting.models import VerificationCode
        expired_code = VerificationCode(
            code='123456',
            email=email,
            voter_id=voter.voter_id,
            expires_at=datetime.now() - timedelta(minutes=1)  # Expired 1 minute ago
        )
        voting_data_store._verification_codes[expired_code.code] = expired_code

        # Try to verify expired code
        response = self.client.post('/api/voting/auth/verify',
                                  json={'email': email, 'code': '123456'},
                                  content_type='application/json')

        assert response.status_code == 401
        data = json.loads(response.data)
        assert 'error' in data
        assert 'Invalid or expired verification code' in data['error']

    def test_session_expiration(self):
        """Test that expired sessions are rejected."""
        # Create authenticated session
        email = 'test@voter.com'
        token = self._create_authenticated_session(email)

        # Manually expire the session
        session = voting_data_store.get_session_by_token(token)
        session.expires_at = datetime.now() - timedelta(minutes=1)

        # Try to use expired session
        response = self.client.get('/api/voting/auth/session',
                                 headers={'Authorization': f'Bearer {token}'})

        assert response.status_code == 401
        data = json.loads(response.data)
        assert 'error' in data
        assert 'Invalid or expired session' in data['error']

    def test_data_store_statistics(self):
        """Test data store statistics tracking."""
        # Create some test data
        email1 = 'test1@voter.com'
        email2 = 'test2@voter.com'
        self._create_authenticated_session(email1)
        self._create_authenticated_session(email2)

        # Get stats
        stats = voting_data_store.get_stats()

        assert 'total_voters' in stats
        assert 'active_sessions' in stats
        assert 'pending_codes' in stats
        assert 'total_votes' in stats
        assert 'total_candidates' in stats
        assert 'audit_log_entries' in stats

        assert stats['total_voters'] >= 2
        assert stats['active_sessions'] >= 2
        assert stats['total_candidates'] > 0  # From default election

    def _create_authenticated_session(self, email):
        """Helper method to create an authenticated session and return token."""
        # Request verification code
        response = self.client.post('/api/voting/auth/request-code',
                                  json={'email': email},
                                  content_type='application/json')
        assert response.status_code == 200
        request_data = json.loads(response.data)
        code = request_data['code']

        # Verify code
        response = self.client.post('/api/voting/auth/verify',
                                  json={'email': email, 'code': code},
                                  content_type='application/json')
        assert response.status_code == 200
        verify_data = json.loads(response.data)
        return verify_data['token']


def test_voting_authentication_integration():
    """Integration test for the complete authentication flow."""
    print("\\n=== PTA Voting System Authentication Integration Test ===")

    # Initialize test client
    client = app.test_client()
    client.testing = True
    voting_data_store.clear_all_data()

    email = 'integration@test.com'

    print(f"1. Requesting verification code for {email}...")
    response = client.post('/api/voting/auth/request-code',
                          json={'email': email},
                          content_type='application/json')
    assert response.status_code == 200
    request_data = json.loads(response.data)
    code = request_data['code']
    print(f"   ✓ Code received: {code}")

    print("2. Verifying code and authenticating...")
    response = client.post('/api/voting/auth/verify',
                          json={'email': email, 'code': code},
                          content_type='application/json')
    assert response.status_code == 200
    auth_data = json.loads(response.data)
    token = auth_data['token']
    print(f"   ✓ Authentication successful, token: {token[:20]}...")

    print("3. Getting session information...")
    response = client.get('/api/voting/auth/session',
                         headers={'Authorization': f'Bearer {token}'})
    assert response.status_code == 200
    session_data = json.loads(response.data)
    print(f"   ✓ Session valid for voter: {session_data['email']}")
    print(f"   ✓ Admin status: {session_data['is_admin']}")
    print(f"   ✓ Voting progress: {session_data['voting_progress']}")

    print("4. Getting election information...")
    response = client.get('/api/voting/election/info')
    assert response.status_code == 200
    election_data = json.loads(response.data)
    print(f"   ✓ Election: {election_data['name']}")
    print(f"   ✓ Positions available: {len(election_data['positions'])}")
    for pos in election_data['positions']:
        print(f"     - {pos['position']}: {len(pos['candidates'])} candidates")

    print("5. Testing admin login...")
    response = client.post('/api/voting/auth/admin-login',
                          json={'username': 'admin@pta.school', 'password': 'admin123'},
                          content_type='application/json')
    assert response.status_code == 200
    admin_data = json.loads(response.data)
    print(f"   ✓ Admin authentication successful")
    print(f"   ✓ Admin status: {admin_data['is_admin']}")

    print("6. Logging out...")
    response = client.post('/api/voting/auth/logout',
                          headers={'Authorization': f'Bearer {token}'})
    assert response.status_code == 200
    print("   ✓ Logout successful")

    print("7. Getting system statistics...")
    stats = voting_data_store.get_stats()
    print(f"   ✓ Total voters: {stats['total_voters']}")
    print(f"   ✓ Active sessions: {stats['active_sessions']}")
    print(f"   ✓ Total candidates: {stats['total_candidates']}")
    print(f"   ✓ Audit log entries: {stats['audit_log_entries']}")

    print("\\n=== All Authentication Tests Passed Successfully! ===\\n")


if __name__ == '__main__':
    # Run integration test
    test_voting_authentication_integration()

    # Run full test suite
    pytest.main([__file__, '-v'])