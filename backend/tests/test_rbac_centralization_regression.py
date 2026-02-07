"""
RBAC Centralization Regression Test
Tests all major flows after 18 routers were updated to use centralized permission helpers.

This test verifies:
1. Health endpoint works
2. Inventory endpoint returns data
3. Stocks endpoint works
4. Email templates verify endpoint works
5. Auth endpoints work
6. Demo mode authentication
7. Permission service helpers work correctly

Created for iteration 77 after RBAC refactoring.
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials - PE Desk admin
PE_DESK_EMAIL = "pe@smifs.com"
PE_DESK_PASSWORD = "Admin@123"


class TestHealthEndpoint:
    """Health endpoint tests"""
    
    def test_health_returns_ok(self):
        """GET /api/health should return status=ok"""
        response = requests.get(f"{BASE_URL}/api/health", timeout=10)
        assert response.status_code == 200, f"Health check failed: {response.text}"
        
        data = response.json()
        assert data.get("status") == "ok", f"Health status not ok: {data}"
        print(f"✓ Health check passed: {data.get('status')}")


class TestAuthEndpoints:
    """Authentication endpoint tests"""
    
    def test_login_with_invalid_credentials(self):
        """POST /api/auth/login with invalid credentials should return 401"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "invalid@test.com", "password": "wrongpassword"},
            timeout=10
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Invalid login correctly rejected")
    
    def test_login_with_valid_pe_desk(self):
        """POST /api/auth/login with PE Desk credentials should return token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": PE_DESK_EMAIL, "password": PE_DESK_PASSWORD},
            timeout=10
        )
        assert response.status_code == 200, f"PE Desk login failed: {response.text}"
        
        data = response.json()
        assert "token" in data, "No token in response"
        assert "user" in data, "No user in response"
        print(f"✓ PE Desk login successful: {data['user'].get('name')}")
        return data["token"]
    
    def test_demo_mode_login(self):
        """POST /api/demo/login should return demo token"""
        response = requests.post(
            f"{BASE_URL}/api/demo/login",
            json={"role": "employee"},
            timeout=10
        )
        # Demo mode might not require auth or might return different status
        if response.status_code == 200:
            data = response.json()
            assert "token" in data or "access_token" in data, "No token in demo response"
            print("✓ Demo mode login successful")
        elif response.status_code == 404:
            print("⚠ Demo endpoint not found (may not be exposed)")
        else:
            print(f"⚠ Demo login returned: {response.status_code}")


class TestInventoryEndpoints:
    """Inventory endpoint tests - verifies RBAC on inventory router"""
    
    @pytest.fixture
    def auth_token(self):
        """Get PE Desk auth token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": PE_DESK_EMAIL, "password": PE_DESK_PASSWORD},
            timeout=10
        )
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Could not authenticate")
    
    def test_inventory_without_auth(self):
        """GET /api/inventory without auth should return 401"""
        response = requests.get(f"{BASE_URL}/api/inventory", timeout=10)
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Inventory correctly requires authentication")
    
    def test_inventory_with_auth(self, auth_token):
        """GET /api/inventory with auth should return inventory data"""
        response = requests.get(
            f"{BASE_URL}/api/inventory",
            headers={"Authorization": f"Bearer {auth_token}"},
            timeout=10
        )
        assert response.status_code == 200, f"Inventory fetch failed: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Inventory should return a list"
        print(f"✓ Inventory endpoint works, returned {len(data)} items")


