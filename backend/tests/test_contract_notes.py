"""
Contract Notes API Tests
Tests for contract note generation, download, preview, and email functionality
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
PE_DESK_EMAIL = "pedesk@smifs.com"
PE_DESK_PASSWORD = "Kutta@123"


class TestContractNotesAuth:
    """Authentication and access control tests"""
    
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
        self.token = response.json()["token"]
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
    
    def test_01_pe_desk_can_access_contract_notes(self):
        """PE Desk (role 1) can access contract notes list"""
        response = self.session.get(f"{BASE_URL}/api/contract-notes")
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "notes" in data
        assert isinstance(data["notes"], list)
        print(f"✓ PE Desk can access contract notes - Total: {data['total']}")
    
    def test_02_unauthenticated_access_denied(self):
        """Unauthenticated requests are denied"""
        session = requests.Session()
        response = session.get(f"{BASE_URL}/api/contract-notes")
        assert response.status_code in [401, 403]  # Either unauthorized or forbidden
        print("✓ Unauthenticated access denied")


class TestContractNotesList:
    """Tests for GET /api/contract-notes endpoint"""
    
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
        assert response.status_code == 200
        self.token = response.json()["token"]
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
    
    def test_01_list_contract_notes_with_pagination(self):
        """List contract notes with pagination"""
        response = self.session.get(f"{BASE_URL}/api/contract-notes?limit=10&skip=0")
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "notes" in data
        assert "limit" in data
        assert "skip" in data
        assert data["limit"] == 10
        assert data["skip"] == 0
        print(f"✓ Contract notes list with pagination - Total: {data['total']}")
    
    def test_02_list_contract_notes_with_status_filter(self):
        """List contract notes with status filter"""
        response = self.session.get(f"{BASE_URL}/api/contract-notes?status=generated")
        assert response.status_code == 200
        data = response.json()
        # All returned notes should have status=generated
        for note in data["notes"]:
            assert note["status"] == "generated"
        print(f"✓ Contract notes filtered by status - Count: {len(data['notes'])}")
    
    def test_03_contract_notes_enriched_with_client_stock(self):
        """Contract notes are enriched with client and stock names"""
        response = self.session.get(f"{BASE_URL}/api/contract-notes")
        assert response.status_code == 200
        data = response.json()
        if data["notes"]:
            note = data["notes"][0]
            assert "client_name" in note
            assert "stock_symbol" in note
            print(f"✓ Contract note enriched - Client: {note['client_name']}, Stock: {note['stock_symbol']}")
        else:
            print("✓ No contract notes to verify enrichment")


class TestContractNoteDetail:
    """Tests for GET /api/contract-notes/{note_id} endpoint"""
    
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
        assert response.status_code == 200
        self.token = response.json()["token"]
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
    
    def test_01_get_single_contract_note(self):
        """Get single contract note by ID"""
        # First get list to find a note ID
        list_response = self.session.get(f"{BASE_URL}/api/contract-notes")
        assert list_response.status_code == 200
        notes = list_response.json()["notes"]
        
        if notes:
            note_id = notes[0]["id"]
            response = self.session.get(f"{BASE_URL}/api/contract-notes/{note_id}")
            assert response.status_code == 200
            note = response.json()
            assert note["id"] == note_id
            assert "contract_note_number" in note
            assert "booking_id" in note
            assert "client_name" in note
            assert "stock_symbol" in note
            print(f"✓ Got contract note: {note['contract_note_number']}")
        else:
            pytest.skip("No contract notes available for testing")
    
    def test_02_get_nonexistent_contract_note(self):
        """Get non-existent contract note returns 404"""
        response = self.session.get(f"{BASE_URL}/api/contract-notes/nonexistent-id")
        assert response.status_code == 404
        print("✓ Non-existent contract note returns 404")


class TestContractNoteGeneration:
    """Tests for POST /api/contract-notes/generate/{booking_id} endpoint"""
    
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
        assert response.status_code == 200
        self.token = response.json()["token"]
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
    
    def test_01_generate_contract_note_requires_dp_transfer(self):
        """Cannot generate contract note without DP transfer"""
        # Find a booking without DP transfer
        bookings_response = self.session.get(f"{BASE_URL}/api/bookings")
        assert bookings_response.status_code == 200
        bookings = bookings_response.json()
        
        # Find booking without stock_transferred
        booking_without_dp = None
        for booking in bookings:
            if not booking.get("stock_transferred"):
                booking_without_dp = booking
                break
        
        if booking_without_dp:
            response = self.session.post(f"{BASE_URL}/api/contract-notes/generate/{booking_without_dp['id']}")
            assert response.status_code == 400
            assert "DP transfer not complete" in response.json()["detail"]
            print(f"✓ Cannot generate CN without DP transfer - Booking: {booking_without_dp['booking_number']}")
        else:
            pytest.skip("No booking without DP transfer available")
    
    def test_02_generate_contract_note_duplicate_rejected(self):
        """Cannot generate duplicate contract note for same booking"""
        # Find a booking that already has a contract note
        cn_response = self.session.get(f"{BASE_URL}/api/contract-notes")
        assert cn_response.status_code == 200
        notes = cn_response.json()["notes"]
        
        if notes:
            booking_id = notes[0]["booking_id"]
            response = self.session.post(f"{BASE_URL}/api/contract-notes/generate/{booking_id}")
            assert response.status_code == 400
            assert "already exists" in response.json()["detail"]
            print(f"✓ Duplicate contract note rejected - Booking: {notes[0]['booking_number']}")
        else:
            pytest.skip("No existing contract notes to test duplicate rejection")
    
    def test_03_generate_contract_note_nonexistent_booking(self):
        """Cannot generate contract note for non-existent booking"""
        response = self.session.post(f"{BASE_URL}/api/contract-notes/generate/nonexistent-booking-id")
        assert response.status_code == 404
        assert "Booking not found" in response.json()["detail"]
        print("✓ Non-existent booking returns 404")


class TestContractNoteDownload:
    """Tests for GET /api/contract-notes/download/{note_id} endpoint"""
    
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
        assert response.status_code == 200
        self.token = response.json()["token"]
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
    
    def test_01_download_contract_note_pdf(self):
        """Download contract note PDF"""
        # Get a contract note
        list_response = self.session.get(f"{BASE_URL}/api/contract-notes")
        assert list_response.status_code == 200
        notes = list_response.json()["notes"]
        
        if notes:
            note_id = notes[0]["id"]
            response = self.session.get(f"{BASE_URL}/api/contract-notes/download/{note_id}")
            assert response.status_code == 200
            assert response.headers.get("content-type") == "application/pdf"
            assert len(response.content) > 0
            print(f"✓ Downloaded PDF - Size: {len(response.content)} bytes")
        else:
            pytest.skip("No contract notes available for download test")
    
    def test_02_download_nonexistent_contract_note(self):
        """Download non-existent contract note returns 404"""
        response = self.session.get(f"{BASE_URL}/api/contract-notes/download/nonexistent-id")
        assert response.status_code == 404
        print("✓ Non-existent contract note download returns 404")


class TestContractNotePreview:
    """Tests for POST /api/contract-notes/preview/{booking_id} endpoint"""
    
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
        assert response.status_code == 200
        self.token = response.json()["token"]
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
    
    def test_01_preview_contract_note_pdf(self):
        """Preview contract note PDF without saving"""
        # Find a booking with DP transfer complete
        bookings_response = self.session.get(f"{BASE_URL}/api/bookings")
        assert bookings_response.status_code == 200
        bookings = bookings_response.json()
        
        booking_with_dp = None
        for booking in bookings:
            if booking.get("stock_transferred"):
                booking_with_dp = booking
                break
        
        if booking_with_dp:
            response = self.session.post(f"{BASE_URL}/api/contract-notes/preview/{booking_with_dp['id']}")
            assert response.status_code == 200
            assert response.headers.get("content-type") == "application/pdf"
            assert len(response.content) > 0
            print(f"✓ Preview PDF generated - Size: {len(response.content)} bytes")
        else:
            pytest.skip("No booking with DP transfer available for preview")
    
    def test_02_preview_nonexistent_booking(self):
        """Preview non-existent booking returns 404"""
        response = self.session.post(f"{BASE_URL}/api/contract-notes/preview/nonexistent-booking-id")
        assert response.status_code == 404
        print("✓ Non-existent booking preview returns 404")


class TestContractNoteByBooking:
    """Tests for GET /api/contract-notes/by-booking/{booking_id} endpoint"""
    
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
        assert response.status_code == 200
        self.token = response.json()["token"]
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
    
    def test_01_get_contract_note_by_booking_exists(self):
        """Get contract note by booking ID when it exists"""
        # Get a contract note to find its booking_id
        list_response = self.session.get(f"{BASE_URL}/api/contract-notes")
        assert list_response.status_code == 200
        notes = list_response.json()["notes"]
        
        if notes:
            booking_id = notes[0]["booking_id"]
            response = self.session.get(f"{BASE_URL}/api/contract-notes/by-booking/{booking_id}")
            assert response.status_code == 200
            data = response.json()
            assert data["exists"] == True
            assert data["note"] is not None
            assert data["note"]["booking_id"] == booking_id
            print(f"✓ Found contract note for booking: {data['note']['booking_number']}")
        else:
            pytest.skip("No contract notes available")
    
    def test_02_get_contract_note_by_booking_not_exists(self):
        """Get contract note by booking ID when it doesn't exist"""
        # Find a booking without contract note
        bookings_response = self.session.get(f"{BASE_URL}/api/bookings")
        assert bookings_response.status_code == 200
        bookings = bookings_response.json()
        
        # Get existing contract note booking IDs
        cn_response = self.session.get(f"{BASE_URL}/api/contract-notes")
        cn_booking_ids = [n["booking_id"] for n in cn_response.json()["notes"]]
        
        booking_without_cn = None
        for booking in bookings:
            if booking["id"] not in cn_booking_ids:
                booking_without_cn = booking
                break
        
        if booking_without_cn:
            response = self.session.get(f"{BASE_URL}/api/contract-notes/by-booking/{booking_without_cn['id']}")
            assert response.status_code == 200
            data = response.json()
            assert data["exists"] == False
            assert data["note"] is None
            print(f"✓ No contract note for booking: {booking_without_cn['booking_number']}")
        else:
            pytest.skip("All bookings have contract notes")


