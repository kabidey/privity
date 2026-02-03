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

# Global session and token to avoid rate limiting
_session = None
_token = None


def get_authenticated_session():
    """Get or create authenticated session"""
    global _session, _token
    
    if _session is None:
        _session = requests.Session()
        _session.headers.update({"Content-Type": "application/json"})
    
    if _token is None:
        # Wait to avoid rate limiting
        time.sleep(2)
        response = _session.post(f"{BASE_URL}/api/auth/login", json={
            "email": PE_DESK_EMAIL,
            "password": PE_DESK_PASSWORD
        })
        if response.status_code == 200:
            data = response.json()
            _token = data.get("access_token")
            _session.headers.update({"Authorization": f"Bearer {_token}"})
        else:
            raise Exception(f"Login failed: {response.text}")
    
    return _session


def get_test_booking(session):
    """Get a booking that can be used for RP mapping tests"""
    response = session.get(f"{BASE_URL}/api/bookings")
    if response.status_code != 200:
        return None
    bookings = response.json()
    
    # Find a booking that is not BP booking, not transferred, not voided
    for booking in bookings:
        if (not booking.get("is_bp_booking") and 
            not booking.get("stock_transferred") and 
            not booking.get("is_voided")):
            return booking
    
    return None


def get_approved_rp(session):
    """Get an approved RP for testing"""
    response = session.get(f"{BASE_URL}/api/referral-partners-approved")
    if response.status_code != 200:
        return None
    rps = response.json()
    
    if rps and len(rps) > 0:
        return rps[0]
    return None


# ============== API ENDPOINT TESTS ==============

def test_01_login_and_get_bookings():
    """Test PE Desk login and get bookings list"""
    session = get_authenticated_session()
    
    response = session.get(f"{BASE_URL}/api/bookings")
    assert response.status_code == 200, f"Failed to get bookings: {response.text}"
    bookings = response.json()
    assert isinstance(bookings, list), "Bookings should be a list"
    print(f"SUCCESS: Got {len(bookings)} bookings")


def test_02_get_approved_rps():
    """Test getting approved RPs"""
    session = get_authenticated_session()
    
    response = session.get(f"{BASE_URL}/api/referral-partners-approved")
    assert response.status_code == 200, f"Failed to get RPs: {response.text}"
    rps = response.json()
    assert isinstance(rps, list), "RPs should be a list"
    print(f"SUCCESS: Got {len(rps)} approved RPs")


