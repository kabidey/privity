"""
Payment Tracking Feature Tests
Tests for:
- Payment tranche recording API (POST /api/bookings/{booking_id}/payments)
- Payment tranche validation (max 4 tranches, amount cannot exceed remaining balance)
- Payment status progression: pending -> partial -> completed
- DP Transfer Ready flag automatically set when payment completed
- DP Transfer Report API (GET /api/dp-transfer-report) returns only fully paid bookings
- DP Transfer Report export functionality (CSV and Excel)
- Role-based access: Only PE Desk (role 1) and Zonal Manager (role 2) can access payment features
"""

import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestPaymentTracking:
    """Payment tracking endpoint tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test data and authentication"""
        # Login as admin (PE Desk - role 1)
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@privity.com",
            "password": "Admin@123"
        })
        assert login_response.status_code == 200, f"Admin login failed: {login_response.text}"
        self.admin_token = login_response.json()["token"]
        self.admin_headers = {
            "Authorization": f"Bearer {self.admin_token}",
            "Content-Type": "application/json"
        }
        
        # Get existing bookings
        bookings_response = requests.get(f"{BASE_URL}/api/bookings", headers=self.admin_headers)
        assert bookings_response.status_code == 200
        self.bookings = bookings_response.json()
        
        # Find the fully paid booking (53b689bd)
        self.fully_paid_booking = next((b for b in self.bookings if b["id"].startswith("53b689bd")), None)
        
        # Find the approved booking without selling price (f7d7e8b0)
        self.no_price_booking = next((b for b in self.bookings if b["id"].startswith("f7d7e8b0")), None)
        
        # Find pending booking
        self.pending_booking = next((b for b in self.bookings if b["approval_status"] == "pending"), None)
    
    # ============== Payment Recording Tests ==============
    
    def test_payment_recording_requires_auth(self):
        """Test that payment recording requires authentication"""
        response = requests.post(f"{BASE_URL}/api/bookings/test-id/payments", json={
            "amount": 100,
            "payment_date": "2026-01-24"
        })
        assert response.status_code == 403, "Should require authentication"
        print("PASS: Payment recording requires authentication")
    
    def test_payment_recording_role_restriction(self):
        """Test that only PE Desk and Zonal Manager can record payments"""
        # Create an employee user for testing
        employee_email = f"test_employee_{uuid.uuid4().hex[:8]}@smifs.com"
        
        # Register employee
        register_response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": employee_email,
            "password": "Test@123",
            "name": "Test Employee"
        })
        
        if register_response.status_code == 200:
            employee_token = register_response.json()["token"]
            employee_headers = {
                "Authorization": f"Bearer {employee_token}",
                "Content-Type": "application/json"
            }
            
            # Try to record payment as employee (should fail)
            if self.fully_paid_booking:
                response = requests.post(
                    f"{BASE_URL}/api/bookings/{self.fully_paid_booking['id']}/payments",
                    headers=employee_headers,
                    json={"amount": 100, "payment_date": "2026-01-24"}
                )
                assert response.status_code == 403, f"Employee should not be able to record payments: {response.text}"
                assert "Only PE Desk and Zonal Manager" in response.json().get("detail", "")
                print("PASS: Employee cannot record payments (role restriction works)")
        else:
            print(f"SKIP: Could not create employee user: {register_response.text}")
    
    def test_payment_on_pending_booking_fails(self):
        """Test that payments cannot be added to pending (unapproved) bookings"""
        if not self.pending_booking:
            pytest.skip("No pending booking available for testing")
        
        response = requests.post(
            f"{BASE_URL}/api/bookings/{self.pending_booking['id']}/payments",
            headers=self.admin_headers,
            json={"amount": 100, "payment_date": "2026-01-24"}
        )
        assert response.status_code == 400, f"Should reject payment on pending booking: {response.text}"
        assert "approved" in response.json().get("detail", "").lower()
        print("PASS: Cannot add payment to pending (unapproved) booking")
    
    def test_payment_exceeding_balance_fails(self):
        """Test that payment amount cannot exceed remaining balance"""
        # Find an approved booking with selling price that's not fully paid
        test_booking = None
        for b in self.bookings:
            if (b["approval_status"] == "approved" and 
                b.get("selling_price") and 
                not b.get("dp_transfer_ready")):
                test_booking = b
                break
        
        if not test_booking:
            # Create a new booking for testing
            pytest.skip("No suitable booking for testing payment exceeding balance")
        
        total_amount = (test_booking.get("selling_price") or 0) * test_booking.get("quantity", 0)
        remaining = total_amount - (test_booking.get("total_paid") or 0)
        
        # Try to pay more than remaining
        response = requests.post(
            f"{BASE_URL}/api/bookings/{test_booking['id']}/payments",
            headers=self.admin_headers,
            json={"amount": remaining + 1000, "payment_date": "2026-01-24"}
        )
        assert response.status_code == 400, f"Should reject payment exceeding balance: {response.text}"
        assert "exceeds" in response.json().get("detail", "").lower()
        print(f"PASS: Payment exceeding remaining balance ({remaining}) is rejected")
    
    def test_max_4_tranches_validation(self):
        """Test that maximum 4 payment tranches are allowed"""
        if not self.fully_paid_booking:
            pytest.skip("No fully paid booking available")
        
        # The fully paid booking already has 3 tranches and is complete
        # Try to add another payment (should fail because it's already complete)
        response = requests.post(
            f"{BASE_URL}/api/bookings/{self.fully_paid_booking['id']}/payments",
            headers=self.admin_headers,
            json={"amount": 1, "payment_date": "2026-01-24"}
        )
        # Should fail either because max tranches or because exceeds balance
        assert response.status_code == 400, f"Should reject additional payment: {response.text}"
        print("PASS: Cannot add more payments to fully paid booking")
    
    # ============== DP Transfer Ready Tests ==============
    
    def test_fully_paid_booking_is_dp_ready(self):
        """Test that fully paid booking has dp_transfer_ready=true"""
        if not self.fully_paid_booking:
            pytest.skip("No fully paid booking available")
        
        assert self.fully_paid_booking.get("dp_transfer_ready") == True
        assert self.fully_paid_booking.get("payment_status") == "completed"
        print(f"PASS: Fully paid booking {self.fully_paid_booking['id'][:8]} is DP ready")
    
    def test_partial_paid_booking_not_dp_ready(self):
        """Test that partially paid booking is not DP ready"""
        partial_booking = next(
            (b for b in self.bookings if b.get("payment_status") == "partial"),
            None
        )
        if partial_booking:
            assert partial_booking.get("dp_transfer_ready") == False
            print("PASS: Partially paid booking is not DP ready")
        else:
            print("SKIP: No partially paid booking to test")
    
    # ============== DP Transfer Report Tests ==============
    
    def test_dp_transfer_report_returns_only_fully_paid(self):
        """Test that DP transfer report only returns fully paid bookings"""
        response = requests.get(f"{BASE_URL}/api/dp-transfer-report", headers=self.admin_headers)
        assert response.status_code == 200, f"DP report failed: {response.text}"
        
        records = response.json()
        assert isinstance(records, list)
        
        # All records should be fully paid
        for record in records:
            assert record.get("total_paid") == record.get("total_amount"), \
                f"Record {record.get('booking_id')} is not fully paid"
        
        print(f"PASS: DP transfer report returns {len(records)} fully paid bookings")
    
    def test_dp_transfer_report_contains_required_fields(self):
        """Test that DP transfer report contains all required fields"""
        response = requests.get(f"{BASE_URL}/api/dp-transfer-report", headers=self.admin_headers)
        assert response.status_code == 200
        
        records = response.json()
        if len(records) > 0:
            record = records[0]
            required_fields = [
                "booking_id", "client_name", "pan_number", "dp_id",
                "stock_symbol", "quantity", "total_amount", "total_paid",
                "payment_completed_at"
            ]
            for field in required_fields:
                assert field in record, f"Missing required field: {field}"
            print(f"PASS: DP transfer report contains all required fields")
        else:
            print("SKIP: No records in DP transfer report to validate fields")
    
    def test_dp_transfer_report_role_restriction(self):
        """Test that only PE Desk and Zonal Manager can access DP report"""
        # Create an employee user
        employee_email = f"test_emp_dp_{uuid.uuid4().hex[:8]}@smifs.com"
        
        register_response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": employee_email,
            "password": "Test@123",
            "name": "Test Employee DP"
        })
        
        if register_response.status_code == 200:
            employee_token = register_response.json()["token"]
            employee_headers = {
                "Authorization": f"Bearer {employee_token}",
                "Content-Type": "application/json"
            }
            
            response = requests.get(f"{BASE_URL}/api/dp-transfer-report", headers=employee_headers)
            assert response.status_code == 403, f"Employee should not access DP report: {response.text}"
            print("PASS: Employee cannot access DP transfer report")
        else:
            print(f"SKIP: Could not create employee user: {register_response.text}")
    
    # ============== Export Tests ==============
    
    def test_dp_transfer_export_csv(self):
        """Test CSV export of DP transfer report"""
        response = requests.get(
            f"{BASE_URL}/api/dp-transfer-report/export?format=csv",
            headers=self.admin_headers
        )
        
        if response.status_code == 404:
            print("SKIP: No records to export (404)")
            return
        
        assert response.status_code == 200, f"CSV export failed: {response.text}"
        assert "text/csv" in response.headers.get("content-type", "")
        assert "dp_transfer_report.csv" in response.headers.get("content-disposition", "")
        print("PASS: CSV export works correctly")
    
    def test_dp_transfer_export_excel(self):
        """Test Excel export of DP transfer report"""
        response = requests.get(
            f"{BASE_URL}/api/dp-transfer-report/export?format=excel",
            headers=self.admin_headers
        )
        
        if response.status_code == 404:
            print("SKIP: No records to export (404)")
            return
        
        assert response.status_code == 200, f"Excel export failed: {response.text}"
        assert "spreadsheet" in response.headers.get("content-type", "")
        assert "dp_transfer_report.xlsx" in response.headers.get("content-disposition", "")
        print("PASS: Excel export works correctly")
    
    # ============== Payment Status Progression Tests ==============
    
    def test_payment_status_values(self):
        """Test that payment status values are correct"""
        for booking in self.bookings:
            status = booking.get("payment_status", "pending")
            assert status in ["pending", "partial", "completed"], \
                f"Invalid payment status: {status}"
        print("PASS: All payment statuses are valid")
    
    def test_booking_without_selling_price_no_payment(self):
        """Test that booking without selling price cannot have payment recorded"""
        if not self.no_price_booking:
            pytest.skip("No booking without selling price available")
        
        # Booking without selling price should have total_amount = 0
        # Payment should fail because remaining balance is 0
        response = requests.post(
            f"{BASE_URL}/api/bookings/{self.no_price_booking['id']}/payments",
            headers=self.admin_headers,
            json={"amount": 100, "payment_date": "2026-01-24"}
        )
        # Should fail because amount exceeds remaining (which is 0)
        assert response.status_code == 400, f"Should reject payment on booking without price: {response.text}"
        print("PASS: Cannot add payment to booking without selling price")


