"""Tests for multi-tenancy implementation.

This module tests the multi-tenancy features including authentication,
access control, and data isolation.

Author: Pat G Cappelaere, IBM Federal Consulting
Created: 2025-12-09
Version: 1.0.0
License: MIT
"""

import pytest
import json
from pathlib import Path
import sys
import os

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
    verify_credentials,
    create_token_with_context,
    verify_token_with_context
)
from bee_agents.middleware import ScholarshipAccessMiddleware


class TestUserConfiguration:
    """Test user configuration loading and validation."""
    
    def test_load_user_config(self):
        """Test loading user configuration from JSON file."""
        config = load_user_config()
        
        assert "users" in config
        assert "scholarships" in config
        assert "pat" in config["users"]  # Admin user is 'pat'
        assert "delaney_manager" in config["users"]
        assert "evans_manager" in config["users"]
        assert "Delaney_Wings" in config["scholarships"]
        assert "Evans_Wings" in config["scholarships"]
    
    def test_get_user_info(self):
        """Test retrieving user information."""
        # Test existing user (pat is the admin)
        admin_info = get_user_info("pat")
        assert admin_info is not None
        assert admin_info["role"] == "admin"
        assert "*" in admin_info["scholarships"]
        
        # Test non-existing user
        invalid_info = get_user_info("nonexistent")
        assert invalid_info is None
    
    def test_get_user_scholarships(self):
        """Test retrieving user scholarship assignments."""
        # Test admin (pat should have all access)
        admin_scholarships = get_user_scholarships("pat")
        assert "*" in admin_scholarships
        
        # Test delaney manager (should have only Delaney_Wings)
        delaney_scholarships = get_user_scholarships("delaney_manager")
        assert delaney_scholarships == ["Delaney_Wings"]
        
        # Test evans manager (should have only Evans_Wings)
        evans_scholarships = get_user_scholarships("evans_manager")
        assert evans_scholarships == ["Evans_Wings"]
    
    def test_get_user_role(self):
        """Test retrieving user roles."""
        assert get_user_role("pat") == "admin"
        assert get_user_role("delaney_manager") == "manager"
        assert get_user_role("evans_manager") == "manager"
        assert get_user_role("user") == "reviewer"
    
    def test_get_user_permissions(self):
        """Test retrieving user permissions."""
        admin_perms = get_user_permissions("pat")
        assert "read" in admin_perms
        assert "write" in admin_perms
        assert "admin" in admin_perms
        
        manager_perms = get_user_permissions("delaney_manager")
        assert "read" in manager_perms
        assert "write" in manager_perms
        assert "admin" not in manager_perms
        
        reviewer_perms = get_user_permissions("user")
        assert "read" in reviewer_perms
        assert "write" not in reviewer_perms
        assert "admin" not in reviewer_perms


class TestAuthentication:
    """Test authentication functions."""
    
    def test_verify_credentials(self):
        """Test credential verification."""
        # Note: Actual passwords come from environment variables
        # These tests will pass if environment variables are set correctly
        # Test valid credentials (using pat as admin)
        assert verify_credentials("pat", os.getenv("ADMIN_PASSWORD", "test")) == True
        assert verify_credentials("delaney_manager", os.getenv("DELANEY_PASSWORD", "test")) == True
        assert verify_credentials("evans_manager", os.getenv("EVANS_PASSWORD", "test")) == True
        
        # Test invalid credentials
        assert verify_credentials("pat", "wrong_password") == False
        assert verify_credentials("nonexistent", "password") == False
    
    def test_has_scholarship_access(self):
        """Test scholarship access checking."""
        # Admin (pat) should have access to all scholarships
        assert has_scholarship_access("pat", "Delaney_Wings") == True
        assert has_scholarship_access("pat", "Evans_Wings") == True
        
        # Delaney manager should only have access to Delaney_Wings
        assert has_scholarship_access("delaney_manager", "Delaney_Wings") == True
        assert has_scholarship_access("delaney_manager", "Evans_Wings") == False
        
        # Evans manager should only have access to Evans_Wings
        assert has_scholarship_access("evans_manager", "Evans_Wings") == True
        assert has_scholarship_access("evans_manager", "Delaney_Wings") == False
    
    def test_is_user_enabled(self):
        """Test user enabled status."""
        assert is_user_enabled("pat") == True
        assert is_user_enabled("delaney_manager") == True
        assert is_user_enabled("nonexistent") == False
    
    def test_token_creation_and_verification(self):
        """Test token creation and verification with context."""
        # Create token for delaney manager
        token_data = create_token_with_context("delaney_manager")
        
        assert "token" in token_data
        assert token_data["username"] == "delaney_manager"
        assert token_data["role"] == "manager"
        assert token_data["scholarships"] == ["Delaney_Wings"]
        assert "read" in token_data["permissions"]
        assert "write" in token_data["permissions"]
        
        # Verify token
        verified_data = verify_token_with_context(token_data["token"])
        assert verified_data is not None
        assert verified_data["username"] == "delaney_manager"
        assert verified_data["role"] == "manager"
        assert verified_data["scholarships"] == ["Delaney_Wings"]
        
        # Test invalid token
        invalid_data = verify_token_with_context("invalid_token")
        assert invalid_data is None


