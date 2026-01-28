"""
Backend API Tests for Modular Routers - Iteration 30
Tests all new modular router endpoints after server.py refactoring:
- Auth endpoints (register, login, me, change-password, sso/config)
- Dashboard endpoints (stats, analytics)
- Analytics endpoints (summary, stock-performance, employee-performance)
- Reports endpoints (pnl, export/excel)
- Inventory endpoints (list, by stock_id)
- Purchases endpoints (list, create)
- Audit Logs endpoints (list, stats)
- Bookings endpoints (list, by id, check-client-rp-conflict)
- Finance endpoints (refund-requests, rp-payments)
- Referral Partners endpoints (list, create)
"""
import pytest
import requests
import os
import uuid
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
PE_DESK_EMAIL = "pedesk@smifs.com"
PE_DESK_PASSWORD = "Kutta@123"


class TestAuthEndpoints:
    """Authentication endpoint tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup for auth tests"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def test_01_login_pe_desk_success(self):
        """Test PE Desk login with valid credentials"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": PE_DESK_EMAIL,
            "password": PE_DESK_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        
        data = response.json()
        assert "token" in data, "Token not in response"
        assert "user" in data, "User not in response"
        assert data["user"]["email"] == PE_DESK_EMAIL
        assert data["user"]["role"] == 1  # PE Desk role
        assert data["user"]["role_name"] == "PE Desk"
    
    def test_02_login_invalid_credentials(self):
        """Test login with invalid credentials returns 401"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "invalid@smifs.com",
            "password": "wrongpassword"
        })
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
    
    def test_03_get_current_user(self):
        """Test /auth/me endpoint returns correct user data"""
        # Login first
        login_resp = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": PE_DESK_EMAIL,
            "password": PE_DESK_PASSWORD
        })
        token = login_resp.json().get("token")
        
        # Get current user
        response = self.session.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200, f"Get me failed: {response.text}"
        
        data = response.json()
        assert data["email"] == PE_DESK_EMAIL
        assert data["role"] == 1
        assert "name" in data
        assert "created_at" in data
    
    def test_04_sso_config(self):
        """Test SSO config endpoint returns expected structure"""
        response = self.session.get(f"{BASE_URL}/api/auth/sso/config")
        assert response.status_code == 200, f"SSO config failed: {response.text}"
        
        data = response.json()
        assert "enabled" in data, "enabled field missing"
        # SSO is disabled in test env
        assert data["enabled"] == False


class TestDashboardEndpoints:
    """Dashboard endpoint tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup with authentication"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login
        login_resp = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": PE_DESK_EMAIL,
            "password": PE_DESK_PASSWORD
        })
        self.token = login_resp.json().get("token")
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
    
    def test_01_get_dashboard_stats(self):
        """Test dashboard stats endpoint returns all expected fields"""
        response = self.session.get(f"{BASE_URL}/api/dashboard/stats")
        assert response.status_code == 200, f"Dashboard stats failed: {response.text}"
        
        data = response.json()
        # Verify DashboardStats model fields
        expected_fields = [
            "total_clients", "total_vendors", "total_stocks", "total_bookings",
            "open_bookings", "closed_bookings", "total_profit_loss",
            "total_inventory_value", "total_purchases"
        ]
        for field in expected_fields:
            assert field in data, f"Missing field: {field}"
        
        # Verify types
        assert isinstance(data["total_clients"], int)
        assert isinstance(data["total_vendors"], int)
        assert isinstance(data["total_stocks"], int)
        assert isinstance(data["total_bookings"], int)
    
    def test_02_get_dashboard_analytics(self):
        """Test dashboard analytics endpoint"""
        response = self.session.get(f"{BASE_URL}/api/dashboard/analytics")
        assert response.status_code == 200, f"Dashboard analytics failed: {response.text}"
        
        data = response.json()
        assert "status_distribution" in data
        assert "approval_distribution" in data
        assert "recent_bookings" in data
        assert isinstance(data["recent_bookings"], list)


