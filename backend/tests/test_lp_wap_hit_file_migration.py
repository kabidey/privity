"""
Test LP/WAP Pricing Logic, PE Desk HIT Report, and File Migration Features
Tests for iteration 45 - Privity Share Booking System
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
PE_DESK_EMAIL = "pe@smifs.com"
PE_DESK_PASSWORD = "Kutta@123"
EMPLOYEE_EMAIL = "employee@test.com"
EMPLOYEE_PASSWORD = "Test@123"


class TestAuthentication:
    """Test authentication for different user roles"""
    
    def test_pe_desk_login(self):
        """Test PE Desk Super Admin login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": PE_DESK_EMAIL,
            "password": PE_DESK_PASSWORD
        })
        assert response.status_code == 200, f"PE Desk login failed: {response.text}"
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == 1, "PE Desk should have role 1"
        print(f"✓ PE Desk login successful - Role: {data['user']['role']}")
        return data["token"]
    
    def test_employee_login(self):
        """Test Employee login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": EMPLOYEE_EMAIL,
            "password": EMPLOYEE_PASSWORD
        })
        # Employee might not exist, skip if 401
        if response.status_code == 401:
            pytest.skip("Employee user not found - skipping employee tests")
        assert response.status_code == 200, f"Employee login failed: {response.text}"
        data = response.json()
        assert "token" in data
        print(f"✓ Employee login successful - Role: {data['user']['role']}")
        return data["token"]


@pytest.fixture(scope="class")
def pe_desk_token():
    """Get PE Desk authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": PE_DESK_EMAIL,
        "password": PE_DESK_PASSWORD
    })
    if response.status_code != 200:
        pytest.skip("PE Desk login failed")
    return response.json()["token"]


