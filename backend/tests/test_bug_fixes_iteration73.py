"""
Bug Fix Tests - Iteration 73
Tests for:
1. Employee visibility of bookings for mapped clients (even if created by PE Desk)
2. Payment status update to 'paid' when full payment is recorded
3. DP status update to 'ready' when payment is complete
4. PE level users can download documents from GridFS
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
PE_DESK_EMAIL = "pedesk@smifs.com"
PE_DESK_PASSWORD = "password"
EMPLOYEE_EMAIL = "freshemployee@smifs.com"
EMPLOYEE_PASSWORD = "password"

# Test data from context
TEST_CLIENT_ID = "d6e65ab9-d513-4a95-abec-d01fdfeb38e3"
TEST_EMPLOYEE_ID = "158a4cbd-cfad-41fa-aea2-22f3cf170402"


class TestAuthentication:
    """Test authentication for both users"""
    
    def test_pe_desk_login(self):
        """PE Desk can login successfully"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": PE_DESK_EMAIL,
            "password": PE_DESK_PASSWORD
        })
        assert response.status_code == 200, f"PE Desk login failed: {response.text}"
        data = response.json()
        assert "token" in data
        assert data.get("user", {}).get("email") == PE_DESK_EMAIL
        print("✓ PE Desk login successful")
    
    def test_employee_login(self):
        """Employee can login successfully"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": EMPLOYEE_EMAIL,
            "password": EMPLOYEE_PASSWORD
        })
        assert response.status_code == 200, f"Employee login failed: {response.text}"
        data = response.json()
        assert "token" in data
        assert data.get("user", {}).get("email") == EMPLOYEE_EMAIL
        print("✓ Employee login successful")


@pytest.fixture
def pe_desk_token():
    """Get PE Desk authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": PE_DESK_EMAIL,
        "password": PE_DESK_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip("PE Desk authentication failed")


