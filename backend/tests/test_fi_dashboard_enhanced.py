"""
FI Dashboard Enhanced Features Tests
Tests for duration_distribution, sector_breakdown, cash_flow_calendar, and Recharts integration
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestFIDashboardEnhanced:
    """Tests for Enhanced FI Dashboard API - duration, sector, cash flow features"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login and get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "pe@smifs.com",
            "password": "Kutta@123"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        self.token = response.json()["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_dashboard_returns_200(self):
        """Test FI dashboard returns 200 status"""
        response = requests.get(f"{BASE_URL}/api/fixed-income/dashboard", headers=self.headers)
        assert response.status_code == 200, f"Dashboard failed: {response.text}"
        print("PASS: FI Dashboard API returns 200")
    
    def test_dashboard_has_duration_distribution(self):
        """Test dashboard returns duration_distribution with correct structure"""
        response = requests.get(f"{BASE_URL}/api/fixed-income/dashboard", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        
        # Check duration_distribution exists
        assert "duration_distribution" in data, "Missing duration_distribution field"
        duration_dist = data["duration_distribution"]
        
        # Check it's a list with expected ranges
        assert isinstance(duration_dist, list), "duration_distribution should be a list"
        assert len(duration_dist) == 5, f"Expected 5 duration ranges, got {len(duration_dist)}"
        
        # Validate structure
        expected_ranges = ["< 1 year", "1-3 years", "3-5 years", "5-7 years", "7+ years"]
        for i, item in enumerate(duration_dist):
            assert "range" in item, f"Missing 'range' in duration_distribution[{i}]"
            assert "count" in item, f"Missing 'count' in duration_distribution[{i}]"
            assert "value" in item, f"Missing 'value' in duration_distribution[{i}]"
            assert item["range"] == expected_ranges[i], f"Unexpected range: {item['range']}"
        
        print("PASS: duration_distribution has correct structure")
    
    def test_dashboard_has_sector_breakdown(self):
        """Test dashboard returns sector_breakdown with correct structure"""
        response = requests.get(f"{BASE_URL}/api/fixed-income/dashboard", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        
        # Check sector_breakdown exists
        assert "sector_breakdown" in data, "Missing sector_breakdown field"
        sector_data = data["sector_breakdown"]
        
        # Check it's a list (can be empty if no holdings)
        assert isinstance(sector_data, list), "sector_breakdown should be a list"
        
        # If there's data, validate structure
        for item in sector_data:
            assert "sector" in item, "Missing 'sector' field in sector_breakdown item"
            assert "count" in item, "Missing 'count' field in sector_breakdown item"
            assert "value" in item, "Missing 'value' field in sector_breakdown item"
        
        print(f"PASS: sector_breakdown has correct structure ({len(sector_data)} sectors)")
    
    def test_dashboard_has_cash_flow_calendar(self):
        """Test dashboard returns cash_flow_calendar with 12 months of data"""
        response = requests.get(f"{BASE_URL}/api/fixed-income/dashboard", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        
        # Check cash_flow_calendar exists
        assert "cash_flow_calendar" in data, "Missing cash_flow_calendar field"
        cash_flow = data["cash_flow_calendar"]
        
        # Check it's a list with 12 months
        assert isinstance(cash_flow, list), "cash_flow_calendar should be a list"
        assert len(cash_flow) == 12, f"Expected 12 months in cash_flow_calendar, got {len(cash_flow)}"
        
        # Validate structure for each month
        for i, month_data in enumerate(cash_flow):
            assert "month" in month_data, f"Missing 'month' in cash_flow_calendar[{i}]"
            assert "coupons" in month_data, f"Missing 'coupons' in cash_flow_calendar[{i}]"
            assert "maturities" in month_data, f"Missing 'maturities' in cash_flow_calendar[{i}]"
            assert "total" in month_data, f"Missing 'total' in cash_flow_calendar[{i}]"
            
            # Values should be numeric
            assert isinstance(month_data["coupons"], (int, float)), f"coupons should be numeric"
            assert isinstance(month_data["maturities"], (int, float)), f"maturities should be numeric"
            assert isinstance(month_data["total"], (int, float)), f"total should be numeric"
        
        print("PASS: cash_flow_calendar has 12 months with correct structure")
    
    def test_dashboard_has_ytm_distribution(self):
        """Test dashboard returns ytm_distribution with correct structure"""
        response = requests.get(f"{BASE_URL}/api/fixed-income/dashboard", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        
        # Check ytm_distribution exists
        assert "ytm_distribution" in data, "Missing ytm_distribution field"
        ytm_dist = data["ytm_distribution"]
        
        # Check it's a list with expected ranges
        assert isinstance(ytm_dist, list), "ytm_distribution should be a list"
        assert len(ytm_dist) == 5, f"Expected 5 YTM ranges, got {len(ytm_dist)}"
        
        # Validate ranges
        expected_ranges = ["< 8%", "8-9%", "9-10%", "10-11%", "11%+"]
        for i, item in enumerate(ytm_dist):
            assert item["range"] == expected_ranges[i], f"Unexpected YTM range: {item['range']}"
        
        print("PASS: ytm_distribution has correct structure")
    
    def test_dashboard_summary_has_avg_duration(self):
        """Test dashboard summary includes avg_duration field"""
        response = requests.get(f"{BASE_URL}/api/fixed-income/dashboard", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        
        # Check summary has avg_duration
        assert "summary" in data, "Missing summary field"
        summary = data["summary"]
        
        assert "avg_duration" in summary, "Missing avg_duration in summary"
        assert isinstance(summary["avg_duration"], (int, float)), "avg_duration should be numeric"
        
        print(f"PASS: summary.avg_duration = {summary['avg_duration']} years")
    
    def test_dashboard_summary_complete_fields(self):
        """Test dashboard summary has all required fields"""
        response = requests.get(f"{BASE_URL}/api/fixed-income/dashboard", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        
        summary = data.get("summary", {})
        required_fields = [
            "total_aum", "total_holdings", "total_clients", 
            "avg_ytm", "avg_duration", "total_accrued_interest", "pending_orders"
        ]
        
        for field in required_fields:
            assert field in summary, f"Missing {field} in summary"
            print(f"  {field}: {summary[field]}")
        
        print("PASS: summary has all required fields")
    
    def test_dashboard_has_holdings_by_type(self):
        """Test dashboard returns holdings_by_type"""
        response = requests.get(f"{BASE_URL}/api/fixed-income/dashboard", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        
        assert "holdings_by_type" in data, "Missing holdings_by_type field"
        assert isinstance(data["holdings_by_type"], dict), "holdings_by_type should be a dict"
        
        print(f"PASS: holdings_by_type present (types: {list(data['holdings_by_type'].keys())})")
    
    def test_dashboard_has_holdings_by_rating(self):
        """Test dashboard returns holdings_by_rating"""
        response = requests.get(f"{BASE_URL}/api/fixed-income/dashboard", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        
        assert "holdings_by_rating" in data, "Missing holdings_by_rating field"
        assert isinstance(data["holdings_by_rating"], dict), "holdings_by_rating should be a dict"
        
        print(f"PASS: holdings_by_rating present (ratings: {list(data['holdings_by_rating'].keys())})")
    
    def test_dashboard_response_structure_complete(self):
        """Test complete dashboard response structure for frontend compatibility"""
        response = requests.get(f"{BASE_URL}/api/fixed-income/dashboard", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        
        # All required top-level fields
        required_fields = [
            "summary", "holdings_by_type", "holdings_by_rating",
            "sector_breakdown", "duration_distribution",
            "upcoming_maturities", "upcoming_coupons",
            "recent_orders", "ytm_distribution", "cash_flow_calendar"
        ]
        
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"
        
        print("PASS: Dashboard response has all required fields for Recharts integration")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
