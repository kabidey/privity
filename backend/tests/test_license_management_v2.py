"""
License Management V2 Test Suite
Tests the granular licensing system including:
- License admin authentication and verification
- License generation with granular permissions
- License activation and status
- Hidden admin user exclusion from user lists
- Access control for regular users
"""
import pytest
import requests
import os

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

# Test credentials
LICENSE_ADMIN_EMAIL = "deynet@gmail.com"
LICENSE_ADMIN_PASSWORD = "Kutta@123"
PE_DESK_EMAIL = "pe@smifs.com"
PE_DESK_PASSWORD = "Kutta@123"


class TestLicenseAdminAuth:
    """Test license admin login and verification"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def test_license_admin_login_success(self):
        """Test license admin can login successfully"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": LICENSE_ADMIN_EMAIL,
            "password": LICENSE_ADMIN_PASSWORD
        })
        print(f"License admin login response: {response.status_code}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "access_token" in data or "token" in data, "Expected token in response"
        print("PASS: License admin login successful")
    
    def test_license_admin_verify_endpoint(self):
        """Test /api/licence/verify-admin returns is_license_admin=true for license admin"""
        # First login
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": LICENSE_ADMIN_EMAIL,
            "password": LICENSE_ADMIN_PASSWORD
        })
        assert login_response.status_code == 200
        
        token = login_response.json().get("access_token") or login_response.json().get("token")
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        # Verify admin access
        response = self.session.get(f"{BASE_URL}/api/licence/verify-admin")
        print(f"Verify admin response: {response.status_code} - {response.text}")
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("is_license_admin") == True, f"Expected is_license_admin=True, got {data}"
        print("PASS: License admin verified successfully")
    
    def test_pe_desk_cannot_access_verify_admin(self):
        """Test regular PE desk user is not a license admin"""
        # Login as PE desk
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": PE_DESK_EMAIL,
            "password": PE_DESK_PASSWORD
        })
        assert login_response.status_code == 200
        
        token = login_response.json().get("access_token") or login_response.json().get("token")
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        # Check verify-admin returns is_license_admin=false
        response = self.session.get(f"{BASE_URL}/api/licence/verify-admin")
        print(f"PE desk verify admin response: {response.status_code} - {response.text}")
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("is_license_admin") == False, f"Expected is_license_admin=False for PE desk, got {data}"
        print("PASS: PE desk correctly not a license admin")


