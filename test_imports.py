#!/usr/bin/env python3
"""Test import validation"""

import sys
import traceback

def test_import(module_name, description):
    try:
        exec(f"import {module_name}")
        print(f"✅ {description}: OK")
        return True
    except Exception as e:
        print(f"❌ {description}: {str(e)}")
        traceback.print_exc()
        return False

def main():
    print("Testing module imports...")

    # Test basic modules first
    test_import("datetime", "datetime module")
    test_import("typing", "typing module")

    # Test Flask and related
    test_import("flask", "Flask framework")
    test_import("flask_cors", "Flask CORS")
    test_import("werkzeug.security", "Werkzeug security")
    test_import("jwt", "JWT library")

    # Test our modules
    test_import("api.data_store", "Data store module")
    test_import("api.audit_service", "Audit service module")
    test_import("api.validators", "Validators module")
    test_import("api.auth", "Auth module")

    # Test main app
    test_import("api.app", "Main Flask app")

if __name__ == "__main__":
    main()