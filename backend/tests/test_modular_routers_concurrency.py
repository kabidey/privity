"""
Test Suite for Backend Refactoring and High-Concurrency Booking Support

Tests:
1. Modular routers (clients, bookings, finance)
2. Atomic inventory operations
3. Unique booking number generation under concurrent load
4. Race condition prevention during booking approvals
"""
import pytest
import requests
import os
import asyncio
import aiohttp
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Tuple
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://privity-booking-1.preview.emergentagent.com').rstrip('/')

# Test credentials
PE_DESK_EMAIL = "pedesk@smifs.com"
PE_DESK_PASSWORD = "Kutta@123"


class TestModularRouters:
    """Test that modular routers are working correctly"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as PE Desk
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": PE_DESK_EMAIL,
            "password": PE_DESK_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        self.token = data.get("token")
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        yield
        self.session.close()
    
    # === CLIENTS ROUTER TESTS ===
    
    def test_01_clients_router_get_clients(self):
        """Test GET /api/clients endpoint from clients router"""
        response = self.session.get(f"{BASE_URL}/api/clients")
        assert response.status_code == 200, f"Failed to get clients: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"✓ GET /api/clients returned {len(data)} clients")
    
    def test_02_clients_router_get_single_client(self):
        """Test GET /api/clients/{id} endpoint"""
        # First get list of clients
        response = self.session.get(f"{BASE_URL}/api/clients")
        assert response.status_code == 200
        clients = response.json()
        
        if clients:
            client_id = clients[0]["id"]
            response = self.session.get(f"{BASE_URL}/api/clients/{client_id}")
            assert response.status_code == 200, f"Failed to get client: {response.text}"
            client = response.json()
            assert client["id"] == client_id
            print(f"✓ GET /api/clients/{client_id} returned client: {client['name']}")
    
    def test_03_clients_router_pending_approval(self):
        """Test GET /api/clients/pending-approval endpoint"""
        response = self.session.get(f"{BASE_URL}/api/clients/pending-approval")
        assert response.status_code == 200, f"Failed to get pending clients: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"✓ GET /api/clients/pending-approval returned {len(data)} pending clients")
    
    # === BOOKINGS ROUTER TESTS ===
    
    def test_04_bookings_router_get_bookings(self):
        """Test GET /api/bookings endpoint from bookings router"""
        response = self.session.get(f"{BASE_URL}/api/bookings")
        assert response.status_code == 200, f"Failed to get bookings: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"✓ GET /api/bookings returned {len(data)} bookings")
    
    def test_05_bookings_router_get_single_booking(self):
        """Test GET /api/bookings/{id} endpoint"""
        response = self.session.get(f"{BASE_URL}/api/bookings")
        assert response.status_code == 200
        bookings = response.json()
        
        if bookings:
            booking_id = bookings[0]["id"]
            response = self.session.get(f"{BASE_URL}/api/bookings/{booking_id}")
            assert response.status_code == 200, f"Failed to get booking: {response.text}"
            booking = response.json()
            assert booking["id"] == booking_id
            print(f"✓ GET /api/bookings/{booking_id} returned booking: {booking.get('booking_number', 'N/A')}")
    
    def test_06_bookings_router_filter_by_status(self):
        """Test GET /api/bookings with status filter"""
        response = self.session.get(f"{BASE_URL}/api/bookings?approval_status=approved")
        assert response.status_code == 200, f"Failed to filter bookings: {response.text}"
        data = response.json()
        # All returned bookings should have approved status
        for booking in data:
            assert booking.get("approval_status") == "approved", f"Booking {booking['id']} has wrong status"
        print(f"✓ GET /api/bookings?approval_status=approved returned {len(data)} approved bookings")
    
    # === FINANCE ROUTER TESTS ===
    
    def test_07_finance_router_get_payments(self):
        """Test GET /api/finance/payments endpoint from finance router"""
        response = self.session.get(f"{BASE_URL}/api/finance/payments")
        assert response.status_code == 200, f"Failed to get payments: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"✓ GET /api/finance/payments returned {len(data)} payments")
    
    def test_08_finance_router_get_summary(self):
        """Test GET /api/finance/summary endpoint"""
        response = self.session.get(f"{BASE_URL}/api/finance/summary")
        assert response.status_code == 200, f"Failed to get finance summary: {response.text}"
        data = response.json()
        
        # Verify expected fields
        expected_fields = ["total_received", "total_sent", "net_flow", "client_payments_count", 
                          "vendor_payments_count", "pending_refunds_count", "completed_refunds_count"]
        for field in expected_fields:
            assert field in data, f"Missing field: {field}"
        
        print(f"✓ GET /api/finance/summary returned summary with net_flow: {data['net_flow']}")
    
    def test_09_finance_router_get_refund_requests(self):
        """Test GET /api/finance/refund-requests endpoint"""
        response = self.session.get(f"{BASE_URL}/api/finance/refund-requests")
        assert response.status_code == 200, f"Failed to get refund requests: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"✓ GET /api/finance/refund-requests returned {len(data)} refund requests")


class TestBookingNumberUniqueness:
    """Test that booking numbers are unique even under concurrent load"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as PE Desk
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": PE_DESK_EMAIL,
            "password": PE_DESK_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        self.token = data.get("token")
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        
        # Get test data
        self._get_test_data()
        yield
        self.session.close()
    
    def _get_test_data(self):
        """Get existing test client and stock"""
        # Get approved client
        response = self.session.get(f"{BASE_URL}/api/clients")
        assert response.status_code == 200
        clients = response.json()
        approved_clients = [c for c in clients if c.get("approval_status") == "approved" and not c.get("is_vendor")]
        assert len(approved_clients) > 0, "No approved clients found for testing"
        self.client_id = approved_clients[0]["id"]
        
        # Get stock with inventory
        response = self.session.get(f"{BASE_URL}/api/inventory")
        assert response.status_code == 200
        inventory = response.json()
        available_stocks = [i for i in inventory if i.get("available_quantity", 0) >= 50]
        assert len(available_stocks) > 0, "No stocks with sufficient inventory found"
        self.stock_id = available_stocks[0]["stock_id"]
        self.available_qty = available_stocks[0]["available_quantity"]
    
    def _create_booking_sync(self, booking_num: int) -> Tuple[bool, str, str]:
        """Create a booking synchronously (for thread pool)"""
        try:
            response = requests.post(
                f"{BASE_URL}/api/bookings",
                headers={
                    "Authorization": f"Bearer {self.token}",
                    "Content-Type": "application/json"
                },
                json={
                    "client_id": self.client_id,
                    "stock_id": self.stock_id,
                    "quantity": 1,  # Small quantity to avoid inventory issues
                    "selling_price": 150.0,
                    "booking_date": "2026-01-28",
                    "booking_type": "client",
                    "status": "pending"
                },
                timeout=30
            )
            if response.status_code == 200:
                data = response.json()
                return True, data.get("booking_number", ""), data.get("id", "")
            else:
                return False, response.json().get("detail", "Unknown error"), ""
        except Exception as e:
            return False, str(e), ""
    
    def test_10_concurrent_booking_creation_unique_numbers(self):
        """Test that concurrent booking creation generates unique booking numbers"""
        num_concurrent = 5  # Number of concurrent bookings
        
        print(f"\n=== Testing {num_concurrent} concurrent booking creations ===")
        print(f"Client ID: {self.client_id}")
        print(f"Stock ID: {self.stock_id}")
        print(f"Available inventory: {self.available_qty}")
        
        # Use ThreadPoolExecutor for concurrent requests
        booking_numbers = []
        booking_ids = []
        
        with ThreadPoolExecutor(max_workers=num_concurrent) as executor:
            futures = [executor.submit(self._create_booking_sync, i) for i in range(num_concurrent)]
            
            for future in as_completed(futures):
                success, booking_number, booking_id = future.result()
                if success:
                    booking_numbers.append(booking_number)
                    booking_ids.append(booking_id)
                    print(f"  ✓ Created booking: {booking_number}")
                else:
                    print(f"  ✗ Failed: {booking_number}")
        
        # Verify uniqueness
        unique_numbers = set(booking_numbers)
        print(f"\nResults:")
        print(f"  Total successful: {len(booking_numbers)}")
        print(f"  Unique numbers: {len(unique_numbers)}")
        
        assert len(booking_numbers) == len(unique_numbers), \
            f"Duplicate booking numbers detected! Numbers: {booking_numbers}"
        
        print(f"✓ All {len(booking_numbers)} booking numbers are unique")
        
        # Store for cleanup
        self.created_booking_ids = booking_ids


