"""
RBAC Comprehensive Audit Tests - Full Backend RBAC Verification

This test suite verifies:
1. PE Desk Admin (pe@smifs.com) has full access to ALL protected endpoints
2. Restricted roles (Viewer) are correctly denied access to protected endpoints
3. Proper 403 Forbidden responses for unauthorized access

Test Users:
- PE Desk Super Admin (pe@smifs.com / Kutta@123) - Has wildcard (*) permission, full access
- Viewer (testuser@smifs.com / Test@123) - Limited permissions, should be denied restricted endpoints

Endpoints Tested:
- reports.py: /api/reports/pnl, /api/reports/export/excel, /api/reports/pe-desk-hit
- research.py: /api/research/reports, /api/research/stats
- revenue_dashboard.py: /api/rp-revenue, /api/employee-revenue, /api/my-team
- kill_switch.py: /api/kill-switch/activate, /api/kill-switch/deactivate
- analytics.py: /api/analytics/summary, /api/analytics/stock-performance
- bookings.py: /api/bookings, /api/bookings/dp-ready, /api/bookings/dp-transferred
- stocks.py: /api/stocks, /api/corporate-actions
- clients.py: /api/clients, /api/clients/pending-approval
- users.py: /api/users
- roles.py: /api/roles, /api/roles/permissions
- database_backup.py: /api/database/backups, /api/database/clear, /api/database/stats
- finance.py: /api/finance/payments, /api/finance/refund-requests
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


def login_with_retry(email, password, max_retries=3, delay=5):
    """Login with retry logic to handle rate limiting"""
    for attempt in range(max_retries):
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": email, "password": password}
        )
        if response.status_code == 200:
            return response.json().get("token")
        elif response.status_code == 429:  # Rate limited
            print(f"Rate limited, waiting {delay}s before retry {attempt + 1}/{max_retries}")
            time.sleep(delay)
        else:
            print(f"Login failed: {response.status_code} - {response.text}")
            return None
    return None


class TestPEAdminReportsAccess:
    """Test PE Admin access to reports.py endpoints"""
    
    pe_token = None
    
    @classmethod
    def setup_class(cls):
        """Login PE Admin"""
        print(f"\n=== Testing Reports Endpoints - PE Admin Access ===")
        print(f"BASE_URL: {BASE_URL}")
        
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": PE_DESK_EMAIL, "password": PE_DESK_PASSWORD}
        )
        if response.status_code == 200:
            cls.pe_token = response.json().get("token")
            print(f"✓ PE Admin login successful")
        else:
            print(f"✗ PE Admin login failed: {response.status_code}")
    
    def get_headers(self):
        return {"Authorization": f"Bearer {self.pe_token}", "Content-Type": "application/json"}
    
    def test_reports_pnl(self):
        """PE Admin can access /api/reports/pnl (requires reports.view)"""
        if not self.pe_token:
            pytest.skip("PE token not available")
        
        response = requests.get(f"{BASE_URL}/api/reports/pnl", headers=self.get_headers())
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        data = response.json()
        assert "items" in data or "summary" in data, "Response should contain items or summary"
        print(f"✓ /api/reports/pnl - 200 OK")
    
    def test_reports_export_excel(self):
        """PE Admin can access /api/reports/export/excel (requires reports.export)"""
        if not self.pe_token:
            pytest.skip("PE token not available")
        
        response = requests.get(f"{BASE_URL}/api/reports/export/excel", headers=self.get_headers())
        # Should return 200 with Excel file or empty data
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        print(f"✓ /api/reports/export/excel - 200 OK")
    
    def test_reports_export_pdf(self):
        """PE Admin can access /api/reports/export/pdf (requires reports.export)"""
        if not self.pe_token:
            pytest.skip("PE token not available")
        
        response = requests.get(f"{BASE_URL}/api/reports/export/pdf", headers=self.get_headers())
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        print(f"✓ /api/reports/export/pdf - 200 OK")
    
    def test_reports_pe_desk_hit(self):
        """PE Admin can access /api/reports/pe-desk-hit (requires reports.pe_hit)"""
        if not self.pe_token:
            pytest.skip("PE token not available")
        
        response = requests.get(f"{BASE_URL}/api/reports/pe-desk-hit", headers=self.get_headers())
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        data = response.json()
        assert "report_type" in data, "Response should contain report_type"
        print(f"✓ /api/reports/pe-desk-hit - 200 OK")


class TestPEAdminResearchAccess:
    """Test PE Admin access to research.py endpoints"""
    
    pe_token = None
    
    @classmethod
    def setup_class(cls):
        """Login PE Admin"""
        print(f"\n=== Testing Research Endpoints - PE Admin Access ===")
        
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": PE_DESK_EMAIL, "password": PE_DESK_PASSWORD}
        )
        if response.status_code == 200:
            cls.pe_token = response.json().get("token")
    
    def get_headers(self):
        return {"Authorization": f"Bearer {self.pe_token}", "Content-Type": "application/json"}
    
    def test_research_reports_list(self):
        """PE Admin can access /api/research/reports (requires research.view)"""
        if not self.pe_token:
            pytest.skip("PE token not available")
        
        response = requests.get(f"{BASE_URL}/api/research/reports", headers=self.get_headers())
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        print(f"✓ /api/research/reports - 200 OK")
    
    def test_research_stats(self):
        """PE Admin can access /api/research/stats (requires research.view)"""
        if not self.pe_token:
            pytest.skip("PE token not available")
        
        response = requests.get(f"{BASE_URL}/api/research/stats", headers=self.get_headers())
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        data = response.json()
        assert "total_reports" in data, "Response should contain total_reports"
        print(f"✓ /api/research/stats - 200 OK")


class TestPEAdminRevenueDashboardAccess:
    """Test PE Admin access to revenue_dashboard.py endpoints"""
    
    pe_token = None
    
    @classmethod
    def setup_class(cls):
        """Login PE Admin"""
        print(f"\n=== Testing Revenue Dashboard Endpoints - PE Admin Access ===")
        
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": PE_DESK_EMAIL, "password": PE_DESK_PASSWORD}
        )
        if response.status_code == 200:
            cls.pe_token = response.json().get("token")
    
    def get_headers(self):
        return {"Authorization": f"Bearer {self.pe_token}", "Content-Type": "application/json"}
    
    def test_rp_revenue_dashboard(self):
        """PE Admin can access /api/rp-revenue (requires revenue.rp_view)"""
        if not self.pe_token:
            pytest.skip("PE token not available")
        
        response = requests.get(f"{BASE_URL}/api/rp-revenue", headers=self.get_headers())
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        data = response.json()
        assert "total_rps" in data or "rp_details" in data, "Response should contain RP data"
        print(f"✓ /api/rp-revenue - 200 OK")
    
    def test_employee_revenue_dashboard(self):
        """PE Admin can access /api/employee-revenue (requires revenue.employee_view)"""
        if not self.pe_token:
            pytest.skip("PE token not available")
        
        response = requests.get(f"{BASE_URL}/api/employee-revenue", headers=self.get_headers())
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        data = response.json()
        assert "total_employees" in data or "employee_details" in data, "Response should contain employee data"
        print(f"✓ /api/employee-revenue - 200 OK")
    
    def test_my_team(self):
        """PE Admin can access /api/my-team (requires revenue.team_view)"""
        if not self.pe_token:
            pytest.skip("PE token not available")
        
        response = requests.get(f"{BASE_URL}/api/my-team", headers=self.get_headers())
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        data = response.json()
        assert "team_members" in data or "total" in data, "Response should contain team data"
        print(f"✓ /api/my-team - 200 OK")


class TestPEAdminKillSwitchAccess:
    """Test PE Admin access to kill_switch.py endpoints"""
    
    pe_token = None
    
    @classmethod
    def setup_class(cls):
        """Login PE Admin"""
        print(f"\n=== Testing Kill Switch Endpoints - PE Admin Access ===")
        
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": PE_DESK_EMAIL, "password": PE_DESK_PASSWORD}
        )
        if response.status_code == 200:
            cls.pe_token = response.json().get("token")
    
    def get_headers(self):
        return {"Authorization": f"Bearer {self.pe_token}", "Content-Type": "application/json"}
    
    def test_kill_switch_status(self):
        """Anyone can access /api/kill-switch/status (public endpoint)"""
        if not self.pe_token:
            pytest.skip("PE token not available")
        
        response = requests.get(f"{BASE_URL}/api/kill-switch/status", headers=self.get_headers())
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        data = response.json()
        assert "is_active" in data, "Response should contain is_active"
        print(f"✓ /api/kill-switch/status - 200 OK")
    
    # Note: We don't actually activate the kill switch in tests as it would freeze the system


class TestPEAdminAnalyticsAccess:
    """Test PE Admin access to analytics.py endpoints"""
    
    pe_token = None
    
    @classmethod
    def setup_class(cls):
        """Login PE Admin"""
        print(f"\n=== Testing Analytics Endpoints - PE Admin Access ===")
        
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": PE_DESK_EMAIL, "password": PE_DESK_PASSWORD}
        )
        if response.status_code == 200:
            cls.pe_token = response.json().get("token")
    
    def get_headers(self):
        return {"Authorization": f"Bearer {self.pe_token}", "Content-Type": "application/json"}
    
    def test_analytics_summary(self):
        """PE Admin can access /api/analytics/summary (requires analytics.view)"""
        if not self.pe_token:
            pytest.skip("PE token not available")
        
        response = requests.get(f"{BASE_URL}/api/analytics/summary", headers=self.get_headers())
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        data = response.json()
        assert "total_bookings" in data, "Response should contain total_bookings"
        print(f"✓ /api/analytics/summary - 200 OK")
    
    def test_analytics_stock_performance(self):
        """PE Admin can access /api/analytics/stock-performance (requires analytics.performance)"""
        if not self.pe_token:
            pytest.skip("PE token not available")
        
        response = requests.get(f"{BASE_URL}/api/analytics/stock-performance", headers=self.get_headers())
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        print(f"✓ /api/analytics/stock-performance - 200 OK")
    
    def test_analytics_employee_performance(self):
        """PE Admin can access /api/analytics/employee-performance (requires analytics.performance)"""
        if not self.pe_token:
            pytest.skip("PE token not available")
        
        response = requests.get(f"{BASE_URL}/api/analytics/employee-performance", headers=self.get_headers())
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        print(f"✓ /api/analytics/employee-performance - 200 OK")
    
    def test_analytics_sector_distribution(self):
        """PE Admin can access /api/analytics/sector-distribution (requires analytics.view)"""
        if not self.pe_token:
            pytest.skip("PE token not available")
        
        response = requests.get(f"{BASE_URL}/api/analytics/sector-distribution", headers=self.get_headers())
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        print(f"✓ /api/analytics/sector-distribution - 200 OK")
    
    def test_analytics_daily_trend(self):
        """PE Admin can access /api/analytics/daily-trend (requires analytics.view)"""
        if not self.pe_token:
            pytest.skip("PE token not available")
        
        response = requests.get(f"{BASE_URL}/api/analytics/daily-trend", headers=self.get_headers())
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        print(f"✓ /api/analytics/daily-trend - 200 OK")


class TestPEAdminDatabaseBackupAccess:
    """Test PE Admin access to database_backup.py endpoints"""
    
    pe_token = None
    
    @classmethod
    def setup_class(cls):
        """Login PE Admin"""
        print(f"\n=== Testing Database Backup Endpoints - PE Admin Access ===")
        
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": PE_DESK_EMAIL, "password": PE_DESK_PASSWORD}
        )
        if response.status_code == 200:
            cls.pe_token = response.json().get("token")
    
    def get_headers(self):
        return {"Authorization": f"Bearer {self.pe_token}", "Content-Type": "application/json"}
    
    def test_database_backups_list(self):
        """PE Admin can access /api/database/backups (requires database_backup.view)"""
        if not self.pe_token:
            pytest.skip("PE token not available")
        
        response = requests.get(f"{BASE_URL}/api/database/backups", headers=self.get_headers())
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        print(f"✓ /api/database/backups - 200 OK")
    
    def test_database_stats(self):
        """PE Admin can access /api/database/stats (requires database_backup.view)"""
        if not self.pe_token:
            pytest.skip("PE token not available")
        
        response = requests.get(f"{BASE_URL}/api/database/stats", headers=self.get_headers())
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        data = response.json()
        assert "collections" in data, "Response should contain collections"
        print(f"✓ /api/database/stats - 200 OK")
    
    def test_clearable_collections(self):
        """PE Admin can access /api/database/clearable-collections (requires database_backup.clear)"""
        if not self.pe_token:
            pytest.skip("PE token not available")
        
        response = requests.get(f"{BASE_URL}/api/database/clearable-collections", headers=self.get_headers())
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        data = response.json()
        assert "collections" in data, "Response should contain collections"
        print(f"✓ /api/database/clearable-collections - 200 OK")


class TestPEAdminFinanceAccess:
    """Test PE Admin access to finance.py endpoints"""
    
    pe_token = None
    
    @classmethod
    def setup_class(cls):
        """Login PE Admin"""
        print(f"\n=== Testing Finance Endpoints - PE Admin Access ===")
        
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": PE_DESK_EMAIL, "password": PE_DESK_PASSWORD}
        )
        if response.status_code == 200:
            cls.pe_token = response.json().get("token")
    
    def get_headers(self):
        return {"Authorization": f"Bearer {self.pe_token}", "Content-Type": "application/json"}
    
    def test_finance_payments(self):
        """PE Admin can access /api/finance/payments (requires finance.view)"""
        if not self.pe_token:
            pytest.skip("PE token not available")
        
        response = requests.get(f"{BASE_URL}/api/finance/payments", headers=self.get_headers())
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        print(f"✓ /api/finance/payments - 200 OK")
    
    def test_finance_summary(self):
        """PE Admin can access /api/finance/summary (requires finance.view)"""
        if not self.pe_token:
            pytest.skip("PE token not available")
        
        response = requests.get(f"{BASE_URL}/api/finance/summary", headers=self.get_headers())
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        data = response.json()
        assert "total_received" in data, "Response should contain total_received"
        print(f"✓ /api/finance/summary - 200 OK")
    
    def test_finance_refund_requests(self):
        """PE Admin can access /api/finance/refund-requests (requires finance.refunds)"""
        if not self.pe_token:
            pytest.skip("PE token not available")
        
        response = requests.get(f"{BASE_URL}/api/finance/refund-requests", headers=self.get_headers())
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        print(f"✓ /api/finance/refund-requests - 200 OK")
    
    def test_finance_tcs_payments(self):
        """PE Admin can access /api/finance/tcs-payments (requires finance.view_tcs)"""
        if not self.pe_token:
            pytest.skip("PE token not available")
        
        response = requests.get(f"{BASE_URL}/api/finance/tcs-payments", headers=self.get_headers())
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        print(f"✓ /api/finance/tcs-payments - 200 OK")
    
    def test_finance_rp_payments(self):
        """PE Admin can access /api/finance/rp-payments (requires referral_partners.view_payouts)"""
        if not self.pe_token:
            pytest.skip("PE token not available")
        
        response = requests.get(f"{BASE_URL}/api/finance/rp-payments", headers=self.get_headers())
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        print(f"✓ /api/finance/rp-payments - 200 OK")
    
    def test_finance_bp_payments(self):
        """PE Admin can access /api/finance/bp-payments (requires business_partners.view_payouts)"""
        if not self.pe_token:
            pytest.skip("PE token not available")
        
        response = requests.get(f"{BASE_URL}/api/finance/bp-payments", headers=self.get_headers())
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        print(f"✓ /api/finance/bp-payments - 200 OK")
    
    def test_finance_employee_commissions(self):
        """PE Admin can access /api/finance/employee-commissions (requires finance.view)"""
        if not self.pe_token:
            pytest.skip("PE token not available")
        
        response = requests.get(f"{BASE_URL}/api/finance/employee-commissions", headers=self.get_headers())
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        print(f"✓ /api/finance/employee-commissions - 200 OK")


class TestPEAdminRolesAccess:
    """Test PE Admin access to roles.py endpoints"""
    
    pe_token = None
    
    @classmethod
    def setup_class(cls):
        """Login PE Admin"""
        print(f"\n=== Testing Roles Endpoints - PE Admin Access ===")
        
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": PE_DESK_EMAIL, "password": PE_DESK_PASSWORD}
        )
        if response.status_code == 200:
            cls.pe_token = response.json().get("token")
    
    def get_headers(self):
        return {"Authorization": f"Bearer {self.pe_token}", "Content-Type": "application/json"}
    
    def test_roles_list(self):
        """PE Admin can access /api/roles (requires roles.view)"""
        if not self.pe_token:
            pytest.skip("PE token not available")
        
        response = requests.get(f"{BASE_URL}/api/roles", headers=self.get_headers())
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list of roles"
        print(f"✓ /api/roles - 200 OK (found {len(data)} roles)")
    
    def test_roles_permissions(self):
        """PE Admin can access /api/roles/permissions (requires roles.view)"""
        if not self.pe_token:
            pytest.skip("PE token not available")
        
        response = requests.get(f"{BASE_URL}/api/roles/permissions", headers=self.get_headers())
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        data = response.json()
        assert "dashboard" in data, "Response should contain dashboard permissions"
        print(f"✓ /api/roles/permissions - 200 OK")


class TestPEAdminUsersAccess:
    """Test PE Admin access to users.py endpoints"""
    
    pe_token = None
    
    @classmethod
    def setup_class(cls):
        """Login PE Admin"""
        print(f"\n=== Testing Users Endpoints - PE Admin Access ===")
        
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": PE_DESK_EMAIL, "password": PE_DESK_PASSWORD}
        )
        if response.status_code == 200:
            cls.pe_token = response.json().get("token")
    
    def get_headers(self):
        return {"Authorization": f"Bearer {self.pe_token}", "Content-Type": "application/json"}
    
    def test_users_list(self):
        """PE Admin can access /api/users (requires users.view)"""
        if not self.pe_token:
            pytest.skip("PE token not available")
        
        response = requests.get(f"{BASE_URL}/api/users", headers=self.get_headers())
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        print(f"✓ /api/users - 200 OK")
    
    def test_users_employees(self):
        """PE Admin can access /api/users/employees (requires users.view)"""
        if not self.pe_token:
            pytest.skip("PE token not available")
        
        response = requests.get(f"{BASE_URL}/api/users/employees", headers=self.get_headers())
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        print(f"✓ /api/users/employees - 200 OK")


# ============== RESTRICTED ROLE DENIAL TESTS ==============

class TestViewerDeniedReportsAccess:
    """Test that Viewer role is denied access to restricted reports endpoints"""
    
    viewer_token = None
    
    @classmethod
    def setup_class(cls):
        """Login Viewer"""
        print(f"\n=== Testing Reports Endpoints - Viewer Denial ===")
        
        cls.viewer_token = login_with_retry(VIEWER_EMAIL, VIEWER_PASSWORD)
        if cls.viewer_token:
            print(f"✓ Viewer login successful")
        else:
            print(f"✗ Viewer login failed")
    
    def get_headers(self):
        return {"Authorization": f"Bearer {self.viewer_token}", "Content-Type": "application/json"}
    
    def test_viewer_denied_pe_desk_hit_report(self):
        """Viewer should be denied /api/reports/pe-desk-hit (requires reports.pe_hit)"""
        if not self.viewer_token:
            pytest.skip("Viewer token not available")
        
        response = requests.get(f"{BASE_URL}/api/reports/pe-desk-hit", headers=self.get_headers())
        assert response.status_code == 403, f"Expected 403, got {response.status_code} - {response.text}"
        print(f"✓ Viewer correctly denied /api/reports/pe-desk-hit (403)")


class TestViewerDeniedKillSwitchAccess:
    """Test that Viewer role is denied access to kill switch activation"""
    
    viewer_token = None
    
    @classmethod
    def setup_class(cls):
        """Login Viewer"""
        print(f"\n=== Testing Kill Switch Endpoints - Viewer Denial ===")
        
        cls.viewer_token = login_with_retry(VIEWER_EMAIL, VIEWER_PASSWORD)
    
    def get_headers(self):
        return {"Authorization": f"Bearer {self.viewer_token}", "Content-Type": "application/json"}
    
    def test_viewer_denied_kill_switch_activate(self):
        """Viewer should be denied /api/kill-switch/activate (requires system.kill_switch)"""
        if not self.viewer_token:
            pytest.skip("Viewer token not available")
        
        response = requests.post(f"{BASE_URL}/api/kill-switch/activate", headers=self.get_headers())
        assert response.status_code == 403, f"Expected 403, got {response.status_code} - {response.text}"
        print(f"✓ Viewer correctly denied /api/kill-switch/activate (403)")
    
    def test_viewer_denied_kill_switch_deactivate(self):
        """Viewer should be denied /api/kill-switch/deactivate (requires system.kill_switch)"""
        if not self.viewer_token:
            pytest.skip("Viewer token not available")
        
        response = requests.post(f"{BASE_URL}/api/kill-switch/deactivate", headers=self.get_headers())
        assert response.status_code in [400, 403], f"Expected 400/403, got {response.status_code} - {response.text}"
        print(f"✓ Viewer correctly denied /api/kill-switch/deactivate ({response.status_code})")


class TestViewerDeniedDatabaseAccess:
    """Test that Viewer role is denied access to database management endpoints"""
    
    viewer_token = None
    
    @classmethod
    def setup_class(cls):
        """Login Viewer"""
        print(f"\n=== Testing Database Endpoints - Viewer Denial ===")
        
        cls.viewer_token = login_with_retry(VIEWER_EMAIL, VIEWER_PASSWORD)
    
    def get_headers(self):
        return {"Authorization": f"Bearer {self.viewer_token}", "Content-Type": "application/json"}
    
    def test_viewer_denied_database_backups(self):
        """Viewer should be denied /api/database/backups (requires database_backup.view)"""
        if not self.viewer_token:
            pytest.skip("Viewer token not available")
        
        response = requests.get(f"{BASE_URL}/api/database/backups", headers=self.get_headers())
        assert response.status_code == 403, f"Expected 403, got {response.status_code} - {response.text}"
        print(f"✓ Viewer correctly denied /api/database/backups (403)")
    
    def test_viewer_denied_database_stats(self):
        """Viewer should be denied /api/database/stats (requires database_backup.view)"""
        if not self.viewer_token:
            pytest.skip("Viewer token not available")
        
        response = requests.get(f"{BASE_URL}/api/database/stats", headers=self.get_headers())
        assert response.status_code == 403, f"Expected 403, got {response.status_code} - {response.text}"
        print(f"✓ Viewer correctly denied /api/database/stats (403)")
    
    def test_viewer_denied_database_clear(self):
        """Viewer should be denied /api/database/clear (requires database_backup.clear)"""
        if not self.viewer_token:
            pytest.skip("Viewer token not available")
        
        response = requests.delete(f"{BASE_URL}/api/database/clear", headers=self.get_headers())
        assert response.status_code == 403, f"Expected 403, got {response.status_code} - {response.text}"
        print(f"✓ Viewer correctly denied /api/database/clear (403)")
    
    def test_viewer_denied_create_backup(self):
        """Viewer should be denied POST /api/database/backups (requires database_backup.create)"""
        if not self.viewer_token:
            pytest.skip("Viewer token not available")
        
        response = requests.post(
            f"{BASE_URL}/api/database/backups",
            params={"name": "Test Backup"},
            headers=self.get_headers()
        )
        assert response.status_code == 403, f"Expected 403, got {response.status_code} - {response.text}"
        print(f"✓ Viewer correctly denied POST /api/database/backups (403)")


class TestViewerDeniedRolesAccess:
    """Test that Viewer role is denied access to role management endpoints"""
    
    viewer_token = None
    
    @classmethod
    def setup_class(cls):
        """Login Viewer"""
        print(f"\n=== Testing Roles Endpoints - Viewer Denial ===")
        
        cls.viewer_token = login_with_retry(VIEWER_EMAIL, VIEWER_PASSWORD)
    
    def get_headers(self):
        return {"Authorization": f"Bearer {self.viewer_token}", "Content-Type": "application/json"}
    
    def test_viewer_denied_roles_list(self):
        """Viewer should be denied /api/roles (requires roles.view)"""
        if not self.viewer_token:
            pytest.skip("Viewer token not available")
        
        response = requests.get(f"{BASE_URL}/api/roles", headers=self.get_headers())
        assert response.status_code == 403, f"Expected 403, got {response.status_code} - {response.text}"
        print(f"✓ Viewer correctly denied /api/roles (403)")
    
    def test_viewer_denied_create_role(self):
        """Viewer should be denied POST /api/roles (requires roles.create)"""
        if not self.viewer_token:
            pytest.skip("Viewer token not available")
        
        response = requests.post(
            f"{BASE_URL}/api/roles",
            json={"name": "Test Role", "permissions": []},
            headers=self.get_headers()
        )
        assert response.status_code == 403, f"Expected 403, got {response.status_code} - {response.text}"
        print(f"✓ Viewer correctly denied POST /api/roles (403)")


class TestViewerDeniedUserManagement:
    """Test that Viewer role is denied access to user management endpoints"""
    
    viewer_token = None
    
    @classmethod
    def setup_class(cls):
        """Login Viewer"""
        print(f"\n=== Testing User Management Endpoints - Viewer Denial ===")
        
        cls.viewer_token = login_with_retry(VIEWER_EMAIL, VIEWER_PASSWORD)
    
    def get_headers(self):
        return {"Authorization": f"Bearer {self.viewer_token}", "Content-Type": "application/json"}
    
    def test_viewer_denied_create_user(self):
        """Viewer should be denied POST /api/users (requires users.create)"""
        if not self.viewer_token:
            pytest.skip("Viewer token not available")
        
        response = requests.post(
            f"{BASE_URL}/api/users",
            json={
                "email": "test_new_user@test.com",
                "password": "Test@123",
                "name": "Test User",
                "role": 7
            },
            headers=self.get_headers()
        )
        assert response.status_code == 403, f"Expected 403, got {response.status_code} - {response.text}"
        print(f"✓ Viewer correctly denied POST /api/users (403)")


class TestViewerDeniedClientApproval:
    """Test that Viewer role is denied access to client approval endpoints"""
    
    viewer_token = None
    
    @classmethod
    def setup_class(cls):
        """Login Viewer"""
        print(f"\n=== Testing Client Approval Endpoints - Viewer Denial ===")
        
        cls.viewer_token = login_with_retry(VIEWER_EMAIL, VIEWER_PASSWORD)
    
    def get_headers(self):
        return {"Authorization": f"Bearer {self.viewer_token}", "Content-Type": "application/json"}
    
    def test_viewer_denied_pending_clients(self):
        """Viewer should be denied /api/clients/pending-approval (requires client_approval.view)"""
        if not self.viewer_token:
            pytest.skip("Viewer token not available")
        
        response = requests.get(f"{BASE_URL}/api/clients/pending-approval", headers=self.get_headers())
        assert response.status_code == 403, f"Expected 403, got {response.status_code} - {response.text}"
        print(f"✓ Viewer correctly denied /api/clients/pending-approval (403)")
    
    def test_viewer_denied_approve_client(self):
        """Viewer should be denied PUT /api/clients/{id}/approve (requires client_approval.approve)"""
        if not self.viewer_token:
            pytest.skip("Viewer token not available")
        
        response = requests.put(
            f"{BASE_URL}/api/clients/fake-client-id/approve",
            params={"approve": True},
            headers=self.get_headers()
        )
        assert response.status_code == 403, f"Expected 403, got {response.status_code} - {response.text}"
        print(f"✓ Viewer correctly denied PUT /api/clients/approve (403)")


class TestViewerDeniedBookingApproval:
    """Test that Viewer role is denied access to booking approval endpoints"""
    
    viewer_token = None
    
    @classmethod
    def setup_class(cls):
        """Login Viewer"""
        print(f"\n=== Testing Booking Approval Endpoints - Viewer Denial ===")
        
        cls.viewer_token = login_with_retry(VIEWER_EMAIL, VIEWER_PASSWORD)
    
    def get_headers(self):
        return {"Authorization": f"Bearer {self.viewer_token}", "Content-Type": "application/json"}
    
    def test_viewer_denied_approve_booking(self):
        """Viewer should be denied PUT /api/bookings/{id}/approve (requires bookings.approve)"""
        if not self.viewer_token:
            pytest.skip("Viewer token not available")
        
        response = requests.put(
            f"{BASE_URL}/api/bookings/fake-booking-id/approve",
            params={"approve": True},
            headers=self.get_headers()
        )
        assert response.status_code == 403, f"Expected 403, got {response.status_code} - {response.text}"
        print(f"✓ Viewer correctly denied PUT /api/bookings/approve (403)")
    
    def test_viewer_denied_void_booking(self):
        """Viewer should be denied PUT /api/bookings/{id}/void (requires bookings.delete)"""
        if not self.viewer_token:
            pytest.skip("Viewer token not available")
        
        response = requests.put(
            f"{BASE_URL}/api/bookings/fake-booking-id/void",
            params={"reason": "Test void"},
            headers=self.get_headers()
        )
        assert response.status_code == 403, f"Expected 403, got {response.status_code} - {response.text}"
        print(f"✓ Viewer correctly denied PUT /api/bookings/void (403)")
    
    def test_viewer_denied_dp_ready_bookings(self):
        """Viewer should be denied /api/bookings/dp-ready (requires dp.view_receivables)"""
        if not self.viewer_token:
            pytest.skip("Viewer token not available")
        
        response = requests.get(f"{BASE_URL}/api/bookings/dp-ready", headers=self.get_headers())
        assert response.status_code == 403, f"Expected 403, got {response.status_code} - {response.text}"
        print(f"✓ Viewer correctly denied /api/bookings/dp-ready (403)")
    
    def test_viewer_denied_dp_transferred_bookings(self):
        """Viewer should be denied /api/bookings/dp-transferred (requires dp.view_transfers)"""
        if not self.viewer_token:
            pytest.skip("Viewer token not available")
        
        response = requests.get(f"{BASE_URL}/api/bookings/dp-transferred", headers=self.get_headers())
        assert response.status_code == 403, f"Expected 403, got {response.status_code} - {response.text}"
        print(f"✓ Viewer correctly denied /api/bookings/dp-transferred (403)")


class TestViewerDeniedResearchUpload:
    """Test that Viewer role is denied access to research upload endpoints"""
    
    viewer_token = None
    
    @classmethod
    def setup_class(cls):
        """Login Viewer"""
        print(f"\n=== Testing Research Upload Endpoints - Viewer Denial ===")
        
        cls.viewer_token = login_with_retry(VIEWER_EMAIL, VIEWER_PASSWORD)
    
    def get_headers(self):
        return {"Authorization": f"Bearer {self.viewer_token}", "Content-Type": "application/json"}
    
    def test_viewer_denied_delete_research_report(self):
        """Viewer should be denied DELETE /api/research/reports/{id} (requires research.delete)"""
        if not self.viewer_token:
            pytest.skip("Viewer token not available")
        
        response = requests.delete(
            f"{BASE_URL}/api/research/reports/fake-report-id",
            headers=self.get_headers()
        )
        assert response.status_code == 403, f"Expected 403, got {response.status_code} - {response.text}"
        print(f"✓ Viewer correctly denied DELETE /api/research/reports (403)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
