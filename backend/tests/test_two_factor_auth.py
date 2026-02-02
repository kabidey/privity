"""
Two-Factor Authentication (2FA) API Tests

Tests all 2FA endpoints:
- GET /api/auth/2fa/status - Get 2FA status
- POST /api/auth/2fa/enable - Initiate 2FA setup
- POST /api/auth/2fa/verify-setup - Verify TOTP and activate 2FA
- POST /api/auth/2fa/verify - Verify TOTP code during login
- POST /api/auth/2fa/use-backup-code - Use backup code
- POST /api/auth/2fa/regenerate-backup-codes - Regenerate backup codes
- POST /api/auth/2fa/disable - Disable 2FA
- GET /api/auth/2fa/check-required - Check if 2FA is required
"""
import pytest
import requests
import os
import pyotp

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
PE_ADMIN_EMAIL = "pe@smifs.com"
PE_ADMIN_PASSWORD = "Kutta@123"
EMPLOYEE_EMAIL = "employee@test.com"
EMPLOYEE_PASSWORD = "Test@123"


class TestTwoFactorAuth:
    """Two-Factor Authentication API Tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        self.token = None
        self.user_id = None
        
    def login(self, email=PE_ADMIN_EMAIL, password=PE_ADMIN_PASSWORD):
        """Login and get auth token"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": email,
            "password": password
        })
        if response.status_code == 200:
            data = response.json()
            self.token = data.get("token")
            self.user_id = data.get("user", {}).get("id")
            self.session.headers.update({"Authorization": f"Bearer {self.token}"})
            return True
        return False
    
    # ============== 2FA Status Tests ==============
    
    def test_2fa_status_without_auth(self):
        """Test 2FA status endpoint without authentication - should fail"""
        response = self.session.get(f"{BASE_URL}/api/auth/2fa/status")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ 2FA status without auth returns 401/403")
    
    def test_2fa_status_with_auth(self):
        """Test 2FA status endpoint with authentication"""
        assert self.login(), "Login failed"
        
        response = self.session.get(f"{BASE_URL}/api/auth/2fa/status")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "enabled" in data, "Response should contain 'enabled' field"
        assert isinstance(data["enabled"], bool), "'enabled' should be boolean"
        assert "setup_pending" in data, "Response should contain 'setup_pending' field"
        assert "backup_codes_remaining" in data, "Response should contain 'backup_codes_remaining' field"
        
        print(f"✓ 2FA status: enabled={data['enabled']}, setup_pending={data['setup_pending']}, backup_codes={data['backup_codes_remaining']}")
    
    # ============== 2FA Enable Tests ==============
    
    def test_2fa_enable_without_auth(self):
        """Test 2FA enable endpoint without authentication - should fail"""
        response = self.session.post(f"{BASE_URL}/api/auth/2fa/enable", json={
            "password": "test"
        })
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ 2FA enable without auth returns 401/403")
    
    def test_2fa_enable_wrong_password(self):
        """Test 2FA enable with wrong password - should fail"""
        assert self.login(), "Login failed"
        
        response = self.session.post(f"{BASE_URL}/api/auth/2fa/enable", json={
            "password": "WrongPassword123"
        })
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
        print("✓ 2FA enable with wrong password returns 401")
    
    def test_2fa_enable_success(self):
        """Test 2FA enable with correct password - should return QR code and backup codes"""
        assert self.login(), "Login failed"
        
        # First check if 2FA is already enabled
        status_response = self.session.get(f"{BASE_URL}/api/auth/2fa/status")
        status_data = status_response.json()
        
        if status_data.get("enabled"):
            # Disable 2FA first
            disable_response = self.session.post(f"{BASE_URL}/api/auth/2fa/disable", json={
                "password": PE_ADMIN_PASSWORD
            })
            if disable_response.status_code != 200:
                pytest.skip("Cannot disable existing 2FA to test enable")
        
        response = self.session.post(f"{BASE_URL}/api/auth/2fa/enable", json={
            "password": PE_ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "qr_code_url" in data, "Response should contain 'qr_code_url'"
        assert "secret_key" in data, "Response should contain 'secret_key'"
        assert "backup_codes" in data, "Response should contain 'backup_codes'"
        assert "message" in data, "Response should contain 'message'"
        
        # Validate QR code URL format (data URL)
        assert data["qr_code_url"].startswith("data:image/png;base64,"), "QR code should be a data URL"
        
        # Validate secret key format (base32)
        assert len(data["secret_key"]) >= 16, "Secret key should be at least 16 characters"
        
        # Validate backup codes
        assert isinstance(data["backup_codes"], list), "backup_codes should be a list"
        assert len(data["backup_codes"]) == 10, f"Should have 10 backup codes, got {len(data['backup_codes'])}"
        
        # Validate backup code format (XXXX-XXXX)
        for code in data["backup_codes"]:
            assert "-" in code, f"Backup code should contain dash: {code}"
            assert len(code) == 9, f"Backup code should be 9 chars (XXXX-XXXX): {code}"
        
        print(f"✓ 2FA enable success: QR code generated, secret_key length={len(data['secret_key'])}, backup_codes={len(data['backup_codes'])}")
        
        # Store for next test
        self.__class__.pending_secret = data["secret_key"]
        self.__class__.backup_codes = data["backup_codes"]
    
    # ============== 2FA Verify Setup Tests ==============
    
    def test_2fa_verify_setup_without_pending(self):
        """Test verify-setup without pending setup - should fail"""
        assert self.login(), "Login failed"
        
        # First check status
        status_response = self.session.get(f"{BASE_URL}/api/auth/2fa/status")
        status_data = status_response.json()
        
        if status_data.get("setup_pending"):
            pytest.skip("Setup is pending, cannot test this case")
        
        response = self.session.post(f"{BASE_URL}/api/auth/2fa/verify-setup", json={
            "totp_code": "123456"
        })
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        print("✓ 2FA verify-setup without pending setup returns 400")
    
    def test_2fa_verify_setup_invalid_code(self):
        """Test verify-setup with invalid TOTP code - should fail"""
        assert self.login(), "Login failed"
        
        # First enable 2FA to create pending setup
        status_response = self.session.get(f"{BASE_URL}/api/auth/2fa/status")
        status_data = status_response.json()
        
        if status_data.get("enabled"):
            # Disable first
            self.session.post(f"{BASE_URL}/api/auth/2fa/disable", json={
                "password": PE_ADMIN_PASSWORD
            })
        
        # Enable 2FA
        enable_response = self.session.post(f"{BASE_URL}/api/auth/2fa/enable", json={
            "password": PE_ADMIN_PASSWORD
        })
        if enable_response.status_code != 200:
            pytest.skip("Cannot enable 2FA")
        
        # Try to verify with invalid code
        response = self.session.post(f"{BASE_URL}/api/auth/2fa/verify-setup", json={
            "totp_code": "000000"
        })
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
        print("✓ 2FA verify-setup with invalid code returns 401")
    
    def test_2fa_verify_setup_success(self):
        """Test verify-setup with valid TOTP code - should activate 2FA"""
        assert self.login(), "Login failed"
        
        # First check status
        status_response = self.session.get(f"{BASE_URL}/api/auth/2fa/status")
        status_data = status_response.json()
        
        if status_data.get("enabled"):
            # Disable first
            self.session.post(f"{BASE_URL}/api/auth/2fa/disable", json={
                "password": PE_ADMIN_PASSWORD
            })
        
        # Enable 2FA
        enable_response = self.session.post(f"{BASE_URL}/api/auth/2fa/enable", json={
            "password": PE_ADMIN_PASSWORD
        })
        assert enable_response.status_code == 200, f"Enable failed: {enable_response.text}"
        
        enable_data = enable_response.json()
        secret = enable_data["secret_key"]
        
        # Generate valid TOTP code using pyotp
        totp = pyotp.TOTP(secret)
        valid_code = totp.now()
        
        # Verify setup
        response = self.session.post(f"{BASE_URL}/api/auth/2fa/verify-setup", json={
            "totp_code": valid_code
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "message" in data, "Response should contain 'message'"
        assert "status" in data, "Response should contain 'status'"
        assert data["status"] == "enabled", f"Status should be 'enabled', got {data['status']}"
        
        # Verify 2FA is now enabled
        status_response = self.session.get(f"{BASE_URL}/api/auth/2fa/status")
        status_data = status_response.json()
        assert status_data["enabled"] == True, "2FA should be enabled after verify-setup"
        
        print(f"✓ 2FA verify-setup success: 2FA is now enabled")
        
        # Store secret for later tests
        self.__class__.active_secret = secret
    
    # ============== 2FA Verify Tests ==============
    
    def test_2fa_verify_when_not_enabled(self):
        """Test verify endpoint when 2FA is not enabled - should fail"""
        assert self.login(), "Login failed"
        
        # Check if 2FA is enabled
        status_response = self.session.get(f"{BASE_URL}/api/auth/2fa/status")
        status_data = status_response.json()
        
        if status_data.get("enabled"):
            # Disable first
            self.session.post(f"{BASE_URL}/api/auth/2fa/disable", json={
                "password": PE_ADMIN_PASSWORD
            })
        
        response = self.session.post(f"{BASE_URL}/api/auth/2fa/verify", json={
            "totp_code": "123456"
        })
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        print("✓ 2FA verify when not enabled returns 400")
    
    def test_2fa_verify_invalid_code(self):
        """Test verify endpoint with invalid TOTP code - should fail"""
        assert self.login(), "Login failed"
        
        # Ensure 2FA is enabled
        status_response = self.session.get(f"{BASE_URL}/api/auth/2fa/status")
        status_data = status_response.json()
        
        if not status_data.get("enabled"):
            # Enable 2FA first
            enable_response = self.session.post(f"{BASE_URL}/api/auth/2fa/enable", json={
                "password": PE_ADMIN_PASSWORD
            })
            if enable_response.status_code == 200:
                secret = enable_response.json()["secret_key"]
                totp = pyotp.TOTP(secret)
                self.session.post(f"{BASE_URL}/api/auth/2fa/verify-setup", json={
                    "totp_code": totp.now()
                })
        
        # Verify status again
        status_response = self.session.get(f"{BASE_URL}/api/auth/2fa/status")
        if not status_response.json().get("enabled"):
            pytest.skip("Cannot enable 2FA for this test")
        
        response = self.session.post(f"{BASE_URL}/api/auth/2fa/verify", json={
            "totp_code": "000000"
        })
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
        print("✓ 2FA verify with invalid code returns 401")
    
    def test_2fa_verify_success(self):
        """Test verify endpoint with valid TOTP code - should succeed"""
        assert self.login(), "Login failed"
        
        # Ensure 2FA is enabled
        status_response = self.session.get(f"{BASE_URL}/api/auth/2fa/status")
        status_data = status_response.json()
        
        secret = None
        if not status_data.get("enabled"):
            # Enable 2FA first
            enable_response = self.session.post(f"{BASE_URL}/api/auth/2fa/enable", json={
                "password": PE_ADMIN_PASSWORD
            })
            if enable_response.status_code == 200:
                secret = enable_response.json()["secret_key"]
                totp = pyotp.TOTP(secret)
                self.session.post(f"{BASE_URL}/api/auth/2fa/verify-setup", json={
                    "totp_code": totp.now()
                })
        
        # We need to get the secret from the user's 2FA config
        # Since we can't access it directly, we'll use the stored secret if available
        if hasattr(self.__class__, 'active_secret'):
            secret = self.__class__.active_secret
        
        if not secret:
            pytest.skip("No active secret available for verification test")
        
        totp = pyotp.TOTP(secret)
        valid_code = totp.now()
        
        response = self.session.post(f"{BASE_URL}/api/auth/2fa/verify", json={
            "totp_code": valid_code
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "verified" in data, "Response should contain 'verified'"
        assert data["verified"] == True, "verified should be True"
        
        print("✓ 2FA verify with valid code returns 200 and verified=True")
    
    # ============== Backup Code Tests ==============
    
    def test_2fa_use_backup_code_when_not_enabled(self):
        """Test use-backup-code when 2FA is not enabled - should fail"""
        assert self.login(), "Login failed"
        
        # Check if 2FA is enabled
        status_response = self.session.get(f"{BASE_URL}/api/auth/2fa/status")
        status_data = status_response.json()
        
        if status_data.get("enabled"):
            # Disable first
            self.session.post(f"{BASE_URL}/api/auth/2fa/disable", json={
                "password": PE_ADMIN_PASSWORD
            })
        
        response = self.session.post(f"{BASE_URL}/api/auth/2fa/use-backup-code", json={
            "backup_code": "ABCD-1234"
        })
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        print("✓ use-backup-code when 2FA not enabled returns 400")
    
    def test_2fa_use_backup_code_invalid(self):
        """Test use-backup-code with invalid code - should fail"""
        assert self.login(), "Login failed"
        
        # Ensure 2FA is enabled
        status_response = self.session.get(f"{BASE_URL}/api/auth/2fa/status")
        status_data = status_response.json()
        
        if not status_data.get("enabled"):
            # Enable 2FA first
            enable_response = self.session.post(f"{BASE_URL}/api/auth/2fa/enable", json={
                "password": PE_ADMIN_PASSWORD
            })
            if enable_response.status_code == 200:
                secret = enable_response.json()["secret_key"]
                totp = pyotp.TOTP(secret)
                self.session.post(f"{BASE_URL}/api/auth/2fa/verify-setup", json={
                    "totp_code": totp.now()
                })
        
        response = self.session.post(f"{BASE_URL}/api/auth/2fa/use-backup-code", json={
            "backup_code": "INVALID-CODE"
        })
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
        print("✓ use-backup-code with invalid code returns 401")
    
    # ============== Regenerate Backup Codes Tests ==============
    
    def test_2fa_regenerate_backup_codes_when_not_enabled(self):
        """Test regenerate-backup-codes when 2FA is not enabled - should fail"""
        assert self.login(), "Login failed"
        
        # Check if 2FA is enabled
        status_response = self.session.get(f"{BASE_URL}/api/auth/2fa/status")
        status_data = status_response.json()
        
        if status_data.get("enabled"):
            # Disable first
            self.session.post(f"{BASE_URL}/api/auth/2fa/disable", json={
                "password": PE_ADMIN_PASSWORD
            })
        
        response = self.session.post(f"{BASE_URL}/api/auth/2fa/regenerate-backup-codes", json={
            "password": PE_ADMIN_PASSWORD
        })
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        print("✓ regenerate-backup-codes when 2FA not enabled returns 400")
    
    def test_2fa_regenerate_backup_codes_wrong_password(self):
        """Test regenerate-backup-codes with wrong password - should fail"""
        assert self.login(), "Login failed"
        
        # Ensure 2FA is enabled
        status_response = self.session.get(f"{BASE_URL}/api/auth/2fa/status")
        status_data = status_response.json()
        
        if not status_data.get("enabled"):
            # Enable 2FA first
            enable_response = self.session.post(f"{BASE_URL}/api/auth/2fa/enable", json={
                "password": PE_ADMIN_PASSWORD
            })
            if enable_response.status_code == 200:
                secret = enable_response.json()["secret_key"]
                totp = pyotp.TOTP(secret)
                self.session.post(f"{BASE_URL}/api/auth/2fa/verify-setup", json={
                    "totp_code": totp.now()
                })
        
        response = self.session.post(f"{BASE_URL}/api/auth/2fa/regenerate-backup-codes", json={
            "password": "WrongPassword123"
        })
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
        print("✓ regenerate-backup-codes with wrong password returns 401")
    
    def test_2fa_regenerate_backup_codes_success(self):
        """Test regenerate-backup-codes with correct password - should succeed"""
        assert self.login(), "Login failed"
        
        # Ensure 2FA is enabled
        status_response = self.session.get(f"{BASE_URL}/api/auth/2fa/status")
        status_data = status_response.json()
        
        if not status_data.get("enabled"):
            # Enable 2FA first
            enable_response = self.session.post(f"{BASE_URL}/api/auth/2fa/enable", json={
                "password": PE_ADMIN_PASSWORD
            })
            if enable_response.status_code == 200:
                secret = enable_response.json()["secret_key"]
                self.__class__.active_secret = secret
                totp = pyotp.TOTP(secret)
                self.session.post(f"{BASE_URL}/api/auth/2fa/verify-setup", json={
                    "totp_code": totp.now()
                })
        
        response = self.session.post(f"{BASE_URL}/api/auth/2fa/regenerate-backup-codes", json={
            "password": PE_ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "backup_codes" in data, "Response should contain 'backup_codes'"
        assert isinstance(data["backup_codes"], list), "backup_codes should be a list"
        assert len(data["backup_codes"]) == 10, f"Should have 10 backup codes, got {len(data['backup_codes'])}"
        
        print(f"✓ regenerate-backup-codes success: {len(data['backup_codes'])} new codes generated")
    
    # ============== Disable 2FA Tests ==============
    
    def test_2fa_disable_when_not_enabled(self):
        """Test disable when 2FA is not enabled - should fail"""
        assert self.login(), "Login failed"
        
        # Check if 2FA is enabled
        status_response = self.session.get(f"{BASE_URL}/api/auth/2fa/status")
        status_data = status_response.json()
        
        if status_data.get("enabled"):
            # Disable first
            self.session.post(f"{BASE_URL}/api/auth/2fa/disable", json={
                "password": PE_ADMIN_PASSWORD
            })
        
        response = self.session.post(f"{BASE_URL}/api/auth/2fa/disable", json={
            "password": PE_ADMIN_PASSWORD
        })
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        print("✓ disable when 2FA not enabled returns 400")
    
    def test_2fa_disable_wrong_password(self):
        """Test disable with wrong password - should fail"""
        assert self.login(), "Login failed"
        
        # Ensure 2FA is enabled
        status_response = self.session.get(f"{BASE_URL}/api/auth/2fa/status")
        status_data = status_response.json()
        
        if not status_data.get("enabled"):
            # Enable 2FA first
            enable_response = self.session.post(f"{BASE_URL}/api/auth/2fa/enable", json={
                "password": PE_ADMIN_PASSWORD
            })
            if enable_response.status_code == 200:
                secret = enable_response.json()["secret_key"]
                totp = pyotp.TOTP(secret)
                self.session.post(f"{BASE_URL}/api/auth/2fa/verify-setup", json={
                    "totp_code": totp.now()
                })
        
        response = self.session.post(f"{BASE_URL}/api/auth/2fa/disable", json={
            "password": "WrongPassword123"
        })
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
        print("✓ disable with wrong password returns 401")
    
    def test_2fa_disable_success(self):
        """Test disable with correct password - should succeed"""
        assert self.login(), "Login failed"
        
        # Ensure 2FA is enabled
        status_response = self.session.get(f"{BASE_URL}/api/auth/2fa/status")
        status_data = status_response.json()
        
        if not status_data.get("enabled"):
            # Enable 2FA first
            enable_response = self.session.post(f"{BASE_URL}/api/auth/2fa/enable", json={
                "password": PE_ADMIN_PASSWORD
            })
            if enable_response.status_code == 200:
                secret = enable_response.json()["secret_key"]
                totp = pyotp.TOTP(secret)
                self.session.post(f"{BASE_URL}/api/auth/2fa/verify-setup", json={
                    "totp_code": totp.now()
                })
        
        response = self.session.post(f"{BASE_URL}/api/auth/2fa/disable", json={
            "password": PE_ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "status" in data, "Response should contain 'status'"
        assert data["status"] == "disabled", f"Status should be 'disabled', got {data['status']}"
        
        # Verify 2FA is now disabled
        status_response = self.session.get(f"{BASE_URL}/api/auth/2fa/status")
        status_data = status_response.json()
        assert status_data["enabled"] == False, "2FA should be disabled after disable"
        
        print("✓ disable success: 2FA is now disabled")
    
    # ============== Check Required Tests ==============
    
    def test_2fa_check_required(self):
        """Test check-required endpoint"""
        assert self.login(), "Login failed"
        
        response = self.session.get(f"{BASE_URL}/api/auth/2fa/check-required")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "two_factor_enabled" in data, "Response should contain 'two_factor_enabled'"
        assert "two_factor_required" in data, "Response should contain 'two_factor_required'"
        
        print(f"✓ check-required: enabled={data['two_factor_enabled']}, required={data['two_factor_required']}")


class TestTwoFactorAuthFullFlow:
    """Full 2FA flow test - Enable, Verify, Use, Disable"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
    def test_full_2fa_flow(self):
        """Test complete 2FA flow: Enable -> Verify Setup -> Verify Code -> Regenerate Backup -> Disable"""
        # Login
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": PE_ADMIN_EMAIL,
            "password": PE_ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        token = response.json()["token"]
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        print("✓ Step 1: Login successful")
        
        # Check initial status
        status_response = self.session.get(f"{BASE_URL}/api/auth/2fa/status")
        assert status_response.status_code == 200
        initial_status = status_response.json()
        print(f"✓ Step 2: Initial 2FA status: enabled={initial_status['enabled']}")
        
        # If 2FA is enabled, disable it first
        if initial_status.get("enabled"):
            disable_response = self.session.post(f"{BASE_URL}/api/auth/2fa/disable", json={
                "password": PE_ADMIN_PASSWORD
            })
            assert disable_response.status_code == 200, f"Disable failed: {disable_response.text}"
            print("✓ Step 2b: Disabled existing 2FA")
        
        # Enable 2FA
        enable_response = self.session.post(f"{BASE_URL}/api/auth/2fa/enable", json={
            "password": PE_ADMIN_PASSWORD
        })
        assert enable_response.status_code == 200, f"Enable failed: {enable_response.text}"
        enable_data = enable_response.json()
        secret = enable_data["secret_key"]
        backup_codes = enable_data["backup_codes"]
        print(f"✓ Step 3: 2FA enabled, got secret and {len(backup_codes)} backup codes")
        
        # Verify setup with valid TOTP
        totp = pyotp.TOTP(secret)
        valid_code = totp.now()
        verify_setup_response = self.session.post(f"{BASE_URL}/api/auth/2fa/verify-setup", json={
            "totp_code": valid_code
        })
        assert verify_setup_response.status_code == 200, f"Verify setup failed: {verify_setup_response.text}"
        print("✓ Step 4: 2FA setup verified and activated")
        
        # Verify status is now enabled
        status_response = self.session.get(f"{BASE_URL}/api/auth/2fa/status")
        assert status_response.json()["enabled"] == True
        print("✓ Step 5: Confirmed 2FA is enabled")
        
        # Verify TOTP code
        valid_code = totp.now()
        verify_response = self.session.post(f"{BASE_URL}/api/auth/2fa/verify", json={
            "totp_code": valid_code
        })
        assert verify_response.status_code == 200, f"Verify failed: {verify_response.text}"
        assert verify_response.json()["verified"] == True
        print("✓ Step 6: TOTP code verification successful")
        
        # Regenerate backup codes
        regen_response = self.session.post(f"{BASE_URL}/api/auth/2fa/regenerate-backup-codes", json={
            "password": PE_ADMIN_PASSWORD
        })
        assert regen_response.status_code == 200, f"Regenerate failed: {regen_response.text}"
        new_backup_codes = regen_response.json()["backup_codes"]
        assert len(new_backup_codes) == 10
        print(f"✓ Step 7: Regenerated {len(new_backup_codes)} new backup codes")
        
        # Disable 2FA
        disable_response = self.session.post(f"{BASE_URL}/api/auth/2fa/disable", json={
            "password": PE_ADMIN_PASSWORD
        })
        assert disable_response.status_code == 200, f"Disable failed: {disable_response.text}"
        print("✓ Step 8: 2FA disabled")
        
        # Verify status is now disabled
        status_response = self.session.get(f"{BASE_URL}/api/auth/2fa/status")
        assert status_response.json()["enabled"] == False
        print("✓ Step 9: Confirmed 2FA is disabled")
        
        print("\n✓✓✓ FULL 2FA FLOW TEST PASSED ✓✓✓")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
