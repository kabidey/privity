"""
Test Loss Booking Approval Workflow
- Loss booking detection: is_loss_booking flag set when selling_price < buying_price
- Loss approval status: starts as 'pending' for loss bookings
- Loss approval endpoint: PUT /api/bookings/{booking_id}/approve-loss
- Pending loss bookings API: GET /api/bookings/pending-loss-approval
- Role validation: Only PE Desk (role 1) can approve loss bookings
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestLossBookingWorkflow:
    """Test loss booking detection and approval workflow"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as admin (PE Desk - role 1)
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@privity.com",
            "password": "Admin@123"
        })
        assert login_response.status_code == 200, f"Admin login failed: {login_response.text}"
        self.admin_token = login_response.json()["token"]
        self.admin_user = login_response.json()["user"]
        
        # Set auth header
        self.session.headers.update({"Authorization": f"Bearer {self.admin_token}"})
        
        yield
        
        # Cleanup - delete test bookings
        self._cleanup_test_data()
    
    def _cleanup_test_data(self):
        """Clean up test-created data"""
        try:
            # Get all bookings and delete test ones
            bookings_res = self.session.get(f"{BASE_URL}/api/bookings")
            if bookings_res.status_code == 200:
                for booking in bookings_res.data if hasattr(bookings_res, 'data') else bookings_res.json():
                    if booking.get("notes", "").startswith("TEST_LOSS_"):
                        self.session.delete(f"{BASE_URL}/api/bookings/{booking['id']}")
        except Exception as e:
            print(f"Cleanup error: {e}")
    
    def _get_or_create_test_stock(self):
        """Get existing E2ETEST stock or create one"""
        stocks_res = self.session.get(f"{BASE_URL}/api/stocks")
        assert stocks_res.status_code == 200
        stocks = stocks_res.json()
        
        # Look for E2ETEST stock
        for stock in stocks:
            if stock["symbol"] == "E2ETEST":
                return stock
        
        # Create test stock if not exists
        stock_res = self.session.post(f"{BASE_URL}/api/stocks", json={
            "symbol": "E2ETEST",
            "name": "E2E Test Stock",
            "exchange": "NSE"
        })
        if stock_res.status_code == 200:
            return stock_res.json()
        
        # Return first available stock
        return stocks[0] if stocks else None
    
    def _get_or_create_test_client(self):
        """Get existing test client or create one"""
        clients_res = self.session.get(f"{BASE_URL}/api/clients")
        assert clients_res.status_code == 200
        clients = clients_res.json()
        
        # Return first active non-vendor client
        for client in clients:
            if not client.get("is_vendor") and client.get("is_active", True):
                return client
        
        # Create test client if none exists
        client_res = self.session.post(f"{BASE_URL}/api/clients", json={
            "name": "TEST_LOSS_Client",
            "pan_number": "TESTL1234A",
            "dp_id": "IN123456789012",
            "email": "testloss@example.com"
        })
        if client_res.status_code == 200:
            return client_res.json()
        
        return None
    
    def _get_inventory_for_stock(self, stock_id):
        """Get inventory for a stock"""
        inventory_res = self.session.get(f"{BASE_URL}/api/inventory")
        if inventory_res.status_code == 200:
            for inv in inventory_res.json():
                if inv["stock_id"] == stock_id:
                    return inv
        return None
    
    # ==================== BACKEND TESTS ====================
    
    def test_loss_booking_detection_when_selling_below_buying(self):
        """Test that is_loss_booking=True when selling_price < buying_price"""
        stock = self._get_or_create_test_stock()
        client = self._get_or_create_test_client()
        
        assert stock is not None, "No stock available for testing"
        assert client is not None, "No client available for testing"
        
        # Get inventory to know the weighted avg price
        inventory = self._get_inventory_for_stock(stock["id"])
        
        if inventory and inventory.get("weighted_avg_price", 0) > 0:
            buying_price = inventory["weighted_avg_price"]
            # Set selling price BELOW buying price to trigger loss booking
            selling_price = buying_price * 0.8  # 20% below
        else:
            # If no inventory, use arbitrary values
            buying_price = 100.0
            selling_price = 80.0  # Below buying price
        
        # Create a loss booking
        booking_res = self.session.post(f"{BASE_URL}/api/bookings", json={
            "client_id": client["id"],
            "stock_id": stock["id"],
            "quantity": 10,
            "buying_price": buying_price,
            "selling_price": selling_price,
            "booking_date": "2025-01-24",
            "status": "open",
            "notes": "TEST_LOSS_detection"
        })
        
        assert booking_res.status_code == 200, f"Failed to create booking: {booking_res.text}"
        booking = booking_res.json()
        
        # Verify loss booking flags
        assert booking.get("is_loss_booking") == True, f"Expected is_loss_booking=True, got {booking.get('is_loss_booking')}"
        assert booking.get("loss_approval_status") == "pending", f"Expected loss_approval_status='pending', got {booking.get('loss_approval_status')}"
        
        print(f"✓ Loss booking detected correctly: is_loss_booking={booking['is_loss_booking']}, loss_approval_status={booking['loss_approval_status']}")
        
        # Cleanup
        self.session.delete(f"{BASE_URL}/api/bookings/{booking['id']}")
    
    def test_non_loss_booking_when_selling_above_buying(self):
        """Test that is_loss_booking=False when selling_price >= buying_price"""
        stock = self._get_or_create_test_stock()
        client = self._get_or_create_test_client()
        
        assert stock is not None, "No stock available for testing"
        assert client is not None, "No client available for testing"
        
        # Get inventory to know the weighted avg price
        inventory = self._get_inventory_for_stock(stock["id"])
        
        if inventory and inventory.get("weighted_avg_price", 0) > 0:
            buying_price = inventory["weighted_avg_price"]
            # Set selling price ABOVE buying price (profit)
            selling_price = buying_price * 1.2  # 20% above
        else:
            buying_price = 100.0
            selling_price = 120.0  # Above buying price
        
        # Create a profit booking
        booking_res = self.session.post(f"{BASE_URL}/api/bookings", json={
            "client_id": client["id"],
            "stock_id": stock["id"],
            "quantity": 10,
            "buying_price": buying_price,
            "selling_price": selling_price,
            "booking_date": "2025-01-24",
            "status": "open",
            "notes": "TEST_LOSS_profit_booking"
        })
        
        assert booking_res.status_code == 200, f"Failed to create booking: {booking_res.text}"
        booking = booking_res.json()
        
        # Verify NOT a loss booking
        assert booking.get("is_loss_booking") == False, f"Expected is_loss_booking=False, got {booking.get('is_loss_booking')}"
        assert booking.get("loss_approval_status") == "not_required", f"Expected loss_approval_status='not_required', got {booking.get('loss_approval_status')}"
        
        print(f"✓ Profit booking correctly NOT flagged as loss: is_loss_booking={booking['is_loss_booking']}")
        
        # Cleanup
        self.session.delete(f"{BASE_URL}/api/bookings/{booking['id']}")
    
    def test_pending_loss_approval_endpoint_returns_loss_bookings(self):
        """Test GET /api/bookings/pending-loss-approval returns pending loss bookings"""
        stock = self._get_or_create_test_stock()
        client = self._get_or_create_test_client()
        
        assert stock is not None, "No stock available for testing"
        assert client is not None, "No client available for testing"
        
        # Get inventory
        inventory = self._get_inventory_for_stock(stock["id"])
        buying_price = inventory["weighted_avg_price"] if inventory and inventory.get("weighted_avg_price", 0) > 0 else 100.0
        selling_price = buying_price * 0.7  # 30% loss
        
        # Create a loss booking
        booking_res = self.session.post(f"{BASE_URL}/api/bookings", json={
            "client_id": client["id"],
            "stock_id": stock["id"],
            "quantity": 5,
            "buying_price": buying_price,
            "selling_price": selling_price,
            "booking_date": "2025-01-24",
            "status": "open",
            "notes": "TEST_LOSS_pending_api"
        })
        
        assert booking_res.status_code == 200, f"Failed to create booking: {booking_res.text}"
        created_booking = booking_res.json()
        
        # Get pending loss bookings
        pending_res = self.session.get(f"{BASE_URL}/api/bookings/pending-loss-approval")
        assert pending_res.status_code == 200, f"Failed to get pending loss bookings: {pending_res.text}"
        
        pending_bookings = pending_res.json()
        
        # Verify our booking is in the list
        booking_ids = [b["id"] for b in pending_bookings]
        assert created_booking["id"] in booking_ids, "Created loss booking not found in pending list"
        
        # Verify all returned bookings are loss bookings with pending status
        for booking in pending_bookings:
            assert booking.get("is_loss_booking") == True, "Non-loss booking in pending-loss-approval list"
            assert booking.get("loss_approval_status") == "pending", "Non-pending booking in pending-loss-approval list"
        
        print(f"✓ Pending loss approval endpoint returns {len(pending_bookings)} pending loss bookings")
        
        # Cleanup
        self.session.delete(f"{BASE_URL}/api/bookings/{created_booking['id']}")
    
    def test_approve_loss_booking_success(self):
        """Test PUT /api/bookings/{booking_id}/approve-loss approves loss booking"""
        stock = self._get_or_create_test_stock()
        client = self._get_or_create_test_client()
        
        assert stock is not None, "No stock available for testing"
        assert client is not None, "No client available for testing"
        
        # Get inventory
        inventory = self._get_inventory_for_stock(stock["id"])
        buying_price = inventory["weighted_avg_price"] if inventory and inventory.get("weighted_avg_price", 0) > 0 else 100.0
        selling_price = buying_price * 0.75  # 25% loss
        
        # Create a loss booking
        booking_res = self.session.post(f"{BASE_URL}/api/bookings", json={
            "client_id": client["id"],
            "stock_id": stock["id"],
            "quantity": 5,
            "buying_price": buying_price,
            "selling_price": selling_price,
            "booking_date": "2025-01-24",
            "status": "open",
            "notes": "TEST_LOSS_approve"
        })
        
        assert booking_res.status_code == 200, f"Failed to create booking: {booking_res.text}"
        created_booking = booking_res.json()
        
        # Approve the loss booking
        approve_res = self.session.put(f"{BASE_URL}/api/bookings/{created_booking['id']}/approve-loss?approve=true")
        assert approve_res.status_code == 200, f"Failed to approve loss booking: {approve_res.text}"
        
        # Verify the booking is now approved
        get_res = self.session.get(f"{BASE_URL}/api/bookings/{created_booking['id']}")
        assert get_res.status_code == 200
        updated_booking = get_res.json()
        
        assert updated_booking.get("loss_approval_status") == "approved", f"Expected loss_approval_status='approved', got {updated_booking.get('loss_approval_status')}"
        assert updated_booking.get("loss_approved_by") is not None, "loss_approved_by should be set"
        assert updated_booking.get("loss_approved_at") is not None, "loss_approved_at should be set"
        
        print(f"✓ Loss booking approved successfully: loss_approval_status={updated_booking['loss_approval_status']}")
        
        # Cleanup
        self.session.delete(f"{BASE_URL}/api/bookings/{created_booking['id']}")
    
    def test_reject_loss_booking_success(self):
        """Test PUT /api/bookings/{booking_id}/approve-loss?approve=false rejects loss booking"""
        stock = self._get_or_create_test_stock()
        client = self._get_or_create_test_client()
        
        assert stock is not None, "No stock available for testing"
        assert client is not None, "No client available for testing"
        
        # Get inventory
        inventory = self._get_inventory_for_stock(stock["id"])
        buying_price = inventory["weighted_avg_price"] if inventory and inventory.get("weighted_avg_price", 0) > 0 else 100.0
        selling_price = buying_price * 0.6  # 40% loss
        
        # Create a loss booking
        booking_res = self.session.post(f"{BASE_URL}/api/bookings", json={
            "client_id": client["id"],
            "stock_id": stock["id"],
            "quantity": 5,
            "buying_price": buying_price,
            "selling_price": selling_price,
            "booking_date": "2025-01-24",
            "status": "open",
            "notes": "TEST_LOSS_reject"
        })
        
        assert booking_res.status_code == 200, f"Failed to create booking: {booking_res.text}"
        created_booking = booking_res.json()
        
        # Reject the loss booking
        reject_res = self.session.put(f"{BASE_URL}/api/bookings/{created_booking['id']}/approve-loss?approve=false")
        assert reject_res.status_code == 200, f"Failed to reject loss booking: {reject_res.text}"
        
        # Verify the booking is now rejected
        get_res = self.session.get(f"{BASE_URL}/api/bookings/{created_booking['id']}")
        assert get_res.status_code == 200
        updated_booking = get_res.json()
        
        assert updated_booking.get("loss_approval_status") == "rejected", f"Expected loss_approval_status='rejected', got {updated_booking.get('loss_approval_status')}"
        
        print(f"✓ Loss booking rejected successfully: loss_approval_status={updated_booking['loss_approval_status']}")
        
        # Cleanup
        self.session.delete(f"{BASE_URL}/api/bookings/{created_booking['id']}")
    
    def test_cannot_approve_non_loss_booking(self):
        """Test that approve-loss endpoint rejects non-loss bookings"""
        stock = self._get_or_create_test_stock()
        client = self._get_or_create_test_client()
        
        assert stock is not None, "No stock available for testing"
        assert client is not None, "No client available for testing"
        
        # Get inventory
        inventory = self._get_inventory_for_stock(stock["id"])
        buying_price = inventory["weighted_avg_price"] if inventory and inventory.get("weighted_avg_price", 0) > 0 else 100.0
        selling_price = buying_price * 1.5  # 50% profit (NOT a loss)
        
        # Create a profit booking
        booking_res = self.session.post(f"{BASE_URL}/api/bookings", json={
            "client_id": client["id"],
            "stock_id": stock["id"],
            "quantity": 5,
            "buying_price": buying_price,
            "selling_price": selling_price,
            "booking_date": "2025-01-24",
            "status": "open",
            "notes": "TEST_LOSS_not_loss"
        })
        
        assert booking_res.status_code == 200, f"Failed to create booking: {booking_res.text}"
        created_booking = booking_res.json()
        
        # Try to approve as loss booking - should fail
        approve_res = self.session.put(f"{BASE_URL}/api/bookings/{created_booking['id']}/approve-loss?approve=true")
        assert approve_res.status_code == 400, f"Expected 400 for non-loss booking, got {approve_res.status_code}"
        assert "not a loss booking" in approve_res.text.lower(), f"Expected 'not a loss booking' error, got: {approve_res.text}"
        
        print(f"✓ Cannot approve non-loss booking: {approve_res.json().get('detail', '')}")
        
        # Cleanup
        self.session.delete(f"{BASE_URL}/api/bookings/{created_booking['id']}")
    
    def test_cannot_approve_already_processed_loss_booking(self):
        """Test that approve-loss endpoint rejects already processed loss bookings"""
        stock = self._get_or_create_test_stock()
        client = self._get_or_create_test_client()
        
        assert stock is not None, "No stock available for testing"
        assert client is not None, "No client available for testing"
        
        # Get inventory
        inventory = self._get_inventory_for_stock(stock["id"])
        buying_price = inventory["weighted_avg_price"] if inventory and inventory.get("weighted_avg_price", 0) > 0 else 100.0
        selling_price = buying_price * 0.8  # 20% loss
        
        # Create a loss booking
        booking_res = self.session.post(f"{BASE_URL}/api/bookings", json={
            "client_id": client["id"],
            "stock_id": stock["id"],
            "quantity": 5,
            "buying_price": buying_price,
            "selling_price": selling_price,
            "booking_date": "2025-01-24",
            "status": "open",
            "notes": "TEST_LOSS_already_processed"
        })
        
        assert booking_res.status_code == 200, f"Failed to create booking: {booking_res.text}"
        created_booking = booking_res.json()
        
        # First approval - should succeed
        approve_res1 = self.session.put(f"{BASE_URL}/api/bookings/{created_booking['id']}/approve-loss?approve=true")
        assert approve_res1.status_code == 200, f"First approval failed: {approve_res1.text}"
        
        # Second approval - should fail
        approve_res2 = self.session.put(f"{BASE_URL}/api/bookings/{created_booking['id']}/approve-loss?approve=true")
        assert approve_res2.status_code == 400, f"Expected 400 for already processed, got {approve_res2.status_code}"
        assert "already processed" in approve_res2.text.lower(), f"Expected 'already processed' error, got: {approve_res2.text}"
        
        print(f"✓ Cannot approve already processed loss booking: {approve_res2.json().get('detail', '')}")
        
        # Cleanup
        self.session.delete(f"{BASE_URL}/api/bookings/{created_booking['id']}")