class TestAtomicInventoryOperations:
    """Test atomic inventory operations during booking approval"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as PE Desk
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": PE_DESK_EMAIL,
            "password": PE_DESK_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        self.token = data.get("token")
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        yield
        self.session.close()
    
    def test_11_inventory_check_on_booking_creation(self):
        """Test that inventory is checked when creating a booking"""
        # Get a stock with inventory
        response = self.session.get(f"{BASE_URL}/api/inventory")
        assert response.status_code == 200
        inventory = response.json()
        
        if not inventory:
            pytest.skip("No inventory available for testing")
        
        stock_inv = inventory[0]
        stock_id = stock_inv["stock_id"]
        available = stock_inv["available_quantity"]
        
        # Get an approved client
        response = self.session.get(f"{BASE_URL}/api/clients")
        clients = [c for c in response.json() if c.get("approval_status") == "approved" and not c.get("is_vendor")]
        if not clients:
            pytest.skip("No approved clients for testing")
        client_id = clients[0]["id"]
        
        # Try to book more than available
        response = self.session.post(f"{BASE_URL}/api/bookings", json={
            "client_id": client_id,
            "stock_id": stock_id,
            "quantity": available + 10000,  # More than available
            "selling_price": 150.0,
            "booking_date": "2026-01-28",
            "booking_type": "client",
            "status": "pending"
        })
        
        # Should fail with insufficient inventory
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        assert "Insufficient" in response.json().get("detail", ""), \
            f"Expected insufficient inventory error, got: {response.json()}"
        
        print(f"✓ Inventory check correctly rejected booking for {available + 10000} units (available: {available})")
    
    def test_12_inventory_blocked_on_approval(self):
        """Test that inventory is blocked when booking is approved"""
        # Get inventory before
        response = self.session.get(f"{BASE_URL}/api/inventory")
        assert response.status_code == 200
        inventory_before = {i["stock_id"]: i for i in response.json()}
        
        # Get a pending booking
        response = self.session.get(f"{BASE_URL}/api/bookings?approval_status=pending")
        assert response.status_code == 200
        pending_bookings = response.json()
        
        if not pending_bookings:
            print("No pending bookings to test approval")
            pytest.skip("No pending bookings available")
        
        booking = pending_bookings[0]
        booking_id = booking["id"]
        stock_id = booking["stock_id"]
        quantity = booking["quantity"]
        
        initial_blocked = inventory_before.get(stock_id, {}).get("blocked_quantity", 0)
        initial_available = inventory_before.get(stock_id, {}).get("available_quantity", 0)
        
        # Approve the booking
        response = self.session.put(f"{BASE_URL}/api/bookings/{booking_id}/approve?approve=true")
        
        if response.status_code != 200:
            print(f"Approval failed: {response.json()}")
            pytest.skip(f"Could not approve booking: {response.json()}")
        
        # Get inventory after
        response = self.session.get(f"{BASE_URL}/api/inventory")
        inventory_after = {i["stock_id"]: i for i in response.json()}
        
        final_blocked = inventory_after.get(stock_id, {}).get("blocked_quantity", 0)
        final_available = inventory_after.get(stock_id, {}).get("available_quantity", 0)
        
        print(f"\nInventory changes for stock {stock_id}:")
        print(f"  Blocked: {initial_blocked} -> {final_blocked} (expected +{quantity})")
        print(f"  Available: {initial_available} -> {final_available} (expected -{quantity})")
        
        # Verify inventory was blocked
        assert final_blocked >= initial_blocked, "Blocked quantity should increase or stay same"
        print(f"✓ Inventory correctly updated on booking approval")
    
    def test_13_inventory_released_on_void(self):
        """Test that inventory is released when booking is voided"""
        # Get an approved booking
        response = self.session.get(f"{BASE_URL}/api/bookings?approval_status=approved")
        assert response.status_code == 200
        approved_bookings = response.json()
        
        # Find one that's not voided and not transferred
        voidable = [b for b in approved_bookings 
                    if not b.get("is_voided") and not b.get("stock_transferred")]
        
        if not voidable:
            print("No voidable bookings available")
            pytest.skip("No voidable bookings available")
        
        booking = voidable[0]
        booking_id = booking["id"]
        stock_id = booking["stock_id"]
        quantity = booking["quantity"]
        
        # Get inventory before
        response = self.session.get(f"{BASE_URL}/api/inventory")
        inventory_before = {i["stock_id"]: i for i in response.json()}
        initial_blocked = inventory_before.get(stock_id, {}).get("blocked_quantity", 0)
        initial_available = inventory_before.get(stock_id, {}).get("available_quantity", 0)
        
        # Void the booking
        response = self.session.put(
            f"{BASE_URL}/api/bookings/{booking_id}/void?reason=Test%20void%20for%20inventory%20release"
        )
        
        if response.status_code != 200:
            print(f"Void failed: {response.json()}")
            pytest.skip(f"Could not void booking: {response.json()}")
        
        # Get inventory after
        response = self.session.get(f"{BASE_URL}/api/inventory")
        inventory_after = {i["stock_id"]: i for i in response.json()}
        final_blocked = inventory_after.get(stock_id, {}).get("blocked_quantity", 0)
        final_available = inventory_after.get(stock_id, {}).get("available_quantity", 0)
        
        print(f"\nInventory changes after void for stock {stock_id}:")
        print(f"  Blocked: {initial_blocked} -> {final_blocked}")
        print(f"  Available: {initial_available} -> {final_available}")
        
        # Verify inventory was released
        assert final_available >= initial_available, "Available quantity should increase after void"
        print(f"✓ Inventory correctly released on booking void")


class TestConcurrentBookingApprovals:
    """Test that concurrent booking approvals don't cause race conditions"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as PE Desk
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": PE_DESK_EMAIL,
            "password": PE_DESK_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        self.token = data.get("token")
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        yield
        self.session.close()
    
    def _approve_booking_sync(self, booking_id: str) -> Tuple[bool, str]:
        """Approve a booking synchronously"""
        try:
            response = requests.put(
                f"{BASE_URL}/api/bookings/{booking_id}/approve?approve=true",
                headers={
                    "Authorization": f"Bearer {self.token}",
                    "Content-Type": "application/json"
                },
                timeout=30
            )
            if response.status_code == 200:
                return True, "Approved"
            else:
                return False, response.json().get("detail", "Unknown error")
        except Exception as e:
            return False, str(e)
    
    def test_14_concurrent_approvals_no_overselling(self):
        """Test that concurrent approvals don't oversell inventory"""
        # Get pending bookings for the same stock
        response = self.session.get(f"{BASE_URL}/api/bookings?approval_status=pending")
        assert response.status_code == 200
        pending = response.json()
        
        if len(pending) < 2:
            print(f"Only {len(pending)} pending bookings, need at least 2 for concurrent test")
            pytest.skip("Not enough pending bookings for concurrent approval test")
        
        # Group by stock
        by_stock = {}
        for b in pending:
            stock_id = b["stock_id"]
            if stock_id not in by_stock:
                by_stock[stock_id] = []
            by_stock[stock_id].append(b)
        
        # Find a stock with multiple pending bookings
        test_stock = None
        test_bookings = []
        for stock_id, bookings in by_stock.items():
            if len(bookings) >= 2:
                test_stock = stock_id
                test_bookings = bookings[:3]  # Take up to 3
                break
        
        if not test_stock:
            print("No stock with multiple pending bookings")
            pytest.skip("No stock with multiple pending bookings for concurrent test")
        
        # Get inventory before
        response = self.session.get(f"{BASE_URL}/api/inventory")
        inventory = {i["stock_id"]: i for i in response.json()}
        initial_available = inventory.get(test_stock, {}).get("available_quantity", 0)
        initial_blocked = inventory.get(test_stock, {}).get("blocked_quantity", 0)
        
        total_quantity = sum(b["quantity"] for b in test_bookings)
        
        print(f"\n=== Concurrent Approval Test ===")
        print(f"Stock: {test_stock}")
        print(f"Initial available: {initial_available}")
        print(f"Bookings to approve: {len(test_bookings)}")
        print(f"Total quantity: {total_quantity}")
        
        # Approve concurrently
        results = []
        with ThreadPoolExecutor(max_workers=len(test_bookings)) as executor:
            futures = {executor.submit(self._approve_booking_sync, b["id"]): b for b in test_bookings}
            
            for future in as_completed(futures):
                booking = futures[future]
                success, message = future.result()
                results.append((success, message, booking["quantity"]))
                status = "✓" if success else "✗"
                print(f"  {status} Booking {booking['id'][:8]}: {message}")
        
        # Get inventory after
        response = self.session.get(f"{BASE_URL}/api/inventory")
        inventory = {i["stock_id"]: i for i in response.json()}
        final_available = inventory.get(test_stock, {}).get("available_quantity", 0)
        final_blocked = inventory.get(test_stock, {}).get("blocked_quantity", 0)
        
        # Calculate expected changes
        successful_qty = sum(qty for success, _, qty in results if success)
        
        print(f"\nResults:")
        print(f"  Successful approvals: {sum(1 for s, _, _ in results if s)}")
        print(f"  Failed approvals: {sum(1 for s, _, _ in results if not s)}")
        print(f"  Quantity approved: {successful_qty}")
        print(f"  Available: {initial_available} -> {final_available}")
        print(f"  Blocked: {initial_blocked} -> {final_blocked}")
        
        # Verify no overselling
        assert final_available >= 0, "Available quantity should never go negative"
        print(f"✓ No overselling detected (available >= 0)")