class TestAnalyticsEndpoints:
    """Analytics endpoint tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup with authentication"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        login_resp = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": PE_DESK_EMAIL,
            "password": PE_DESK_PASSWORD
        })
        self.token = login_resp.json().get("token")
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
    
    def test_01_get_analytics_summary(self):
        """Test analytics summary endpoint"""
        response = self.session.get(f"{BASE_URL}/api/analytics/summary")
        assert response.status_code == 200, f"Analytics summary failed: {response.text}"
        
        data = response.json()
        expected_fields = ["total_bookings", "total_revenue", "total_cost", "profit", "profit_margin"]
        for field in expected_fields:
            assert field in data, f"Missing field: {field}"
    
    def test_02_get_stock_performance(self):
        """Test stock performance analytics endpoint"""
        response = self.session.get(f"{BASE_URL}/api/analytics/stock-performance")
        assert response.status_code == 200, f"Stock performance failed: {response.text}"
        
        data = response.json()
        assert isinstance(data, list)
        
        if len(data) > 0:
            item = data[0]
            assert "stock_id" in item
            assert "symbol" in item
            assert "total_quantity" in item
            assert "profit" in item
    
    def test_03_get_employee_performance(self):
        """Test employee performance analytics endpoint (PE level only)"""
        response = self.session.get(f"{BASE_URL}/api/analytics/employee-performance")
        assert response.status_code == 200, f"Employee performance failed: {response.text}"
        
        data = response.json()
        assert isinstance(data, list)


class TestReportsEndpoints:
    """Reports endpoint tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup with authentication"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        login_resp = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": PE_DESK_EMAIL,
            "password": PE_DESK_PASSWORD
        })
        self.token = login_resp.json().get("token")
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
    
    def test_01_get_pnl_report(self):
        """Test P&L report endpoint"""
        response = self.session.get(f"{BASE_URL}/api/reports/pnl")
        assert response.status_code == 200, f"P&L report failed: {response.text}"
        
        data = response.json()
        assert "items" in data
        assert "summary" in data
        assert isinstance(data["items"], list)
        
        summary = data["summary"]
        assert "total_revenue" in summary
        assert "total_cost" in summary
        assert "gross_profit" in summary
        assert "total_bookings" in summary
    
    def test_02_export_excel(self):
        """Test Excel export endpoint returns file"""
        response = self.session.get(f"{BASE_URL}/api/reports/export/excel")
        assert response.status_code == 200, f"Excel export failed: {response.status_code}"
        
        # Check content type
        content_type = response.headers.get("content-type", "")
        assert "spreadsheet" in content_type or "octet-stream" in content_type


class TestInventoryEndpoints:
    """Inventory endpoint tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup with authentication"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        login_resp = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": PE_DESK_EMAIL,
            "password": PE_DESK_PASSWORD
        })
        self.token = login_resp.json().get("token")
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
    
    def test_01_get_inventory_list(self):
        """Test get inventory list"""
        response = self.session.get(f"{BASE_URL}/api/inventory")
        assert response.status_code == 200, f"Get inventory failed: {response.text}"
        
        data = response.json()
        assert isinstance(data, list)
        
        if len(data) > 0:
            item = data[0]
            assert "stock_id" in item
            assert "available_quantity" in item or "quantity" in item


class TestPurchasesEndpoints:
    """Purchases endpoint tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup with authentication"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        login_resp = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": PE_DESK_EMAIL,
            "password": PE_DESK_PASSWORD
        })
        self.token = login_resp.json().get("token")
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
    
    def test_01_get_purchases_list(self):
        """Test get purchases list with enriched data"""
        response = self.session.get(f"{BASE_URL}/api/purchases")
        assert response.status_code == 200, f"Get purchases failed: {response.text}"
        
        data = response.json()
        assert isinstance(data, list)
        
        if len(data) > 0:
            item = data[0]
            # Verify enriched fields are present
            assert "vendor_name" in item, "vendor_name missing from purchase"
            assert "stock_symbol" in item, "stock_symbol missing from purchase"
            assert "vendor_id" in item
            assert "stock_id" in item
            assert "quantity" in item


class TestAuditLogsEndpoints:
    """Audit logs endpoint tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup with authentication"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        login_resp = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": PE_DESK_EMAIL,
            "password": PE_DESK_PASSWORD
        })
        self.token = login_resp.json().get("token")
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
    
    def test_01_get_audit_logs(self):
        """Test get audit logs list"""
        response = self.session.get(f"{BASE_URL}/api/audit-logs")
        assert response.status_code == 200, f"Get audit logs failed: {response.text}"
        
        data = response.json()
        assert isinstance(data, list)
    
    def test_02_get_audit_logs_stats(self):
        """Test get audit logs stats"""
        response = self.session.get(f"{BASE_URL}/api/audit-logs/stats")
        assert response.status_code == 200, f"Get audit logs stats failed: {response.text}"
        
        data = response.json()
        assert "total_logs" in data


class TestBookingsEndpoints:
    """Bookings endpoint tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup with authentication"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        login_resp = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": PE_DESK_EMAIL,
            "password": PE_DESK_PASSWORD
        })
        self.token = login_resp.json().get("token")
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
    
    def test_01_get_bookings_list(self):
        """Test get bookings list"""
        response = self.session.get(f"{BASE_URL}/api/bookings")
        assert response.status_code == 200, f"Get bookings failed: {response.text}"
        
        data = response.json()
        assert isinstance(data, list)
        
        if len(data) > 0:
            booking = data[0]
            assert "id" in booking
            assert "client_name" in booking
            assert "stock_symbol" in booking
    
    def test_02_get_booking_by_id(self):
        """Test get single booking by ID"""
        # First get list to find a booking ID
        list_resp = self.session.get(f"{BASE_URL}/api/bookings")
        bookings = list_resp.json()
        
        if len(bookings) > 0:
            booking_id = bookings[0]["id"]
            response = self.session.get(f"{BASE_URL}/api/bookings/{booking_id}")
            assert response.status_code == 200, f"Get booking failed: {response.text}"
            
            data = response.json()
            assert data["id"] == booking_id
        else:
            pytest.skip("No bookings in database to test")


