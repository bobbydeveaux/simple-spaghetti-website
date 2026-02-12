#!/usr/bin/env python3
"""
Admin creation script for PTA voting system.
This script should be run once to create the initial admin user.
"""

import sys
import os
import getpass
from typing import Optional

# Add the api directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from utils.password import hash_password
from voting.data_store import VotingDataStore


def create_admin_user():
    """Create an admin user interactively."""
    print("PTA Voting System - Admin Creation")
    print("=" * 40)

    # Get admin details
    while True:
        email = input("Admin email address: ").strip()
        if email and '@' in email:
            break
        print("Please enter a valid email address.")

    while True:
        full_name = input("Admin full name: ").strip()
        if full_name:
            break
        print("Please enter the admin's full name.")

    while True:
        password = getpass.getpass("Password (min 8 chars): ")
        if len(password) >= 8:
            break
        print("Password must be at least 8 characters long.")

    while True:
        confirm_password = getpass.getpass("Confirm password: ")
        if password == confirm_password:
            break
        print("Passwords do not match. Please try again.")

    # Create admin
    try:
        data_store = VotingDataStore()

        # Check if admin already exists
        existing_admin = data_store.get_admin_by_email(email)
        if existing_admin:
            print(f"Error: Admin with email {email} already exists.")
            return False

        # Hash password and create admin
        password_hash = hash_password(password)
        admin = data_store.create_admin(email, password_hash, full_name)

        print(f"\nAdmin created successfully!")
        print(f"Admin ID: {admin.admin_id}")
        print(f"Email: {admin.email}")
        print(f"Full Name: {admin.full_name}")
        print(f"\nThe admin can now log in to the system.")

        return True

    except Exception as e:
        print(f"Error creating admin: {str(e)}")
        return False


def list_admins():
    """List all existing admins."""
    try:
        data_store = VotingDataStore()
        admins = data_store.list_admins()

        if not admins:
            print("No admin users found.")
            return

        print(f"\nExisting Admin Users ({len(admins)}):")
        print("-" * 50)
        for admin in admins:
            status = "ACTIVE" if admin.is_active else "INACTIVE"
            if admin.locked_until and admin.locked_until > admin.created_at:
                status = "LOCKED"

            print(f"ID: {admin.admin_id}")
            print(f"Email: {admin.email}")
            print(f"Name: {admin.full_name}")
            print(f"Status: {status}")
            print(f"Created: {admin.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
            if admin.last_login:
                print(f"Last Login: {admin.last_login.strftime('%Y-%m-%d %H:%M:%S')}")
            print("-" * 50)

    except Exception as e:
        print(f"Error listing admins: {str(e)}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "list":
        list_admins()
    else:
        create_admin_user()