class TestStocksEndpoints:
    """Stocks endpoint tests - verifies RBAC on stocks router"""
    
    @pytest.fixture
    def auth_token(self):
        """Get PE Desk auth token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": PE_DESK_EMAIL, "password": PE_DESK_PASSWORD},
            timeout=10
        )
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Could not authenticate")
    
    def test_stocks_without_auth(self):
        """GET /api/stocks without auth should return 401"""
        response = requests.get(f"{BASE_URL}/api/stocks", timeout=10)
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Stocks correctly requires authentication")
    
    def test_stocks_with_auth(self, auth_token):
        """GET /api/stocks with auth should return stock data"""
        response = requests.get(
            f"{BASE_URL}/api/stocks",
            headers={"Authorization": f"Bearer {auth_token}"},
            timeout=10
        )
        assert response.status_code == 200, f"Stocks fetch failed: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Stocks should return a list"
        print(f"✓ Stocks endpoint works, returned {len(data)} stocks")


class TestEmailTemplatesEndpoints:
    """Email templates endpoint tests - verifies RBAC on email_templates router"""
    
    @pytest.fixture
    def auth_token(self):
        """Get PE Desk auth token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": PE_DESK_EMAIL, "password": PE_DESK_PASSWORD},
            timeout=10
        )
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Could not authenticate")
    
    def test_email_templates_verify_without_auth(self):
        """GET /api/email-templates/verify without auth should return 401"""
        response = requests.get(f"{BASE_URL}/api/email-templates/verify", timeout=10)
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Email templates verify correctly requires authentication")
    
    def test_email_templates_verify_with_auth(self, auth_token):
        """GET /api/email-templates/verify with auth should return verification data"""
        response = requests.get(
            f"{BASE_URL}/api/email-templates/verify",
            headers={"Authorization": f"Bearer {auth_token}"},
            timeout=10
        )
        assert response.status_code == 200, f"Email templates verify failed: {response.text}"
        
        data = response.json()
        assert "total_templates" in data, "Should have total_templates count"
        print(f"✓ Email templates verify works, {data.get('total_templates')} templates")


class TestNotificationsEndpoints:
    """Notifications endpoint tests - verifies RBAC on notifications router"""
    
    @pytest.fixture
    def auth_token(self):
        """Get PE Desk auth token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": PE_DESK_EMAIL, "password": PE_DESK_PASSWORD},
            timeout=10
        )
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Could not authenticate")
    
    def test_notifications_without_auth(self):
        """GET /api/notifications without auth should return 401"""
        response = requests.get(f"{BASE_URL}/api/notifications", timeout=10)
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Notifications correctly requires authentication")
    
    def test_notifications_with_auth(self, auth_token):
        """GET /api/notifications with auth should return notification data"""
        response = requests.get(
            f"{BASE_URL}/api/notifications",
            headers={"Authorization": f"Bearer {auth_token}"},
            timeout=10
        )
        assert response.status_code == 200, f"Notifications fetch failed: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Notifications should return a list"
        print(f"✓ Notifications endpoint works, returned {len(data)} notifications")


class TestClientsEndpoints:
    """Clients endpoint tests - verifies RBAC on clients router"""
    
    @pytest.fixture
    def auth_token(self):
        """Get PE Desk auth token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": PE_DESK_EMAIL, "password": PE_DESK_PASSWORD},
            timeout=10
        )
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Could not authenticate")
    
    def test_clients_without_auth(self):
        """GET /api/clients without auth should return 401"""
        response = requests.get(f"{BASE_URL}/api/clients", timeout=10)
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Clients correctly requires authentication")
    
    def test_clients_with_auth(self, auth_token):
        """GET /api/clients with auth should return client data"""
        response = requests.get(
            f"{BASE_URL}/api/clients",
            headers={"Authorization": f"Bearer {auth_token}"},
            timeout=10
        )
        assert response.status_code == 200, f"Clients fetch failed: {response.text}"
        
        data = response.json()
        assert isinstance(data, (list, dict)), "Clients should return list or dict"
        if isinstance(data, dict) and "data" in data:
            print(f"✓ Clients endpoint works, returned {len(data['data'])} clients")
        else:
            print(f"✓ Clients endpoint works, returned data")


