"""
Backend Regression Test Suite - Iteration 29

Tests all major API endpoints after server.py refactoring:
- Authentication (Login with PE Desk)
- RP Approval Workflow (pending, approve, reject)
- RP CRUD (create, list, approved list)
- Bookings API
- Clients API
- Finance API (dashboard, RP payments, employee commissions)
- Stocks API
- Inventory API
- Dashboard API
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


class TestAuthentication:
    """Test authentication endpoints"""
    
    def test_01_login_pe_desk_success(self):
        """Test PE Desk login with valid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": PE_DESK_EMAIL,
            "password": PE_DESK_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        
        data = response.json()
        assert "token" in data, "Token not in response"
        assert "user" in data, "User not in response"
        assert data["user"]["email"] == PE_DESK_EMAIL
        assert data["user"]["role"] == 1, "PE Desk should have role 1"
        assert data["user"]["role_name"] == "PE Desk"
        
        # Store token for other tests
        TestAuthentication.token = data["token"]
        TestAuthentication.user_id = data["user"]["id"]
        print(f"✓ PE Desk login successful, user_id: {data['user']['id']}")
    
    def test_02_login_invalid_credentials(self):
        """Test login with invalid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "invalid@smifs.com",
            "password": "wrongpassword"
        })
        assert response.status_code == 401, "Should return 401 for invalid credentials"
        print("✓ Invalid credentials correctly rejected")
    
    def test_03_get_current_user(self):
        """Test /auth/me endpoint"""
        headers = {"Authorization": f"Bearer {TestAuthentication.token}"}
        response = requests.get(f"{BASE_URL}/api/auth/me", headers=headers)
        
        assert response.status_code == 200, f"Get me failed: {response.text}"
        data = response.json()
        assert data["email"] == PE_DESK_EMAIL
        assert data["role"] == 1
        print("✓ Get current user successful")


class TestDashboard:
    """Test dashboard endpoints"""
    
    def test_01_get_dashboard_stats(self):
        """Test dashboard stats endpoint"""
        headers = {"Authorization": f"Bearer {TestAuthentication.token}"}
        response = requests.get(f"{BASE_URL}/api/dashboard/stats", headers=headers)
        
        assert response.status_code == 200, f"Dashboard stats failed: {response.text}"
        data = response.json()
        
        # Verify expected fields exist
        expected_fields = ["total_clients", "total_stocks", "total_bookings", "total_inventory_value"]
        for field in expected_fields:
            assert field in data, f"Missing field: {field}"
        
        print(f"✓ Dashboard stats: {data.get('total_clients')} clients, {data.get('total_stocks')} stocks, {data.get('total_bookings')} bookings")
    
    def test_02_get_dashboard_analytics(self):
        """Test dashboard analytics endpoint"""
        headers = {"Authorization": f"Bearer {TestAuthentication.token}"}
        response = requests.get(f"{BASE_URL}/api/dashboard/analytics", headers=headers)
        
        assert response.status_code == 200, f"Dashboard analytics failed: {response.text}"
        print("✓ Dashboard analytics endpoint working")


class TestClients:
    """Test clients API endpoints"""
    
    def test_01_get_clients_list(self):
        """Test get clients list"""
        headers = {"Authorization": f"Bearer {TestAuthentication.token}"}
        response = requests.get(f"{BASE_URL}/api/clients", headers=headers)
        
        assert response.status_code == 200, f"Get clients failed: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        
        TestClients.client_count = len(data)
        if len(data) > 0:
            TestClients.sample_client = data[0]
            print(f"✓ Got {len(data)} clients, sample: {data[0].get('name', 'N/A')}")
        else:
            print(f"✓ Got {len(data)} clients (empty list)")
    
    def test_02_get_client_by_id(self):
        """Test get single client by ID"""
        if not hasattr(TestClients, 'sample_client'):
            pytest.skip("No clients available to test")
        
        headers = {"Authorization": f"Bearer {TestAuthentication.token}"}
        client_id = TestClients.sample_client["id"]
        response = requests.get(f"{BASE_URL}/api/clients/{client_id}", headers=headers)
        
        assert response.status_code == 200, f"Get client failed: {response.text}"
        data = response.json()
        assert data["id"] == client_id
        print(f"✓ Got client by ID: {data.get('name')}")


class TestStocks:
    """Test stocks API endpoints"""
    
    def test_01_get_stocks_list(self):
        """Test get stocks list"""
        headers = {"Authorization": f"Bearer {TestAuthentication.token}"}
        response = requests.get(f"{BASE_URL}/api/stocks", headers=headers)
        
        assert response.status_code == 200, f"Get stocks failed: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        
        TestStocks.stock_count = len(data)
        if len(data) > 0:
            TestStocks.sample_stock = data[0]
            print(f"✓ Got {len(data)} stocks, sample: {data[0].get('symbol', 'N/A')}")
        else:
            print(f"✓ Got {len(data)} stocks (empty list)")
    
    def test_02_get_stock_by_id(self):
        """Test get single stock by ID"""
        if not hasattr(TestStocks, 'sample_stock'):
            pytest.skip("No stocks available to test")
        
        headers = {"Authorization": f"Bearer {TestAuthentication.token}"}
        stock_id = TestStocks.sample_stock["id"]
        response = requests.get(f"{BASE_URL}/api/stocks/{stock_id}", headers=headers)
        
        assert response.status_code == 200, f"Get stock failed: {response.text}"
        data = response.json()
        assert data["id"] == stock_id
        print(f"✓ Got stock by ID: {data.get('symbol')}")


class TestInventory:
    """Test inventory API endpoints"""
    
    def test_01_get_inventory_list(self):
        """Test get inventory list"""
        headers = {"Authorization": f"Bearer {TestAuthentication.token}"}
        response = requests.get(f"{BASE_URL}/api/inventory", headers=headers)
        
        assert response.status_code == 200, f"Get inventory failed: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        
        TestInventory.inventory_count = len(data)
        print(f"✓ Got {len(data)} inventory items")


class TestBookings:
    """Test bookings API endpoints"""
    
    def test_01_get_bookings_list(self):
        """Test get bookings list"""
        headers = {"Authorization": f"Bearer {TestAuthentication.token}"}
        response = requests.get(f"{BASE_URL}/api/bookings", headers=headers)
        
        assert response.status_code == 200, f"Get bookings failed: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        
        TestBookings.booking_count = len(data)
        if len(data) > 0:
            TestBookings.sample_booking = data[0]
            print(f"✓ Got {len(data)} bookings, sample: {data[0].get('booking_number', 'N/A')}")
        else:
            print(f"✓ Got {len(data)} bookings (empty list)")
    
    def test_02_get_booking_by_id(self):
        """Test get single booking by ID"""
        if not hasattr(TestBookings, 'sample_booking'):
            pytest.skip("No bookings available to test")
        
        headers = {"Authorization": f"Bearer {TestAuthentication.token}"}
        booking_id = TestBookings.sample_booking["id"]
        response = requests.get(f"{BASE_URL}/api/bookings/{booking_id}", headers=headers)
        
        assert response.status_code == 200, f"Get booking failed: {response.text}"
        data = response.json()
        assert data["id"] == booking_id
        print(f"✓ Got booking by ID: {data.get('booking_number')}")


class TestReferralPartners:
    """Test Referral Partners CRUD and approval workflow"""
    
    def test_01_get_rp_list(self):
        """Test get all referral partners"""
        headers = {"Authorization": f"Bearer {TestAuthentication.token}"}
        response = requests.get(f"{BASE_URL}/api/referral-partners", headers=headers)
        
        assert response.status_code == 200, f"Get RPs failed: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        
        TestReferralPartners.rp_count = len(data)
        print(f"✓ Got {len(data)} referral partners")
    
    def test_02_get_approved_rps(self):
        """Test get approved referral partners"""
        headers = {"Authorization": f"Bearer {TestAuthentication.token}"}
        response = requests.get(f"{BASE_URL}/api/referral-partners-approved", headers=headers)
        
        assert response.status_code == 200, f"Get approved RPs failed: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        
        # All returned RPs should be approved and active
        for rp in data:
            assert rp.get("approval_status") == "approved", f"RP {rp.get('rp_code')} is not approved"
            assert rp.get("is_active") == True, f"RP {rp.get('rp_code')} is not active"
        
        print(f"✓ Got {len(data)} approved referral partners")
    
    def test_03_get_pending_rps(self):
        """Test get pending referral partners (PE Level only)"""
        headers = {"Authorization": f"Bearer {TestAuthentication.token}"}
        response = requests.get(f"{BASE_URL}/api/referral-partners-pending", headers=headers)
        
        assert response.status_code == 200, f"Get pending RPs failed: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        
        # All returned RPs should be pending
        for rp in data:
            assert rp.get("approval_status") == "pending", f"RP {rp.get('rp_code')} is not pending"
        
        TestReferralPartners.pending_count = len(data)
        if len(data) > 0:
            TestReferralPartners.pending_rp = data[0]
        print(f"✓ Got {len(data)} pending referral partners")
    
    def test_04_create_rp_for_approval_test(self):
        """Create a new RP for approval workflow testing"""
        headers = {"Authorization": f"Bearer {TestAuthentication.token}"}
        
        # Generate unique test data
        unique_id = str(uuid.uuid4())[:8]
        # Generate unique 12-digit Aadhar using timestamp
        timestamp = str(int(datetime.now().timestamp()))[-12:]
        aadhar = timestamp.zfill(12)
        
        test_rp = {
            "name": f"TEST_RP_{unique_id}",
            "email": f"test_rp_{unique_id}@example.com",
            "phone": "9876543210",
            "pan_number": f"ABCDE{unique_id[:4].upper()}F",
            "aadhar_number": aadhar,
            "address": "Test Address, Test City"
        }
        
        response = requests.post(f"{BASE_URL}/api/referral-partners", headers=headers, json=test_rp)
        
        assert response.status_code == 200, f"Create RP failed: {response.text}"
        data = response.json()
        
        # PE Desk creates auto-approved RPs
        assert data.get("approval_status") == "approved", "PE Desk created RP should be auto-approved"
        assert "rp_code" in data, "RP code should be generated"
        
        TestReferralPartners.created_rp_id = data["id"]
        TestReferralPartners.created_rp_code = data["rp_code"]
        print(f"✓ Created RP: {data['rp_code']} (auto-approved by PE Desk)")
    
    def test_05_approve_rp_workflow(self):
        """Test RP approval workflow"""
        # First, we need a pending RP to approve
        # Since PE Desk auto-approves, we'll test the endpoint with an already approved RP
        # which should return an error
        
        if not hasattr(TestReferralPartners, 'created_rp_id'):
            pytest.skip("No RP created to test approval")
        
        headers = {"Authorization": f"Bearer {TestAuthentication.token}"}
        
        # Try to approve an already approved RP - should fail
        response = requests.put(
            f"{BASE_URL}/api/referral-partners/{TestReferralPartners.created_rp_id}/approve",
            headers=headers,
            json={"approve": True}
        )
        
        # Should return 400 because RP is already approved
        assert response.status_code == 400, f"Expected 400 for already approved RP, got {response.status_code}"
        print("✓ Approval workflow correctly rejects already approved RP")
    
    def test_06_reject_rp_requires_reason(self):
        """Test that rejecting RP requires a reason"""
        if not hasattr(TestReferralPartners, 'pending_rp'):
            pytest.skip("No pending RP to test rejection")
        
        headers = {"Authorization": f"Bearer {TestAuthentication.token}"}
        
        # Try to reject without reason
        response = requests.put(
            f"{BASE_URL}/api/referral-partners/{TestReferralPartners.pending_rp['id']}/approve",
            headers=headers,
            json={"approve": False}  # No rejection_reason
        )
        
        assert response.status_code == 400, f"Expected 400 for rejection without reason, got {response.status_code}"
        print("✓ Rejection correctly requires a reason")
    
    def test_07_get_rp_by_id(self):
        """Test get single RP by ID"""
        if not hasattr(TestReferralPartners, 'created_rp_id'):
            pytest.skip("No RP created to test")
        
        headers = {"Authorization": f"Bearer {TestAuthentication.token}"}
        response = requests.get(
            f"{BASE_URL}/api/referral-partners/{TestReferralPartners.created_rp_id}",
            headers=headers
        )
        
        assert response.status_code == 200, f"Get RP failed: {response.text}"
        data = response.json()
        assert data["id"] == TestReferralPartners.created_rp_id
        assert data["rp_code"] == TestReferralPartners.created_rp_code
        print(f"✓ Got RP by ID: {data['rp_code']}")


class TestFinance:
    """Test Finance API endpoints"""
    
    def test_01_get_finance_summary(self):
        """Test finance summary endpoint"""
        headers = {"Authorization": f"Bearer {TestAuthentication.token}"}
        response = requests.get(f"{BASE_URL}/api/finance/summary", headers=headers)
        
        assert response.status_code == 200, f"Finance summary failed: {response.text}"
        data = response.json()
        
        # Verify expected fields
        expected_fields = ["total_received", "total_sent", "net_flow", "client_payments_count", "vendor_payments_count"]
        for field in expected_fields:
            assert field in data, f"Missing field: {field}"
        
        print(f"✓ Finance summary: received={data.get('total_received')}, sent={data.get('total_sent')}")
    
    def test_02_get_finance_payments(self):
        """Test get all payments"""
        headers = {"Authorization": f"Bearer {TestAuthentication.token}"}
        response = requests.get(f"{BASE_URL}/api/finance/payments", headers=headers)
        
        assert response.status_code == 200, f"Finance payments failed: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        
        print(f"✓ Got {len(data)} finance payments")
    
    def test_03_get_rp_payments(self):
        """Test get RP payments"""
        headers = {"Authorization": f"Bearer {TestAuthentication.token}"}
        response = requests.get(f"{BASE_URL}/api/finance/rp-payments", headers=headers)
        
        assert response.status_code == 200, f"RP payments failed: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        
        print(f"✓ Got {len(data)} RP payments")
    
    def test_04_get_rp_payments_summary(self):
        """Test get RP payments summary"""
        headers = {"Authorization": f"Bearer {TestAuthentication.token}"}
        response = requests.get(f"{BASE_URL}/api/finance/rp-payments/summary", headers=headers)
        
        assert response.status_code == 200, f"RP payments summary failed: {response.text}"
        data = response.json()
        
        expected_fields = ["pending_count", "pending_amount", "paid_count", "paid_amount", "total_count", "total_amount"]
        for field in expected_fields:
            assert field in data, f"Missing field: {field}"
        
        print(f"✓ RP payments summary: pending={data.get('pending_count')}, paid={data.get('paid_count')}")
    
    def test_05_get_employee_commissions(self):
        """Test get employee commissions"""
        headers = {"Authorization": f"Bearer {TestAuthentication.token}"}
        response = requests.get(f"{BASE_URL}/api/finance/employee-commissions", headers=headers)
        
        assert response.status_code == 200, f"Employee commissions failed: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        
        print(f"✓ Got {len(data)} employee commissions")
    
    def test_06_get_employee_commissions_summary(self):
        """Test get employee commissions summary"""
        headers = {"Authorization": f"Bearer {TestAuthentication.token}"}
        response = requests.get(f"{BASE_URL}/api/finance/employee-commissions/summary", headers=headers)
        
        assert response.status_code == 200, f"Employee commissions summary failed: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        
        print(f"✓ Got employee commissions summary for {len(data)} employees")
    
    def test_07_get_refund_requests(self):
        """Test get refund requests"""
        headers = {"Authorization": f"Bearer {TestAuthentication.token}"}
        response = requests.get(f"{BASE_URL}/api/finance/refund-requests", headers=headers)
        
        assert response.status_code == 200, f"Refund requests failed: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        
        print(f"✓ Got {len(data)} refund requests")


class TestUsers:
    """Test user management endpoints"""
    
    def test_01_get_users_list(self):
        """Test get users list (admin only)"""
        headers = {"Authorization": f"Bearer {TestAuthentication.token}"}
        response = requests.get(f"{BASE_URL}/api/users", headers=headers)
        
        assert response.status_code == 200, f"Get users failed: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        
        # Verify PE Desk user exists
        pe_desk_found = any(u.get("email") == PE_DESK_EMAIL for u in data)
        assert pe_desk_found, "PE Desk user should be in the list"
        
        print(f"✓ Got {len(data)} users")
    
    def test_02_get_employees_list(self):
        """Test get employees list"""
        headers = {"Authorization": f"Bearer {TestAuthentication.token}"}
        response = requests.get(f"{BASE_URL}/api/employees", headers=headers)
        
        assert response.status_code == 200, f"Get employees failed: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        
        print(f"✓ Got {len(data)} employees")


class TestNotifications:
    """Test notification endpoints"""
    
    def test_01_get_notifications(self):
        """Test get notifications"""
        headers = {"Authorization": f"Bearer {TestAuthentication.token}"}
        response = requests.get(f"{BASE_URL}/api/notifications", headers=headers)
        
        assert response.status_code == 200, f"Get notifications failed: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        
        print(f"✓ Got {len(data)} notifications")
    
    def test_02_get_unread_count(self):
        """Test get unread notification count"""
        headers = {"Authorization": f"Bearer {TestAuthentication.token}"}
        response = requests.get(f"{BASE_URL}/api/notifications/unread-count", headers=headers)
        
        assert response.status_code == 200, f"Get unread count failed: {response.text}"
        data = response.json()
        assert "count" in data, "Response should have count field"
        
        print(f"✓ Unread notifications: {data.get('count')}")


class TestAuditLogs:
    """Test audit log endpoints"""
    
    def test_01_get_audit_logs(self):
        """Test get audit logs"""
        headers = {"Authorization": f"Bearer {TestAuthentication.token}"}
        response = requests.get(f"{BASE_URL}/api/audit-logs", headers=headers)
        
        assert response.status_code == 200, f"Get audit logs failed: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        
        print(f"✓ Got {len(data)} audit logs")


class TestEmailTemplates:
    """Test email template endpoints"""
    
    def test_01_get_email_templates(self):
        """Test get email templates"""
        headers = {"Authorization": f"Bearer {TestAuthentication.token}"}
        response = requests.get(f"{BASE_URL}/api/email-templates", headers=headers)
        
        assert response.status_code == 200, f"Get email templates failed: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        
        # Verify new RP approval/rejection templates exist
        template_keys = [t.get("key") for t in data]
        assert "rp_approval_notification" in template_keys, "RP approval template should exist"
        assert "rp_rejection_notification" in template_keys, "RP rejection template should exist"
        
        print(f"✓ Got {len(data)} email templates (including RP approval/rejection)")


class TestCleanup:
    """Cleanup test data"""
    
    def test_99_cleanup_test_rp(self):
        """Cleanup test RP created during tests"""
        if not hasattr(TestReferralPartners, 'created_rp_id'):
            pytest.skip("No test RP to cleanup")
        
        # Note: We don't delete the RP as it might be needed for audit trail
        # Just deactivate it
        headers = {"Authorization": f"Bearer {TestAuthentication.token}"}
        response = requests.put(
            f"{BASE_URL}/api/referral-partners/{TestReferralPartners.created_rp_id}/toggle-active",
            headers=headers,
            params={"is_active": False}
        )
        
        if response.status_code == 200:
            print(f"✓ Deactivated test RP: {TestReferralPartners.created_rp_code}")
        else:
            print(f"⚠ Could not deactivate test RP: {response.text}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
