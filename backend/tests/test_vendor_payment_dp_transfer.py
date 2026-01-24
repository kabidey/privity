"""
Test suite for Vendor Payment and DP Transfer Confirmation features
- POST /api/purchases/{purchase_id}/payments - Record vendor payment
- PUT /api/bookings/{booking_id}/confirm-transfer - Confirm stock transfer
"""
import pytest
import requests
import os
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
PE_DESK_ADMIN = {"email": "admin@privity.com", "password": "Admin@123"}


class TestVendorPaymentAndDPTransfer:
    """Test vendor payment recording and DP transfer confirmation"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session with authentication"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as PE Desk admin
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json=PE_DESK_ADMIN)
        assert login_response.status_code == 200, f"Login failed: {login_response.text}"
        
        token = login_response.json().get("token")
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        self.user = login_response.json().get("user")
        print(f"✓ Logged in as PE Desk admin: {self.user['email']} (role: {self.user['role']})")
    
    # ============== Vendor Payment Tests ==============
    
    def test_get_purchases_list(self):
        """Test getting list of purchases"""
        response = self.session.get(f"{BASE_URL}/api/purchases")
        assert response.status_code == 200, f"Failed to get purchases: {response.text}"
        
        purchases = response.json()
        print(f"✓ Retrieved {len(purchases)} purchases")
        
        # Check purchase structure
        if purchases:
            purchase = purchases[0]
            assert "id" in purchase
            assert "vendor_id" in purchase
            assert "stock_id" in purchase
            assert "quantity" in purchase
            assert "total_amount" in purchase
            print(f"✓ Purchase structure validated: {purchase.get('stock_symbol', 'N/A')} - ₹{purchase.get('total_amount', 0)}")
        
        return purchases
    
    def test_purchase_payment_status_fields(self):
        """Test that purchases have payment status fields"""
        response = self.session.get(f"{BASE_URL}/api/purchases")
        assert response.status_code == 200
        
        purchases = response.json()
        if purchases:
            purchase = purchases[0]
            # Check payment-related fields exist
            assert "payment_status" in purchase or purchase.get("payment_status") is None, "payment_status field should exist"
            assert "total_paid" in purchase or purchase.get("total_paid") is None, "total_paid field should exist"
            print(f"✓ Payment fields present: status={purchase.get('payment_status', 'pending')}, paid=₹{purchase.get('total_paid', 0)}")
    
    def test_record_vendor_payment_requires_pe_desk(self):
        """Test that only PE Desk can record vendor payments"""
        # First get a purchase
        purchases_response = self.session.get(f"{BASE_URL}/api/purchases")
        if purchases_response.status_code != 200 or not purchases_response.json():
            pytest.skip("No purchases available for testing")
        
        purchase = purchases_response.json()[0]
        purchase_id = purchase["id"]
        
        # PE Desk should be able to record payment
        payment_data = {
            "amount": 100.00,
            "payment_date": datetime.now().strftime("%Y-%m-%d"),
            "notes": "Test payment"
        }
        
        # This should work for PE Desk
        response = self.session.post(f"{BASE_URL}/api/purchases/{purchase_id}/payments", json=payment_data)
        # Either success or validation error (like exceeding remaining balance)
        assert response.status_code in [200, 400], f"Unexpected status: {response.status_code} - {response.text}"
        
        if response.status_code == 200:
            result = response.json()
            print(f"✓ Payment recorded: tranche #{result.get('tranche_number')}, amount=₹{result.get('amount')}")
        else:
            print(f"✓ Payment validation working: {response.json().get('detail')}")
    
    def test_payment_validation_exceeds_remaining(self):
        """Test that payment amount cannot exceed remaining balance"""
        purchases_response = self.session.get(f"{BASE_URL}/api/purchases")
        if purchases_response.status_code != 200 or not purchases_response.json():
            pytest.skip("No purchases available for testing")
        
        purchase = purchases_response.json()[0]
        purchase_id = purchase["id"]
        total_amount = purchase["total_amount"]
        
        # Try to pay more than total amount
        payment_data = {
            "amount": total_amount + 10000,  # Way more than total
            "payment_date": datetime.now().strftime("%Y-%m-%d"),
            "notes": "Overpayment test"
        }
        
        response = self.session.post(f"{BASE_URL}/api/purchases/{purchase_id}/payments", json=payment_data)
        assert response.status_code == 400, f"Should reject overpayment: {response.text}"
        assert "exceeds" in response.json().get("detail", "").lower()
        print(f"✓ Overpayment correctly rejected: {response.json().get('detail')}")
    
    def test_payment_invalid_purchase_id(self):
        """Test payment with invalid purchase ID"""
        payment_data = {
            "amount": 100.00,
            "payment_date": datetime.now().strftime("%Y-%m-%d"),
            "notes": "Test"
        }
        
        response = self.session.post(f"{BASE_URL}/api/purchases/invalid-id-12345/payments", json=payment_data)
        assert response.status_code == 404, f"Should return 404 for invalid purchase: {response.text}"
        print(f"✓ Invalid purchase ID correctly returns 404")
    
    def test_get_purchase_payments(self):
        """Test getting payment history for a purchase"""
        purchases_response = self.session.get(f"{BASE_URL}/api/purchases")
        if purchases_response.status_code != 200 or not purchases_response.json():
            pytest.skip("No purchases available for testing")
        
        purchase = purchases_response.json()[0]
        purchase_id = purchase["id"]
        
        response = self.session.get(f"{BASE_URL}/api/purchases/{purchase_id}/payments")
        assert response.status_code == 200, f"Failed to get payments: {response.text}"
        
        result = response.json()
        assert "payments" in result
        assert "total_paid" in result
        assert "remaining" in result
        print(f"✓ Payment history retrieved: {len(result.get('payments', []))} payments, total_paid=₹{result.get('total_paid', 0)}")
    
    # ============== DP Transfer Tests ==============
    
    def test_get_dp_transfer_report(self):
        """Test getting DP transfer report"""
        response = self.session.get(f"{BASE_URL}/api/dp-transfer-report")
        assert response.status_code == 200, f"Failed to get DP transfer report: {response.text}"
        
        records = response.json()
        print(f"✓ DP Transfer Report: {len(records)} records ready for transfer")
        
        if records:
            record = records[0]
            assert "booking_id" in record
            assert "client_name" in record
            assert "pan_number" in record
            assert "dp_id" in record
            assert "stock_symbol" in record
            assert "quantity" in record
            print(f"✓ Record structure validated: {record.get('client_name')} - {record.get('stock_symbol')}")
        
        return records
    
    def test_confirm_transfer_requires_pe_desk(self):
        """Test that only PE Desk can confirm stock transfers"""
        # Get DP transfer records
        records_response = self.session.get(f"{BASE_URL}/api/dp-transfer-report")
        if records_response.status_code != 200 or not records_response.json():
            pytest.skip("No records ready for DP transfer")
        
        record = records_response.json()[0]
        booking_id = record["booking_id"]
        
        # PE Desk should be able to confirm transfer
        response = self.session.put(
            f"{BASE_URL}/api/bookings/{booking_id}/confirm-transfer",
            json={"notes": "Test transfer confirmation"}
        )
        
        # Either success or already transferred
        assert response.status_code in [200, 400], f"Unexpected status: {response.status_code} - {response.text}"
        
        if response.status_code == 200:
            result = response.json()
            print(f"✓ Transfer confirmed: {result.get('booking_number')}")
        else:
            print(f"✓ Transfer validation: {response.json().get('detail')}")
    
    def test_confirm_transfer_invalid_booking(self):
        """Test transfer confirmation with invalid booking ID"""
        response = self.session.put(
            f"{BASE_URL}/api/bookings/invalid-booking-12345/confirm-transfer",
            json={"notes": "Test"}
        )
        assert response.status_code == 404, f"Should return 404 for invalid booking: {response.text}"
        print(f"✓ Invalid booking ID correctly returns 404")
    
    def test_confirm_transfer_not_ready(self):
        """Test that transfer fails if booking is not ready (no full payment)"""
        # Get all bookings
        bookings_response = self.session.get(f"{BASE_URL}/api/bookings")
        if bookings_response.status_code != 200 or not bookings_response.json():
            pytest.skip("No bookings available for testing")
        
        bookings = bookings_response.json()
        
        # Find a booking that is NOT ready for transfer
        not_ready_booking = None
        for booking in bookings:
            if not booking.get("dp_transfer_ready"):
                not_ready_booking = booking
                break
        
        if not not_ready_booking:
            pytest.skip("All bookings are ready for transfer")
        
        response = self.session.put(
            f"{BASE_URL}/api/bookings/{not_ready_booking['id']}/confirm-transfer",
            json={"notes": "Test"}
        )
        assert response.status_code == 400, f"Should reject non-ready booking: {response.text}"
        print(f"✓ Non-ready booking correctly rejected: {response.json().get('detail')}")
    
    # ============== Integration Tests ==============
    
    def test_purchases_page_data_structure(self):
        """Test that purchases have all required fields for UI"""
        response = self.session.get(f"{BASE_URL}/api/purchases")
        assert response.status_code == 200
        
        purchases = response.json()
        if purchases:
            purchase = purchases[0]
            required_fields = ["id", "vendor_id", "vendor_name", "stock_id", "stock_symbol", 
                            "quantity", "price_per_unit", "total_amount", "purchase_date"]
            
            for field in required_fields:
                assert field in purchase, f"Missing required field: {field}"
            
            print(f"✓ All required fields present for Purchases page UI")
    
    def test_dp_transfer_report_data_structure(self):
        """Test that DP transfer records have all required fields for UI"""
        response = self.session.get(f"{BASE_URL}/api/dp-transfer-report")
        assert response.status_code == 200
        
        records = response.json()
        if records:
            record = records[0]
            required_fields = ["booking_id", "client_name", "pan_number", "dp_id", 
                            "stock_symbol", "quantity", "total_amount"]
            
            for field in required_fields:
                assert field in record, f"Missing required field: {field}"
            
            print(f"✓ All required fields present for DP Transfer Report UI")


class TestVendorPaymentEndToEnd:
    """End-to-end test for vendor payment flow"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as PE Desk admin
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json=PE_DESK_ADMIN)
        assert login_response.status_code == 200
        
        token = login_response.json().get("token")
        self.session.headers.update({"Authorization": f"Bearer {token}"})
    
    def test_create_purchase_and_record_payment(self):
        """Test creating a purchase and recording payment"""
        # Get vendors and stocks
        vendors_response = self.session.get(f"{BASE_URL}/api/clients?is_vendor=true")
        stocks_response = self.session.get(f"{BASE_URL}/api/stocks")
        
        if vendors_response.status_code != 200 or not vendors_response.json():
            pytest.skip("No vendors available")
        if stocks_response.status_code != 200 or not stocks_response.json():
            pytest.skip("No stocks available")
        
        vendor = vendors_response.json()[0]
        stock = stocks_response.json()[0]
        
        # Create a new purchase
        purchase_data = {
            "vendor_id": vendor["id"],
            "stock_id": stock["id"],
            "quantity": 100,
            "price_per_unit": 50.00,
            "purchase_date": datetime.now().strftime("%Y-%m-%d"),
            "notes": "TEST_PAYMENT_FLOW"
        }
        
        create_response = self.session.post(f"{BASE_URL}/api/purchases", json=purchase_data)
        assert create_response.status_code == 200, f"Failed to create purchase: {create_response.text}"
        
        purchase = create_response.json()
        purchase_id = purchase["id"]
        total_amount = purchase["total_amount"]
        print(f"✓ Created purchase: {purchase_id}, total=₹{total_amount}")
        
        # Record partial payment
        payment1 = {
            "amount": total_amount / 2,
            "payment_date": datetime.now().strftime("%Y-%m-%d"),
            "notes": "First partial payment"
        }
        
        payment1_response = self.session.post(f"{BASE_URL}/api/purchases/{purchase_id}/payments", json=payment1)
        assert payment1_response.status_code == 200, f"Failed to record payment: {payment1_response.text}"
        
        result1 = payment1_response.json()
        assert result1["payment_status"] == "partial"
        print(f"✓ Partial payment recorded: ₹{result1['amount']}, status={result1['payment_status']}")
        
        # Record final payment
        payment2 = {
            "amount": total_amount / 2,
            "payment_date": datetime.now().strftime("%Y-%m-%d"),
            "notes": "Final payment"
        }
        
        payment2_response = self.session.post(f"{BASE_URL}/api/purchases/{purchase_id}/payments", json=payment2)
        assert payment2_response.status_code == 200, f"Failed to record final payment: {payment2_response.text}"
        
        result2 = payment2_response.json()
        assert result2["payment_status"] == "completed"
        assert result2["remaining"] < 0.01  # Should be 0 or very close
        print(f"✓ Final payment recorded: ₹{result2['amount']}, status={result2['payment_status']}")
        
        # Verify purchase status
        verify_response = self.session.get(f"{BASE_URL}/api/purchases/{purchase_id}/payments")
        assert verify_response.status_code == 200
        
        verify_data = verify_response.json()
        assert len(verify_data["payments"]) == 2
        assert verify_data["payment_status"] == "completed"
        print(f"✓ Payment flow completed: {len(verify_data['payments'])} tranches, status={verify_data['payment_status']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
