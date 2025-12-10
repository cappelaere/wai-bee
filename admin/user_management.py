#!/usr/bin/env python3
"""User management utility for multi-tenancy system.

This utility provides command-line tools for managing users and their
scholarship assignments in the multi-tenancy system.

Author: Pat G Cappelaere, IBM Federal Consulting
Created: 2025-12-09
Version: 1.0.0
License: MIT

Usage:
    python admin/user_management.py list-users
    python admin/user_management.py show-user <username>
    python admin/user_management.py test-access <username> <scholarship>
    python admin/user_management.py validate-config
"""

import sys
import json
import argparse
from pathlib import Path
from typing import Dict, List

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from bee_agents.auth import (
    load_user_config,
    get_user_info,
    get_user_scholarships,
    get_user_role,
    get_user_permissions,
    has_scholarship_access,
    is_user_enabled,
    verify_credentials
)
from bee_agents.middleware import ScholarshipAccessMiddleware, log_access_attempt


def list_users():
    """List all users and their basic information."""
    try:
        config = load_user_config()
        users = config["users"]
        
        print("📋 User List")
        print("=" * 60)
        
        for username, user_data in users.items():
            enabled = "✅" if user_data.get("enabled", True) else "❌"
            role = user_data.get("role", "unknown")
            scholarships = user_data.get("scholarships", [])
            
            print(f"{enabled} {username:<20} {role:<10} {scholarships}")
        
        print(f"\nTotal users: {len(users)}")
        
    except Exception as e:
        print(f"❌ Error listing users: {e}")
        return False
    
    return True


def show_user(username: str):
    """Show detailed information for a specific user."""
    try:
        user_info = get_user_info(username)
        
        if not user_info:
            print(f"❌ User '{username}' not found")
            return False
        
        print(f"👤 User Details: {username}")
        print("=" * 50)
        
        print(f"Full Name:     {user_info.get('full_name', 'N/A')}")
        print(f"Email:         {user_info.get('email', 'N/A')}")
        print(f"Role:          {user_info.get('role', 'N/A')}")
        print(f"Enabled:       {'Yes' if user_info.get('enabled', True) else 'No'}")
        print(f"Password Env:  {user_info.get('password_env', 'N/A')}")
        
        scholarships = user_info.get('scholarships', [])
        if "*" in scholarships:
            print(f"Scholarships:  All (Admin Access)")
        else:
            print(f"Scholarships:  {', '.join(scholarships) if scholarships else 'None'}")
        
        permissions = user_info.get('permissions', [])
        print(f"Permissions:   {', '.join(permissions) if permissions else 'None'}")
        
        # Show accessible scholarship details
        config = load_user_config()
        print(f"\n📚 Accessible Scholarship Details:")
        
        if "*" in scholarships:
            # Admin sees all scholarships
            for scholarship_id, scholarship_data in config["scholarships"].items():
                if scholarship_data.get("enabled", True):
                    print(f"  • {scholarship_data['name']} ({scholarship_id})")
                    print(f"    Data Folder: {scholarship_data['data_folder']}")
        else:
            # Regular user sees only assigned scholarships
            for scholarship_id in scholarships:
                if scholarship_id in config["scholarships"]:
                    scholarship_data = config["scholarships"][scholarship_id]
                    if scholarship_data.get("enabled", True):
                        print(f"  • {scholarship_data['name']} ({scholarship_id})")
                        print(f"    Data Folder: {scholarship_data['data_folder']}")
        
    except Exception as e:
        print(f"❌ Error showing user details: {e}")
        return False
    
    return True


def test_access(username: str, scholarship: str):
    """Test if a user has access to a specific scholarship."""
    try:
        user_info = get_user_info(username)
        
        if not user_info:
            print(f"❌ User '{username}' not found")
            return False
        
        config = load_user_config()
        if scholarship not in config["scholarships"]:
            print(f"❌ Scholarship '{scholarship}' not found")
            return False
        
        has_access = has_scholarship_access(username, scholarship)
        
        print(f"🔐 Access Test: {username} → {scholarship}")
        print("=" * 50)
        
        print(f"User:          {username}")
        print(f"Role:          {get_user_role(username)}")
        print(f"Scholarships:  {get_user_scholarships(username)}")
        print(f"Permissions:   {get_user_permissions(username)}")
        print(f"Target:        {scholarship}")
        print(f"Access:        {'✅ GRANTED' if has_access else '❌ DENIED'}")
        
        if has_access:
            try:
                from bee_agents.auth import create_token_with_context
                token_data = create_token_with_context(username)
                middleware = ScholarshipAccessMiddleware(token_data)
                data_folder = middleware.get_data_folder(scholarship)
                print(f"Data Folder:   {data_folder}")
            except Exception as e:
                print(f"Data Folder:   Error - {e}")
        
    except Exception as e:
        print(f"❌ Error testing access: {e}")
        return False
    
    return True