class TestLicenseAdminHiddenFromUserList:
    """Test that license admin is hidden from user listings"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as PE desk to get token for user list
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": PE_DESK_EMAIL,
            "password": PE_DESK_PASSWORD
        })
        assert login_response.status_code == 200
        token = login_response.json().get("access_token") or login_response.json().get("token")
        self.session.headers.update({"Authorization": f"Bearer {token}"})
    
    def test_license_admin_not_in_user_list(self):
        """Test /api/users does not include the hidden license admin"""
        response = self.session.get(f"{BASE_URL}/api/users")
        print(f"User list response: {response.status_code}")
        assert response.status_code == 200
        
        users = response.json()
        # Check that license admin email is NOT in the list
        user_emails = [u.get("email") for u in users]
        assert LICENSE_ADMIN_EMAIL not in user_emails, f"License admin {LICENSE_ADMIN_EMAIL} should NOT be in user list"
        print(f"PASS: License admin not in user list (checked {len(users)} users)")
    
    def test_license_admin_not_in_employees_list(self):
        """Test /api/users/employees does not include the hidden license admin"""
        response = self.session.get(f"{BASE_URL}/api/users/employees")
        print(f"Employees list response: {response.status_code}")
        assert response.status_code == 200
        
        users = response.json()
        user_emails = [u.get("email") for u in users]
        assert LICENSE_ADMIN_EMAIL not in user_emails, f"License admin should NOT be in employees list"
        print(f"PASS: License admin not in employees list")


class TestLicenseDefinitions:
    """Test license definitions endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as license admin
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": LICENSE_ADMIN_EMAIL,
            "password": LICENSE_ADMIN_PASSWORD
        })
        assert login_response.status_code == 200
        token = login_response.json().get("access_token") or login_response.json().get("token")
        self.session.headers.update({"Authorization": f"Bearer {token}"})
    
    def test_get_license_definitions(self):
        """Test /api/licence/definitions returns modules, features, and usage_limits"""
        response = self.session.get(f"{BASE_URL}/api/licence/definitions")
        print(f"Definitions response: {response.status_code}")
        assert response.status_code == 200
        
        data = response.json()
        assert "modules" in data, "Expected 'modules' in definitions"
        assert "features" in data, "Expected 'features' in definitions"
        assert "usage_limits" in data, "Expected 'usage_limits' in definitions"
        
        # Check modules contain PE and FI
        modules = data["modules"]
        assert "private_equity" in modules, "Expected 'private_equity' module"
        assert "fixed_income" in modules, "Expected 'fixed_income' module"
        
        # Check features structure
        features = data["features"]
        assert len(features) > 0, "Expected at least some features"
        # Check a sample feature
        if "clients" in features:
            assert "name" in features["clients"]
            assert "module" in features["clients"]
        
        # Check usage limits
        usage_limits = data["usage_limits"]
        assert "max_users" in usage_limits, "Expected 'max_users' in usage_limits"
        assert "max_clients" in usage_limits, "Expected 'max_clients' in usage_limits"
        
        print(f"PASS: Definitions returned {len(modules)} modules, {len(features)} features, {len(usage_limits)} usage limits")
    
    def test_pe_desk_cannot_access_definitions(self):
        """Test regular PE desk user cannot access definitions"""
        # Create new session and login as PE desk
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})
        
        login_response = session.post(f"{BASE_URL}/api/auth/login", json={
            "email": PE_DESK_EMAIL,
            "password": PE_DESK_PASSWORD
        })
        assert login_response.status_code == 200
        token = login_response.json().get("access_token") or login_response.json().get("token")
        session.headers.update({"Authorization": f"Bearer {token}"})
        
        # Try to access definitions
        response = session.get(f"{BASE_URL}/api/licence/definitions")
        print(f"PE desk definitions access: {response.status_code}")
        assert response.status_code == 403, f"Expected 403 for PE desk, got {response.status_code}"
        print("PASS: PE desk correctly denied access to definitions")


