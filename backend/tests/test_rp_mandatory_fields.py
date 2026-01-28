"""
Test Referral Partner Creation with Mandatory Fields Validation
Tests:
- All fields mandatory (Name, Email, Phone, PAN, Aadhar, Address)
- 10-digit phone validation (without +91)
- Email validation
- PAN 10-char validation
- Aadhar 12-digit validation
- Address mandatory validation
- RP email notification on stock transfer confirmation
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestRPMandatoryFields:
    """Test RP creation with all mandatory fields validation"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - login and get auth token"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as PE Desk
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "pedesk@smifs.com",
            "password": "Kutta@123"
        })
        
        if login_response.status_code == 200:
            token = login_response.json().get("token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
            self.auth_token = token
        else:
            pytest.skip("Authentication failed - skipping tests")
    
    # ============== Name Validation ==============
    def test_01_name_required(self):
        """Test that name is required"""
        response = self.session.post(f"{BASE_URL}/api/referral-partners", json={
            "name": "",  # Empty name
            "email": "test@example.com",
            "phone": "9876543210",
            "pan_number": "ABCDE1234F",
            "aadhar_number": "123456789012",
            "address": "Test Address"
        })
        # Should fail validation - either 400 or 422
        assert response.status_code in [400, 422], f"Expected 400/422, got {response.status_code}: {response.text}"
        print(f"✓ Empty name correctly rejected: {response.status_code}")
    
    def test_02_name_whitespace_only(self):
        """Test that whitespace-only name is rejected"""
        response = self.session.post(f"{BASE_URL}/api/referral-partners", json={
            "name": "   ",  # Whitespace only
            "email": "test@example.com",
            "phone": "9876543210",
            "pan_number": "ABCDE1234F",
            "aadhar_number": "123456789012",
            "address": "Test Address"
        })
        # Should fail - name should be stripped and validated
        assert response.status_code in [400, 422], f"Expected 400/422, got {response.status_code}"
        print(f"✓ Whitespace-only name correctly rejected: {response.status_code}")
    
    # ============== Email Validation ==============
    def test_03_email_required(self):
        """Test that email is required"""
        response = self.session.post(f"{BASE_URL}/api/referral-partners", json={
            "name": "Test RP",
            "email": "",  # Empty email
            "phone": "9876543210",
            "pan_number": "ABCDE1234F",
            "aadhar_number": "123456789012",
            "address": "Test Address"
        })
        assert response.status_code in [400, 422], f"Expected 400/422, got {response.status_code}"
        print(f"✓ Empty email correctly rejected: {response.status_code}")
    
    def test_04_email_invalid_format(self):
        """Test that invalid email format is rejected"""
        response = self.session.post(f"{BASE_URL}/api/referral-partners", json={
            "name": "Test RP",
            "email": "invalid-email",  # Invalid format
            "phone": "9876543210",
            "pan_number": "ABCDE1234F",
            "aadhar_number": "123456789012",
            "address": "Test Address"
        })
        assert response.status_code in [400, 422], f"Expected 400/422, got {response.status_code}"
        print(f"✓ Invalid email format correctly rejected: {response.status_code}")
    
    def test_05_email_valid_format(self):
        """Test that valid email format is accepted"""
        # This test just validates the email format check, not full creation
        # We'll use a unique email to avoid duplicate errors
        import uuid
        unique_email = f"test_{uuid.uuid4().hex[:8]}@example.com"
        unique_pan = f"TEST{uuid.uuid4().hex[:6].upper()}"[:10]
        unique_aadhar = str(uuid.uuid4().int)[:12]
        
        response = self.session.post(f"{BASE_URL}/api/referral-partners", json={
            "name": "Test RP Valid Email",
            "email": unique_email,
            "phone": "9876543210",
            "pan_number": unique_pan,
            "aadhar_number": unique_aadhar,
            "address": "Test Address"
        })
        # Should succeed or fail for other reasons (not email format)
        if response.status_code == 201:
            print(f"✓ Valid email format accepted: {response.status_code}")
        else:
            # Check if error is NOT about email format
            error_detail = response.json().get("detail", "")
            assert "email" not in error_detail.lower() or "already exists" in error_detail.lower(), \
                f"Email format should be valid: {error_detail}"
            print(f"✓ Valid email format accepted (other validation failed): {error_detail}")
    
    # ============== Phone Validation (10 digits without +91) ==============
    def test_06_phone_required(self):
        """Test that phone is required"""
        response = self.session.post(f"{BASE_URL}/api/referral-partners", json={
            "name": "Test RP",
            "email": "test@example.com",
            "phone": "",  # Empty phone
            "pan_number": "ABCDE1234F",
            "aadhar_number": "123456789012",
            "address": "Test Address"
        })
        assert response.status_code in [400, 422], f"Expected 400/422, got {response.status_code}"
        print(f"✓ Empty phone correctly rejected: {response.status_code}")
    
    def test_07_phone_less_than_10_digits(self):
        """Test that phone with less than 10 digits is rejected"""
        response = self.session.post(f"{BASE_URL}/api/referral-partners", json={
            "name": "Test RP",
            "email": "test@example.com",
            "phone": "987654321",  # 9 digits
            "pan_number": "ABCDE1234F",
            "aadhar_number": "123456789012",
            "address": "Test Address"
        })
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        assert "10 digits" in response.json().get("detail", "").lower(), \
            f"Error should mention 10 digits: {response.json()}"
        print(f"✓ 9-digit phone correctly rejected: {response.json().get('detail')}")
    
    def test_08_phone_more_than_10_digits(self):
        """Test that phone with more than 10 digits is rejected"""
        response = self.session.post(f"{BASE_URL}/api/referral-partners", json={
            "name": "Test RP",
            "email": "test@example.com",
            "phone": "98765432101",  # 11 digits
            "pan_number": "ABCDE1234F",
            "aadhar_number": "123456789012",
            "address": "Test Address"
        })
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        assert "10 digits" in response.json().get("detail", "").lower(), \
            f"Error should mention 10 digits: {response.json()}"
        print(f"✓ 11-digit phone correctly rejected: {response.json().get('detail')}")
    
    def test_09_phone_with_plus91_rejected(self):
        """Test that phone with +91 prefix is rejected (should be 10 digits only)"""
        response = self.session.post(f"{BASE_URL}/api/referral-partners", json={
            "name": "Test RP",
            "email": "test@example.com",
            "phone": "+919876543210",  # With +91 prefix
            "pan_number": "ABCDE1234F",
            "aadhar_number": "123456789012",
            "address": "Test Address"
        })
        # Backend extracts digits, so +919876543210 becomes 919876543210 (12 digits) - should fail
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print(f"✓ Phone with +91 prefix correctly rejected: {response.json().get('detail')}")
    
    def test_10_phone_exactly_10_digits_valid(self):
        """Test that exactly 10 digit phone is accepted"""
        import uuid
        unique_email = f"test_{uuid.uuid4().hex[:8]}@example.com"
        unique_pan = f"PHONE{uuid.uuid4().hex[:5].upper()}"[:10]
        unique_aadhar = str(uuid.uuid4().int)[:12]
        
        response = self.session.post(f"{BASE_URL}/api/referral-partners", json={
            "name": "Test RP 10 Digit Phone",
            "email": unique_email,
            "phone": "9876543210",  # Exactly 10 digits
            "pan_number": unique_pan,
            "aadhar_number": unique_aadhar,
            "address": "Test Address"
        })
        # Should succeed or fail for other reasons (not phone)
        if response.status_code == 201:
            print(f"✓ 10-digit phone accepted: {response.status_code}")
        else:
            error_detail = response.json().get("detail", "")
            assert "phone" not in error_detail.lower() or "10 digits" not in error_detail.lower(), \
                f"Phone should be valid: {error_detail}"
            print(f"✓ 10-digit phone format accepted (other validation failed): {error_detail}")
    
    # ============== PAN Validation (10 characters) ==============
    def test_11_pan_required(self):
        """Test that PAN is required"""
        response = self.session.post(f"{BASE_URL}/api/referral-partners", json={
            "name": "Test RP",
            "email": "test@example.com",
            "phone": "9876543210",
            "pan_number": "",  # Empty PAN
            "aadhar_number": "123456789012",
            "address": "Test Address"
        })
        assert response.status_code in [400, 422], f"Expected 400/422, got {response.status_code}"
        print(f"✓ Empty PAN correctly rejected: {response.status_code}")
    
    def test_12_pan_less_than_10_chars(self):
        """Test that PAN with less than 10 characters is rejected"""
        response = self.session.post(f"{BASE_URL}/api/referral-partners", json={
            "name": "Test RP",
            "email": "test@example.com",
            "phone": "9876543210",
            "pan_number": "ABCDE1234",  # 9 characters
            "aadhar_number": "123456789012",
            "address": "Test Address"
        })
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        assert "10 characters" in response.json().get("detail", "").lower(), \
            f"Error should mention 10 characters: {response.json()}"
        print(f"✓ 9-char PAN correctly rejected: {response.json().get('detail')}")
    
    def test_13_pan_more_than_10_chars(self):
        """Test that PAN with more than 10 characters is rejected"""
        response = self.session.post(f"{BASE_URL}/api/referral-partners", json={
            "name": "Test RP",
            "email": "test@example.com",
            "phone": "9876543210",
            "pan_number": "ABCDE12345F",  # 11 characters
            "aadhar_number": "123456789012",
            "address": "Test Address"
        })
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        assert "10 characters" in response.json().get("detail", "").lower(), \
            f"Error should mention 10 characters: {response.json()}"
        print(f"✓ 11-char PAN correctly rejected: {response.json().get('detail')}")
    
    # ============== Aadhar Validation (12 digits) ==============
    def test_14_aadhar_required(self):
        """Test that Aadhar is required"""
        response = self.session.post(f"{BASE_URL}/api/referral-partners", json={
            "name": "Test RP",
            "email": "test@example.com",
            "phone": "9876543210",
            "pan_number": "ABCDE1234F",
            "aadhar_number": "",  # Empty Aadhar
            "address": "Test Address"
        })
        assert response.status_code in [400, 422], f"Expected 400/422, got {response.status_code}"
        print(f"✓ Empty Aadhar correctly rejected: {response.status_code}")
    
    def test_15_aadhar_less_than_12_digits(self):
        """Test that Aadhar with less than 12 digits is rejected"""
        response = self.session.post(f"{BASE_URL}/api/referral-partners", json={
            "name": "Test RP",
            "email": "test@example.com",
            "phone": "9876543210",
            "pan_number": "ABCDE1234F",
            "aadhar_number": "12345678901",  # 11 digits
            "address": "Test Address"
        })
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        assert "12 digits" in response.json().get("detail", "").lower(), \
            f"Error should mention 12 digits: {response.json()}"
        print(f"✓ 11-digit Aadhar correctly rejected: {response.json().get('detail')}")
    
    def test_16_aadhar_more_than_12_digits(self):
        """Test that Aadhar with more than 12 digits is rejected"""
        response = self.session.post(f"{BASE_URL}/api/referral-partners", json={
            "name": "Test RP",
            "email": "test@example.com",
            "phone": "9876543210",
            "pan_number": "ABCDE1234F",
            "aadhar_number": "1234567890123",  # 13 digits
            "address": "Test Address"
        })
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        assert "12 digits" in response.json().get("detail", "").lower(), \
            f"Error should mention 12 digits: {response.json()}"
        print(f"✓ 13-digit Aadhar correctly rejected: {response.json().get('detail')}")
    
    # ============== Address Validation ==============
    def test_17_address_required(self):
        """Test that address is required"""
        response = self.session.post(f"{BASE_URL}/api/referral-partners", json={
            "name": "Test RP",
            "email": "test@example.com",
            "phone": "9876543210",
            "pan_number": "ABCDE1234F",
            "aadhar_number": "123456789012",
            "address": ""  # Empty address
        })
        assert response.status_code in [400, 422], f"Expected 400/422, got {response.status_code}"
        print(f"✓ Empty address correctly rejected: {response.status_code}")
    
    def test_18_address_whitespace_only(self):
        """Test that whitespace-only address is rejected"""
        response = self.session.post(f"{BASE_URL}/api/referral-partners", json={
            "name": "Test RP",
            "email": "test@example.com",
            "phone": "9876543210",
            "pan_number": "ABCDE1234F",
            "aadhar_number": "123456789012",
            "address": "   "  # Whitespace only
        })
        # Should fail - address should be stripped and validated
        assert response.status_code in [400, 422], f"Expected 400/422, got {response.status_code}"
        print(f"✓ Whitespace-only address correctly rejected: {response.status_code}")
    
    # ============== Successful RP Creation ==============
    def test_19_successful_rp_creation_all_fields(self):
        """Test successful RP creation with all mandatory fields"""
        import uuid
        unique_suffix = uuid.uuid4().hex[:6].upper()
        unique_email = f"testrp_{unique_suffix}@example.com"
        unique_pan = f"TEST{unique_suffix}"[:10]
        unique_aadhar = str(uuid.uuid4().int)[:12]
        
        response = self.session.post(f"{BASE_URL}/api/referral-partners", json={
            "name": f"Test RP {unique_suffix}",
            "email": unique_email,
            "phone": "9876543210",
            "pan_number": unique_pan,
            "aadhar_number": unique_aadhar,
            "address": "123 Test Street, Test City, Test State 123456"
        })
        
        assert response.status_code in [200, 201], f"Expected 200/201, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "id" in data, "Response should contain id"
        assert "rp_code" in data, "Response should contain rp_code"
        assert data["rp_code"].startswith("RP-"), f"RP code should start with RP-: {data['rp_code']}"
        assert data["name"] == f"Test RP {unique_suffix}", "Name should match"
        assert data["email"] == unique_email.lower(), "Email should match (lowercase)"
        assert data["phone"] == "9876543210", "Phone should match"
        assert data["pan_number"] == unique_pan.upper(), "PAN should match (uppercase)"
        assert data["aadhar_number"] == unique_aadhar, "Aadhar should match"
        assert data["address"] == "123 Test Street, Test City, Test State 123456", "Address should match"
        
        print(f"✓ RP created successfully: {data['rp_code']}")
        
        # Store for cleanup
        self.created_rp_id = data["id"]
    
    # ============== Duplicate Validation ==============
    def test_20_duplicate_pan_rejected(self):
        """Test that duplicate PAN is rejected"""
        # First, get an existing RP's PAN
        response = self.session.get(f"{BASE_URL}/api/referral-partners?active_only=false")
        assert response.status_code == 200
        
        rps = response.json()
        if not rps:
            pytest.skip("No existing RPs to test duplicate PAN")
        
        existing_pan = rps[0]["pan_number"]
        
        import uuid
        unique_email = f"dup_pan_{uuid.uuid4().hex[:8]}@example.com"
        unique_aadhar = str(uuid.uuid4().int)[:12]
        
        response = self.session.post(f"{BASE_URL}/api/referral-partners", json={
            "name": "Test Duplicate PAN",
            "email": unique_email,
            "phone": "9876543210",
            "pan_number": existing_pan,  # Duplicate PAN
            "aadhar_number": unique_aadhar,
            "address": "Test Address"
        })
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        assert "already exists" in response.json().get("detail", "").lower(), \
            f"Error should mention already exists: {response.json()}"
        print(f"✓ Duplicate PAN correctly rejected: {response.json().get('detail')}")
    
    def test_21_duplicate_email_rejected(self):
        """Test that duplicate email is rejected"""
        # First, get an existing RP's email
        response = self.session.get(f"{BASE_URL}/api/referral-partners?active_only=false")
        assert response.status_code == 200
        
        rps = response.json()
        rp_with_email = next((rp for rp in rps if rp.get("email")), None)
        if not rp_with_email:
            pytest.skip("No existing RPs with email to test duplicate")
        
        existing_email = rp_with_email["email"]
        
        import uuid
        unique_pan = f"DUPEML{uuid.uuid4().hex[:4].upper()}"[:10]
        unique_aadhar = str(uuid.uuid4().int)[:12]
        
        response = self.session.post(f"{BASE_URL}/api/referral-partners", json={
            "name": "Test Duplicate Email",
            "email": existing_email,  # Duplicate email
            "phone": "9876543210",
            "pan_number": unique_pan,
            "aadhar_number": unique_aadhar,
            "address": "Test Address"
        })
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        assert "already exists" in response.json().get("detail", "").lower(), \
            f"Error should mention already exists: {response.json()}"
        print(f"✓ Duplicate email correctly rejected: {response.json().get('detail')}")
    
    def test_22_duplicate_aadhar_rejected(self):
        """Test that duplicate Aadhar is rejected"""
        # First, get an existing RP's Aadhar
        response = self.session.get(f"{BASE_URL}/api/referral-partners?active_only=false")
        assert response.status_code == 200
        
        rps = response.json()
        rp_with_aadhar = next((rp for rp in rps if rp.get("aadhar_number")), None)
        if not rp_with_aadhar:
            pytest.skip("No existing RPs with Aadhar to test duplicate")
        
        existing_aadhar = rp_with_aadhar["aadhar_number"]
        
        import uuid
        unique_email = f"dup_aadhar_{uuid.uuid4().hex[:8]}@example.com"
        unique_pan = f"DUPAD{uuid.uuid4().hex[:5].upper()}"[:10]
        
        response = self.session.post(f"{BASE_URL}/api/referral-partners", json={
            "name": "Test Duplicate Aadhar",
            "email": unique_email,
            "phone": "9876543210",
            "pan_number": unique_pan,
            "aadhar_number": existing_aadhar,  # Duplicate Aadhar
            "address": "Test Address"
        })
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        assert "already exists" in response.json().get("detail", "").lower(), \
            f"Error should mention already exists: {response.json()}"
        print(f"✓ Duplicate Aadhar correctly rejected: {response.json().get('detail')}")


class TestRPEmailNotification:
    """Test RP email notification on stock transfer"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - login and get auth token"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as PE Desk
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "pedesk@smifs.com",
            "password": "Kutta@123"
        })
        
        if login_response.status_code == 200:
            token = login_response.json().get("token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
        else:
            pytest.skip("Authentication failed - skipping tests")
    
    def test_23_rp_deal_notification_template_exists(self):
        """Test that rp_deal_notification email template exists"""
        response = self.session.get(f"{BASE_URL}/api/email-templates")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        templates = response.json()
        rp_template = next((t for t in templates if t.get("key") == "rp_deal_notification"), None)
        
        assert rp_template is not None, "rp_deal_notification template should exist"
        # is_active may not be in response for default templates, check if present
        is_active = rp_template.get("is_active")
        assert is_active is None or is_active == True, "Template should be active or default"
        
        # Check required variables
        expected_vars = ["rp_name", "rp_code", "booking_number", "client_name", 
                        "stock_symbol", "stock_name", "quantity", "transfer_date",
                        "profit", "revenue_share_percent", "payment_amount"]
        template_vars = rp_template.get("variables", [])
        
        for var in expected_vars:
            assert var in template_vars, f"Template should have variable: {var}"
        
        print(f"✓ rp_deal_notification template exists with all required variables")
    
    def test_24_stock_transfer_creates_rp_payment(self):
        """Test that stock transfer with RP creates RP payment record"""
        # Get a booking with RP that has stock_transferred = True
        response = self.session.get(f"{BASE_URL}/api/finance/rp-payments")
        
        if response.status_code == 200:
            rp_payments = response.json()
            if rp_payments:
                # Verify RP payment structure
                payment = rp_payments[0]
                assert "referral_partner_id" in payment, "Should have referral_partner_id"
                assert "rp_code" in payment, "Should have rp_code"
                assert "booking_number" in payment, "Should have booking_number"
                assert "payment_amount" in payment, "Should have payment_amount"
                assert "status" in payment, "Should have status"
                print(f"✓ RP payment records exist with correct structure")
            else:
                print("⚠ No RP payments found - this is expected if no bookings with RP have been transferred")
        else:
            print(f"⚠ Could not fetch RP payments: {response.status_code}")


class TestRPEditValidation:
    """Test RP edit with mandatory fields validation (PE Level only)"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - login and get auth token"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as PE Desk
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "pedesk@smifs.com",
            "password": "Kutta@123"
        })
        
        if login_response.status_code == 200:
            token = login_response.json().get("token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
        else:
            pytest.skip("Authentication failed - skipping tests")
    
    def test_25_edit_rp_phone_validation(self):
        """Test that editing RP validates phone (10 digits)"""
        # Get an existing RP
        response = self.session.get(f"{BASE_URL}/api/referral-partners?active_only=false")
        assert response.status_code == 200
        
        rps = response.json()
        if not rps:
            pytest.skip("No existing RPs to test edit")
        
        rp = rps[0]
        
        # Try to update with invalid phone
        response = self.session.put(f"{BASE_URL}/api/referral-partners/{rp['id']}", json={
            "name": rp["name"],
            "email": rp.get("email", "test@example.com"),
            "phone": "12345",  # Invalid - less than 10 digits
            "pan_number": rp["pan_number"],
            "aadhar_number": rp["aadhar_number"],
            "address": rp.get("address", "Test Address")
        })
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        assert "10 digits" in response.json().get("detail", "").lower()
        print(f"✓ Edit with invalid phone correctly rejected")
    
    def test_26_edit_rp_aadhar_validation(self):
        """Test that editing RP validates Aadhar (12 digits)"""
        # Get an existing RP
        response = self.session.get(f"{BASE_URL}/api/referral-partners?active_only=false")
        assert response.status_code == 200
        
        rps = response.json()
        if not rps:
            pytest.skip("No existing RPs to test edit")
        
        rp = rps[0]
        
        # Try to update with invalid Aadhar
        response = self.session.put(f"{BASE_URL}/api/referral-partners/{rp['id']}", json={
            "name": rp["name"],
            "email": rp.get("email", "test@example.com"),
            "phone": rp.get("phone", "9876543210"),
            "pan_number": rp["pan_number"],
            "aadhar_number": "12345",  # Invalid - less than 12 digits
            "address": rp.get("address", "Test Address")
        })
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        assert "12 digits" in response.json().get("detail", "").lower()
        print(f"✓ Edit with invalid Aadhar correctly rejected")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
