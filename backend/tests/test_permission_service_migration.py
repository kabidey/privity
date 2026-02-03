"""
Test Permission Service Migration - Regression Tests
Tests that all migrated routers work correctly after permission_service integration.

Routers tested:
- dashboard.py - Dashboard stats and analytics
- bookings.py - Bookings list and CRUD
- clients.py - Clients list and CRUD
- inventory.py - Inventory list and recalculate

Roles tested:
- PE Desk (role 1): Full access
- Viewer (role 4): Read-only access, should get 403 on write operations
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
PE_DESK_CREDS = {"email": "pe@smifs.com", "password": "Kutta@123"}
VIEWER_CREDS = {"email": "testuser@smifs.com", "password": "Test@123"}


class TestAuthSetup:
    """Test authentication and get tokens"""
    
    @pytest.fixture(scope="class")
    def pe_desk_token(self):
        """Get PE Desk authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=PE_DESK_CREDS)
        assert response.status_code == 200, f"PE Desk login failed: {response.text}"
        data = response.json()
        assert "token" in data, "No token in response"
        return data["token"]
    
    @pytest.fixture(scope="class")
    def viewer_token(self):
        """Get Viewer authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=VIEWER_CREDS)
        assert response.status_code == 200, f"Viewer login failed: {response.text}"
        data = response.json()
        assert "token" in data, "No token in response"
        return data["token"]
    
    def test_pe_desk_login(self, pe_desk_token):
        """Verify PE Desk can login"""
        assert pe_desk_token is not None
        assert len(pe_desk_token) > 0
        print(f"✅ PE Desk login successful")
    
    def test_viewer_login(self, viewer_token):
        """Verify Viewer can login"""
        assert viewer_token is not None
        assert len(viewer_token) > 0
        print(f"✅ Viewer login successful")


class TestDashboardEndpoints:
    """Test dashboard.py endpoints after migration"""
    
    @pytest.fixture(scope="class")
    def pe_desk_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=PE_DESK_CREDS)
        return response.json().get("token")
    
    @pytest.fixture(scope="class")
    def viewer_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=VIEWER_CREDS)
        return response.json().get("token")
    
    def test_dashboard_stats_pe_desk(self, pe_desk_token):
        """PE Desk should access dashboard stats"""
        headers = {"Authorization": f"Bearer {pe_desk_token}"}
        response = requests.get(f"{BASE_URL}/api/dashboard/stats", headers=headers)
        
        assert response.status_code == 200, f"Dashboard stats failed: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "total_clients" in data
        assert "total_stocks" in data
        assert "total_bookings" in data
        assert "total_inventory_value" in data
        print(f"✅ PE Desk dashboard stats: {data.get('total_bookings')} bookings, {data.get('total_clients')} clients")
    
    def test_dashboard_stats_viewer(self, viewer_token):
        """Viewer should also access dashboard stats (read-only)"""
        headers = {"Authorization": f"Bearer {viewer_token}"}
        response = requests.get(f"{BASE_URL}/api/dashboard/stats", headers=headers)
        
        assert response.status_code == 200, f"Viewer dashboard stats failed: {response.text}"
        data = response.json()
        assert "total_clients" in data
        print(f"✅ Viewer can access dashboard stats")
    
    def test_dashboard_analytics_pe_desk(self, pe_desk_token):
        """PE Desk should access dashboard analytics"""
        headers = {"Authorization": f"Bearer {pe_desk_token}"}
        response = requests.get(f"{BASE_URL}/api/dashboard/analytics", headers=headers)
        
        assert response.status_code == 200, f"Dashboard analytics failed: {response.text}"
        data = response.json()
        assert "status_distribution" in data or "recent_bookings" in data
        print(f"✅ PE Desk dashboard analytics accessible")


class TestBookingsEndpoints:
    """Test bookings.py endpoints after migration"""
    
    @pytest.fixture(scope="class")
    def pe_desk_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=PE_DESK_CREDS)
        return response.json().get("token")
    
    @pytest.fixture(scope="class")
    def viewer_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=VIEWER_CREDS)
        return response.json().get("token")
    
    def test_bookings_list_pe_desk(self, pe_desk_token):
        """PE Desk should access bookings list"""
        headers = {"Authorization": f"Bearer {pe_desk_token}"}
        response = requests.get(f"{BASE_URL}/api/bookings", headers=headers)
        
        assert response.status_code == 200, f"Bookings list failed: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Bookings should be a list"
        print(f"✅ PE Desk bookings list: {len(data)} bookings")
    
    def test_bookings_list_viewer(self, viewer_token):
        """Viewer should access bookings list (read-only)"""
        headers = {"Authorization": f"Bearer {viewer_token}"}
        response = requests.get(f"{BASE_URL}/api/bookings", headers=headers)
        
        assert response.status_code == 200, f"Viewer bookings list failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"✅ Viewer can access bookings list: {len(data)} bookings")
    
    def test_bookings_list_with_filters(self, pe_desk_token):
        """PE Desk should access bookings with filters"""
        headers = {"Authorization": f"Bearer {pe_desk_token}"}
        response = requests.get(f"{BASE_URL}/api/bookings?status=open", headers=headers)
        
        assert response.status_code == 200, f"Filtered bookings failed: {response.text}"
        print(f"✅ PE Desk filtered bookings accessible")


class TestClientsEndpoints:
    """Test clients.py endpoints after migration"""
    
    @pytest.fixture(scope="class")
    def pe_desk_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=PE_DESK_CREDS)
        return response.json().get("token")
    
    @pytest.fixture(scope="class")
    def viewer_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=VIEWER_CREDS)
        return response.json().get("token")
    
    def test_clients_list_pe_desk(self, pe_desk_token):
        """PE Desk should access clients list"""
        headers = {"Authorization": f"Bearer {pe_desk_token}"}
        response = requests.get(f"{BASE_URL}/api/clients", headers=headers)
        
        assert response.status_code == 200, f"Clients list failed: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Clients should be a list"
        print(f"✅ PE Desk clients list: {len(data)} clients")
    
    def test_clients_list_viewer(self, viewer_token):
        """Viewer should access clients list (read-only)"""
        headers = {"Authorization": f"Bearer {viewer_token}"}
        response = requests.get(f"{BASE_URL}/api/clients", headers=headers)
        
        assert response.status_code == 200, f"Viewer clients list failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"✅ Viewer can access clients list: {len(data)} clients")


class TestInventoryEndpoints:
    """Test inventory.py endpoints after migration"""
    
    @pytest.fixture(scope="class")
    def pe_desk_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=PE_DESK_CREDS)
        return response.json().get("token")
    
    @pytest.fixture(scope="class")
    def viewer_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=VIEWER_CREDS)
        return response.json().get("token")
    
    def test_inventory_list_pe_desk(self, pe_desk_token):
        """PE Desk should access inventory list with WAP and LP"""
        headers = {"Authorization": f"Bearer {pe_desk_token}"}
        response = requests.get(f"{BASE_URL}/api/inventory", headers=headers)
        
        assert response.status_code == 200, f"Inventory list failed: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Inventory should be a list"
        
        # PE Desk should see both WAP and LP
        if len(data) > 0:
            item = data[0]
            assert "weighted_avg_price" in item or "landing_price" in item
        print(f"✅ PE Desk inventory list: {len(data)} items")
    
    def test_inventory_list_viewer(self, viewer_token):
        """Viewer should access inventory list (LP only, no WAP)"""
        headers = {"Authorization": f"Bearer {viewer_token}"}
        response = requests.get(f"{BASE_URL}/api/inventory", headers=headers)
        
        assert response.status_code == 200, f"Viewer inventory list failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"✅ Viewer can access inventory list: {len(data)} items")
    
    def test_recalculate_inventory_pe_desk(self, pe_desk_token):
        """PE Desk should be able to recalculate inventory"""
        headers = {"Authorization": f"Bearer {pe_desk_token}"}
        response = requests.post(f"{BASE_URL}/api/inventory/recalculate", headers=headers)
        
        assert response.status_code == 200, f"Recalculate inventory failed: {response.text}"
        data = response.json()
        assert "message" in data
        assert "recalculated" in data.get("message", "").lower() or "details" in data
        print(f"✅ PE Desk recalculate inventory: {data.get('message')}")
    
    def test_recalculate_inventory_viewer_forbidden(self, viewer_token):
        """Viewer should get 403 with descriptive message when trying to recalculate"""
        headers = {"Authorization": f"Bearer {viewer_token}"}
        response = requests.post(f"{BASE_URL}/api/inventory/recalculate", headers=headers)
        
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify descriptive error message with role name
        detail = data.get("detail", "")
        assert "permission" in detail.lower() or "denied" in detail.lower(), f"Expected permission denied message, got: {detail}"
        assert "viewer" in detail.lower() or "role" in detail.lower(), f"Expected role name in message, got: {detail}"
        print(f"✅ Viewer correctly denied recalculate: {detail}")


class TestPermissionServiceIntegration:
    """Test that permission_service is properly integrated"""
    
    @pytest.fixture(scope="class")
    def pe_desk_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=PE_DESK_CREDS)
        return response.json().get("token")
    
    @pytest.fixture(scope="class")
    def viewer_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=VIEWER_CREDS)
        return response.json().get("token")
    
    def test_pe_desk_user_info(self, pe_desk_token):
        """Verify PE Desk user has correct role"""
        headers = {"Authorization": f"Bearer {pe_desk_token}"}
        response = requests.get(f"{BASE_URL}/api/auth/me", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("role") == 1, f"PE Desk should have role 1, got {data.get('role')}"
        print(f"✅ PE Desk user verified: role={data.get('role')}, name={data.get('name')}")
    
    def test_viewer_user_info(self, viewer_token):
        """Verify Viewer user has correct role"""
        headers = {"Authorization": f"Bearer {viewer_token}"}
        response = requests.get(f"{BASE_URL}/api/auth/me", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("role") == 4, f"Viewer should have role 4, got {data.get('role')}"
        print(f"✅ Viewer user verified: role={data.get('role')}, name={data.get('name')}")
    
    def test_unauthenticated_access_denied(self):
        """Unauthenticated requests should be denied"""
        response = requests.get(f"{BASE_URL}/api/dashboard/stats")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print(f"✅ Unauthenticated access correctly denied")
    
    def test_invalid_token_denied(self):
        """Invalid token should be denied"""
        headers = {"Authorization": "Bearer invalid_token_12345"}
        response = requests.get(f"{BASE_URL}/api/dashboard/stats", headers=headers)
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print(f"✅ Invalid token correctly denied")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
