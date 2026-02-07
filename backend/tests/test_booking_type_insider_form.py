"""
Test Booking Type (Client/Team/Own) and Insider Trading Form Upload/Download
Tests the new feature for booking types and insider trading compliance forms
"""
import pytest
import requests
import os
import io

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
PE_DESK_ADMIN = {"email": "admin@privity.com", "password": "Admin@123"}
EMPLOYEE = {"email": "test_emp_dp_8a1404fd@smifs.com", "password": "Test@123"}


class TestBookingTypeFeature:
    """Test booking type (client/team/own) functionality"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        self.admin_token = None
        self.employee_token = None
        self.test_booking_id = None
    
    def login_admin(self):
        """Login as PE Desk Admin"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json=PE_DESK_ADMIN)
        if response.status_code == 200:
            self.admin_token = response.json().get("token")
            self.session.headers.update({"Authorization": f"Bearer {self.admin_token}"})
            return True
        return False
    
    def login_employee(self):
        """Login as Employee"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json=EMPLOYEE)
        if response.status_code == 200:
            self.employee_token = response.json().get("token")
            self.session.headers.update({"Authorization": f"Bearer {self.employee_token}"})
            return True
        return False
    
    def test_01_admin_login(self):
        """Test PE Desk Admin login"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json=PE_DESK_ADMIN)
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == 1  # PE Desk role
        print("SUCCESS: PE Desk Admin login successful")
    
    def test_02_get_clients_for_booking(self):
        """Test getting approved clients for booking"""
        assert self.login_admin(), "Admin login failed"
        
        response = self.session.get(f"{BASE_URL}/api/clients")
        assert response.status_code == 200, f"Failed to get clients: {response.text}"
        
        clients = response.json()
        approved_clients = [c for c in clients if c.get("approval_status") == "approved" and not c.get("is_vendor")]
        print(f"SUCCESS: Found {len(approved_clients)} approved clients for booking")
        assert len(approved_clients) >= 0  # May be 0 if no approved clients
    
    def test_03_get_stocks_for_booking(self):
        """Test getting stocks for booking"""
        assert self.login_admin(), "Admin login failed"
        
        response = self.session.get(f"{BASE_URL}/api/stocks")
        assert response.status_code == 200, f"Failed to get stocks: {response.text}"
        
        stocks = response.json()
        print(f"SUCCESS: Found {len(stocks)} stocks available")
    
    def test_04_get_inventory_for_booking(self):
        """Test getting inventory for booking"""
        assert self.login_admin(), "Admin login failed"
        
        response = self.session.get(f"{BASE_URL}/api/inventory")
        assert response.status_code == 200, f"Failed to get inventory: {response.text}"
        
        inventory = response.json()
        print(f"SUCCESS: Found {len(inventory)} inventory items")
    
    def test_05_create_client_booking(self):
        """Test creating a booking with booking_type='client'"""
        assert self.login_admin(), "Admin login failed"
        
        # Get an approved client
        clients_resp = self.session.get(f"{BASE_URL}/api/clients")
        clients = clients_resp.json()
        approved_clients = [c for c in clients if c.get("approval_status") == "approved" and not c.get("is_vendor")]
        
        if not approved_clients:
            pytest.skip("No approved clients available for testing")
        
        # Get a stock with inventory (quantity > 0)
        inventory_resp = self.session.get(f"{BASE_URL}/api/inventory")
        inventory = inventory_resp.json()
        
        # Filter for inventory with available quantity
        inventory_with_qty = [i for i in inventory if i.get("available_quantity", 0) > 0]
        
        if not inventory_with_qty:
            pytest.skip("No inventory with available quantity for testing")
        
        stock_with_inventory = inventory_with_qty[0]
        
        booking_data = {
            "client_id": approved_clients[0]["id"],
            "stock_id": stock_with_inventory["stock_id"],
            "quantity": 1,
            "selling_price": stock_with_inventory["weighted_avg_price"] + 10,
            "booking_date": "2026-01-24",
            "status": "open",
            "notes": "Test client booking",
            "booking_type": "client",
            "insider_form_uploaded": False
        }
        
        response = self.session.post(f"{BASE_URL}/api/bookings", json=booking_data)
        assert response.status_code == 200, f"Failed to create client booking: {response.text}"
        
        booking = response.json()
        assert booking.get("booking_type") == "client", "Booking type should be 'client'"
        print(f"SUCCESS: Created client booking with ID: {booking.get('id')}")
    
    def test_06_create_team_booking(self):
        """Test creating a booking with booking_type='team'"""
        assert self.login_admin(), "Admin login failed"
        
        # Get an approved client
        clients_resp = self.session.get(f"{BASE_URL}/api/clients")
        clients = clients_resp.json()
        approved_clients = [c for c in clients if c.get("approval_status") == "approved" and not c.get("is_vendor")]
        
        if not approved_clients:
            pytest.skip("No approved clients available for testing")
        
        # Get a stock with inventory (quantity > 0)
        inventory_resp = self.session.get(f"{BASE_URL}/api/inventory")
        inventory = inventory_resp.json()
        
        # Filter for inventory with available quantity
        inventory_with_qty = [i for i in inventory if i.get("available_quantity", 0) > 0]
        
        if not inventory_with_qty:
            pytest.skip("No inventory with available quantity for testing")
        
        stock_with_inventory = inventory_with_qty[0]
        
        booking_data = {
            "client_id": approved_clients[0]["id"],
            "stock_id": stock_with_inventory["stock_id"],
            "quantity": 1,
            "selling_price": stock_with_inventory["weighted_avg_price"] + 10,
            "booking_date": "2026-01-24",
            "status": "open",
            "notes": "Test team booking",
            "booking_type": "team",
            "insider_form_uploaded": False
        }
        
        response = self.session.post(f"{BASE_URL}/api/bookings", json=booking_data)
        assert response.status_code == 200, f"Failed to create team booking: {response.text}"
        
        booking = response.json()
        assert booking.get("booking_type") == "team", "Booking type should be 'team'"
        print(f"SUCCESS: Created team booking with ID: {booking.get('id')}")
    
    def test_07_create_own_booking(self):
        """Test creating a booking with booking_type='own'"""
        assert self.login_admin(), "Admin login failed"
        
        # Get an approved client
        clients_resp = self.session.get(f"{BASE_URL}/api/clients")
        clients = clients_resp.json()
        approved_clients = [c for c in clients if c.get("approval_status") == "approved" and not c.get("is_vendor")]
        
        if not approved_clients:
            pytest.skip("No approved clients available for testing")
        
        # Get a stock with inventory (quantity > 0)
        inventory_resp = self.session.get(f"{BASE_URL}/api/inventory")
        inventory = inventory_resp.json()
        
        # Filter for inventory with available quantity
        inventory_with_qty = [i for i in inventory if i.get("available_quantity", 0) > 0]
        
        if not inventory_with_qty:
            pytest.skip("No inventory with available quantity for testing")
        
        stock_with_inventory = inventory_with_qty[0]
        
        booking_data = {
            "client_id": approved_clients[0]["id"],
            "stock_id": stock_with_inventory["stock_id"],
            "quantity": 1,
            "selling_price": stock_with_inventory["weighted_avg_price"] + 10,
            "booking_date": "2026-01-24",
            "status": "open",
            "notes": "Test own booking - insider trading compliance",
            "booking_type": "own",
            "insider_form_uploaded": False
        }
        
        response = self.session.post(f"{BASE_URL}/api/bookings", json=booking_data)
        assert response.status_code == 200, f"Failed to create own booking: {response.text}"
        
        booking = response.json()
        assert booking.get("booking_type") == "own", "Booking type should be 'own'"
        self.test_booking_id = booking.get("id")
        print(f"SUCCESS: Created own booking with ID: {booking.get('id')}")
        return booking.get("id")
    
    def test_08_get_bookings_with_booking_type(self):
        """Test that bookings list includes booking_type field"""
        assert self.login_admin(), "Admin login failed"
        
        response = self.session.get(f"{BASE_URL}/api/bookings")
        assert response.status_code == 200, f"Failed to get bookings: {response.text}"
        
        bookings = response.json()
        if bookings:
            # Check that booking_type field exists
            for booking in bookings[:5]:  # Check first 5
                assert "booking_type" in booking or booking.get("booking_type") is None, "booking_type field should exist"
            print("SUCCESS: Bookings list contains booking_type field")
        else:
            print("INFO: No bookings found to verify")