class TestContractNoteCompanyMasterIntegration:
    """Tests for Company Master integration in contract notes"""
    
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
        assert response.status_code == 200
        self.token = response.json()["token"]
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
    
    def test_01_company_master_data_exists(self):
        """Verify Company Master data is populated"""
        response = self.session.get(f"{BASE_URL}/api/company-master")
        assert response.status_code == 200
        data = response.json()
        
        # Verify key fields exist
        assert data.get("company_name"), "Company name should be set"
        assert data.get("company_address"), "Company address should be set"
        assert data.get("company_pan"), "Company PAN should be set"
        
        print(f"✓ Company Master populated - Name: {data['company_name']}")
        print(f"  Address: {data['company_address']}")
        print(f"  PAN: {data['company_pan']}")
        print(f"  Bank: {data.get('company_bank_name', 'N/A')}")


class TestContractNoteDataValidation:
    """Tests for contract note data validation"""
    
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
        assert response.status_code == 200
        self.token = response.json()["token"]
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
    
    def test_01_contract_note_has_required_fields(self):
        """Contract note has all required fields"""
        list_response = self.session.get(f"{BASE_URL}/api/contract-notes")
        assert list_response.status_code == 200
        notes = list_response.json()["notes"]
        
        if notes:
            note = notes[0]
            required_fields = [
                "id", "contract_note_number", "booking_id", "booking_number",
                "client_id", "quantity", "rate", "gross_amount", "net_amount",
                "status", "email_sent", "created_by", "created_by_name", "created_at"
            ]
            
            for field in required_fields:
                assert field in note, f"Missing required field: {field}"
            
            print(f"✓ Contract note has all required fields")
            print(f"  CN Number: {note['contract_note_number']}")
            print(f"  Booking: {note['booking_number']}")
            print(f"  Amount: ₹{note['net_amount']}")
        else:
            pytest.skip("No contract notes available")
    
    def test_02_contract_note_number_format(self):
        """Contract note number follows expected format"""
        list_response = self.session.get(f"{BASE_URL}/api/contract-notes")
        assert list_response.status_code == 200
        notes = list_response.json()["notes"]
        
        if notes:
            cn_number = notes[0]["contract_note_number"]
            # Expected format: SMIFS/CN/YY-YY/XXXX
            assert cn_number.startswith("SMIFS/CN/"), f"Invalid CN number format: {cn_number}"
            parts = cn_number.split("/")
            assert len(parts) == 4, f"CN number should have 4 parts: {cn_number}"
            print(f"✓ Contract note number format valid: {cn_number}")
        else:
            pytest.skip("No contract notes available")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
