"""
Test RP Mapping Feature - PUT /api/bookings/{booking_id}/referral-partner

Tests for the ability to edit the Referral Partner (RP) mapping on bookings.
Users should be able to change or remove the RP assigned to a booking after creation,
as long as the stock has not been transferred.
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
PE_DESK_EMAIL = "pe@smifs.com"
PE_DESK_PASSWORD = "Kutta@123"


class TestRPMappingFeature:
    """Tests for RP Mapping edit functionality"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        self.pe_token = None
        self.booking_id = None
        self.rp_id = None
    
    def login_pe_desk(self):
        """Login as PE Desk Super Admin"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": PE_DESK_EMAIL,
            "password": PE_DESK_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        self.pe_token = data.get("access_token")
        self.session.headers.update({"Authorization": f"Bearer {self.pe_token}"})
        return self.pe_token
    
    def get_test_booking(self):
        """Get a booking that can be used for RP mapping tests"""
        response = self.session.get(f"{BASE_URL}/api/bookings")
        assert response.status_code == 200, f"Failed to get bookings: {response.text}"
        bookings = response.json()
        
        # Find a booking that is not BP booking, not transferred, not voided
        for booking in bookings:
            if (not booking.get("is_bp_booking") and 
                not booking.get("stock_transferred") and 
                not booking.get("is_voided")):
                return booking
        
        return None
    
    def get_approved_rp(self):
        """Get an approved RP for testing"""
        response = self.session.get(f"{BASE_URL}/api/referral-partners-approved")
        assert response.status_code == 200, f"Failed to get RPs: {response.text}"
        rps = response.json()
        
        if rps and len(rps) > 0:
            return rps[0]
        return None
    
    # ============== API ENDPOINT TESTS ==============
    
    def test_01_login_pe_desk(self):
        """Test PE Desk login"""
        token = self.login_pe_desk()
        assert token is not None, "Failed to get access token"
        print(f"SUCCESS: PE Desk logged in")
    
    def test_02_get_bookings_list(self):
        """Test getting bookings list"""
        self.login_pe_desk()
        response = self.session.get(f"{BASE_URL}/api/bookings")
        assert response.status_code == 200, f"Failed to get bookings: {response.text}"
        bookings = response.json()
        assert isinstance(bookings, list), "Bookings should be a list"
        print(f"SUCCESS: Got {len(bookings)} bookings")
    
    def test_03_get_approved_rps(self):
        """Test getting approved RPs"""
        self.login_pe_desk()
        response = self.session.get(f"{BASE_URL}/api/referral-partners-approved")
        assert response.status_code == 200, f"Failed to get RPs: {response.text}"
        rps = response.json()
        assert isinstance(rps, list), "RPs should be a list"
        print(f"SUCCESS: Got {len(rps)} approved RPs")
    
    def test_04_update_rp_mapping_add_rp(self):
        """Test adding RP to a booking that has no RP"""
        self.login_pe_desk()
        
        booking = self.get_test_booking()
        if not booking:
            pytest.skip("No suitable booking found for testing")
        
        rp = self.get_approved_rp()
        if not rp:
            pytest.skip("No approved RP found for testing")
        
        booking_id = booking.get("id")
        rp_id = rp.get("id")
        
        # Update RP mapping
        response = self.session.put(
            f"{BASE_URL}/api/bookings/{booking_id}/referral-partner",
            params={
                "referral_partner_id": rp_id,
                "rp_revenue_share_percent": 20.0
            }
        )
        
        assert response.status_code == 200, f"Failed to update RP mapping: {response.text}"
        data = response.json()
        
        assert data.get("message") == "Referral partner mapping updated", f"Unexpected message: {data}"
        assert data.get("referral_partner_id") == rp_id, "RP ID mismatch"
        assert data.get("rp_revenue_share_percent") == 20.0, "RP share mismatch"
        
        print(f"SUCCESS: Added RP {rp.get('rp_code')} to booking {booking.get('booking_number')}")
    
    def test_05_update_rp_mapping_change_share(self):
        """Test changing RP revenue share percentage"""
        self.login_pe_desk()
        
        booking = self.get_test_booking()
        if not booking:
            pytest.skip("No suitable booking found for testing")
        
        rp = self.get_approved_rp()
        if not rp:
            pytest.skip("No approved RP found for testing")
        
        booking_id = booking.get("id")
        rp_id = rp.get("id")
        
        # Update RP mapping with different share
        response = self.session.put(
            f"{BASE_URL}/api/bookings/{booking_id}/referral-partner",
            params={
                "referral_partner_id": rp_id,
                "rp_revenue_share_percent": 15.0
            }
        )
        
        assert response.status_code == 200, f"Failed to update RP share: {response.text}"
        data = response.json()
        
        assert data.get("rp_revenue_share_percent") == 15.0, "RP share not updated"
        print(f"SUCCESS: Changed RP share to 15%")
    
    def test_06_update_rp_mapping_remove_rp(self):
        """Test removing RP from a booking"""
        self.login_pe_desk()
        
        booking = self.get_test_booking()
        if not booking:
            pytest.skip("No suitable booking found for testing")
        
        booking_id = booking.get("id")
        
        # Remove RP mapping (no referral_partner_id parameter)
        response = self.session.put(
            f"{BASE_URL}/api/bookings/{booking_id}/referral-partner"
        )
        
        assert response.status_code == 200, f"Failed to remove RP: {response.text}"
        data = response.json()
        
        assert data.get("referral_partner_id") is None, "RP should be removed"
        assert data.get("rp_revenue_share_percent") == 0, "RP share should be 0"
        
        print(f"SUCCESS: Removed RP from booking {booking.get('booking_number')}")
    
    def test_07_verify_booking_after_rp_update(self):
        """Test that booking reflects RP changes after update"""
        self.login_pe_desk()
        
        booking = self.get_test_booking()
        if not booking:
            pytest.skip("No suitable booking found for testing")
        
        rp = self.get_approved_rp()
        if not rp:
            pytest.skip("No approved RP found for testing")
        
        booking_id = booking.get("id")
        rp_id = rp.get("id")
        
        # Add RP
        self.session.put(
            f"{BASE_URL}/api/bookings/{booking_id}/referral-partner",
            params={
                "referral_partner_id": rp_id,
                "rp_revenue_share_percent": 25.0
            }
        )
        
        # Get booking and verify
        response = self.session.get(f"{BASE_URL}/api/bookings/{booking_id}")
        assert response.status_code == 200, f"Failed to get booking: {response.text}"
        
        updated_booking = response.json()
        assert updated_booking.get("referral_partner_id") == rp_id, "RP ID not persisted"
        assert updated_booking.get("rp_revenue_share_percent") == 25.0, "RP share not persisted"
        assert updated_booking.get("employee_revenue_share_percent") == 75.0, "Employee share not calculated correctly"
        
        print(f"SUCCESS: Booking correctly reflects RP update (RP: 25%, Employee: 75%)")
    
    def test_08_rp_share_max_30_percent(self):
        """Test that RP share cannot exceed 30%"""
        self.login_pe_desk()
        
        booking = self.get_test_booking()
        if not booking:
            pytest.skip("No suitable booking found for testing")
        
        rp = self.get_approved_rp()
        if not rp:
            pytest.skip("No approved RP found for testing")
        
        booking_id = booking.get("id")
        rp_id = rp.get("id")
        
        # Try to set RP share to 50% (should be capped or rejected)
        response = self.session.put(
            f"{BASE_URL}/api/bookings/{booking_id}/referral-partner",
            params={
                "referral_partner_id": rp_id,
                "rp_revenue_share_percent": 50.0
            }
        )
        
        # The API should either cap at 30% or return an error
        if response.status_code == 200:
            data = response.json()
            # If accepted, share should be capped at 30%
            assert data.get("rp_revenue_share_percent") <= 30.0, "RP share should be capped at 30%"
            print(f"SUCCESS: RP share capped at {data.get('rp_revenue_share_percent')}%")
        else:
            # If rejected, that's also acceptable
            assert response.status_code == 400, f"Unexpected status: {response.status_code}"
            print(f"SUCCESS: API rejected RP share > 30%")
    
    def test_09_cannot_update_transferred_booking(self):
        """Test that RP cannot be changed after stock transfer"""
        self.login_pe_desk()
        
        # Get all bookings and find one that is transferred
        response = self.session.get(f"{BASE_URL}/api/bookings")
        assert response.status_code == 200
        bookings = response.json()
        
        transferred_booking = None
        for booking in bookings:
            if booking.get("stock_transferred"):
                transferred_booking = booking
                break
        
        if not transferred_booking:
            pytest.skip("No transferred booking found for testing")
        
        rp = self.get_approved_rp()
        if not rp:
            pytest.skip("No approved RP found for testing")
        
        # Try to update RP on transferred booking
        response = self.session.put(
            f"{BASE_URL}/api/bookings/{transferred_booking['id']}/referral-partner",
            params={
                "referral_partner_id": rp.get("id"),
                "rp_revenue_share_percent": 20.0
            }
        )
        
        assert response.status_code == 400, f"Should reject update on transferred booking: {response.text}"
        assert "transferred" in response.json().get("detail", "").lower(), "Error should mention transfer"
        
        print(f"SUCCESS: API correctly rejected RP update on transferred booking")
    
    def test_10_cannot_update_bp_booking(self):
        """Test that RP cannot be assigned to BP booking"""
        self.login_pe_desk()
        
        # Get all bookings and find a BP booking
        response = self.session.get(f"{BASE_URL}/api/bookings")
        assert response.status_code == 200
        bookings = response.json()
        
        bp_booking = None
        for booking in bookings:
            if booking.get("is_bp_booking"):
                bp_booking = booking
                break
        
        if not bp_booking:
            pytest.skip("No BP booking found for testing")
        
        rp = self.get_approved_rp()
        if not rp:
            pytest.skip("No approved RP found for testing")
        
        # Try to update RP on BP booking
        response = self.session.put(
            f"{BASE_URL}/api/bookings/{bp_booking['id']}/referral-partner",
            params={
                "referral_partner_id": rp.get("id"),
                "rp_revenue_share_percent": 20.0
            }
        )
        
        assert response.status_code == 400, f"Should reject RP on BP booking: {response.text}"
        assert "business partner" in response.json().get("detail", "").lower(), "Error should mention BP"
        
        print(f"SUCCESS: API correctly rejected RP assignment on BP booking")
    
    def test_11_invalid_rp_id(self):
        """Test that invalid RP ID is rejected"""
        self.login_pe_desk()
        
        booking = self.get_test_booking()
        if not booking:
            pytest.skip("No suitable booking found for testing")
        
        # Try to set invalid RP ID
        response = self.session.put(
            f"{BASE_URL}/api/bookings/{booking['id']}/referral-partner",
            params={
                "referral_partner_id": "invalid-rp-id-12345",
                "rp_revenue_share_percent": 20.0
            }
        )
        
        assert response.status_code == 404, f"Should reject invalid RP ID: {response.text}"
        
        print(f"SUCCESS: API correctly rejected invalid RP ID")
    
    def test_12_invalid_booking_id(self):
        """Test that invalid booking ID returns 404"""
        self.login_pe_desk()
        
        rp = self.get_approved_rp()
        if not rp:
            pytest.skip("No approved RP found for testing")
        
        # Try to update non-existent booking
        response = self.session.put(
            f"{BASE_URL}/api/bookings/invalid-booking-id-12345/referral-partner",
            params={
                "referral_partner_id": rp.get("id"),
                "rp_revenue_share_percent": 20.0
            }
        )
        
        assert response.status_code == 404, f"Should return 404 for invalid booking: {response.text}"
        
        print(f"SUCCESS: API correctly returned 404 for invalid booking ID")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
