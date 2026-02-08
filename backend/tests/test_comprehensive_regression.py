"""
Comprehensive Regression Test Suite for Privity Share Booking System
Tests: Auth, Dashboard, Clients, Vendors, Stocks, Bookings, Finance, Research, Database Backup
"""
import pytest
import requests
import os
from datetime import datetime

# Get BASE_URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
if not BASE_URL:
    BASE_URL = "https://live-nsdl-lookup.preview.emergentagent.com"

# Test credentials
PE_DESK_EMAIL = "pedesk@smifs.com"
PE_DESK_PASSWORD = "Kutta@123"
PE_MANAGER_EMAIL = "pemanager@smifs.com"
PE_MANAGER_PASSWORD = "Test@123"
EMPLOYEE_EMAIL = "testemployee@smifs.com"
EMPLOYEE_PASSWORD = "Test@123"


class TestHealthEndpoints:
    """Test health check endpoints"""
    
    def test_root_health(self):
        """Test /health endpoint for Kubernetes probes"""
        response = requests.get(f"{BASE_URL}/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        print(f"✓ Root health check passed: {data}")
    
    def test_api_health(self):
        """Test /api/health endpoint"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        print(f"✓ API health check passed: {data}")


class TestAuthentication:
    """Test authentication endpoints"""
    
    def test_login_pe_desk_valid(self):
        """Test PE Desk login with valid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": PE_DESK_EMAIL,
            "password": PE_DESK_PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert "user" in data
        assert data["user"]["email"] == PE_DESK_EMAIL
        assert data["user"]["role"] == 1
        assert data["user"]["role_name"] == "PE Desk"
        print(f"✓ PE Desk login successful: role={data['user']['role']}")
        return data["token"]
    
    def test_login_invalid_credentials(self):
        """Test login with invalid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "invalid@smifs.com",
            "password": "wrongpassword"
        })
        assert response.status_code == 401
        print("✓ Invalid credentials correctly rejected")
    
    def test_get_current_user(self):
        """Test /api/auth/me endpoint"""
        token = self.test_login_pe_desk_valid()
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/api/auth/me", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == PE_DESK_EMAIL
        print(f"✓ Get current user passed: {data['name']}")


class TestDashboard:
    """Test dashboard endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": PE_DESK_EMAIL,
            "password": PE_DESK_PASSWORD
        })
        self.token = response.json()["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_dashboard_stats(self):
        """Test dashboard stats endpoint"""
        response = requests.get(f"{BASE_URL}/api/dashboard/stats", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert "total_clients" in data
        assert "total_vendors" in data
        assert "total_stocks" in data
        assert "total_bookings" in data
        print(f"✓ Dashboard stats: clients={data['total_clients']}, stocks={data['total_stocks']}")
    
    def test_dashboard_analytics(self):
        """Test dashboard analytics endpoint"""
        response = requests.get(f"{BASE_URL}/api/dashboard/analytics", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert "status_distribution" in data
        assert "approval_distribution" in data
        print("✓ Dashboard analytics loaded")
    
    def test_pe_dashboard(self):
        """Test PE-specific dashboard"""
        response = requests.get(f"{BASE_URL}/api/dashboard/pe", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert "pending_actions" in data
        assert "today_activity" in data
        print(f"✓ PE Dashboard: pending_actions={data['pending_actions']['total']}")
    
    def test_finance_dashboard(self):
        """Test finance dashboard"""
        response = requests.get(f"{BASE_URL}/api/dashboard/finance", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert "receivables" in data
        assert "payables" in data
        print("✓ Finance Dashboard loaded")


class TestClients:
    """Test client management endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": PE_DESK_EMAIL,
            "password": PE_DESK_PASSWORD
        })
        self.token = response.json()["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_list_clients(self):
        """Test listing clients (is_vendor=false)"""
        response = requests.get(f"{BASE_URL}/api/clients?is_vendor=false", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Listed {len(data)} clients")
        return data
    
    def test_list_vendors(self):
        """Test listing vendors (is_vendor=true)"""
        response = requests.get(f"{BASE_URL}/api/clients?is_vendor=true", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Listed {len(data)} vendors")
        return data
    
    def test_create_client(self):
        """Test creating a new client"""
        test_pan = f"TEST{datetime.now().strftime('%H%M%S')}A"
        client_data = {
            "name": f"Test Client {datetime.now().strftime('%H%M%S')}",
            "email": f"testclient{datetime.now().strftime('%H%M%S')}@example.com",
            "phone": "9876543210",
            "pan_number": test_pan,
            "dp_id": "IN123456",
            "dp_type": "outside",
            "is_vendor": False,
            "bank_accounts": []
        }
        response = requests.post(f"{BASE_URL}/api/clients", json=client_data, headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == client_data["name"]
        assert data["pan_number"] == test_pan
        assert "otc_ucc" in data
        print(f"✓ Created client: {data['name']} (OTC UCC: {data['otc_ucc']})")
        return data
    
    def test_get_pending_clients(self):
        """Test getting pending approval clients"""
        response = requests.get(f"{BASE_URL}/api/clients/pending-approval", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Pending clients: {len(data)}")


class TestVendors:
    """Test vendor management endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": PE_DESK_EMAIL,
            "password": PE_DESK_PASSWORD
        })
        self.token = response.json()["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_create_vendor(self):
        """Test creating a new vendor"""
        test_pan = f"VEND{datetime.now().strftime('%H%M%S')}V"
        vendor_data = {
            "name": f"Test Vendor {datetime.now().strftime('%H%M%S')}",
            "email": f"testvendor{datetime.now().strftime('%H%M%S')}@example.com",
            "phone": "9876543211",
            "pan_number": test_pan,
            "dp_id": "VN123456",
            "dp_type": "outside",
            "is_vendor": True,
            "bank_accounts": []
        }
        response = requests.post(f"{BASE_URL}/api/clients", json=vendor_data, headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert data["is_vendor"] == True
        print(f"✓ Created vendor: {data['name']}")
        return data


class TestStocks:
    """Test stock management endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": PE_DESK_EMAIL,
            "password": PE_DESK_PASSWORD
        })
        self.token = response.json()["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_list_stocks(self):
        """Test listing all stocks"""
        response = requests.get(f"{BASE_URL}/api/stocks", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Listed {len(data)} stocks")
        return data
    
    def test_create_stock(self):
        """Test creating a new stock"""
        stock_symbol = f"TST{datetime.now().strftime('%H%M%S')}"
        stock_data = {
            "symbol": stock_symbol,
            "name": f"Test Stock {datetime.now().strftime('%H%M%S')}",
            "isin_number": f"INE{datetime.now().strftime('%H%M%S')}01",
            "exchange": "NSE",
            "sector": "Technology",
            "product": "Equity",
            "face_value": 10.0
        }
        response = requests.post(f"{BASE_URL}/api/stocks", json=stock_data, headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == stock_symbol
        print(f"✓ Created stock: {data['symbol']}")
        return data
    
    def test_get_inventory(self):
        """Test getting inventory"""
        response = requests.get(f"{BASE_URL}/api/inventory", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Inventory items: {len(data)}")


class TestBookings:
    """Test booking management endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": PE_DESK_EMAIL,
            "password": PE_DESK_PASSWORD
        })
        self.token = response.json()["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_list_bookings(self):
        """Test listing all bookings"""
        response = requests.get(f"{BASE_URL}/api/bookings", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Listed {len(data)} bookings")
        return data
    
    def test_get_pending_bookings(self):
        """Test getting pending approval bookings"""
        response = requests.get(f"{BASE_URL}/api/bookings/pending-approval", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Pending bookings: {len(data)}")
    
    def test_get_pending_loss_bookings(self):
        """Test getting pending loss approval bookings"""
        response = requests.get(f"{BASE_URL}/api/bookings/pending-loss-approval", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Pending loss bookings: {len(data)}")
    
    def test_get_dp_ready_bookings(self):
        """Test getting DP ready bookings"""
        response = requests.get(f"{BASE_URL}/api/bookings/dp-ready", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ DP ready bookings: {len(data)}")
    
    def test_get_dp_transferred_bookings(self):
        """Test getting DP transferred bookings"""
        response = requests.get(f"{BASE_URL}/api/bookings/dp-transferred", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ DP transferred bookings: {len(data)}")


class TestFinance:
    """Test finance endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": PE_DESK_EMAIL,
            "password": PE_DESK_PASSWORD
        })
        self.token = response.json()["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_finance_payments(self):
        """Test getting all payments"""
        response = requests.get(f"{BASE_URL}/api/finance/payments", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Finance payments: {len(data)}")
    
    def test_finance_summary(self):
        """Test getting finance summary"""
        response = requests.get(f"{BASE_URL}/api/finance/summary", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert "total_received" in data
        assert "total_sent" in data
        print(f"✓ Finance summary: received={data['total_received']}, sent={data['total_sent']}")
    
    def test_refund_requests(self):
        """Test getting refund requests"""
        response = requests.get(f"{BASE_URL}/api/finance/refund-requests", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Refund requests: {len(data)}")
    
    def test_rp_payments(self):
        """Test getting RP payments"""
        response = requests.get(f"{BASE_URL}/api/finance/rp-payments", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ RP payments: {len(data)}")
    
    def test_rp_payments_summary(self):
        """Test getting RP payments summary"""
        response = requests.get(f"{BASE_URL}/api/finance/rp-payments/summary", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert "pending_count" in data
        assert "paid_count" in data
        print(f"✓ RP payments summary: pending={data['pending_count']}, paid={data['paid_count']}")
    
    def test_employee_commissions(self):
        """Test getting employee commissions"""
        response = requests.get(f"{BASE_URL}/api/finance/employee-commissions", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Employee commissions: {len(data)}")


class TestResearchCenter:
    """Test research center endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": PE_DESK_EMAIL,
            "password": PE_DESK_PASSWORD
        })
        self.token = response.json()["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_research_stats(self):
        """Test getting research stats"""
        response = requests.get(f"{BASE_URL}/api/research/stats", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert "total_reports" in data
        assert "by_type" in data
        print(f"✓ Research stats: total_reports={data['total_reports']}")
    
    def test_list_research_reports(self):
        """Test listing research reports"""
        response = requests.get(f"{BASE_URL}/api/research/reports", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Research reports: {len(data)}")
    
    def test_ai_research_query(self):
        """Test AI research assistant"""
        response = requests.post(
            f"{BASE_URL}/api/research/ai-research",
            data={"query": "What are the key factors to consider when investing in private equity?"},
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert "disclaimer" in data
        print(f"✓ AI Research response received (length: {len(data['response'])})")
    
    def test_ai_research_empty_query_rejected(self):
        """Test AI research rejects empty query"""
        response = requests.post(
            f"{BASE_URL}/api/research/ai-research",
            data={"query": ""},
            headers=self.headers
        )
        # Empty query should be rejected
        assert response.status_code in [400, 422]
        print("✓ Empty AI research query correctly rejected")


class TestDatabaseBackup:
    """Test database backup endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": PE_DESK_EMAIL,
            "password": PE_DESK_PASSWORD
        })
        self.token = response.json()["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_list_backups(self):
        """Test listing database backups"""
        response = requests.get(f"{BASE_URL}/api/database/backups", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Database backups: {len(data)}")


class TestReferralPartners:
    """Test referral partner endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": PE_DESK_EMAIL,
            "password": PE_DESK_PASSWORD
        })
        self.token = response.json()["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_list_referral_partners(self):
        """Test listing referral partners"""
        response = requests.get(f"{BASE_URL}/api/referral-partners", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Referral partners: {len(data)}")


class TestBusinessPartners:
    """Test business partner endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": PE_DESK_EMAIL,
            "password": PE_DESK_PASSWORD
        })
        self.token = response.json()["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_list_business_partners(self):
        """Test listing business partners"""
        response = requests.get(f"{BASE_URL}/api/business-partners", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Business partners: {len(data)}")


class TestUsers:
    """Test user management endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": PE_DESK_EMAIL,
            "password": PE_DESK_PASSWORD
        })
        self.token = response.json()["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_list_users(self):
        """Test listing users"""
        response = requests.get(f"{BASE_URL}/api/users", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Users: {len(data)}")


class TestNotifications:
    """Test notification endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": PE_DESK_EMAIL,
            "password": PE_DESK_PASSWORD
        })
        self.token = response.json()["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_get_notifications(self):
        """Test getting notifications"""
        response = requests.get(f"{BASE_URL}/api/notifications", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Notifications: {len(data)}")


class TestAuditLogs:
    """Test audit log endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": PE_DESK_EMAIL,
            "password": PE_DESK_PASSWORD
        })
        self.token = response.json()["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_get_audit_logs(self):
        """Test getting audit logs"""
        response = requests.get(f"{BASE_URL}/api/audit-logs", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Audit logs: {len(data)}")


class TestEmailTemplates:
    """Test email template endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": PE_DESK_EMAIL,
            "password": PE_DESK_PASSWORD
        })
        self.token = response.json()["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_list_email_templates(self):
        """Test listing email templates"""
        response = requests.get(f"{BASE_URL}/api/email-templates", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Email templates: {len(data)}")


class TestCompanyMaster:
    """Test company master endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": PE_DESK_EMAIL,
            "password": PE_DESK_PASSWORD
        })
        self.token = response.json()["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_get_company_info(self):
        """Test getting company info"""
        response = requests.get(f"{BASE_URL}/api/company", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        print("✓ Company info retrieved")


class TestReports:
    """Test report endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": PE_DESK_EMAIL,
            "password": PE_DESK_PASSWORD
        })
        self.token = response.json()["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_get_reports_summary(self):
        """Test getting reports summary"""
        response = requests.get(f"{BASE_URL}/api/reports/summary", headers=self.headers)
        # Reports endpoint may return 200 or 404 if no data
        assert response.status_code in [200, 404]
        print("✓ Reports summary endpoint accessible")


class TestPurchases:
    """Test purchase endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": PE_DESK_EMAIL,
            "password": PE_DESK_PASSWORD
        })
        self.token = response.json()["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_list_purchases(self):
        """Test listing purchases"""
        response = requests.get(f"{BASE_URL}/api/purchases", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Purchases: {len(data)}")


class TestPEManagerAccess:
    """Test PE Manager role access"""
    
    def test_pe_manager_login(self):
        """Test PE Manager login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": PE_MANAGER_EMAIL,
            "password": PE_MANAGER_PASSWORD
        })
        # PE Manager may or may not exist
        if response.status_code == 200:
            data = response.json()
            assert data["user"]["role"] == 2
            print("✓ PE Manager login successful")
            return data["token"]
        else:
            pytest.skip("PE Manager user not found")
    
    def test_pe_manager_can_access_vendors(self):
        """Test PE Manager can access vendors"""
        token = self.test_pe_manager_login()
        if not token:
            pytest.skip("PE Manager not available")
        
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/api/clients?is_vendor=true", headers=headers)
        assert response.status_code == 200
        print("✓ PE Manager can access vendors")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
