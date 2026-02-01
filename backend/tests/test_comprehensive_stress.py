"""
Comprehensive Stress Test for Privity System
Tests: Authentication, Kill Switch, DP Receivables, DP Transfer, Audit Trail, 
Database Backup, Sohini AI, Dashboards, User Management, Email Logs, etc.
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://privity-booking-1.preview.emergentagent.com').rstrip('/')

# Test credentials
PE_DESK_CREDS = {"email": "pedesk@smifs.com", "password": "Kutta@123"}
EMPLOYEE_CREDS = {"email": "employee@test.com", "password": "Test@123"}
FINANCE_CREDS = {"email": "finance@test.com", "password": "Test@123"}


class TestAuthentication:
    """Test authentication flows for different user roles"""
    
    def test_health_check(self):
        """Test health endpoint"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["version"] == "2.0.0"
        print(f"✓ Health check passed - version {data['version']}")
    
    def test_pe_desk_login(self):
        """Test PE Desk login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=PE_DESK_CREDS)
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == 1
        assert data["user"]["role_name"] == "PE Desk"
        print(f"✓ PE Desk login successful - {data['user']['name']}")
        return data["token"]
    
    def test_invalid_login(self):
        """Test invalid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "invalid@test.com",
            "password": "wrongpassword"
        })
        assert response.status_code == 401
        print("✓ Invalid login correctly rejected")
    
    def test_get_current_user(self):
        """Test /auth/me endpoint"""
        token = self.test_pe_desk_login()
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/api/auth/me", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "pedesk@smifs.com"
        print(f"✓ Current user retrieved - {data['name']}")