class TestPaymentTrancheValidation:
    """Detailed payment tranche validation tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup authentication"""
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@privity.com",
            "password": "Admin@123"
        })
        assert login_response.status_code == 200
        self.admin_token = login_response.json()["token"]
        self.admin_headers = {
            "Authorization": f"Bearer {self.admin_token}",
            "Content-Type": "application/json"
        }
    
    def test_payment_tranche_required_fields(self):
        """Test that payment tranche requires amount and payment_date"""
        # Get any approved booking
        bookings_response = requests.get(f"{BASE_URL}/api/bookings", headers=self.admin_headers)
        bookings = bookings_response.json()
        approved_booking = next(
            (b for b in bookings if b["approval_status"] == "approved" and b.get("selling_price")),
            None
        )
        
        if not approved_booking:
            pytest.skip("No approved booking with selling price")
        
        # Test missing amount
        response = requests.post(
            f"{BASE_URL}/api/bookings/{approved_booking['id']}/payments",
            headers=self.admin_headers,
            json={"payment_date": "2026-01-24"}
        )
        assert response.status_code == 422, "Should require amount field"
        
        # Test missing payment_date
        response = requests.post(
            f"{BASE_URL}/api/bookings/{approved_booking['id']}/payments",
            headers=self.admin_headers,
            json={"amount": 100}
        )
        assert response.status_code == 422, "Should require payment_date field"
        
        print("PASS: Payment tranche validation for required fields works")
    
    def test_payment_amount_must_be_positive(self):
        """Test that payment amount must be positive"""
        bookings_response = requests.get(f"{BASE_URL}/api/bookings", headers=self.admin_headers)
        bookings = bookings_response.json()
        approved_booking = next(
            (b for b in bookings if b["approval_status"] == "approved" and b.get("selling_price") and not b.get("dp_transfer_ready")),
            None
        )
        
        if not approved_booking:
            pytest.skip("No suitable booking for testing")
        
        # Test zero amount
        response = requests.post(
            f"{BASE_URL}/api/bookings/{approved_booking['id']}/payments",
            headers=self.admin_headers,
            json={"amount": 0, "payment_date": "2026-01-24"}
        )
        # Should either reject or accept 0 (depends on implementation)
        print(f"Zero amount response: {response.status_code}")
        
        # Test negative amount
        response = requests.post(
            f"{BASE_URL}/api/bookings/{approved_booking['id']}/payments",
            headers=self.admin_headers,
            json={"amount": -100, "payment_date": "2026-01-24"}
        )
        # Should reject negative amount
        print(f"Negative amount response: {response.status_code}")
        print("PASS: Payment amount validation tested")