class TestMiddleware:
    """Test scholarship access middleware."""
    
    def setup_method(self):
        """Set up test data for each test method."""
        self.admin_token = create_token_with_context("pat")
        self.delaney_token = create_token_with_context("delaney_manager")
        self.evans_token = create_token_with_context("evans_manager")
        
        self.admin_middleware = ScholarshipAccessMiddleware(self.admin_token)
        self.delaney_middleware = ScholarshipAccessMiddleware(self.delaney_token)
        self.evans_middleware = ScholarshipAccessMiddleware(self.evans_token)
    
    def test_can_access_scholarship(self):
        """Test scholarship access checking in middleware."""
        # Admin should access all scholarships
        assert self.admin_middleware.can_access_scholarship("Delaney_Wings") == True
        assert self.admin_middleware.can_access_scholarship("Evans_Wings") == True
        
        # Delaney manager should only access Delaney_Wings
        assert self.delaney_middleware.can_access_scholarship("Delaney_Wings") == True
        assert self.delaney_middleware.can_access_scholarship("Evans_Wings") == False
        
        # Evans manager should only access Evans_Wings
        assert self.evans_middleware.can_access_scholarship("Evans_Wings") == True
        assert self.evans_middleware.can_access_scholarship("Delaney_Wings") == False
    
    def test_filter_scholarships(self):
        """Test scholarship list filtering."""
        all_scholarships = ["Delaney_Wings", "Evans_Wings"]
        
        # Admin should see all scholarships
        admin_filtered = self.admin_middleware.filter_scholarships(all_scholarships)
        assert set(admin_filtered) == set(all_scholarships)
        
        # Delaney manager should only see Delaney_Wings
        delaney_filtered = self.delaney_middleware.filter_scholarships(all_scholarships)
        assert delaney_filtered == ["Delaney_Wings"]
        
        # Evans manager should only see Evans_Wings
        evans_filtered = self.evans_middleware.filter_scholarships(all_scholarships)
        assert evans_filtered == ["Evans_Wings"]
    
    def test_get_accessible_scholarships(self):
        """Test getting accessible scholarships with details."""
        # Admin should see all scholarships
        admin_scholarships = self.admin_middleware.get_accessible_scholarships()
        scholarship_ids = [s["id"] for s in admin_scholarships]
        assert "Delaney_Wings" in scholarship_ids
        assert "Evans_Wings" in scholarship_ids
        
        # Delaney manager should only see Delaney_Wings
        delaney_scholarships = self.delaney_middleware.get_accessible_scholarships()
        assert len(delaney_scholarships) == 1
        assert delaney_scholarships[0]["id"] == "Delaney_Wings"
        assert delaney_scholarships[0]["name"] == "Delaney Wings Scholarship"
        
        # Evans manager should only see Evans_Wings
        evans_scholarships = self.evans_middleware.get_accessible_scholarships()
        assert len(evans_scholarships) == 1
        assert evans_scholarships[0]["id"] == "Evans_Wings"
        assert evans_scholarships[0]["name"] == "Evans Wings Scholarship"
    
    def test_has_permission(self):
        """Test permission checking."""
        # Admin should have all permissions
        assert self.admin_middleware.has_permission("read") == True
        assert self.admin_middleware.has_permission("write") == True
        assert self.admin_middleware.has_permission("admin") == True
        
        # Manager should have read and write, but not admin
        assert self.delaney_middleware.has_permission("read") == True
        assert self.delaney_middleware.has_permission("write") == True
        assert self.delaney_middleware.has_permission("admin") == False
    
    def test_get_data_folder(self):
        """Test getting data folder for scholarship."""
        # Test valid access
        delaney_folder = self.delaney_middleware.get_data_folder("Delaney_Wings")
        assert delaney_folder == "data/Delaney_Wings"
        
        # Test invalid access (should raise PermissionError)
        with pytest.raises(PermissionError):
            self.delaney_middleware.get_data_folder("Evans_Wings")


