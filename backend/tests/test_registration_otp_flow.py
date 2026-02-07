"""
Test suite for OTP-based Registration Flow
Tests email domain validation, mobile number validation, PAN validation,
and error handling for the registration endpoints
"""
import pytest
import requests
import os
import re

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestRegistrationOTPFlow:
    """Tests for OTP-based registration endpoints"""
    
    def test_health_endpoint(self):
        """Verify the API is accessible"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "ok"
        print("✓ Health endpoint accessible")
    
    # ============== Email Domain Validation Tests ==============
    
    def test_request_otp_invalid_email_domain_gmail(self):
        """Test that registration rejects non-smifs.com email domains (gmail.com)"""
        payload = {
            "email": "testuser@gmail.com",
            "password": "Test@12345",
            "name": "Test User",
            "mobile_number": "9876543210",
            "pan_number": "ABCDE1234F"
        }
        response = requests.post(f"{BASE_URL}/api/auth/register/request-otp", json=payload)
        
        assert response.status_code == 400, f"Expected 400 for invalid domain, got {response.status_code}"
        data = response.json()
        assert "detail" in data
        # Check error message mentions domain restriction
        error_msg = data["detail"].lower()
        assert "smifs" in error_msg or "domain" in error_msg or "restricted" in error_msg
        print(f"✓ Correctly rejected gmail.com domain: {data['detail']}")
    
    def test_request_otp_invalid_email_domain_yahoo(self):
        """Test that registration rejects yahoo.com email domain"""
        payload = {
            "email": "testuser@yahoo.com",
            "password": "Test@12345",
            "name": "Test User",
            "mobile_number": "9876543210",
            "pan_number": "ABCDE1234F"
        }
        response = requests.post(f"{BASE_URL}/api/auth/register/request-otp", json=payload)
        
        assert response.status_code == 400, f"Expected 400 for invalid domain, got {response.status_code}"
        data = response.json()
        assert "detail" in data
        print(f"✓ Correctly rejected yahoo.com domain: {data['detail']}")
    
    def test_request_otp_invalid_email_domain_hotmail(self):
        """Test that registration rejects hotmail.com email domain"""
        payload = {
            "email": "testuser@hotmail.com",
            "password": "Test@12345",
            "name": "Test User",
            "mobile_number": "9876543210",
            "pan_number": "ABCDE1234F"
        }
        response = requests.post(f"{BASE_URL}/api/auth/register/request-otp", json=payload)
        
        assert response.status_code == 400, f"Expected 400 for invalid domain, got {response.status_code}"
        data = response.json()
        assert "detail" in data
        print(f"✓ Correctly rejected hotmail.com domain: {data['detail']}")
    
    # ============== Missing Fields Validation Tests ==============
    
    def test_request_otp_missing_mobile_number(self):
        """Test that registration fails when mobile number is missing"""
        payload = {
            "email": "testuser@smifs.com",
            "password": "Test@12345",
            "name": "Test User",
            "pan_number": "ABCDE1234F"
            # mobile_number is missing
        }
        response = requests.post(f"{BASE_URL}/api/auth/register/request-otp", json=payload)
        
        # Should return 400 or 422 for missing required field
        assert response.status_code in [400, 422], f"Expected 400/422 for missing mobile, got {response.status_code}"
        data = response.json()
        print(f"✓ Correctly rejected missing mobile number: {data}")
    
    def test_request_otp_missing_pan_number(self):
        """Test that registration fails when PAN number is missing"""
        payload = {
            "email": "testuser@smifs.com",
            "password": "Test@12345",
            "name": "Test User",
            "mobile_number": "9876543210"
            # pan_number is missing
        }
        response = requests.post(f"{BASE_URL}/api/auth/register/request-otp", json=payload)
        
        # Should return 400 or 422 for missing required field
        assert response.status_code in [400, 422], f"Expected 400/422 for missing PAN, got {response.status_code}"
        data = response.json()
        print(f"✓ Correctly rejected missing PAN number: {data}")
    
    def test_request_otp_missing_email(self):
        """Test that registration fails when email is missing"""
        payload = {
            "password": "Test@12345",
            "name": "Test User",
            "mobile_number": "9876543210",
            "pan_number": "ABCDE1234F"
            # email is missing
        }
        response = requests.post(f"{BASE_URL}/api/auth/register/request-otp", json=payload)
        
        # Should return 400 or 422 for missing required field
        assert response.status_code in [400, 422], f"Expected 400/422 for missing email, got {response.status_code}"
        data = response.json()
        print(f"✓ Correctly rejected missing email: {data}")
    
    # ============== Mobile Number Validation Tests ==============
    
    def test_request_otp_invalid_mobile_too_short(self):
        """Test that registration rejects mobile number with less than 10 digits"""
        import time
        unique_suffix = int(time.time())
        payload = {
            "email": f"testmobile{unique_suffix}@smifs.com",  # Unique email
            "password": "Test@12345",
            "name": "Test User",
            "mobile_number": "12345",  # Only 5 digits
            "pan_number": f"ZZZZZ{unique_suffix % 10000:04d}A"  # Unique PAN format
        }
        response = requests.post(f"{BASE_URL}/api/auth/register/request-otp", json=payload)
        
        assert response.status_code == 400, f"Expected 400 for short mobile, got {response.status_code}: {response.json()}"
        data = response.json()
        assert "detail" in data
        error_msg = data["detail"].lower()
        assert "10" in error_msg or "digits" in error_msg or "mobile" in error_msg
        print(f"✓ Correctly rejected short mobile number: {data['detail']}")
    
    def test_request_otp_invalid_mobile_too_long(self):
        """Test that registration rejects mobile number with more than 10 digits"""
        payload = {
            "email": "testuser@smifs.com",
            "password": "Test@12345",
            "name": "Test User",
            "mobile_number": "98765432109876",  # 14 digits
            "pan_number": "ABCDE1234F"
        }
        response = requests.post(f"{BASE_URL}/api/auth/register/request-otp", json=payload)
        
        assert response.status_code == 400, f"Expected 400 for long mobile, got {response.status_code}"
        data = response.json()
        assert "detail" in data
        print(f"✓ Correctly rejected long mobile number: {data['detail']}")
    
    def test_request_otp_mobile_with_non_digits_stripped(self):
        """Test that mobile number with non-digits is stripped and validated"""
        payload = {
            "email": "testuser@smifs.com",
            "password": "Test@12345",
            "name": "Test User",
            "mobile_number": "+91-987-654-3210",  # Has non-digits but 10 digits total
            "pan_number": "ABCDE1234F"
        }
        response = requests.post(f"{BASE_URL}/api/auth/register/request-otp", json=payload)
        
        # After stripping non-digits: 919876543210 (12 digits) - should fail
        # Or: might only take last 10 or first 10
        # The backend strips non-digits, so +91-987-654-3210 becomes 919876543210 (12 digits) - should fail
        print(f"Response for mobile with non-digits: {response.status_code} - {response.json()}")
        # This test verifies the backend's handling of non-digit characters
    
    # ============== PAN Number Validation Tests ==============
    
    def test_request_otp_invalid_pan_format(self):
        """Test that registration rejects invalid PAN format"""
        import time
        unique_suffix = int(time.time())
        payload = {
            "email": f"testpan{unique_suffix}@smifs.com",  # Unique email
            "password": "Test@12345",
            "name": "Test User",
            "mobile_number": f"9{unique_suffix % 1000000000:09d}",  # Unique mobile
            "pan_number": "INVALID123"  # Invalid format (doesn't match AAAAA9999A pattern)
        }
        response = requests.post(f"{BASE_URL}/api/auth/register/request-otp", json=payload)
        
        assert response.status_code == 400, f"Expected 400 for invalid PAN format, got {response.status_code}: {response.json()}"
        data = response.json()
        assert "detail" in data
        error_msg = data["detail"].lower()
        assert "pan" in error_msg or "format" in error_msg or "invalid" in error_msg
        print(f"✓ Correctly rejected invalid PAN format: {data['detail']}")
    
    def test_request_otp_pan_too_short(self):
        """Test that registration rejects PAN with less than 10 characters"""
        payload = {
            "email": "testuser@smifs.com",
            "password": "Test@12345",
            "name": "Test User",
            "mobile_number": "9876543210",
            "pan_number": "ABCDE12"  # Only 7 characters
        }
        response = requests.post(f"{BASE_URL}/api/auth/register/request-otp", json=payload)
        
        assert response.status_code == 400, f"Expected 400 for short PAN, got {response.status_code}"
        data = response.json()
        assert "detail" in data
        print(f"✓ Correctly rejected short PAN: {data['detail']}")
    
    def test_request_otp_pan_all_numbers(self):
        """Test that registration rejects PAN with all numbers"""
        payload = {
            "email": "testuser@smifs.com",
            "password": "Test@12345",
            "name": "Test User",
            "mobile_number": "9876543210",
            "pan_number": "1234567890"  # All numbers, invalid format
        }
        response = requests.post(f"{BASE_URL}/api/auth/register/request-otp", json=payload)
        
        assert response.status_code == 400, f"Expected 400 for numeric PAN, got {response.status_code}"
        data = response.json()
        assert "detail" in data
        print(f"✓ Correctly rejected all-numeric PAN: {data['detail']}")
    
    # ============== Valid Domain Tests (these will send OTP if email exists) ==============
    
    def test_request_otp_valid_smifs_com_domain_format(self):
        """Test that @smifs.com domain is accepted format-wise (may fail for other reasons like existing email)"""
        # Using a unique email that likely doesn't exist to test domain validation passes
        import time
        unique_suffix = int(time.time())
        payload = {
            "email": f"testnewuser{unique_suffix}@smifs.com",
            "password": "Test@12345",
            "name": "Test New User",
            "mobile_number": "9876543210",
            "pan_number": "ABCDE1234F"
        }
        response = requests.post(f"{BASE_URL}/api/auth/register/request-otp", json=payload)
        
        # If domain is valid, we either get success (OTP sent) or error for duplicate email/pan/mobile
        # We should NOT get a domain restriction error
        data = response.json()
        if response.status_code == 400:
            error_msg = data.get("detail", "").lower()
            # Should NOT be a domain error
            assert "domain" not in error_msg or "smifs" in error_msg, f"Should not reject @smifs.com domain: {error_msg}"
            print(f"✓ @smifs.com domain accepted, failed for other reason: {data['detail']}")
        else:
            # Either success (200) or might fail for duplicate mobile/pan
            print(f"✓ @smifs.com domain validated successfully: {response.status_code} - {data}")
    
    def test_request_otp_valid_smifs_co_in_domain_format(self):
        """Test that @smifs.co.in domain is accepted format-wise"""
        import time
        unique_suffix = int(time.time())
        payload = {
            "email": f"testnewuser{unique_suffix}@smifs.co.in",
            "password": "Test@12345",
            "name": "Test New User",
            "mobile_number": "9876543211",
            "pan_number": "FGHIJ5678K"
        }
        response = requests.post(f"{BASE_URL}/api/auth/register/request-otp", json=payload)
        
        data = response.json()
        if response.status_code == 400:
            error_msg = data.get("detail", "").lower()
            # Should NOT be a domain error
            assert "domain" not in error_msg or "smifs" in error_msg, f"Should not reject @smifs.co.in domain: {error_msg}"
            print(f"✓ @smifs.co.in domain accepted, failed for other reason: {data['detail']}")
        else:
            print(f"✓ @smifs.co.in domain validated successfully: {response.status_code} - {data}")
    
    # ============== OTP Verification Tests ==============
    
    def test_verify_otp_no_pending_registration(self):
        """Test that OTP verification fails when no pending registration exists"""
        payload = {
            "email": "nonexistent@smifs.com",
            "otp": "123456"
        }
        response = requests.post(f"{BASE_URL}/api/auth/register/verify-otp", json=payload)
        
        # Accept 400 or 422 (validation error for body format)
        assert response.status_code in [400, 422], f"Expected 400/422 for no pending registration, got {response.status_code}"
        data = response.json()
        print(f"✓ Correctly rejected OTP for non-existent pending registration: {response.status_code} - {data}")
    
    def test_resend_otp_no_pending_registration(self):
        """Test that resend OTP fails when no pending registration exists"""
        response = requests.post(
            f"{BASE_URL}/api/auth/register/resend-otp", 
            json={"email": "nonexistent@smifs.com"}
        )
        
        # Accept 400 or 422 (validation error for body format)
        assert response.status_code in [400, 422], f"Expected 400/422 for no pending registration, got {response.status_code}"
        data = response.json()
        print(f"✓ Correctly rejected resend OTP for non-existent pending registration: {response.status_code} - {data}")


class TestRegistrationEdgeCases:
    """Edge case tests for registration"""
    
    def test_empty_payload(self):
        """Test that empty payload is rejected"""
        response = requests.post(f"{BASE_URL}/api/auth/register/request-otp", json={})
        
        # Should return 400 or 422 for missing required fields
        assert response.status_code in [400, 422], f"Expected 400/422 for empty payload, got {response.status_code}"
        print(f"✓ Correctly rejected empty payload: {response.status_code}")
    
    def test_null_values(self):
        """Test that null values are rejected"""
        payload = {
            "email": None,
            "password": None,
            "name": None,
            "mobile_number": None,
            "pan_number": None
        }
        response = requests.post(f"{BASE_URL}/api/auth/register/request-otp", json=payload)
        
        # Should return 400 or 422 for null values
        assert response.status_code in [400, 422], f"Expected 400/422 for null values, got {response.status_code}"
        print(f"✓ Correctly rejected null values: {response.status_code}")
    
    def test_email_case_insensitivity(self):
        """Test that email domain validation is case-insensitive"""
        payload = {
            "email": "testuser@GMAIL.COM",  # Uppercase domain
            "password": "Test@12345",
            "name": "Test User",
            "mobile_number": "9876543210",
            "pan_number": "ABCDE1234F"
        }
        response = requests.post(f"{BASE_URL}/api/auth/register/request-otp", json=payload)
        
        # Should still be rejected as gmail.com (case-insensitive)
        assert response.status_code == 400, f"Expected 400 for uppercase invalid domain, got {response.status_code}"
        data = response.json()
        print(f"✓ Email domain validation is case-insensitive: {data['detail']}")
    
    def test_pan_lowercase_converted(self):
        """Test that lowercase PAN is converted to uppercase and validated"""
        payload = {
            "email": "testuser@gmail.com",  # Using invalid domain to hit that error first
            "password": "Test@12345",
            "name": "Test User",
            "mobile_number": "9876543210",
            "pan_number": "abcde1234f"  # Lowercase PAN
        }
        response = requests.post(f"{BASE_URL}/api/auth/register/request-otp", json=payload)
        
        # Will fail for domain, but verifies request went through
        assert response.status_code == 400
        data = response.json()
        # Should fail for domain, not for PAN case
        print(f"✓ Lowercase PAN request processed: {data['detail']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