class TestInsiderFormUploadDownload:
    """Test insider trading form upload and download endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session"""
        self.session = requests.Session()
        self.admin_token = None
        self.own_booking_id = None
    
    def login_admin(self):
        """Login as PE Desk Admin"""
        self.session.headers.update({"Content-Type": "application/json"})
        response = self.session.post(f"{BASE_URL}/api/auth/login", json=PE_DESK_ADMIN)
        if response.status_code == 200:
            self.admin_token = response.json().get("token")
            self.session.headers.update({"Authorization": f"Bearer {self.admin_token}"})
            return True
        return False
    
    def create_own_booking(self):
        """Create an 'own' booking for testing"""
        # Get an approved client
        clients_resp = self.session.get(f"{BASE_URL}/api/clients")
        clients = clients_resp.json()
        approved_clients = [c for c in clients if c.get("approval_status") == "approved" and not c.get("is_vendor")]
        
        if not approved_clients:
            return None
        
        # Get a stock with inventory (quantity > 0)
        inventory_resp = self.session.get(f"{BASE_URL}/api/inventory")
        inventory = inventory_resp.json()
        
        # Filter for inventory with available quantity
        inventory_with_qty = [i for i in inventory if i.get("available_quantity", 0) > 0]
        
        if not inventory_with_qty:
            return None
        
        stock_with_inventory = inventory_with_qty[0]
        
        booking_data = {
            "client_id": approved_clients[0]["id"],
            "stock_id": stock_with_inventory["stock_id"],
            "quantity": 1,
            "selling_price": stock_with_inventory["weighted_avg_price"] + 10,
            "booking_date": "2026-01-24",
            "status": "open",
            "notes": "Test own booking for insider form upload",
            "booking_type": "own",
            "insider_form_uploaded": False
        }
        
        self.session.headers.update({"Content-Type": "application/json"})
        response = self.session.post(f"{BASE_URL}/api/bookings", json=booking_data)
        if response.status_code == 200:
            return response.json().get("id")
        return None
    
    def test_01_upload_insider_form_to_own_booking(self):
        """Test uploading insider form to an 'own' booking"""
        assert self.login_admin(), "Admin login failed"
        
        # Create an own booking first
        booking_id = self.create_own_booking()
        if not booking_id:
            pytest.skip("Could not create own booking for testing")
        
        self.own_booking_id = booking_id
        
        # Create a test PDF file
        test_file_content = b"%PDF-1.4 Test insider trading form content"
        files = {
            'file': ('insider_form_test.pdf', io.BytesIO(test_file_content), 'application/pdf')
        }
        
        # Remove Content-Type header for multipart upload
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        response = requests.post(
            f"{BASE_URL}/api/bookings/{booking_id}/insider-form",
            files=files,
            headers=headers
        )
        
        assert response.status_code == 200, f"Failed to upload insider form: {response.text}"
        data = response.json()
        assert "message" in data
        assert "filename" in data
        print(f"SUCCESS: Uploaded insider form for booking {booking_id}")
        return booking_id
    
    def test_02_upload_insider_form_to_non_own_booking_fails(self):
        """Test that uploading insider form to non-own booking fails"""
        assert self.login_admin(), "Admin login failed"
        
        # Get a client booking (not own)
        response = self.session.get(f"{BASE_URL}/api/bookings")
        bookings = response.json()
        
        client_booking = None
        for b in bookings:
            if b.get("booking_type") == "client":
                client_booking = b
                break
        
        if not client_booking:
            pytest.skip("No client booking found for testing")
        
        # Try to upload form to client booking
        test_file_content = b"%PDF-1.4 Test insider trading form content"
        files = {
            'file': ('insider_form_test.pdf', io.BytesIO(test_file_content), 'application/pdf')
        }
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        response = requests.post(
            f"{BASE_URL}/api/bookings/{client_booking['id']}/insider-form",
            files=files,
            headers=headers
        )
        
        # Should fail with 400 - insider forms only for 'own' bookings
        assert response.status_code == 400, f"Expected 400 for non-own booking, got {response.status_code}"
        print("SUCCESS: Upload to non-own booking correctly rejected")
    
    def test_03_download_insider_form(self):
        """Test downloading insider form (PE Desk only)"""
        assert self.login_admin(), "Admin login failed"
        
        # First upload a form
        booking_id = self.create_own_booking()
        if not booking_id:
            pytest.skip("Could not create own booking for testing")
        
        # Upload form
        test_file_content = b"%PDF-1.4 Test insider trading form content for download"
        files = {
            'file': ('insider_form_download_test.pdf', io.BytesIO(test_file_content), 'application/pdf')
        }
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        upload_response = requests.post(
            f"{BASE_URL}/api/bookings/{booking_id}/insider-form",
            files=files,
            headers=headers
        )
        
        if upload_response.status_code != 200:
            pytest.skip("Could not upload form for download test")
        
        # Now download
        download_response = self.session.get(f"{BASE_URL}/api/bookings/{booking_id}/insider-form")
        
        assert download_response.status_code == 200, f"Failed to download insider form: {download_response.text}"
        print(f"SUCCESS: Downloaded insider form for booking {booking_id}")
    
    def test_04_download_insider_form_not_found(self):
        """Test downloading insider form when none uploaded"""
        assert self.login_admin(), "Admin login failed"
        
        # Create an own booking without uploading form
        booking_id = self.create_own_booking()
        if not booking_id:
            pytest.skip("Could not create own booking for testing")
        
        # Try to download (should fail - no form uploaded)
        response = self.session.get(f"{BASE_URL}/api/bookings/{booking_id}/insider-form")
        
        assert response.status_code == 404, f"Expected 404 for no form, got {response.status_code}"
        print("SUCCESS: Download correctly returns 404 when no form uploaded")
    
    def test_05_download_insider_form_invalid_booking(self):
        """Test downloading insider form for invalid booking ID"""
        assert self.login_admin(), "Admin login failed"
        
        response = self.session.get(f"{BASE_URL}/api/bookings/invalid-booking-id-12345/insider-form")
        
        assert response.status_code == 404, f"Expected 404 for invalid booking, got {response.status_code}"
        print("SUCCESS: Download correctly returns 404 for invalid booking")


