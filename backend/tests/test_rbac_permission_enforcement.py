"""
RBAC Permission Enforcement Tests
Tests that granular permissions are properly enforced on backend API endpoints.

Test Users:
- PE Desk Admin (pe@smifs.com / Kutta@123) - Has wildcard (*) permission, full access
- Employee (employee@test.com / Test@123) - Limited permissions, should be denied restricted endpoints
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
PE_DESK_EMAIL = "pe@smifs.com"
PE_DESK_PASSWORD = "Kutta@123"

# Viewer user (role 4) - has limited permissions
VIEWER_EMAIL = "testuser@smifs.com"
VIEWER_PASSWORD = "Test@123"


class TestRBACPermissionEnforcement:
    """Test RBAC permission enforcement on backend API endpoints"""
    
    pe_desk_token = None
    viewer_token = None
    
    @classmethod
    def setup_class(cls):
        """Login both users and get tokens"""
        # Login PE Desk Admin
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": PE_DESK_EMAIL, "password": PE_DESK_PASSWORD}
        )
        if response.status_code == 200:
            cls.pe_desk_token = response.json().get("token")
            print(f"✓ PE Desk login successful")
        else:
            print(f"✗ PE Desk login failed: {response.status_code} - {response.text}")
        
        time.sleep(1)  # Rate limiting protection
        
        # Login Viewer
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": VIEWER_EMAIL, "password": VIEWER_PASSWORD}
        )
        if response.status_code == 200:
            cls.viewer_token = response.json().get("token")
            print(f"✓ Viewer login successful")
        else:
            print(f"✗ Viewer login failed: {response.status_code} - {response.text}")
    
    def get_pe_desk_headers(self):
        """Get headers with PE Desk token"""
        return {"Authorization": f"Bearer {self.pe_desk_token}", "Content-Type": "application/json"}
    
    def get_viewer_headers(self):
        """Get headers with Viewer token"""
        return {"Authorization": f"Bearer {self.viewer_token}", "Content-Type": "application/json"}
    
    # ============== BOOKINGS PERMISSION TESTS ==============
    
    def test_pe_desk_can_access_pending_approval_bookings(self):
        """PE Desk should be able to access /api/bookings/pending-approval"""
        if not self.pe_desk_token:
            pytest.skip("PE Desk token not available")
        
        response = requests.get(
            f"{BASE_URL}/api/bookings",
            params={"approval_status": "pending"},
            headers=self.get_pe_desk_headers()
        )
        assert response.status_code == 200, f"PE Desk should access bookings: {response.text}"
        print(f"✓ PE Desk can access bookings (status: {response.status_code})")
    
    def test_pe_desk_can_access_dp_ready_bookings(self):
        """PE Desk should be able to access /api/bookings/dp-ready (requires dp.view_receivables)"""
        if not self.pe_desk_token:
            pytest.skip("PE Desk token not available")
        
        response = requests.get(
            f"{BASE_URL}/api/bookings/dp-ready",
            headers=self.get_pe_desk_headers()
        )
        assert response.status_code == 200, f"PE Desk should access DP ready bookings: {response.text}"
        print(f"✓ PE Desk can access DP ready bookings (status: {response.status_code})")
    
    def test_pe_desk_can_access_dp_transferred_bookings(self):
        """PE Desk should be able to access /api/bookings/dp-transferred (requires dp.view_transfers)"""
        if not self.pe_desk_token:
            pytest.skip("PE Desk token not available")
        
        response = requests.get(
            f"{BASE_URL}/api/bookings/dp-transferred",
            headers=self.get_pe_desk_headers()
        )
        assert response.status_code == 200, f"PE Desk should access DP transferred bookings: {response.text}"
        print(f"✓ PE Desk can access DP transferred bookings (status: {response.status_code})")
    
    def test_viewer_denied_dp_ready_bookings(self):
        """Viewer should be denied access to /api/bookings/dp-ready (requires dp.view_receivables)"""
        if not self.viewer_token:
            pytest.skip("Viewer token not available")
        
        response = requests.get(
            f"{BASE_URL}/api/bookings/dp-ready",
            headers=self.get_viewer_headers()
        )
        # Should return 403 Forbidden
        assert response.status_code == 403, f"Viewer should be denied DP ready bookings: {response.status_code} - {response.text}"
        print(f"✓ Viewer correctly denied DP ready bookings (status: {response.status_code})")
    
    def test_viewer_denied_dp_transferred_bookings(self):
        """Viewer should be denied access to /api/bookings/dp-transferred (requires dp.view_transfers)"""
        if not self.viewer_token:
            pytest.skip("Viewer token not available")
        
        response = requests.get(
            f"{BASE_URL}/api/bookings/dp-transferred",
            headers=self.get_viewer_headers()
        )
        # Should return 403 Forbidden
        assert response.status_code == 403, f"Viewer should be denied DP transferred bookings: {response.status_code} - {response.text}"
        print(f"✓ Viewer correctly denied DP transferred bookings (status: {response.status_code})")
    
    # ============== AUDIT LOGS PERMISSION TESTS ==============
    
    def test_pe_desk_can_access_audit_logs(self):
        """PE Desk should be able to access /api/audit-logs (requires audit_logs.view)"""
        if not self.pe_desk_token:
            pytest.skip("PE Desk token not available")
        
        response = requests.get(
            f"{BASE_URL}/api/audit-logs",
            headers=self.get_pe_desk_headers()
        )
        assert response.status_code == 200, f"PE Desk should access audit logs: {response.text}"
        print(f"✓ PE Desk can access audit logs (status: {response.status_code})")
    
    def test_viewer_denied_audit_logs(self):
        """Viewer should be denied access to /api/audit-logs (requires audit_logs.view)"""
        if not self.viewer_token:
            pytest.skip("Viewer token not available")
        
        response = requests.get(
            f"{BASE_URL}/api/audit-logs",
            headers=self.get_viewer_headers()
        )
        # Should return 403 Forbidden
        assert response.status_code == 403, f"Viewer should be denied audit logs: {response.status_code} - {response.text}"
        print(f"✓ Viewer correctly denied audit logs (status: {response.status_code})")
    
    # ============== DATABASE BACKUP PERMISSION TESTS ==============
    
    def test_pe_desk_can_access_database_backups(self):
        """PE Desk should be able to access /api/database/backups (requires database_backup.view)"""
        if not self.pe_desk_token:
            pytest.skip("PE Desk token not available")
        
        response = requests.get(
            f"{BASE_URL}/api/database/backups",
            headers=self.get_pe_desk_headers()
        )
        assert response.status_code == 200, f"PE Desk should access database backups: {response.text}"
        print(f"✓ PE Desk can access database backups (status: {response.status_code})")
    
    def test_pe_desk_can_access_database_stats(self):
        """PE Desk should be able to access /api/database/stats (requires database_backup.view)"""
        if not self.pe_desk_token:
            pytest.skip("PE Desk token not available")
        
        response = requests.get(
            f"{BASE_URL}/api/database/stats",
            headers=self.get_pe_desk_headers()
        )
        assert response.status_code == 200, f"PE Desk should access database stats: {response.text}"
        print(f"✓ PE Desk can access database stats (status: {response.status_code})")
    
    def test_viewer_denied_database_backups(self):
        """Viewer should be denied access to /api/database/backups (requires database_backup.view)"""
        if not self.viewer_token:
            pytest.skip("Viewer token not available")
        
        response = requests.get(
            f"{BASE_URL}/api/database/backups",
            headers=self.get_viewer_headers()
        )
        # Should return 403 Forbidden
        assert response.status_code == 403, f"Viewer should be denied database backups: {response.status_code} - {response.text}"
        print(f"✓ Viewer correctly denied database backups (status: {response.status_code})")
    
    def test_viewer_denied_database_stats(self):
        """Viewer should be denied access to /api/database/stats (requires database_backup.view)"""
        if not self.viewer_token:
            pytest.skip("Viewer token not available")
        
        response = requests.get(
            f"{BASE_URL}/api/database/stats",
            headers=self.get_viewer_headers()
        )
        # Should return 403 Forbidden
        assert response.status_code == 403, f"Viewer should be denied database stats: {response.status_code} - {response.text}"
        print(f"✓ Viewer correctly denied database stats (status: {response.status_code})")
    
    # ============== USER MANAGEMENT PERMISSION TESTS ==============
    
    def test_pe_desk_can_access_users_list(self):
        """PE Desk should be able to access /api/users (requires users.view)"""
        if not self.pe_desk_token:
            pytest.skip("PE Desk token not available")
        
        response = requests.get(
            f"{BASE_URL}/api/users",
            headers=self.get_pe_desk_headers()
        )
        assert response.status_code == 200, f"PE Desk should access users list: {response.text}"
        print(f"✓ PE Desk can access users list (status: {response.status_code})")
    
    def test_viewer_denied_users_list(self):
        """Viewer should be denied access to /api/users (requires users.view)"""
        if not self.viewer_token:
            pytest.skip("Viewer token not available")
        
        response = requests.get(
            f"{BASE_URL}/api/users",
            headers=self.get_viewer_headers()
        )
        # Should return 403 Forbidden
        assert response.status_code == 403, f"Viewer should be denied users list: {response.status_code} - {response.text}"
        print(f"✓ Viewer correctly denied users list (status: {response.status_code})")
    
    # ============== CLIENT APPROVAL PERMISSION TESTS ==============
    
    def test_pe_desk_can_access_pending_clients(self):
        """PE Desk should be able to access /api/clients/pending-approval (requires client_approval.view)"""
        if not self.pe_desk_token:
            pytest.skip("PE Desk token not available")
        
        response = requests.get(
            f"{BASE_URL}/api/clients/pending-approval",
            headers=self.get_pe_desk_headers()
        )
        assert response.status_code == 200, f"PE Desk should access pending clients: {response.text}"
        print(f"✓ PE Desk can access pending clients (status: {response.status_code})")
    
    def test_viewer_denied_pending_clients(self):
        """Viewer should be denied access to /api/clients/pending-approval (requires client_approval.view)"""
        if not self.viewer_token:
            pytest.skip("Viewer token not available")
        
        response = requests.get(
            f"{BASE_URL}/api/clients/pending-approval",
            headers=self.get_viewer_headers()
        )
        # Should return 403 Forbidden
        assert response.status_code == 403, f"Viewer should be denied pending clients: {response.status_code} - {response.text}"
        print(f"✓ Viewer correctly denied pending clients (status: {response.status_code})")
    
    # ============== CONTRACT NOTES PERMISSION TESTS ==============
    
    def test_pe_desk_can_access_contract_notes(self):
        """PE Desk should be able to access /api/contract-notes (requires contract_notes.view)"""
        if not self.pe_desk_token:
            pytest.skip("PE Desk token not available")
        
        response = requests.get(
            f"{BASE_URL}/api/contract-notes",
            headers=self.get_pe_desk_headers()
        )
        assert response.status_code == 200, f"PE Desk should access contract notes: {response.text}"
        print(f"✓ PE Desk can access contract notes (status: {response.status_code})")
    
    def test_employee_denied_contract_notes(self):
        """Employee should be denied access to /api/contract-notes (requires contract_notes.view)"""
        if not self.employee_token:
            pytest.skip("Employee token not available")
        
        response = requests.get(
            f"{BASE_URL}/api/contract-notes",
            headers=self.get_employee_headers()
        )
        # Should return 403 Forbidden
        assert response.status_code == 403, f"Employee should be denied contract notes: {response.status_code} - {response.text}"
        print(f"✓ Employee correctly denied contract notes (status: {response.status_code})")
    
    # ============== FINANCE PERMISSION TESTS ==============
    
    def test_pe_desk_can_access_finance_payments(self):
        """PE Desk should be able to access /api/finance/payments (requires finance.view)"""
        if not self.pe_desk_token:
            pytest.skip("PE Desk token not available")
        
        response = requests.get(
            f"{BASE_URL}/api/finance/payments",
            headers=self.get_pe_desk_headers()
        )
        assert response.status_code == 200, f"PE Desk should access finance payments: {response.text}"
        print(f"✓ PE Desk can access finance payments (status: {response.status_code})")
    
    def test_employee_denied_finance_payments(self):
        """Employee should be denied access to /api/finance/payments (requires finance.view)"""
        if not self.employee_token:
            pytest.skip("Employee token not available")
        
        response = requests.get(
            f"{BASE_URL}/api/finance/payments",
            headers=self.get_employee_headers()
        )
        # Should return 403 Forbidden
        assert response.status_code == 403, f"Employee should be denied finance payments: {response.status_code} - {response.text}"
        print(f"✓ Employee correctly denied finance payments (status: {response.status_code})")
    
    # ============== INVENTORY PERMISSION TESTS ==============
    
    def test_pe_desk_can_access_inventory(self):
        """PE Desk should be able to access /api/inventory"""
        if not self.pe_desk_token:
            pytest.skip("PE Desk token not available")
        
        response = requests.get(
            f"{BASE_URL}/api/inventory",
            headers=self.get_pe_desk_headers()
        )
        assert response.status_code == 200, f"PE Desk should access inventory: {response.text}"
        print(f"✓ PE Desk can access inventory (status: {response.status_code})")
    
    def test_employee_can_access_inventory_view(self):
        """Employee should be able to access /api/inventory (has inventory.view)"""
        if not self.employee_token:
            pytest.skip("Employee token not available")
        
        response = requests.get(
            f"{BASE_URL}/api/inventory",
            headers=self.get_employee_headers()
        )
        # Employee should have inventory.view permission
        assert response.status_code == 200, f"Employee should access inventory view: {response.status_code} - {response.text}"
        print(f"✓ Employee can access inventory view (status: {response.status_code})")
    
    def test_employee_denied_inventory_recalculate(self):
        """Employee should be denied access to POST /api/inventory/recalculate (requires inventory.recalculate)"""
        if not self.employee_token:
            pytest.skip("Employee token not available")
        
        response = requests.post(
            f"{BASE_URL}/api/inventory/recalculate",
            headers=self.get_employee_headers()
        )
        # Should return 403 Forbidden
        assert response.status_code == 403, f"Employee should be denied inventory recalculate: {response.status_code} - {response.text}"
        print(f"✓ Employee correctly denied inventory recalculate (status: {response.status_code})")
    
    # ============== CLIENTS PERMISSION TESTS ==============
    
    def test_pe_desk_can_access_clients(self):
        """PE Desk should be able to access /api/clients"""
        if not self.pe_desk_token:
            pytest.skip("PE Desk token not available")
        
        response = requests.get(
            f"{BASE_URL}/api/clients",
            headers=self.get_pe_desk_headers()
        )
        assert response.status_code == 200, f"PE Desk should access clients: {response.text}"
        print(f"✓ PE Desk can access clients (status: {response.status_code})")
    
    def test_employee_can_access_clients_view(self):
        """Employee should be able to access /api/clients (has clients.view)"""
        if not self.employee_token:
            pytest.skip("Employee token not available")
        
        response = requests.get(
            f"{BASE_URL}/api/clients",
            headers=self.get_employee_headers()
        )
        # Employee should have clients.view permission
        assert response.status_code == 200, f"Employee should access clients view: {response.status_code} - {response.text}"
        print(f"✓ Employee can access clients view (status: {response.status_code})")
    
    # ============== STOCKS PERMISSION TESTS ==============
    
    def test_pe_desk_can_access_stocks(self):
        """PE Desk should be able to access /api/stocks"""
        if not self.pe_desk_token:
            pytest.skip("PE Desk token not available")
        
        response = requests.get(
            f"{BASE_URL}/api/stocks",
            headers=self.get_pe_desk_headers()
        )
        assert response.status_code == 200, f"PE Desk should access stocks: {response.text}"
        print(f"✓ PE Desk can access stocks (status: {response.status_code})")
    
    def test_employee_can_access_stocks_view(self):
        """Employee should be able to access /api/stocks (has stocks.view)"""
        if not self.employee_token:
            pytest.skip("Employee token not available")
        
        response = requests.get(
            f"{BASE_URL}/api/stocks",
            headers=self.get_employee_headers()
        )
        # Employee should have stocks.view permission
        assert response.status_code == 200, f"Employee should access stocks view: {response.status_code} - {response.text}"
        print(f"✓ Employee can access stocks view (status: {response.status_code})")
    
    # ============== PURCHASES PERMISSION TESTS ==============
    
    def test_pe_desk_can_access_purchases(self):
        """PE Desk should be able to access /api/purchases"""
        if not self.pe_desk_token:
            pytest.skip("PE Desk token not available")
        
        response = requests.get(
            f"{BASE_URL}/api/purchases",
            headers=self.get_pe_desk_headers()
        )
        assert response.status_code == 200, f"PE Desk should access purchases: {response.text}"
        print(f"✓ PE Desk can access purchases (status: {response.status_code})")
    
    def test_employee_denied_purchases(self):
        """Employee should be denied access to /api/purchases (requires purchases.view)"""
        if not self.employee_token:
            pytest.skip("Employee token not available")
        
        response = requests.get(
            f"{BASE_URL}/api/purchases",
            headers=self.get_employee_headers()
        )
        # Employee doesn't have purchases.view permission
        assert response.status_code == 403, f"Employee should be denied purchases: {response.status_code} - {response.text}"
        print(f"✓ Employee correctly denied purchases (status: {response.status_code})")
    
    # ============== ERROR MESSAGE QUALITY TESTS ==============
    
    def test_permission_denied_error_message_is_descriptive(self):
        """Permission denied error should include role name and action description"""
        if not self.employee_token:
            pytest.skip("Employee token not available")
        
        response = requests.get(
            f"{BASE_URL}/api/audit-logs",
            headers=self.get_employee_headers()
        )
        
        assert response.status_code == 403
        error_detail = response.json().get("detail", "")
        
        # Error message should be descriptive
        assert "Permission denied" in error_detail, f"Error should mention 'Permission denied': {error_detail}"
        assert "role" in error_detail.lower() or "permission" in error_detail.lower(), f"Error should mention role or permission: {error_detail}"
        print(f"✓ Permission denied error is descriptive: {error_detail}")


class TestBookingApprovalPermissions:
    """Test booking approval specific permissions"""
    
    pe_desk_token = None
    employee_token = None
    
    @classmethod
    def setup_class(cls):
        """Login both users"""
        # Login PE Desk
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": PE_DESK_EMAIL, "password": PE_DESK_PASSWORD}
        )
        if response.status_code == 200:
            cls.pe_desk_token = response.json().get("token")
        
        time.sleep(0.5)
        
        # Login Employee
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": EMPLOYEE_EMAIL, "password": EMPLOYEE_PASSWORD}
        )
        if response.status_code == 200:
            cls.employee_token = response.json().get("token")
    
    def get_pe_desk_headers(self):
        return {"Authorization": f"Bearer {self.pe_desk_token}", "Content-Type": "application/json"}
    
    def get_employee_headers(self):
        return {"Authorization": f"Bearer {self.employee_token}", "Content-Type": "application/json"}
    
    def test_employee_cannot_approve_booking(self):
        """Employee should not be able to approve bookings (requires bookings.approve)"""
        if not self.employee_token:
            pytest.skip("Employee token not available")
        
        # Try to approve a non-existent booking - should fail with 403 before 404
        response = requests.put(
            f"{BASE_URL}/api/bookings/fake-booking-id/approve",
            params={"approve": True},
            headers=self.get_employee_headers()
        )
        
        # Should return 403 Forbidden (permission check happens before booking lookup)
        assert response.status_code == 403, f"Employee should be denied booking approval: {response.status_code} - {response.text}"
        print(f"✓ Employee correctly denied booking approval (status: {response.status_code})")
    
    def test_employee_cannot_void_booking(self):
        """Employee should not be able to void bookings (requires bookings.delete)"""
        if not self.employee_token:
            pytest.skip("Employee token not available")
        
        # Try to void a non-existent booking - should fail with 403 before 404
        response = requests.put(
            f"{BASE_URL}/api/bookings/fake-booking-id/void",
            params={"reason": "Test void"},
            headers=self.get_employee_headers()
        )
        
        # Should return 403 Forbidden
        assert response.status_code == 403, f"Employee should be denied booking void: {response.status_code} - {response.text}"
        print(f"✓ Employee correctly denied booking void (status: {response.status_code})")


class TestClientApprovalPermissions:
    """Test client approval specific permissions"""
    
    pe_desk_token = None
    employee_token = None
    
    @classmethod
    def setup_class(cls):
        """Login both users"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": PE_DESK_EMAIL, "password": PE_DESK_PASSWORD}
        )
        if response.status_code == 200:
            cls.pe_desk_token = response.json().get("token")
        
        time.sleep(0.5)
        
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": EMPLOYEE_EMAIL, "password": EMPLOYEE_PASSWORD}
        )
        if response.status_code == 200:
            cls.employee_token = response.json().get("token")
    
    def get_employee_headers(self):
        return {"Authorization": f"Bearer {self.employee_token}", "Content-Type": "application/json"}
    
    def test_employee_cannot_approve_client(self):
        """Employee should not be able to approve clients (requires client_approval.approve)"""
        if not self.employee_token:
            pytest.skip("Employee token not available")
        
        # Try to approve a non-existent client - should fail with 403 before 404
        response = requests.put(
            f"{BASE_URL}/api/clients/fake-client-id/approve",
            params={"approve": True},
            headers=self.get_employee_headers()
        )
        
        # Should return 403 Forbidden
        assert response.status_code == 403, f"Employee should be denied client approval: {response.status_code} - {response.text}"
        print(f"✓ Employee correctly denied client approval (status: {response.status_code})")
    
    def test_employee_cannot_delete_client(self):
        """Employee should not be able to delete clients (requires clients.delete)"""
        if not self.employee_token:
            pytest.skip("Employee token not available")
        
        # Try to delete a non-existent client - should fail with 403 before 404
        response = requests.delete(
            f"{BASE_URL}/api/clients/fake-client-id",
            headers=self.get_employee_headers()
        )
        
        # Should return 403 Forbidden
        assert response.status_code == 403, f"Employee should be denied client delete: {response.status_code} - {response.text}"
        print(f"✓ Employee correctly denied client delete (status: {response.status_code})")


