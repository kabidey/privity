"""
Test file for Booking Selling Price Validation Bug Fix
Tests that POST /api/bookings endpoint:
1. Rejects bookings without selling_price
2. Rejects bookings with selling_price=0
3. Accepts bookings with valid selling_price > 0
"""

import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
PE_DESK_EMAIL = "pedesk@smifs.com"
PE_DESK_PASSWORD = "Kutta@123"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for PE Desk user"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": PE_DESK_EMAIL,
        "password": PE_DESK_PASSWORD
    })
    assert response.status_code == 200, f"Login failed: {response.text}"
    return response.json()["token"]


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Get headers with auth token"""
    return {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    }


@pytest.fixture(scope="module")
def test_client_id(auth_headers):
    """Get an approved client ID for testing"""
    response = requests.get(f"{BASE_URL}/api/clients", headers=auth_headers)
    assert response.status_code == 200, f"Failed to get clients: {response.text}"
    clients = response.json()
    
    # Find an approved, active client
    for client in clients:
        if (not client.get("is_vendor") and 
            client.get("is_active") and 
            client.get("approval_status") == "approved" and
            not client.get("is_suspended")):
            return client["id"]
    
    pytest.skip("No approved active client found for testing")


@pytest.fixture(scope="module")
def test_stock_id(auth_headers):
    """Get a stock ID with available inventory for testing"""
    # Get stocks
    response = requests.get(f"{BASE_URL}/api/stocks", headers=auth_headers)
    assert response.status_code == 200, f"Failed to get stocks: {response.text}"
    stocks = response.json()
    
    # Get inventory
    inv_response = requests.get(f"{BASE_URL}/api/inventory", headers=auth_headers)
    assert inv_response.status_code == 200, f"Failed to get inventory: {inv_response.text}"
    inventory = inv_response.json()
    
    # Find a stock with available inventory
    for inv in inventory:
        if inv.get("available_quantity", 0) > 0:
            # Verify stock is not blocked
            for stock in stocks:
                if stock["id"] == inv["stock_id"] and stock.get("exchange") != "Blocked IPO/RTA":
                    return stock["id"]
    
    pytest.skip("No stock with available inventory found for testing")


class TestBookingSellingPriceValidation:
    """Test selling_price validation in booking creation"""
    
    def test_booking_without_selling_price_rejected(self, auth_headers, test_client_id, test_stock_id):
        """Test that booking without selling_price is rejected"""
        booking_data = {
            "client_id": test_client_id,
            "stock_id": test_stock_id,
            "quantity": 1,
            "booking_date": "2026-01-15",
            "status": "open"
            # No selling_price provided
        }
        
        response = requests.post(
            f"{BASE_URL}/api/bookings",
            headers=auth_headers,
            json=booking_data
        )
        
        # Should be rejected with 400 status
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        
        # Verify error message mentions selling price
        error_detail = response.json().get("detail", "")
        assert "selling price" in error_detail.lower() or "selling_price" in error_detail.lower(), \
            f"Error message should mention selling price: {error_detail}"
        print(f"✓ Booking without selling_price correctly rejected: {error_detail}")
    
    def test_booking_with_selling_price_zero_rejected(self, auth_headers, test_client_id, test_stock_id):
        """Test that booking with selling_price=0 is rejected"""
        booking_data = {
            "client_id": test_client_id,
            "stock_id": test_stock_id,
            "quantity": 1,
            "selling_price": 0,  # Zero selling price
            "booking_date": "2026-01-15",
            "status": "open"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/bookings",
            headers=auth_headers,
            json=booking_data
        )
        
        # Should be rejected with 400 status
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        
        # Verify error message mentions selling price must be > 0
        error_detail = response.json().get("detail", "")
        assert "greater than 0" in error_detail.lower() or "selling price" in error_detail.lower(), \
            f"Error message should mention selling price must be > 0: {error_detail}"
        print(f"✓ Booking with selling_price=0 correctly rejected: {error_detail}")
    
    def test_booking_with_negative_selling_price_rejected(self, auth_headers, test_client_id, test_stock_id):
        """Test that booking with negative selling_price is rejected"""
        booking_data = {
            "client_id": test_client_id,
            "stock_id": test_stock_id,
            "quantity": 1,
            "selling_price": -100,  # Negative selling price
            "booking_date": "2026-01-15",
            "status": "open"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/bookings",
            headers=auth_headers,
            json=booking_data
        )
        
        # Should be rejected with 400 status
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        
        error_detail = response.json().get("detail", "")
        print(f"✓ Booking with negative selling_price correctly rejected: {error_detail}")
    
    def test_booking_with_valid_selling_price_accepted(self, auth_headers, test_client_id, test_stock_id):
        """Test that booking with valid selling_price > 0 is accepted"""
        booking_data = {
            "client_id": test_client_id,
            "stock_id": test_stock_id,
            "quantity": 1,
            "selling_price": 150.00,  # Valid selling price
            "booking_date": "2026-01-15",
            "status": "open",
            "notes": "TEST_selling_price_validation"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/bookings",
            headers=auth_headers,
            json=booking_data
        )
        
        # Should be accepted with 200 status
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        booking = response.json()
        assert "id" in booking, "Response should contain booking id"
        assert "booking_number" in booking, "Response should contain booking_number"
        assert booking.get("selling_price") == 150.00, f"Selling price should be 150.00, got {booking.get('selling_price')}"
        
        print(f"✓ Booking with valid selling_price created: {booking.get('booking_number')}")
        
        # Cleanup - delete the test booking
        booking_id = booking["id"]
        delete_response = requests.delete(
            f"{BASE_URL}/api/bookings/{booking_id}",
            headers=auth_headers
        )
        if delete_response.status_code == 200:
            print(f"✓ Test booking cleaned up: {booking_id}")
    
    def test_booking_with_null_selling_price_rejected(self, auth_headers, test_client_id, test_stock_id):
        """Test that booking with explicit null selling_price is rejected"""
        booking_data = {
            "client_id": test_client_id,
            "stock_id": test_stock_id,
            "quantity": 1,
            "selling_price": None,  # Explicit null
            "booking_date": "2026-01-15",
            "status": "open"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/bookings",
            headers=auth_headers,
            json=booking_data
        )
        
        # Should be rejected with 400 status
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        
        error_detail = response.json().get("detail", "")
        print(f"✓ Booking with null selling_price correctly rejected: {error_detail}")


class TestBookingSellingPriceEdgeCases:
    """Test edge cases for selling_price validation"""
    
    def test_booking_with_very_small_selling_price_accepted(self, auth_headers, test_client_id, test_stock_id):
        """Test that booking with very small but positive selling_price is accepted"""
        booking_data = {
            "client_id": test_client_id,
            "stock_id": test_stock_id,
            "quantity": 1,
            "selling_price": 0.01,  # Very small but positive
            "booking_date": "2026-01-15",
            "status": "open",
            "notes": "TEST_small_selling_price"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/bookings",
            headers=auth_headers,
            json=booking_data
        )
        
        # Should be accepted with 200 status
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        booking = response.json()
        print(f"✓ Booking with small selling_price (0.01) created: {booking.get('booking_number')}")
        
        # Cleanup
        booking_id = booking["id"]
        requests.delete(f"{BASE_URL}/api/bookings/{booking_id}", headers=auth_headers)
    
    def test_booking_with_large_selling_price_accepted(self, auth_headers, test_client_id, test_stock_id):
        """Test that booking with large selling_price is accepted"""
        booking_data = {
            "client_id": test_client_id,
            "stock_id": test_stock_id,
            "quantity": 1,
            "selling_price": 999999.99,  # Large selling price
            "booking_date": "2026-01-15",
            "status": "open",
            "notes": "TEST_large_selling_price"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/bookings",
            headers=auth_headers,
            json=booking_data
        )
        
        # Should be accepted with 200 status
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        booking = response.json()
        print(f"✓ Booking with large selling_price (999999.99) created: {booking.get('booking_number')}")
        
        # Cleanup
        booking_id = booking["id"]
        requests.delete(f"{BASE_URL}/api/bookings/{booking_id}", headers=auth_headers)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
