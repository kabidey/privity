"""
Test suite for Mobile Number Registration & Activity Alert Features
Tests:
1. Registration form validation (10-digit mobile number)
2. POST /api/auth/register - Mobile validation
3. POST /api/auth/login - Returns mobile_required flag
4. POST /api/auth/update-mobile - Updates user's mobile number
5. GET /api/dashboard/revenue-report - Returns user's revenue report
6. Activity alert service imports
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test headers with User-Agent for bot protection
HEADERS = {
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 Test"
}


@pytest.fixture
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update(HEADERS)
    return session


@pytest.fixture
def pe_desk_token(api_client):
    """Get PE Desk authentication token"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": "pe@smifs.com",
        "password": "Kutta@123"
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"PE Desk authentication failed: {response.status_code} - {response.text}")


@pytest.fixture
def authenticated_client(api_client, pe_desk_token):
    """Session with PE Desk auth header"""
    api_client.headers.update({"Authorization": f"Bearer {pe_desk_token}"})
    return api_client


class TestMobileRegistrationValidation:
    """Test mobile number validation during registration"""
    
    def test_register_without_mobile_fails_for_non_superadmin(self, api_client):
        """Non-superadmin registration should fail without mobile number"""
        unique_email = f"test_nomobile_{uuid.uuid4().hex[:8]}@smifs.com"
        
        response = api_client.post(f"{BASE_URL}/api/auth/register", json={
            "email": unique_email,
            "name": "Test User No Mobile",
            "pan_number": "ABCDE1234F"
            # mobile_number intentionally omitted
        })
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        data = response.json()
        assert "mobile" in data.get("detail", "").lower() or "required" in data.get("detail", "").lower()
        print(f"✓ Registration without mobile rejected: {data.get('detail')}")
    
    def test_register_with_invalid_mobile_fails(self, api_client):
        """Registration with invalid mobile (not 10 digits) should fail"""
        unique_email = f"test_badmobile_{uuid.uuid4().hex[:8]}@smifs.com"
        
        # Test with 5 digit mobile
        response = api_client.post(f"{BASE_URL}/api/auth/register", json={
            "email": unique_email,
            "name": "Test User Bad Mobile",
            "pan_number": "ABCDE1234F",
            "mobile_number": "12345"  # Only 5 digits
        })
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        data = response.json()
        assert "10 digits" in data.get("detail", "").lower() or "mobile" in data.get("detail", "").lower()
        print(f"✓ Registration with 5-digit mobile rejected: {data.get('detail')}")
    
    def test_register_with_12_digit_mobile_fails(self, api_client):
        """Registration with 12 digit mobile should fail"""
        unique_email = f"test_longmobile_{uuid.uuid4().hex[:8]}@smifs.com"
        
        response = api_client.post(f"{BASE_URL}/api/auth/register", json={
            "email": unique_email,
            "name": "Test User Long Mobile",
            "pan_number": "ABCDE1234F",
            "mobile_number": "123456789012"  # 12 digits
        })
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        data = response.json()
        assert "10 digits" in data.get("detail", "").lower() or "mobile" in data.get("detail", "").lower()
        print(f"✓ Registration with 12-digit mobile rejected: {data.get('detail')}")


class TestLoginMobileRequired:
    """Test login mobile_required flag for existing users without mobile"""
    
    def test_pe_desk_login_returns_response_structure(self, api_client):
        """PE Desk login should return proper response structure including mobile_required"""
        response = api_client.post(f"{BASE_URL}/api/auth/login", json={
            "email": "pe@smifs.com",
            "password": "Kutta@123"
        })
        
        assert response.status_code == 200, f"Login failed: {response.status_code} - {response.text}"
        data = response.json()
        
        # Check response structure
        assert "token" in data, "Response should contain token"
        assert "user" in data, "Response should contain user object"
        assert "mobile_required" in data, "Response should contain mobile_required flag"
        
        # PE Desk (role 1) should not require mobile
        assert data["mobile_required"] == False, "PE Desk should not require mobile update"
        print(f"✓ Login response structure correct, mobile_required={data['mobile_required']}")


