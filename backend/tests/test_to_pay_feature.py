"""
Test suite for Finance To Pay feature
Tests: Vendor payment calculations with TCS (@0.1% if FY > 50L) and Stamp Duty (@0.015%)

Formula:
A = Gross Consideration = Price × Qty
B = TCS @0.1% if FY cumulative payments exceed ₹50 lakhs
C = Stamp Duty @0.015% of Gross Consideration  
D = Net Payable = A - B - C
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Constants matching backend
TCS_RATE = 0.001  # 0.1%
TCS_THRESHOLD = 5000000  # 50 lakhs
STAMP_DUTY_RATE = 0.00015  # 0.015%


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for PE user"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": "pe@smifs.com",
        "password": "Kutta@123"
    })
    assert response.status_code == 200, f"Login failed: {response.text}"
    return response.json()["token"]


@pytest.fixture
def authenticated_client(auth_token):
    """Create authenticated session"""
    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    })
    return session


class TestToPayEndpoint:
    """Tests for /finance/to-pay endpoint"""

    def test_endpoint_returns_200(self, authenticated_client):
        """Test endpoint is accessible and returns 200"""
        response = authenticated_client.get(f"{BASE_URL}/api/finance/to-pay")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("PASS: /finance/to-pay endpoint returns 200")

    def test_response_structure(self, authenticated_client):
        """Test response has correct structure"""
        response = authenticated_client.get(f"{BASE_URL}/api/finance/to-pay")
        assert response.status_code == 200
        data = response.json()
        
        # Check top-level fields
        required_fields = ['financial_year', 'tcs_threshold', 'tcs_rate_percent', 
                          'stamp_duty_rate_percent', 'to_pay_list', 'summary']
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"
        
        print("PASS: Response has all required top-level fields")

    def test_tcs_threshold_value(self, authenticated_client):
        """Test TCS threshold is 50 lakhs (5,000,000)"""
        response = authenticated_client.get(f"{BASE_URL}/api/finance/to-pay")
        assert response.status_code == 200
        data = response.json()
        
        assert data['tcs_threshold'] == 5000000, f"TCS threshold should be 5000000, got {data['tcs_threshold']}"
        print("PASS: TCS threshold is correctly set to 5,000,000 (₹50 lakhs)")

    def test_tcs_rate_value(self, authenticated_client):
        """Test TCS rate is 0.1%"""
        response = authenticated_client.get(f"{BASE_URL}/api/finance/to-pay")
        assert response.status_code == 200
        data = response.json()
        
        assert data['tcs_rate_percent'] == 0.1, f"TCS rate should be 0.1%, got {data['tcs_rate_percent']}%"
        print("PASS: TCS rate is correctly set to 0.1%")

    def test_stamp_duty_rate_value(self, authenticated_client):
        """Test Stamp Duty rate is 0.015%"""
        response = authenticated_client.get(f"{BASE_URL}/api/finance/to-pay")
        assert response.status_code == 200
        data = response.json()
        
        assert data['stamp_duty_rate_percent'] == 0.015, f"Stamp duty should be 0.015%, got {data['stamp_duty_rate_percent']}%"
        print("PASS: Stamp Duty rate is correctly set to 0.015%")

    def test_summary_fields(self, authenticated_client):
        """Test summary contains all required calculation fields"""
        response = authenticated_client.get(f"{BASE_URL}/api/finance/to-pay")
        assert response.status_code == 200
        data = response.json()
        
        summary = data['summary']
        summary_fields = ['total_purchases', 'total_gross_consideration', 'total_tcs', 
                         'total_stamp_duty', 'total_net_payable', 'total_remaining']
        for field in summary_fields:
            assert field in summary, f"Missing summary field: {field}"
        
        print("PASS: Summary contains all required calculation fields")

    def test_to_pay_item_fields(self, authenticated_client):
        """Test each to_pay_list item has correct calculation fields"""
        response = authenticated_client.get(f"{BASE_URL}/api/finance/to-pay")
        assert response.status_code == 200
        data = response.json()
        
        if len(data['to_pay_list']) > 0:
            item = data['to_pay_list'][0]
            required_item_fields = [
                'purchase_id', 'purchase_number', 'vendor_id', 'vendor_name', 'vendor_pan',
                'stock_symbol', 'quantity', 'price_per_unit', 'gross_consideration',
                'tcs_applicable', 'tcs_rate', 'tcs_amount', 'stamp_duty_rate', 
                'stamp_duty_amount', 'net_payable', 'already_paid', 'remaining_to_pay',
                'financial_year', 'vendor_fy_cumulative_before', 'vendor_fy_cumulative_after',
                'tcs_threshold', 'tcs_threshold_exceeded'
            ]
            for field in required_item_fields:
                assert field in item, f"Missing item field: {field}"
            print(f"PASS: to_pay_list item has all {len(required_item_fields)} required fields")
        else:
            print("INFO: No items in to_pay_list to validate field structure")

    def test_gross_consideration_calculation(self, authenticated_client):
        """Test A = Price × Qty calculation"""
        response = authenticated_client.get(f"{BASE_URL}/api/finance/to-pay")
        assert response.status_code == 200
        data = response.json()
        
        for item in data['to_pay_list']:
            expected_gross = item['price_per_unit'] * item['quantity']
            assert abs(item['gross_consideration'] - expected_gross) < 0.01, \
                f"Gross calculation error for {item['purchase_number']}: expected {expected_gross}, got {item['gross_consideration']}"
        
        print("PASS: Gross Consideration (A) = Price × Qty calculation is correct")

    def test_stamp_duty_calculation(self, authenticated_client):
        """Test C = 0.015% of Gross Consideration"""
        response = authenticated_client.get(f"{BASE_URL}/api/finance/to-pay")
        assert response.status_code == 200
        data = response.json()
        
        for item in data['to_pay_list']:
            expected_stamp = item['gross_consideration'] * STAMP_DUTY_RATE
            assert abs(item['stamp_duty_amount'] - expected_stamp) < 0.01, \
                f"Stamp duty calculation error for {item['purchase_number']}: expected {expected_stamp}, got {item['stamp_duty_amount']}"
        
        print("PASS: Stamp Duty (C) = 0.015% of Gross calculation is correct")

    def test_net_payable_calculation(self, authenticated_client):
        """Test D = A - B - C (Net Payable = Gross - TCS - Stamp Duty)"""
        response = authenticated_client.get(f"{BASE_URL}/api/finance/to-pay")
        assert response.status_code == 200
        data = response.json()
        
        for item in data['to_pay_list']:
            expected_net = item['gross_consideration'] - item['tcs_amount'] - item['stamp_duty_amount']
            assert abs(item['net_payable'] - expected_net) < 0.01, \
                f"Net payable calculation error for {item['purchase_number']}: expected {expected_net}, got {item['net_payable']}"
        
        print("PASS: Net Payable (D) = A - B - C calculation is correct")

    def test_tcs_applicability_when_below_threshold(self, authenticated_client):
        """Test TCS is NOT applicable when FY cumulative is below 50 lakhs"""
        response = authenticated_client.get(f"{BASE_URL}/api/finance/to-pay")
        assert response.status_code == 200
        data = response.json()
        
        for item in data['to_pay_list']:
            if item['vendor_fy_cumulative_after'] <= TCS_THRESHOLD:
                assert item['tcs_applicable'] == False, \
                    f"TCS should NOT be applicable for {item['purchase_number']} (cumulative {item['vendor_fy_cumulative_after']} <= {TCS_THRESHOLD})"
        
        print("PASS: TCS is correctly NOT applied when FY cumulative <= ₹50 lakhs")

    def test_unauthorized_access(self):
        """Test endpoint returns 401/403 without authentication"""
        response = requests.get(f"{BASE_URL}/api/finance/to-pay")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print(f"PASS: Endpoint correctly returns {response.status_code} for unauthorized access")


class TestToPayCalculationLogic:
    """Tests for TCS and calculation logic"""

    def test_financial_year_format(self, authenticated_client):
        """Test financial year is in correct format"""
        response = authenticated_client.get(f"{BASE_URL}/api/finance/to-pay")
        assert response.status_code == 200
        data = response.json()
        
        fy = data['financial_year']
        assert fy.startswith("FY "), f"Financial year should start with 'FY ', got {fy}"
        assert "-" in fy, f"Financial year should contain dash, got {fy}"
        print(f"PASS: Financial year format is correct: {fy}")

    def test_summary_totals_match_items(self, authenticated_client):
        """Test summary totals match sum of individual items"""
        response = authenticated_client.get(f"{BASE_URL}/api/finance/to-pay")
        assert response.status_code == 200
        data = response.json()
        
        items = data['to_pay_list']
        summary = data['summary']
        
        # Calculate sums from items
        calc_gross = sum(item['gross_consideration'] for item in items)
        calc_tcs = sum(item['tcs_amount'] for item in items)
        calc_stamp = sum(item['stamp_duty_amount'] for item in items)
        calc_net = sum(item['net_payable'] for item in items)
        calc_remaining = sum(item['remaining_to_pay'] for item in items)
        
        assert abs(summary['total_gross_consideration'] - calc_gross) < 0.01, "Gross total mismatch"
        assert abs(summary['total_tcs'] - calc_tcs) < 0.01, "TCS total mismatch"
        assert abs(summary['total_stamp_duty'] - calc_stamp) < 0.01, "Stamp duty total mismatch"
        assert abs(summary['total_net_payable'] - calc_net) < 0.01, "Net payable total mismatch"
        assert abs(summary['total_remaining'] - calc_remaining) < 0.01, "Remaining total mismatch"
        assert summary['total_purchases'] == len(items), "Purchase count mismatch"
        
        print("PASS: Summary totals correctly match sum of individual items")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