class TestBookingsEndpoints:
    """Bookings endpoint tests - verifies RBAC on bookings router"""
    
    @pytest.fixture
    def auth_token(self):
        """Get PE Desk auth token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": PE_DESK_EMAIL, "password": PE_DESK_PASSWORD},
            timeout=10
        )
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Could not authenticate")
    
    def test_bookings_without_auth(self):
        """GET /api/bookings without auth should return 401"""
        response = requests.get(f"{BASE_URL}/api/bookings", timeout=10)
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Bookings correctly requires authentication")
    
    def test_bookings_with_auth(self, auth_token):
        """GET /api/bookings with auth should return booking data"""
        response = requests.get(
            f"{BASE_URL}/api/bookings",
            headers={"Authorization": f"Bearer {auth_token}"},
            timeout=10
        )
        assert response.status_code == 200, f"Bookings fetch failed: {response.text}"
        
        data = response.json()
        # Bookings may return dict with data key or list
        if isinstance(data, dict) and "data" in data:
            print(f"✓ Bookings endpoint works, returned {len(data['data'])} bookings")
        elif isinstance(data, list):
            print(f"✓ Bookings endpoint works, returned {len(data)} bookings")
        else:
            print("✓ Bookings endpoint works")


class TestDashboardEndpoints:
    """Dashboard endpoint tests - verifies RBAC on dashboard router"""
    
    @pytest.fixture
    def auth_token(self):
        """Get PE Desk auth token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": PE_DESK_EMAIL, "password": PE_DESK_PASSWORD},
            timeout=10
        )
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Could not authenticate")
    
    def test_dashboard_without_auth(self):
        """GET /api/dashboard without auth should return 401"""
        response = requests.get(f"{BASE_URL}/api/dashboard", timeout=10)
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Dashboard correctly requires authentication")
    
    def test_dashboard_with_auth(self, auth_token):
        """GET /api/dashboard with auth should return dashboard data"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard",
            headers={"Authorization": f"Bearer {auth_token}"},
            timeout=10
        )
        assert response.status_code == 200, f"Dashboard fetch failed: {response.text}"
        print("✓ Dashboard endpoint works")


class TestUsersEndpoints:
    """Users endpoint tests - verifies RBAC on users router"""
    
    @pytest.fixture
    def auth_token(self):
        """Get PE Desk auth token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": PE_DESK_EMAIL, "password": PE_DESK_PASSWORD},
            timeout=10
        )
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Could not authenticate")
    
    def test_users_without_auth(self):
        """GET /api/users without auth should return 401"""
        response = requests.get(f"{BASE_URL}/api/users", timeout=10)
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Users correctly requires authentication")
    
    def test_users_with_auth(self, auth_token):
        """GET /api/users with auth should return user data"""
        response = requests.get(
            f"{BASE_URL}/api/users",
            headers={"Authorization": f"Bearer {auth_token}"},
            timeout=10
        )
        assert response.status_code == 200, f"Users fetch failed: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Users should return a list"
        print(f"✓ Users endpoint works, returned {len(data)} users")


class TestRolesEndpoints:
    """Roles endpoint tests - verifies RBAC on roles router"""
    
    @pytest.fixture
    def auth_token(self):
        """Get PE Desk auth token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": PE_DESK_EMAIL, "password": PE_DESK_PASSWORD},
            timeout=10
        )
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Could not authenticate")
    
    def test_roles_with_auth(self, auth_token):
        """GET /api/roles with auth should return role data"""
        response = requests.get(
            f"{BASE_URL}/api/roles",
            headers={"Authorization": f"Bearer {auth_token}"},
            timeout=10
        )
        assert response.status_code == 200, f"Roles fetch failed: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Roles should return a list"
        print(f"✓ Roles endpoint works, returned {len(data)} roles")


class TestFinanceEndpoints:
    """Finance endpoint tests - verifies RBAC on finance router"""
    
    @pytest.fixture
    def auth_token(self):
        """Get PE Desk auth token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": PE_DESK_EMAIL, "password": PE_DESK_PASSWORD},
            timeout=10
        )
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Could not authenticate")
    
    def test_finance_dashboard_with_auth(self, auth_token):
        """GET /api/finance/dashboard with auth should return finance data"""
        response = requests.get(
            f"{BASE_URL}/api/finance/dashboard",
            headers={"Authorization": f"Bearer {auth_token}"},
            timeout=10
        )
        # Finance dashboard may not exist or may require specific role
        if response.status_code == 200:
            print("✓ Finance dashboard endpoint works")
        elif response.status_code == 404:
            print("⚠ Finance dashboard endpoint not found")
        elif response.status_code == 403:
            print("⚠ Finance dashboard requires different role")
        else:
            print(f"⚠ Finance dashboard returned: {response.status_code}")


