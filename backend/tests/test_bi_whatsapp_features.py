"""
Test Suite for v6.2.4.7 Features:
1. BI Report Builder endpoints
2. WhatsApp Notification endpoints
3. BP Overrides count in PE Dashboard
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
HEADERS = {
    "User-Agent": "Mozilla/5.0 Test",
    "Content-Type": "application/json"
}

# Test credentials
PE_DESK_EMAIL = "pe@smifs.com"
PE_DESK_PASSWORD = "Kutta@123"


class TestAuthentication:
    """Authentication tests to get token for protected endpoints"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token for PE Desk user"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": PE_DESK_EMAIL, "password": PE_DESK_PASSWORD},
            headers=HEADERS
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "access_token" in data or "token" in data
        return data.get("access_token") or data.get("token")
    
    def test_login_success(self, auth_token):
        """Verify login returns valid token"""
        assert auth_token is not None
        assert len(auth_token) > 0
        print(f"PASS: Got auth token with length {len(auth_token)}")


class TestBIReportsAPI:
    """BI Report Builder API Tests"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": PE_DESK_EMAIL, "password": PE_DESK_PASSWORD},
            headers=HEADERS
        )
        assert response.status_code == 200
        data = response.json()
        return data.get("access_token") or data.get("token")
    
    def test_get_bi_reports_config(self, auth_token):
        """GET /api/bi-reports/config - Returns report types and configurations"""
        response = requests.get(
            f"{BASE_URL}/api/bi-reports/config",
            headers={**HEADERS, "Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        data = response.json()
        
        # Verify structure
        assert "report_types" in data, "Missing report_types key"
        assert "configs" in data, "Missing configs key"
        
        # Verify report types
        report_types = data["report_types"]
        assert len(report_types) >= 6, f"Expected at least 6 report types, got {len(report_types)}"
        
        # Check expected report types
        type_keys = [t["key"] for t in report_types]
        expected_types = ["bookings", "clients", "revenue", "inventory", "payments", "pnl"]
        for expected in expected_types:
            assert expected in type_keys, f"Missing report type: {expected}"
        
        # Verify configs have dimensions and metrics
        for report_type in expected_types:
            assert report_type in data["configs"], f"Missing config for {report_type}"
            config = data["configs"][report_type]
            assert "dimensions" in config, f"Missing dimensions for {report_type}"
            assert "metrics" in config, f"Missing metrics for {report_type}"
            assert "collection" in config, f"Missing collection for {report_type}"
        
        print(f"PASS: BI Reports config returned {len(report_types)} report types with proper structure")
    
    def test_generate_bookings_report(self, auth_token):
        """POST /api/bi-reports/generate - Generates report with dimensions and metrics"""
        payload = {
            "report_type": "bookings",
            "dimensions": ["approval_status"],
            "metrics": ["count"],
            "filters": [],
            "date_from": None,
            "date_to": None,
            "sort_by": "count",
            "sort_order": "desc",
            "limit": 100
        }
        
        response = requests.post(
            f"{BASE_URL}/api/bi-reports/generate",
            json=payload,
            headers={**HEADERS, "Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "report_type" in data
        assert "dimensions" in data
        assert "metrics" in data
        assert "total_rows" in data
        assert "data" in data
        assert "summary" in data
        assert "generated_at" in data
        
        assert data["report_type"] == "bookings"
        assert isinstance(data["data"], list)
        
        print(f"PASS: Generated bookings report with {data['total_rows']} rows")
    
    def test_generate_clients_report(self, auth_token):
        """Test generating clients report"""
        payload = {
            "report_type": "clients",
            "dimensions": ["approval_status"],
            "metrics": ["count"],
            "filters": [],
            "limit": 50
        }
        
        response = requests.post(
            f"{BASE_URL}/api/bi-reports/generate",
            json=payload,
            headers={**HEADERS, "Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        data = response.json()
        assert data["report_type"] == "clients"
        print(f"PASS: Generated clients report with {data['total_rows']} rows")
    
    def test_generate_revenue_report(self, auth_token):
        """Test generating revenue report"""
        payload = {
            "report_type": "revenue",
            "dimensions": ["created_by_name"],
            "metrics": ["count", "company_revenue"],
            "filters": [],
            "limit": 50
        }
        
        response = requests.post(
            f"{BASE_URL}/api/bi-reports/generate",
            json=payload,
            headers={**HEADERS, "Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        data = response.json()
        assert data["report_type"] == "revenue"
        print(f"PASS: Generated revenue report with {data['total_rows']} rows")
    
    def test_generate_inventory_report(self, auth_token):
        """Test generating inventory report"""
        payload = {
            "report_type": "inventory",
            "dimensions": ["stock_symbol"],
            "metrics": ["available_quantity"],
            "filters": [],
            "limit": 50
        }
        
        response = requests.post(
            f"{BASE_URL}/api/bi-reports/generate",
            json=payload,
            headers={**HEADERS, "Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        data = response.json()
        assert data["report_type"] == "inventory"
        print(f"PASS: Generated inventory report with {data['total_rows']} rows")
    
    def test_generate_payments_report(self, auth_token):
        """Test generating payments report"""
        payload = {
            "report_type": "payments",
            "dimensions": ["payment_status"],
            "metrics": ["count", "total_amount"],
            "filters": [],
            "limit": 50
        }
        
        response = requests.post(
            f"{BASE_URL}/api/bi-reports/generate",
            json=payload,
            headers={**HEADERS, "Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        data = response.json()
        assert data["report_type"] == "payments"
        print(f"PASS: Generated payments report with {data['total_rows']} rows")
    
    def test_generate_pnl_report(self, auth_token):
        """Test generating P&L report"""
        payload = {
            "report_type": "pnl",
            "dimensions": ["stock_symbol"],
            "metrics": ["count", "net_pnl"],
            "filters": [],
            "limit": 50
        }
        
        response = requests.post(
            f"{BASE_URL}/api/bi-reports/generate",
            json=payload,
            headers={**HEADERS, "Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        data = response.json()
        assert data["report_type"] == "pnl"
        print(f"PASS: Generated P&L report with {data['total_rows']} rows")
    
    def test_export_report_to_excel(self, auth_token):
        """POST /api/bi-reports/export - Exports report to Excel"""
        payload = {
            "report_type": "bookings",
            "dimensions": ["approval_status"],
            "metrics": ["count"],
            "filters": [],
            "limit": 100
        }
        
        response = requests.post(
            f"{BASE_URL}/api/bi-reports/export",
            json=payload,
            headers={**HEADERS, "Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        
        # Check content type
        content_type = response.headers.get("Content-Type", "")
        assert "spreadsheet" in content_type or "octet-stream" in content_type, \
            f"Expected Excel content type, got: {content_type}"
        
        # Check content disposition (download filename)
        content_disp = response.headers.get("Content-Disposition", "")
        assert "attachment" in content_disp.lower(), "Expected attachment in Content-Disposition"
        assert ".xlsx" in content_disp, "Expected .xlsx in filename"
        
        # Check file size
        assert len(response.content) > 0, "Empty Excel file returned"
        
        print(f"PASS: Excel export returned {len(response.content)} bytes")
    
    def test_invalid_report_type(self, auth_token):
        """Test error handling for invalid report type"""
        payload = {
            "report_type": "invalid_type",
            "dimensions": ["test"],
            "metrics": ["count"],
        }
        
        response = requests.post(
            f"{BASE_URL}/api/bi-reports/generate",
            json=payload,
            headers={**HEADERS, "Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print("PASS: Invalid report type correctly returns 400 error")
    
    def test_unauthorized_access(self):
        """Test that endpoints require authentication"""
        response = requests.get(
            f"{BASE_URL}/api/bi-reports/config",
            headers=HEADERS
        )
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("PASS: BI Reports config requires authentication")


class TestWhatsAppAPI:
    """WhatsApp Notification System API Tests"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": PE_DESK_EMAIL, "password": PE_DESK_PASSWORD},
            headers=HEADERS
        )
        assert response.status_code == 200
        data = response.json()
        return data.get("access_token") or data.get("token")
    
    def test_get_whatsapp_config(self, auth_token):
        """GET /api/whatsapp/config - Returns WhatsApp connection status"""
        response = requests.get(
            f"{BASE_URL}/api/whatsapp/config",
            headers={**HEADERS, "Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        data = response.json()
        
        # Config should have these fields
        assert "status" in data or "enabled" in data
        print(f"PASS: WhatsApp config returned with status: {data.get('status', data.get('enabled'))}")
    
    def test_get_whatsapp_templates(self, auth_token):
        """GET /api/whatsapp/templates - Returns message templates"""
        response = requests.get(
            f"{BASE_URL}/api/whatsapp/templates",
            headers={**HEADERS, "Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        data = response.json()
        
        # Should return list of templates
        assert isinstance(data, list), "Expected list of templates"
        
        # Verify default templates exist
        if len(data) > 0:
            template = data[0]
            assert "name" in template
            assert "message_template" in template
            assert "category" in template
            
            # Check for expected system templates
            template_names = [t.get("name", "") for t in data]
            expected_templates = ["Booking Confirmation", "Payment Reminder", "DP Transfer Complete"]
            found_count = sum(1 for exp in expected_templates if exp in template_names)
            print(f"PASS: WhatsApp templates returned {len(data)} templates, {found_count} expected templates found")
        else:
            print("PASS: WhatsApp templates endpoint works (empty list - will be populated on first access)")
    
    def test_get_qr_code(self, auth_token):
        """GET /api/whatsapp/qr-code - Generates QR code for connection"""
        response = requests.get(
            f"{BASE_URL}/api/whatsapp/qr-code",
            headers={**HEADERS, "Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "session_id" in data, "Missing session_id"
        assert "qr_code" in data, "Missing qr_code"
        assert "expires_in" in data, "Missing expires_in"
        assert "instructions" in data, "Missing instructions"
        
        # Verify QR code is base64 image
        assert data["qr_code"].startswith("data:image/png;base64,"), "QR code should be base64 PNG"
        
        # Verify instructions
        assert isinstance(data["instructions"], list)
        assert len(data["instructions"]) > 0
        
        print(f"PASS: QR code generated with session_id, expires in {data['expires_in']} seconds")
    
    def test_send_message_without_connection(self, auth_token):
        """POST /api/whatsapp/send - Should fail when not connected"""
        payload = {
            "phone_number": "+919876543210",
            "message": "Test message",
            "template_id": None
        }
        
        response = requests.post(
            f"{BASE_URL}/api/whatsapp/send",
            json=payload,
            headers={**HEADERS, "Authorization": f"Bearer {auth_token}"}
        )
        
        # Should either fail (400) if not connected, or succeed (200) if connected
        # Both are valid states
        if response.status_code == 400:
            data = response.json()
            assert "not connected" in data.get("detail", "").lower()
            print("PASS: Send message correctly blocked - WhatsApp not connected")
        elif response.status_code == 200:
            print("PASS: Send message succeeded - WhatsApp is connected")
        else:
            pytest.fail(f"Unexpected status: {response.status_code} - {response.text}")
    
    def test_get_whatsapp_stats(self, auth_token):
        """GET /api/whatsapp/stats - Get messaging statistics"""
        response = requests.get(
            f"{BASE_URL}/api/whatsapp/stats",
            headers={**HEADERS, "Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        data = response.json()
        
        # Verify structure
        assert "total_messages" in data
        assert "today_messages" in data
        assert "by_status" in data
        
        print(f"PASS: WhatsApp stats - total: {data['total_messages']}, today: {data['today_messages']}")
    
    def test_get_message_logs(self, auth_token):
        """GET /api/whatsapp/messages - Get message history"""
        response = requests.get(
            f"{BASE_URL}/api/whatsapp/messages",
            headers={**HEADERS, "Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        data = response.json()
        
        # Should return list
        assert isinstance(data, list)
        print(f"PASS: WhatsApp message logs returned {len(data)} messages")
    
    def test_unauthorized_whatsapp_access(self):
        """Test that WhatsApp endpoints require authentication"""
        response = requests.get(
            f"{BASE_URL}/api/whatsapp/config",
            headers=HEADERS
        )
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("PASS: WhatsApp config requires authentication")


class TestPEDashboardBPOverrides:
    """Test BP Overrides widget on PE Dashboard"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": PE_DESK_EMAIL, "password": PE_DESK_PASSWORD},
            headers=HEADERS
        )
        assert response.status_code == 200
        data = response.json()
        return data.get("access_token") or data.get("token")
    
    def test_pe_dashboard_includes_bp_overrides(self, auth_token):
        """GET /api/dashboard/pe - Should include bp_overrides count"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/pe",
            headers={**HEADERS, "Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        data = response.json()
        
        # Verify pending_actions structure
        assert "pending_actions" in data, "Missing pending_actions key"
        pending = data["pending_actions"]
        
        assert "bp_overrides" in pending, "Missing bp_overrides in pending_actions"
        assert isinstance(pending["bp_overrides"], int), "bp_overrides should be integer"
        
        # Verify other expected fields
        assert "bookings" in pending
        assert "clients" in pending
        assert "total" in pending
        
        print(f"PASS: PE Dashboard includes bp_overrides count: {pending['bp_overrides']}")


class TestNewPermissions:
    """Test new permissions are available in Role Management"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": PE_DESK_EMAIL, "password": PE_DESK_PASSWORD},
            headers=HEADERS
        )
        assert response.status_code == 200
        data = response.json()
        return data.get("access_token") or data.get("token")
    
    def test_bi_builder_permission_exists(self, auth_token):
        """Verify reports.bi_builder permission exists"""
        response = requests.get(
            f"{BASE_URL}/api/roles/permissions",
            headers={**HEADERS, "Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        data = response.json()
        
        # Check if permissions is list or dict
        if isinstance(data, list):
            permission_keys = [p.get("key", p.get("name", "")) for p in data]
        elif isinstance(data, dict):
            permission_keys = list(data.keys())
        else:
            permission_keys = []
        
        # Look for bi_builder permission
        bi_found = any("bi_builder" in p for p in permission_keys)
        if not bi_found:
            # Also check in full list
            all_perms = str(data)
            bi_found = "bi_builder" in all_perms
        
        assert bi_found, f"reports.bi_builder permission not found in permissions: {permission_keys[:20]}"
        print("PASS: reports.bi_builder permission exists in Role Management")
    
    def test_whatsapp_permission_exists(self, auth_token):
        """Verify notifications.whatsapp permission exists"""
        response = requests.get(
            f"{BASE_URL}/api/roles/permissions",
            headers={**HEADERS, "Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        data = response.json()
        
        # Check if permissions is list or dict
        if isinstance(data, list):
            permission_keys = [p.get("key", p.get("name", "")) for p in data]
        elif isinstance(data, dict):
            permission_keys = list(data.keys())
        else:
            permission_keys = []
        
        # Look for whatsapp permission
        wa_found = any("whatsapp" in p for p in permission_keys)
        if not wa_found:
            # Also check in full list
            all_perms = str(data)
            wa_found = "whatsapp" in all_perms
        
        assert wa_found, "notifications.whatsapp permission not found in permissions"
        print("PASS: notifications.whatsapp permission exists in Role Management")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