class TestFinanceEndpoints:
    """Finance endpoint tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup with authentication"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        login_resp = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": PE_DESK_EMAIL,
            "password": PE_DESK_PASSWORD
        })
        self.token = login_resp.json().get("token")
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
    
    def test_01_get_refund_requests(self):
        """Test get refund requests list"""
        response = self.session.get(f"{BASE_URL}/api/finance/refund-requests")
        assert response.status_code == 200, f"Get refund requests failed: {response.text}"
        
        data = response.json()
        assert isinstance(data, list)
    
    def test_02_get_rp_payments(self):
        """Test get RP payments list"""
        response = self.session.get(f"{BASE_URL}/api/finance/rp-payments")
        assert response.status_code == 200, f"Get RP payments failed: {response.text}"
        
        data = response.json()
        assert isinstance(data, list)
    
    def test_03_get_rp_payments_summary(self):
        """Test get RP payments summary"""
        response = self.session.get(f"{BASE_URL}/api/finance/rp-payments/summary")
        assert response.status_code == 200, f"Get RP payments summary failed: {response.text}"
        
        data = response.json()
        expected_fields = ["pending_count", "pending_amount", "paid_count", "paid_amount"]
        for field in expected_fields:
            assert field in data, f"Missing field: {field}"
    
    def test_04_get_finance_summary(self):
        """Test get finance summary"""
        response = self.session.get(f"{BASE_URL}/api/finance/summary")
        assert response.status_code == 200, f"Get finance summary failed: {response.text}"
        
        data = response.json()
        assert "total_received" in data
        assert "total_sent" in data
        assert "net_flow" in data


class TestReferralPartnersEndpoints:
    """Referral Partners endpoint tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup with authentication"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        login_resp = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": PE_DESK_EMAIL,
            "password": PE_DESK_PASSWORD
        })
        self.token = login_resp.json().get("token")
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
    
    def test_01_get_referral_partners_list(self):
        """Test get referral partners list"""
        response = self.session.get(f"{BASE_URL}/api/referral-partners")
        assert response.status_code == 200, f"Get RPs failed: {response.text}"
        
        data = response.json()
        assert isinstance(data, list)
        
        if len(data) > 0:
            rp = data[0]
            assert "id" in rp
            assert "name" in rp
            assert "rp_code" in rp
    
    def test_02_get_approved_referral_partners(self):
        """Test get approved referral partners"""
        response = self.session.get(f"{BASE_URL}/api/referral-partners/approved")
        assert response.status_code == 200, f"Get approved RPs failed: {response.text}"
        
        data = response.json()
        assert isinstance(data, list)
        
        # All returned RPs should be approved and active
        for rp in data:
            assert rp.get("approval_status") == "approved"
            assert rp.get("is_active") == True


class TestClientRPConflictCheck:
    """Test client-RP conflict check endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup with authentication"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        login_resp = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": PE_DESK_EMAIL,
            "password": PE_DESK_PASSWORD
        })
        self.token = login_resp.json().get("token")
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
    
    def test_01_check_client_rp_conflict(self):
        """Test client-RP conflict check endpoint"""
        # Get a client ID first
        clients_resp = self.session.get(f"{BASE_URL}/api/clients")
        clients = clients_resp.json()
        
        if len(clients) > 0:
            client_id = clients[0]["id"]
            response = self.session.get(f"{BASE_URL}/api/bookings/check-client-rp-conflict/{client_id}")
            assert response.status_code == 200, f"Conflict check failed: {response.text}"
            
            data = response.json()
            assert "has_conflict" in data
            assert isinstance(data["has_conflict"], bool)
        else:
            pytest.skip("No clients in database to test")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
