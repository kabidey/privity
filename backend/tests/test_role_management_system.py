"""
Role Management System Tests
Tests for creating roles, assigning to users, and verifying permission changes
"""

import pytest
import requests
import os
import uuid
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
PE_DESK_EMAIL = "pe@smifs.com"
PE_DESK_PASSWORD = "Kutta@123"

# Global token cache to avoid rate limiting
_token_cache = {}


class TestRoleManagementSystem:
    """Comprehensive tests for Role Management functionality"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        self.pe_token = None
        self.test_user_id = None
        self.test_role_id = None
        self.test_user_email = f"test_role_user_{uuid.uuid4().hex[:8]}@smifs.com"
        self.test_user_password = "TestPass123!"
        
    def get_pe_token(self):
        """Get PE Desk authentication token"""
        if self.pe_token:
            return self.pe_token
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": PE_DESK_EMAIL,
            "password": PE_DESK_PASSWORD
        })
        assert response.status_code == 200, f"PE Desk login failed: {response.text}"
        self.pe_token = response.json()["token"]
        return self.pe_token
    
    def auth_headers(self, token=None):
        """Get authorization headers"""
        return {"Authorization": f"Bearer {token or self.get_pe_token()}"}
    
    # ==================== ROLE CRUD TESTS ====================
    
    def test_01_get_all_roles(self):
        """Test fetching all roles (system + custom)"""
        response = self.session.get(
            f"{BASE_URL}/api/roles",
            headers=self.auth_headers()
        )
        assert response.status_code == 200, f"Failed to get roles: {response.text}"
        roles = response.json()
        
        # Verify system roles exist (1-7)
        role_ids = [r["id"] for r in roles]
        for i in range(1, 8):
            assert i in role_ids, f"System role {i} not found"
        
        # Verify PE Desk has all permissions
        pe_desk = next((r for r in roles if r["id"] == 1), None)
        assert pe_desk is not None, "PE Desk role not found"
        assert "*" in pe_desk.get("permissions", []), "PE Desk should have wildcard permission"
        print(f"✓ Found {len(roles)} roles including all system roles")
    
    def test_02_get_all_permissions(self):
        """Test fetching all available permissions"""
        response = self.session.get(
            f"{BASE_URL}/api/roles/permissions",
            headers=self.auth_headers()
        )
        assert response.status_code == 200, f"Failed to get permissions: {response.text}"
        permissions = response.json()
        
        # Verify key permission categories exist
        expected_categories = ["dashboard", "bookings", "clients", "users", "roles"]
        for cat in expected_categories:
            assert cat in permissions, f"Permission category '{cat}' not found"
        
        print(f"✓ Found {len(permissions)} permission categories")
    
    def test_03_create_custom_role(self):
        """Test creating a new custom role with specific permissions"""
        role_name = f"TEST_CustomRole_{uuid.uuid4().hex[:6]}"
        role_data = {
            "name": role_name,
            "description": "Test custom role with limited permissions",
            "permissions": ["dashboard.view", "bookings.view"],
            "color": "bg-blue-100 text-blue-800"
        }
        
        response = self.session.post(
            f"{BASE_URL}/api/roles",
            headers=self.auth_headers(),
            json=role_data
        )
        assert response.status_code == 200, f"Failed to create role: {response.text}"
        
        created_role = response.json()
        assert created_role["name"] == role_name
        assert created_role["id"] >= 8, "Custom role ID should be >= 8"
        assert created_role["is_system"] == False, "Custom role should not be system role"
        assert "dashboard.view" in created_role["permissions"]
        assert "bookings.view" in created_role["permissions"]
        
        self.__class__.test_role_id = created_role["id"]
        print(f"✓ Created custom role '{role_name}' with ID {created_role['id']}")
        return created_role["id"]
    
    def test_04_get_specific_role(self):
        """Test fetching a specific role by ID"""
        # First create a role if not exists
        if not hasattr(self.__class__, 'test_role_id') or not self.__class__.test_role_id:
            self.test_03_create_custom_role()
        
        role_id = self.__class__.test_role_id
        response = self.session.get(
            f"{BASE_URL}/api/roles/{role_id}",
            headers=self.auth_headers()
        )
        assert response.status_code == 200, f"Failed to get role: {response.text}"
        
        role = response.json()
        assert role["id"] == role_id
        print(f"✓ Retrieved role ID {role_id}: {role['name']}")
    
    def test_05_update_role_permissions(self):
        """Test updating a role's permissions"""
        if not hasattr(self.__class__, 'test_role_id') or not self.__class__.test_role_id:
            self.test_03_create_custom_role()
        
        role_id = self.__class__.test_role_id
        
        # Add clients.view permission
        update_data = {
            "permissions": ["dashboard.view", "bookings.view", "clients.view"]
        }
        
        response = self.session.put(
            f"{BASE_URL}/api/roles/{role_id}",
            headers=self.auth_headers(),
            json=update_data
        )
        assert response.status_code == 200, f"Failed to update role: {response.text}"
        
        updated_role = response.json()
        assert "clients.view" in updated_role["permissions"], "clients.view should be added"
        print(f"✓ Updated role {role_id} with new permissions")
    
    def test_06_cannot_delete_system_roles(self):
        """Test that system roles (1-7) cannot be deleted"""
        for role_id in [1, 2, 3, 4, 5, 6, 7]:
            response = self.session.delete(
                f"{BASE_URL}/api/roles/{role_id}",
                headers=self.auth_headers()
            )
            assert response.status_code == 400, f"System role {role_id} should not be deletable"
            assert "system" in response.json().get("detail", "").lower()
        
        print("✓ Verified all system roles (1-7) cannot be deleted")
    
    def test_07_can_delete_custom_role(self):
        """Test that custom roles can be deleted"""
        # Create a new role specifically for deletion test
        role_name = f"TEST_DeleteMe_{uuid.uuid4().hex[:6]}"
        create_response = self.session.post(
            f"{BASE_URL}/api/roles",
            headers=self.auth_headers(),
            json={
                "name": role_name,
                "description": "Role to be deleted",
                "permissions": ["dashboard.view"],
                "color": "bg-red-100 text-red-800"
            }
        )
        assert create_response.status_code == 200
        role_id = create_response.json()["id"]
        
        # Delete the role
        delete_response = self.session.delete(
            f"{BASE_URL}/api/roles/{role_id}",
            headers=self.auth_headers()
        )
        assert delete_response.status_code == 200, f"Failed to delete custom role: {delete_response.text}"
        
        # Verify role is deleted
        get_response = self.session.get(
            f"{BASE_URL}/api/roles/{role_id}",
            headers=self.auth_headers()
        )
        assert get_response.status_code == 404, "Deleted role should not be found"
        
        print(f"✓ Successfully deleted custom role {role_id}")
    
    # ==================== USER ROLE ASSIGNMENT TESTS ====================
    
    def test_08_create_test_user(self):
        """Create a test user for role assignment tests"""
        user_data = {
            "email": self.test_user_email,
            "password": self.test_user_password,
            "name": "TEST Role Assignment User",
            "role": 7  # Start as Employee
        }
        
        response = self.session.post(
            f"{BASE_URL}/api/users",
            headers=self.auth_headers(),
            json=user_data
        )
        assert response.status_code == 200, f"Failed to create test user: {response.text}"
        
        user = response.json()["user"]
        self.__class__.test_user_id = user["id"]
        self.__class__.test_user_email = self.test_user_email
        self.__class__.test_user_password = self.test_user_password
        print(f"✓ Created test user: {user['email']} with ID {user['id']}")
        return user["id"]
    
    def test_09_assign_custom_role_to_user(self):
        """Test assigning a custom role to a user"""
        if not hasattr(self.__class__, 'test_user_id') or not self.__class__.test_user_id:
            self.test_08_create_test_user()
        if not hasattr(self.__class__, 'test_role_id') or not self.__class__.test_role_id:
            self.test_03_create_custom_role()
        
        user_id = self.__class__.test_user_id
        role_id = self.__class__.test_role_id
        
        response = self.session.put(
            f"{BASE_URL}/api/users/{user_id}/role?role={role_id}",
            headers=self.auth_headers()
        )
        assert response.status_code == 200, f"Failed to assign role: {response.text}"
        print(f"✓ Assigned custom role {role_id} to user {user_id}")
    
    def test_10_verify_user_permissions_after_role_assignment(self):
        """Verify user has correct permissions after role assignment"""
        if not hasattr(self.__class__, 'test_user_id') or not self.__class__.test_user_id:
            self.test_08_create_test_user()
            self.test_09_assign_custom_role_to_user()
        
        user_id = self.__class__.test_user_id
        
        response = self.session.get(
            f"{BASE_URL}/api/roles/user/{user_id}/permissions",
            headers=self.auth_headers()
        )
        assert response.status_code == 200, f"Failed to get user permissions: {response.text}"
        
        data = response.json()
        permissions = data.get("permissions", [])
        
        # Should have the permissions from the custom role
        assert "dashboard.view" in permissions, "User should have dashboard.view"
        assert "bookings.view" in permissions, "User should have bookings.view"
        
        print(f"✓ User has {len(permissions)} permissions: {permissions}")
    
    def test_11_login_as_test_user_and_verify_permissions(self):
        """Login as test user and verify permissions in token response"""
        if not hasattr(self.__class__, 'test_user_email'):
            self.test_08_create_test_user()
            self.test_09_assign_custom_role_to_user()
        
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": self.__class__.test_user_email,
            "password": self.__class__.test_user_password
        })
        assert response.status_code == 200, f"Test user login failed: {response.text}"
        
        data = response.json()
        user = data["user"]
        permissions = user.get("permissions", [])
        
        # Verify permissions are returned in login response
        assert "dashboard.view" in permissions, "Login should return dashboard.view permission"
        assert "bookings.view" in permissions, "Login should return bookings.view permission"
        
        self.__class__.test_user_token = data["token"]
        print(f"✓ Test user logged in with permissions: {permissions}")
    
    def test_12_auth_me_returns_fresh_permissions(self):
        """Test that /api/auth/me returns fresh permissions"""
        if not hasattr(self.__class__, 'test_user_token'):
            self.test_11_login_as_test_user_and_verify_permissions()
        
        response = self.session.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {self.__class__.test_user_token}"}
        )
        assert response.status_code == 200, f"Failed to get /auth/me: {response.text}"
        
        user = response.json()
        permissions = user.get("permissions", [])
        
        assert "dashboard.view" in permissions
        print(f"✓ /auth/me returns fresh permissions: {permissions}")
    
    # ==================== DYNAMIC PERMISSION UPDATE TESTS ====================
    
    def test_13_add_permission_to_role_and_verify_user_access(self):
        """Test that adding permission to role grants user access without re-login"""
        if not hasattr(self.__class__, 'test_role_id') or not self.__class__.test_role_id:
            self.test_03_create_custom_role()
        if not hasattr(self.__class__, 'test_user_token'):
            self.test_11_login_as_test_user_and_verify_permissions()
        
        role_id = self.__class__.test_role_id
        
        # Add stocks.view permission to the role
        update_data = {
            "permissions": ["dashboard.view", "bookings.view", "clients.view", "stocks.view"]
        }
        
        response = self.session.put(
            f"{BASE_URL}/api/roles/{role_id}",
            headers=self.auth_headers(),
            json=update_data
        )
        assert response.status_code == 200, f"Failed to update role: {response.text}"
        
        # Now check user's permissions via /auth/me (simulating frontend refresh)
        me_response = self.session.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {self.__class__.test_user_token}"}
        )
        assert me_response.status_code == 200
        
        user = me_response.json()
        permissions = user.get("permissions", [])
        
        # User should now have stocks.view without re-login
        assert "stocks.view" in permissions, "User should have stocks.view after role update"
        print(f"✓ User gained stocks.view permission dynamically: {permissions}")
    
    def test_14_remove_permission_from_role_and_verify_user_access(self):
        """Test that removing permission from role revokes user access without re-login"""
        if not hasattr(self.__class__, 'test_role_id') or not self.__class__.test_role_id:
            self.test_03_create_custom_role()
        if not hasattr(self.__class__, 'test_user_token'):
            self.test_11_login_as_test_user_and_verify_permissions()
        
        role_id = self.__class__.test_role_id
        
        # Remove bookings.view permission from the role
        update_data = {
            "permissions": ["dashboard.view", "clients.view", "stocks.view"]  # bookings.view removed
        }
        
        response = self.session.put(
            f"{BASE_URL}/api/roles/{role_id}",
            headers=self.auth_headers(),
            json=update_data
        )
        assert response.status_code == 200, f"Failed to update role: {response.text}"
        
        # Check user's permissions via /auth/me
        me_response = self.session.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {self.__class__.test_user_token}"}
        )
        assert me_response.status_code == 200
        
        user = me_response.json()
        permissions = user.get("permissions", [])
        
        # User should NOT have bookings.view anymore
        assert "bookings.view" not in permissions, "User should NOT have bookings.view after removal"
        assert "dashboard.view" in permissions, "User should still have dashboard.view"
        print(f"✓ User lost bookings.view permission dynamically: {permissions}")
    
    # ==================== SYSTEM ROLE TESTS ====================
    
    def test_15_assign_system_roles_to_user(self):
        """Test assigning different system roles to users"""
        if not hasattr(self.__class__, 'test_user_id') or not self.__class__.test_user_id:
            self.test_08_create_test_user()
        
        user_id = self.__class__.test_user_id
        
        # Test assigning Finance role (3)
        response = self.session.put(
            f"{BASE_URL}/api/users/{user_id}/role?role=3",
            headers=self.auth_headers()
        )
        assert response.status_code == 200, f"Failed to assign Finance role: {response.text}"
        
        # Verify permissions
        me_response = self.session.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {self.__class__.test_user_token}"}
        )
        assert me_response.status_code == 200
        
        user = me_response.json()
        assert user["role"] == 3, "User should have Finance role"
        permissions = user.get("permissions", [])
        
        # Finance role should have finance permissions
        assert "finance.view" in permissions or "finance.*" in permissions or any("finance" in p for p in permissions)
        print(f"✓ Assigned Finance role to user, permissions: {permissions[:5]}...")
    
    def test_16_check_permission_endpoint(self):
        """Test the check-permission endpoint"""
        response = self.session.post(
            f"{BASE_URL}/api/roles/check-permission?permission=dashboard.view",
            headers=self.auth_headers()
        )
        assert response.status_code == 200, f"Failed to check permission: {response.text}"
        
        data = response.json()
        assert data.get("has_permission") == True, "PE Desk should have dashboard.view"
        print("✓ Permission check endpoint working correctly")
    
    # ==================== CLEANUP ====================
    
    def test_99_cleanup(self):
        """Cleanup test data"""
        # Delete test user
        if hasattr(self.__class__, 'test_user_id') and self.__class__.test_user_id:
            response = self.session.delete(
                f"{BASE_URL}/api/users/{self.__class__.test_user_id}",
                headers=self.auth_headers()
            )
            if response.status_code == 200:
                print(f"✓ Deleted test user {self.__class__.test_user_id}")
        
        # Delete test role (if not already deleted)
        if hasattr(self.__class__, 'test_role_id') and self.__class__.test_role_id:
            response = self.session.delete(
                f"{BASE_URL}/api/roles/{self.__class__.test_role_id}",
                headers=self.auth_headers()
            )
            if response.status_code == 200:
                print(f"✓ Deleted test role {self.__class__.test_role_id}")
            elif response.status_code == 400 and "user" in response.text.lower():
                print(f"⚠ Could not delete role {self.__class__.test_role_id} - users still assigned")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