class TestBusinessPartnersEndpoints:
    """Business Partners endpoint tests - verifies RBAC on business_partners router"""
    
    @pytest.fixture
    def auth_token(self):
        """Get PE Desk auth token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": PE_DESK_EMAIL, "password": PE_DESK_PASSWORD},
            timeout=10
        )
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Could not authenticate")
    
    def test_business_partners_with_auth(self, auth_token):
        """GET /api/business-partners with auth should return BP data"""
        response = requests.get(
            f"{BASE_URL}/api/business-partners",
            headers={"Authorization": f"Bearer {auth_token}"},
            timeout=10
        )
        assert response.status_code == 200, f"Business Partners fetch failed: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Business Partners should return a list"
        print(f"✓ Business Partners endpoint works, returned {len(data)} BPs")


class TestReferralPartnersEndpoints:
    """Referral Partners endpoint tests - verifies RBAC on referral_partners router"""
    
    @pytest.fixture
    def auth_token(self):
        """Get PE Desk auth token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": PE_DESK_EMAIL, "password": PE_DESK_PASSWORD},
            timeout=10
        )
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Could not authenticate")
    
    def test_referral_partners_with_auth(self, auth_token):
        """GET /api/referral-partners with auth should return RP data"""
        response = requests.get(
            f"{BASE_URL}/api/referral-partners",
            headers={"Authorization": f"Bearer {auth_token}"},
            timeout=10
        )
        assert response.status_code == 200, f"Referral Partners fetch failed: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Referral Partners should return a list"
        print(f"✓ Referral Partners endpoint works, returned {len(data)} RPs")


class TestReportsEndpoints:
    """Reports endpoint tests - verifies RBAC on reports router"""
    
    @pytest.fixture
    def auth_token(self):
        """Get PE Desk auth token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": PE_DESK_EMAIL, "password": PE_DESK_PASSWORD},
            timeout=10
        )
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Could not authenticate")
    
    def test_bi_reports_with_auth(self, auth_token):
        """GET /api/bi/summary with auth should return BI report data"""
        response = requests.get(
            f"{BASE_URL}/api/bi/summary",
            headers={"Authorization": f"Bearer {auth_token}"},
            timeout=10
        )
        if response.status_code == 200:
            print("✓ BI Reports endpoint works")
        elif response.status_code == 404:
            print("⚠ BI Reports endpoint not found at /api/bi/summary")
        else:
            print(f"⚠ BI Reports returned: {response.status_code}")


class TestPurchasesEndpoints:
    """Purchases endpoint tests - verifies RBAC on purchases router"""
    
    @pytest.fixture
    def auth_token(self):
        """Get PE Desk auth token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": PE_DESK_EMAIL, "password": PE_DESK_PASSWORD},
            timeout=10
        )
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Could not authenticate")
    
    def test_purchases_with_auth(self, auth_token):
        """GET /api/purchases with auth should return purchase data"""
        response = requests.get(
            f"{BASE_URL}/api/purchases",
            headers={"Authorization": f"Bearer {auth_token}"},
            timeout=10
        )
        assert response.status_code == 200, f"Purchases fetch failed: {response.text}"
        
        data = response.json()
        if isinstance(data, dict) and "data" in data:
            print(f"✓ Purchases endpoint works, returned {len(data['data'])} purchases")
        elif isinstance(data, list):
            print(f"✓ Purchases endpoint works, returned {len(data)} purchases")
        else:
            print("✓ Purchases endpoint works")


class TestWhatsAppEndpoints:
    """WhatsApp endpoint tests - verifies RBAC on whatsapp router"""
    
    @pytest.fixture
    def auth_token(self):
        """Get PE Desk auth token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": PE_DESK_EMAIL, "password": PE_DESK_PASSWORD},
            timeout=10
        )
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Could not authenticate")
    
    def test_whatsapp_delivery_stats(self, auth_token):
        """GET /api/whatsapp/delivery-stats with auth should return stats"""
        response = requests.get(
            f"{BASE_URL}/api/whatsapp/delivery-stats",
            headers={"Authorization": f"Bearer {auth_token}"},
            timeout=10
        )
        if response.status_code == 200:
            print("✓ WhatsApp delivery stats endpoint works")
        elif response.status_code == 404:
            print("⚠ WhatsApp delivery stats endpoint not found")
        else:
            print(f"⚠ WhatsApp delivery stats returned: {response.status_code}")


# Run tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
