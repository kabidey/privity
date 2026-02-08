"""
License Admin Login Tests
Tests for the hidden license admin user (deynet@gmail.com)
- Login returns is_license_admin: true
- Login returns mobile_required: false
- License admin should not need mobile number update
- Normal users without mobile should still be prompted
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
LICENSE_ADMIN = {
    "email": "deynet@gmail.com",
    "password": "Kutta@123"
}

PE_USER = {
    "email": "pe@smifs.com",
    "password": "Kutta@123"
}


class TestLicenseAdminLogin:
    """Test login functionality for license admin"""
    
    def test_license_admin_login_returns_is_license_admin_true(self):
        """License admin login should return is_license_admin: true"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json=LICENSE_ADMIN
        )
        
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        
        # Verify is_license_admin flag
        assert "user" in data, "Response should contain user object"
        user = data["user"]
        assert user.get("is_license_admin") == True, f"Expected is_license_admin=True, got {user.get('is_license_admin')}"
        print(f"PASS: License admin login returns is_license_admin=True")
    
    def test_license_admin_login_returns_mobile_required_false(self):
        """License admin login should return mobile_required: false"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json=LICENSE_ADMIN
        )
        
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        
        # Verify mobile_required is false
        assert data.get("mobile_required") == False, f"Expected mobile_required=False, got {data.get('mobile_required')}"
        print(f"PASS: License admin login returns mobile_required=False")
    
    def test_license_admin_role_is_zero(self):
        """License admin should have role=0"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json=LICENSE_ADMIN
        )
        
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        user = data["user"]
        
        assert user.get("role") == 0, f"Expected role=0, got {user.get('role')}"
        print(f"PASS: License admin has role=0")
    
    def test_license_admin_returns_valid_token(self):
        """License admin login should return a valid token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json=LICENSE_ADMIN
        )
        
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        
        assert "token" in data, "Response should contain token"
        assert len(data["token"]) > 0, "Token should not be empty"
        print(f"PASS: License admin login returns valid token")


class TestPEUserLogin:
    """Test that normal PE user login works correctly"""
    
    def test_pe_user_login_returns_no_license_admin_flag(self):
        """PE user should not have is_license_admin=True"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json=PE_USER
        )
        
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        user = data["user"]
        
        # is_license_admin should be None or False for normal users
        assert user.get("is_license_admin") != True, f"PE user should not have is_license_admin=True"
        print(f"PASS: PE user does not have is_license_admin flag")
    
    def test_pe_user_login_role_is_one(self):
        """PE user should have role=1"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json=PE_USER
        )
        
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        user = data["user"]
        
        assert user.get("role") == 1, f"Expected role=1 for PE user, got {user.get('role')}"
        print(f"PASS: PE user has role=1")
    
    def test_pe_user_login_mobile_required_false(self):
        """PE user (superadmin) should not require mobile update"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json=PE_USER
        )
        
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        
        # PE Desk (role=1) should not require mobile
        assert data.get("mobile_required") == False, f"Expected mobile_required=False for PE user, got {data.get('mobile_required')}"
        print(f"PASS: PE user does not require mobile update")


class TestLicenseAdminAuthentication:
    """Test authenticated routes for license admin"""
    
    @pytest.fixture
    def license_admin_token(self):
        """Get token for license admin"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json=LICENSE_ADMIN
        )
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Failed to login as license admin")
    
    def test_license_admin_can_access_me_endpoint(self, license_admin_token):
        """License admin should be able to access /auth/me"""
        response = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {license_admin_token}"}
        )
        
        assert response.status_code == 200, f"Failed to access /me: {response.text}"
        data = response.json()
        assert data["email"] == LICENSE_ADMIN["email"], "Email mismatch"
        print(f"PASS: License admin can access /auth/me")
    
    def test_license_admin_can_access_license_endpoint(self, license_admin_token):
        """License admin should be able to access license management endpoints"""
        response = requests.get(
            f"{BASE_URL}/api/license/status",
            headers={"Authorization": f"Bearer {license_admin_token}"}
        )
        
        # Should get 200 or some valid response (not 403 or 401)
        assert response.status_code in [200, 404], f"License endpoint access failed: {response.status_code} - {response.text}"
        print(f"PASS: License admin can access license endpoints")


class TestLoginResponseStructure:
    """Test the structure of login responses"""
    
    def test_license_admin_response_structure(self):
        """Verify complete response structure for license admin"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json=LICENSE_ADMIN
        )
        
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        
        # Check top-level fields
        assert "token" in data, "Missing token field"
        assert "user" in data, "Missing user field"
        assert "mobile_required" in data, "Missing mobile_required field"
        
        # Check user fields
        user = data["user"]
        required_fields = ["id", "email", "name", "role"]
        for field in required_fields:
            assert field in user, f"Missing user.{field} field"
        
        # Specific license admin checks
        assert user.get("is_license_admin") == True, "is_license_admin should be True"
        assert data.get("mobile_required") == False, "mobile_required should be False"
        
        print(f"PASS: License admin response has correct structure")
        print(f"  - token: present")
        print(f"  - user.id: {user.get('id')[:8]}...")
        print(f"  - user.email: {user.get('email')}")
        print(f"  - user.role: {user.get('role')}")
        print(f"  - user.is_license_admin: {user.get('is_license_admin')}")
        print(f"  - mobile_required: {data.get('mobile_required')}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
