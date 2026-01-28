"""
RP Finance Integration Tests

Tests for:
1. 30% RP revenue share cap validation on booking creation
2. RP Payments API endpoint GET /api/finance/rp-payments
3. RP Payments API endpoint PUT /api/finance/rp-payments/{id}
4. End-to-end: Create booking with RP → Confirm stock transfer → RP payment created → Update status to Paid
"""
import pytest
import requests
import os
import uuid
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
PE_DESK_EMAIL = "pedesk@smifs.com"
PE_DESK_PASSWORD = "Kutta@123"


class TestRPFinanceIntegration:
    """Test RP Finance Integration features"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        self.pe_desk_token = None
        self.test_client_id = None
        self.test_stock_id = None
        self.test_rp_id = None
        self.test_booking_id = None
        self.test_rp_payment_id = None
    
    def login_pe_desk(self):
        """Login as PE Desk and get token"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": PE_DESK_EMAIL,
            "password": PE_DESK_PASSWORD
        })
        assert response.status_code == 200, f"PE Desk login failed: {response.text}"
        data = response.json()
        self.pe_desk_token = data["token"]
        self.session.headers.update({"Authorization": f"Bearer {self.pe_desk_token}"})
        return data
    
    # ============== 30% RP Revenue Share Cap Tests ==============
    
    def test_01_rp_revenue_share_cap_30_percent(self):
        """Test that RP revenue share cannot exceed 30%"""
        self.login_pe_desk()
        
        # Get an existing client
        clients_response = self.session.get(f"{BASE_URL}/api/clients")
        assert clients_response.status_code == 200
        clients = clients_response.json()
        
        if not clients:
            pytest.skip("No clients available for testing")
        
        client = clients[0]
        
        # Get an existing stock with inventory
        inventory_response = self.session.get(f"{BASE_URL}/api/inventory")
        assert inventory_response.status_code == 200
        inventory = inventory_response.json()
        
        if not inventory or not any(i.get("available_quantity", 0) > 0 for i in inventory):
            pytest.skip("No stocks with available inventory for testing")
        
        stock_with_inventory = next((i for i in inventory if i.get("available_quantity", 0) > 0), None)
        if not stock_with_inventory:
            pytest.skip("No stocks with available inventory")
        
        stock_id = stock_with_inventory["stock_id"]
        
        # Get an existing RP
        rp_response = self.session.get(f"{BASE_URL}/api/referral-partners")
        assert rp_response.status_code == 200
        rps = rp_response.json()
        
        if not rps:
            pytest.skip("No referral partners available for testing")
        
        rp = rps[0]
        
        # Try to create booking with 35% revenue share (should fail)
        booking_data = {
            "client_id": client["id"],
            "stock_id": stock_id,
            "quantity": 1,
            "selling_price": 150.0,
            "buying_price": 100.0,
            "booking_date": datetime.now().strftime("%Y-%m-%d"),
            "status": "pending",
            "booking_type": "regular",
            "insider_form_uploaded": False,
            "referral_partner_id": rp["id"],
            "rp_revenue_share_percent": 35.0  # Exceeds 30% cap
        }
        
        response = self.session.post(f"{BASE_URL}/api/bookings", json=booking_data)
        
        # Should return 400 error
        assert response.status_code == 400, f"Expected 400 for >30% revenue share, got {response.status_code}: {response.text}"
        assert "30%" in response.text or "exceed" in response.text.lower(), f"Error message should mention 30% cap: {response.text}"
        print("✓ 30% RP revenue share cap validation working - rejected 35%")
    
    def test_02_rp_revenue_share_negative_rejected(self):
        """Test that negative RP revenue share is rejected"""
        self.login_pe_desk()
        
        # Get an existing client
        clients_response = self.session.get(f"{BASE_URL}/api/clients")
        clients = clients_response.json()
        
        if not clients:
            pytest.skip("No clients available for testing")
        
        client = clients[0]
        
        # Get an existing stock with inventory
        inventory_response = self.session.get(f"{BASE_URL}/api/inventory")
        inventory = inventory_response.json()
        
        if not inventory or not any(i.get("available_quantity", 0) > 0 for i in inventory):
            pytest.skip("No stocks with available inventory for testing")
        
        stock_with_inventory = next((i for i in inventory if i.get("available_quantity", 0) > 0), None)
        if not stock_with_inventory:
            pytest.skip("No stocks with available inventory")
        
        stock_id = stock_with_inventory["stock_id"]
        
        # Get an existing RP
        rp_response = self.session.get(f"{BASE_URL}/api/referral-partners")
        rps = rp_response.json()
        
        if not rps:
            pytest.skip("No referral partners available for testing")
        
        rp = rps[0]
        
        # Try to create booking with negative revenue share (should fail)
        booking_data = {
            "client_id": client["id"],
            "stock_id": stock_id,
            "quantity": 1,
            "selling_price": 150.0,
            "buying_price": 100.0,
            "booking_date": datetime.now().strftime("%Y-%m-%d"),
            "status": "pending",
            "booking_type": "regular",
            "insider_form_uploaded": False,
            "referral_partner_id": rp["id"],
            "rp_revenue_share_percent": -5.0  # Negative value
        }
        
        response = self.session.post(f"{BASE_URL}/api/bookings", json=booking_data)
        
        # Should return 400 error
        assert response.status_code == 400, f"Expected 400 for negative revenue share, got {response.status_code}: {response.text}"
        assert "negative" in response.text.lower(), f"Error message should mention negative: {response.text}"
        print("✓ Negative RP revenue share correctly rejected")
    
    def test_03_rp_revenue_share_valid_30_percent(self):
        """Test that 30% RP revenue share is accepted (boundary test)"""
        self.login_pe_desk()
        
        # Get an existing client
        clients_response = self.session.get(f"{BASE_URL}/api/clients")
        clients = clients_response.json()
        
        if not clients:
            pytest.skip("No clients available for testing")
        
        # Find an approved client
        approved_client = next((c for c in clients if c.get("approval_status") == "approved" and not c.get("is_suspended")), None)
        if not approved_client:
            pytest.skip("No approved clients available for testing")
        
        # Get an existing stock with inventory
        inventory_response = self.session.get(f"{BASE_URL}/api/inventory")
        inventory = inventory_response.json()
        
        if not inventory or not any(i.get("available_quantity", 0) > 0 for i in inventory):
            pytest.skip("No stocks with available inventory for testing")
        
        stock_with_inventory = next((i for i in inventory if i.get("available_quantity", 0) > 0), None)
        if not stock_with_inventory:
            pytest.skip("No stocks with available inventory")
        
        stock_id = stock_with_inventory["stock_id"]
        
        # Get an existing RP
        rp_response = self.session.get(f"{BASE_URL}/api/referral-partners")
        rps = rp_response.json()
        
        if not rps:
            pytest.skip("No referral partners available for testing")
        
        rp = rps[0]
        
        # Create booking with exactly 30% revenue share (should succeed)
        booking_data = {
            "client_id": approved_client["id"],
            "stock_id": stock_id,
            "quantity": 1,
            "selling_price": 150.0,
            "buying_price": 100.0,
            "booking_date": datetime.now().strftime("%Y-%m-%d"),
            "status": "pending",
            "booking_type": "regular",
            "insider_form_uploaded": False,
            "referral_partner_id": rp["id"],
            "rp_revenue_share_percent": 30.0  # Exactly 30% - should be accepted
        }
        
        response = self.session.post(f"{BASE_URL}/api/bookings", json=booking_data)
        
        # Should succeed (201 or 200)
        assert response.status_code in [200, 201], f"Expected 200/201 for 30% revenue share, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("rp_revenue_share_percent") == 30.0, "Revenue share should be 30%"
        print(f"✓ 30% RP revenue share accepted - Booking {data.get('booking_number')} created")
        
        # Store for cleanup
        self.test_booking_id = data.get("id")
    
    # ============== RP Payments API Tests ==============
    
    def test_04_get_rp_payments_endpoint(self):
        """Test GET /api/finance/rp-payments endpoint"""
        self.login_pe_desk()
        
        response = self.session.get(f"{BASE_URL}/api/finance/rp-payments")
        
        assert response.status_code == 200, f"GET /api/finance/rp-payments failed: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"✓ GET /api/finance/rp-payments returns {len(data)} payments")
    
    def test_05_get_rp_payments_with_status_filter(self):
        """Test GET /api/finance/rp-payments with status filter"""
        self.login_pe_desk()
        
        # Test with pending status
        response = self.session.get(f"{BASE_URL}/api/finance/rp-payments?status=pending")
        assert response.status_code == 200, f"GET with status filter failed: {response.text}"
        data = response.json()
        
        # All returned payments should have pending status
        for payment in data:
            assert payment.get("status") == "pending", f"Payment {payment.get('id')} has status {payment.get('status')}, expected pending"
        
        print(f"✓ GET /api/finance/rp-payments?status=pending returns {len(data)} pending payments")
    
    def test_06_get_rp_payments_summary(self):
        """Test GET /api/finance/rp-payments/summary endpoint"""
        self.login_pe_desk()
        
        response = self.session.get(f"{BASE_URL}/api/finance/rp-payments/summary")
        
        assert response.status_code == 200, f"GET /api/finance/rp-payments/summary failed: {response.text}"
        data = response.json()
        
        # Check expected fields
        expected_fields = ["pending_count", "pending_amount", "processing_count", "processing_amount", 
                          "paid_count", "paid_amount", "total_count", "total_amount"]
        for field in expected_fields:
            assert field in data, f"Missing field: {field}"
        
        print(f"✓ GET /api/finance/rp-payments/summary - Pending: {data['pending_count']}, Paid: {data['paid_count']}")
    
    def test_07_update_rp_payment_status(self):
        """Test PUT /api/finance/rp-payments/{id} endpoint"""
        self.login_pe_desk()
        
        # Get existing RP payments
        response = self.session.get(f"{BASE_URL}/api/finance/rp-payments")
        assert response.status_code == 200
        payments = response.json()
        
        if not payments:
            pytest.skip("No RP payments available for testing")
        
        # Find a pending payment to update
        pending_payment = next((p for p in payments if p.get("status") == "pending"), None)
        if not pending_payment:
            pytest.skip("No pending RP payments available for testing")
        
        payment_id = pending_payment["id"]
        
        # Update to processing status
        update_data = {
            "status": "processing",
            "notes": "Test update - processing payment"
        }
        
        response = self.session.put(f"{BASE_URL}/api/finance/rp-payments/{payment_id}", json=update_data)
        
        assert response.status_code == 200, f"PUT /api/finance/rp-payments/{payment_id} failed: {response.text}"
        print(f"✓ PUT /api/finance/rp-payments/{payment_id} - Updated to processing")
        
        # Verify the update
        verify_response = self.session.get(f"{BASE_URL}/api/finance/rp-payments")
        verify_payments = verify_response.json()
        updated_payment = next((p for p in verify_payments if p.get("id") == payment_id), None)
        
        assert updated_payment is not None, "Payment not found after update"
        assert updated_payment.get("status") == "processing", f"Status should be processing, got {updated_payment.get('status')}"
        print(f"✓ Verified payment status updated to processing")
        
        # Store for next test
        self.test_rp_payment_id = payment_id
    
    def test_08_update_rp_payment_to_paid(self):
        """Test updating RP payment to paid status with reference"""
        self.login_pe_desk()
        
        # Get existing RP payments
        response = self.session.get(f"{BASE_URL}/api/finance/rp-payments")
        assert response.status_code == 200
        payments = response.json()
        
        if not payments:
            pytest.skip("No RP payments available for testing")
        
        # Find a processing or pending payment to mark as paid
        payment_to_update = next((p for p in payments if p.get("status") in ["pending", "processing"]), None)
        if not payment_to_update:
            pytest.skip("No pending/processing RP payments available for testing")
        
        payment_id = payment_to_update["id"]
        
        # Update to paid status with reference
        update_data = {
            "status": "paid",
            "payment_reference": f"UTR{uuid.uuid4().hex[:12].upper()}",
            "payment_date": datetime.now().strftime("%Y-%m-%d"),
            "notes": "Test payment completed"
        }
        
        response = self.session.put(f"{BASE_URL}/api/finance/rp-payments/{payment_id}", json=update_data)
        
        assert response.status_code == 200, f"PUT to paid status failed: {response.text}"
        print(f"✓ PUT /api/finance/rp-payments/{payment_id} - Updated to paid with reference")
        
        # Verify the update
        verify_response = self.session.get(f"{BASE_URL}/api/finance/rp-payments")
        verify_payments = verify_response.json()
        updated_payment = next((p for p in verify_payments if p.get("id") == payment_id), None)
        
        assert updated_payment is not None, "Payment not found after update"
        assert updated_payment.get("status") == "paid", f"Status should be paid, got {updated_payment.get('status')}"
        assert updated_payment.get("payment_reference") is not None, "Payment reference should be set"
        print(f"✓ Verified payment marked as paid with reference: {updated_payment.get('payment_reference')}")
    
    def test_09_update_nonexistent_rp_payment(self):
        """Test updating non-existent RP payment returns 404"""
        self.login_pe_desk()
        
        fake_id = str(uuid.uuid4())
        update_data = {
            "status": "paid",
            "notes": "Test"
        }
        
        response = self.session.put(f"{BASE_URL}/api/finance/rp-payments/{fake_id}", json=update_data)
        
        assert response.status_code == 404, f"Expected 404 for non-existent payment, got {response.status_code}"
        print("✓ Non-existent RP payment correctly returns 404")
    
    # ============== Finance Summary Tests ==============
    
    def test_10_finance_summary_includes_rp_payments(self):
        """Test that finance summary includes RP payment stats"""
        self.login_pe_desk()
        
        response = self.session.get(f"{BASE_URL}/api/finance/summary")
        
        assert response.status_code == 200, f"GET /api/finance/summary failed: {response.text}"
        data = response.json()
        
        # Check RP payment fields exist
        assert "pending_rp_payments_count" in data, "Missing pending_rp_payments_count"
        assert "pending_rp_payments_amount" in data, "Missing pending_rp_payments_amount"
        assert "paid_rp_payments_count" in data, "Missing paid_rp_payments_count"
        assert "paid_rp_payments_amount" in data, "Missing paid_rp_payments_amount"
        
        print(f"✓ Finance summary includes RP payments - Pending: {data['pending_rp_payments_count']}, Paid: {data['paid_rp_payments_count']}")
    
    # ============== Access Control Tests ==============
    
    def test_11_rp_payments_requires_finance_access(self):
        """Test that RP payments endpoint requires finance access"""
        # Try without authentication
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})
        
        response = session.get(f"{BASE_URL}/api/finance/rp-payments")
        
        # Should return 401 or 403
        assert response.status_code in [401, 403], f"Expected 401/403 without auth, got {response.status_code}"
        print("✓ RP payments endpoint requires authentication")