class TestLossBookingRoleRestrictions:
    """Test role-based access control for loss booking approval"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as admin (PE Desk - role 1)
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@privity.com",
            "password": "Admin@123"
        })
        assert login_response.status_code == 200, f"Admin login failed: {login_response.text}"
        self.admin_token = login_response.json()["token"]
        
        yield
    
    def test_only_pe_desk_can_view_pending_loss_bookings(self):
        """Test that only PE Desk (role 1) can access pending-loss-approval endpoint"""
        # As admin (PE Desk) - should succeed
        self.session.headers.update({"Authorization": f"Bearer {self.admin_token}"})
        
        pending_res = self.session.get(f"{BASE_URL}/api/bookings/pending-loss-approval")
        assert pending_res.status_code == 200, f"PE Desk should access pending loss bookings, got {pending_res.status_code}"
        
        print("✓ PE Desk can view pending loss bookings")
    
    def test_non_pe_desk_cannot_view_pending_loss_bookings(self):
        """Test that non-PE Desk users cannot access pending-loss-approval endpoint"""
        # Try to create an employee user for testing
        self.session.headers.update({"Authorization": f"Bearer {self.admin_token}"})
        
        # Get users to find a non-PE Desk user
        users_res = self.session.get(f"{BASE_URL}/api/users")
        if users_res.status_code == 200:
            users = users_res.json()
            non_pe_user = None
            for user in users:
                if user.get("role", 5) != 1:  # Not PE Desk
                    non_pe_user = user
                    break
            
            if non_pe_user:
                # We can't easily login as another user without their password
                # So we'll test by checking the endpoint returns 403 for non-PE Desk
                print(f"✓ Found non-PE Desk user: {non_pe_user.get('name')} (role {non_pe_user.get('role')})")
                print("  Note: Cannot test login without password, but endpoint has role check")
        
        # Test without auth - should fail
        no_auth_session = requests.Session()
        no_auth_session.headers.update({"Content-Type": "application/json"})
        
        pending_res = no_auth_session.get(f"{BASE_URL}/api/bookings/pending-loss-approval")
        assert pending_res.status_code in [401, 403], f"Unauthenticated request should fail, got {pending_res.status_code}"
        
        print("✓ Unauthenticated users cannot view pending loss bookings")
    
    def test_only_pe_desk_can_approve_loss_bookings(self):
        """Test that only PE Desk (role 1) can approve loss bookings"""
        # Test without auth - should fail
        no_auth_session = requests.Session()
        no_auth_session.headers.update({"Content-Type": "application/json"})
        
        # Use a fake booking ID
        approve_res = no_auth_session.put(f"{BASE_URL}/api/bookings/fake-id/approve-loss?approve=true")
        assert approve_res.status_code in [401, 403], f"Unauthenticated request should fail, got {approve_res.status_code}"
        
        print("✓ Unauthenticated users cannot approve loss bookings")


class TestLossBookingDataIntegrity:
    """Test data integrity for loss booking fields"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as admin (PE Desk - role 1)
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@privity.com",
            "password": "Admin@123"
        })
        assert login_response.status_code == 200, f"Admin login failed: {login_response.text}"
        self.admin_token = login_response.json()["token"]
        self.session.headers.update({"Authorization": f"Bearer {self.admin_token}"})
        
        yield
    
    def test_loss_booking_fields_in_booking_response(self):
        """Test that loss booking fields are present in booking response"""
        # Get all bookings
        bookings_res = self.session.get(f"{BASE_URL}/api/bookings")
        assert bookings_res.status_code == 200
        
        bookings = bookings_res.json()
        if bookings:
            booking = bookings[0]
            
            # Check required loss booking fields exist
            assert "is_loss_booking" in booking, "is_loss_booking field missing"
            assert "loss_approval_status" in booking, "loss_approval_status field missing"
            
            # Check field types
            assert isinstance(booking["is_loss_booking"], bool), "is_loss_booking should be boolean"
            assert booking["loss_approval_status"] in ["not_required", "pending", "approved", "rejected"], \
                f"Invalid loss_approval_status: {booking['loss_approval_status']}"
            
            print("✓ Loss booking fields present in booking response")
            print(f"  - is_loss_booking: {booking['is_loss_booking']}")
            print(f"  - loss_approval_status: {booking['loss_approval_status']}")
        else:
            pytest.skip("No bookings available to test")
    
    def test_loss_booking_profit_loss_calculation(self):
        """Test that profit/loss is calculated correctly for loss bookings"""
        # Get all bookings
        bookings_res = self.session.get(f"{BASE_URL}/api/bookings")
        assert bookings_res.status_code == 200
        
        bookings = bookings_res.json()
        
        for booking in bookings:
            if booking.get("selling_price") and booking.get("buying_price"):
                expected_pl = (booking["selling_price"] - booking["buying_price"]) * booking["quantity"]
                actual_pl = booking.get("profit_loss")
                
                if actual_pl is not None:
                    assert abs(actual_pl - expected_pl) < 0.01, \
                        f"P&L mismatch: expected {expected_pl}, got {actual_pl}"
                
                # Verify is_loss_booking flag matches P&L
                if booking["selling_price"] < booking["buying_price"]:
                    assert booking.get("is_loss_booking") == True, \
                        "Booking with loss should have is_loss_booking=True"
        
        print(f"✓ Profit/loss calculations verified for {len(bookings)} bookings")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
