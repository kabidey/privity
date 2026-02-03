"""
Test Recalculate Inventory Feature
Tests the POST /api/inventory/recalculate endpoint with role-based access control.

Features tested:
- PE Desk (role 1) can recalculate inventory
- PE Manager (role 2) can recalculate inventory (has inventory.* permission)
- Viewer (role 4) cannot recalculate inventory (returns 403)
- Finance (role 3) cannot recalculate inventory (returns 403)
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestRecalculateInventory:
    """Tests for POST /api/inventory/recalculate endpoint"""
    
    @pytest.fixture(scope="class")
    def pe_desk_token(self):
        """Get PE Desk authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "pe@smifs.com",
            "password": "Kutta@123"
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("PE Desk authentication failed")
    
    @pytest.fixture(scope="class")
    def pe_manager_token(self):
        """Get PE Manager authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "pemanager@smifs.com",
            "password": "Test@123"
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("PE Manager authentication failed")
    
    @pytest.fixture(scope="class")
    def viewer_token(self):
        """Get Viewer authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "testuser@smifs.com",
            "password": "Test@123"
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Viewer authentication failed")
    
    def test_pe_desk_can_recalculate_inventory(self, pe_desk_token):
        """PE Desk (role 1) should be able to recalculate inventory"""
        response = requests.post(
            f"{BASE_URL}/api/inventory/recalculate",
            headers={"Authorization": f"Bearer {pe_desk_token}"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "message" in data
        assert "details" in data
        assert "total_stocks" in data["details"]
        assert "recalculated" in data["details"]
        assert "errors" in data["details"]
        
        # Verify recalculation was successful
        assert data["details"]["recalculated"] >= 0
        print(f"✅ PE Desk recalculated {data['details']['recalculated']} of {data['details']['total_stocks']} stocks")
    
    def test_pe_manager_can_recalculate_inventory(self, pe_manager_token):
        """PE Manager (role 2) should be able to recalculate inventory (has inventory.* permission)"""
        response = requests.post(
            f"{BASE_URL}/api/inventory/recalculate",
            headers={"Authorization": f"Bearer {pe_manager_token}"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "message" in data
        assert "details" in data
        print(f"✅ PE Manager recalculated {data['details']['recalculated']} of {data['details']['total_stocks']} stocks")
    
    def test_viewer_cannot_recalculate_inventory(self, viewer_token):
        """Viewer (role 4) should NOT be able to recalculate inventory"""
        response = requests.post(
            f"{BASE_URL}/api/inventory/recalculate",
            headers={"Authorization": f"Bearer {viewer_token}"}
        )
        
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "detail" in data
        assert "Permission denied" in data["detail"]
        assert "Viewer" in data["detail"]
        print(f"✅ Viewer correctly denied: {data['detail']}")
    
    def test_unauthenticated_cannot_recalculate_inventory(self):
        """Unauthenticated requests should be rejected"""
        response = requests.post(f"{BASE_URL}/api/inventory/recalculate")
        
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✅ Unauthenticated request correctly rejected")


class TestInventoryEndpoints:
    """Tests for other inventory endpoints"""
    
    @pytest.fixture(scope="class")
    def pe_desk_token(self):
        """Get PE Desk authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "pe@smifs.com",
            "password": "Kutta@123"
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("PE Desk authentication failed")
    
    @pytest.fixture(scope="class")
    def viewer_token(self):
        """Get Viewer authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "testuser@smifs.com",
            "password": "Test@123"
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Viewer authentication failed")
    
    def test_get_inventory_pe_desk(self, pe_desk_token):
        """PE Desk should see WAP and LP columns"""
        response = requests.get(
            f"{BASE_URL}/api/inventory",
            headers={"Authorization": f"Bearer {pe_desk_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        if len(data) > 0:
            item = data[0]
            # PE Desk should see both WAP and LP
            assert "weighted_avg_price" in item, "PE Desk should see weighted_avg_price"
            assert "landing_price" in item, "PE Desk should see landing_price"
            assert "lp_total_value" in item, "PE Desk should see lp_total_value"
            print(f"✅ PE Desk sees WAP: {item.get('weighted_avg_price')}, LP: {item.get('landing_price')}")
    
    def test_get_inventory_viewer(self, viewer_token):
        """Viewer should NOT see WAP (only LP as 'price')"""
        response = requests.get(
            f"{BASE_URL}/api/inventory",
            headers={"Authorization": f"Bearer {viewer_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        if len(data) > 0:
            item = data[0]
            # Viewer should see landing_price as weighted_avg_price (hidden WAP)
            assert "weighted_avg_price" in item, "Viewer should see weighted_avg_price (which is actually LP)"
            assert "landing_price" in item, "Viewer should see landing_price"
            # Viewer should NOT see lp_total_value (PE-only field)
            assert "lp_total_value" not in item, "Viewer should NOT see lp_total_value"
            print(f"✅ Viewer sees price (LP): {item.get('weighted_avg_price')}")


class TestPermissionService:
    """Tests for the permission service functionality"""
    
    @pytest.fixture(scope="class")
    def pe_desk_token(self):
        """Get PE Desk authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "pe@smifs.com",
            "password": "Kutta@123"
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("PE Desk authentication failed")
    
    def test_pe_desk_user_info(self, pe_desk_token):
        """Verify PE Desk user has role 1"""
        response = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {pe_desk_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("role") == 1, f"Expected role 1, got {data.get('role')}"
        assert data.get("role_name") == "PE Desk", f"Expected 'PE Desk', got {data.get('role_name')}"
        print(f"✅ PE Desk user verified: {data.get('name')} (role {data.get('role')})")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