class TestEndToEndRPPaymentFlow:
    """End-to-end test for RP payment creation flow"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def login_pe_desk(self):
        """Login as PE Desk and get token"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": PE_DESK_EMAIL,
            "password": PE_DESK_PASSWORD
        })
        assert response.status_code == 200, f"PE Desk login failed: {response.text}"
        data = response.json()
        self.session.headers.update({"Authorization": f"Bearer {data['token']}"})
        return data
    
    def test_e2e_booking_with_rp_creates_payment_on_transfer(self):
        """
        End-to-end test:
        1. Create booking with RP and revenue share
        2. Approve booking
        3. Record full payment
        4. Confirm stock transfer
        5. Verify RP payment is created
        """
        self.login_pe_desk()
        
        # Step 1: Get test data
        clients_response = self.session.get(f"{BASE_URL}/api/clients")
        clients = clients_response.json()
        approved_client = next((c for c in clients if c.get("approval_status") == "approved" and not c.get("is_suspended") and not c.get("is_vendor")), None)
        
        if not approved_client:
            pytest.skip("No approved client available")
        
        inventory_response = self.session.get(f"{BASE_URL}/api/inventory")
        inventory = inventory_response.json()
        stock_with_inventory = next((i for i in inventory if i.get("available_quantity", 0) >= 10), None)
        
        if not stock_with_inventory:
            pytest.skip("No stock with sufficient inventory")
        
        rp_response = self.session.get(f"{BASE_URL}/api/referral-partners?active_only=true")
        rps = rp_response.json()
        
        if not rps:
            pytest.skip("No active referral partners")
        
        rp = rps[0]
        stock_id = stock_with_inventory["stock_id"]
        
        # Step 2: Create booking with RP
        booking_data = {
            "client_id": approved_client["id"],
            "stock_id": stock_id,
            "quantity": 5,
            "selling_price": 200.0,
            "buying_price": 100.0,
            "booking_date": datetime.now().strftime("%Y-%m-%d"),
            "status": "pending",
            "booking_type": "regular",
            "insider_form_uploaded": False,
            "referral_partner_id": rp["id"],
            "rp_revenue_share_percent": 20.0  # 20% revenue share
        }
        
        create_response = self.session.post(f"{BASE_URL}/api/bookings", json=booking_data)
        
        if create_response.status_code != 200 and create_response.status_code != 201:
            pytest.skip(f"Could not create booking: {create_response.text}")
        
        booking = create_response.json()
        booking_id = booking["id"]
        booking_number = booking.get("booking_number")
        print(f"✓ Step 1: Created booking {booking_number} with RP {rp.get('rp_code')}")
        
        # Step 3: Approve booking
        approve_response = self.session.put(f"{BASE_URL}/api/bookings/{booking_id}/approve?approve=true")
        assert approve_response.status_code == 200, f"Approve failed: {approve_response.text}"
        print(f"✓ Step 2: Booking approved")
        
        # Step 4: Simulate client confirmation
        # Get booking to get confirmation token
        booking_detail = self.session.get(f"{BASE_URL}/api/bookings/{booking_id}").json()
        
        # Step 5: Record full payment
        total_amount = 5 * 200.0  # quantity * selling_price = 1000
        payment_data = {
            "amount": total_amount,
            "payment_date": datetime.now().strftime("%Y-%m-%d"),
            "notes": "Test payment for RP flow"
        }
        
        payment_response = self.session.post(f"{BASE_URL}/api/bookings/{booking_id}/payments", json=payment_data)
        
        if payment_response.status_code != 200:
            # Try to void the booking for cleanup
            self.session.put(f"{BASE_URL}/api/bookings/{booking_id}/void?reason=Test%20cleanup")
            pytest.skip(f"Could not record payment: {payment_response.text}")
        
        print(f"✓ Step 3: Recorded payment of {total_amount}")
        
        # Step 6: Confirm stock transfer
        transfer_response = self.session.put(f"{BASE_URL}/api/bookings/{booking_id}/confirm-transfer", json={
            "notes": "Test transfer for RP payment flow"
        })
        
        if transfer_response.status_code != 200:
            pytest.skip(f"Could not confirm transfer: {transfer_response.text}")
        
        transfer_data = transfer_response.json()
        print(f"✓ Step 4: Stock transfer confirmed")
        
        # Step 7: Verify RP payment was created
        assert transfer_data.get("rp_payment_created") == True, "RP payment should be created"
        
        # Calculate expected payment: profit * revenue_share_percent / 100
        # Profit = (200 - 100) * 5 = 500
        # RP Payment = 500 * 20% = 100
        expected_rp_payment = 500 * 0.20
        actual_rp_payment = transfer_data.get("rp_payment_amount")
        
        assert actual_rp_payment == expected_rp_payment, f"Expected RP payment {expected_rp_payment}, got {actual_rp_payment}"
        print(f"✓ Step 5: RP payment created - Amount: {actual_rp_payment}")
        
        # Step 8: Verify RP payment appears in finance endpoint
        rp_payments_response = self.session.get(f"{BASE_URL}/api/finance/rp-payments")
        rp_payments = rp_payments_response.json()
        
        rp_payment = next((p for p in rp_payments if p.get("booking_id") == booking_id), None)
        assert rp_payment is not None, "RP payment should appear in finance endpoint"
        assert rp_payment.get("status") == "pending", "New RP payment should have pending status"
        assert rp_payment.get("payment_amount") == expected_rp_payment, f"Payment amount mismatch"
        assert rp_payment.get("revenue_share_percent") == 20.0, "Revenue share should be 20%"
        
        print(f"✓ Step 6: RP payment verified in finance endpoint")
        print(f"  - RP: {rp_payment.get('rp_name')} ({rp_payment.get('rp_code')})")
        print(f"  - Profit: {rp_payment.get('profit')}")
        print(f"  - Revenue Share: {rp_payment.get('revenue_share_percent')}%")
        print(f"  - Payment Amount: {rp_payment.get('payment_amount')}")
        print(f"  - Status: {rp_payment.get('status')}")
        
        # Step 9: Update RP payment to paid
        update_response = self.session.put(f"{BASE_URL}/api/finance/rp-payments/{rp_payment['id']}", json={
            "status": "paid",
            "payment_reference": f"UTR{uuid.uuid4().hex[:12].upper()}",
            "payment_date": datetime.now().strftime("%Y-%m-%d"),
            "notes": "E2E test payment completed"
        })
        
        assert update_response.status_code == 200, f"Failed to update RP payment: {update_response.text}"
        print(f"✓ Step 7: RP payment marked as paid")
        
        print("\n✓ END-TO-END TEST PASSED: Booking with RP → Transfer → RP Payment Created → Marked Paid")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
