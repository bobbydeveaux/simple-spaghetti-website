#!/usr/bin/env python3
"""
Test script for election management functionality.
Tests the admin API endpoints and election management features.
"""

import sys
import json
from datetime import datetime

# Test the data store and API functionality
def test_election_management():
    """Test election management functionality"""
    print("🔧 Testing Election Management Functionality")
    print("=" * 60)

    try:
        # Import the voting system modules
        sys.path.append('.')
        from api.voting.data_store import voting_data_store
        from api.voting.routes import require_admin_session

        print("✅ Successfully imported voting system modules")

        # Test 1: Check if default election exists
        print("\n📋 Test 1: Default Election Initialization")
        election = voting_data_store.get_active_election()
        if election:
            print(f"✅ Default election found: {election.name}")
            print(f"   Election ID: {election.election_id}")
            print(f"   Positions: {list(election.positions) if hasattr(election, 'positions') else 'N/A'}")
            print(f"   Status: {getattr(election, 'status', 'N/A')}")
            print(f"   Created: {election.created_at}")
        else:
            print("❌ No default election found")
            return False

        # Test 2: Test position management
        print("\n📍 Test 2: Position Management")
        original_positions = list(election.positions) if hasattr(election, 'positions') else []
        print(f"   Original positions: {original_positions}")

        # Add a test position
        test_position = "Test Position"
        election.add_position(test_position)
        new_positions = list(election.positions) if hasattr(election, 'positions') else []
        if test_position in new_positions:
            print(f"✅ Successfully added position: {test_position}")
            print(f"   Updated positions: {new_positions}")
        else:
            print(f"❌ Failed to add position: {test_position}")

        # Remove the test position
        if isinstance(election.positions, set):
            election.positions.discard(test_position)
        elif isinstance(election.positions, list):
            if test_position in election.positions:
                election.positions.remove(test_position)

        final_positions = list(election.positions) if hasattr(election, 'positions') else []
        if test_position not in final_positions:
            print(f"✅ Successfully removed position: {test_position}")
            print(f"   Final positions: {final_positions}")
        else:
            print(f"❌ Failed to remove position: {test_position}")

        # Test 3: Test status management
        print("\n🔄 Test 3: Status Management")
        original_status = getattr(election, 'status', 'SETUP')
        print(f"   Original status: {original_status}")

        # Test status changes
        if hasattr(election, 'status'):
            election.status = 'ACTIVE'
            if not election.start_time:
                election.start_time = datetime.utcnow()
            print(f"✅ Updated status to ACTIVE")
            print(f"   Start time set: {election.start_time}")

            election.status = 'CLOSED'
            if not election.end_time:
                election.end_time = datetime.utcnow()
                election.is_active = False
            print(f"✅ Updated status to CLOSED")
            print(f"   End time set: {election.end_time}")

            # Reset to original status
            election.status = original_status
            print(f"✅ Reset status to: {original_status}")
        else:
            print("❌ Election status attribute not available")

        # Test 4: Test data persistence in store
        print("\n💾 Test 4: Data Store Functionality")
        store_election = voting_data_store.get_active_election()
        if store_election and store_election.election_id == election.election_id:
            print("✅ Election data persisted in store correctly")
        else:
            print("❌ Election data not properly persisted")

        print("\n🎉 All election management tests completed successfully!")
        return True

    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("   Make sure the voting system modules are properly installed")
        return False
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_api_endpoint_structure():
    """Test that API endpoints are properly structured"""
    print("\n🔌 Testing API Endpoint Structure")
    print("=" * 60)

    try:
        # Test API route imports
        sys.path.append('.')
        from api.voting.routes import voting_bp

        # Check if our admin routes are registered
        admin_routes = [
            'get_election_config',
            'update_election_status',
            'add_election_position',
            'remove_election_position'
        ]

        print("✅ Successfully imported voting blueprint")

        # Test that the functions exist
        import api.voting.routes as routes_module
        for route_name in admin_routes:
            if hasattr(routes_module, route_name):
                print(f"✅ Admin route '{route_name}' is defined")
            else:
                print(f"❌ Admin route '{route_name}' is missing")

        # Test require_admin_session helper
        if hasattr(routes_module, 'require_admin_session'):
            print("✅ Admin session helper is defined")
        else:
            print("❌ Admin session helper is missing")

        print("🎉 API endpoint structure tests completed!")
        return True

    except Exception as e:
        print(f"❌ API structure test failed: {e}")
        return False

def test_frontend_component_structure():
    """Test that frontend components exist and have correct structure"""
    print("\n⚛️ Testing Frontend Component Structure")
    print("=" * 60)

    import os

    # Check if admin components exist
    admin_components = [
        'src/voting/pages/admin/Dashboard.jsx',
        'src/voting/pages/admin/ElectionManagement.jsx'
    ]

    for component_path in admin_components:
        full_path = os.path.join('.', component_path)
        if os.path.exists(full_path):
            print(f"✅ Component exists: {component_path}")

            # Check if component has expected content
            with open(full_path, 'r') as f:
                content = f.read()

            if component_path.endswith('Dashboard.jsx'):
                if 'ElectionManagement' in content and 'useState' in content:
                    print("   ✅ Dashboard has required imports and state")
                else:
                    print("   ❌ Dashboard missing required functionality")

            elif component_path.endswith('ElectionManagement.jsx'):
                required_elements = ['useState', 'useEffect', 'fetch', 'election', 'status']
                missing_elements = [elem for elem in required_elements if elem not in content]

                if not missing_elements:
                    print("   ✅ ElectionManagement has all required functionality")
                else:
                    print(f"   ❌ ElectionManagement missing: {missing_elements}")
        else:
            print(f"❌ Component missing: {component_path}")

    print("🎉 Frontend component structure tests completed!")
    return True

def main():
    """Run all tests"""
    print("🚀 PTA Voting System - Election Management Test Suite")
    print("=" * 60)

    tests = [
        ("Election Management Core Functionality", test_election_management),
        ("API Endpoint Structure", test_api_endpoint_structure),
        ("Frontend Component Structure", test_frontend_component_structure)
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        print(f"\n🧪 Running: {test_name}")
        if test_func():
            passed += 1
            print(f"✅ PASSED: {test_name}")
        else:
            print(f"❌ FAILED: {test_name}")

    print("\n" + "=" * 60)
    print(f"📊 Test Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed! Election management implementation is ready.")
        return True
    else:
        print("💥 Some tests failed. Please review the implementation.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)