class TestLicenseGeneration:
    """Test license generation endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as license admin
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": LICENSE_ADMIN_EMAIL,
            "password": LICENSE_ADMIN_PASSWORD
        })
        assert login_response.status_code == 200
        token = login_response.json().get("access_token") or login_response.json().get("token")
        self.session.headers.update({"Authorization": f"Bearer {token}"})
    
    def test_generate_pe_license(self):
        """Test generating a Private Equity license"""
        response = self.session.post(f"{BASE_URL}/api/licence/generate", json={
            "company_type": "private_equity",
            "company_name": "TEST_COMPANY_PE",
            "duration_days": 30,
            "modules": ["private_equity"],
            "features": ["clients", "bookings", "reports"],
            "usage_limits": {"max_users": 10, "max_clients": 100}
        })
        print(f"Generate PE license response: {response.status_code}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("success") == True, f"Expected success=True, got {data}"
        assert "license" in data, "Expected 'license' in response"
        
        license_info = data["license"]
        assert license_info.get("key", "").startswith("PRIV-PE-"), f"Expected PE license key, got {license_info.get('key')}"
        assert license_info.get("company_type") == "private_equity"
        print(f"PASS: PE license generated: {license_info.get('key')}")
        
        return license_info.get("key")
    
    def test_generate_fi_license(self):
        """Test generating a Fixed Income license"""
        response = self.session.post(f"{BASE_URL}/api/licence/generate", json={
            "company_type": "fixed_income",
            "company_name": "TEST_COMPANY_FI",
            "duration_days": 60,
            "modules": ["fixed_income"],
            "features": ["fi_instruments", "fi_orders", "fi_reports"],
            "usage_limits": {"max_fi_orders_per_month": 50}
        })
        print(f"Generate FI license response: {response.status_code}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("success") == True
        
        license_info = data["license"]
        assert license_info.get("key", "").startswith("PRIV-FI-"), f"Expected FI license key, got {license_info.get('key')}"
        assert license_info.get("company_type") == "fixed_income"
        print(f"PASS: FI license generated: {license_info.get('key')}")
    
    def test_pe_desk_cannot_generate_license(self):
        """Test regular PE desk user cannot generate licenses"""
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})
        
        login_response = session.post(f"{BASE_URL}/api/auth/login", json={
            "email": PE_DESK_EMAIL,
            "password": PE_DESK_PASSWORD
        })
        assert login_response.status_code == 200
        token = login_response.json().get("access_token") or login_response.json().get("token")
        session.headers.update({"Authorization": f"Bearer {token}"})
        
        response = session.post(f"{BASE_URL}/api/licence/generate", json={
            "company_type": "private_equity",
            "company_name": "TEST",
            "duration_days": 30
        })
        print(f"PE desk generate license: {response.status_code}")
        assert response.status_code == 403, f"Expected 403 for PE desk, got {response.status_code}"
        print("PASS: PE desk correctly denied license generation")


class TestLicenseActivation:
    """Test license activation endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as license admin
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": LICENSE_ADMIN_EMAIL,
            "password": LICENSE_ADMIN_PASSWORD
        })
        assert login_response.status_code == 200
        token = login_response.json().get("access_token") or login_response.json().get("token")
        self.session.headers.update({"Authorization": f"Bearer {token}"})
    
    def test_activate_license(self):
        """Test activating a generated license"""
        # First generate a license
        gen_response = self.session.post(f"{BASE_URL}/api/licence/generate", json={
            "company_type": "private_equity",
            "company_name": "TEST_ACTIVATE_PE",
            "duration_days": 30,
            "modules": ["private_equity"],
            "features": ["clients", "bookings"]
        })
        assert gen_response.status_code == 200
        license_key = gen_response.json()["license"]["key"]
        print(f"Generated license: {license_key}")
        
        # Now activate it
        activate_response = self.session.post(f"{BASE_URL}/api/licence/activate", json={
            "license_key": license_key
        })
        print(f"Activate response: {activate_response.status_code} - {activate_response.text}")
        assert activate_response.status_code == 200, f"Expected 200, got {activate_response.status_code}: {activate_response.text}"
        
        data = activate_response.json()
        assert data.get("success") == True
        assert data.get("company_type") == "private_equity"
        print(f"PASS: License activated successfully")
    
    def test_activate_invalid_license(self):
        """Test activating an invalid license key"""
        response = self.session.post(f"{BASE_URL}/api/licence/activate", json={
            "license_key": "INVALID-KEY-1234"
        })
        print(f"Invalid license activation: {response.status_code}")
        assert response.status_code == 400, f"Expected 400 for invalid key, got {response.status_code}"
        print("PASS: Invalid license correctly rejected")


