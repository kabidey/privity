"""
License Enforcement, FI Dashboard, and Client Module Segregation Tests
Tests for:
1. Backend license enforcement - /api/bookings checks bookings feature license
2. Backend license enforcement - /api/fixed-income/instruments checks fi_instruments license
3. Client filtering by module via /api/clients/by-module/{module}
4. FI Dashboard API /api/fixed-income/dashboard returns summary metrics
5. License admin (deynet@gmail.com) has full access
6. SMIFS employees (@smifs.com) are exempt from license checks
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
LICENSE_ADMIN = {"email": "deynet@gmail.com", "password": "Kutta@123"}
PE_DESK = {"email": "pe@smifs.com", "password": "Kutta@123"}


def get_auth_token(email: str, password: str) -> str:
    """Get authentication token for user."""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": email, "password": password}
    )
    if response.status_code == 200:
        return response.json().get("token")
    return None


def auth_headers(token: str) -> dict:
    """Get headers with auth token."""
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


class TestSMIFSExemption:
    """Test SMIFS employees (@smifs.com) are exempt from license checks"""
    
    @pytest.fixture(scope="class")
    def pe_token(self):
        """Get PE Desk token (SMIFS employee)"""
        token = get_auth_token(PE_DESK["email"], PE_DESK["password"])
        assert token is not None, "Failed to login as PE desk"
        return token
    
    def test_smifs_employee_can_access_bookings(self, pe_token):
        """SMIFS employees should be exempt from license checks for bookings"""
        response = requests.get(
            f"{BASE_URL}/api/bookings",
            headers=auth_headers(pe_token)
        )
        # Should return 200 OK since SMIFS employees are exempt
        assert response.status_code == 200, f"Expected 200 but got {response.status_code}: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Expected list of bookings"
        print(f"PASS: SMIFS employee can access /api/bookings - returned {len(data)} bookings")
    
    def test_smifs_employee_can_access_fi_instruments(self, pe_token):
        """SMIFS employees should be exempt from license checks for FI instruments"""
        response = requests.get(
            f"{BASE_URL}/api/fixed-income/instruments",
            headers=auth_headers(pe_token)
        )
        # Should return 200 OK since SMIFS employees are exempt
        assert response.status_code == 200, f"Expected 200 but got {response.status_code}: {response.text}"
        data = response.json()
        assert "instruments" in data or "total" in data, "Expected instruments data"
        print(f"PASS: SMIFS employee can access /api/fixed-income/instruments - returned {data.get('total', 0)} instruments")
    
    def test_smifs_employee_can_access_fi_dashboard(self, pe_token):
        """SMIFS employees should be exempt from license checks for FI dashboard"""
        response = requests.get(
            f"{BASE_URL}/api/fixed-income/dashboard",
            headers=auth_headers(pe_token)
        )
        # Should return 200 OK since SMIFS employees are exempt
        assert response.status_code == 200, f"Expected 200 but got {response.status_code}: {response.text}"
        data = response.json()
        assert "summary" in data, "Expected summary in response"
        print(f"PASS: SMIFS employee can access /api/fixed-income/dashboard")


class TestLicenseAdminAccess:
    """Test license admin (deynet@gmail.com) has full access"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get license admin token"""
        token = get_auth_token(LICENSE_ADMIN["email"], LICENSE_ADMIN["password"])
        assert token is not None, "Failed to login as license admin"
        return token
    
    def test_license_admin_can_access_bookings(self, admin_token):
        """License admin should have full access to bookings"""
        response = requests.get(
            f"{BASE_URL}/api/bookings",
            headers=auth_headers(admin_token)
        )
        # Should return 200 OK since license admin has full access
        assert response.status_code == 200, f"Expected 200 but got {response.status_code}: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Expected list of bookings"
        print(f"PASS: License admin can access /api/bookings - returned {len(data)} bookings")
    
    def test_license_admin_can_access_fi_instruments(self, admin_token):
        """License admin should have full access to FI instruments"""
        response = requests.get(
            f"{BASE_URL}/api/fixed-income/instruments",
            headers=auth_headers(admin_token)
        )
        # Should return 200 OK since license admin has full access
        assert response.status_code == 200, f"Expected 200 but got {response.status_code}: {response.text}"
        data = response.json()
        assert "instruments" in data or "total" in data, "Expected instruments data"
        print(f"PASS: License admin can access /api/fixed-income/instruments")
    
    def test_license_admin_can_access_fi_dashboard(self, admin_token):
        """License admin should have full access to FI dashboard"""
        response = requests.get(
            f"{BASE_URL}/api/fixed-income/dashboard",
            headers=auth_headers(admin_token)
        )
        # Should return 200 OK since license admin has full access
        assert response.status_code == 200, f"Expected 200 but got {response.status_code}: {response.text}"
        data = response.json()
        assert "summary" in data, "Expected summary in response"
        print(f"PASS: License admin can access /api/fixed-income/dashboard")