def validate_config():
    """Validate the user configuration file."""
    try:
        print("🔍 Validating Configuration")
        print("=" * 50)
        
        # Load and validate config structure
        config = load_user_config()
        print("✅ Configuration file loaded successfully")
        
        # Check required sections
        required_sections = ["users", "scholarships"]
        for section in required_sections:
            if section not in config:
                print(f"❌ Missing required section: {section}")
                return False
            print(f"✅ Section '{section}' found")
        
        # Validate users
        users = config["users"]
        print(f"\n👥 Validating {len(users)} users:")
        
        for username, user_data in users.items():
            print(f"  Checking {username}...")
            
            # Check required fields
            required_fields = ["role", "scholarships", "permissions"]
            for field in required_fields:
                if field not in user_data:
                    print(f"    ❌ Missing field: {field}")
                    return False
            
            # Check password environment variable
            if "password_env" in user_data:
                import os
                password_env = user_data["password_env"]
                if not os.environ.get(password_env):
                    print(f"    ⚠️  Password environment variable not set: {password_env}")
                else:
                    print(f"    ✅ Password environment variable found: {password_env}")
            
            # Check scholarship references
            user_scholarships = user_data["scholarships"]
            if "*" not in user_scholarships:
                for scholarship in user_scholarships:
                    if scholarship not in config["scholarships"]:
                        print(f"    ❌ Invalid scholarship reference: {scholarship}")
                        return False
            
            print(f"    ✅ User {username} is valid")
        
        # Validate scholarships
        scholarships = config["scholarships"]
        print(f"\n📚 Validating {len(scholarships)} scholarships:")
        
        for scholarship_id, scholarship_data in scholarships.items():
            print(f"  Checking {scholarship_id}...")
            
            # Check required fields
            required_fields = ["name", "data_folder"]
            for field in required_fields:
                if field not in scholarship_data:
                    print(f"    ❌ Missing field: {field}")
                    return False
            
            # Check data folder exists
            data_folder = Path(scholarship_data["data_folder"])
            if not data_folder.exists():
                print(f"    ⚠️  Data folder does not exist: {data_folder}")
            else:
                print(f"    ✅ Data folder exists: {data_folder}")
            
            print(f"    ✅ Scholarship {scholarship_id} is valid")
        
        print(f"\n🎉 Configuration validation completed successfully!")
        print(f"   Users: {len(users)}")
        print(f"   Scholarships: {len(scholarships)}")
        
    except Exception as e:
        print(f"❌ Configuration validation failed: {e}")
        return False
    
    return True


def list_scholarships():
    """List all scholarships and their details."""
    try:
        config = load_user_config()
        scholarships = config["scholarships"]
        
        print("📚 Scholarship List")
        print("=" * 80)
        
        for scholarship_id, scholarship_data in scholarships.items():
            enabled = "✅" if scholarship_data.get("enabled", True) else "❌"
            name = scholarship_data.get("name", "N/A")
            data_folder = scholarship_data.get("data_folder", "N/A")
            
            print(f"{enabled} {scholarship_id:<15} {name:<30} {data_folder}")
        
        print(f"\nTotal scholarships: {len(scholarships)}")
        
    except Exception as e:
        print(f"❌ Error listing scholarships: {e}")
        return False
    
    return True


def show_access_matrix():
    """Show access matrix for all users and scholarships."""
    try:
        config = load_user_config()
        users = config["users"]
        scholarships = config["scholarships"]
        
        print("🔐 Access Matrix")
        print("=" * 80)
        
        # Header
        scholarship_ids = list(scholarships.keys())
        header = "User" + "".join(f"{s[:10]:>12}" for s in scholarship_ids)
        print(header)
        print("-" * len(header))
        
        # User rows
        for username in users.keys():
            row = f"{username:<12}"
            for scholarship_id in scholarship_ids:
                has_access = has_scholarship_access(username, scholarship_id)
                symbol = "✅" if has_access else "❌"
                row += f"{symbol:>12}"
            print(row)
        
        print(f"\nLegend: ✅ = Access Granted, ❌ = Access Denied")
        
    except Exception as e:
        print(f"❌ Error showing access matrix: {e}")
        return False
    
    return True


def main():
    """Main entry point for the user management utility."""
    parser = argparse.ArgumentParser(
        description="User Management Utility for Multi-Tenancy System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python admin/user_management.py list-users
  python admin/user_management.py show-user admin
  python admin/user_management.py test-access delaney_manager Delaney_Wings
  python admin/user_management.py validate-config
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # List users command
    subparsers.add_parser("list-users", help="List all users")
    
    # Show user command
    show_parser = subparsers.add_parser("show-user", help="Show detailed user information")
    show_parser.add_argument("username", help="Username to show details for")
    
    # Test access command
    test_parser = subparsers.add_parser("test-access", help="Test user access to scholarship")
    test_parser.add_argument("username", help="Username to test")
    test_parser.add_argument("scholarship", help="Scholarship to test access for")
    
    # Validate config command
    subparsers.add_parser("validate-config", help="Validate configuration file")
    
    # List scholarships command
    subparsers.add_parser("list-scholarships", help="List all scholarships")
    
    # Show access matrix command
    subparsers.add_parser("access-matrix", help="Show access matrix for all users and scholarships")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    try:
        if args.command == "list-users":
            success = list_users()
        elif args.command == "show-user":
            success = show_user(args.username)
        elif args.command == "test-access":
            success = test_access(args.username, args.scholarship)
        elif args.command == "validate-config":
            success = validate_config()
        elif args.command == "list-scholarships":
            success = list_scholarships()
        elif args.command == "access-matrix":
            success = show_access_matrix()
        else:
            print(f"❌ Unknown command: {args.command}")
            return 1
        
        return 0 if success else 1
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Operation cancelled by user")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    exit(main())

# Made with Bob