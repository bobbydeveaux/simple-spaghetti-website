#!/usr/bin/env python3
"""
Test script for admin endpoints in PTA Voting System
Tests candidate management, audit log functionality, and all admin API endpoints
"""

import requests
import json
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:5000/api/voting"
ADMIN_USERNAME = "admin@pta.school"
ADMIN_PASSWORD = "admin123"

# Global variables
admin_token = None
test_candidate_id = None

def log_test(test_name, success=True, message=""):
    """Log test results"""
    status = "✓ PASS" if success else "✗ FAIL"
    print(f"{status}: {test_name}")
    if message:
        print(f"   {message}")

def admin_login():
    """Login as admin and get token"""
    global admin_token

    print("=== Testing Admin Authentication ===")

    try:
        response = requests.post(
            f"{BASE_URL}/auth/admin-login",
            json={
                "username": ADMIN_USERNAME,
                "password": ADMIN_PASSWORD
            },
            headers={"Content-Type": "application/json"}
        )

        if response.status_code == 200:
            data = response.json()
            admin_token = data.get('token')
            log_test("Admin login", True, f"Token received: {admin_token[:20]}...")
            return True
        else:
            log_test("Admin login", False, f"Status {response.status_code}: {response.text}")
            return False

    except Exception as e:
        log_test("Admin login", False, f"Exception: {str(e)}")
        return False