class TestLicenseStatus:
    """Test license status endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as license admin
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": LICENSE_ADMIN_EMAIL,
            "password": LICENSE_ADMIN_PASSWORD
        })
        assert login_response.status_code == 200
        token = login_response.json().get("access_token") or login_response.json().get("token")
        self.session.headers.update({"Authorization": f"Bearer {token}"})
    
    def test_get_license_status(self):
        """Test /api/licence/status returns PE and FI license status"""
        response = self.session.get(f"{BASE_URL}/api/licence/status")
        print(f"License status response: {response.status_code}")
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data, "Expected 'status' in response"
        
        status = data["status"]
        assert "private_equity" in status, "Expected 'private_equity' status"
        assert "fixed_income" in status, "Expected 'fixed_income' status"
        
        # Check structure of status
        pe_status = status["private_equity"]
        fi_status = status["fixed_income"]
        
        # Status should have these fields
        assert "status" in pe_status or "is_active" in pe_status
        assert "status" in fi_status or "is_active" in fi_status
        
        print(f"PASS: License status returned - PE: {pe_status.get('status', pe_status.get('is_active'))}, FI: {fi_status.get('status', fi_status.get('is_active'))}")
    
    def test_pe_desk_cannot_access_status(self):
        """Test regular PE desk user cannot access full license status"""
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})
        
        login_response = session.post(f"{BASE_URL}/api/auth/login", json={
            "email": PE_DESK_EMAIL,
            "password": PE_DESK_PASSWORD
        })
        assert login_response.status_code == 200
        token = login_response.json().get("access_token") or login_response.json().get("token")
        session.headers.update({"Authorization": f"Bearer {token}"})
        
        response = session.get(f"{BASE_URL}/api/licence/status")
        print(f"PE desk status access: {response.status_code}")
        assert response.status_code == 403, f"Expected 403 for PE desk, got {response.status_code}"
        print("PASS: PE desk correctly denied access to status")


class TestLicenseAllList:
    """Test listing all licenses"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as license admin
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": LICENSE_ADMIN_EMAIL,
            "password": LICENSE_ADMIN_PASSWORD
        })
        assert login_response.status_code == 200
        token = login_response.json().get("access_token") or login_response.json().get("token")
        self.session.headers.update({"Authorization": f"Bearer {token}"})
    
    def test_get_all_licenses(self):
        """Test /api/licence/all returns list of all licenses"""
        response = self.session.get(f"{BASE_URL}/api/licence/all")
        print(f"All licenses response: {response.status_code}")
        assert response.status_code == 200
        
        data = response.json()
        assert "licenses" in data, "Expected 'licenses' in response"
        
        licenses = data["licenses"]
        print(f"PASS: Found {len(licenses)} licenses")
        
        if len(licenses) > 0:
            # Check structure of a license
            lic = licenses[0]
            assert "license_key" in lic or "license_key_masked" in lic
            assert "company_type" in lic
            assert "status" in lic
            print(f"First license: {lic.get('license_key_masked', lic.get('license_key', '')[:15])} - {lic.get('status')}")
    
    def test_pe_desk_cannot_list_all_licenses(self):
        """Test regular PE desk user cannot list all licenses"""
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})
        
        login_response = session.post(f"{BASE_URL}/api/auth/login", json={
            "email": PE_DESK_EMAIL,
            "password": PE_DESK_PASSWORD
        })
        assert login_response.status_code == 200
        token = login_response.json().get("access_token") or login_response.json().get("token")
        session.headers.update({"Authorization": f"Bearer {token}"})
        
        response = session.get(f"{BASE_URL}/api/licence/all")
        print(f"PE desk all licenses access: {response.status_code}")
        assert response.status_code == 403, f"Expected 403 for PE desk, got {response.status_code}"
        print("PASS: PE desk correctly denied access to all licenses")


class TestLicenseCheckEndpoints:
    """Test public license checking endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def test_check_app_license_status_as_pe_desk(self):
        """Test /api/licence/check/status works for regular users"""
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": PE_DESK_EMAIL,
            "password": PE_DESK_PASSWORD
        })
        assert login_response.status_code == 200
        token = login_response.json().get("access_token") or login_response.json().get("token")
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        response = self.session.get(f"{BASE_URL}/api/licence/check/status")
        print(f"Check status response: {response.status_code}")
        assert response.status_code == 200
        
        data = response.json()
        assert "is_licensed" in data
        assert "private_equity" in data
        assert "fixed_income" in data
        print(f"PASS: License check status returned - is_licensed: {data.get('is_licensed')}")
    
    def test_check_feature_license(self):
        """Test /api/licence/check/feature endpoint"""
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": PE_DESK_EMAIL,
            "password": PE_DESK_PASSWORD
        })
        assert login_response.status_code == 200
        token = login_response.json().get("access_token") or login_response.json().get("token")
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        response = self.session.post(f"{BASE_URL}/api/licence/check/feature", json={
            "feature": "clients",
            "company_type": "private_equity"
        })
        print(f"Check feature response: {response.status_code} - {response.text}")
        assert response.status_code == 200
        
        data = response.json()
        assert "is_licensed" in data
        assert "message" in data
        print(f"PASS: Feature check returned - is_licensed: {data.get('is_licensed')}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
