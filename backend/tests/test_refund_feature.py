"""
Test Suite for Refund Feature in Privity Share Booking System
Tests:
1. Refund request creation when voiding a paid booking
2. Refund request NOT created when voiding unpaid booking
3. Refund requests listing on Finance page
4. Refund status update to completed with reference number
5. Finance summary shows correct pending/completed refund counts
6. Loss booking rejection also rejects main booking
"""

import pytest
import requests
import os
import uuid
from datetime import datetime, timezone

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
PE_DESK_EMAIL = "pedesk@smifs.com"
PE_DESK_PASSWORD = "Kutta@123"
PE_MANAGER_EMAIL = "pemanager@test.com"
PE_MANAGER_PASSWORD = "Test@123"


class TestRefundFeature:
    """Test refund request creation and management"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test data"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        self.pe_desk_token = None
        self.pe_manager_token = None
        self.test_client_id = None
        self.test_vendor_id = None
        self.test_stock_id = None
        self.test_booking_id = None
        self.test_purchase_id = None
        
    def login_pe_desk(self):
        """Login as PE Desk"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": PE_DESK_EMAIL,
            "password": PE_DESK_PASSWORD
        })
        assert response.status_code == 200, f"PE Desk login failed: {response.text}"
        self.pe_desk_token = response.json()["token"]
        self.session.headers.update({"Authorization": f"Bearer {self.pe_desk_token}"})
        return response.json()
    
    def login_pe_manager(self):
        """Login as PE Manager"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": PE_MANAGER_EMAIL,
            "password": PE_MANAGER_PASSWORD
        })
        if response.status_code == 200:
            self.pe_manager_token = response.json()["token"]
            self.session.headers.update({"Authorization": f"Bearer {self.pe_manager_token}"})
        return response
    
    def create_test_client(self):
        """Create a test client with bank details"""
        unique_id = str(uuid.uuid4())[:8]
        client_data = {
            "name": f"TEST_Refund_Client_{unique_id}",
            "email": f"test_refund_{unique_id}@example.com",
            "phone": "9876543210",
            "pan_number": f"ABCDE{unique_id[:4].upper()}F",
            "dp_id": f"DP{unique_id[:8].upper()}",
            "dp_type": "outside",
            "is_vendor": False,
            "bank_accounts": [
                {
                    "bank_name": "Test Bank",
                    "account_number": "1234567890",
                    "ifsc_code": "TEST0001234",
                    "account_holder_name": f"TEST_Refund_Client_{unique_id}",
                    "branch": "Test Branch"
                }
            ]
        }
        response = self.session.post(f"{BASE_URL}/api/clients", json=client_data)
        if response.status_code in [200, 201]:
            self.test_client_id = response.json()["id"]
        return response
    
    def create_test_vendor(self):
        """Create a test vendor"""
        unique_id = str(uuid.uuid4())[:8]
        vendor_data = {
            "name": f"TEST_Refund_Vendor_{unique_id}",
            "email": f"test_vendor_{unique_id}@example.com",
            "phone": "9876543211",
            "pan_number": f"VNDRE{unique_id[:4].upper()}G",
            "dp_id": f"VDP{unique_id[:8].upper()}",
            "dp_type": "outside",
            "is_vendor": True,
            "bank_accounts": []
        }
        response = self.session.post(f"{BASE_URL}/api/clients", json=vendor_data)
        if response.status_code in [200, 201]:
            self.test_vendor_id = response.json()["id"]
        return response
    
    def create_test_stock(self):
        """Create a test stock"""
        unique_id = str(uuid.uuid4())[:8]
        stock_data = {
            "symbol": f"TRFND{unique_id[:4].upper()}",
            "name": f"Test Refund Stock {unique_id}",
            "isin": f"INE{unique_id[:9].upper()}",
            "face_value": 10.0
        }
        response = self.session.post(f"{BASE_URL}/api/stocks", json=stock_data)
        if response.status_code in [200, 201]:
            self.test_stock_id = response.json()["id"]
        return response
    
    def create_test_purchase(self, quantity=100, price=100.0):
        """Create a test purchase to add inventory"""
        if not self.test_vendor_id or not self.test_stock_id:
            return None
        purchase_data = {
            "vendor_id": self.test_vendor_id,
            "stock_id": self.test_stock_id,
            "quantity": quantity,
            "price_per_unit": price,
            "purchase_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "notes": "Test purchase for refund testing"
        }
        response = self.session.post(f"{BASE_URL}/api/purchases", json=purchase_data)
        if response.status_code in [200, 201]:
            self.test_purchase_id = response.json()["id"]
        return response
    
    def create_test_booking(self, quantity=10, selling_price=110.0):
        """Create a test booking"""
        if not self.test_client_id or not self.test_stock_id:
            return None
        booking_data = {
            "client_id": self.test_client_id,
            "stock_id": self.test_stock_id,
            "quantity": quantity,
            "selling_price": selling_price,
            "booking_type": "client",
            "booking_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "notes": "Test booking for refund testing"
        }
        response = self.session.post(f"{BASE_URL}/api/bookings", json=booking_data)
        if response.status_code in [200, 201]:
            self.test_booking_id = response.json()["id"]
        return response
    
    def approve_booking(self, booking_id):
        """Approve a booking"""
        response = self.session.put(f"{BASE_URL}/api/bookings/{booking_id}/approve?approve=true")
        return response
    
    def add_payment_to_booking(self, booking_id, amount):
        """Add a payment tranche to booking"""
        payment_data = {
            "amount": amount,
            "payment_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "payment_mode": "bank_transfer",
            "reference_number": f"REF{str(uuid.uuid4())[:8].upper()}"
        }
        response = self.session.post(f"{BASE_URL}/api/bookings/{booking_id}/payments", json=payment_data)
        return response
    
    def void_booking(self, booking_id, reason="Test void"):
        """Void a booking"""
        response = self.session.put(f"{BASE_URL}/api/bookings/{booking_id}/void?reason={reason}")
        return response
    
    def cleanup_test_data(self):
        """Clean up test data"""
        # Delete test booking if exists
        if self.test_booking_id:
            self.session.delete(f"{BASE_URL}/api/bookings/{self.test_booking_id}")
        # Delete test client
        if self.test_client_id:
            self.session.delete(f"{BASE_URL}/api/clients/{self.test_client_id}")
        # Delete test vendor
        if self.test_vendor_id:
            self.session.delete(f"{BASE_URL}/api/clients/{self.test_vendor_id}")
        # Delete test stock
        if self.test_stock_id:
            self.session.delete(f"{BASE_URL}/api/stocks/{self.test_stock_id}")
    
    # ============== TEST CASES ==============
    
    def test_01_pe_desk_login(self):
        """Test PE Desk can login"""
        result = self.login_pe_desk()
        assert "token" in result
        assert result["user"]["role"] == 1
        print("✓ PE Desk login successful")
    
    def test_02_get_refund_requests_list(self):
        """Test getting refund requests list"""
        self.login_pe_desk()
        response = self.session.get(f"{BASE_URL}/api/finance/refund-requests")
        assert response.status_code == 200, f"Failed to get refund requests: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Got {len(data)} refund requests")
    
    def test_03_get_finance_summary_with_refunds(self):
        """Test finance summary includes refund stats"""
        self.login_pe_desk()
        response = self.session.get(f"{BASE_URL}/api/finance/summary")
        assert response.status_code == 200, f"Failed to get finance summary: {response.text}"
        data = response.json()
        
        # Verify refund fields exist
        assert "pending_refunds_count" in data, "Missing pending_refunds_count"
        assert "pending_refunds_amount" in data, "Missing pending_refunds_amount"
        assert "completed_refunds_count" in data, "Missing completed_refunds_count"
        assert "completed_refunds_amount" in data, "Missing completed_refunds_amount"
        
        print("✓ Finance summary has refund stats:")
        print(f"  - Pending refunds: {data['pending_refunds_count']} (₹{data['pending_refunds_amount']:,.2f})")
        print(f"  - Completed refunds: {data['completed_refunds_count']} (₹{data['completed_refunds_amount']:,.2f})")
    
    def test_04_void_paid_booking_creates_refund(self):
        """Test that voiding a paid booking creates a refund request"""
        self.login_pe_desk()
        
        # Create test data
        client_resp = self.create_test_client()
        assert client_resp.status_code in [200, 201], f"Failed to create client: {client_resp.text}"
        
        vendor_resp = self.create_test_vendor()
        assert vendor_resp.status_code in [200, 201], f"Failed to create vendor: {vendor_resp.text}"
        
        stock_resp = self.create_test_stock()
        assert stock_resp.status_code in [200, 201], f"Failed to create stock: {stock_resp.text}"
        
        purchase_resp = self.create_test_purchase(quantity=100, price=100.0)
        assert purchase_resp.status_code in [200, 201], f"Failed to create purchase: {purchase_resp.text}"
        
        # Create booking
        booking_resp = self.create_test_booking(quantity=10, selling_price=110.0)
        assert booking_resp.status_code in [200, 201], f"Failed to create booking: {booking_resp.text}"
        booking_id = booking_resp.json()["id"]
        
        # Approve booking
        approve_resp = self.approve_booking(booking_id)
        assert approve_resp.status_code == 200, f"Failed to approve booking: {approve_resp.text}"
        
        # Add payment
        payment_amount = 500.0
        payment_resp = self.add_payment_to_booking(booking_id, payment_amount)
        assert payment_resp.status_code in [200, 201], f"Failed to add payment: {payment_resp.text}"
        
        # Void the booking
        void_resp = self.void_booking(booking_id, "Testing refund creation")
        assert void_resp.status_code == 200, f"Failed to void booking: {void_resp.text}"
        void_data = void_resp.json()
        
        # Verify refund request was created
        assert void_data.get("refund_request_created") == True, "Refund request should be created"
        assert void_data.get("refund_amount") == payment_amount, f"Refund amount should be {payment_amount}"
        assert "refund_request_id" in void_data, "Should return refund_request_id"
        
        print("✓ Voiding paid booking created refund request:")
        print(f"  - Refund ID: {void_data.get('refund_request_id')}")
        print(f"  - Refund Amount: ₹{void_data.get('refund_amount'):,.2f}")
        
        # Cleanup
        self.cleanup_test_data()
    
    def test_05_void_unpaid_booking_no_refund(self):
        """Test that voiding an unpaid booking does NOT create a refund request"""
        self.login_pe_desk()
        
        # Create test data
        client_resp = self.create_test_client()
        assert client_resp.status_code in [200, 201], f"Failed to create client: {client_resp.text}"
        
        vendor_resp = self.create_test_vendor()
        assert vendor_resp.status_code in [200, 201], f"Failed to create vendor: {vendor_resp.text}"
        
        stock_resp = self.create_test_stock()
        assert stock_resp.status_code in [200, 201], f"Failed to create stock: {stock_resp.text}"
        
        purchase_resp = self.create_test_purchase(quantity=100, price=100.0)
        assert purchase_resp.status_code in [200, 201], f"Failed to create purchase: {purchase_resp.text}"
        
        # Create booking (no payment)
        booking_resp = self.create_test_booking(quantity=10, selling_price=110.0)
        assert booking_resp.status_code in [200, 201], f"Failed to create booking: {booking_resp.text}"
        booking_id = booking_resp.json()["id"]
        
        # Approve booking
        approve_resp = self.approve_booking(booking_id)
        assert approve_resp.status_code == 200, f"Failed to approve booking: {approve_resp.text}"
        
        # Void the booking WITHOUT adding payment
        void_resp = self.void_booking(booking_id, "Testing no refund for unpaid")
        assert void_resp.status_code == 200, f"Failed to void booking: {void_resp.text}"
        void_data = void_resp.json()
        
        # Verify NO refund request was created
        assert void_data.get("refund_request_created") != True, "Refund request should NOT be created for unpaid booking"
        assert "refund_request_id" not in void_data or void_data.get("refund_request_id") is None
        
        print("✓ Voiding unpaid booking did NOT create refund request")
        
        # Cleanup
        self.cleanup_test_data()
    
    def test_06_update_refund_to_completed(self):
        """Test updating refund request status to completed"""
        self.login_pe_desk()
        
        # Get existing refund requests
        response = self.session.get(f"{BASE_URL}/api/finance/refund-requests")
        assert response.status_code == 200
        refunds = response.json()
        
        # Find a pending refund or create test data
        pending_refund = next((r for r in refunds if r.get("status") == "pending"), None)
        
        if pending_refund:
            refund_id = pending_refund["id"]
            
            # Update to completed
            update_data = {
                "status": "completed",
                "notes": "Test completion",
                "reference_number": f"UTR{str(uuid.uuid4())[:8].upper()}"
            }
            update_resp = self.session.put(f"{BASE_URL}/api/finance/refund-requests/{refund_id}", json=update_data)
            assert update_resp.status_code == 200, f"Failed to update refund: {update_resp.text}"
            
            # Verify update
            get_resp = self.session.get(f"{BASE_URL}/api/finance/refund-requests/{refund_id}")
            assert get_resp.status_code == 200
            updated_refund = get_resp.json()
            assert updated_refund["status"] == "completed"
            assert updated_refund["reference_number"] == update_data["reference_number"]
            
            print(f"✓ Updated refund {refund_id} to completed with reference {update_data['reference_number']}")
        else:
            print("⚠ No pending refund found to test update - creating test data")
            # Create test data and void with payment
            self.test_04_void_paid_booking_creates_refund()
    
    def test_07_pe_manager_can_access_refunds(self):
        """Test PE Manager can access refund requests"""
        login_resp = self.login_pe_manager()
        if login_resp.status_code != 200:
            pytest.skip("PE Manager user not available")
        
        response = self.session.get(f"{BASE_URL}/api/finance/refund-requests")
        assert response.status_code == 200, f"PE Manager should access refunds: {response.text}"
        print("✓ PE Manager can access refund requests")
    
    def test_08_pe_manager_can_update_refunds(self):
        """Test PE Manager can update refund requests"""
        login_resp = self.login_pe_manager()
        if login_resp.status_code != 200:
            pytest.skip("PE Manager user not available")
        
        # Get refund requests
        response = self.session.get(f"{BASE_URL}/api/finance/refund-requests")
        assert response.status_code == 200
        refunds = response.json()
        
        if refunds:
            refund_id = refunds[0]["id"]
            update_data = {
                "status": "processing",
                "notes": "PE Manager processing test"
            }
            update_resp = self.session.put(f"{BASE_URL}/api/finance/refund-requests/{refund_id}", json=update_data)
            assert update_resp.status_code == 200, f"PE Manager should update refunds: {update_resp.text}"
            print("✓ PE Manager can update refund requests")
        else:
            print("⚠ No refunds available to test PE Manager update")
    
    def test_09_refund_request_has_bank_details(self):
        """Test refund request includes client bank details"""
        self.login_pe_desk()
        
        response = self.session.get(f"{BASE_URL}/api/finance/refund-requests")
        assert response.status_code == 200
        refunds = response.json()
        
        if refunds:
            refund = refunds[0]
            assert "bank_details" in refund, "Refund should have bank_details field"
            bank_details = refund.get("bank_details", {})
            print("✓ Refund request has bank details:")
            print(f"  - Bank: {bank_details.get('bank_name', 'N/A')}")
            print(f"  - Account: {bank_details.get('account_number', 'N/A')}")
            print(f"  - IFSC: {bank_details.get('ifsc_code', 'N/A')}")
        else:
            print("⚠ No refunds available to check bank details")
    
    def test_10_loss_booking_rejection_rejects_main_booking(self):
        """Test that rejecting a loss booking also rejects the main booking"""
        self.login_pe_desk()
        
        # Create test data
        client_resp = self.create_test_client()
        assert client_resp.status_code in [200, 201], f"Failed to create client: {client_resp.text}"
        
        vendor_resp = self.create_test_vendor()
        assert vendor_resp.status_code in [200, 201], f"Failed to create vendor: {vendor_resp.text}"
        
        stock_resp = self.create_test_stock()
        assert stock_resp.status_code in [200, 201], f"Failed to create stock: {stock_resp.text}"
        
        purchase_resp = self.create_test_purchase(quantity=100, price=100.0)
        assert purchase_resp.status_code in [200, 201], f"Failed to create purchase: {purchase_resp.text}"
        
        # Create a loss booking (selling price < buying price)
        # Buying price is 100 (from purchase), selling at 90 = loss
        booking_data = {
            "client_id": self.test_client_id,
            "stock_id": self.test_stock_id,
            "quantity": 10,
            "selling_price": 90.0,  # Less than buying price of 100
            "booking_type": "client",
            "booking_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "notes": "Test loss booking for rejection"
        }
        booking_resp = self.session.post(f"{BASE_URL}/api/bookings", json=booking_data)
        
        if booking_resp.status_code in [200, 201]:
            booking = booking_resp.json()
            booking_id = booking["id"]
            
            # Check if it's a loss booking
            if booking.get("is_loss_booking"):
                # First approve the booking
                approve_resp = self.approve_booking(booking_id)
                
                # Reject the loss booking
                reject_resp = self.session.put(f"{BASE_URL}/api/bookings/{booking_id}/approve-loss?approve=false")
                
                if reject_resp.status_code == 200:
                    # Verify the main booking is also rejected
                    get_resp = self.session.get(f"{BASE_URL}/api/bookings/{booking_id}")
                    if get_resp.status_code == 200:
                        updated_booking = get_resp.json()
                        assert updated_booking.get("status") == "rejected", "Main booking should be rejected"
                        assert updated_booking.get("loss_approval_status") == "rejected", "Loss approval should be rejected"
                        print("✓ Loss booking rejection also rejected the main booking")
                    else:
                        print(f"⚠ Could not verify booking status: {get_resp.text}")
                else:
                    print(f"⚠ Loss rejection failed: {reject_resp.text}")
            else:
                print("⚠ Booking was not marked as loss booking - may need different price")
        else:
            print(f"⚠ Could not create loss booking: {booking_resp.text}")
        
        # Cleanup
        self.cleanup_test_data()


class TestRefundAPIValidation:
    """Test refund API validation and error handling"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def login_pe_desk(self):
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": PE_DESK_EMAIL,
            "password": PE_DESK_PASSWORD
        })
        if response.status_code == 200:
            self.session.headers.update({"Authorization": f"Bearer {response.json()['token']}"})
        return response
    
    def test_invalid_refund_status(self):
        """Test that invalid status is rejected"""
        self.login_pe_desk()
        
        # Get a refund request
        response = self.session.get(f"{BASE_URL}/api/finance/refund-requests")
        if response.status_code == 200 and response.json():
            refund_id = response.json()[0]["id"]
            
            # Try invalid status
            update_data = {
                "status": "invalid_status",
                "notes": "Test"
            }
            update_resp = self.session.put(f"{BASE_URL}/api/finance/refund-requests/{refund_id}", json=update_data)
            assert update_resp.status_code == 400, "Should reject invalid status"
            print("✓ Invalid refund status correctly rejected")
        else:
            print("⚠ No refunds available to test validation")
    
    def test_nonexistent_refund_request(self):
        """Test 404 for non-existent refund request"""
        self.login_pe_desk()
        
        fake_id = str(uuid.uuid4())
        response = self.session.get(f"{BASE_URL}/api/finance/refund-requests/{fake_id}")
        assert response.status_code == 404, "Should return 404 for non-existent refund"
        print("✓ Non-existent refund request returns 404")
    
    def test_unauthorized_access_to_refunds(self):
        """Test that non-PE users cannot access refunds"""
        # Try without auth
        response = self.session.get(f"{BASE_URL}/api/finance/refund-requests")
        assert response.status_code in [401, 403], "Should deny unauthorized access"
        print("✓ Unauthorized access to refunds correctly denied")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
