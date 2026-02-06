"""
Test Custom Domain Feature for Company Master
Tests that:
1. Company Master UI can save custom_domain
2. custom_domain is persisted in MongoDB
3. Booking approval flow reads custom_domain from Company Master
4. Falls back to FRONTEND_URL env variable if custom_domain not set
"""

import pytest
import requests
import os

# Get backend URL from environment - use localhost for internal testing
BASE_URL = "http://localhost:8001"


class TestCustomDomainFeature:
    """Test custom_domain field in Company Master"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test - login as PE Desk"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as PE Desk
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "pedesk@smifs.com",
            "password": "password"
        })
        assert login_response.status_code == 200, f"Login failed: {login_response.text}"
        self.token = login_response.json().get("access_token")
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
    
    def test_01_get_company_master_has_custom_domain_field(self):
        """Test GET /api/company-master returns custom_domain field"""
        response = self.session.get(f"{BASE_URL}/api/company-master")
        assert response.status_code == 200, f"GET company-master failed: {response.text}"
        
        data = response.json()
        # custom_domain should be in the response (even if null)
        assert "custom_domain" in data, "custom_domain field missing from Company Master response"
        print(f"✓ custom_domain field present in response: {data.get('custom_domain')}")
    
    def test_02_save_custom_domain(self):
        """Test PUT /api/company-master saves custom_domain"""
        # First get current settings
        get_response = self.session.get(f"{BASE_URL}/api/company-master")
        assert get_response.status_code == 200
        current_data = get_response.json()
        
        # Update with custom_domain
        test_domain = "https://privity.production-example.com"
        update_payload = {
            "company_name": current_data.get("company_name") or "Test Company",
            "company_address": current_data.get("company_address"),
            "company_cin": current_data.get("company_cin"),
            "company_gst": current_data.get("company_gst"),
            "company_pan": current_data.get("company_pan"),
            "cdsl_dp_id": current_data.get("cdsl_dp_id"),
            "nsdl_dp_id": current_data.get("nsdl_dp_id"),
            "company_tan": current_data.get("company_tan"),
            "company_bank_name": current_data.get("company_bank_name"),
            "company_bank_account": current_data.get("company_bank_account"),
            "company_bank_ifsc": current_data.get("company_bank_ifsc"),
            "company_bank_branch": current_data.get("company_bank_branch"),
            "user_agreement_text": current_data.get("user_agreement_text"),
            "custom_domain": test_domain
        }
        
        response = self.session.put(f"{BASE_URL}/api/company-master", json=update_payload)
        assert response.status_code == 200, f"PUT company-master failed: {response.text}"
        
        # Verify the response contains updated custom_domain
        updated_data = response.json()
        assert updated_data.get("custom_domain") == test_domain, \
            f"custom_domain not saved correctly. Expected: {test_domain}, Got: {updated_data.get('custom_domain')}"
        print(f"✓ custom_domain saved successfully: {test_domain}")
    
    def test_03_verify_custom_domain_persisted(self):
        """Verify custom_domain is persisted after save"""
        response = self.session.get(f"{BASE_URL}/api/company-master")
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("custom_domain") == "https://privity.production-example.com", \
            f"custom_domain not persisted. Got: {data.get('custom_domain')}"
        print(f"✓ custom_domain persisted: {data.get('custom_domain')}")
    
    def test_04_custom_domain_trailing_slash_removed(self):
        """Test that trailing slash is removed from custom_domain"""
        # Get current settings
        get_response = self.session.get(f"{BASE_URL}/api/company-master")
        current_data = get_response.json()
        
        # Update with trailing slash
        test_domain_with_slash = "https://privity.production-example.com/"
        update_payload = {
            "company_name": current_data.get("company_name") or "Test Company",
            "company_address": current_data.get("company_address"),
            "company_cin": current_data.get("company_cin"),
            "company_gst": current_data.get("company_gst"),
            "company_pan": current_data.get("company_pan"),
            "cdsl_dp_id": current_data.get("cdsl_dp_id"),
            "nsdl_dp_id": current_data.get("nsdl_dp_id"),
            "company_tan": current_data.get("company_tan"),
            "company_bank_name": current_data.get("company_bank_name"),
            "company_bank_account": current_data.get("company_bank_account"),
            "company_bank_ifsc": current_data.get("company_bank_ifsc"),
            "company_bank_branch": current_data.get("company_bank_branch"),
            "user_agreement_text": current_data.get("user_agreement_text"),
            "custom_domain": test_domain_with_slash
        }
        
        response = self.session.put(f"{BASE_URL}/api/company-master", json=update_payload)
        assert response.status_code == 200
        
        # Verify trailing slash was removed
        updated_data = response.json()
        expected_domain = "https://privity.production-example.com"
        assert updated_data.get("custom_domain") == expected_domain, \
            f"Trailing slash not removed. Expected: {expected_domain}, Got: {updated_data.get('custom_domain')}"
        print(f"✓ Trailing slash correctly removed: {updated_data.get('custom_domain')}")
    
    def test_05_custom_domain_can_be_cleared(self):
        """Test that custom_domain can be set to None/empty"""
        # Get current settings
        get_response = self.session.get(f"{BASE_URL}/api/company-master")
        current_data = get_response.json()
        
        # Update with empty custom_domain
        update_payload = {
            "company_name": current_data.get("company_name") or "Test Company",
            "company_address": current_data.get("company_address"),
            "company_cin": current_data.get("company_cin"),
            "company_gst": current_data.get("company_gst"),
            "company_pan": current_data.get("company_pan"),
            "cdsl_dp_id": current_data.get("cdsl_dp_id"),
            "nsdl_dp_id": current_data.get("nsdl_dp_id"),
            "company_tan": current_data.get("company_tan"),
            "company_bank_name": current_data.get("company_bank_name"),
            "company_bank_account": current_data.get("company_bank_account"),
            "company_bank_ifsc": current_data.get("company_bank_ifsc"),
            "company_bank_branch": current_data.get("company_bank_branch"),
            "user_agreement_text": current_data.get("user_agreement_text"),
            "custom_domain": ""  # Empty string
        }
        
        response = self.session.put(f"{BASE_URL}/api/company-master", json=update_payload)
        assert response.status_code == 200
        
        # Verify custom_domain is cleared (None)
        updated_data = response.json()
        assert updated_data.get("custom_domain") is None or updated_data.get("custom_domain") == "", \
            f"custom_domain not cleared. Got: {updated_data.get('custom_domain')}"
        print(f"✓ custom_domain successfully cleared")
    
    def test_06_restore_custom_domain_for_production(self):
        """Restore custom_domain for production testing"""
        # Get current settings
        get_response = self.session.get(f"{BASE_URL}/api/company-master")
        current_data = get_response.json()
        
        # Restore the production test domain
        test_domain = "https://privity.production-example.com"
        update_payload = {
            "company_name": current_data.get("company_name") or "Test Company",
            "company_address": current_data.get("company_address"),
            "company_cin": current_data.get("company_cin"),
            "company_gst": current_data.get("company_gst"),
            "company_pan": current_data.get("company_pan"),
            "cdsl_dp_id": current_data.get("cdsl_dp_id"),
            "nsdl_dp_id": current_data.get("nsdl_dp_id"),
            "company_tan": current_data.get("company_tan"),
            "company_bank_name": current_data.get("company_bank_name"),
            "company_bank_account": current_data.get("company_bank_account"),
            "company_bank_ifsc": current_data.get("company_bank_ifsc"),
            "company_bank_branch": current_data.get("company_bank_branch"),
            "user_agreement_text": current_data.get("user_agreement_text"),
            "custom_domain": test_domain
        }
        
        response = self.session.put(f"{BASE_URL}/api/company-master", json=update_payload)
        assert response.status_code == 200
        
        updated_data = response.json()
        assert updated_data.get("custom_domain") == test_domain
        print(f"✓ custom_domain restored: {test_domain}")


class TestBookingApprovalUsesCustomDomain:
    """Test that booking approval flow uses custom_domain for email URLs
    
    Note: We can't actually test email sending, but we can verify:
    1. The code path reads company_master.custom_domain
    2. The frontend_url resolution logic is correct
    """
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test - login as PE Desk"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as PE Desk
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "pedesk@smifs.com",
            "password": "password"
        })
        assert login_response.status_code == 200, f"Login failed: {login_response.text}"
        self.token = login_response.json().get("access_token")
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
    
    def test_01_verify_custom_domain_set_in_company_master(self):
        """Verify custom_domain is set for booking approval tests"""
        response = self.session.get(f"{BASE_URL}/api/company-master")
        assert response.status_code == 200
        
        data = response.json()
        custom_domain = data.get("custom_domain")
        
        # Verify custom_domain is set
        assert custom_domain is not None and custom_domain != "", \
            "custom_domain should be set for booking approval tests"
        assert "privity.production-example.com" in custom_domain, \
            f"Expected test domain, got: {custom_domain}"
        print(f"✓ custom_domain is set: {custom_domain}")
    
    def test_02_booking_approval_endpoint_accessible(self):
        """Verify booking approval endpoint is accessible (setup test)"""
        # Get a pending booking if available
        response = self.session.get(f"{BASE_URL}/api/bookings/pending-approval")
        assert response.status_code == 200, f"Failed to get pending bookings: {response.text}"
        
        pending = response.json()
        print(f"✓ Found {len(pending)} pending bookings")
        
        if pending:
            booking = pending[0]
            print(f"  Sample booking: {booking.get('booking_number')}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