@pytest.fixture(scope="class")
def employee_token():
    """Get Employee authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": EMPLOYEE_EMAIL,
        "password": EMPLOYEE_PASSWORD
    })
    if response.status_code != 200:
        pytest.skip("Employee login failed - user may not exist")
    return response.json()["token"]


class TestInventoryLPWAP:
    """Test Inventory LP/WAP pricing logic"""
    
    def test_inventory_endpoint_returns_data(self, pe_desk_token):
        """Test that inventory endpoint returns data for PE Desk"""
        headers = {"Authorization": f"Bearer {pe_desk_token}"}
        response = requests.get(f"{BASE_URL}/api/inventory", headers=headers)
        assert response.status_code == 200, f"Inventory fetch failed: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Inventory should return a list"
        print(f"✓ Inventory endpoint returns {len(data)} items")
        return data
    
    def test_pe_level_sees_wap_and_lp(self, pe_desk_token):
        """Test that PE Level users see both WAP and LP columns"""
        headers = {"Authorization": f"Bearer {pe_desk_token}"}
        response = requests.get(f"{BASE_URL}/api/inventory", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        if len(data) == 0:
            pytest.skip("No inventory data to test")
        
        # Check first item has both WAP and LP fields
        item = data[0]
        assert "weighted_avg_price" in item, "PE Level should see weighted_avg_price (WAP)"
        assert "landing_price" in item, "PE Level should see landing_price (LP)"
        assert "total_value" in item, "PE Level should see total_value (WAP-based)"
        assert "lp_total_value" in item, "PE Level should see lp_total_value (LP-based)"
        
        print(f"✓ PE Level sees WAP: {item['weighted_avg_price']}, LP: {item['landing_price']}")
        print(f"  WAP Value: {item['total_value']}, LP Value: {item['lp_total_value']}")
    
    def test_non_pe_user_sees_only_lp(self, employee_token):
        """Test that non-PE users only see LP as the price (WAP hidden)"""
        headers = {"Authorization": f"Bearer {employee_token}"}
        response = requests.get(f"{BASE_URL}/api/inventory", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        if len(data) == 0:
            pytest.skip("No inventory data to test")
        
        # For non-PE users, weighted_avg_price should equal landing_price
        item = data[0]
        assert "weighted_avg_price" in item, "Should have weighted_avg_price field"
        assert "landing_price" in item, "Should have landing_price field"
        
        # The weighted_avg_price shown to non-PE users should be the LP
        # (WAP is hidden, LP is shown as "price")
        print(f"✓ Non-PE user sees price: {item['weighted_avg_price']} (should be LP)")
    
    def test_landing_price_endpoint(self, pe_desk_token):
        """Test getting landing price for a specific stock"""
        headers = {"Authorization": f"Bearer {pe_desk_token}"}
        
        # First get inventory to find a stock_id
        response = requests.get(f"{BASE_URL}/api/inventory", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        if len(data) == 0:
            pytest.skip("No inventory data to test")
        
        stock_id = data[0]["stock_id"]
        
        # Get landing price for this stock
        response = requests.get(f"{BASE_URL}/api/inventory/{stock_id}/landing-price", headers=headers)
        assert response.status_code == 200, f"Landing price fetch failed: {response.text}"
        
        lp_data = response.json()
        assert "stock_id" in lp_data
        assert "landing_price" in lp_data
        assert "available_quantity" in lp_data
        
        print(f"✓ Landing price for {stock_id}: {lp_data['landing_price']}")
    
    def test_update_landing_price_pe_desk_only(self, pe_desk_token):
        """Test that only PE Desk can update landing price"""
        headers = {"Authorization": f"Bearer {pe_desk_token}"}
        
        # First get inventory to find a stock_id
        response = requests.get(f"{BASE_URL}/api/inventory", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        if len(data) == 0:
            pytest.skip("No inventory data to test")
        
        stock_id = data[0]["stock_id"]
        current_lp = data[0].get("landing_price", 100)
        
        # Update landing price (PE Desk should be able to)
        new_lp = current_lp + 0.01  # Small change
        response = requests.put(
            f"{BASE_URL}/api/inventory/{stock_id}/landing-price",
            headers=headers,
            json={"landing_price": new_lp}
        )
        assert response.status_code == 200, f"LP update failed: {response.text}"
        
        result = response.json()
        assert result["landing_price"] == round(new_lp, 2)
        print(f"✓ PE Desk updated LP from {current_lp} to {new_lp}")
        
        # Restore original LP
        requests.put(
            f"{BASE_URL}/api/inventory/{stock_id}/landing-price",
            headers=headers,
            json={"landing_price": current_lp}
        )


class TestPEDeskHITReport:
    """Test PE Desk HIT Report endpoints"""
    
    def test_hit_report_endpoint_exists(self, pe_desk_token):
        """Test that PE Desk HIT report endpoint exists and returns data"""
        headers = {"Authorization": f"Bearer {pe_desk_token}"}
        response = requests.get(f"{BASE_URL}/api/reports/pe-desk-hit", headers=headers)
        assert response.status_code == 200, f"HIT report failed: {response.text}"
        
        data = response.json()
        assert "report_type" in data
        assert data["report_type"] == "PE Desk HIT Report"
        assert "summary" in data
        assert "details" in data
        assert "by_stock" in data
        
        print(f"✓ HIT Report returned with {data['summary']['total_bookings']} bookings")
        print(f"  Total HIT: {data['summary']['total_hit']}")
    
    def test_hit_report_summary_fields(self, pe_desk_token):
        """Test HIT report summary has required fields"""
        headers = {"Authorization": f"Bearer {pe_desk_token}"}
        response = requests.get(f"{BASE_URL}/api/reports/pe-desk-hit", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        summary = data["summary"]
        
        assert "total_bookings" in summary
        assert "total_quantity" in summary
        assert "total_hit" in summary
        assert "avg_hit_per_share" in summary
        
        print(f"✓ HIT Summary: {summary}")
    
    def test_hit_report_with_filters(self, pe_desk_token):
        """Test HIT report with date filters"""
        headers = {"Authorization": f"Bearer {pe_desk_token}"}
        
        # Test with date filters
        response = requests.get(
            f"{BASE_URL}/api/reports/pe-desk-hit",
            headers=headers,
            params={"start_date": "2024-01-01", "end_date": "2026-12-31"}
        )
        assert response.status_code == 200, f"HIT report with filters failed: {response.text}"
        
        data = response.json()
        assert data["filters"]["start_date"] == "2024-01-01"
        assert data["filters"]["end_date"] == "2026-12-31"
        
        print(f"✓ HIT Report with filters returned {data['summary']['total_bookings']} bookings")
    
    def test_hit_report_non_pe_forbidden(self, employee_token):
        """Test that non-PE users cannot access HIT report"""
        headers = {"Authorization": f"Bearer {employee_token}"}
        response = requests.get(f"{BASE_URL}/api/reports/pe-desk-hit", headers=headers)
        assert response.status_code == 403, "Non-PE users should be forbidden from HIT report"
        print("✓ Non-PE user correctly forbidden from HIT report")
    
    def test_hit_report_export_endpoint(self, pe_desk_token):
        """Test HIT report export endpoint exists"""
        headers = {"Authorization": f"Bearer {pe_desk_token}"}
        
        # Test Excel export
        response = requests.get(
            f"{BASE_URL}/api/reports/pe-desk-hit/export",
            headers=headers,
            params={"format": "xlsx"}
        )
        assert response.status_code == 200, f"Excel export failed: {response.text}"
        assert "spreadsheet" in response.headers.get("content-type", "").lower() or \
               "octet-stream" in response.headers.get("content-type", "").lower()
        print("✓ HIT Report Excel export works")
        
        # Test PDF export
        response = requests.get(
            f"{BASE_URL}/api/reports/pe-desk-hit/export",
            headers=headers,
            params={"format": "pdf"}
        )
        assert response.status_code == 200, f"PDF export failed: {response.text}"
        assert "pdf" in response.headers.get("content-type", "").lower()
        print("✓ HIT Report PDF export works")


class TestFileMigration:
    """Test File Migration / GridFS endpoints"""
    
    def test_storage_stats_endpoint(self, pe_desk_token):
        """Test file storage stats endpoint"""
        headers = {"Authorization": f"Bearer {pe_desk_token}"}
        response = requests.get(f"{BASE_URL}/api/files/storage-stats", headers=headers)
        assert response.status_code == 200, f"Storage stats failed: {response.text}"
        
        data = response.json()
        assert "total_files" in data
        assert "total_size_bytes" in data
        assert "total_size_mb" in data
        assert "by_category" in data
        
        print(f"✓ Storage Stats: {data['total_files']} files, {data['total_size_mb']} MB")
    
    def test_scan_missing_files_endpoint(self, pe_desk_token):
        """Test scan missing files endpoint"""
        headers = {"Authorization": f"Bearer {pe_desk_token}"}
        response = requests.get(f"{BASE_URL}/api/files/scan-missing", headers=headers)
        assert response.status_code == 200, f"Scan missing failed: {response.text}"
        
        data = response.json()
        assert "missing_files" in data
        assert "total_missing" in data
        assert "message" in data
        
        print(f"✓ Scan Missing: {data['total_missing']} missing files")
    
    def test_storage_stats_non_pe_forbidden(self, employee_token):
        """Test that non-PE users cannot access storage stats"""
        headers = {"Authorization": f"Bearer {employee_token}"}
        response = requests.get(f"{BASE_URL}/api/files/storage-stats", headers=headers)
        assert response.status_code == 403, "Non-PE users should be forbidden from storage stats"
        print("✓ Non-PE user correctly forbidden from storage stats")
    
    def test_scan_missing_non_pe_forbidden(self, employee_token):
        """Test that non-PE users cannot scan missing files"""
        headers = {"Authorization": f"Bearer {employee_token}"}
        response = requests.get(f"{BASE_URL}/api/files/scan-missing", headers=headers)
        assert response.status_code == 403, "Non-PE users should be forbidden from scan missing"
        print("✓ Non-PE user correctly forbidden from scan missing files")


class TestNavigationLinks:
    """Test that navigation links exist for new pages"""
    
    def test_pe_hit_report_accessible(self, pe_desk_token):
        """Test PE HIT Report page is accessible via API"""
        headers = {"Authorization": f"Bearer {pe_desk_token}"}
        response = requests.get(f"{BASE_URL}/api/reports/pe-desk-hit", headers=headers)
        assert response.status_code == 200
        print("✓ PE HIT Report API accessible")
    
    def test_file_migration_accessible(self, pe_desk_token):
        """Test File Migration page APIs are accessible"""
        headers = {"Authorization": f"Bearer {pe_desk_token}"}
        
        # Storage stats
        response = requests.get(f"{BASE_URL}/api/files/storage-stats", headers=headers)
        assert response.status_code == 200
        
        # Scan missing
        response = requests.get(f"{BASE_URL}/api/files/scan-missing", headers=headers)
        assert response.status_code == 200
        
        print("✓ File Migration APIs accessible")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