class TestFIDashboardAPI:
    """Test FI Dashboard API /api/fixed-income/dashboard"""
    
    @pytest.fixture(scope="class")
    def pe_token(self):
        """Get PE Desk token"""
        token = get_auth_token(PE_DESK["email"], PE_DESK["password"])
        assert token is not None, "Failed to login as PE desk"
        return token
    
    def test_fi_dashboard_returns_summary_metrics(self, pe_token):
        """FI Dashboard should return summary metrics"""
        response = requests.get(
            f"{BASE_URL}/api/fixed-income/dashboard",
            headers=auth_headers(pe_token)
        )
        assert response.status_code == 200, f"FI Dashboard failed: {response.status_code} {response.text}"
        data = response.json()
        
        # Check summary exists and has required fields
        assert "summary" in data, "Missing summary in response"
        summary = data["summary"]
        required_fields = ["total_aum", "total_holdings", "total_clients", "avg_ytm", "total_accrued_interest", "pending_orders"]
        for field in required_fields:
            assert field in summary, f"Missing {field} in summary"
        
        print(f"PASS: FI Dashboard summary - AUM: {summary['total_aum']}, Holdings: {summary['total_holdings']}, YTM: {summary['avg_ytm']}%")
    
    def test_fi_dashboard_returns_holdings_by_type(self, pe_token):
        """FI Dashboard should return holdings by type"""
        response = requests.get(
            f"{BASE_URL}/api/fixed-income/dashboard",
            headers=auth_headers(pe_token)
        )
        assert response.status_code == 200
        data = response.json()
        
        # Check holdings_by_type exists
        assert "holdings_by_type" in data, "Missing holdings_by_type in response"
        holdings_by_type = data["holdings_by_type"]
        # Can be empty dict if no holdings
        assert isinstance(holdings_by_type, dict), "holdings_by_type should be a dict"
        print(f"PASS: FI Dashboard holdings by type - {len(holdings_by_type)} types")
    
    def test_fi_dashboard_returns_holdings_by_rating(self, pe_token):
        """FI Dashboard should return holdings by rating"""
        response = requests.get(
            f"{BASE_URL}/api/fixed-income/dashboard",
            headers=auth_headers(pe_token)
        )
        assert response.status_code == 200
        data = response.json()
        
        # Check holdings_by_rating exists
        assert "holdings_by_rating" in data, "Missing holdings_by_rating in response"
        holdings_by_rating = data["holdings_by_rating"]
        assert isinstance(holdings_by_rating, dict), "holdings_by_rating should be a dict"
        print(f"PASS: FI Dashboard holdings by rating - {len(holdings_by_rating)} ratings")
    
    def test_fi_dashboard_returns_upcoming_maturities(self, pe_token):
        """FI Dashboard should return upcoming maturities"""
        response = requests.get(
            f"{BASE_URL}/api/fixed-income/dashboard",
            headers=auth_headers(pe_token)
        )
        assert response.status_code == 200
        data = response.json()
        
        # Check upcoming_maturities exists
        assert "upcoming_maturities" in data, "Missing upcoming_maturities in response"
        maturities = data["upcoming_maturities"]
        assert isinstance(maturities, list), "upcoming_maturities should be a list"
        print(f"PASS: FI Dashboard upcoming maturities - {len(maturities)} items")
    
    def test_fi_dashboard_returns_upcoming_coupons(self, pe_token):
        """FI Dashboard should return upcoming coupon payments"""
        response = requests.get(
            f"{BASE_URL}/api/fixed-income/dashboard",
            headers=auth_headers(pe_token)
        )
        assert response.status_code == 200
        data = response.json()
        
        # Check upcoming_coupons exists
        assert "upcoming_coupons" in data, "Missing upcoming_coupons in response"
        coupons = data["upcoming_coupons"]
        assert isinstance(coupons, list), "upcoming_coupons should be a list"
        print(f"PASS: FI Dashboard upcoming coupons - {len(coupons)} items")
    
    def test_fi_dashboard_returns_recent_orders(self, pe_token):
        """FI Dashboard should return recent orders"""
        response = requests.get(
            f"{BASE_URL}/api/fixed-income/dashboard",
            headers=auth_headers(pe_token)
        )
        assert response.status_code == 200
        data = response.json()
        
        # Check recent_orders exists
        assert "recent_orders" in data, "Missing recent_orders in response"
        orders = data["recent_orders"]
        assert isinstance(orders, list), "recent_orders should be a list"
        print(f"PASS: FI Dashboard recent orders - {len(orders)} items")


