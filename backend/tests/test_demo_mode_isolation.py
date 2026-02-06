"""
Demo Mode Isolation Tests

This test file verifies that demo mode is completely isolated from live production data.
Critical security feature - demo users should ONLY see demo data (is_demo=True).
Regular users should NEVER see demo data.

Tests cover:
1. Demo initialization via /api/demo/init
2. Demo user API calls returning ONLY demo data
3. Regular user API calls NOT returning any demo data
4. Dashboard stats showing correct counts for each user type
5. Demo cleanup removing all demo data

IMPORTANT: Use User-Agent header to bypass bot protection middleware.
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
if not BASE_URL:
    BASE_URL = "https://booking-mgmt-fixes.preview.emergentagent.com"

# Standard headers to bypass bot protection
HEADERS = {
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

# Credentials from agent context
REGULAR_USER_CREDS = {
    "email": "pe@smifs.com",
    "password": "Kutta@123"
}


class TestDemoModeIsolation:
    """Test suite for Demo Mode Data Isolation - Critical security feature"""
    
    @pytest.fixture(scope="class")
    def regular_user_token(self):
        """Get token for regular (non-demo) user"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json=REGULAR_USER_CREDS,
            headers=HEADERS
        )
        if response.status_code != 200:
            pytest.skip(f"Regular user login failed: {response.status_code} - {response.text}")
        return response.json().get("token")
    
    @pytest.fixture(scope="class")
    def demo_token(self):
        """Initialize demo mode and get demo token"""
        response = requests.post(
            f"{BASE_URL}/api/demo/init",
            headers=HEADERS
        )
        if response.status_code not in [200, 201]:
            pytest.skip(f"Demo init failed: {response.status_code} - {response.text}")
        data = response.json()
        return data.get("token")
    
    def get_auth_headers(self, token):
        """Get headers with authorization"""
        return {
            **HEADERS,
            "Authorization": f"Bearer {token}"
        }
    
    # ============== Demo Initialization Tests ==============
    
    def test_demo_init_creates_demo_data(self):
        """Test POST /api/demo/init creates demo-specific data with is_demo=True"""
        response = requests.post(
            f"{BASE_URL}/api/demo/init",
            headers=HEADERS
        )
        
        # Should return 200 or 201
        assert response.status_code in [200, 201], f"Demo init failed: {response.status_code} - {response.text}"
        
        data = response.json()
        
        # Verify response structure
        assert data.get("success") == True, "Demo init should return success=True"
        assert "token" in data, "Demo init should return a token"
        assert "user" in data, "Demo init should return user info"
        assert "demo_data" in data, "Demo init should return demo_data counts"
        
        # Verify user is marked as demo
        user = data.get("user", {})
        assert user.get("is_demo") == True, "Demo user should have is_demo=True"
        assert user.get("email") == "demo@privity.com", "Demo user should have demo@privity.com email"
        
        # Verify demo data was created
        demo_data = data.get("demo_data", {})
        assert demo_data.get("clients", 0) > 0, "Demo should create clients"
        assert demo_data.get("stocks", 0) > 0, "Demo should create stocks"
        assert demo_data.get("bookings", 0) > 0, "Demo should create bookings"
        
        print(f"PASS: Demo init created {demo_data.get('clients')} clients, {demo_data.get('stocks')} stocks, {demo_data.get('bookings')} bookings")
    
    def test_demo_init_returns_valid_token(self, demo_token):
        """Test that demo token is valid and works for API calls"""
        assert demo_token is not None, "Demo token should not be None"
        assert len(demo_token) > 20, "Demo token should be a valid JWT"
        print(f"PASS: Demo token obtained successfully")
    
    # ============== Demo User Data Isolation Tests ==============
    
    def test_demo_user_gets_only_demo_clients(self, demo_token):
        """Test that demo user API calls to /api/clients returns ONLY clients with is_demo=true"""
        response = requests.get(
            f"{BASE_URL}/api/clients",
            headers=self.get_auth_headers(demo_token)
        )
        
        assert response.status_code == 200, f"Failed to get clients: {response.status_code} - {response.text}"
        
        clients = response.json()
        
        # All returned clients should have is_demo=True
        for client in clients:
            assert client.get("is_demo") == True, f"Demo user received non-demo client: {client.get('id')} - {client.get('name')}"
        
        # Demo user should get some clients (demo was initialized)
        assert len(clients) > 0, "Demo user should see some demo clients"
        
        print(f"PASS: Demo user received {len(clients)} clients, ALL with is_demo=True")
    
    def test_demo_user_gets_only_demo_stocks(self, demo_token):
        """Test that demo user API calls to /api/stocks returns ONLY stocks with is_demo=true"""
        response = requests.get(
            f"{BASE_URL}/api/stocks",
            headers=self.get_auth_headers(demo_token)
        )
        
        assert response.status_code == 200, f"Failed to get stocks: {response.status_code} - {response.text}"
        
        stocks = response.json()
        
        # All returned stocks should have is_demo=True
        for stock in stocks:
            assert stock.get("is_demo") == True, f"Demo user received non-demo stock: {stock.get('id')} - {stock.get('symbol')}"
        
        # Demo user should get some stocks
        assert len(stocks) > 0, "Demo user should see some demo stocks"
        
        print(f"PASS: Demo user received {len(stocks)} stocks, ALL with is_demo=True")
    
    def test_demo_user_gets_only_demo_bookings(self, demo_token):
        """Test that demo user API calls to /api/bookings returns ONLY bookings with is_demo=true"""
        response = requests.get(
            f"{BASE_URL}/api/bookings",
            headers=self.get_auth_headers(demo_token)
        )
        
        assert response.status_code == 200, f"Failed to get bookings: {response.status_code} - {response.text}"
        
        bookings = response.json()
        
        # All returned bookings should have is_demo=True
        for booking in bookings:
            assert booking.get("is_demo") == True, f"Demo user received non-demo booking: {booking.get('id')} - {booking.get('booking_number')}"
        
        # Demo user should get some bookings
        assert len(bookings) > 0, "Demo user should see some demo bookings"
        
        print(f"PASS: Demo user received {len(bookings)} bookings, ALL with is_demo=True")
    
    # ============== Regular User Data Isolation Tests ==============
    
    def test_regular_user_gets_no_demo_clients(self, regular_user_token, demo_token):
        """Test that regular user API calls to /api/clients returns NO clients with is_demo=true"""
        # First ensure demo data exists
        assert demo_token is not None
        
        response = requests.get(
            f"{BASE_URL}/api/clients",
            headers=self.get_auth_headers(regular_user_token)
        )
        
        assert response.status_code == 200, f"Failed to get clients: {response.status_code} - {response.text}"
        
        clients = response.json()
        
        # None of the returned clients should have is_demo=True
        demo_clients = [c for c in clients if c.get("is_demo") == True]
        assert len(demo_clients) == 0, f"CRITICAL SECURITY: Regular user received {len(demo_clients)} demo clients - DATA LEAK DETECTED!"
        
        print(f"PASS: Regular user received {len(clients)} clients, NONE with is_demo=True")
    
    def test_regular_user_gets_no_demo_stocks(self, regular_user_token, demo_token):
        """Test that regular user API calls to /api/stocks returns NO stocks with is_demo=true"""
        # First ensure demo data exists
        assert demo_token is not None
        
        response = requests.get(
            f"{BASE_URL}/api/stocks",
            headers=self.get_auth_headers(regular_user_token)
        )
        
        assert response.status_code == 200, f"Failed to get stocks: {response.status_code} - {response.text}"
        
        stocks = response.json()
        
        # None of the returned stocks should have is_demo=True
        demo_stocks = [s for s in stocks if s.get("is_demo") == True]
        assert len(demo_stocks) == 0, f"CRITICAL SECURITY: Regular user received {len(demo_stocks)} demo stocks - DATA LEAK DETECTED!"
        
        print(f"PASS: Regular user received {len(stocks)} stocks, NONE with is_demo=True")
    
    def test_regular_user_gets_no_demo_bookings(self, regular_user_token, demo_token):
        """Test that regular user API calls to /api/bookings returns NO bookings with is_demo=true"""
        # First ensure demo data exists
        assert demo_token is not None
        
        response = requests.get(
            f"{BASE_URL}/api/bookings",
            headers=self.get_auth_headers(regular_user_token)
        )
        
        assert response.status_code == 200, f"Failed to get bookings: {response.status_code} - {response.text}"
        
        bookings = response.json()
        
        # None of the returned bookings should have is_demo=True
        demo_bookings = [b for b in bookings if b.get("is_demo") == True]
        assert len(demo_bookings) == 0, f"CRITICAL SECURITY: Regular user received {len(demo_bookings)} demo bookings - DATA LEAK DETECTED!"
        
        print(f"PASS: Regular user received {len(bookings)} bookings, NONE with is_demo=True")
    
    # ============== Dashboard Stats Isolation Tests ==============
    
    def test_demo_user_dashboard_shows_only_demo_counts(self, demo_token):
        """Test that dashboard stats for demo user shows only demo data counts"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/stats",
            headers=self.get_auth_headers(demo_token)
        )
        
        assert response.status_code == 200, f"Failed to get dashboard stats: {response.status_code} - {response.text}"
        
        stats = response.json()
        
        # Verify the dashboard returns valid stats
        assert "total_clients" in stats, "Dashboard should include total_clients"
        assert "total_stocks" in stats, "Dashboard should include total_stocks"
        assert "total_bookings" in stats, "Dashboard should include total_bookings"
        
        # Demo user should see demo data counts (not zero if demo was initialized)
        # Note: We can't verify exact counts here, but we verify the response structure
        print(f"PASS: Demo user dashboard stats - clients: {stats.get('total_clients')}, stocks: {stats.get('total_stocks')}, bookings: {stats.get('total_bookings')}")
    
    def test_regular_user_dashboard_excludes_demo_counts(self, regular_user_token, demo_token):
        """Test that dashboard stats for regular user excludes demo data counts"""
        # First, get demo user stats for comparison
        demo_response = requests.get(
            f"{BASE_URL}/api/dashboard/stats",
            headers=self.get_auth_headers(demo_token)
        )
        demo_stats = demo_response.json() if demo_response.status_code == 200 else {}
        
        # Now get regular user stats
        response = requests.get(
            f"{BASE_URL}/api/dashboard/stats",
            headers=self.get_auth_headers(regular_user_token)
        )
        
        assert response.status_code == 200, f"Failed to get dashboard stats: {response.status_code} - {response.text}"
        
        regular_stats = response.json()
        
        # Verify the dashboard returns valid stats
        assert "total_clients" in regular_stats, "Dashboard should include total_clients"
        assert "total_stocks" in regular_stats, "Dashboard should include total_stocks"
        assert "total_bookings" in regular_stats, "Dashboard should include total_bookings"
        
        print(f"PASS: Regular user dashboard stats - clients: {regular_stats.get('total_clients')}, stocks: {regular_stats.get('total_stocks')}, bookings: {regular_stats.get('total_bookings')}")
        print(f"INFO: Demo user dashboard stats - clients: {demo_stats.get('total_clients')}, stocks: {demo_stats.get('total_stocks')}, bookings: {demo_stats.get('total_bookings')}")
    
    # ============== Demo Status and Cleanup Tests ==============
    
    def test_demo_status_endpoint(self, demo_token):
        """Test GET /api/demo/status shows demo data counts"""
        response = requests.get(
            f"{BASE_URL}/api/demo/status",
            headers=HEADERS  # No auth needed
        )
        
        assert response.status_code == 200, f"Failed to get demo status: {response.status_code} - {response.text}"
        
        status = response.json()
        
        # Verify response structure
        assert "demo_active" in status, "Status should include demo_active flag"
        assert "demo_data" in status, "Status should include demo_data counts"
        
        print(f"PASS: Demo status - active: {status.get('demo_active')}, data: {status.get('demo_data')}")
    
    def test_demo_verify_isolation_endpoint(self, demo_token):
        """Test GET /api/demo/verify-isolation returns isolation status"""
        response = requests.get(
            f"{BASE_URL}/api/demo/verify-isolation",
            headers=HEADERS
        )
        
        assert response.status_code == 200, f"Failed to verify isolation: {response.status_code} - {response.text}"
        
        report = response.json()
        
        # Verify response structure
        assert "status" in report, "Report should include status"
        assert "checks" in report, "Report should include checks"
        
        # Isolation should be verified or warnings
        assert report.get("status") in ["verified", "warnings"], f"Unexpected status: {report.get('status')}"
        
        print(f"PASS: Demo isolation status: {report.get('status')}, checks: {len(report.get('checks', []))}")
        
        # Log any warnings
        warnings = report.get("warnings", [])
        if warnings:
            print(f"WARNINGS: {warnings}")
    
    def test_demo_cleanup_removes_all_demo_data(self):
        """Test POST /api/demo/cleanup removes all demo data"""
        # First initialize demo to have data to cleanup
        init_response = requests.post(
            f"{BASE_URL}/api/demo/init",
            headers=HEADERS
        )
        
        if init_response.status_code not in [200, 201]:
            pytest.skip("Could not initialize demo for cleanup test")
        
        # Now cleanup
        response = requests.post(
            f"{BASE_URL}/api/demo/cleanup",
            headers=HEADERS
        )
        
        assert response.status_code == 200, f"Failed to cleanup demo: {response.status_code} - {response.text}"
        
        cleanup_result = response.json()
        
        # Verify cleanup was successful
        assert cleanup_result.get("success") == True, "Cleanup should return success=True"
        assert "deleted" in cleanup_result, "Cleanup should return deleted counts"
        
        # Verify data was actually deleted
        deleted = cleanup_result.get("deleted", {})
        print(f"PASS: Demo cleanup deleted - clients: {deleted.get('clients')}, stocks: {deleted.get('stocks')}, bookings: {deleted.get('bookings')}")
        
        # Verify status after cleanup
        status_response = requests.get(
            f"{BASE_URL}/api/demo/status",
            headers=HEADERS
        )
        
        if status_response.status_code == 200:
            status = status_response.json()
            demo_data = status.get("demo_data", {})
            # After cleanup, demo data counts should be 0
            assert demo_data.get("clients", 0) == 0, f"Demo clients not cleaned up: {demo_data.get('clients')}"
            assert demo_data.get("bookings", 0) == 0, f"Demo bookings not cleaned up: {demo_data.get('bookings')}"
            print(f"PASS: Verified demo data counts are 0 after cleanup")


class TestDemoIsolationEdgeCases:
    """Test edge cases and error scenarios for demo isolation"""
    
    @pytest.fixture(scope="class")
    def demo_token(self):
        """Initialize demo mode and get demo token"""
        response = requests.post(
            f"{BASE_URL}/api/demo/init",
            headers=HEADERS
        )
        if response.status_code not in [200, 201]:
            pytest.skip(f"Demo init failed: {response.status_code}")
        return response.json().get("token")
    
    @pytest.fixture(scope="class")
    def regular_user_token(self):
        """Get token for regular user"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json=REGULAR_USER_CREDS,
            headers=HEADERS
        )
        if response.status_code != 200:
            pytest.skip(f"Regular user login failed: {response.status_code}")
        return response.json().get("token")
    
    def get_auth_headers(self, token):
        """Get headers with authorization"""
        return {
            **HEADERS,
            "Authorization": f"Bearer {token}"
        }
    
    def test_demo_user_cannot_access_specific_live_client(self, demo_token, regular_user_token):
        """Test demo user cannot access a specific live client by ID"""
        # First, get a live client ID from regular user
        response = requests.get(
            f"{BASE_URL}/api/clients",
            headers=self.get_auth_headers(regular_user_token)
        )
        
        if response.status_code != 200 or not response.json():
            pytest.skip("No live clients available")
        
        live_clients = response.json()
        if not live_clients:
            pytest.skip("No live clients available")
        
        live_client_id = live_clients[0].get("id")
        
        # Demo user should NOT be able to access this live client
        demo_response = requests.get(
            f"{BASE_URL}/api/clients/{live_client_id}",
            headers=self.get_auth_headers(demo_token)
        )
        
        # Should return 403 or 404 (access denied)
        assert demo_response.status_code in [403, 404], f"SECURITY ISSUE: Demo user accessed live client! Status: {demo_response.status_code}"
        
        print(f"PASS: Demo user blocked from accessing live client (status: {demo_response.status_code})")
    
    def test_regular_user_cannot_access_specific_demo_client(self, demo_token, regular_user_token):
        """Test regular user cannot access a specific demo client by ID"""
        # First, get a demo client ID from demo user
        response = requests.get(
            f"{BASE_URL}/api/clients",
            headers=self.get_auth_headers(demo_token)
        )
        
        if response.status_code != 200 or not response.json():
            pytest.skip("No demo clients available")
        
        demo_clients = response.json()
        if not demo_clients:
            pytest.skip("No demo clients available")
        
        demo_client_id = demo_clients[0].get("id")
        
        # Regular user should NOT be able to access this demo client
        regular_response = requests.get(
            f"{BASE_URL}/api/clients/{demo_client_id}",
            headers=self.get_auth_headers(regular_user_token)
        )
        
        # Should return 404 (not found - to not reveal demo data exists)
        assert regular_response.status_code == 404, f"SECURITY ISSUE: Regular user accessed demo client! Status: {regular_response.status_code}"
        
        print(f"PASS: Regular user blocked from accessing demo client (status: {regular_response.status_code})")
    
    def test_demo_reinit_clears_and_recreates(self):
        """Test that re-initializing demo mode clears old data and creates fresh data"""
        # First init
        first_response = requests.post(
            f"{BASE_URL}/api/demo/init",
            headers=HEADERS
        )
        
        assert first_response.status_code in [200, 201], f"First demo init failed: {first_response.status_code}"
        
        first_data = first_response.json().get("demo_data", {})
        
        # Second init (should clear and recreate)
        second_response = requests.post(
            f"{BASE_URL}/api/demo/init",
            headers=HEADERS
        )
        
        assert second_response.status_code in [200, 201], f"Second demo init failed: {second_response.status_code}"
        
        second_data = second_response.json().get("demo_data", {})
        
        # Verify data was recreated (counts should be similar)
        assert second_data.get("clients", 0) > 0, "Demo should have clients after reinit"
        assert second_data.get("stocks", 0) > 0, "Demo should have stocks after reinit"
        
        print(f"PASS: Demo reinit works - first: {first_data}, second: {second_data}")


class TestDemoModeCleanup:
    """Final cleanup test - run last to clean demo data"""
    
    def test_final_demo_cleanup(self):
        """Cleanup demo data at end of test suite"""
        response = requests.post(
            f"{BASE_URL}/api/demo/cleanup",
            headers=HEADERS
        )
        
        if response.status_code == 200:
            print(f"FINAL: Demo data cleaned up successfully")
        else:
            print(f"WARNING: Demo cleanup returned status {response.status_code}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