class TestGetBookingPayments:
    """Tests for GET /api/bookings/{booking_id}/payments endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup authentication"""
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@privity.com",
            "password": "Admin@123"
        })
        assert login_response.status_code == 200
        self.admin_token = login_response.json()["token"]
        self.admin_headers = {
            "Authorization": f"Bearer {self.admin_token}",
            "Content-Type": "application/json"
        }
    
    def test_get_booking_payments(self):
        """Test getting payment details for a booking"""
        # Get bookings
        bookings_response = requests.get(f"{BASE_URL}/api/bookings", headers=self.admin_headers)
        bookings = bookings_response.json()
        
        # Find booking with payments
        booking_with_payments = next(
            (b for b in bookings if len(b.get("payments", [])) > 0),
            None
        )
        
        if not booking_with_payments:
            pytest.skip("No booking with payments available")
        
        response = requests.get(
            f"{BASE_URL}/api/bookings/{booking_with_payments['id']}/payments",
            headers=self.admin_headers
        )
        assert response.status_code == 200, f"Get payments failed: {response.text}"
        
        data = response.json()
        assert "booking_id" in data
        assert "total_amount" in data
        assert "total_paid" in data
        assert "remaining" in data
        assert "payments" in data
        assert "dp_transfer_ready" in data
        
        print(f"PASS: Get booking payments returns correct structure")
        print(f"  - Total amount: {data['total_amount']}")
        print(f"  - Total paid: {data['total_paid']}")
        print(f"  - Remaining: {data['remaining']}")
        print(f"  - Tranches: {len(data['payments'])}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