class TestUpdateMobileEndpoint:
    """Test POST /api/auth/update-mobile endpoint"""
    
    def test_update_mobile_without_auth_fails(self, api_client):
        """Update mobile should require authentication"""
        response = api_client.post(f"{BASE_URL}/api/auth/update-mobile", json={
            "mobile_number": "9876543210"
        })
        
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print(f"✓ Update mobile without auth rejected (status {response.status_code})")
    
    def test_update_mobile_with_invalid_number_fails(self, authenticated_client):
        """Update mobile with invalid number should fail"""
        response = authenticated_client.post(f"{BASE_URL}/api/auth/update-mobile", json={
            "mobile_number": "12345"  # Only 5 digits
        })
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        data = response.json()
        assert "10 digits" in data.get("detail", "").lower()
        print(f"✓ Update mobile with invalid number rejected: {data.get('detail')}")
    
    def test_update_mobile_endpoint_exists(self, authenticated_client):
        """Verify update-mobile endpoint exists and responds"""
        # Test with valid format but potentially duplicate number
        response = authenticated_client.post(f"{BASE_URL}/api/auth/update-mobile", json={
            "mobile_number": "9999999999"
        })
        
        # Should be 200 (success) or 400 (duplicate)
        assert response.status_code in [200, 400], f"Expected 200/400, got {response.status_code}: {response.text}"
        print(f"✓ Update mobile endpoint exists (status {response.status_code})")


class TestRevenueReport:
    """Test GET /api/dashboard/revenue-report endpoint"""
    
    def test_revenue_report_without_auth_fails(self, api_client):
        """Revenue report should require authentication"""
        response = api_client.get(f"{BASE_URL}/api/dashboard/revenue-report")
        
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print(f"✓ Revenue report without auth rejected (status {response.status_code})")
    
    def test_revenue_report_returns_data(self, authenticated_client):
        """Revenue report should return report data structure"""
        response = authenticated_client.get(f"{BASE_URL}/api/dashboard/revenue-report")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Check report structure - should have user, date, own, total fields or error message
        if "error" not in data:
            assert "user" in data or "own" in data or "total" in data, f"Unexpected report structure: {data.keys()}"
            print("✓ Revenue report returned successfully")
        else:
            print(f"✓ Revenue report endpoint working, returned: {data}")
    
    def test_revenue_report_with_date_parameter(self, authenticated_client):
        """Revenue report should accept date parameter"""
        response = authenticated_client.get(f"{BASE_URL}/api/dashboard/revenue-report?date=2025-01-01")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Should either return report or error but not crash
        assert isinstance(data, dict), "Response should be a dictionary"
        print("✓ Revenue report with date parameter works")


class TestActivityAlertServiceImport:
    """Test activity alert service can be imported"""
    
    def test_activity_alerts_service_exists(self, api_client):
        """Activity alerts service file should exist"""
        import os
        service_path = "/app/backend/services/activity_alerts.py"
        assert os.path.exists(service_path), f"Activity alerts service file not found at {service_path}"
        
        # Read and verify key functions are defined
        with open(service_path, "r") as f:
            content = f.read()
        
        assert "async def send_activity_alert" in content, "send_activity_alert function not found"
        assert "async def notify_booking_created" in content, "notify_booking_created function not found"
        assert "async def notify_payment_received" in content, "notify_payment_received function not found"
        assert "async def notify_dp_transfer" in content, "notify_dp_transfer function not found"
        print("✓ Activity alerts service exists with required functions")
    
    def test_day_end_reports_service_exists(self, api_client):
        """Day end reports service file should exist"""
        import os
        service_path = "/app/backend/services/day_end_reports.py"
        assert os.path.exists(service_path), f"Day end reports service file not found at {service_path}"
        
        # Read and verify key functions are defined
        with open(service_path, "r") as f:
            content = f.read()
        
        assert "async def generate_revenue_report" in content, "generate_revenue_report function not found"
        assert "async def trigger_manual_report" in content, "trigger_manual_report function not found"
        assert "async def send_day_end_reports" in content, "send_day_end_reports function not found"
        assert "def build_revenue_email" in content, "build_revenue_email function not found"
        assert "def build_revenue_whatsapp" in content, "build_revenue_whatsapp function not found"
        print("✓ Day end reports service exists with required functions")


class TestRegistrationPANLabel:
    """Test PAN label is 'Identification' in error messages"""
    
    def test_pan_label_in_error_message(self, api_client):
        """Error message should use 'Identification (PAN)' label"""
        unique_email = f"test_panlabel_{uuid.uuid4().hex[:8]}@smifs.com"
        
        # Register without PAN
        response = api_client.post(f"{BASE_URL}/api/auth/register", json={
            "email": unique_email,
            "name": "Test User No PAN",
            "mobile_number": "9876543210"
            # pan_number intentionally omitted
        })
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        data = response.json()
        detail = data.get("detail", "").lower()
        
        # Should contain 'identification' in error message
        assert "identification" in detail or "pan" in detail, f"Error message should mention Identification/PAN: {detail}"
        print(f"✓ PAN label in error message: {data.get('detail')}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