def test_admin_dashboard():
    """Test admin dashboard endpoint"""
    print("\n=== Testing Admin Dashboard ===")

    if not admin_token:
        log_test("Admin dashboard", False, "No admin token available")
        return False

    headers = {
        "Authorization": f"Bearer {admin_token}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.get(f"{BASE_URL}/admin/dashboard", headers=headers)
        if response.status_code == 200:
            data = response.json()
            stats = data.get('dashboard', {})
            total_voters = stats.get('total_voters', 0)
            active_sessions = stats.get('active_sessions', 0)
            log_test("Get dashboard stats", True, f"Voters: {total_voters}, Sessions: {active_sessions}")
        else:
            log_test("Get dashboard stats", False, f"Status {response.status_code}: {response.text}")
            return False
    except Exception as e:
        log_test("Get dashboard stats", False, f"Exception: {str(e)}")
        return False

    return True

def test_voter_management():
    """Test voter management endpoints"""
    print("\n=== Testing Voter Management ===")

    if not admin_token:
        log_test("Voter management", False, "No admin token available")
        return False

    headers = {
        "Authorization": f"Bearer {admin_token}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.get(f"{BASE_URL}/admin/voters", headers=headers)
        if response.status_code == 200:
            data = response.json()
            voter_count = len(data.get('voters', []))
            log_test("Get all voters", True, f"Found {voter_count} voters")
        else:
            log_test("Get all voters", False, f"Status {response.status_code}: {response.text}")
            return False
    except Exception as e:
        log_test("Get all voters", False, f"Exception: {str(e)}")
        return False

    return True

def test_candidate_management():
    """Test candidate CRUD operations"""
    global test_candidate_id

    print("\n=== Testing Candidate Management ===")

    if not admin_token:
        log_test("Candidate management", False, "No admin token available")
        return False

    headers = {
        "Authorization": f"Bearer {admin_token}",
        "Content-Type": "application/json"
    }

    # Test 1: Get all candidates
    try:
        response = requests.get(f"{BASE_URL}/admin/candidates", headers=headers)
        if response.status_code == 200:
            data = response.json()
            candidate_count = len(data.get('candidates', []))
            log_test("Get all candidates", True, f"Found {candidate_count} candidates")
        else:
            log_test("Get all candidates", False, f"Status {response.status_code}: {response.text}")
            return False
    except Exception as e:
        log_test("Get all candidates", False, f"Exception: {str(e)}")
        return False

    # Test 2: Create a new candidate
    new_candidate = {
        "name": "Test Candidate Admin",
        "position": "president",
        "bio": "A test candidate created by admin endpoint testing."
    }

    try:
        response = requests.post(
            f"{BASE_URL}/admin/candidates",
            json=new_candidate,
            headers=headers
        )

        if response.status_code == 201:
            data = response.json()
            test_candidate_id = data.get('candidate', {}).get('candidate_id')
            log_test("Create candidate", True, f"Created candidate with ID: {test_candidate_id}")
        else:
            log_test("Create candidate", False, f"Status {response.status_code}: {response.text}")
            return False
    except Exception as e:
        log_test("Create candidate", False, f"Exception: {str(e)}")
        return False

    # Test 3: Update the candidate
    if test_candidate_id:
        updated_data = {
            "name": "Updated Test Candidate",
            "bio": "Updated biography for the test candidate."
        }

        try:
            response = requests.put(
                f"{BASE_URL}/admin/candidates/{test_candidate_id}",
                json=updated_data,
                headers=headers
            )

            if response.status_code == 200:
                log_test("Update candidate", True, "Candidate updated successfully")
            else:
                log_test("Update candidate", False, f"Status {response.status_code}: {response.text}")
        except Exception as e:
            log_test("Update candidate", False, f"Exception: {str(e)}")

    # Test 4: Get specific candidate
    if test_candidate_id:
        try:
            response = requests.get(
                f"{BASE_URL}/admin/candidates/{test_candidate_id}",
                headers=headers
            )

            if response.status_code == 200:
                data = response.json()
                candidate_name = data.get('candidate', {}).get('name')
                log_test("Get specific candidate", True, f"Retrieved: {candidate_name}")
            else:
                log_test("Get specific candidate", False, f"Status {response.status_code}: {response.text}")
        except Exception as e:
            log_test("Get specific candidate", False, f"Exception: {str(e)}")

    return True

def test_audit_logs():
    """Test audit log functionality"""
    print("\n=== Testing Audit Logs ===")

    if not admin_token:
        log_test("Audit logs", False, "No admin token available")
        return False

    headers = {
        "Authorization": f"Bearer {admin_token}",
        "Content-Type": "application/json"
    }

    # Test 1: Get all audit logs
    try:
        response = requests.get(f"{BASE_URL}/admin/audit", headers=headers)
        if response.status_code == 200:
            data = response.json()
            log_count = len(data.get('audit_logs', []))
            total_logs = data.get('total', 0)
            log_test("Get audit logs", True, f"Retrieved {log_count} logs out of {total_logs} total")
        else:
            log_test("Get audit logs", False, f"Status {response.status_code}: {response.text}")
            return False
    except Exception as e:
        log_test("Get audit logs", False, f"Exception: {str(e)}")
        return False

    # Test 2: Get audit logs with pagination
    try:
        response = requests.get(
            f"{BASE_URL}/admin/audit?limit=10&offset=0",
            headers=headers
        )
        if response.status_code == 200:
            data = response.json()
            log_test("Get paginated audit logs", True, f"Limit: {data.get('limit')}, Offset: {data.get('offset')}")
        else:
            log_test("Get paginated audit logs", False, f"Status {response.status_code}: {response.text}")
    except Exception as e:
        log_test("Get paginated audit logs", False, f"Exception: {str(e)}")

    # Test 3: Filter by action type
    try:
        response = requests.get(
            f"{BASE_URL}/admin/audit?action=ADMIN_ACTION",
            headers=headers
        )
        if response.status_code == 200:
            data = response.json()
            filtered_logs = len(data.get('audit_logs', []))
            log_test("Filter audit logs by action", True, f"Found {filtered_logs} ADMIN_ACTION logs")
        else:
            log_test("Filter audit logs by action", False, f"Status {response.status_code}: {response.text}")
    except Exception as e:
        log_test("Filter audit logs by action", False, f"Exception: {str(e)}")

    return True

def test_election_management():
    """Test election management endpoint"""
    print("\n=== Testing Election Management ===")

    if not admin_token:
        log_test("Election management", False, "No admin token available")
        return False

    headers = {
        "Authorization": f"Bearer {admin_token}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.get(f"{BASE_URL}/admin/elections", headers=headers)
        if response.status_code == 200:
            data = response.json()
            election_data = data.get('election', {})
            positions_count = len(election_data.get('positions', []))
            log_test("Get election data", True, f"Election has {positions_count} positions")
        else:
            log_test("Get election data", False, f"Status {response.status_code}: {response.text}")
            return False
    except Exception as e:
        log_test("Get election data", False, f"Exception: {str(e)}")
        return False

    return True

def test_results_analysis():
    """Test results analysis endpoint"""
    print("\n=== Testing Results Analysis ===")

    if not admin_token:
        log_test("Results analysis", False, "No admin token available")
        return False

    headers = {
        "Authorization": f"Bearer {admin_token}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.get(f"{BASE_URL}/admin/results", headers=headers)
        if response.status_code == 200:
            data = response.json()
            results = data.get('results', {})
            total_votes = results.get('total_votes', 0)
            log_test("Get voting results", True, f"Total votes analyzed: {total_votes}")
        else:
            log_test("Get voting results", False, f"Status {response.status_code}: {response.text}")
            return False
    except Exception as e:
        log_test("Get voting results", False, f"Exception: {str(e)}")
        return False

    return True

def test_admin_statistics():
    """Test admin statistics endpoint"""
    print("\n=== Testing Admin Statistics ===")

    if not admin_token:
        log_test("Admin statistics", False, "No admin token available")
        return False

    headers = {
        "Authorization": f"Bearer {admin_token}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.get(f"{BASE_URL}/admin/statistics", headers=headers)
        if response.status_code == 200:
            data = response.json()
            stats = data.get('statistics', {})
            total_voters = stats.get('total_voters', 0)
            total_candidates = stats.get('total_candidates', 0)
            log_test("Get admin statistics", True, f"Voters: {total_voters}, Candidates: {total_candidates}")
        else:
            log_test("Get admin statistics", False, f"Status {response.status_code}: {response.text}")
            return False
    except Exception as e:
        log_test("Get admin statistics", False, f"Exception: {str(e)}")
        return False

    return True

def cleanup_test_data():
    """Clean up test candidate"""
    print("\n=== Cleaning Up Test Data ===")

    if not admin_token or not test_candidate_id:
        return

    headers = {
        "Authorization": f"Bearer {admin_token}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.delete(
            f"{BASE_URL}/admin/candidates/{test_candidate_id}",
            headers=headers
        )

        if response.status_code == 200:
            log_test("Delete test candidate", True, "Test data cleaned up")
        else:
            log_test("Delete test candidate", False, f"Status {response.status_code}: {response.text}")
    except Exception as e:
        log_test("Delete test candidate", False, f"Exception: {str(e)}")

def main():
    """Run all admin endpoint tests"""
    print("🧪 Testing PTA Voting System Admin Endpoints")
    print("=" * 50)

    # Step 1: Admin login
    if not admin_login():
        print("\n❌ Cannot proceed without admin authentication")
        return False

    # Step 2: Test all admin endpoints
    dashboard_success = test_admin_dashboard()
    voter_success = test_voter_management()
    candidate_success = test_candidate_management()
    audit_success = test_audit_logs()
    election_success = test_election_management()
    results_success = test_results_analysis()
    stats_success = test_admin_statistics()

    # Step 3: Cleanup
    cleanup_test_data()

    # Summary
    print("\n" + "=" * 50)
    all_tests_passed = all([
        dashboard_success, voter_success, candidate_success,
        audit_success, election_success, results_success, stats_success
    ])

    if all_tests_passed:
        print("🎉 All admin endpoint tests passed!")
        print("\n📋 Tested Admin Endpoints:")
        print("   • GET /api/voting/admin/dashboard - System overview and statistics")
        print("   • GET /api/voting/admin/voters - List all voters with pagination")
        print("   • GET /api/voting/admin/candidates - Candidate management (CRUD)")
        print("   • GET /api/voting/admin/audit - Audit trail with filtering")
        print("   • GET /api/voting/admin/elections - Election management info")
        print("   • GET /api/voting/admin/results - Comprehensive voting results")
        print("   • GET /api/voting/admin/statistics - Admin statistics")
        return True
    else:
        print("❌ Some admin endpoint tests failed")
        return False

if __name__ == "__main__":
    try:
        success = main()
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        exit(1)
    except Exception as e:
        print(f"\n\n💥 Unexpected error: {str(e)}")
        exit(1)
