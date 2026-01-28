"""
Test Finance Role (7) and PE Manager Vendor Access
Tests for:
1. Finance role (7) can access Finance page
2. Finance role can view/update refund requests
3. Finance role CANNOT access Vendors
4. Finance role has employee-like rights (create bookings, view clients)
5. PE Manager (role 2) can access Vendors page
6. PE Manager can create/edit vendors
7. PE Manager CANNOT delete vendors (should return 403)
8. PE Manager can access Finance page
9. User Management shows Finance role in dropdown
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestFinanceRoleAndVendorAccess:
    """Test Finance role permissions and PE Manager vendor access"""
    
    # Test credentials
    PE_DESK_EMAIL = "pedesk@smifs.com"
    PE_DESK_PASSWORD = "Kutta@123"
    PE_MANAGER_EMAIL = "pemanager@smifs.com"
    PE_MANAGER_PASSWORD = "Manager@123"
    FINANCE_EMAIL = "finance@smifs.com"
    FINANCE_PASSWORD = "Finance@123"
    
    # Store tokens
    pe_desk_token = None
    pe_manager_token = None
    finance_token = None
    
    # Test data
    test_vendor_id = "3db2feac-9f8f-4a55-a056-a4551aa10ee3"
    created_vendor_id = None
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    # ==================== LOGIN TESTS ====================
    
    def test_01_pe_desk_login(self):
        """Test PE Desk login"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": self.PE_DESK_EMAIL,
            "password": self.PE_DESK_PASSWORD
        })
        assert response.status_code == 200, f"PE Desk login failed: {response.text}"
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == 1
        TestFinanceRoleAndVendorAccess.pe_desk_token = data["token"]
        print(f"✓ PE Desk login successful - Role: {data['user']['role_name']}")
    
    def test_02_pe_manager_login(self):
        """Test PE Manager login"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": self.PE_MANAGER_EMAIL,
            "password": self.PE_MANAGER_PASSWORD
        })
        assert response.status_code == 200, f"PE Manager login failed: {response.text}"
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == 2
        TestFinanceRoleAndVendorAccess.pe_manager_token = data["token"]
        print(f"✓ PE Manager login successful - Role: {data['user']['role_name']}")
    
    def test_03_finance_login(self):
        """Test Finance user login"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": self.FINANCE_EMAIL,
            "password": self.FINANCE_PASSWORD
        })
        assert response.status_code == 200, f"Finance login failed: {response.text}"
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == 7, f"Expected role 7, got {data['user']['role']}"
        assert data["user"]["role_name"] == "Finance"
        TestFinanceRoleAndVendorAccess.finance_token = data["token"]
        print(f"✓ Finance login successful - Role: {data['user']['role_name']}")
    
    # ==================== FINANCE ROLE TESTS ====================
    
    def test_04_finance_can_access_finance_page(self):
        """Finance role (7) can access Finance page - GET /api/finance/payments"""
        self.session.headers.update({"Authorization": f"Bearer {TestFinanceRoleAndVendorAccess.finance_token}"})
        response = self.session.get(f"{BASE_URL}/api/finance/payments")
        assert response.status_code == 200, f"Finance role cannot access finance page: {response.text}"
        print("✓ Finance role can access Finance page (GET /api/finance/payments)")
    
    def test_05_finance_can_view_refund_requests(self):
        """Finance role can view refund requests"""
        self.session.headers.update({"Authorization": f"Bearer {TestFinanceRoleAndVendorAccess.finance_token}"})
        response = self.session.get(f"{BASE_URL}/api/finance/refund-requests")
        assert response.status_code == 200, f"Finance role cannot view refund requests: {response.text}"
        print("✓ Finance role can view refund requests")
    
    def test_06_finance_can_view_finance_summary(self):
        """Finance role can view finance summary"""
        self.session.headers.update({"Authorization": f"Bearer {TestFinanceRoleAndVendorAccess.finance_token}"})
        response = self.session.get(f"{BASE_URL}/api/finance/summary")
        assert response.status_code == 200, f"Finance role cannot view finance summary: {response.text}"
        data = response.json()
        # Verify summary has expected fields
        assert "total_received" in data
        assert "total_sent" in data
        assert "net_flow" in data
        print("✓ Finance role can view finance summary")
    
    def test_07_finance_cannot_access_vendors(self):
        """Finance role CANNOT access Vendors (is_vendor=True)"""
        self.session.headers.update({"Authorization": f"Bearer {TestFinanceRoleAndVendorAccess.finance_token}"})
        response = self.session.get(f"{BASE_URL}/api/clients?is_vendor=true")
        assert response.status_code == 403, f"Finance role should NOT access vendors, got {response.status_code}"
        print("✓ Finance role correctly denied access to vendors (403)")
    
    def test_08_finance_can_view_clients(self):
        """Finance role can view clients (employee-like rights)"""
        self.session.headers.update({"Authorization": f"Bearer {TestFinanceRoleAndVendorAccess.finance_token}"})
        response = self.session.get(f"{BASE_URL}/api/clients")
        assert response.status_code == 200, f"Finance role cannot view clients: {response.text}"
        # Verify no vendors in response
        clients = response.json()
        for client in clients:
            assert client.get("is_vendor") == False, "Finance role should not see vendors in client list"
        print(f"✓ Finance role can view clients ({len(clients)} clients)")
    
    def test_09_finance_can_view_inventory(self):
        """Finance role can view inventory"""
        self.session.headers.update({"Authorization": f"Bearer {TestFinanceRoleAndVendorAccess.finance_token}"})
        response = self.session.get(f"{BASE_URL}/api/inventory")
        assert response.status_code == 200, f"Finance role cannot view inventory: {response.text}"
        print("✓ Finance role can view inventory")
    
    def test_10_finance_can_view_bookings(self):
        """Finance role can view bookings"""
        self.session.headers.update({"Authorization": f"Bearer {TestFinanceRoleAndVendorAccess.finance_token}"})
        response = self.session.get(f"{BASE_URL}/api/bookings")
        assert response.status_code == 200, f"Finance role cannot view bookings: {response.text}"
        print("✓ Finance role can view bookings")
    
    # ==================== PE MANAGER VENDOR ACCESS TESTS ====================
    
    def test_11_pe_manager_can_access_vendors(self):
        """PE Manager (role 2) can access Vendors page"""
        self.session.headers.update({"Authorization": f"Bearer {TestFinanceRoleAndVendorAccess.pe_manager_token}"})
        response = self.session.get(f"{BASE_URL}/api/clients?is_vendor=true")
        assert response.status_code == 200, f"PE Manager cannot access vendors: {response.text}"
        vendors = response.json()
        print(f"✓ PE Manager can access Vendors page ({len(vendors)} vendors)")
    
    def test_12_pe_manager_can_create_vendor(self):
        """PE Manager can create vendors"""
        self.session.headers.update({"Authorization": f"Bearer {TestFinanceRoleAndVendorAccess.pe_manager_token}"})
        vendor_data = {
            "name": "TEST_PM_Vendor_Create",
            "email": "test_pm_vendor@test.com",
            "phone": "9876543210",
            "pan_number": "TESTPM001V",
            "dp_id": "TESTPM001DP",
            "dp_type": "outside",
            "is_vendor": True,
            "bank_accounts": [{
                "bank_name": "Test Bank",
                "account_number": "1234567890",
                "ifsc_code": "TEST0001234",
                "account_holder_name": "Test PM Vendor"
            }]
        }
        response = self.session.post(f"{BASE_URL}/api/clients", json=vendor_data)
        assert response.status_code == 200, f"PE Manager cannot create vendor: {response.text}"
        data = response.json()
        TestFinanceRoleAndVendorAccess.created_vendor_id = data["id"]
        print(f"✓ PE Manager can create vendor (ID: {data['id']})")
    
    def test_13_pe_manager_can_edit_vendor(self):
        """PE Manager can edit vendors"""
        if not TestFinanceRoleAndVendorAccess.created_vendor_id:
            pytest.skip("No vendor created to edit")
        
        self.session.headers.update({"Authorization": f"Bearer {TestFinanceRoleAndVendorAccess.pe_manager_token}"})
        update_data = {
            "name": "TEST_PM_Vendor_Updated",
            "email": "test_pm_vendor_updated@test.com",
            "phone": "9876543211",
            "pan_number": "TESTPM001V",
            "dp_id": "TESTPM001DP",
            "dp_type": "outside",
            "is_vendor": True
        }
        response = self.session.put(
            f"{BASE_URL}/api/clients/{TestFinanceRoleAndVendorAccess.created_vendor_id}",
            json=update_data
        )
        assert response.status_code == 200, f"PE Manager cannot edit vendor: {response.text}"
        data = response.json()
        assert data["name"] == "TEST_PM_Vendor_Updated"
        print("✓ PE Manager can edit vendor")
    
    def test_14_pe_manager_cannot_delete_vendor(self):
        """PE Manager CANNOT delete vendors (should return 403)"""
        # Use the provided vendor ID for deletion test
        vendor_id = self.test_vendor_id
        if TestFinanceRoleAndVendorAccess.created_vendor_id:
            vendor_id = TestFinanceRoleAndVendorAccess.created_vendor_id
        
        self.session.headers.update({"Authorization": f"Bearer {TestFinanceRoleAndVendorAccess.pe_manager_token}"})
        response = self.session.delete(f"{BASE_URL}/api/clients/{vendor_id}")
        assert response.status_code == 403, f"PE Manager should NOT be able to delete vendors, got {response.status_code}: {response.text}"
        print("✓ PE Manager correctly denied vendor deletion (403)")
    
    def test_15_pe_manager_can_access_finance(self):
        """PE Manager can access Finance page"""
        self.session.headers.update({"Authorization": f"Bearer {TestFinanceRoleAndVendorAccess.pe_manager_token}"})
        response = self.session.get(f"{BASE_URL}/api/finance/payments")
        assert response.status_code == 200, f"PE Manager cannot access finance: {response.text}"
        print("✓ PE Manager can access Finance page")
    
    def test_16_pe_manager_can_view_refund_requests(self):
        """PE Manager can view refund requests"""
        self.session.headers.update({"Authorization": f"Bearer {TestFinanceRoleAndVendorAccess.pe_manager_token}"})
        response = self.session.get(f"{BASE_URL}/api/finance/refund-requests")
        assert response.status_code == 200, f"PE Manager cannot view refund requests: {response.text}"
        print("✓ PE Manager can view refund requests")
    
    # ==================== PE DESK TESTS (BASELINE) ====================
    
    def test_17_pe_desk_can_delete_vendor(self):
        """PE Desk CAN delete vendors (baseline test)"""
        if not TestFinanceRoleAndVendorAccess.created_vendor_id:
            pytest.skip("No vendor created to delete")
        
        self.session.headers.update({"Authorization": f"Bearer {TestFinanceRoleAndVendorAccess.pe_desk_token}"})
        response = self.session.delete(f"{BASE_URL}/api/clients/{TestFinanceRoleAndVendorAccess.created_vendor_id}")
        assert response.status_code == 200, f"PE Desk cannot delete vendor: {response.text}"
        print("✓ PE Desk can delete vendor (baseline)")
    
    # ==================== USER MANAGEMENT TESTS ====================
    
    def test_18_user_management_shows_finance_role(self):
        """User Management shows Finance role in dropdown (via users endpoint)"""
        self.session.headers.update({"Authorization": f"Bearer {TestFinanceRoleAndVendorAccess.pe_desk_token}"})
        response = self.session.get(f"{BASE_URL}/api/users")
        assert response.status_code == 200, f"Cannot get users: {response.text}"
        users = response.json()
        
        # Check if Finance user exists with role 7
        finance_users = [u for u in users if u.get("role") == 7]
        assert len(finance_users) > 0, "No Finance role users found"
        
        # Verify role_name is "Finance"
        for user in finance_users:
            assert user.get("role_name") == "Finance", f"Expected role_name 'Finance', got {user.get('role_name')}"
        
        print(f"✓ User Management shows Finance role ({len(finance_users)} Finance users)")
    
    def test_19_roles_config_includes_finance(self):
        """Verify ROLES config includes Finance (role 7)"""
        # This is a code verification test - we check via the API response
        self.session.headers.update({"Authorization": f"Bearer {TestFinanceRoleAndVendorAccess.pe_desk_token}"})
        response = self.session.get(f"{BASE_URL}/api/auth/me")
        assert response.status_code == 200
        
        # Login as Finance to verify role_name
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": self.FINANCE_EMAIL,
            "password": self.FINANCE_PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        assert data["user"]["role"] == 7
        assert data["user"]["role_name"] == "Finance"
        print("✓ ROLES config includes Finance (role 7)")


