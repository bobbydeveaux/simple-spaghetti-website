#!/usr/bin/env python3
"""
Comprehensive test suite for admin services and audit logging implementation.
Tests all admin endpoints, role-based access control, and audit trail functionality.
"""

import requests
import json
from datetime import datetime
from time import sleep

# Configuration
BASE_URL = "http://localhost:5000"
ADMIN_EMAIL = "admin@library.com"
ADMIN_PASSWORD = "admin123"
TEST_USER_EMAIL = "john.doe@email.com"
TEST_USER_PASSWORD = "password123"

class AdminTestSuite:
    def __init__(self):
        self.admin_token = None
        self.user_token = None
        self.test_results = []

    def log_result(self, test_name, passed, details=""):
        """Log test result"""
        result = {
            "test": test_name,
            "passed": passed,
            "details": details,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        self.test_results.append(result)
        status = "PASS" if passed else "FAIL"
        print(f"[{status}] {test_name}: {details}")

    def setup_tokens(self):
        """Authenticate and get tokens for both admin and regular user"""
        print("\\n=== AUTHENTICATION TESTS ===")

        # Test admin login
        try:
            response = requests.post(f"{BASE_URL}/auth/login", json={
                "email": ADMIN_EMAIL,
                "password": ADMIN_PASSWORD
            })
            if response.status_code == 200:
                self.admin_token = response.json()["token"]
                self.log_result("Admin Login", True, "Admin authentication successful")
            else:
                self.log_result("Admin Login", False, f"Failed with status {response.status_code}")
                return False
        except Exception as e:
            self.log_result("Admin Login", False, f"Exception: {str(e)}")
            return False

        # Test user login
        try:
            response = requests.post(f"{BASE_URL}/auth/login", json={
                "email": TEST_USER_EMAIL,
                "password": TEST_USER_PASSWORD
            })
            if response.status_code == 200:
                self.user_token = response.json()["token"]
                self.log_result("User Login", True, "User authentication successful")
            else:
                self.log_result("User Login", False, f"Failed with status {response.status_code}")
                return False
        except Exception as e:
            self.log_result("User Login", False, f"Exception: {str(e)}")
            return False

        return True

    def test_admin_dashboard(self):
        """Test admin dashboard endpoint"""
        print("\\n=== ADMIN DASHBOARD TESTS ===")

        headers = {"Authorization": f"Bearer {self.admin_token}"}

        try:
            response = requests.get(f"{BASE_URL}/admin/dashboard", headers=headers)
            if response.status_code == 200:
                data = response.json()
                expected_keys = ["system_overview", "member_statistics", "audit_statistics"]
                has_all_keys = all(key in data for key in expected_keys)

                if has_all_keys:
                    self.log_result("Admin Dashboard Content", True, "All expected sections present")

                    # Check if system overview has correct structure
                    system_overview = data["system_overview"]
                    if "total_books" in system_overview and "total_members" in system_overview:
                        self.log_result("Dashboard System Stats", True, f"Books: {system_overview['total_books']}, Members: {system_overview['total_members']}")
                    else:
                        self.log_result("Dashboard System Stats", False, "Missing system statistics")
                else:
                    self.log_result("Admin Dashboard Content", False, f"Missing keys: {[k for k in expected_keys if k not in data]}")
            else:
                self.log_result("Admin Dashboard Access", False, f"HTTP {response.status_code}: {response.text}")
        except Exception as e:
            self.log_result("Admin Dashboard Access", False, f"Exception: {str(e)}")

    def test_admin_member_management(self):
        """Test admin member management endpoints"""
        print("\\n=== ADMIN MEMBER MANAGEMENT TESTS ===")

        headers = {"Authorization": f"Bearer {self.admin_token}"}

        # Test list all members
        try:
            response = requests.get(f"{BASE_URL}/admin/members", headers=headers)
            if response.status_code == 200:
                members = response.json()
                if isinstance(members, list) and len(members) > 0:
                    self.log_result("List Members", True, f"Found {len(members)} members")

                    # Check if admin user is in the list
                    admin_found = any(member["email"] == ADMIN_EMAIL for member in members)
                    self.log_result("Admin User in List", admin_found, "Admin user found in members list")

                    # Test get specific member details
                    admin_member = next((m for m in members if m["email"] == ADMIN_EMAIL), None)
                    if admin_member:
                        member_id = admin_member["id"]
                        detail_response = requests.get(f"{BASE_URL}/admin/members/{member_id}", headers=headers)
                        if detail_response.status_code == 200:
                            detail_data = detail_response.json()
                            if "loan_history" in detail_data:
                                self.log_result("Member Details", True, "Member details include loan history")
                            else:
                                self.log_result("Member Details", False, "Member details missing loan history")
                        else:
                            self.log_result("Member Details", False, f"HTTP {detail_response.status_code}")
                else:
                    self.log_result("List Members", False, "No members returned or invalid format")
            else:
                self.log_result("List Members", False, f"HTTP {response.status_code}: {response.text}")
        except Exception as e:
            self.log_result("List Members", False, f"Exception: {str(e)}")

    def test_role_based_access_control(self):
        """Test that regular users cannot access admin endpoints"""
        print("\\n=== ROLE-BASED ACCESS CONTROL TESTS ===")

        user_headers = {"Authorization": f"Bearer {self.user_token}"}

        # Test user trying to access admin dashboard
        try:
            response = requests.get(f"{BASE_URL}/admin/dashboard", headers=user_headers)
            if response.status_code == 403:
                self.log_result("User Dashboard Access Denied", True, "Regular user correctly denied admin access")
            else:
                self.log_result("User Dashboard Access Denied", False, f"Expected 403, got {response.status_code}")
        except Exception as e:
            self.log_result("User Dashboard Access Denied", False, f"Exception: {str(e)}")

        # Test user trying to access admin members endpoint
        try:
            response = requests.get(f"{BASE_URL}/admin/members", headers=user_headers)
            if response.status_code == 403:
                self.log_result("User Members Access Denied", True, "Regular user correctly denied admin members access")
            else:
                self.log_result("User Members Access Denied", False, f"Expected 403, got {response.status_code}")
        except Exception as e:
            self.log_result("User Members Access Denied", False, f"Exception: {str(e)}")

    def test_audit_logging(self):
        """Test audit logging functionality"""
        print("\\n=== AUDIT LOGGING TESTS ===")

        headers = {"Authorization": f"Bearer {self.admin_token}"}

        # Create a test member to generate audit logs
        test_member_data = {
            "name": "Test User Audit",
            "email": "test.audit@email.com",
            "password": "testpassword123"
        }

        try:
            # Create member (should generate audit log)
            response = requests.post(f"{BASE_URL}/members", json=test_member_data)
            if response.status_code == 201:
                self.log_result("Test Member Creation", True, "Test member created for audit testing")

                # Wait a moment for audit log to be created
                sleep(1)

                # Check audit logs
                audit_response = requests.get(f"{BASE_URL}/admin/audit-logs?limit=10", headers=headers)
                if audit_response.status_code == 200:
                    audit_logs = audit_response.json()
                    if isinstance(audit_logs, list) and len(audit_logs) > 0:
                        # Look for member creation in recent logs
                        member_create_log = next((log for log in audit_logs
                                                if log.get("action") == "CREATE"
                                                and log.get("resource_type") == "member"), None)

                        if member_create_log:
                            self.log_result("Audit Log Creation", True, "Member creation audit log found")

                            # Check log structure
                            expected_fields = ["timestamp", "user_id", "action", "resource_type", "status"]
                            has_required_fields = all(field in member_create_log for field in expected_fields)
                            self.log_result("Audit Log Structure", has_required_fields, f"Log contains required fields: {expected_fields}")
                        else:
                            self.log_result("Audit Log Creation", False, "Member creation audit log not found")
                    else:
                        self.log_result("Audit Logs Retrieval", False, "No audit logs returned or invalid format")
                else:
                    self.log_result("Audit Logs Access", False, f"HTTP {audit_response.status_code}")
            else:
                self.log_result("Test Member Creation", False, f"HTTP {response.status_code}")
        except Exception as e:
            self.log_result("Audit Logging Test", False, f"Exception: {str(e)}")

    def test_member_role_update(self):
        """Test updating member roles (admin functionality)"""
        print("\\n=== MEMBER ROLE UPDATE TESTS ===")

        headers = {"Authorization": f"Bearer {self.admin_token}"}

        try:
            # Get list of members to find a non-admin user
            response = requests.get(f"{BASE_URL}/admin/members", headers=headers)
            if response.status_code == 200:
                members = response.json()
                regular_user = next((m for m in members if m.get("role") == "user"), None)

                if regular_user:
                    member_id = regular_user["id"]
                    original_role = regular_user["role"]

                    # Update user to admin role
                    update_data = {"role": "admin"}
                    update_response = requests.put(f"{BASE_URL}/admin/members/{member_id}",
                                                 json=update_data, headers=headers)

                    if update_response.status_code == 200:
                        updated_member = update_response.json()
                        if updated_member.get("role") == "admin":
                            self.log_result("Role Update to Admin", True, f"User {updated_member['name']} promoted to admin")

                            # Revert back to original role
                            revert_data = {"role": original_role}
                            revert_response = requests.put(f"{BASE_URL}/admin/members/{member_id}",
                                                         json=revert_data, headers=headers)
                            if revert_response.status_code == 200:
                                self.log_result("Role Revert", True, "Role successfully reverted")
                            else:
                                self.log_result("Role Revert", False, f"Failed to revert role: HTTP {revert_response.status_code}")
                        else:
                            self.log_result("Role Update to Admin", False, "Role update did not take effect")
                    else:
                        self.log_result("Role Update to Admin", False, f"HTTP {update_response.status_code}")
                else:
                    self.log_result("Find Regular User", False, "No regular user found for role update test")
            else:
                self.log_result("Get Members for Role Test", False, f"HTTP {response.status_code}")
        except Exception as e:
            self.log_result("Member Role Update Test", False, f"Exception: {str(e)}")

    def test_api_root_endpoint(self):
        """Test that API root shows admin endpoints"""
        print("\\n=== API ROOT ENDPOINT TEST ===")

        try:
            response = requests.get(f"{BASE_URL}/")
            if response.status_code == 200:
                data = response.json()
                if "admin_endpoints" in data:
                    admin_endpoints = data["admin_endpoints"]
                    expected_admin_endpoints = ["admin_dashboard", "admin_members", "admin_audit_logs"]
                    has_admin_endpoints = all(endpoint in admin_endpoints for endpoint in expected_admin_endpoints)
                    self.log_result("API Root Admin Endpoints", has_admin_endpoints, f"Admin endpoints documented: {list(admin_endpoints.keys())}")
                else:
                    self.log_result("API Root Admin Endpoints", False, "Admin endpoints not documented in root")
            else:
                self.log_result("API Root Access", False, f"HTTP {response.status_code}")
        except Exception as e:
            self.log_result("API Root Test", False, f"Exception: {str(e)}")

    def run_all_tests(self):
        """Run complete test suite"""
        print("🚀 Starting Admin Services and Audit Logging Test Suite")
        print("=" * 60)

        # Setup authentication
        if not self.setup_tokens():
            print("❌ Authentication setup failed. Cannot continue with tests.")
            return False

        # Run all test suites
        self.test_admin_dashboard()
        self.test_admin_member_management()
        self.test_role_based_access_control()
        self.test_audit_logging()
        self.test_member_role_update()
        self.test_api_root_endpoint()

        # Print summary
        self.print_summary()

        # Return overall success
        return all(result["passed"] for result in self.test_results)

    def print_summary(self):
        """Print test summary"""
        print("\\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)

        passed = sum(1 for result in self.test_results if result["passed"])
        total = len(self.test_results)

        print(f"Total Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")
        print(f"Success Rate: {(passed/total)*100:.1f}%")

        if total - passed > 0:
            print("\\n❌ Failed Tests:")
            for result in self.test_results:
                if not result["passed"]:
                    print(f"  - {result['test']}: {result['details']}")
        else:
            print("\\n✅ All tests passed!")

def main():
    """Main test function"""
    print("Admin Services and Audit Logging Test Suite")
    print("Make sure the Flask API server is running on http://localhost:5000")
    input("Press Enter to continue...")

    test_suite = AdminTestSuite()
    success = test_suite.run_all_tests()

    if success:
        print("\\n🎉 All tests completed successfully!")
        return 0
    else:
        print("\\n💥 Some tests failed. Check the details above.")
        return 1

if __name__ == "__main__":
    exit(main())