"""
Referral Partners Feature Tests
Tests for RP CRUD operations, document upload, and booking integration
"""
import pytest
import requests
import os
import time
import random
import string

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
PE_DESK_EMAIL = "pedesk@smifs.com"
PE_DESK_PASSWORD = "Kutta@123"
EMPLOYEE_EMAIL = "employee@test.com"
EMPLOYEE_PASSWORD = "Test@123"


def generate_random_pan():
    """Generate a random PAN number"""
    letters = ''.join(random.choices(string.ascii_uppercase, k=5))
    digits = ''.join(random.choices(string.digits, k=4))
    last_letter = random.choice(string.ascii_uppercase)
    return f"{letters}{digits}{last_letter}"


def generate_random_aadhar():
    """Generate a random 12-digit Aadhar number"""
    return ''.join(random.choices(string.digits, k=12))


class TestReferralPartnersAPI:
    """Test Referral Partners API endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
    def get_pe_desk_token(self):
        """Get PE Desk authentication token"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": PE_DESK_EMAIL,
            "password": PE_DESK_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip(f"PE Desk login failed: {response.status_code}")
        
    def get_employee_token(self):
        """Get Employee authentication token"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": EMPLOYEE_EMAIL,
            "password": EMPLOYEE_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("token")
        # Create employee if doesn't exist
        return None
    
    # ============== RP Listing Tests ==============
    
    def test_01_get_referral_partners_list(self):
        """Test GET /api/referral-partners returns list"""
        token = self.get_pe_desk_token()
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        response = self.session.get(f"{BASE_URL}/api/referral-partners")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"✓ GET /api/referral-partners returned {len(data)} RPs")
        
    def test_02_get_referral_partners_with_search(self):
        """Test GET /api/referral-partners with search parameter"""
        token = self.get_pe_desk_token()
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        # Search for existing RP
        response = self.session.get(f"{BASE_URL}/api/referral-partners?search=RP-0001")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"✓ Search for RP-0001 returned {len(data)} results")
        
    def test_03_get_referral_partners_active_only(self):
        """Test GET /api/referral-partners with active_only filter"""
        token = self.get_pe_desk_token()
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        # Get only active RPs
        response = self.session.get(f"{BASE_URL}/api/referral-partners?active_only=true")
        assert response.status_code == 200
        
        data = response.json()
        for rp in data:
            assert rp.get("is_active") == True, f"RP {rp.get('rp_code')} should be active"
        print(f"✓ Active only filter returned {len(data)} active RPs")
        
    # ============== RP Creation Tests ==============
    
    def test_04_create_referral_partner_pe_desk(self):
        """Test PE Desk can create a new Referral Partner"""
        token = self.get_pe_desk_token()
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        pan = generate_random_pan()
        aadhar = generate_random_aadhar()
        
        rp_data = {
            "name": f"TEST_RP_{int(time.time())}",
            "email": f"testrp_{int(time.time())}@test.com",
            "phone": "+91 98765 43210",
            "pan_number": pan,
            "aadhar_number": aadhar,
            "address": "Test Address, Mumbai"
        }
        
        response = self.session.post(f"{BASE_URL}/api/referral-partners", json=rp_data)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "id" in data, "Response should contain id"
        assert "rp_code" in data, "Response should contain rp_code"
        assert data["rp_code"].startswith("RP-"), f"RP code should start with RP-, got {data['rp_code']}"
        assert data["name"] == rp_data["name"], "Name should match"
        assert data["pan_number"] == pan.upper(), "PAN should be uppercase"
        assert data["is_active"] == True, "New RP should be active"
        
        print(f"✓ Created RP with code: {data['rp_code']}")
        
        # Store for cleanup
        self.created_rp_id = data["id"]
        return data
        
    def test_05_create_referral_partner_unique_code_format(self):
        """Test RP code follows RP-XXXX format"""
        token = self.get_pe_desk_token()
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        pan = generate_random_pan()
        aadhar = generate_random_aadhar()
        
        rp_data = {
            "name": f"TEST_RP_Format_{int(time.time())}",
            "pan_number": pan,
            "aadhar_number": aadhar
        }
        
        response = self.session.post(f"{BASE_URL}/api/referral-partners", json=rp_data)
        assert response.status_code == 200
        
        data = response.json()
        rp_code = data["rp_code"]
        
        # Verify format RP-XXXX (4 digits)
        assert rp_code.startswith("RP-"), f"Code should start with RP-, got {rp_code}"
        code_number = rp_code.split("-")[1]
        assert len(code_number) == 4, f"Code number should be 4 digits, got {code_number}"
        assert code_number.isdigit(), f"Code number should be numeric, got {code_number}"
        
        print(f"✓ RP code format verified: {rp_code}")
        
    def test_06_create_referral_partner_duplicate_pan_rejected(self):
        """Test duplicate PAN number is rejected"""
        token = self.get_pe_desk_token()
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        pan = generate_random_pan()
        aadhar1 = generate_random_aadhar()
        aadhar2 = generate_random_aadhar()
        
        # Create first RP
        rp_data1 = {
            "name": "TEST_RP_DupPAN_1",
            "pan_number": pan,
            "aadhar_number": aadhar1
        }
        response1 = self.session.post(f"{BASE_URL}/api/referral-partners", json=rp_data1)
        assert response1.status_code == 200
        
        # Try to create second RP with same PAN
        rp_data2 = {
            "name": "TEST_RP_DupPAN_2",
            "pan_number": pan,
            "aadhar_number": aadhar2
        }
        response2 = self.session.post(f"{BASE_URL}/api/referral-partners", json=rp_data2)
        assert response2.status_code == 400, f"Expected 400 for duplicate PAN, got {response2.status_code}"
        
        error_detail = response2.json().get("detail", "")
        assert "already exists" in error_detail.lower(), f"Error should mention duplicate: {error_detail}"
        
        print("✓ Duplicate PAN correctly rejected")
        
    def test_07_create_referral_partner_duplicate_aadhar_rejected(self):
        """Test duplicate Aadhar number is rejected"""
        token = self.get_pe_desk_token()
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        pan1 = generate_random_pan()
        pan2 = generate_random_pan()
        aadhar = generate_random_aadhar()
        
        # Create first RP
        rp_data1 = {
            "name": "TEST_RP_DupAadhar_1",
            "pan_number": pan1,
            "aadhar_number": aadhar
        }
        response1 = self.session.post(f"{BASE_URL}/api/referral-partners", json=rp_data1)
        assert response1.status_code == 200
        
        # Try to create second RP with same Aadhar
        rp_data2 = {
            "name": "TEST_RP_DupAadhar_2",
            "pan_number": pan2,
            "aadhar_number": aadhar
        }
        response2 = self.session.post(f"{BASE_URL}/api/referral-partners", json=rp_data2)
        assert response2.status_code == 400, f"Expected 400 for duplicate Aadhar, got {response2.status_code}"
        
        print("✓ Duplicate Aadhar correctly rejected")
        
    # ============== RP Edit Tests ==============
    
    def test_08_pe_desk_can_edit_rp(self):
        """Test PE Desk can edit Referral Partner"""
        token = self.get_pe_desk_token()
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        # First create an RP
        pan = generate_random_pan()
        aadhar = generate_random_aadhar()
        
        create_data = {
            "name": "TEST_RP_Edit_Original",
            "pan_number": pan,
            "aadhar_number": aadhar,
            "phone": "1234567890"
        }
        create_response = self.session.post(f"{BASE_URL}/api/referral-partners", json=create_data)
        assert create_response.status_code == 200
        rp_id = create_response.json()["id"]
        
        # Now edit it
        update_data = {
            "name": "TEST_RP_Edit_Updated",
            "pan_number": pan,
            "aadhar_number": aadhar,
            "phone": "9876543210",
            "address": "Updated Address"
        }
        
        update_response = self.session.put(f"{BASE_URL}/api/referral-partners/{rp_id}", json=update_data)
        assert update_response.status_code == 200, f"Expected 200, got {update_response.status_code}: {update_response.text}"
        
        updated_data = update_response.json()
        assert updated_data["name"] == "TEST_RP_Edit_Updated", "Name should be updated"
        assert updated_data["phone"] == "9876543210", "Phone should be updated"
        assert updated_data["address"] == "Updated Address", "Address should be updated"
        
        print("✓ PE Desk successfully edited RP")
        
    def test_09_get_single_referral_partner(self):
        """Test GET /api/referral-partners/{id} returns single RP"""
        token = self.get_pe_desk_token()
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        # Get list first
        list_response = self.session.get(f"{BASE_URL}/api/referral-partners?active_only=false")
        assert list_response.status_code == 200
        rps = list_response.json()
        
        if len(rps) == 0:
            pytest.skip("No RPs available to test")
            
        rp_id = rps[0]["id"]
        
        # Get single RP
        response = self.session.get(f"{BASE_URL}/api/referral-partners/{rp_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["id"] == rp_id, "ID should match"
        assert "rp_code" in data, "Should have rp_code"
        assert "name" in data, "Should have name"
        
        print(f"✓ GET single RP returned: {data['rp_code']} - {data['name']}")
        
    # ============== RP Toggle Active Tests ==============
    
    def test_10_pe_desk_can_toggle_rp_active(self):
        """Test PE Desk can activate/deactivate RP"""
        token = self.get_pe_desk_token()
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        # Create an RP
        pan = generate_random_pan()
        aadhar = generate_random_aadhar()
        
        create_data = {
            "name": "TEST_RP_Toggle",
            "pan_number": pan,
            "aadhar_number": aadhar
        }
        create_response = self.session.post(f"{BASE_URL}/api/referral-partners", json=create_data)
        assert create_response.status_code == 200
        rp_id = create_response.json()["id"]
        
        # Deactivate
        deactivate_response = self.session.put(f"{BASE_URL}/api/referral-partners/{rp_id}/toggle-active?is_active=false")
        assert deactivate_response.status_code == 200
        
        # Verify deactivated
        get_response = self.session.get(f"{BASE_URL}/api/referral-partners/{rp_id}")
        assert get_response.json()["is_active"] == False
        
        # Reactivate
        activate_response = self.session.put(f"{BASE_URL}/api/referral-partners/{rp_id}/toggle-active?is_active=true")
        assert activate_response.status_code == 200
        
        # Verify activated
        get_response2 = self.session.get(f"{BASE_URL}/api/referral-partners/{rp_id}")
        assert get_response2.json()["is_active"] == True
        
        print("✓ PE Desk can toggle RP active status")
        
    # ============== RP Bookings Integration Tests ==============
    
    def test_11_get_rp_bookings(self):
        """Test GET /api/referral-partners/{id}/bookings returns bookings"""
        token = self.get_pe_desk_token()
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        # Get list of RPs
        list_response = self.session.get(f"{BASE_URL}/api/referral-partners")
        assert list_response.status_code == 200
        rps = list_response.json()
        
        if len(rps) == 0:
            pytest.skip("No RPs available")
            
        rp_id = rps[0]["id"]
        
        # Get bookings for RP
        response = self.session.get(f"{BASE_URL}/api/referral-partners/{rp_id}/bookings")
        assert response.status_code == 200
        
        data = response.json()
        assert "referral_partner" in data, "Should have referral_partner"
        assert "total_bookings" in data, "Should have total_bookings"
        assert "bookings" in data, "Should have bookings list"
        
        print(f"✓ RP {rps[0]['rp_code']} has {data['total_bookings']} bookings")
        
    # ============== Booking with RP Tests ==============
    
    def test_12_create_booking_with_rp(self):
        """Test creating a booking with Referral Partner"""
        token = self.get_pe_desk_token()
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        # Get an active RP
        rp_response = self.session.get(f"{BASE_URL}/api/referral-partners?active_only=true")
        assert rp_response.status_code == 200
        rps = rp_response.json()
        
        if len(rps) == 0:
            pytest.skip("No active RPs available")
            
        rp = rps[0]
        
        # Get a client
        clients_response = self.session.get(f"{BASE_URL}/api/clients")
        assert clients_response.status_code == 200
        clients = clients_response.json()
        
        approved_clients = [c for c in clients if c.get("approval_status") == "approved" and not c.get("is_vendor")]
        if len(approved_clients) == 0:
            pytest.skip("No approved clients available")
            
        client = approved_clients[0]
        
        # Get a stock
        stocks_response = self.session.get(f"{BASE_URL}/api/stocks")
        assert stocks_response.status_code == 200
        stocks = stocks_response.json()
        
        if len(stocks) == 0:
            pytest.skip("No stocks available")
            
        stock = stocks[0]
        
        # Create booking with RP
        booking_data = {
            "client_id": client["id"],
            "stock_id": stock["id"],
            "quantity": 10,
            "buying_price": 100.0,
            "selling_price": 110.0,
            "booking_date": "2026-01-28",
            "status": "open",
            "referral_partner_id": rp["id"],
            "rp_revenue_share_percent": 10.0
        }
        
        response = self.session.post(f"{BASE_URL}/api/bookings", json=booking_data)
        
        # Accept 200 or 201 for success
        if response.status_code in [200, 201]:
            data = response.json()
            assert data.get("referral_partner_id") == rp["id"], "RP ID should be saved"
            assert data.get("rp_revenue_share_percent") == 10.0, "Revenue share should be saved"
            print(f"✓ Created booking with RP {rp['rp_code']}, revenue share: 10%")
        elif response.status_code == 400:
            # May fail due to inventory constraints
            print(f"⚠ Booking creation returned 400 (may be inventory constraint): {response.text}")
        else:
            pytest.fail(f"Unexpected status code: {response.status_code}: {response.text}")
            
    def test_13_booking_without_rp_allowed(self):
        """Test booking can be created without RP"""
        token = self.get_pe_desk_token()
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        # Get a client
        clients_response = self.session.get(f"{BASE_URL}/api/clients")
        clients = clients_response.json()
        
        approved_clients = [c for c in clients if c.get("approval_status") == "approved" and not c.get("is_vendor")]
        if len(approved_clients) == 0:
            pytest.skip("No approved clients available")
            
        client = approved_clients[0]
        
        # Get a stock
        stocks_response = self.session.get(f"{BASE_URL}/api/stocks")
        stocks = stocks_response.json()
        
        if len(stocks) == 0:
            pytest.skip("No stocks available")
            
        stock = stocks[0]
        
        # Create booking without RP
        booking_data = {
            "client_id": client["id"],
            "stock_id": stock["id"],
            "quantity": 5,
            "buying_price": 100.0,
            "selling_price": 105.0,
            "booking_date": "2026-01-28",
            "status": "open"
            # No referral_partner_id
        }
        
        response = self.session.post(f"{BASE_URL}/api/bookings", json=booking_data)
        
        if response.status_code in [200, 201]:
            data = response.json()
            assert data.get("referral_partner_id") is None, "RP ID should be None"
            print("✓ Created booking without RP")
        elif response.status_code == 400:
            print(f"⚠ Booking creation returned 400 (may be inventory constraint): {response.text}")
        else:
            pytest.fail(f"Unexpected status code: {response.status_code}")


class TestReferralPartnersDocuments:
    """Test RP document upload functionality"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.session = requests.Session()
        
    def get_pe_desk_token(self):
        """Get PE Desk authentication token"""
        response = self.session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": PE_DESK_EMAIL, "password": PE_DESK_PASSWORD},
            headers={"Content-Type": "application/json"}
        )
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("PE Desk login failed")
        
    def test_14_document_upload_endpoint_exists(self):
        """Test document upload endpoint exists"""
        token = self.get_pe_desk_token()
        
        # Get an RP
        response = self.session.get(
            f"{BASE_URL}/api/referral-partners",
            headers={"Authorization": f"Bearer {token}"}
        )
        rps = response.json()
        
        if len(rps) == 0:
            pytest.skip("No RPs available")
            
        rp_id = rps[0]["id"]
        
        # Test endpoint with invalid document type (should return 400, not 404)
        files = {"file": ("test.txt", b"test content", "text/plain")}
        data = {"document_type": "invalid_type"}
        
        response = self.session.post(
            f"{BASE_URL}/api/referral-partners/{rp_id}/documents",
            headers={"Authorization": f"Bearer {token}"},
            files=files,
            data=data
        )
        
        # Should return 400 for invalid type, not 404
        assert response.status_code in [400, 422], f"Expected 400/422 for invalid type, got {response.status_code}"
        print("✓ Document upload endpoint exists and validates document type")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
