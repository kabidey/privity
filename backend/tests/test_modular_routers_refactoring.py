"""
Test suite for verifying modular routers refactoring
Tests all key endpoints after server.py was reduced from 4313 to 332 lines
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestHealthAndAuth:
    """Test health check and authentication endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def test_health_check(self):
        """Test /api/health endpoint"""
        response = self.session.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["version"] == "2.0.0"
        print("✓ Health check passed - version 2.0.0")
    
    def test_login_success(self):
        """Test login with PE Desk credentials"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "pedesk@smifs.com",
            "password": "Kutta@123"
        })
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert "user" in data
        assert data["user"]["email"] == "pedesk@smifs.com"
        assert data["user"]["role"] == 1
        assert data["user"]["role_name"] == "PE Desk"
        print(f"✓ Login successful - User: {data['user']['name']}")
    
    def test_login_invalid_credentials(self):
        """Test login with invalid credentials"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "invalid@test.com",
            "password": "wrongpassword"
        })
        assert response.status_code == 401
        print("✓ Invalid login correctly rejected")


class TestDashboard:
    """Test dashboard endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        # Login and get token
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "pedesk@smifs.com",
            "password": "Kutta@123"
        })
        if response.status_code == 200:
            token = response.json().get("token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
    
    def test_dashboard_stats(self):
        """Test /api/dashboard/stats endpoint"""
        response = self.session.get(f"{BASE_URL}/api/dashboard/stats")
        assert response.status_code == 200
        data = response.json()
        assert "total_clients" in data
        assert "total_stocks" in data
        assert "total_bookings" in data
        print(f"✓ Dashboard stats - Clients: {data['total_clients']}, Stocks: {data['total_stocks']}, Bookings: {data['total_bookings']}")


class TestClients:
    """Test clients endpoints from routers/clients.py"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "pedesk@smifs.com",
            "password": "Kutta@123"
        })
        if response.status_code == 200:
            token = response.json().get("token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
    
    def test_get_clients(self):
        """Test GET /api/clients endpoint"""
        response = self.session.get(f"{BASE_URL}/api/clients")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Clients list - {len(data)} clients found")
    
    def test_get_clients_filter_vendor(self):
        """Test GET /api/clients with is_vendor filter"""
        response = self.session.get(f"{BASE_URL}/api/clients?is_vendor=false")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # All returned should be non-vendors
        for client in data:
            assert client.get("is_vendor", False) == False
        print(f"✓ Clients filter (non-vendors) - {len(data)} clients")
    
    def test_get_pending_approval_clients(self):
        """Test GET /api/clients/pending-approval endpoint"""
        response = self.session.get(f"{BASE_URL}/api/clients/pending-approval")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Pending approval clients - {len(data)} pending")


class TestStocks:
    """Test stocks endpoints from routers/stocks.py"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "pedesk@smifs.com",
            "password": "Kutta@123"
        })
        if response.status_code == 200:
            token = response.json().get("token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
    
    def test_get_stocks(self):
        """Test GET /api/stocks endpoint"""
        response = self.session.get(f"{BASE_URL}/api/stocks")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Stocks list - {len(data)} stocks found")
        if len(data) > 0:
            stock = data[0]
            assert "id" in stock
            assert "symbol" in stock
            assert "name" in stock
            print(f"  First stock: {stock['symbol']} - {stock['name']}")
    
    def test_get_inventory(self):
        """Test GET /api/inventory endpoint"""
        response = self.session.get(f"{BASE_URL}/api/inventory")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Inventory list - {len(data)} items")
    
    def test_get_corporate_actions(self):
        """Test GET /api/corporate-actions endpoint"""
        response = self.session.get(f"{BASE_URL}/api/corporate-actions")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Corporate actions - {len(data)} actions")


class TestBookings:
    """Test bookings endpoints from routers/bookings.py"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "pedesk@smifs.com",
            "password": "Kutta@123"
        })
        if response.status_code == 200:
            token = response.json().get("token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
    
    def test_get_bookings(self):
        """Test GET /api/bookings endpoint"""
        response = self.session.get(f"{BASE_URL}/api/bookings")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Bookings list - {len(data)} bookings found")
        if len(data) > 0:
            booking = data[0]
            assert "id" in booking
            assert "booking_number" in booking
            assert "client_name" in booking
            assert "stock_symbol" in booking
            print(f"  First booking: {booking['booking_number']} - {booking['client_name']}")


class TestReferralPartners:
    """Test referral partners endpoints from routers/referral_partners.py"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "pedesk@smifs.com",
            "password": "Kutta@123"
        })
        if response.status_code == 200:
            token = response.json().get("token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
    
    def test_get_referral_partners(self):
        """Test GET /api/referral-partners endpoint"""
        response = self.session.get(f"{BASE_URL}/api/referral-partners")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Referral partners - {len(data)} partners found")


class TestReports:
    """Test reports endpoints from routers/reports.py"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "pedesk@smifs.com",
            "password": "Kutta@123"
        })
        if response.status_code == 200:
            token = response.json().get("token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
    
    def test_get_pnl_report(self):
        """Test GET /api/reports/pnl endpoint"""
        response = self.session.get(f"{BASE_URL}/api/reports/pnl")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "summary" in data
        summary = data["summary"]
        assert "total_revenue" in summary
        assert "total_cost" in summary
        assert "gross_profit" in summary
        print(f"✓ P&L Report - Revenue: {summary['total_revenue']}, Profit: {summary['gross_profit']}")


class TestFinance:
    """Test finance endpoints from routers/finance.py"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "pedesk@smifs.com",
            "password": "Kutta@123"
        })
        if response.status_code == 200:
            token = response.json().get("token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
    
    def test_get_payments(self):
        """Test GET /api/finance/payments endpoint"""
        response = self.session.get(f"{BASE_URL}/api/finance/payments")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Finance payments - {len(data)} payments found")


class TestBusinessPartners:
    """Test business partners endpoints from routers/business_partners.py"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "pedesk@smifs.com",
            "password": "Kutta@123"
        })
        if response.status_code == 200:
            token = response.json().get("token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
    
    def test_get_business_partners(self):
        """Test GET /api/business-partners endpoint"""
        response = self.session.get(f"{BASE_URL}/api/business-partners")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Business partners - {len(data)} partners found")


class TestUsers:
    """Test users endpoints from routers/users.py"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "pedesk@smifs.com",
            "password": "Kutta@123"
        })
        if response.status_code == 200:
            token = response.json().get("token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
    
    def test_get_users(self):
        """Test GET /api/users endpoint"""
        response = self.session.get(f"{BASE_URL}/api/users")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Users list - {len(data)} users found")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