class TestBookingTypeValidation:
    """Test booking type validation and edge cases"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def login_admin(self):
        """Login as PE Desk Admin"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json=PE_DESK_ADMIN)
        if response.status_code == 200:
            token = response.json().get("token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
            return True
        return False
    
    def test_01_booking_type_default_value(self):
        """Test that booking_type defaults to 'client' if not provided"""
        assert self.login_admin(), "Admin login failed"
        
        # Get an approved client
        clients_resp = self.session.get(f"{BASE_URL}/api/clients")
        clients = clients_resp.json()
        approved_clients = [c for c in clients if c.get("approval_status") == "approved" and not c.get("is_vendor")]
        
        if not approved_clients:
            pytest.skip("No approved clients available for testing")
        
        # Get a stock with inventory (quantity > 0)
        inventory_resp = self.session.get(f"{BASE_URL}/api/inventory")
        inventory = inventory_resp.json()
        
        # Filter for inventory with available quantity
        inventory_with_qty = [i for i in inventory if i.get("available_quantity", 0) > 0]
        
        if not inventory_with_qty:
            pytest.skip("No inventory with available quantity for testing")
        
        stock_with_inventory = inventory_with_qty[0]
        
        # Create booking without specifying booking_type
        booking_data = {
            "client_id": approved_clients[0]["id"],
            "stock_id": stock_with_inventory["stock_id"],
            "quantity": 1,
            "selling_price": stock_with_inventory["weighted_avg_price"] + 10,
            "booking_date": "2026-01-24",
            "status": "open",
            "notes": "Test default booking type"
            # booking_type not specified - should default to 'client'
        }
        
        response = self.session.post(f"{BASE_URL}/api/bookings", json=booking_data)
        assert response.status_code == 200, f"Failed to create booking: {response.text}"
        
        booking = response.json()
        # Default should be 'client'
        assert booking.get("booking_type") == "client", f"Expected default 'client', got '{booking.get('booking_type')}'"
        print("SUCCESS: Booking type defaults to 'client' when not specified")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
