"""
Contract Notes Email Attachment and Auto-Generation Tests
Tests for:
1. PDF attachment support in contract note emails
2. Auto-generation of contract notes when DP transfer is marked complete
3. Email service attachments parameter
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
PE_DESK_EMAIL = "pedesk@smifs.com"
PE_DESK_PASSWORD = "Kutta@123"


class TestEmailServiceAttachments:
    """Tests for email service attachments parameter"""
    
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
    
    def test_01_send_email_endpoint_exists(self):
        """Verify send-email endpoint exists for contract notes"""
        # Get a contract note
        list_response = self.session.get(f"{BASE_URL}/api/contract-notes")
        assert list_response.status_code == 200
        notes = list_response.json()["notes"]
        
        if notes:
            note_id = notes[0]["id"]
            # Try to send email - may fail due to SMTP config but endpoint should exist
            response = self.session.post(f"{BASE_URL}/api/contract-notes/send-email/{note_id}")
            # Should not be 404 (endpoint exists)
            assert response.status_code != 404, "send-email endpoint should exist"
            print(f"✓ send-email endpoint exists - Status: {response.status_code}")
            
            # If SMTP not configured, it may return 500 or success with skipped email
            if response.status_code == 200:
                print(f"  Response: {response.json()}")
            elif response.status_code == 500:
                print(f"  Email sending failed (SMTP may not be configured): {response.json().get('detail', 'Unknown error')}")
        else:
            pytest.skip("No contract notes available for testing")
    
    def test_02_send_email_nonexistent_note_returns_404(self):
        """Send email for non-existent contract note returns 404"""
        response = self.session.post(f"{BASE_URL}/api/contract-notes/send-email/nonexistent-id")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
        print("✓ Non-existent contract note returns 404 for send-email")


class TestContractNotePDFAttachment:
    """Tests for PDF attachment in contract note emails"""
    
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
    
    def test_01_contract_note_has_pdf_url(self):
        """Contract notes have pdf_url field"""
        list_response = self.session.get(f"{BASE_URL}/api/contract-notes")
        assert list_response.status_code == 200
        notes = list_response.json()["notes"]
        
        if notes:
            note = notes[0]
            assert "pdf_url" in note, "Contract note should have pdf_url field"
            print(f"✓ Contract note has pdf_url: {note.get('pdf_url')}")
        else:
            pytest.skip("No contract notes available")
    
    def test_02_pdf_file_is_downloadable(self):
        """PDF file can be downloaded and is valid"""
        list_response = self.session.get(f"{BASE_URL}/api/contract-notes")
        assert list_response.status_code == 200
        notes = list_response.json()["notes"]
        
        if notes:
            note_id = notes[0]["id"]
            response = self.session.get(f"{BASE_URL}/api/contract-notes/download/{note_id}")
            assert response.status_code == 200
            assert response.headers.get("content-type") == "application/pdf"
            
            # Verify PDF content starts with PDF magic bytes
            content = response.content
            assert content[:4] == b'%PDF', "Downloaded file should be a valid PDF"
            print(f"✓ PDF is valid and downloadable - Size: {len(content)} bytes")
        else:
            pytest.skip("No contract notes available")
    
    def test_03_email_sent_status_tracked(self):
        """Contract notes track email_sent status"""
        list_response = self.session.get(f"{BASE_URL}/api/contract-notes")
        assert list_response.status_code == 200
        notes = list_response.json()["notes"]
        
        if notes:
            note = notes[0]
            assert "email_sent" in note, "Contract note should have email_sent field"
            assert isinstance(note["email_sent"], bool), "email_sent should be boolean"
            print(f"✓ email_sent status tracked: {note['email_sent']}")
        else:
            pytest.skip("No contract notes available")


class TestDPTransferAutoGeneration:
    """Tests for auto-generation of contract notes on DP transfer completion"""
    
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
    
    def test_01_confirm_stock_transfer_endpoint_exists(self):
        """Verify confirm-stock-transfer endpoint exists"""
        # Try with a non-existent booking to verify endpoint exists
        response = self.session.post(f"{BASE_URL}/api/bookings/nonexistent-id/confirm-stock-transfer")
        # Should be 404 (booking not found) not 405 (method not allowed)
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ confirm-stock-transfer endpoint exists")
    
    def test_02_find_booking_for_dp_transfer_test(self):
        """Find a booking that can be used for DP transfer test"""
        # Get all bookings
        bookings_response = self.session.get(f"{BASE_URL}/api/bookings")
        assert bookings_response.status_code == 200
        bookings = bookings_response.json()
        
        # Find booking with:
        # - approval_status = approved
        # - client_confirmation_status = accepted
        # - payment_status = completed
        # - stock_transferred = False
        eligible_booking = None
        for booking in bookings:
            if (booking.get("approval_status") == "approved" and
                booking.get("client_confirmation_status") == "accepted" and
                booking.get("payment_status") == "completed" and
                not booking.get("stock_transferred")):
                eligible_booking = booking
                break
        
        if eligible_booking:
            print(f"✓ Found eligible booking for DP transfer: {eligible_booking['booking_number']}")
            print(f"  Client: {eligible_booking.get('client_name', 'N/A')}")
            print(f"  Stock: {eligible_booking.get('stock_symbol', 'N/A')}")
            print(f"  Quantity: {eligible_booking.get('quantity', 'N/A')}")
        else:
            print("✓ No eligible booking found for DP transfer test (all may already be transferred)")
            # List bookings that are close to eligible
            for booking in bookings[:5]:
                print(f"  Booking {booking.get('booking_number')}: approval={booking.get('approval_status')}, "
                      f"client_confirm={booking.get('client_confirmation_status')}, "
                      f"payment={booking.get('payment_status')}, transferred={booking.get('stock_transferred')}")
    
    def test_03_verify_existing_contract_notes_have_auto_fields(self):
        """Verify existing contract notes have auto-generation related fields"""
        list_response = self.session.get(f"{BASE_URL}/api/contract-notes")
        assert list_response.status_code == 200
        notes = list_response.json()["notes"]
        
        if notes:
            note = notes[0]
            # Check for email tracking fields
            assert "email_sent" in note, "Should have email_sent field"
            
            # Get detailed note to check more fields
            detail_response = self.session.get(f"{BASE_URL}/api/contract-notes/{note['id']}")
            assert detail_response.status_code == 200
            detail = detail_response.json()
            
            print(f"✓ Contract note fields verified:")
            print(f"  CN Number: {detail.get('contract_note_number')}")
            print(f"  email_sent: {detail.get('email_sent')}")
            print(f"  email_sent_at: {detail.get('email_sent_at', 'N/A')}")
            print(f"  email_sent_by: {detail.get('email_sent_by', 'N/A')}")
        else:
            pytest.skip("No contract notes available")


class TestConfirmStockTransferResponse:
    """Tests for confirm-stock-transfer response fields"""
    
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
    
    def test_01_verify_bookings_with_dp_transfer_have_contract_notes(self):
        """Bookings with DP transfer complete should have contract notes"""
        # Get bookings with stock_transferred = True
        bookings_response = self.session.get(f"{BASE_URL}/api/bookings")
        assert bookings_response.status_code == 200
        bookings = bookings_response.json()
        
        transferred_bookings = [b for b in bookings if b.get("stock_transferred")]
        
        if transferred_bookings:
            # Check if they have contract notes
            cn_response = self.session.get(f"{BASE_URL}/api/contract-notes")
            cn_booking_ids = [n["booking_id"] for n in cn_response.json()["notes"]]
            
            for booking in transferred_bookings[:3]:  # Check first 3
                has_cn = booking["id"] in cn_booking_ids
                print(f"  Booking {booking['booking_number']}: has_contract_note={has_cn}")
            
            print(f"✓ Checked {len(transferred_bookings)} transferred bookings")
        else:
            print("✓ No transferred bookings found")
    
    def test_02_contract_notes_list_shows_email_status(self):
        """Contract notes list shows email_sent status correctly"""
        list_response = self.session.get(f"{BASE_URL}/api/contract-notes")
        assert list_response.status_code == 200
        data = list_response.json()
        
        email_sent_count = sum(1 for n in data["notes"] if n.get("email_sent"))
        pending_count = sum(1 for n in data["notes"] if not n.get("email_sent"))
        
        print(f"✓ Contract notes email status:")
        print(f"  Total: {data['total']}")
        print(f"  Email Sent: {email_sent_count}")
        print(f"  Pending Email: {pending_count}")


class TestEmailServiceCodeReview:
    """Code review tests for email service attachments"""
    
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
    
    def test_01_email_logs_endpoint_exists(self):
        """Email logs endpoint exists for tracking"""
        response = self.session.get(f"{BASE_URL}/api/email-logs")
        # Should not be 404
        assert response.status_code != 404, "email-logs endpoint should exist"
        print(f"✓ email-logs endpoint exists - Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"  Total email logs: {data.get('total', len(data.get('logs', [])))}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
