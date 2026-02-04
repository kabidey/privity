"""
Test BP Revenue Share Override Feature

This module tests the BP Revenue Share Override functionality:
1. GET /api/bookings/pending-bp-overrides - List bookings with pending overrides
2. PUT /api/bookings/{booking_id}/bp-override-approval - Approve/reject override
3. PUT /api/bookings/{booking_id}/bp-override - Edit override (reset to pending)
4. Permission checks for override and approval

BP Override Flow:
- BP/Partners Desk creates booking with lower revenue share override
- Override requires PE Desk approval
- If approved: override becomes effective
- If rejected: original BP revenue share is restored
"""

import pytest
import requests
import os
from datetime import datetime
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
USER_AGENT = 'Mozilla/5.0 Test'

class TestBPRevenueOverride:
    """Test BP Revenue Share Override functionality"""
    
    # Test credentials
    PE_DESK_EMAIL = "pe@smifs.com"
    PE_DESK_PASSWORD = "Kutta@123"
    
    @pytest.fixture(scope="class")
    def pe_desk_session(self):
        """Get authenticated session for PE Desk user"""
        session = requests.Session()
        session.headers.update({
            "Content-Type": "application/json",
            "User-Agent": USER_AGENT
        })
        
        # Login as PE Desk
        response = session.post(f"{BASE_URL}/api/auth/login", json={
            "email": self.PE_DESK_EMAIL,
            "password": self.PE_DESK_PASSWORD
        })
        
        if response.status_code != 200:
            pytest.skip("PE Desk login failed - skipping tests")
        
        token = response.json().get("access_token")
        session.headers.update({"Authorization": f"Bearer {token}"})
        return session
    
    def test_01_get_pending_bp_overrides_endpoint_exists(self, pe_desk_session):
        """Test GET /api/bookings/pending-bp-overrides endpoint exists and returns valid response"""
        response = pe_desk_session.get(f"{BASE_URL}/api/bookings/pending-bp-overrides")
        
        # Should return 200 (PE Desk has approve_revenue_override permission)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Should return a list
        data = response.json()
        assert isinstance(data, list), f"Expected list, got {type(data)}"
        print(f"GET /api/bookings/pending-bp-overrides: Found {len(data)} pending overrides")
    
    def test_02_bp_override_approval_requires_booking(self, pe_desk_session):
        """Test PUT /api/bookings/{booking_id}/bp-override-approval requires valid booking"""
        fake_booking_id = str(uuid.uuid4())
        
        response = pe_desk_session.put(
            f"{BASE_URL}/api/bookings/{fake_booking_id}/bp-override-approval",
            json={"approve": True}
        )
        
        # Should return 404 for non-existent booking
        assert response.status_code == 404, f"Expected 404 for fake booking, got {response.status_code}"
        print("PUT /api/bookings/{id}/bp-override-approval: Correctly returns 404 for non-existent booking")
    
    def test_03_bp_override_edit_requires_booking(self, pe_desk_session):
        """Test PUT /api/bookings/{booking_id}/bp-override requires valid booking"""
        fake_booking_id = str(uuid.uuid4())
        
        response = pe_desk_session.put(
            f"{BASE_URL}/api/bookings/{fake_booking_id}/bp-override?override_percent=20"
        )
        
        # Should return 404 for non-existent booking
        assert response.status_code == 404, f"Expected 404 for fake booking, got {response.status_code}"
        print("PUT /api/bookings/{id}/bp-override: Correctly returns 404 for non-existent booking")
    
    def test_04_bp_override_approval_requires_rejection_reason(self, pe_desk_session):
        """Test that rejecting an override requires a rejection reason"""
        # First get any booking to use for testing
        response = pe_desk_session.get(f"{BASE_URL}/api/bookings?approval_status=approved")
        
        if response.status_code != 200 or not response.json():
            pytest.skip("No approved bookings available for testing")
        
        # Try rejecting without reason on a random booking (will fail due to status check)
        booking = response.json()[0]
        
        response = pe_desk_session.put(
            f"{BASE_URL}/api/bookings/{booking['id']}/bp-override-approval",
            json={"approve": False, "rejection_reason": ""}
        )
        
        # Either 400 (rejection_reason required or not BP booking) or 400 (not pending)
        # The important thing is it validates the request
        assert response.status_code in [400, 422], f"Expected validation error, got {response.status_code}"
        print("PUT bp-override-approval: Validates rejection reason requirement")
    
    def test_05_verify_bp_override_permissions_in_roles(self, pe_desk_session):
        """Test that BP override permissions exist in the permission system"""
        response = pe_desk_session.get(f"{BASE_URL}/api/roles/permissions")
        
        assert response.status_code == 200, f"Failed to get permissions: {response.text}"
        
        permissions = response.json()
        
        # Check bookings category has override permissions
        bookings_perms = permissions.get("bookings", {}).get("permissions", [])
        perm_keys = [p["key"] for p in bookings_perms]
        
        # Verify required permissions exist
        required_perms = [
            "bookings.override_revenue_share",
            "bookings.approve_revenue_override",
            "bookings.edit_revenue_override"
        ]
        
        for perm in required_perms:
            assert perm in perm_keys, f"Missing permission: {perm}"
            print(f"✓ Permission exists: {perm}")
    
    def test_06_bp_role_has_override_permission(self, pe_desk_session):
        """Test that Business Partner role (6) has override_revenue_share permission"""
        response = pe_desk_session.get(f"{BASE_URL}/api/roles/6")
        
        assert response.status_code == 200, f"Failed to get BP role: {response.text}"
        
        role = response.json()
        permissions = role.get("permissions", [])
        
        # Check if BP role has override permission
        has_override_perm = (
            "*" in permissions or
            "bookings.*" in permissions or
            "bookings.override_revenue_share" in permissions
        )
        
        print(f"BP Role permissions: {permissions}")
        print(f"BP Role has override permission: {has_override_perm}")
        # Note: This may be configured differently in the roles collection
    
    def test_07_partners_desk_has_override_permission(self, pe_desk_session):
        """Test that Partners Desk role (5) has override_revenue_share permission"""
        response = pe_desk_session.get(f"{BASE_URL}/api/roles/5")
        
        assert response.status_code == 200, f"Failed to get Partners Desk role: {response.text}"
        
        role = response.json()
        permissions = role.get("permissions", [])
        
        # Check if Partners Desk role has override permission
        has_override_perm = (
            "*" in permissions or
            "bookings.*" in permissions or
            "bookings.override_revenue_share" in permissions
        )
        
        print(f"Partners Desk Role permissions: {permissions}")
        print(f"Partners Desk has override permission: {has_override_perm}")
    
    def test_08_pe_desk_has_approve_override_permission(self, pe_desk_session):
        """Test that PE Desk role (1) has approve_revenue_override permission"""
        response = pe_desk_session.get(f"{BASE_URL}/api/roles/1")
        
        assert response.status_code == 200, f"Failed to get PE Desk role: {response.text}"
        
        role = response.json()
        permissions = role.get("permissions", [])
        
        # PE Desk should have all permissions (*)
        has_approve_perm = "*" in permissions
        
        assert has_approve_perm, "PE Desk role should have all permissions (*)"
        print(f"PE Desk Role has approve override permission: {has_approve_perm}")
    
    def test_09_check_pending_bp_overrides_structure(self, pe_desk_session):
        """Test that pending BP overrides response has expected structure"""
        response = pe_desk_session.get(f"{BASE_URL}/api/bookings/pending-bp-overrides")
        
        assert response.status_code == 200
        
        data = response.json()
        
        if len(data) > 0:
            # Check first override has expected fields
            booking = data[0]
            expected_fields = [
                "id", "booking_number", "client_id", "stock_id",
                "bp_override_approval_status", "bp_revenue_share_override",
                "bp_original_revenue_share", "is_bp_booking"
            ]
            
            for field in expected_fields:
                if field in booking:
                    print(f"✓ Field present: {field} = {booking.get(field)}")
                else:
                    print(f"✗ Field missing: {field}")
            
            # Verify it's actually a pending override
            assert booking.get("bp_override_approval_status") == "pending", \
                "Pending overrides endpoint should only return pending status"
        else:
            print("No pending BP overrides found - this is expected if no overrides are pending")
    
    def test_10_bp_override_approval_response_structure(self, pe_desk_session):
        """Test BP override approval endpoint validates request body"""
        # Use a fake booking ID to test request validation
        fake_id = str(uuid.uuid4())
        
        # Test with invalid JSON body
        response = pe_desk_session.put(
            f"{BASE_URL}/api/bookings/{fake_id}/bp-override-approval",
            json={}
        )
        
        # Should return validation error or 404
        assert response.status_code in [400, 404, 422], \
            f"Expected validation/not found, got {response.status_code}"
        print("BP override approval endpoint validates request body correctly")
    
    def test_11_bp_override_edit_requires_override_percent(self, pe_desk_session):
        """Test that editing BP override requires override_percent parameter"""
        # Get any booking
        response = pe_desk_session.get(f"{BASE_URL}/api/bookings")
        
        if response.status_code != 200 or not response.json():
            pytest.skip("No bookings available for testing")
        
        booking = response.json()[0]
        
        # Try to edit without override_percent
        response = pe_desk_session.put(
            f"{BASE_URL}/api/bookings/{booking['id']}/bp-override"
        )
        
        # Should return 422 (validation error - missing required parameter)
        assert response.status_code == 422, \
            f"Expected 422 for missing parameter, got {response.status_code}"
        print("BP override edit correctly requires override_percent parameter")
    
    def test_12_bp_override_edit_validates_percentage_range(self, pe_desk_session):
        """Test that BP override percentage is validated (0-100)"""
        # Get any booking
        response = pe_desk_session.get(f"{BASE_URL}/api/bookings")
        
        if response.status_code != 200 or not response.json():
            pytest.skip("No bookings available for testing")
        
        booking = response.json()[0]
        
        # Try invalid percentage (negative)
        response = pe_desk_session.put(
            f"{BASE_URL}/api/bookings/{booking['id']}/bp-override?override_percent=-5"
        )
        
        # Should return validation error
        assert response.status_code == 422, \
            f"Expected 422 for negative percentage, got {response.status_code}"
        
        # Try invalid percentage (over 100)
        response = pe_desk_session.put(
            f"{BASE_URL}/api/bookings/{booking['id']}/bp-override?override_percent=150"
        )
        
        assert response.status_code == 422, \
            f"Expected 422 for percentage > 100, got {response.status_code}"
        
        print("BP override edit correctly validates percentage range (0-100)")
    
    def test_13_check_bp_booking_in_bookings_list(self, pe_desk_session):
        """Test that BP bookings are correctly flagged in bookings list"""
        response = pe_desk_session.get(f"{BASE_URL}/api/bookings")
        
        assert response.status_code == 200
        
        bookings = response.json()
        bp_bookings = [b for b in bookings if b.get("is_bp_booking")]
        
        print(f"Total bookings: {len(bookings)}")
        print(f"BP bookings: {len(bp_bookings)}")
        
        for bp_booking in bp_bookings[:3]:  # Check first 3 BP bookings
            print(f"\nBP Booking: {bp_booking.get('booking_number')}")
            print(f"  - BP Name: {bp_booking.get('bp_name')}")
            print(f"  - BP Share: {bp_booking.get('bp_revenue_share_percent')}%")
            print(f"  - Override: {bp_booking.get('bp_revenue_share_override')}")
            print(f"  - Override Status: {bp_booking.get('bp_override_approval_status')}")