class TestKillSwitch:
    """Test Kill Switch functionality"""
    
    @pytest.fixture
    def pe_desk_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=PE_DESK_CREDS)
        return response.json()["token"]
    
    def test_get_kill_switch_status(self, pe_desk_token):
        """Test getting kill switch status"""
        headers = {"Authorization": f"Bearer {pe_desk_token}"}
        response = requests.get(f"{BASE_URL}/api/kill-switch/status", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "is_active" in data
        assert "remaining_seconds" in data
        print(f"✓ Kill switch status: active={data['is_active']}, remaining={data['remaining_seconds']}s")
        return data
    
    def test_kill_switch_status_public(self):
        """Test that kill switch status is accessible without auth"""
        response = requests.get(f"{BASE_URL}/api/kill-switch/status")
        assert response.status_code == 200
        print("✓ Kill switch status accessible publicly")


class TestDPReceivables:
    """Test DP Receivables endpoints"""
    
    @pytest.fixture
    def pe_desk_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=PE_DESK_CREDS)
        return response.json()["token"]
    
    def test_get_dp_receivables(self, pe_desk_token):
        """Test getting DP receivables list"""
        headers = {"Authorization": f"Bearer {pe_desk_token}"}
        response = requests.get(f"{BASE_URL}/api/purchases/dp-receivables", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ DP Receivables: {len(data)} pending items")
        return data
    
    def test_get_dp_received(self, pe_desk_token):
        """Test getting DP received list"""
        headers = {"Authorization": f"Bearer {pe_desk_token}"}
        response = requests.get(f"{BASE_URL}/api/purchases/dp-received", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ DP Received: {len(data)} completed items")
        return data


class TestDPTransfer:
    """Test DP Transfer (Client) endpoints"""
    
    @pytest.fixture
    def pe_desk_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=PE_DESK_CREDS)
        return response.json()["token"]
    
    def test_get_dp_ready(self, pe_desk_token):
        """Test getting DP ready for transfer list"""
        headers = {"Authorization": f"Bearer {pe_desk_token}"}
        response = requests.get(f"{BASE_URL}/api/bookings/dp-ready", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ DP Ready: {len(data)} bookings ready for transfer")
        return data
    
    def test_get_dp_transferred(self, pe_desk_token):
        """Test getting DP transferred list"""
        headers = {"Authorization": f"Bearer {pe_desk_token}"}
        response = requests.get(f"{BASE_URL}/api/bookings/dp-transferred", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ DP Transferred: {len(data)} completed transfers")
        return data


class TestAuditTrail:
    """Test Audit Trail endpoints"""
    
    @pytest.fixture
    def pe_desk_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=PE_DESK_CREDS)
        return response.json()["token"]
    
    def test_get_audit_logs(self, pe_desk_token):
        """Test getting audit logs"""
        headers = {"Authorization": f"Bearer {pe_desk_token}"}
        response = requests.get(f"{BASE_URL}/api/audit-logs", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "logs" in data or isinstance(data, list)
        logs = data.get("logs", data) if isinstance(data, dict) else data
        print(f"✓ Audit logs: {len(logs)} entries")
        return data
    
    def test_get_audit_stats(self, pe_desk_token):
        """Test getting audit stats"""
        headers = {"Authorization": f"Bearer {pe_desk_token}"}
        response = requests.get(f"{BASE_URL}/api/audit-logs/stats", headers=headers)
        assert response.status_code == 200
        data = response.json()
        print(f"✓ Audit stats retrieved")
        return data


class TestDatabaseBackup:
    """Test Database Backup endpoints"""
    
    @pytest.fixture
    def pe_desk_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=PE_DESK_CREDS)
        return response.json()["token"]
    
    def test_get_backup_stats(self, pe_desk_token):
        """Test getting database backup stats"""
        headers = {"Authorization": f"Bearer {pe_desk_token}"}
        response = requests.get(f"{BASE_URL}/api/database-backup/stats", headers=headers)
        assert response.status_code == 200
        data = response.json()
        print(f"✓ Database backup stats retrieved")
        return data
    
    def test_get_backup_history(self, pe_desk_token):
        """Test getting backup history"""
        headers = {"Authorization": f"Bearer {pe_desk_token}"}
        response = requests.get(f"{BASE_URL}/api/database-backup/history", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Backup history: {len(data)} backups")
        return data


class TestSohiniAI:
    """Test Sohini AI Assistant endpoints"""
    
    @pytest.fixture
    def pe_desk_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=PE_DESK_CREDS)
        return response.json()["token"]
    
    def test_sohini_chat(self, pe_desk_token):
        """Test Sohini AI chat endpoint"""
        headers = {"Authorization": f"Bearer {pe_desk_token}"}
        response = requests.post(f"{BASE_URL}/api/sohini/chat", 
            headers=headers,
            json={"message": "Hello, what can you help me with?"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert "session_id" in data
        print(f"✓ Sohini AI responded: {data['response'][:50]}...")
        return data


class TestDashboards:
    """Test Dashboard endpoints"""
    
    @pytest.fixture
    def pe_desk_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=PE_DESK_CREDS)
        return response.json()["token"]
    
    def test_dashboard_stats(self, pe_desk_token):
        """Test main dashboard stats"""
        headers = {"Authorization": f"Bearer {pe_desk_token}"}
        response = requests.get(f"{BASE_URL}/api/dashboard/stats", headers=headers)
        assert response.status_code == 200
        data = response.json()
        print(f"✓ Dashboard stats retrieved")
        return data
    
    def test_employee_revenue_dashboard(self, pe_desk_token):
        """Test employee revenue dashboard"""
        headers = {"Authorization": f"Bearer {pe_desk_token}"}
        response = requests.get(f"{BASE_URL}/api/employee-revenue", headers=headers)
        assert response.status_code == 200
        data = response.json()
        print(f"✓ Employee revenue dashboard retrieved")
        return data
    
    def test_rp_revenue_dashboard(self, pe_desk_token):
        """Test RP revenue dashboard"""
        headers = {"Authorization": f"Bearer {pe_desk_token}"}
        response = requests.get(f"{BASE_URL}/api/rp-revenue", headers=headers)
        assert response.status_code == 200
        data = response.json()
        print(f"✓ RP revenue dashboard retrieved")
        return data


class TestUserManagement:
    """Test User Management endpoints"""
    
    @pytest.fixture
    def pe_desk_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=PE_DESK_CREDS)
        return response.json()["token"]
    
    def test_get_users(self, pe_desk_token):
        """Test getting users list"""
        headers = {"Authorization": f"Bearer {pe_desk_token}"}
        response = requests.get(f"{BASE_URL}/api/users", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Users: {len(data)} users found")
        return data
    
    def test_get_user_hierarchy(self, pe_desk_token):
        """Test getting user hierarchy"""
        headers = {"Authorization": f"Bearer {pe_desk_token}"}
        response = requests.get(f"{BASE_URL}/api/users/hierarchy", headers=headers)
        assert response.status_code == 200
        data = response.json()
        print(f"✓ User hierarchy retrieved")
        return data


class TestEmailLogs:
    """Test Email Logs endpoints"""
    
    @pytest.fixture
    def pe_desk_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=PE_DESK_CREDS)
        return response.json()["token"]
    
    def test_get_email_logs(self, pe_desk_token):
        """Test getting email logs"""
        headers = {"Authorization": f"Bearer {pe_desk_token}"}
        response = requests.get(f"{BASE_URL}/api/email-logs", headers=headers)
        assert response.status_code == 200
        data = response.json()
        logs = data.get("logs", data) if isinstance(data, dict) else data
        print(f"✓ Email logs: {len(logs)} entries")
        return data


class TestClientsVendorsStocks:
    """Test Clients, Vendors, and Stocks endpoints"""
    
    @pytest.fixture
    def pe_desk_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=PE_DESK_CREDS)
        return response.json()["token"]
    
    def test_get_clients(self, pe_desk_token):
        """Test getting clients list"""
        headers = {"Authorization": f"Bearer {pe_desk_token}"}
        response = requests.get(f"{BASE_URL}/api/clients", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Clients: {len(data)} clients found")
        return data
    
    def test_get_vendors(self, pe_desk_token):
        """Test getting vendors list (clients with is_vendor=true)"""
        headers = {"Authorization": f"Bearer {pe_desk_token}"}
        response = requests.get(f"{BASE_URL}/api/clients?is_vendor=true", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Vendors: {len(data)} vendors found")
        return data
    
    def test_get_stocks(self, pe_desk_token):
        """Test getting stocks list"""
        headers = {"Authorization": f"Bearer {pe_desk_token}"}
        response = requests.get(f"{BASE_URL}/api/stocks", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Stocks: {len(data)} stocks found")
        return data


class TestBookingsAndPurchases:
    """Test Bookings and Purchases endpoints"""
    
    @pytest.fixture
    def pe_desk_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=PE_DESK_CREDS)
        return response.json()["token"]
    
    def test_get_bookings(self, pe_desk_token):
        """Test getting bookings list"""
        headers = {"Authorization": f"Bearer {pe_desk_token}"}
        response = requests.get(f"{BASE_URL}/api/bookings", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Bookings: {len(data)} bookings found")
        return data
    
    def test_get_purchases(self, pe_desk_token):
        """Test getting purchases list"""
        headers = {"Authorization": f"Bearer {pe_desk_token}"}
        response = requests.get(f"{BASE_URL}/api/purchases", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Purchases: {len(data)} purchases found")
        return data


class TestStressNavigation:
    """Stress test - rapid API calls simulating navigation"""
    
    @pytest.fixture
    def pe_desk_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=PE_DESK_CREDS)
        return response.json()["token"]
    
    def test_rapid_navigation(self, pe_desk_token):
        """Test rapid navigation between pages"""
        headers = {"Authorization": f"Bearer {pe_desk_token}"}
        
        endpoints = [
            "/api/dashboard/stats",
            "/api/clients",
            "/api/stocks",
            "/api/bookings",
            "/api/purchases",
            "/api/users",
            "/api/audit-logs",
            "/api/email-logs",
            "/api/kill-switch/status",
            "/api/notifications/unread-count",
        ]
        
        success_count = 0
        for endpoint in endpoints:
            response = requests.get(f"{BASE_URL}{endpoint}", headers=headers)
            if response.status_code == 200:
                success_count += 1
            time.sleep(0.1)  # Small delay between requests
        
        assert success_count == len(endpoints), f"Only {success_count}/{len(endpoints)} endpoints succeeded"
        print(f"✓ Rapid navigation: {success_count}/{len(endpoints)} endpoints successful")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