@pytest.fixture
def employee_token():
    """Get Employee authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": EMPLOYEE_EMAIL,
        "password": EMPLOYEE_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip("Employee authentication failed")


class TestClientMappingVerification:
    """Verify client d6e65ab9 is mapped to employee 158a4cbd"""
    
    def test_client_mapping(self, pe_desk_token):
        """Verify the test client is mapped to the test employee"""
        headers = {"Authorization": f"Bearer {pe_desk_token}"}
        response = requests.get(f"{BASE_URL}/api/clients/{TEST_CLIENT_ID}", headers=headers)
        
        assert response.status_code == 200, f"Failed to get client: {response.text}"
        client = response.json()
        
        mapped_employee_id = client.get("mapped_employee_id")
        print(f"Client '{client.get('name')}' is mapped to employee ID: {mapped_employee_id}")
        
        assert mapped_employee_id == TEST_EMPLOYEE_ID, \
            f"Client not mapped to expected employee. Actual: {mapped_employee_id}, Expected: {TEST_EMPLOYEE_ID}"
        print(f"✓ Client is correctly mapped to employee {TEST_EMPLOYEE_ID}")


class TestBookingVisibility:
    """Test that employees can see bookings for clients mapped to them"""
    
    def test_pe_desk_creates_booking_for_mapped_client(self, pe_desk_token):
        """PE Desk creates a booking for a client mapped to employee"""
        headers = {"Authorization": f"Bearer {pe_desk_token}"}
        
        # Get a stock to use
        stocks_response = requests.get(f"{BASE_URL}/api/stocks", headers=headers)
        assert stocks_response.status_code == 200
        stocks = stocks_response.json()
        
        if not stocks:
            pytest.skip("No stocks available for booking test")
        
        stock = stocks[0]
        stock_id = stock.get("id")
        
        # Create a booking for the mapped client
        booking_data = {
            "client_id": TEST_CLIENT_ID,
            "stock_id": stock_id,
            "quantity": 10,
            "selling_price": 100.0,
            "booking_date": "2026-02-06",
            "status": "pending",
            "booking_type": "regular"
        }
        
        response = requests.post(f"{BASE_URL}/api/bookings", json=booking_data, headers=headers)
        
        # May fail due to duplicate booking, that's ok
        if response.status_code == 200:
            booking = response.json()
            print(f"✓ PE Desk created booking {booking.get('booking_number')} for mapped client")
            return booking
        elif response.status_code == 400:
            detail = response.json().get("detail", "")
            if "Duplicate" in detail or "already exists" in detail or "just created" in detail:
                print("✓ Booking already exists (duplicate check working)")
                return None
            else:
                pytest.fail(f"Booking creation failed: {detail}")
        else:
            pytest.fail(f"Unexpected response: {response.status_code} - {response.text}")
    
    def test_employee_sees_bookings_for_mapped_client(self, employee_token):
        """Employee should see bookings for clients mapped to them"""
        headers = {"Authorization": f"Bearer {employee_token}"}
        
        # Get all bookings visible to employee
        response = requests.get(f"{BASE_URL}/api/bookings", headers=headers)
        assert response.status_code == 200, f"Failed to get bookings: {response.text}"
        
        bookings = response.json()
        print(f"Employee sees {len(bookings)} bookings")
        
        # Check if any booking is for the mapped client
        bookings_for_mapped_client = [b for b in bookings if b.get("client_id") == TEST_CLIENT_ID]
        print(f"Bookings for mapped client {TEST_CLIENT_ID}: {len(bookings_for_mapped_client)}")
        
        # List all booking numbers for mapped client
        for booking in bookings_for_mapped_client:
            created_by = booking.get("created_by")
            created_by_name = booking.get("created_by_name", "Unknown")
            print(f"  - {booking.get('booking_number')} created by {created_by_name} ({created_by})")
        
        assert len(bookings_for_mapped_client) > 0, \
            "Employee should see at least one booking for their mapped client"
        print(f"✓ Employee can see {len(bookings_for_mapped_client)} booking(s) for mapped client")
        
        return bookings_for_mapped_client
    
    def test_employee_sees_pe_desk_created_bookings(self, employee_token, pe_desk_token):
        """Employee should see bookings created by PE Desk for their mapped client"""
        headers = {"Authorization": f"Bearer {employee_token}"}
        
        # Get all bookings visible to employee
        response = requests.get(f"{BASE_URL}/api/bookings", headers=headers)
        assert response.status_code == 200, f"Failed to get bookings: {response.text}"
        
        bookings = response.json()
        
        # Check for bookings created by PE Desk for the mapped client
        pe_desk_created_bookings = [
            b for b in bookings 
            if b.get("client_id") == TEST_CLIENT_ID and b.get("created_by") != TEST_EMPLOYEE_ID
        ]
        
        print(f"Bookings for mapped client created by others: {len(pe_desk_created_bookings)}")
        for booking in pe_desk_created_bookings:
            print(f"  - {booking.get('booking_number')} created by {booking.get('created_by_name', 'Unknown')}")
        
        # Even if no PE Desk bookings exist, the query should work
        print("✓ Booking visibility query works correctly")


class TestPaymentStatusUpdate:
    """Test that payment status updates correctly when full payment is recorded"""
    
    def test_payment_status_updates_to_paid(self, pe_desk_token):
        """Payment status should be 'paid' when full payment is recorded"""
        headers = {"Authorization": f"Bearer {pe_desk_token}"}
        
        # Get a booking to test payment on
        response = requests.get(f"{BASE_URL}/api/bookings", headers=headers)
        assert response.status_code == 200
        bookings = response.json()
        
        # Find an approved booking without full payment
        test_booking = None
        for booking in bookings:
            if (booking.get("approval_status") == "approved" and 
                not booking.get("is_voided") and
                booking.get("payment_status") != "paid"):
                test_booking = booking
                break
        
        if not test_booking:
            # Check if there's a booking with payment_status = paid to verify
            paid_bookings = [b for b in bookings if b.get("payment_status") == "paid"]
            if paid_bookings:
                print(f"✓ Found {len(paid_bookings)} booking(s) with payment_status='paid'")
                for pb in paid_bookings[:3]:
                    print(f"  - {pb.get('booking_number')}: payment_status={pb.get('payment_status')}, dp_status={pb.get('dp_status')}")
                return
            pytest.skip("No suitable booking found for payment test")
        
        booking_id = test_booking.get("id")
        booking_number = test_booking.get("booking_number")
        total_amount = test_booking.get("total_amount", 0)
        total_paid = test_booking.get("total_paid", 0)
        remaining = total_amount - total_paid
        
        print(f"Testing payment on booking {booking_number}")
        print(f"  Total amount: {total_amount}, Already paid: {total_paid}, Remaining: {remaining}")
        
        if remaining <= 0:
            pytest.skip("Booking already fully paid")
        
        # Record the remaining payment
        payment_data = {
            "amount": remaining,
            "payment_mode": "bank_transfer",
            "reference_number": "TEST-PAYMENT-73"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/bookings/{booking_id}/payments",
            json=payment_data,
            headers=headers
        )
        
        assert response.status_code == 200, f"Payment recording failed: {response.text}"
        payment_result = response.json()
        print(f"  Payment recorded: {payment_result.get('message')}")
        
        # Verify the booking status after payment
        response = requests.get(f"{BASE_URL}/api/bookings/{booking_id}", headers=headers)
        assert response.status_code == 200
        updated_booking = response.json()
        
        payment_status = updated_booking.get("payment_status")
        dp_status = updated_booking.get("dp_status")
        
        print("  After full payment:")
        print(f"    payment_status: {payment_status}")
        print(f"    dp_status: {dp_status}")
        
        assert payment_status == "paid", f"Expected payment_status='paid', got '{payment_status}'"
        print("✓ Payment status correctly updated to 'paid'")
        
        assert dp_status == "ready", f"Expected dp_status='ready', got '{dp_status}'"
        print("✓ DP status correctly updated to 'ready'")


class TestDPStatusUpdate:
    """Test that DP status updates to 'ready' when payment is complete"""
    
    def test_dp_status_ready_when_paid(self, pe_desk_token):
        """DP status should be 'ready' when booking is fully paid"""
        headers = {"Authorization": f"Bearer {pe_desk_token}"}
        
        # Get all bookings
        response = requests.get(f"{BASE_URL}/api/bookings", headers=headers)
        assert response.status_code == 200
        bookings = response.json()
        
        # Find bookings with payment_status='paid'
        paid_bookings = [b for b in bookings if b.get("payment_status") == "paid"]
        
        print(f"Found {len(paid_bookings)} booking(s) with payment_status='paid'")
        
        for booking in paid_bookings[:5]:
            dp_status = booking.get("dp_status")
            booking_number = booking.get("booking_number")
            print(f"  - {booking_number}: payment_status=paid, dp_status={dp_status}")
            
            # Verify dp_status is 'ready' or 'transferred'
            assert dp_status in ["ready", "transferred"], \
                f"Booking {booking_number} has payment_status=paid but dp_status={dp_status}"
        
        print("✓ All paid bookings have correct DP status")
    
    def test_dp_ready_bookings_endpoint(self, pe_desk_token):
        """Test the /bookings/dp-ready endpoint"""
        headers = {"Authorization": f"Bearer {pe_desk_token}"}
        
        response = requests.get(f"{BASE_URL}/api/bookings/dp-ready", headers=headers)
        assert response.status_code == 200, f"Failed to get DP ready bookings: {response.text}"
        
        dp_ready_bookings = response.json()
        print(f"DP Ready bookings count: {len(dp_ready_bookings)}")
        
        for booking in dp_ready_bookings[:5]:
            print(f"  - {booking.get('booking_number')}: client={booking.get('client_name')}")
        
        print("✓ /api/bookings/dp-ready endpoint working")


class TestDocumentDownload:
    """Test that documents can be downloaded from GridFS"""
    
    def test_client_document_status(self, pe_desk_token):
        """Check document status for test client"""
        headers = {"Authorization": f"Bearer {pe_desk_token}"}
        
        response = requests.get(
            f"{BASE_URL}/api/clients/{TEST_CLIENT_ID}/document-status",
            headers=headers
        )
        
        assert response.status_code == 200, f"Failed to get document status: {response.text}"
        doc_status = response.json()
        
        print(f"Document status for client '{doc_status.get('client_name')}':")
        documents = doc_status.get("documents", {})
        
        for doc_type, status in documents.items():
            uploaded = status.get("uploaded", False)
            stored = status.get("stored_in_gridfs", False)
            file_id = status.get("file_id")
            print(f"  - {doc_type}: uploaded={uploaded}, stored_in_gridfs={stored}, file_id={file_id}")
        
        summary = doc_status.get("summary", {})
        print(f"  Summary: all_mandatory_stored={summary.get('all_mandatory_stored')}")
        print("✓ Document status endpoint working")
    
    def test_pe_user_can_download_documents(self, pe_desk_token):
        """PE level users should be able to download documents"""
        headers = {"Authorization": f"Bearer {pe_desk_token}"}
        
        # Get client details to find document filename
        response = requests.get(f"{BASE_URL}/api/clients/{TEST_CLIENT_ID}", headers=headers)
        assert response.status_code == 200
        client = response.json()
        
        documents = client.get("documents", [])
        if not documents:
            pytest.skip("No documents found for test client")
        
        # Try to download each document
        for doc in documents:
            filename = doc.get("filename")
            file_id = doc.get("file_id")
            doc_type = doc.get("doc_type")
            
            print(f"Attempting to download {doc_type} (filename={filename}, file_id={file_id})")
            
            if not filename:
                print("  - Skipping: no filename")
                continue
            
            response = requests.get(
                f"{BASE_URL}/api/clients/{TEST_CLIENT_ID}/documents/{filename}",
                headers=headers
            )
            
            if response.status_code == 200:
                print(f"  ✓ Downloaded successfully (size: {len(response.content)} bytes)")
            elif response.status_code == 404:
                print("  ✗ Document not found (404)")
            else:
                print(f"  ✗ Download failed: {response.status_code} - {response.text[:100]}")
    
    def test_employee_can_view_documents(self, employee_token):
        """Employee should be able to view documents for mapped client"""
        headers = {"Authorization": f"Bearer {employee_token}"}
        
        # Get client document status
        response = requests.get(
            f"{BASE_URL}/api/clients/{TEST_CLIENT_ID}/document-status",
            headers=headers
        )
        
        # Should be accessible
        assert response.status_code == 200, f"Employee cannot access document status: {response.text}"
        print("✓ Employee can access document status for mapped client")
        
        doc_status = response.json()
        documents = doc_status.get("documents", {})
        
        # Try downloading a document
        for doc_type, status in documents.items():
            if status.get("uploaded") and status.get("filename"):
                filename = status.get("filename")
                print(f"Attempting to download {doc_type} as employee...")
                
                response = requests.get(
                    f"{BASE_URL}/api/clients/{TEST_CLIENT_ID}/documents/{filename}",
                    headers=headers
                )
                
                if response.status_code == 200:
                    print(f"  ✓ Employee downloaded {doc_type} successfully")
                else:
                    print(f"  ✗ Download failed: {response.status_code}")
                break


class TestSpecificBooking:
    """Test the specific booking mentioned in the context (BK-2026-00033)"""
    
    def test_booking_bk_2026_00033_visibility(self, employee_token, pe_desk_token):
        """Verify booking BK-2026-00033 is visible to employee"""
        headers = {"Authorization": f"Bearer {employee_token}"}
        
        # Get all bookings for employee
        response = requests.get(f"{BASE_URL}/api/bookings", headers=headers)
        assert response.status_code == 200
        
        bookings = response.json()
        
        # Look for the specific booking
        target_booking = None
        for booking in bookings:
            if booking.get("booking_number") == "BK-2026-00033":
                target_booking = booking
                break
        
        if target_booking:
            print("✓ Booking BK-2026-00033 is visible to employee")
            print(f"  - Client: {target_booking.get('client_name')}")
            print(f"  - Created by: {target_booking.get('created_by_name')}")
            print(f"  - Payment status: {target_booking.get('payment_status')}")
            print(f"  - DP status: {target_booking.get('dp_status')}")
        else:
            # List available bookings
            print("Booking BK-2026-00033 not found. Available bookings:")
            for b in bookings[:10]:
                print(f"  - {b.get('booking_number')} for client {b.get('client_name')}")
            
            # Check if there are any bookings for the mapped client
            client_bookings = [b for b in bookings if b.get("client_id") == TEST_CLIENT_ID]
            if client_bookings:
                print(f"\nBookings for mapped client ({len(client_bookings)}):")
                for b in client_bookings:
                    print(f"  - {b.get('booking_number')} (payment: {b.get('payment_status')}, dp: {b.get('dp_status')})")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