def test_03_update_rp_mapping_add_rp():
    """Test adding RP to a booking that has no RP"""
    session = get_authenticated_session()
    
    booking = get_test_booking(session)
    if not booking:
        pytest.skip("No suitable booking found for testing")
    
    rp = get_approved_rp(session)
    if not rp:
        pytest.skip("No approved RP found for testing")
    
    booking_id = booking.get("id")
    rp_id = rp.get("id")
    
    # Update RP mapping
    response = session.put(
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


def test_04_update_rp_mapping_change_share():
    """Test changing RP revenue share percentage"""
    session = get_authenticated_session()
    
    booking = get_test_booking(session)
    if not booking:
        pytest.skip("No suitable booking found for testing")
    
    rp = get_approved_rp(session)
    if not rp:
        pytest.skip("No approved RP found for testing")
    
    booking_id = booking.get("id")
    rp_id = rp.get("id")
    
    # Update RP mapping with different share
    response = session.put(
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


def test_05_update_rp_mapping_remove_rp():
    """Test removing RP from a booking"""
    session = get_authenticated_session()
    
    booking = get_test_booking(session)
    if not booking:
        pytest.skip("No suitable booking found for testing")
    
    booking_id = booking.get("id")
    
    # Remove RP mapping (no referral_partner_id parameter)
    response = session.put(
        f"{BASE_URL}/api/bookings/{booking_id}/referral-partner"
    )
    
    assert response.status_code == 200, f"Failed to remove RP: {response.text}"
    data = response.json()
    
    assert data.get("referral_partner_id") is None, "RP should be removed"
    assert data.get("rp_revenue_share_percent") == 0, "RP share should be 0"
    
    print(f"SUCCESS: Removed RP from booking {booking.get('booking_number')}")


def test_06_verify_booking_after_rp_update():
    """Test that booking reflects RP changes after update"""
    session = get_authenticated_session()
    
    booking = get_test_booking(session)
    if not booking:
        pytest.skip("No suitable booking found for testing")
    
    rp = get_approved_rp(session)
    if not rp:
        pytest.skip("No approved RP found for testing")
    
    booking_id = booking.get("id")
    rp_id = rp.get("id")
    
    # Add RP
    session.put(
        f"{BASE_URL}/api/bookings/{booking_id}/referral-partner",
        params={
            "referral_partner_id": rp_id,
            "rp_revenue_share_percent": 25.0
        }
    )
    
    # Get booking and verify
    response = session.get(f"{BASE_URL}/api/bookings/{booking_id}")
    assert response.status_code == 200, f"Failed to get booking: {response.text}"
    
    updated_booking = response.json()
    assert updated_booking.get("referral_partner_id") == rp_id, "RP ID not persisted"
    assert updated_booking.get("rp_revenue_share_percent") == 25.0, "RP share not persisted"
    assert updated_booking.get("employee_revenue_share_percent") == 75.0, "Employee share not calculated correctly"
    
    print(f"SUCCESS: Booking correctly reflects RP update (RP: 25%, Employee: 75%)")


def test_07_rp_share_default_30_percent():
    """Test that RP share defaults to 30% when not specified"""
    session = get_authenticated_session()
    
    booking = get_test_booking(session)
    if not booking:
        pytest.skip("No suitable booking found for testing")
    
    rp = get_approved_rp(session)
    if not rp:
        pytest.skip("No approved RP found for testing")
    
    booking_id = booking.get("id")
    rp_id = rp.get("id")
    
    # Set RP without specifying share (should default to 30%)
    response = session.put(
        f"{BASE_URL}/api/bookings/{booking_id}/referral-partner",
        params={
            "referral_partner_id": rp_id
        }
    )
    
    assert response.status_code == 200, f"Failed to update RP: {response.text}"
    data = response.json()
    
    # Default should be 30%
    assert data.get("rp_revenue_share_percent") == 30.0, f"RP share should default to 30%, got {data.get('rp_revenue_share_percent')}"
    print(f"SUCCESS: RP share defaults to 30%")


def test_08_invalid_rp_id():
    """Test that invalid RP ID is rejected"""
    session = get_authenticated_session()
    
    booking = get_test_booking(session)
    if not booking:
        pytest.skip("No suitable booking found for testing")
    
    # Try to set invalid RP ID
    response = session.put(
        f"{BASE_URL}/api/bookings/{booking['id']}/referral-partner",
        params={
            "referral_partner_id": "invalid-rp-id-12345",
            "rp_revenue_share_percent": 20.0
        }
    )
    
    assert response.status_code == 404, f"Should reject invalid RP ID: {response.text}"
    
    print(f"SUCCESS: API correctly rejected invalid RP ID")


def test_09_invalid_booking_id():
    """Test that invalid booking ID returns 404"""
    session = get_authenticated_session()
    
    rp = get_approved_rp(session)
    if not rp:
        pytest.skip("No approved RP found for testing")
    
    # Try to update non-existent booking
    response = session.put(
        f"{BASE_URL}/api/bookings/invalid-booking-id-12345/referral-partner",
        params={
            "referral_partner_id": rp.get("id"),
            "rp_revenue_share_percent": 20.0
        }
    )
    
    assert response.status_code == 404, f"Should return 404 for invalid booking: {response.text}"
    
    print(f"SUCCESS: API correctly returned 404 for invalid booking ID")


def test_10_cannot_update_transferred_booking():
    """Test that RP cannot be changed after stock transfer"""
    session = get_authenticated_session()
    
    # Get all bookings and find one that is transferred
    response = session.get(f"{BASE_URL}/api/bookings")
    assert response.status_code == 200
    bookings = response.json()
    
    transferred_booking = None
    for booking in bookings:
        if booking.get("stock_transferred"):
            transferred_booking = booking
            break
    
    if not transferred_booking:
        pytest.skip("No transferred booking found for testing")
    
    rp = get_approved_rp(session)
    if not rp:
        pytest.skip("No approved RP found for testing")
    
    # Try to update RP on transferred booking
    response = session.put(
        f"{BASE_URL}/api/bookings/{transferred_booking['id']}/referral-partner",
        params={
            "referral_partner_id": rp.get("id"),
            "rp_revenue_share_percent": 20.0
        }
    )
    
    assert response.status_code == 400, f"Should reject update on transferred booking: {response.text}"
    assert "transferred" in response.json().get("detail", "").lower(), "Error should mention transfer"
    
    print(f"SUCCESS: API correctly rejected RP update on transferred booking")


def test_11_cannot_update_bp_booking():
    """Test that RP cannot be assigned to BP booking"""
    session = get_authenticated_session()
    
    # Get all bookings and find a BP booking
    response = session.get(f"{BASE_URL}/api/bookings")
    assert response.status_code == 200
    bookings = response.json()
    
    bp_booking = None
    for booking in bookings:
        if booking.get("is_bp_booking"):
            bp_booking = booking
            break
    
    if not bp_booking:
        pytest.skip("No BP booking found for testing")
    
    rp = get_approved_rp(session)
    if not rp:
        pytest.skip("No approved RP found for testing")
    
    # Try to update RP on BP booking
    response = session.put(
        f"{BASE_URL}/api/bookings/{bp_booking['id']}/referral-partner",
        params={
            "referral_partner_id": rp.get("id"),
            "rp_revenue_share_percent": 20.0
        }
    )
    
    assert response.status_code == 400, f"Should reject RP on BP booking: {response.text}"
    assert "business partner" in response.json().get("detail", "").lower(), "Error should mention BP"
    
    print(f"SUCCESS: API correctly rejected RP assignment on BP booking")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