class TestDatabaseBackupPermissions:
    """Test database backup specific permissions"""
    
    pe_desk_token = None
    employee_token = None
    
    @classmethod
    def setup_class(cls):
        """Login both users"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": PE_DESK_EMAIL, "password": PE_DESK_PASSWORD}
        )
        if response.status_code == 200:
            cls.pe_desk_token = response.json().get("token")
        
        time.sleep(0.5)
        
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": EMPLOYEE_EMAIL, "password": EMPLOYEE_PASSWORD}
        )
        if response.status_code == 200:
            cls.employee_token = response.json().get("token")
    
    def get_pe_desk_headers(self):
        return {"Authorization": f"Bearer {self.pe_desk_token}", "Content-Type": "application/json"}
    
    def get_employee_headers(self):
        return {"Authorization": f"Bearer {self.employee_token}", "Content-Type": "application/json"}
    
    def test_employee_cannot_create_backup(self):
        """Employee should not be able to create database backups (requires database_backup.create)"""
        if not self.employee_token:
            pytest.skip("Employee token not available")
        
        response = requests.post(
            f"{BASE_URL}/api/database/backups",
            json={"name": "Test Backup", "description": "Test"},
            headers=self.get_employee_headers()
        )
        
        # Should return 403 Forbidden
        assert response.status_code == 403, f"Employee should be denied backup creation: {response.status_code} - {response.text}"
        print(f"✓ Employee correctly denied backup creation (status: {response.status_code})")
    
    def test_employee_cannot_clear_database(self):
        """Employee should not be able to clear database (requires database_backup.clear)"""
        if not self.employee_token:
            pytest.skip("Employee token not available")
        
        response = requests.delete(
            f"{BASE_URL}/api/database/clear",
            headers=self.get_employee_headers()
        )
        
        # Should return 403 Forbidden
        assert response.status_code == 403, f"Employee should be denied database clear: {response.status_code} - {response.text}"
        print(f"✓ Employee correctly denied database clear (status: {response.status_code})")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