class TestDataIsolation:
    """Test data isolation between scholarships."""
    
    def test_cross_scholarship_access_denied(self):
        """Test that users cannot access other scholarships' data."""
        delaney_token = create_token_with_context("delaney_manager")
        delaney_middleware = ScholarshipAccessMiddleware(delaney_token)
        
        # Should be able to access own scholarship
        assert delaney_middleware.can_access_scholarship("Delaney_Wings") == True
        
        # Should NOT be able to access other scholarship
        assert delaney_middleware.can_access_scholarship("Evans_Wings") == False
        
        # Should raise PermissionError when trying to get data folder for other scholarship
        with pytest.raises(PermissionError):
            delaney_middleware.get_data_folder("Evans_Wings")
    
    def test_admin_universal_access(self):
        """Test that admin can access all scholarships."""
        admin_token = create_token_with_context("pat")  # pat is the admin user
        admin_middleware = ScholarshipAccessMiddleware(admin_token)
        
        # Admin should access all scholarships
        assert admin_middleware.can_access_scholarship("Delaney_Wings") == True
        assert admin_middleware.can_access_scholarship("Evans_Wings") == True
        
        # Admin should be able to get data folders for all scholarships
        delaney_folder = admin_middleware.get_data_folder("Delaney_Wings")
        evans_folder = admin_middleware.get_data_folder("Evans_Wings")
        
        assert delaney_folder == "data/Delaney_Wings"
        assert evans_folder == "data/Evans_Wings"


class TestBackwardCompatibility:
    """Test backward compatibility with existing authentication."""
    
    def test_legacy_user_support(self):
        """Test that legacy 'user' account still works."""
        # Legacy user should still authenticate
        assert verify_credentials("user", "wai2025") == True
        
        # Legacy user should have scholarship assignment
        user_scholarships = get_user_scholarships("user")
        assert "Delaney_Wings" in user_scholarships
        
        # Legacy user should have reviewer role
        assert get_user_role("user") == "reviewer"
        
        # Legacy user should have read-only permissions
        user_perms = get_user_permissions("user")
        assert "read" in user_perms
        assert "write" not in user_perms


def run_tests():
    """Run all tests and print results."""
    print("Running multi-tenancy tests...")
    
    # Test configuration loading
    print("\n1. Testing configuration loading...")
    try:
        config = load_user_config()
        print("✅ Configuration loaded successfully")
        print(f"   Users: {list(config['users'].keys())}")
        print(f"   Scholarships: {list(config['scholarships'].keys())}")
    except Exception as e:
        print(f"❌ Configuration loading failed: {e}")
        return False
    
    # Test authentication
    print("\n2. Testing authentication...")
    try:
        assert verify_credentials("admin", "1admin2")
        assert verify_credentials("delaney_manager", "delaney2025")
        assert not verify_credentials("admin", "wrong_password")
        print("✅ Authentication tests passed")
    except Exception as e:
        print(f"❌ Authentication tests failed: {e}")
        return False
    
    # Test access control
    print("\n3. Testing access control...")
    try:
        assert has_scholarship_access("admin", "Delaney_Wings")
        assert has_scholarship_access("admin", "Evans_Wings")
        assert has_scholarship_access("delaney_manager", "Delaney_Wings")
        assert not has_scholarship_access("delaney_manager", "Evans_Wings")
        print("✅ Access control tests passed")
    except Exception as e:
        print(f"❌ Access control tests failed: {e}")
        return False
    
    # Test middleware
    print("\n4. Testing middleware...")
    try:
        token_data = create_token_with_context("delaney_manager")
        middleware = ScholarshipAccessMiddleware(token_data)
        
        assert middleware.can_access_scholarship("Delaney_Wings")
        assert not middleware.can_access_scholarship("Evans_Wings")
        
        scholarships = middleware.get_accessible_scholarships()
        assert len(scholarships) == 1
        assert scholarships[0]["id"] == "Delaney_Wings"
        
        print("✅ Middleware tests passed")
    except Exception as e:
        print(f"❌ Middleware tests failed: {e}")
        return False
    
    # Test data isolation
    print("\n5. Testing data isolation...")
    try:
        delaney_token = create_token_with_context("delaney_manager")
        delaney_middleware = ScholarshipAccessMiddleware(delaney_token)
        
        # Should work
        delaney_folder = delaney_middleware.get_data_folder("Delaney_Wings")
        assert delaney_folder == "data/Delaney_Wings"
        
        # Should fail
        try:
            delaney_middleware.get_data_folder("Evans_Wings")
            print("❌ Data isolation failed - access should be denied")
            return False
        except PermissionError:
            pass  # Expected
        
        print("✅ Data isolation tests passed")
    except Exception as e:
        print(f"❌ Data isolation tests failed: {e}")
        return False
    
    print("\n🎉 All multi-tenancy tests passed!")
    return True


if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)

# Made with Bob