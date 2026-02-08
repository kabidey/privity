"""
Test Suite for Fixed Income Yield Curve Analytics
==================================================

Tests for:
- Yield curve construction (G-Sec and corporate)
- Multiple interpolation methods support
- Spread analysis for different ratings
- Chart data formatting
- Efficient frontier calculation
- Key rate durations
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Module-level token storage
_auth_cache = {"token": None, "headers": None}

def get_auth_headers():
    """Get authentication headers, caching the token"""
    if _auth_cache["token"] is None:
        login_response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "pe@smifs.com", "password": "Kutta@123"}
        )
        if login_response.status_code == 200:
            _auth_cache["token"] = login_response.json()["token"]
            _auth_cache["headers"] = {"Authorization": f"Bearer {_auth_cache['token']}"}
        else:
            pytest.skip(f"Cannot authenticate: {login_response.text}")
    return _auth_cache["headers"]


class TestYieldCurveAnalytics:
    """Yield Curve Analytics API Tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get authentication headers"""
        self.headers = get_auth_headers()
    
    # ==================== Yield Curves Endpoint Tests ====================
    
    def test_yield_curves_default(self):
        """Test GET /yield-curves returns G-Sec and corporate curves"""
        response = requests.get(
            f"{BASE_URL}/api/fixed-income/analytics/yield-curves",
            headers=self.headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        
        # Verify response structure
        assert "curve_date" in data, "Missing curve_date"
        assert "interpolation_method" in data, "Missing interpolation_method"
        assert "gsec_curve" in data, "Missing gsec_curve"
        assert "corporate_curves" in data, "Missing corporate_curves"
        assert "forward_curve" in data, "Missing forward_curve"
        
        # Verify G-Sec curve structure
        gsec = data["gsec_curve"]
        assert gsec["curve_type"] == "spot", f"Expected spot curve, got {gsec['curve_type']}"
        assert "points" in gsec, "Missing points in G-Sec curve"
        assert len(gsec["points"]) > 0, "G-Sec curve has no points"
        
        # Verify G-Sec points structure
        for point in gsec["points"]:
            assert "tenor" in point, "Missing tenor in point"
            assert "rate" in point, "Missing rate in point"
            assert "rating" in point, "Missing rating in point"
            assert point["rating"] == "SOVEREIGN", f"G-Sec should be SOVEREIGN, got {point['rating']}"
        
        # Verify corporate curves include default ratings
        assert "AAA" in data["corporate_curves"], "Missing AAA corporate curve"
        assert "AA" in data["corporate_curves"], "Missing AA corporate curve"
        assert "A" in data["corporate_curves"], "Missing A corporate curve"
        
        print(f"SUCCESS: Yield curves returned with {len(gsec['points'])} G-Sec points and {len(data['corporate_curves'])} corporate curves")
    
    def test_yield_curves_linear_interpolation(self):
        """Test yield curves with linear interpolation method"""
        response = requests.get(
            f"{BASE_URL}/api/fixed-income/analytics/yield-curves?interpolation=linear",
            headers=self.headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert data["interpolation_method"] == "linear", f"Expected linear, got {data['interpolation_method']}"
        
        # Linear interpolation should not have model params
        assert data["gsec_curve"]["model_params"] == {}, "Linear should have empty model_params"
        
        print("SUCCESS: Linear interpolation method works correctly")
    
    def test_yield_curves_cubic_spline_interpolation(self):
        """Test yield curves with cubic spline interpolation method"""
        response = requests.get(
            f"{BASE_URL}/api/fixed-income/analytics/yield-curves?interpolation=cubic_spline",
            headers=self.headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert data["interpolation_method"] == "cubic_spline", f"Expected cubic_spline, got {data['interpolation_method']}"
        
        print("SUCCESS: Cubic spline interpolation method works correctly")
    
    def test_yield_curves_nelson_siegel_interpolation(self):
        """Test yield curves with Nelson-Siegel parametric model"""
        response = requests.get(
            f"{BASE_URL}/api/fixed-income/analytics/yield-curves?interpolation=nelson_siegel",
            headers=self.headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert data["interpolation_method"] == "nelson_siegel", f"Expected nelson_siegel, got {data['interpolation_method']}"
        
        # Nelson-Siegel should have model params
        model_params = data["gsec_curve"]["model_params"]
        if model_params:  # Only check if fitting was successful
            assert "beta0" in model_params, "Missing beta0 parameter"
            assert "beta1" in model_params, "Missing beta1 parameter"
            assert "beta2" in model_params, "Missing beta2 parameter"
            assert "tau1" in model_params, "Missing tau1 parameter"
        
        print("SUCCESS: Nelson-Siegel interpolation method works correctly")
    
    def test_yield_curves_svensson_interpolation(self):
        """Test yield curves with Svensson (extended Nelson-Siegel) model"""
        response = requests.get(
            f"{BASE_URL}/api/fixed-income/analytics/yield-curves?interpolation=svensson",
            headers=self.headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert data["interpolation_method"] == "svensson", f"Expected svensson, got {data['interpolation_method']}"
        
        # Svensson should have extended model params
        model_params = data["gsec_curve"]["model_params"]
        if model_params:  # Only check if fitting was successful
            assert "beta0" in model_params, "Missing beta0 parameter"
            assert "beta1" in model_params, "Missing beta1 parameter"
            assert "beta2" in model_params, "Missing beta2 parameter"
            # Svensson adds beta3 and tau2
            if "beta3" in model_params:
                assert "tau2" in model_params, "Missing tau2 parameter for Svensson"
        
        print("SUCCESS: Svensson interpolation method works correctly")
    
    def test_yield_curves_custom_ratings(self):
        """Test yield curves with custom ratings list"""
        response = requests.get(
            f"{BASE_URL}/api/fixed-income/analytics/yield-curves?ratings=AAA,BBB",
            headers=self.headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        corporate_curves = data["corporate_curves"]
        
        assert "AAA" in corporate_curves, "Missing AAA curve"
        assert "BBB" in corporate_curves, "Missing BBB curve"
        
        print("SUCCESS: Custom ratings list works correctly")
    
    # ==================== Spread Analysis Endpoint Tests ====================
    
    def test_spread_analysis_aaa(self):
        """Test spread analysis for AAA rating"""
        response = requests.get(
            f"{BASE_URL}/api/fixed-income/analytics/spread-analysis/AAA",
            headers=self.headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        
        # Verify response structure
        assert data["rating"] == "AAA", f"Expected AAA, got {data['rating']}"
        assert "curve_date" in data, "Missing curve_date"
        assert "spreads" in data, "Missing spreads"
        assert "key_rate_durations" in data, "Missing key_rate_durations"
        assert "summary" in data, "Missing summary"
        
        # Verify spreads structure
        spreads = data["spreads"]
        assert len(spreads) > 0, "No spreads returned"
        
        for spread in spreads:
            assert "tenor" in spread, "Missing tenor in spread"
            assert "corporate_yield" in spread, "Missing corporate_yield"
            assert "benchmark_yield" in spread, "Missing benchmark_yield"
            assert "spread_bps" in spread, "Missing spread_bps"
            assert "spread_pct" in spread, "Missing spread_pct"
        
        # Verify summary structure
        summary = data["summary"]
        assert "avg_spread_bps" in summary, "Missing avg_spread_bps"
        assert "min_spread_bps" in summary, "Missing min_spread_bps"
        assert "max_spread_bps" in summary, "Missing max_spread_bps"
        
        print(f"SUCCESS: AAA spread analysis returned {len(spreads)} tenor points")
    
    def test_spread_analysis_aa(self):
        """Test spread analysis for AA rating"""
        response = requests.get(
            f"{BASE_URL}/api/fixed-income/analytics/spread-analysis/AA",
            headers=self.headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert data["rating"] == "AA", f"Expected AA, got {data['rating']}"
        assert "spreads" in data and len(data["spreads"]) > 0, "No spreads for AA"
        
        print("SUCCESS: AA spread analysis works correctly")
    
    def test_spread_analysis_a(self):
        """Test spread analysis for A rating"""
        response = requests.get(
            f"{BASE_URL}/api/fixed-income/analytics/spread-analysis/A",
            headers=self.headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert data["rating"] == "A", f"Expected A, got {data['rating']}"
        assert "spreads" in data and len(data["spreads"]) > 0, "No spreads for A"
        
        print("SUCCESS: A spread analysis works correctly")
    
    def test_spread_analysis_invalid_rating(self):
        """Test spread analysis rejects invalid rating"""
        response = requests.get(
            f"{BASE_URL}/api/fixed-income/analytics/spread-analysis/XYZ",
            headers=self.headers
        )
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        
        data = response.json()
        assert "detail" in data, "Missing error detail"
        assert "Invalid rating" in data["detail"], f"Unexpected error: {data['detail']}"
        
        print("SUCCESS: Invalid rating properly rejected")
    
    # ==================== Key Rate Durations Tests ====================
    
    def test_key_rate_durations_structure(self):
        """Test key rate durations are returned correctly"""
        response = requests.get(
            f"{BASE_URL}/api/fixed-income/analytics/spread-analysis/AAA",
            headers=self.headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        krds = data["key_rate_durations"]
        
        assert len(krds) > 0, "No key rate durations returned"
        
        for krd in krds:
            assert "tenor" in krd, "Missing tenor"
            assert "key_rate_duration" in krd, "Missing key_rate_duration"
            assert "rate" in krd, "Missing rate"
            assert "dv01_estimate" in krd, "Missing dv01_estimate"
            
            # KRD should be approximately equal to tenor * 0.95
            expected_krd = krd["tenor"] * 0.95
            actual_krd = krd["key_rate_duration"]
            assert abs(actual_krd - expected_krd) < 0.01, f"KRD calculation incorrect at tenor {krd['tenor']}"
        
        print(f"SUCCESS: Key rate durations returned for {len(krds)} tenors")
    
    # ==================== Chart Data Endpoint Tests ====================
    
    def test_chart_data_structure(self):
        """Test chart data endpoint returns properly formatted series"""
        response = requests.get(
            f"{BASE_URL}/api/fixed-income/analytics/yield-curves/chart",
            headers=self.headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        
        # Verify response structure
        assert "curve_date" in data, "Missing curve_date"
        assert "series" in data, "Missing series"
        assert "x_axis" in data, "Missing x_axis"
        assert "y_axis" in data, "Missing y_axis"
        
        # Verify series structure
        series = data["series"]
        assert len(series) > 0, "No series returned"
        
        # First series should be G-Sec
        gsec_series = series[0]
        assert "name" in gsec_series, "Missing name in series"
        assert "G-Sec" in gsec_series["name"], f"First series should be G-Sec, got {gsec_series['name']}"
        assert "data" in gsec_series, "Missing data in series"
        assert "color" in gsec_series, "Missing color in series"
        
        # Verify data points structure
        for point in gsec_series["data"]:
            assert "x" in point, "Missing x coordinate"
            assert "y" in point, "Missing y coordinate"
            assert isinstance(point["x"], (int, float)), "x should be numeric"
            assert isinstance(point["y"], (int, float)), "y should be numeric"
        
        # Verify axis configuration
        assert data["x_axis"]["title"] == "Tenor (Years)", f"Unexpected x_axis title"
        assert data["y_axis"]["title"] == "Yield (%)", f"Unexpected y_axis title"
        
        print(f"SUCCESS: Chart data returned with {len(series)} series")
    
    def test_chart_data_series_count(self):
        """Test chart data includes all requested ratings"""
        response = requests.get(
            f"{BASE_URL}/api/fixed-income/analytics/yield-curves/chart?ratings=AAA,AA,A",
            headers=self.headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        series = data["series"]
        
        # Should have G-Sec + 3 corporate curves = 4 series
        assert len(series) >= 4, f"Expected at least 4 series, got {len(series)}"
        
        series_names = [s["name"] for s in series]
        assert any("G-Sec" in name for name in series_names), "Missing G-Sec series"
        assert any("AAA" in name for name in series_names), "Missing AAA series"
        assert any("AA" in name for name in series_names), "Missing AA series"
        
        print("SUCCESS: Chart data includes all requested rating series")
    
    # ==================== Efficient Frontier Endpoint Tests ====================
    
    def test_efficient_frontier_basic(self):
        """Test efficient frontier endpoint returns risk-return tradeoff points"""
        response = requests.post(
            f"{BASE_URL}/api/fixed-income/analytics/efficient-frontier",
            headers=self.headers,
            json={"n_points": 10, "max_duration": 10.0}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        
        # Verify response structure
        assert "frontier_points" in data, "Missing frontier_points"
        assert "parameters" in data, "Missing parameters"
        assert "chart_config" in data, "Missing chart_config"
        assert "generated_at" in data, "Missing generated_at"
        
        # Verify frontier points structure
        frontier = data["frontier_points"]
        # May be empty if no instruments available
        if len(frontier) > 0:
            for point in frontier:
                assert "risk_score" in point, "Missing risk_score"
                assert "expected_yield" in point, "Missing expected_yield"
                assert "expected_duration" in point, "Missing expected_duration"
                assert "n_instruments" in point, "Missing n_instruments"
                
                # Validate ranges
                assert point["risk_score"] >= 0, "Risk score should be non-negative"
                assert point["expected_yield"] > 0, "Expected yield should be positive"
                assert point["expected_duration"] >= 0, "Duration should be non-negative"
        
        # Verify parameters returned match request
        params = data["parameters"]
        assert params["n_points"] == 10, f"Expected n_points=10, got {params['n_points']}"
        assert params["max_duration"] == 10.0, f"Expected max_duration=10.0, got {params['max_duration']}"
        
        print(f"SUCCESS: Efficient frontier returned {len(frontier)} points")
    
    def test_efficient_frontier_with_more_points(self):
        """Test efficient frontier with more points"""
        response = requests.post(
            f"{BASE_URL}/api/fixed-income/analytics/efficient-frontier",
            headers=self.headers,
            json={"n_points": 20, "max_duration": 15.0}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        
        # More points requested should potentially return more points
        assert "frontier_points" in data, "Missing frontier_points"
        
        params = data["parameters"]
        assert params["n_points"] == 20, f"Expected n_points=20, got {params['n_points']}"
        
        print("SUCCESS: Efficient frontier with custom parameters works")
    
    def test_efficient_frontier_chart_config(self):
        """Test efficient frontier returns proper chart configuration"""
        response = requests.post(
            f"{BASE_URL}/api/fixed-income/analytics/efficient-frontier",
            headers=self.headers,
            json={"n_points": 10, "max_duration": 10.0}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        chart_config = data["chart_config"]
        
        # Verify axis configuration
        assert "x_axis" in chart_config, "Missing x_axis config"
        assert "y_axis" in chart_config, "Missing y_axis config"
        
        assert chart_config["x_axis"]["title"] == "Risk Score", f"Unexpected x_axis title"
        assert chart_config["y_axis"]["title"] == "Expected Yield (%)", f"Unexpected y_axis title"
        
        print("SUCCESS: Efficient frontier chart configuration is correct")
    
    # ==================== Forward Curve Tests ====================
    
    def test_forward_curve_structure(self):
        """Test forward curve is returned with yield curves"""
        response = requests.get(
            f"{BASE_URL}/api/fixed-income/analytics/yield-curves",
            headers=self.headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        forward_curve = data["forward_curve"]
        
        assert forward_curve["curve_type"] == "forward", f"Expected forward, got {forward_curve['curve_type']}"
        assert "points" in forward_curve, "Missing points in forward curve"
        
        # Forward curve points should have rate calculated from spot rates
        if len(forward_curve["points"]) > 0:
            for point in forward_curve["points"]:
                assert "tenor" in point, "Missing tenor"
                assert "rate" in point, "Missing rate"
                assert "instrument" in point, "Missing instrument"
                assert "forward" in point["instrument"].lower(), f"Forward instrument description expected"
        
        print(f"SUCCESS: Forward curve has {len(forward_curve['points'])} points")
    
    # ==================== Authentication Tests ====================
    
    def test_unauthorized_access(self):
        """Test that endpoints require authentication"""
        # No auth header
        response = requests.get(
            f"{BASE_URL}/api/fixed-income/analytics/yield-curves"
        )
        assert response.status_code in [401, 403], f"Expected 401/403 without auth, got {response.status_code}"
        
        print("SUCCESS: Authentication is properly enforced")
    
    def test_invalid_token(self):
        """Test that invalid token is rejected"""
        response = requests.get(
            f"{BASE_URL}/api/fixed-income/analytics/yield-curves",
            headers={"Authorization": "Bearer invalid_token_xyz"}
        )
        assert response.status_code in [401, 403], f"Expected 401/403 with invalid token, got {response.status_code}"
        
        print("SUCCESS: Invalid token is properly rejected")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