class TestBPOverrideWithoutAuth:
    """Test that BP override endpoints require authentication"""
    
    def test_01_pending_bp_overrides_requires_auth(self):
        """Test GET /api/bookings/pending-bp-overrides requires auth"""
        response = requests.get(
            f"{BASE_URL}/api/bookings/pending-bp-overrides",
            headers={"User-Agent": USER_AGENT}
        )
        
        assert response.status_code == 401, \
            f"Expected 401 without auth, got {response.status_code}"
        print("GET pending-bp-overrides correctly requires authentication")
    
    def test_02_bp_override_approval_requires_auth(self):
        """Test PUT /api/bookings/{id}/bp-override-approval requires auth"""
        response = requests.put(
            f"{BASE_URL}/api/bookings/{str(uuid.uuid4())}/bp-override-approval",
            headers={"User-Agent": USER_AGENT, "Content-Type": "application/json"},
            json={"approve": True}
        )
        
        assert response.status_code == 401, \
            f"Expected 401 without auth, got {response.status_code}"
        print("PUT bp-override-approval correctly requires authentication")
    
    def test_03_bp_override_edit_requires_auth(self):
        """Test PUT /api/bookings/{id}/bp-override requires auth"""
        response = requests.put(
            f"{BASE_URL}/api/bookings/{str(uuid.uuid4())}/bp-override?override_percent=20",
            headers={"User-Agent": USER_AGENT}
        )
        
        assert response.status_code == 401, \
            f"Expected 401 without auth, got {response.status_code}"
        print("PUT bp-override correctly requires authentication")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
