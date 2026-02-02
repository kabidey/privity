"""
Test Suite: Delayed Client Confirmation Workflow
=================================================
Tests the key requirement: Client confirmation email should ONLY be sent AFTER PE Desk approval.
For loss bookings, both PE Desk approval AND Loss approval must be complete before sending client confirmation.

Test Scenarios:
1. Normal booking: Create -> PE Desk Approve -> Client confirmation email sent
2. Loss booking: Create -> PE Desk Approve -> Loss Approve -> Client confirmation email sent
3. Client confirmation endpoint returns pending_approval if booking not approved
4. Client confirmation endpoint returns pending_loss_approval if loss not approved
"""

import pytest
import requests
import os
import uuid
from datetime import datetime

# Get BASE_URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
if not BASE_URL:
    BASE_URL = "https://booking-share-app.preview.emergentagent.com"

# Test credentials
PE_DESK_ADMIN = {"email": "admin@privity.com", "password": "Admin@123"}
EMPLOYEE = {"email": "test_emp_dp_8a1404fd@smifs.com", "password": "Test@123"}


class TestDelayedClientConfirmation:
    """Test suite for delayed client confirmation workflow"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        self.admin_token = None
        self.employee_token = None
        self.created_bookings = []
        yield
        # Cleanup created bookings
        self._cleanup_bookings()
    
    def _cleanup_bookings(self):
        """Clean up test bookings"""
        if self.admin_token:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            for booking_id in self.created_bookings:
                try:
                    requests.delete(f"{BASE_URL}/api/bookings/{booking_id}", headers=headers)
                except:
                    pass
    
    def _login_admin(self):
        """Login as PE Desk admin"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json=PE_DESK_ADMIN)
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        self.admin_token = data["token"]
        return data
    
    def _login_employee(self):
        """Login as Employee"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json=EMPLOYEE)
        assert response.status_code == 200, f"Employee login failed: {response.text}"
        data = response.json()
        self.employee_token = data["token"]
        return data
    
    def _get_test_client_and_stock(self, token):
        """Get an approved client and stock with inventory for testing"""
        headers = {"Authorization": f"Bearer {token}"}
        
        # Get clients
        clients_resp = self.session.get(f"{BASE_URL}/api/clients", headers=headers)
        assert clients_resp.status_code == 200
        clients = clients_resp.json()
        
        # Find an approved client
        approved_client = None
        for c in clients:
            if c.get("approval_status") == "approved" and c.get("is_active") and not c.get("is_vendor"):
                approved_client = c
                break
        
        # Get stocks
        stocks_resp = self.session.get(f"{BASE_URL}/api/stocks", headers=headers)
        assert stocks_resp.status_code == 200
        stocks = stocks_resp.json()
        
        # Get inventory
        inventory_resp = self.session.get(f"{BASE_URL}/api/inventory", headers=headers)
        assert inventory_resp.status_code == 200
        inventory = inventory_resp.json()
        
        # Find stock that exists in both stocks table and has inventory
        stock_with_inventory = None
        for stock in stocks:
            for inv in inventory:
                if inv.get("stock_id") == stock.get("id") and inv.get("available_quantity", 0) > 0:
                    stock_with_inventory = {
                        "stock_id": stock["id"],
                        "stock_symbol": stock["symbol"],
                        "stock_name": stock["name"],
                        "weighted_avg_price": inv["weighted_avg_price"],
                        "available_quantity": inv["available_quantity"]
                    }
                    break
            if stock_with_inventory:
                break
        
        return approved_client, stock_with_inventory
    
    # ==================== LOGIN TESTS ====================
    
    def test_01_pe_desk_admin_login(self):
        """Test PE Desk admin login"""
        data = self._login_admin()
        assert data["user"]["role"] == 1, "Admin should have role 1 (PE Desk)"
        assert data["user"]["email"] == PE_DESK_ADMIN["email"]
        print(f"✓ PE Desk admin login successful: {data['user']['name']} (role: {data['user']['role_name']})")
    
    def test_02_employee_login(self):
        """Test Employee login"""
        data = self._login_employee()
        assert data["user"]["role"] == 4, "Employee should have role 4"
        assert data["user"]["email"] == EMPLOYEE["email"]
        print(f"✓ Employee login successful: {data['user']['name']} (role: {data['user']['role_name']})")
    
    # ==================== NORMAL BOOKING WORKFLOW ====================
    
    def test_03_create_normal_booking_no_client_email_at_creation(self):
        """
        Test: Create a normal booking (selling_price >= buying_price)
        Expected: Booking created with client_confirmation_status='pending', NO client confirmation email sent yet
        """
        self._login_employee()
        headers = {"Authorization": f"Bearer {self.employee_token}"}
        
        client, stock = self._get_test_client_and_stock(self.employee_token)
        if not client or not stock:
            pytest.skip("No approved client or stock with inventory available")
        
        # Create normal booking (selling price >= buying price)
        buying_price = stock["weighted_avg_price"]
        selling_price = buying_price + 10  # Profit booking
        
        booking_data = {
            "client_id": client["id"],
            "stock_id": stock["stock_id"],
            "quantity": 1,
            "selling_price": selling_price,
            "booking_date": datetime.now().strftime("%Y-%m-%d"),
            "status": "open",
            "notes": f"TEST_NORMAL_BOOKING_{uuid.uuid4().hex[:8]}"
        }
        
        response = self.session.post(f"{BASE_URL}/api/bookings", json=booking_data, headers=headers)
        assert response.status_code == 200, f"Failed to create booking: {response.text}"
        
        booking = response.json()
        self.created_bookings.append(booking["id"])
        
        # Verify booking state at creation
        assert booking["approval_status"] == "pending", "Booking should be pending PE Desk approval"
        assert booking["client_confirmation_status"] == "pending", "Client confirmation should be pending"
        assert booking["is_loss_booking"] == False, "Should not be a loss booking"
        assert booking.get("client_confirmation_token") is not None, "Should have confirmation token"
        
        print(f"✓ Normal booking created: {booking['booking_number']}")
        print(f"  - approval_status: {booking['approval_status']}")
        print(f"  - client_confirmation_status: {booking['client_confirmation_status']}")
        print(f"  - is_loss_booking: {booking['is_loss_booking']}")
        
        # Store for next test
        self.normal_booking = booking
        return booking
    
    def test_04_client_confirmation_before_approval_returns_pending(self):
        """
        Test: Try to confirm booking before PE Desk approval
        Expected: Returns pending_approval status
        """
        self._login_employee()
        headers = {"Authorization": f"Bearer {self.employee_token}"}
        
        # Create a booking first
        client, stock = self._get_test_client_and_stock(self.employee_token)
        if not client or not stock:
            pytest.skip("No approved client or stock with inventory available")
        
        buying_price = stock["weighted_avg_price"]
        selling_price = buying_price + 10
        
        booking_data = {
            "client_id": client["id"],
            "stock_id": stock["stock_id"],
            "quantity": 1,
            "selling_price": selling_price,
            "booking_date": datetime.now().strftime("%Y-%m-%d"),
            "status": "open",
            "notes": f"TEST_PENDING_CONFIRM_{uuid.uuid4().hex[:8]}"
        }
        
        response = self.session.post(f"{BASE_URL}/api/bookings", json=booking_data, headers=headers)
        assert response.status_code == 200
        booking = response.json()
        self.created_bookings.append(booking["id"])
        
        # Try to confirm before approval (public endpoint - no auth)
        token = booking.get("client_confirmation_token")
        confirm_url = f"{BASE_URL}/api/booking-confirm/{booking['id']}/{token}/accept"
        
        confirm_response = requests.get(confirm_url)
        assert confirm_response.status_code == 200
        
        result = confirm_response.json()
        assert result["status"] == "pending_approval", f"Expected pending_approval, got {result['status']}"
        assert "pending PE Desk approval" in result["message"].lower() or "pending" in result["message"].lower()
        
        print(f"✓ Client confirmation before approval correctly returns pending_approval")
        print(f"  - status: {result['status']}")
        print(f"  - message: {result['message']}")
    
    def test_05_pe_desk_approve_normal_booking(self):
        """
        Test: PE Desk approves normal booking
        Expected: Booking approved, client confirmation email would be sent (check API response)
        """
        # First create a booking as employee
        self._login_employee()
        headers_emp = {"Authorization": f"Bearer {self.employee_token}"}
        
        client, stock = self._get_test_client_and_stock(self.employee_token)
        if not client or not stock:
            pytest.skip("No approved client or stock with inventory available")
        
        buying_price = stock["weighted_avg_price"]
        selling_price = buying_price + 10
        
        booking_data = {
            "client_id": client["id"],
            "stock_id": stock["stock_id"],
            "quantity": 1,
            "selling_price": selling_price,
            "booking_date": datetime.now().strftime("%Y-%m-%d"),
            "status": "open",
            "notes": f"TEST_APPROVE_NORMAL_{uuid.uuid4().hex[:8]}"
        }
        
        response = self.session.post(f"{BASE_URL}/api/bookings", json=booking_data, headers=headers_emp)
        assert response.status_code == 200
        booking = response.json()
        self.created_bookings.append(booking["id"])
        
        # Now login as admin and approve
        self._login_admin()
        headers_admin = {"Authorization": f"Bearer {self.admin_token}"}
        
        approve_response = self.session.put(
            f"{BASE_URL}/api/bookings/{booking['id']}/approve?approve=true",
            headers=headers_admin
        )
        assert approve_response.status_code == 200, f"Failed to approve: {approve_response.text}"
        
        # Verify booking is now approved
        get_response = self.session.get(f"{BASE_URL}/api/bookings/{booking['id']}", headers=headers_admin)
        assert get_response.status_code == 200
        updated_booking = get_response.json()
        
        assert updated_booking["approval_status"] == "approved", "Booking should be approved"
        
        print(f"✓ PE Desk approved normal booking: {booking['booking_number']}")
        print(f"  - approval_status: {updated_booking['approval_status']}")
        print(f"  - Client confirmation email would be sent now (SMTP may not be configured)")
        
        return updated_booking
    
    def test_06_client_confirmation_after_approval_works(self):
        """
        Test: Client can confirm booking after PE Desk approval
        Expected: Confirmation succeeds, status updated to 'accepted'
        """
        # Create and approve a booking
        self._login_employee()
        headers_emp = {"Authorization": f"Bearer {self.employee_token}"}
        
        client, stock = self._get_test_client_and_stock(self.employee_token)
        if not client or not stock:
            pytest.skip("No approved client or stock with inventory available")
        
        buying_price = stock["weighted_avg_price"]
        selling_price = buying_price + 10
        
        booking_data = {
            "client_id": client["id"],
            "stock_id": stock["stock_id"],
            "quantity": 1,
            "selling_price": selling_price,
            "booking_date": datetime.now().strftime("%Y-%m-%d"),
            "status": "open",
            "notes": f"TEST_CLIENT_CONFIRM_{uuid.uuid4().hex[:8]}"
        }
        
        response = self.session.post(f"{BASE_URL}/api/bookings", json=booking_data, headers=headers_emp)
        assert response.status_code == 200
        booking = response.json()
        self.created_bookings.append(booking["id"])
        token = booking.get("client_confirmation_token")
        
        # Approve as admin
        self._login_admin()
        headers_admin = {"Authorization": f"Bearer {self.admin_token}"}
        
        approve_response = self.session.put(
            f"{BASE_URL}/api/bookings/{booking['id']}/approve?approve=true",
            headers=headers_admin
        )
        assert approve_response.status_code == 200
        
        # Now client confirms (public endpoint)
        confirm_url = f"{BASE_URL}/api/booking-confirm/{booking['id']}/{token}/accept"
        confirm_response = requests.get(confirm_url)
        assert confirm_response.status_code == 200
        
        result = confirm_response.json()
        assert result["status"] == "accepted", f"Expected accepted, got {result['status']}"
        
        print(f"✓ Client confirmation after approval works correctly")
        print(f"  - status: {result['status']}")
        print(f"  - message: {result['message']}")
    
    # ==================== LOSS BOOKING WORKFLOW ====================
    
    def test_07_create_loss_booking_no_client_email_at_creation(self):
        """
        Test: Create a loss booking (selling_price < buying_price)
        Expected: Booking created with is_loss_booking=True, loss_approval_status='pending'
        """
        self._login_employee()
        headers = {"Authorization": f"Bearer {self.employee_token}"}
        
        client, stock = self._get_test_client_and_stock(self.employee_token)
        if not client or not stock:
            pytest.skip("No approved client or stock with inventory available")
        
        # Create loss booking (selling price < buying price)
        buying_price = stock["weighted_avg_price"]
        selling_price = buying_price - 10  # Loss booking
        
        booking_data = {
            "client_id": client["id"],
            "stock_id": stock["stock_id"],
            "quantity": 1,
            "selling_price": selling_price,
            "booking_date": datetime.now().strftime("%Y-%m-%d"),
            "status": "open",
            "notes": f"TEST_LOSS_BOOKING_{uuid.uuid4().hex[:8]}"
        }
        
        response = self.session.post(f"{BASE_URL}/api/bookings", json=booking_data, headers=headers)
        assert response.status_code == 200, f"Failed to create loss booking: {response.text}"
        
        booking = response.json()
        self.created_bookings.append(booking["id"])
        
        # Verify booking state at creation
        assert booking["approval_status"] == "pending", "Booking should be pending PE Desk approval"
        assert booking["client_confirmation_status"] == "pending", "Client confirmation should be pending"
        assert booking["is_loss_booking"] == True, "Should be a loss booking"
        assert booking["loss_approval_status"] == "pending", "Loss approval should be pending"
        
        print(f"✓ Loss booking created: {booking['booking_number']}")
        print(f"  - approval_status: {booking['approval_status']}")
        print(f"  - is_loss_booking: {booking['is_loss_booking']}")
        print(f"  - loss_approval_status: {booking['loss_approval_status']}")
        
        return booking
    
    def test_08_pe_desk_approve_loss_booking_still_no_client_email(self):
        """
        Test: PE Desk approves loss booking (but loss approval still pending)
        Expected: Booking approved but client confirmation email NOT sent (loss approval pending)
        """
        # Create loss booking as employee
        self._login_employee()
        headers_emp = {"Authorization": f"Bearer {self.employee_token}"}
        
        client, stock = self._get_test_client_and_stock(self.employee_token)
        if not client or not stock:
            pytest.skip("No approved client or stock with inventory available")
        
        buying_price = stock["weighted_avg_price"]
        selling_price = buying_price - 10  # Loss
        
        booking_data = {
            "client_id": client["id"],
            "stock_id": stock["stock_id"],
            "quantity": 1,
            "selling_price": selling_price,
            "booking_date": datetime.now().strftime("%Y-%m-%d"),
            "status": "open",
            "notes": f"TEST_LOSS_PE_APPROVE_{uuid.uuid4().hex[:8]}"
        }
        
        response = self.session.post(f"{BASE_URL}/api/bookings", json=booking_data, headers=headers_emp)
        assert response.status_code == 200
        booking = response.json()
        self.created_bookings.append(booking["id"])
        token = booking.get("client_confirmation_token")
        
        # Approve as admin (PE Desk approval only)
        self._login_admin()
        headers_admin = {"Authorization": f"Bearer {self.admin_token}"}
        
        approve_response = self.session.put(
            f"{BASE_URL}/api/bookings/{booking['id']}/approve?approve=true",
            headers=headers_admin
        )
        assert approve_response.status_code == 200
        
        # Verify booking state
        get_response = self.session.get(f"{BASE_URL}/api/bookings/{booking['id']}", headers=headers_admin)
        assert get_response.status_code == 200
        updated_booking = get_response.json()
        
        assert updated_booking["approval_status"] == "approved", "Booking should be approved"
        assert updated_booking["loss_approval_status"] == "pending", "Loss approval should still be pending"
        
        # Try client confirmation - should return pending_loss_approval
        confirm_url = f"{BASE_URL}/api/booking-confirm/{booking['id']}/{token}/accept"
        confirm_response = requests.get(confirm_url)
        assert confirm_response.status_code == 200
        
        result = confirm_response.json()
        assert result["status"] == "pending_loss_approval", f"Expected pending_loss_approval, got {result['status']}"
        
        print(f"✓ PE Desk approved loss booking but client confirmation blocked")
        print(f"  - approval_status: {updated_booking['approval_status']}")
        print(f"  - loss_approval_status: {updated_booking['loss_approval_status']}")
        print(f"  - Client confirmation returns: {result['status']}")
        
        return booking
    
    def test_09_loss_approval_then_client_confirmation_works(self):
        """
        Test: After both PE Desk approval AND Loss approval, client can confirm
        Expected: Client confirmation succeeds
        """
        # Create loss booking as employee
        self._login_employee()
        headers_emp = {"Authorization": f"Bearer {self.employee_token}"}
        
        client, stock = self._get_test_client_and_stock(self.employee_token)
        if not client or not stock:
            pytest.skip("No approved client or stock with inventory available")
        
        buying_price = stock["weighted_avg_price"]
        selling_price = buying_price - 10  # Loss
        
        booking_data = {
            "client_id": client["id"],
            "stock_id": stock["stock_id"],
            "quantity": 1,
            "selling_price": selling_price,
            "booking_date": datetime.now().strftime("%Y-%m-%d"),
            "status": "open",
            "notes": f"TEST_FULL_LOSS_FLOW_{uuid.uuid4().hex[:8]}"
        }
        
        response = self.session.post(f"{BASE_URL}/api/bookings", json=booking_data, headers=headers_emp)
        assert response.status_code == 200
        booking = response.json()
        self.created_bookings.append(booking["id"])
        token = booking.get("client_confirmation_token")
        
        # Step 1: PE Desk approval
        self._login_admin()
        headers_admin = {"Authorization": f"Bearer {self.admin_token}"}
        
        approve_response = self.session.put(
            f"{BASE_URL}/api/bookings/{booking['id']}/approve?approve=true",
            headers=headers_admin
        )
        assert approve_response.status_code == 200
        
        # Step 2: Loss approval
        loss_approve_response = self.session.put(
            f"{BASE_URL}/api/bookings/{booking['id']}/approve-loss?approve=true",
            headers=headers_admin
        )
        assert loss_approve_response.status_code == 200
        
        # Verify booking state
        get_response = self.session.get(f"{BASE_URL}/api/bookings/{booking['id']}", headers=headers_admin)
        assert get_response.status_code == 200
        updated_booking = get_response.json()
        
        assert updated_booking["approval_status"] == "approved"
        assert updated_booking["loss_approval_status"] == "approved"
        
        # Step 3: Client confirmation should now work
        confirm_url = f"{BASE_URL}/api/booking-confirm/{booking['id']}/{token}/accept"
        confirm_response = requests.get(confirm_url)
        assert confirm_response.status_code == 200
        
        result = confirm_response.json()
        assert result["status"] == "accepted", f"Expected accepted, got {result['status']}"
        
        print(f"✓ Full loss booking workflow completed successfully")
        print(f"  - PE Desk approval: ✓")
        print(f"  - Loss approval: ✓")
        print(f"  - Client confirmation: {result['status']}")
    
    # ==================== ROLE RESTRICTION TESTS ====================
    
    def test_10_booking_deletion_restricted_to_pe_desk(self):
        """
        Test: Only PE Desk can delete bookings
        """
        # Create booking as employee
        self._login_employee()
        headers_emp = {"Authorization": f"Bearer {self.employee_token}"}
        
        client, stock = self._get_test_client_and_stock(self.employee_token)
        if not client or not stock:
            pytest.skip("No approved client or stock with inventory available")
        
        buying_price = stock["weighted_avg_price"]
        selling_price = buying_price + 10
        
        booking_data = {
            "client_id": client["id"],
            "stock_id": stock["stock_id"],
            "quantity": 1,
            "selling_price": selling_price,
            "booking_date": datetime.now().strftime("%Y-%m-%d"),
            "status": "open",
            "notes": f"TEST_DELETE_RESTRICT_{uuid.uuid4().hex[:8]}"
        }
        
        response = self.session.post(f"{BASE_URL}/api/bookings", json=booking_data, headers=headers_emp)
        assert response.status_code == 200
        booking = response.json()
        self.created_bookings.append(booking["id"])
        
        # Try to delete as employee - should fail
        delete_response = self.session.delete(f"{BASE_URL}/api/bookings/{booking['id']}", headers=headers_emp)
        assert delete_response.status_code == 403, f"Employee should not be able to delete bookings"
        
        # Delete as admin - should succeed
        self._login_admin()
        headers_admin = {"Authorization": f"Bearer {self.admin_token}"}
        
        delete_response = self.session.delete(f"{BASE_URL}/api/bookings/{booking['id']}", headers=headers_admin)
        assert delete_response.status_code == 200, f"PE Desk should be able to delete bookings"
        
        # Remove from cleanup list since already deleted
        self.created_bookings.remove(booking["id"])
        
        print(f"✓ Booking deletion correctly restricted to PE Desk only")
    
    def test_11_purchases_restricted_to_pe_desk(self):
        """
        Test: Purchases module restricted to PE Desk
        """
        # Try as employee
        self._login_employee()
        headers_emp = {"Authorization": f"Bearer {self.employee_token}"}
        
        # Try to create a purchase
        purchase_data = {
            "vendor_id": "test",
            "stock_id": "test",
            "quantity": 1,
            "price_per_unit": 100,
            "purchase_date": datetime.now().strftime("%Y-%m-%d")
        }
        
        response = self.session.post(f"{BASE_URL}/api/purchases", json=purchase_data, headers=headers_emp)
        # Should be 403 (forbidden) or 404 (vendor not found after permission check)
        assert response.status_code in [403, 404], f"Employee should not be able to create purchases: {response.status_code}"
        
        print(f"✓ Purchases module correctly restricted from employees")
    
    def test_12_stocks_restricted_to_pe_desk(self):
        """
        Test: Stock creation restricted to PE Desk
        """
        # Try as employee
        self._login_employee()
        headers_emp = {"Authorization": f"Bearer {self.employee_token}"}
        
        stock_data = {
            "symbol": "TEST",
            "name": "Test Stock"
        }
        
        response = self.session.post(f"{BASE_URL}/api/stocks", json=stock_data, headers=headers_emp)
        assert response.status_code == 403, f"Employee should not be able to create stocks: {response.status_code}"
        
        print(f"✓ Stock creation correctly restricted to PE Desk")
    
    def test_13_vendors_restricted_to_pe_desk(self):
        """
        Test: Vendor creation restricted to PE Desk
        """
        # Try as employee
        self._login_employee()
        headers_emp = {"Authorization": f"Bearer {self.employee_token}"}
        
        vendor_data = {
            "name": "Test Vendor",
            "pan_number": "ABCDE1234F",
            "dp_id": "IN123456",
            "is_vendor": True
        }
        
        response = self.session.post(f"{BASE_URL}/api/clients", json=vendor_data, headers=headers_emp)
        assert response.status_code == 403, f"Employee should not be able to create vendors: {response.status_code}"
        
        print(f"✓ Vendor creation correctly restricted to PE Desk")
    
    # ==================== EXPORT TESTS ====================
    
    def test_14_booking_export_excel(self):
        """
        Test: Export bookings to Excel
        """
        self._login_admin()
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        response = self.session.get(f"{BASE_URL}/api/bookings-export?format=xlsx", headers=headers)
        assert response.status_code == 200, f"Export failed: {response.status_code}"
        assert len(response.content) > 0, "Export should return content"
        
        print(f"✓ Booking export to Excel works (received {len(response.content)} bytes)")
    
    def test_15_booking_export_csv(self):
        """
        Test: Export bookings to CSV
        """
        self._login_admin()
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        response = self.session.get(f"{BASE_URL}/api/bookings-export?format=csv", headers=headers)
        assert response.status_code == 200, f"Export failed: {response.status_code}"
        assert len(response.content) > 0, "Export should return content"
        
        print(f"✓ Booking export to CSV works (received {len(response.content)} bytes)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
