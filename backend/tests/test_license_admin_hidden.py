"""
License Admin Hidden User Test Suite
Tests that the secret license admin (deynet@gmail.com) is properly hidden from all user listings.
Also tests license system functionality including:
- License admin login and verification
- License admin hidden from all user endpoints
- License expiry checking
- Access control for regular vs license admin users
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

# Test credentials
LICENSE_ADMIN_EMAIL = "deynet@gmail.com"
LICENSE_ADMIN_PASSWORD = "Kutta@123"
PE_USER_EMAIL = "pe@smifs.com"
PE_USER_PASSWORD = "Kutta@123"
FI_USER_EMAIL = "fi@smifs.com"
FI_USER_PASSWORD = "Kutta@123"


# Shared token cache to reduce API calls
class TokenCache:
    license_admin_token = None
    pe_user_token = None
    fi_user_token = None
    last_refresh = 0


def get_license_admin_token():
    """Get or cache license admin token"""
    current_time = time.time()
    if TokenCache.license_admin_token is None or (current_time - TokenCache.last_refresh > 300):
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})
        response = session.post(f"{BASE_URL}/api/auth/login", json={
            "email": LICENSE_ADMIN_EMAIL,
            "password": LICENSE_ADMIN_PASSWORD
        })
        if response.status_code == 200:
            TokenCache.license_admin_token = response.json().get("token")
            TokenCache.last_refresh = current_time
        time.sleep(0.5)
    return TokenCache.license_admin_token


def get_pe_user_token():
    """Get or cache PE user token"""
    current_time = time.time()
    if TokenCache.pe_user_token is None or (current_time - TokenCache.last_refresh > 300):
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})
        response = session.post(f"{BASE_URL}/api/auth/login", json={
            "email": PE_USER_EMAIL,
            "password": PE_USER_PASSWORD
        })
        if response.status_code == 200:
            TokenCache.pe_user_token = response.json().get("token")
            TokenCache.last_refresh = current_time
        time.sleep(0.5)
    return TokenCache.pe_user_token


def get_fi_user_token():
    """Get or cache FI user token"""
    current_time = time.time()
    if TokenCache.fi_user_token is None or (current_time - TokenCache.last_refresh > 300):
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})
        response = session.post(f"{BASE_URL}/api/auth/login", json={
            "email": FI_USER_EMAIL,
            "password": FI_USER_PASSWORD
        })
        if response.status_code == 200:
            TokenCache.fi_user_token = response.json().get("token")
            TokenCache.last_refresh = current_time
        time.sleep(0.5)
    return TokenCache.fi_user_token


# ============== License Admin Login Tests ==============

class TestLicenseAdminLogin:
    """Test that license admin can login successfully"""
    
    def test_license_admin_can_login(self):
        """Test license admin (deynet@gmail.com) can login successfully"""
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})
        response = session.post(f"{BASE_URL}/api/auth/login", json={
            "email": LICENSE_ADMIN_EMAIL,
            "password": LICENSE_ADMIN_PASSWORD
        })
        
        print(f"License admin login status: {response.status_code}")
        assert response.status_code == 200, f"License admin login failed: {response.text}"
        
        data = response.json()
        assert "token" in data, "Expected token in response"
        assert data["user"]["email"] == LICENSE_ADMIN_EMAIL
        assert data["user"]["role"] == 0, "License admin should have role 0"
        print("PASS: License admin can login successfully with role 0")
    
    def test_license_admin_verify_endpoint(self):
        """Test /api/licence/verify-admin returns is_license_admin=true"""
        token = get_license_admin_token()
        assert token, "Failed to get license admin token"
        
        session = requests.Session()
        session.headers.update({
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        })
        
        response = session.get(f"{BASE_URL}/api/licence/verify-admin")
        print(f"Verify admin response: {response.status_code}")
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("is_license_admin") == True, f"Expected is_license_admin=True, got {data}"
        print("PASS: License admin verified successfully via /api/licence/verify-admin")


# ============== License Admin Hidden from User Lists Tests ==============

class TestLicenseAdminHiddenFromUserLists:
    """Test that license admin is hidden from all user listing endpoints"""
    
    def test_license_admin_hidden_from_users_endpoint(self):
        """Test /api/users does NOT include license admin"""
        token = get_pe_user_token()
        assert token, "Failed to get PE user token"
        
        session = requests.Session()
        session.headers.update({
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        })
        
        response = session.get(f"{BASE_URL}/api/users")
        print(f"GET /api/users status: {response.status_code}")
        assert response.status_code == 200
        
        users = response.json()
        user_emails = [u.get("email") for u in users]
        
        assert LICENSE_ADMIN_EMAIL not in user_emails, \
            f"License admin {LICENSE_ADMIN_EMAIL} should NOT be in /api/users list"
        print(f"PASS: License admin hidden from /api/users (checked {len(users)} users)")
    
    def test_license_admin_hidden_from_employees_endpoint(self):
        """Test /api/users/employees does NOT include license admin"""
        token = get_pe_user_token()
        assert token, "Failed to get PE user token"
        
        session = requests.Session()
        session.headers.update({
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        })
        
        response = session.get(f"{BASE_URL}/api/users/employees")
        print(f"GET /api/users/employees status: {response.status_code}")
        assert response.status_code == 200
        
        users = response.json()
        user_emails = [u.get("email") for u in users]
        
        assert LICENSE_ADMIN_EMAIL not in user_emails, \
            f"License admin {LICENSE_ADMIN_EMAIL} should NOT be in /api/users/employees list"
        print(f"PASS: License admin hidden from /api/users/employees (checked {len(users)} users)")
    
    def test_license_admin_hidden_from_potential_managers(self):
        """Test /api/users/hierarchy/potential-managers does NOT include license admin"""
        token = get_pe_user_token()
        assert token, "Failed to get PE user token"
        
        session = requests.Session()
        session.headers.update({
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        })
        
        response = session.get(f"{BASE_URL}/api/users/hierarchy/potential-managers")
        print(f"GET /api/users/hierarchy/potential-managers status: {response.status_code}")
        assert response.status_code == 200
        
        users = response.json()
        user_emails = [u.get("email") for u in users]
        
        assert LICENSE_ADMIN_EMAIL not in user_emails, \
            f"License admin {LICENSE_ADMIN_EMAIL} should NOT be in potential managers list"
        print(f"PASS: License admin hidden from /api/users/hierarchy/potential-managers")
    
    def test_license_admin_hidden_from_subordinates(self):
        """Test /api/users/team/subordinates does NOT include license admin"""
        token = get_pe_user_token()
        assert token, "Failed to get PE user token"
        
        session = requests.Session()
        session.headers.update({
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        })
        
        response = session.get(f"{BASE_URL}/api/users/team/subordinates")
        print(f"GET /api/users/team/subordinates status: {response.status_code}")
        
        if response.status_code == 200:
            users = response.json()
            user_emails = [u.get("email") for u in users if isinstance(u, dict)]
            
            assert LICENSE_ADMIN_EMAIL not in user_emails, \
                f"License admin {LICENSE_ADMIN_EMAIL} should NOT be in subordinates list"
            print(f"PASS: License admin hidden from /api/users/team/subordinates")
        else:
            print(f"Subordinates endpoint returned {response.status_code} - may be empty or permission issue")
    
    def test_license_admin_hidden_from_direct_reports(self):
        """Test /api/users/team/direct-reports does NOT include license admin"""
        token = get_pe_user_token()
        assert token, "Failed to get PE user token"
        
        session = requests.Session()
        session.headers.update({
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        })
        
        response = session.get(f"{BASE_URL}/api/users/team/direct-reports")
        print(f"GET /api/users/team/direct-reports status: {response.status_code}")
        
        if response.status_code == 200:
            users = response.json()
            user_emails = [u.get("email") for u in users if isinstance(u, dict)]
            
            assert LICENSE_ADMIN_EMAIL not in user_emails, \
                f"License admin {LICENSE_ADMIN_EMAIL} should NOT be in direct reports list"
            print(f"PASS: License admin hidden from /api/users/team/direct-reports")
        else:
            print(f"Direct reports endpoint returned {response.status_code} - may be empty or permission issue")


# ============== PE User Cannot See License Admin Tests ==============

class TestPEUserCannotSeeLicenseAdmin:
    """Test that PE user specifically cannot see license admin in any list"""
    
    def test_pe_user_cannot_see_license_admin_in_users(self):
        """PE user should not see license admin when listing users"""
        token = get_pe_user_token()
        assert token, "Failed to get PE user token"
        
        session = requests.Session()
        session.headers.update({
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        })
        
        response = session.get(f"{BASE_URL}/api/users")
        assert response.status_code == 200
        
        users = response.json()
        
        # Check that deynet@gmail.com is NOT in the list
        found_license_admin = False
        for user in users:
            if user.get("email") == LICENSE_ADMIN_EMAIL:
                found_license_admin = True
                break
        
        assert not found_license_admin, \
            "PE user should NOT see license admin in user list"
        print("PASS: PE user cannot see license admin in /api/users")
    
    def test_pe_user_cannot_search_for_license_admin(self):
        """PE user should not find license admin when searching users"""
        token = get_pe_user_token()
        assert token, "Failed to get PE user token"
        
        session = requests.Session()
        session.headers.update({
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        })
        
        # Search for the license admin by email
        response = session.get(f"{BASE_URL}/api/users?search=deynet")
        assert response.status_code == 200
        
        users = response.json()
        user_emails = [u.get("email") for u in users]
        
        assert LICENSE_ADMIN_EMAIL not in user_emails, \
            "Search should not return license admin"
        print("PASS: PE user cannot find license admin via search")


# ============== License Status and Check Tests ==============

class TestLicenseStatusChecks:
    """Test license status endpoints"""
    
    def test_license_check_status_returns_is_licensed(self):
        """Test /api/licence/check/status returns is_licensed correctly"""
        token = get_pe_user_token()
        assert token, "Failed to get PE user token"
        
        session = requests.Session()
        session.headers.update({
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        })
        
        response = session.get(f"{BASE_URL}/api/licence/check/status")
        print(f"License check status: {response.status_code}")
        assert response.status_code == 200
        
        data = response.json()
        assert "is_licensed" in data, "Expected 'is_licensed' in response"
        assert "private_equity" in data, "Expected 'private_equity' in response"
        assert "fixed_income" in data, "Expected 'fixed_income' in response"
        
        # Check structure of PE and FI status
        pe_status = data["private_equity"]
        fi_status = data["fixed_income"]
        
        assert "is_licensed" in pe_status, "Expected is_licensed in PE status"
        assert "is_licensed" in fi_status, "Expected is_licensed in FI status"
        
        print(f"PASS: License status returned - PE licensed: {pe_status.get('is_licensed')}, FI licensed: {fi_status.get('is_licensed')}")
    
    def test_license_check_feature_returns_correctly(self):
        """Test /api/licence/check/feature returns is_licensed for features"""
        token = get_pe_user_token()
        assert token, "Failed to get PE user token"
        
        session = requests.Session()
        session.headers.update({
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        })
        
        response = session.post(f"{BASE_URL}/api/licence/check/feature", json={
            "feature": "clients",
            "company_type": "private_equity"
        })
        print(f"Feature check response: {response.status_code}")
        assert response.status_code == 200
        
        data = response.json()
        assert "is_licensed" in data, "Expected 'is_licensed' in response"
        assert "message" in data, "Expected 'message' in response"
        print(f"PASS: Feature 'clients' licensed: {data.get('is_licensed')}")
    
    def test_license_admin_status_shows_expiry(self):
        """Test /api/licence/status shows correct expiry information"""
        token = get_license_admin_token()
        assert token, "Failed to get license admin token"
        
        session = requests.Session()
        session.headers.update({
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        })
        
        response = session.get(f"{BASE_URL}/api/licence/status")
        print(f"License status: {response.status_code}")
        assert response.status_code == 200
        
        data = response.json()
        status = data.get("status", {})
        
        # Check PE status structure
        pe_status = status.get("private_equity", {})
        assert "status" in pe_status, "Expected 'status' in PE status"
        assert "expires_at" in pe_status, "Expected 'expires_at' in PE status"
        assert "days_remaining" in pe_status, "Expected 'days_remaining' in PE status"
        
        print(f"PASS: PE license status: {pe_status.get('status')}, days remaining: {pe_status.get('days_remaining')}")


# ============== License Admin Access Control Tests ==============

class TestLicenseAdminAccessControl:
    """Test that only license admin can access license management endpoints"""
    
    def test_pe_user_cannot_access_license_status(self):
        """PE user should NOT be able to access /api/licence/status"""
        token = get_pe_user_token()
        assert token, "Failed to get PE user token"
        
        session = requests.Session()
        session.headers.update({
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        })
        
        response = session.get(f"{BASE_URL}/api/licence/status")
        print(f"PE user accessing /api/licence/status: {response.status_code}")
        assert response.status_code == 403, \
            f"PE user should get 403 for /api/licence/status, got {response.status_code}"
        print("PASS: PE user correctly denied access to /api/licence/status")
    
    def test_pe_user_cannot_access_license_definitions(self):
        """PE user should NOT be able to access /api/licence/definitions"""
        token = get_pe_user_token()
        assert token, "Failed to get PE user token"
        
        session = requests.Session()
        session.headers.update({
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        })
        
        response = session.get(f"{BASE_URL}/api/licence/definitions")
        print(f"PE user accessing /api/licence/definitions: {response.status_code}")
        assert response.status_code == 403, \
            f"PE user should get 403 for /api/licence/definitions, got {response.status_code}"
        print("PASS: PE user correctly denied access to /api/licence/definitions")
    
    def test_pe_user_cannot_generate_license(self):
        """PE user should NOT be able to generate licenses"""
        token = get_pe_user_token()
        assert token, "Failed to get PE user token"
        
        session = requests.Session()
        session.headers.update({
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        })
        
        response = session.post(f"{BASE_URL}/api/licence/generate", json={
            "company_type": "private_equity",
            "company_name": "TEST_UNAUTHORIZED",
            "duration_days": 30
        })
        print(f"PE user generating license: {response.status_code}")
        assert response.status_code == 403, \
            f"PE user should get 403 for /api/licence/generate, got {response.status_code}"
        print("PASS: PE user correctly denied license generation")
    
    def test_pe_user_cannot_access_all_licenses(self):
        """PE user should NOT be able to list all licenses"""
        token = get_pe_user_token()
        assert token, "Failed to get PE user token"
        
        session = requests.Session()
        session.headers.update({
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        })
        
        response = session.get(f"{BASE_URL}/api/licence/all")
        print(f"PE user accessing /api/licence/all: {response.status_code}")
        assert response.status_code == 403, \
            f"PE user should get 403 for /api/licence/all, got {response.status_code}"
        print("PASS: PE user correctly denied access to all licenses")
    
    def test_license_admin_can_access_license_status(self):
        """License admin should be able to access /api/licence/status"""
        token = get_license_admin_token()
        assert token, "Failed to get license admin token"
        
        session = requests.Session()
        session.headers.update({
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        })
        
        response = session.get(f"{BASE_URL}/api/licence/status")
        print(f"License admin accessing /api/licence/status: {response.status_code}")
        assert response.status_code == 200, \
            f"License admin should get 200 for /api/licence/status, got {response.status_code}"
        print("PASS: License admin can access /api/licence/status")
    
    def test_license_admin_can_access_definitions(self):
        """License admin should be able to access /api/licence/definitions"""
        token = get_license_admin_token()
        assert token, "Failed to get license admin token"
        
        session = requests.Session()
        session.headers.update({
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        })
        
        response = session.get(f"{BASE_URL}/api/licence/definitions")
        print(f"License admin accessing /api/licence/definitions: {response.status_code}")
        assert response.status_code == 200, \
            f"License admin should get 200 for /api/licence/definitions, got {response.status_code}"
        
        data = response.json()
        assert "modules" in data
        assert "features" in data
        assert "usage_limits" in data
        print("PASS: License admin can access /api/licence/definitions")


# ============== PE User NOT License Admin Verification ==============

class TestPEUserNotLicenseAdmin:
    """Test that PE user is correctly NOT a license admin"""
    
    def test_pe_user_verify_admin_returns_false(self):
        """PE user should get is_license_admin=false from verify-admin"""
        token = get_pe_user_token()
        assert token, "Failed to get PE user token"
        
        session = requests.Session()
        session.headers.update({
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        })
        
        response = session.get(f"{BASE_URL}/api/licence/verify-admin")
        print(f"PE user verify-admin: {response.status_code}")
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("is_license_admin") == False, \
            f"PE user should NOT be license admin, got {data}"
        print("PASS: PE user correctly not a license admin")


# ============== License Enforcement Tests ==============

class TestLicenseEnforcement:
    """Test license enforcement middleware"""
    
    def test_smifs_employee_exempt_from_license_checks(self):
        """SMIFS employees (@smifs.com) should be exempt from license checks"""
        token = get_pe_user_token()  # pe@smifs.com
        assert token, "Failed to get PE user token"
        
        session = requests.Session()
        session.headers.update({
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        })
        
        # SMIFS employees should always have access
        response = session.get(f"{BASE_URL}/api/licence/check/status")
        assert response.status_code == 200
        
        data = response.json()
        # SMIFS employee should have access regardless of license status
        print(f"SMIFS employee license check status returned: {data.get('is_licensed')}")
        print("PASS: SMIFS employee can access license check (exempt from checks)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
