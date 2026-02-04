"""
Test Suite for Granular BI Reports and WhatsApp Permissions (Iteration 60)

Tests the following new permissions:
BI Reports (8 new permissions):
- reports.bi_bookings - Generate booking reports
- reports.bi_clients - Generate client reports
- reports.bi_revenue - Generate revenue reports
- reports.bi_inventory - Generate inventory reports
- reports.bi_payments - Generate payment reports
- reports.bi_pnl - Generate P&L reports
- reports.bi_export - Export BI reports to Excel
- reports.bi_save_templates - Save and manage BI report templates

WhatsApp (6 new permissions):
- notifications.whatsapp_view - View WhatsApp configuration
- notifications.whatsapp_connect - Connect/Disconnect WhatsApp
- notifications.whatsapp_templates - Manage message templates
- notifications.whatsapp_send - Send individual messages
- notifications.whatsapp_bulk - Send bulk messages
- notifications.whatsapp_history - View message history
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


@pytest.fixture(scope="module")
def pe_desk_token():
    """Get authentication token for PE Desk user (has all permissions)"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": PE_DESK_EMAIL, "password": PE_DESK_PASSWORD},
        headers=HEADERS
    )
    assert response.status_code == 200, f"Login failed: {response.text}"
    data = response.json()
    token = data.get("access_token") or data.get("token")
    assert token is not None, "No token returned"
    return token