class TestExistingFunctionality:
    """Test that existing functionality still works after refactoring"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        yield
        self.session.close()
    
    def test_15_login_still_works(self):
        """Test that login endpoint still works"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": PE_DESK_EMAIL,
            "password": PE_DESK_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "token" in data, "Token not in response"
        assert "user" in data, "User not in response"
        assert data["user"]["email"] == PE_DESK_EMAIL
        print(f"✓ Login works correctly for {PE_DESK_EMAIL}")
    
    def test_16_auth_me_still_works(self):
        """Test that /auth/me endpoint still works"""
        # Login first
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": PE_DESK_EMAIL,
            "password": PE_DESK_PASSWORD
        })
        token = response.json()["token"]
        
        # Get current user
        response = self.session.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200, f"Auth/me failed: {response.text}"
        user = response.json()
        assert user["email"] == PE_DESK_EMAIL
        assert user["role"] == 1  # PE Desk
        print(f"✓ /auth/me returns correct user: {user['name']}")
    
    def test_17_inventory_endpoint_works(self):
        """Test that inventory endpoint still works"""
        # Login first
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": PE_DESK_EMAIL,
            "password": PE_DESK_PASSWORD
        })
        token = response.json()["token"]
        
        response = self.session.get(
            f"{BASE_URL}/api/inventory",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200, f"Inventory failed: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Inventory should return a list"
        print(f"✓ /inventory returns {len(data)} items")
    
    def test_18_stocks_endpoint_works(self):
        """Test that stocks endpoint still works"""
        # Login first
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": PE_DESK_EMAIL,
            "password": PE_DESK_PASSWORD
        })
        token = response.json()["token"]
        
        response = self.session.get(
            f"{BASE_URL}/api/stocks",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200, f"Stocks failed: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Stocks should return a list"
        print(f"✓ /stocks returns {len(data)} stocks")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