class TestFinanceRoleNegativeCases:
    """Negative test cases for Finance role restrictions"""
    
    FINANCE_EMAIL = "finance@smifs.com"
    FINANCE_PASSWORD = "Finance@123"
    finance_token = None
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as Finance
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": self.FINANCE_EMAIL,
            "password": self.FINANCE_PASSWORD
        })
        if response.status_code == 200:
            TestFinanceRoleNegativeCases.finance_token = response.json()["token"]
    
    def test_finance_cannot_create_vendor(self):
        """Finance role cannot create vendors"""
        if not TestFinanceRoleNegativeCases.finance_token:
            pytest.skip("Finance token not available")
        
        self.session.headers.update({"Authorization": f"Bearer {TestFinanceRoleNegativeCases.finance_token}"})
        vendor_data = {
            "name": "TEST_Finance_Vendor",
            "email": "test_finance_vendor@test.com",
            "pan_number": "TESTFIN01V",
            "dp_id": "TESTFIN01DP",
            "dp_type": "outside",
            "is_vendor": True
        }
        response = self.session.post(f"{BASE_URL}/api/clients", json=vendor_data)
        assert response.status_code == 403, f"Finance role should NOT create vendors, got {response.status_code}"
        print("✓ Finance role correctly denied vendor creation (403)")
    
    def test_finance_cannot_access_purchases(self):
        """Finance role cannot access vendor purchases"""
        if not TestFinanceRoleNegativeCases.finance_token:
            pytest.skip("Finance token not available")
        
        self.session.headers.update({"Authorization": f"Bearer {TestFinanceRoleNegativeCases.finance_token}"})
        response = self.session.get(f"{BASE_URL}/api/purchases")
        assert response.status_code == 403, f"Finance role should NOT access purchases, got {response.status_code}"
        print("✓ Finance role correctly denied access to purchases (403)")
    
    def test_finance_cannot_manage_users(self):
        """Finance role cannot manage users"""
        if not TestFinanceRoleNegativeCases.finance_token:
            pytest.skip("Finance token not available")
        
        self.session.headers.update({"Authorization": f"Bearer {TestFinanceRoleNegativeCases.finance_token}"})
        response = self.session.get(f"{BASE_URL}/api/users")
        assert response.status_code == 403, f"Finance role should NOT manage users, got {response.status_code}"
        print("✓ Finance role correctly denied user management (403)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