class TestClientModuleSegregation:
    """Test client filtering by module"""
    
    @pytest.fixture(scope="class")
    def pe_token(self):
        """Get PE Desk token"""
        token = get_auth_token(PE_DESK["email"], PE_DESK["password"])
        assert token is not None, "Failed to login as PE desk"
        return token
    
    def test_clients_by_module_pe_endpoint_exists(self, pe_token):
        """Test /api/clients/by-module/private_equity endpoint exists and works"""
        response = requests.get(
            f"{BASE_URL}/api/clients/by-module/private_equity",
            headers=auth_headers(pe_token)
        )
        assert response.status_code == 200, f"PE module clients failed: {response.status_code} {response.text}"
        data = response.json()
        assert isinstance(data, list), "Expected list of clients"
        print(f"PASS: /api/clients/by-module/private_equity - returned {len(data)} clients")
    
    def test_clients_by_module_fi_endpoint_exists(self, pe_token):
        """Test /api/clients/by-module/fixed_income endpoint exists and works"""
        response = requests.get(
            f"{BASE_URL}/api/clients/by-module/fixed_income",
            headers=auth_headers(pe_token)
        )
        assert response.status_code == 200, f"FI module clients failed: {response.status_code} {response.text}"
        data = response.json()
        assert isinstance(data, list), "Expected list of clients"
        print(f"PASS: /api/clients/by-module/fixed_income - returned {len(data)} clients")
    
    def test_clients_by_module_invalid_module_returns_400(self, pe_token):
        """Test invalid module returns 400 error"""
        response = requests.get(
            f"{BASE_URL}/api/clients/by-module/invalid_module",
            headers=auth_headers(pe_token)
        )
        assert response.status_code == 400, f"Expected 400 for invalid module but got {response.status_code}"
        print(f"PASS: Invalid module returns 400")
    
    def test_clients_by_module_with_search(self, pe_token):
        """Test client module filtering with search parameter"""
        response = requests.get(
            f"{BASE_URL}/api/clients/by-module/private_equity?search=test",
            headers=auth_headers(pe_token)
        )
        assert response.status_code == 200, f"Search failed: {response.status_code} {response.text}"
        data = response.json()
        assert isinstance(data, list), "Expected list of clients"
        print(f"PASS: /api/clients/by-module/private_equity with search - returned {len(data)} clients")


class TestLicenseCheckEndpoints:
    """Test license status check endpoints"""
    
    @pytest.fixture(scope="class")
    def pe_token(self):
        """Get PE Desk token"""
        token = get_auth_token(PE_DESK["email"], PE_DESK["password"])
        assert token is not None, "Failed to login as PE desk"
        return token
    
    def test_licence_check_status_endpoint(self, pe_token):
        """Test /api/licence/check/status endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/licence/check/status",
            headers=auth_headers(pe_token)
        )
        assert response.status_code == 200, f"License status check failed: {response.status_code} {response.text}"
        data = response.json()
        # Should have PE and FI status
        assert "private_equity" in data or "fixed_income" in data, "Expected module status"
        print(f"PASS: License status check returns module status")
    
    def test_licence_check_feature_bookings(self, pe_token):
        """Test /api/licence/check/feature for bookings"""
        response = requests.get(
            f"{BASE_URL}/api/licence/check/feature?feature=bookings",
            headers=auth_headers(pe_token)
        )
        assert response.status_code == 200, f"Feature check failed: {response.status_code} {response.text}"
        data = response.json()
        assert "is_licensed" in data, "Expected is_licensed field"
        print(f"PASS: Feature check for bookings - licensed: {data.get('is_licensed')}")
    
    def test_licence_check_feature_fi_instruments(self, pe_token):
        """Test /api/licence/check/feature for fi_instruments"""
        response = requests.get(
            f"{BASE_URL}/api/licence/check/feature?feature=fi_instruments",
            headers=auth_headers(pe_token)
        )
        assert response.status_code == 200, f"Feature check failed: {response.status_code} {response.text}"
        data = response.json()
        assert "is_licensed" in data, "Expected is_licensed field"
        print(f"PASS: Feature check for fi_instruments - licensed: {data.get('is_licensed')}")


class TestBookingsLicenseEnforcement:
    """Test license enforcement on bookings endpoint"""
    
    @pytest.fixture(scope="class")
    def pe_token(self):
        """Get PE Desk token"""
        token = get_auth_token(PE_DESK["email"], PE_DESK["password"])
        assert token is not None, "Failed to login as PE desk"
        return token
    
    def test_get_bookings_with_smifs_user(self, pe_token):
        """Test GET /api/bookings works for SMIFS employee (exempt)"""
        response = requests.get(
            f"{BASE_URL}/api/bookings",
            headers=auth_headers(pe_token)
        )
        # SMIFS employees are exempt from license checks
        assert response.status_code == 200, f"Expected 200 but got {response.status_code}: {response.text}"
        print(f"PASS: SMIFS user can GET /api/bookings")


class TestFIInstrumentsLicenseEnforcement:
    """Test license enforcement on FI instruments endpoint"""
    
    @pytest.fixture(scope="class")
    def pe_token(self):
        """Get PE Desk token"""
        token = get_auth_token(PE_DESK["email"], PE_DESK["password"])
        assert token is not None, "Failed to login as PE desk"
        return token
    
    def test_get_fi_instruments_with_smifs_user(self, pe_token):
        """Test GET /api/fixed-income/instruments works for SMIFS employee (exempt)"""
        response = requests.get(
            f"{BASE_URL}/api/fixed-income/instruments",
            headers=auth_headers(pe_token)
        )
        # SMIFS employees are exempt from license checks
        assert response.status_code == 200, f"Expected 200 but got {response.status_code}: {response.text}"
        print(f"PASS: SMIFS user can GET /api/fixed-income/instruments")


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