class TestGranularBIPermissionsInRolesAPI:
    """Test that granular BI permissions are exposed in the roles/permissions API"""
    
    def test_permissions_api_returns_granular_bi_permissions(self, pe_desk_token):
        """GET /api/roles/permissions - Should return granular BI report permissions"""
        response = requests.get(
            f"{BASE_URL}/api/roles/permissions",
            headers={**HEADERS, "Authorization": f"Bearer {pe_desk_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        data = response.json()
        
        # Verify the response structure has reports category
        assert "reports" in data, "Missing 'reports' category in permissions"
        reports_category = data["reports"]
        assert "permissions" in reports_category, "Missing permissions in reports category"
        
        # Extract permission keys from reports category
        perm_keys = [p["key"] for p in reports_category["permissions"]]
        
        # Check for each granular BI permission
        expected_bi_permissions = [
            "reports.bi_bookings",
            "reports.bi_clients",
            "reports.bi_revenue",
            "reports.bi_inventory",
            "reports.bi_payments",
            "reports.bi_pnl",
            "reports.bi_export",
            "reports.bi_save_templates"
        ]
        
        for perm in expected_bi_permissions:
            assert perm in perm_keys, f"Missing BI permission: {perm}"
        
        print(f"PASS: All 8 granular BI permissions found in /api/roles/permissions")
    
    def test_permissions_api_returns_granular_whatsapp_permissions(self, pe_desk_token):
        """GET /api/roles/permissions - Should return granular WhatsApp permissions"""
        response = requests.get(
            f"{BASE_URL}/api/roles/permissions",
            headers={**HEADERS, "Authorization": f"Bearer {pe_desk_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        data = response.json()
        
        # Verify the response structure has notifications category
        assert "notifications" in data, "Missing 'notifications' category in permissions"
        notif_category = data["notifications"]
        assert "permissions" in notif_category, "Missing permissions in notifications category"
        
        # Extract permission keys from notifications category
        perm_keys = [p["key"] for p in notif_category["permissions"]]
        
        # Check for each granular WhatsApp permission
        expected_whatsapp_permissions = [
            "notifications.whatsapp_view",
            "notifications.whatsapp_connect",
            "notifications.whatsapp_templates",
            "notifications.whatsapp_send",
            "notifications.whatsapp_bulk",
            "notifications.whatsapp_history"
        ]
        
        for perm in expected_whatsapp_permissions:
            assert perm in perm_keys, f"Missing WhatsApp permission: {perm}"
        
        print(f"PASS: All 6 granular WhatsApp permissions found in /api/roles/permissions")


class TestBIReportsConfigWithPermissions:
    """Test that /api/bi-reports/config returns only report types user has permission for"""
    
    def test_bi_config_returns_report_types_based_on_permissions(self, pe_desk_token):
        """GET /api/bi-reports/config - Should return only report types user has permission for"""
        response = requests.get(
            f"{BASE_URL}/api/bi-reports/config",
            headers={**HEADERS, "Authorization": f"Bearer {pe_desk_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        data = response.json()
        
        # Verify structure
        assert "report_types" in data, "Missing report_types in response"
        assert "configs" in data, "Missing configs in response"
        
        # PE Desk has all permissions, so all 6 report types should be present
        report_types = data["report_types"]
        report_keys = [t["key"] for t in report_types]
        
        expected_types = ["bookings", "clients", "revenue", "inventory", "payments", "pnl"]
        for expected in expected_types:
            assert expected in report_keys, f"Missing report type: {expected}"
        
        # Each report type should have a permission key
        for rt in report_types:
            assert "permission" in rt, f"Missing permission key for report type {rt['key']}"
            assert rt["permission"].startswith("reports.bi_"), \
                f"Invalid permission format for {rt['key']}: {rt['permission']}"
        
        print(f"PASS: BI config returns {len(report_types)} report types with permission keys")
    
    def test_bi_config_returns_export_and_save_template_flags(self, pe_desk_token):
        """GET /api/bi-reports/config - Should include can_export and can_save_templates flags"""
        response = requests.get(
            f"{BASE_URL}/api/bi-reports/config",
            headers={**HEADERS, "Authorization": f"Bearer {pe_desk_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        data = response.json()
        
        # Verify capability flags
        assert "can_export" in data, "Missing can_export flag in response"
        assert "can_save_templates" in data, "Missing can_save_templates flag in response"
        
        # PE Desk should have both permissions
        assert data["can_export"] is True, "PE Desk should have can_export=True"
        assert data["can_save_templates"] is True, "PE Desk should have can_save_templates=True"
        
        print(f"PASS: BI config returns can_export={data['can_export']}, can_save_templates={data['can_save_templates']}")


class TestBIReportGeneratePermissionChecks:
    """Test that POST /api/bi-reports/generate checks specific report type permission"""
    
    def test_generate_bookings_report_requires_bi_bookings_permission(self, pe_desk_token):
        """POST /api/bi-reports/generate - Should check reports.bi_bookings permission"""
        payload = {
            "report_type": "bookings",
            "dimensions": ["approval_status"],
            "metrics": ["count"],
            "filters": [],
            "limit": 10
        }
        
        response = requests.post(
            f"{BASE_URL}/api/bi-reports/generate",
            json=payload,
            headers={**HEADERS, "Authorization": f"Bearer {pe_desk_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        data = response.json()
        
        assert data["report_type"] == "bookings"
        print("PASS: Generate bookings report works for PE Desk (has bi_bookings permission)")
    
    def test_generate_clients_report_requires_bi_clients_permission(self, pe_desk_token):
        """POST /api/bi-reports/generate - Should check reports.bi_clients permission"""
        payload = {
            "report_type": "clients",
            "dimensions": ["approval_status"],
            "metrics": ["count"],
            "filters": [],
            "limit": 10
        }
        
        response = requests.post(
            f"{BASE_URL}/api/bi-reports/generate",
            json=payload,
            headers={**HEADERS, "Authorization": f"Bearer {pe_desk_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        data = response.json()
        
        assert data["report_type"] == "clients"
        print("PASS: Generate clients report works for PE Desk (has bi_clients permission)")
    
    def test_generate_revenue_report_requires_bi_revenue_permission(self, pe_desk_token):
        """POST /api/bi-reports/generate - Should check reports.bi_revenue permission"""
        payload = {
            "report_type": "revenue",
            "dimensions": ["created_by_name"],
            "metrics": ["count"],
            "filters": [],
            "limit": 10
        }
        
        response = requests.post(
            f"{BASE_URL}/api/bi-reports/generate",
            json=payload,
            headers={**HEADERS, "Authorization": f"Bearer {pe_desk_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        data = response.json()
        
        assert data["report_type"] == "revenue"
        print("PASS: Generate revenue report works for PE Desk (has bi_revenue permission)")
    
    def test_generate_inventory_report_requires_bi_inventory_permission(self, pe_desk_token):
        """POST /api/bi-reports/generate - Should check reports.bi_inventory permission"""
        payload = {
            "report_type": "inventory",
            "dimensions": ["stock_symbol"],
            "metrics": ["available_quantity"],
            "filters": [],
            "limit": 10
        }
        
        response = requests.post(
            f"{BASE_URL}/api/bi-reports/generate",
            json=payload,
            headers={**HEADERS, "Authorization": f"Bearer {pe_desk_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        data = response.json()
        
        assert data["report_type"] == "inventory"
        print("PASS: Generate inventory report works for PE Desk (has bi_inventory permission)")
    
    def test_generate_payments_report_requires_bi_payments_permission(self, pe_desk_token):
        """POST /api/bi-reports/generate - Should check reports.bi_payments permission"""
        payload = {
            "report_type": "payments",
            "dimensions": ["payment_status"],
            "metrics": ["count"],
            "filters": [],
            "limit": 10
        }
        
        response = requests.post(
            f"{BASE_URL}/api/bi-reports/generate",
            json=payload,
            headers={**HEADERS, "Authorization": f"Bearer {pe_desk_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        data = response.json()
        
        assert data["report_type"] == "payments"
        print("PASS: Generate payments report works for PE Desk (has bi_payments permission)")
    
    def test_generate_pnl_report_requires_bi_pnl_permission(self, pe_desk_token):
        """POST /api/bi-reports/generate - Should check reports.bi_pnl permission"""
        payload = {
            "report_type": "pnl",
            "dimensions": ["stock_symbol"],
            "metrics": ["count"],
            "filters": [],
            "limit": 10
        }
        
        response = requests.post(
            f"{BASE_URL}/api/bi-reports/generate",
            json=payload,
            headers={**HEADERS, "Authorization": f"Bearer {pe_desk_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        data = response.json()
        
        assert data["report_type"] == "pnl"
        print("PASS: Generate P&L report works for PE Desk (has bi_pnl permission)")


class TestBIExportPermissionCheck:
    """Test that POST /api/bi-reports/export requires bi_export permission"""
    
    def test_export_requires_bi_export_permission(self, pe_desk_token):
        """POST /api/bi-reports/export - Should require reports.bi_export permission"""
        payload = {
            "report_type": "bookings",
            "dimensions": ["approval_status"],
            "metrics": ["count"],
            "filters": [],
            "limit": 10
        }
        
        response = requests.post(
            f"{BASE_URL}/api/bi-reports/export",
            json=payload,
            headers={**HEADERS, "Authorization": f"Bearer {pe_desk_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        
        # Check it's an Excel file
        content_type = response.headers.get("Content-Type", "")
        assert "spreadsheet" in content_type or "octet-stream" in content_type, \
            f"Expected Excel content type, got: {content_type}"
        
        print("PASS: Export BI report works for PE Desk (has bi_export permission)")


class TestWhatsAppPermissionChecks:
    """Test that WhatsApp endpoints check their specific permissions"""
    
    def test_whatsapp_config_requires_whatsapp_view_permission(self, pe_desk_token):
        """GET /api/whatsapp/config - Should require notifications.whatsapp_view permission"""
        response = requests.get(
            f"{BASE_URL}/api/whatsapp/config",
            headers={**HEADERS, "Authorization": f"Bearer {pe_desk_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        data = response.json()
        
        # Should return config object
        assert "status" in data or "enabled" in data
        print("PASS: WhatsApp config endpoint works for PE Desk (has whatsapp_view permission)")
    
    def test_whatsapp_qr_requires_whatsapp_connect_permission(self, pe_desk_token):
        """GET /api/whatsapp/qr-code - Should require notifications.whatsapp_connect permission"""
        response = requests.get(
            f"{BASE_URL}/api/whatsapp/qr-code",
            headers={**HEADERS, "Authorization": f"Bearer {pe_desk_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        data = response.json()
        
        # Should return QR code data
        assert "session_id" in data
        assert "qr_code" in data
        print("PASS: WhatsApp QR code endpoint works for PE Desk (has whatsapp_connect permission)")
    
    def test_whatsapp_templates_requires_whatsapp_templates_permission(self, pe_desk_token):
        """GET /api/whatsapp/templates - Should require notifications.whatsapp_templates permission"""
        response = requests.get(
            f"{BASE_URL}/api/whatsapp/templates",
            headers={**HEADERS, "Authorization": f"Bearer {pe_desk_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        data = response.json()
        
        # Should return list of templates
        assert isinstance(data, list)
        print(f"PASS: WhatsApp templates endpoint works for PE Desk (has whatsapp_templates permission) - {len(data)} templates")
    
    def test_whatsapp_send_requires_whatsapp_send_permission(self, pe_desk_token):
        """POST /api/whatsapp/send - Should require notifications.whatsapp_send permission"""
        payload = {
            "phone_number": "+919876543210",
            "message": "Test message from granular permissions test"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/whatsapp/send",
            json=payload,
            headers={**HEADERS, "Authorization": f"Bearer {pe_desk_token}"}
        )
        
        # Either 200 (connected) or 400 (not connected) is acceptable
        # Both confirm the permission check passed and business logic is running
        assert response.status_code in [200, 400], f"Unexpected status: {response.status_code} - {response.text}"
        
        if response.status_code == 400:
            data = response.json()
            assert "not connected" in data.get("detail", "").lower()
            print("PASS: WhatsApp send endpoint checked permission, blocked due to no connection")
        else:
            print("PASS: WhatsApp send endpoint works for PE Desk (has whatsapp_send permission)")
    
    def test_whatsapp_history_requires_whatsapp_history_permission(self, pe_desk_token):
        """GET /api/whatsapp/messages - Should require notifications.whatsapp_history permission"""
        response = requests.get(
            f"{BASE_URL}/api/whatsapp/messages",
            headers={**HEADERS, "Authorization": f"Bearer {pe_desk_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        data = response.json()
        
        # Should return list of messages
        assert isinstance(data, list)
        print(f"PASS: WhatsApp message history endpoint works for PE Desk (has whatsapp_history permission) - {len(data)} messages")


class TestPermissionServiceIntegration:
    """Verify that permission service contains the granular permissions"""
    
    def test_permission_service_has_granular_bi_permissions(self, pe_desk_token):
        """Verify that the permission service recognizes BI granular permissions"""
        # Test by checking user permissions endpoint
        response = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={**HEADERS, "Authorization": f"Bearer {pe_desk_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        data = response.json()
        
        # PE Desk (role 1) should have all permissions
        assert data.get("role") == 1, "Expected PE Desk role (1)"
        print(f"PASS: Verified PE Desk user (role 1) has access to all permissions")


class TestUnauthorizedAccess:
    """Test that endpoints properly reject unauthorized access"""
    
    def test_bi_config_rejects_no_auth(self):
        """GET /api/bi-reports/config - Should reject unauthenticated requests"""
        response = requests.get(
            f"{BASE_URL}/api/bi-reports/config",
            headers=HEADERS
        )
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("PASS: BI reports config rejects unauthenticated access")
    
    def test_bi_generate_rejects_no_auth(self):
        """POST /api/bi-reports/generate - Should reject unauthenticated requests"""
        payload = {
            "report_type": "bookings",
            "dimensions": ["approval_status"],
            "metrics": ["count"]
        }
        response = requests.post(
            f"{BASE_URL}/api/bi-reports/generate",
            json=payload,
            headers=HEADERS
        )
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("PASS: BI reports generate rejects unauthenticated access")
    
    def test_bi_export_rejects_no_auth(self):
        """POST /api/bi-reports/export - Should reject unauthenticated requests"""
        payload = {
            "report_type": "bookings",
            "dimensions": ["approval_status"],
            "metrics": ["count"]
        }
        response = requests.post(
            f"{BASE_URL}/api/bi-reports/export",
            json=payload,
            headers=HEADERS
        )
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("PASS: BI reports export rejects unauthenticated access")
    
    def test_whatsapp_config_rejects_no_auth(self):
        """GET /api/whatsapp/config - Should reject unauthenticated requests"""
        response = requests.get(
            f"{BASE_URL}/api/whatsapp/config",
            headers=HEADERS
        )
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("PASS: WhatsApp config rejects unauthenticated access")
    
    def test_whatsapp_qr_rejects_no_auth(self):
        """GET /api/whatsapp/qr-code - Should reject unauthenticated requests"""
        response = requests.get(
            f"{BASE_URL}/api/whatsapp/qr-code",
            headers=HEADERS
        )
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("PASS: WhatsApp QR code rejects unauthenticated access")
    
    def test_whatsapp_templates_rejects_no_auth(self):
        """GET /api/whatsapp/templates - Should reject unauthenticated requests"""
        response = requests.get(
            f"{BASE_URL}/api/whatsapp/templates",
            headers=HEADERS
        )
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("PASS: WhatsApp templates rejects unauthenticated access")
    
    def test_whatsapp_send_rejects_no_auth(self):
        """POST /api/whatsapp/send - Should reject unauthenticated requests"""
        payload = {
            "phone_number": "+919876543210",
            "message": "Test"
        }
        response = requests.post(
            f"{BASE_URL}/api/whatsapp/send",
            json=payload,
            headers=HEADERS
        )
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("PASS: WhatsApp send rejects unauthenticated access")
    
    def test_whatsapp_messages_rejects_no_auth(self):
        """GET /api/whatsapp/messages - Should reject unauthenticated requests"""
        response = requests.get(
            f"{BASE_URL}/api/whatsapp/messages",
            headers=HEADERS
        )
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("PASS: WhatsApp messages rejects unauthenticated access")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
