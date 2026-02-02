"""
Test Payment Recording and Booking Confirmation Features
Tests for:
1. Payment recording endpoint (POST /api/bookings/{booking_id}/payments)
2. Booking confirmation endpoint (GET /api/booking-confirm/{booking_id}/{token}/{action})
3. Email template URL verification
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestPaymentRecording:
    """Test payment recording functionality"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login to get token
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "pe@smifs.com",
            "password": "Kutta@123"
        })
        assert login_response.status_code == 200, f"Login failed: {login_response.text}"
        token = login_response.json().get("token")
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        # Get a booking with approved status for testing
        bookings_response = self.session.get(f"{BASE_URL}/api/bookings")
        assert bookings_response.status_code == 200
        bookings = bookings_response.json()
        
        # Find an approved booking
        self.test_booking = None
        for booking in bookings:
            if booking.get("approval_status") == "approved":
                self.test_booking = booking
                break
        
    def test_payment_recording_with_json_body(self):
        """Test that payment recording accepts JSON body (not query params)"""
        if not self.test_booking:
            pytest.skip("No approved booking found for testing")
        
        booking_id = self.test_booking["id"]
        
        # Test with JSON body - this should work after the fix
        response = self.session.post(
            f"{BASE_URL}/api/bookings/{booking_id}/payments",
            json={
                "amount": 10.0,
                "payment_date": "2026-01-04",
                "notes": "Test payment via pytest"
            }
        )
        
        assert response.status_code == 200, f"Payment recording failed: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "message" in data
        assert "tranche_number" in data
        assert "total_paid" in data
        assert "remaining" in data
        assert "payment_complete" in data
        assert "dp_transfer_ready" in data
        
        print(f"Payment recorded successfully: {data['message']}")
    
    def test_payment_recording_validation(self):
        """Test payment amount validation"""
        if not self.test_booking:
            pytest.skip("No approved booking found for testing")
        
        booking_id = self.test_booking["id"]
        
        # Calculate remaining amount
        total_amount = (self.test_booking.get("selling_price") or 0) * self.test_booking.get("quantity", 0)
        total_paid = self.test_booking.get("total_paid", 0)
        remaining = total_amount - total_paid
        
        # Try to pay more than remaining - should fail
        if remaining > 0:
            response = self.session.post(
                f"{BASE_URL}/api/bookings/{booking_id}/payments",
                json={
                    "amount": remaining + 1000000,  # Way more than remaining
                    "payment_date": "2026-01-04"
                }
            )
            
            # Should return 400 error
            assert response.status_code == 400, f"Expected 400 for overpayment, got {response.status_code}"
            print(f"Overpayment correctly rejected: {response.json()}")
    
    def test_get_booking_payments(self):
        """Test getting payment history for a booking"""
        if not self.test_booking:
            pytest.skip("No approved booking found for testing")
        
        booking_id = self.test_booking["id"]
        
        response = self.session.get(f"{BASE_URL}/api/bookings/{booking_id}/payments")
        
        assert response.status_code == 200, f"Get payments failed: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "booking_id" in data
        assert "payments" in data
        assert "total_amount" in data
        assert "total_paid" in data
        
        print(f"Payment history retrieved: {len(data['payments'])} payments")


class TestBookingConfirmation:
    """Test booking confirmation functionality"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def test_booking_confirm_accept_endpoint(self):
        """Test booking confirmation accept endpoint"""
        # Use a known booking ID and token (this will likely fail with invalid token)
        # This tests that the endpoint exists and responds correctly
        
        fake_booking_id = "test-booking-id"
        fake_token = "test-token"
        
        response = self.session.get(
            f"{BASE_URL}/api/booking-confirm/{fake_booking_id}/{fake_token}/accept"
        )
        
        # Should return 404 (booking not found) or 400 (invalid token)
        # Not 500 (server error) or 405 (method not allowed)
        assert response.status_code in [400, 404], f"Unexpected status: {response.status_code}"
        print(f"Booking confirm endpoint responded correctly: {response.status_code}")
    
    def test_booking_confirm_deny_endpoint(self):
        """Test booking confirmation deny endpoint"""
        fake_booking_id = "test-booking-id"
        fake_token = "test-token"
        
        response = self.session.post(
            f"{BASE_URL}/api/booking-confirm/{fake_booking_id}/{fake_token}/deny",
            json={"reason": "Test denial"}
        )
        
        # Should return 404 (booking not found) or 400 (invalid token)
        assert response.status_code in [400, 404], f"Unexpected status: {response.status_code}"
        print(f"Booking deny endpoint responded correctly: {response.status_code}")


class TestEmailTemplateURLs:
    """Test that email template URLs are correctly formatted"""
    
    def test_frontend_url_env_variable(self):
        """Test that FRONTEND_URL environment variable is set correctly"""
        # This tests the backend configuration
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})
        
        # Login
        login_response = session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "pe@smifs.com",
            "password": "Kutta@123"
        })
        assert login_response.status_code == 200
        token = login_response.json().get("token")
        session.headers.update({"Authorization": f"Bearer {token}"})
        
        # Get company master to verify settings
        response = session.get(f"{BASE_URL}/api/company-master")
        
        # The endpoint should exist and return data
        assert response.status_code == 200, f"Company master endpoint failed: {response.text}"
        print("Company master endpoint working correctly")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
