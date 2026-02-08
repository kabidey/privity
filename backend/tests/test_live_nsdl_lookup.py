"""
Live NSDL Lookup Feature Tests

Tests for the Live Web Scraping feature that searches for bond data from:
- indiabondsinfo.nsdl.com
- indiabonds.com  
- smest.in

When an ISIN is not found locally, the system attempts live lookup from these sources.
Note: Live scraping will fail in container due to network restrictions - we test API structure.

Features tested:
- NSDL Search returns local results when ISIN exists (INE002A08427)
- NSDL Search triggers live lookup when ISIN doesn't exist locally
- Live lookup endpoint works for direct ISIN lookup
- Response includes live_lookup_attempted flag when appropriate
- Response includes live_lookup_result with success/failure info
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestLiveNSDLLookup:
    """Tests for Live NSDL Lookup feature"""
    
    @pytest.fixture(scope='class')
    def auth_token(self):
        """Get authentication token for PE user"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "pe@smifs.com", "password": "Kutta@123"}
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        return response.json().get("token")
    
    @pytest.fixture(scope='class')
    def auth_headers(self, auth_token):
        """Auth headers for authenticated requests"""
        return {"Authorization": f"Bearer {auth_token}"}

    # ========== NSDL Search - Local Results Tests ==========
    
    def test_nsdl_search_local_isin_returns_result(self, auth_headers):
        """Test: NSDL Search returns local results when ISIN exists (INE002A08427)"""
        response = requests.get(
            f"{BASE_URL}/api/fixed-income/instruments/nsdl-search",
            params={"query": "INE002A08427", "search_type": "isin", "live_lookup": "true"},
            headers=auth_headers
        )
        assert response.status_code == 200, f"Search failed: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "results" in data
        assert "total_results" in data
        assert data["total_results"] >= 1, "Expected local result for INE002A08427"
        
        # Verify ISIN matches
        found = any(r["isin"] == "INE002A08427" for r in data["results"])
        assert found, "Expected INE002A08427 in results"
        
        # When local result exists, live_lookup_attempted should NOT be set
        # (or should be false/null)
        if "live_lookup_attempted" in data:
            assert data.get("live_lookup_attempted") in [None, False], \
                "live_lookup_attempted should not be True when local result exists"
    
    def test_nsdl_search_local_result_has_required_fields(self, auth_headers):
        """Test: Local search results have all required display fields"""
        response = requests.get(
            f"{BASE_URL}/api/fixed-income/instruments/nsdl-search",
            params={"query": "INE002A08427", "search_type": "isin"},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        if data["total_results"] > 0:
            result = data["results"][0]
            
            # Required fields for display
            required_fields = [
                "isin", "issuer_name", "instrument_type", "coupon_rate",
                "credit_rating", "maturity_date", "can_import", "already_imported"
            ]
            
            for field in required_fields:
                assert field in result, f"Missing required field: {field}"
    
    def test_nsdl_search_company_name_no_live_lookup(self, auth_headers):
        """Test: Company name search returns results without live lookup"""
        response = requests.get(
            f"{BASE_URL}/api/fixed-income/instruments/nsdl-search",
            params={"query": "Reliance", "search_type": "company", "live_lookup": "true"},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data["total_results"] > 0, "Expected results for Reliance"
        
        # Company search doesn't trigger live lookup (only ISIN triggers it)
        if "live_lookup_attempted" in data:
            assert data.get("live_lookup_attempted") in [None, False]

    # ========== NSDL Search - Live Lookup Trigger Tests ==========
    
    def test_nsdl_search_nonexistent_isin_triggers_live_lookup(self, auth_headers):
        """Test: NSDL Search triggers live lookup when ISIN doesn't exist locally"""
        # Use a valid ISIN format but non-existent in local DB
        response = requests.get(
            f"{BASE_URL}/api/fixed-income/instruments/nsdl-search",
            params={"query": "INE999Z99999", "search_type": "isin", "live_lookup": "true"},
            headers=auth_headers
        )
        assert response.status_code == 200, f"Search failed: {response.text}"
        data = response.json()
        
        # Verify live lookup was attempted
        assert "live_lookup_attempted" in data, "Missing live_lookup_attempted field"
        assert data["live_lookup_attempted"] == True, "Expected live_lookup_attempted=True"
        
        # Verify live_lookup_result structure
        assert "live_lookup_result" in data, "Missing live_lookup_result field"
        live_result = data["live_lookup_result"]
        
        assert "success" in live_result, "live_lookup_result missing success field"
        assert "message" in live_result, "live_lookup_result missing message field"
        
        # In container environment, scraping fails - verify proper error handling
        assert live_result["success"] == False, "Expected success=False due to network restrictions"
    
    def test_nsdl_search_live_lookup_result_has_sources_tried(self, auth_headers):
        """Test: live_lookup_result includes sources_tried when lookup fails"""
        response = requests.get(
            f"{BASE_URL}/api/fixed-income/instruments/nsdl-search",
            params={"query": "INE888X88888", "search_type": "isin", "live_lookup": "true"},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        if data.get("live_lookup_attempted"):
            live_result = data.get("live_lookup_result", {})
            # sources_tried or errors should be present for debugging
            assert "sources_tried" in live_result or "errors" in live_result, \
                "live_lookup_result should include sources_tried or errors"
    
    def test_nsdl_search_live_lookup_disabled(self, auth_headers):
        """Test: Live lookup can be disabled via query param"""
        response = requests.get(
            f"{BASE_URL}/api/fixed-income/instruments/nsdl-search",
            params={"query": "INE777Y77777", "search_type": "isin", "live_lookup": "false"},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # With live_lookup=false, should not attempt live lookup
        assert data.get("live_lookup_attempted") in [None, False], \
            "live_lookup_attempted should be False when live_lookup=false"

    # ========== Direct Live Lookup Endpoint Tests ==========
    
    def test_live_lookup_endpoint_valid_isin(self, auth_headers):
        """Test: Live lookup endpoint works for direct ISIN lookup"""
        response = requests.post(
            f"{BASE_URL}/api/fixed-income/instruments/live-lookup/INE456X12345",
            headers=auth_headers
        )
        
        # Should return 404 with proper error structure (not found from sources)
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        
        data = response.json()
        assert "detail" in data
        
        detail = data["detail"]
        # Verify error structure
        assert "message" in detail, "Error should include message"
        assert "sources_tried" in detail, "Error should include sources_tried"
    
    def test_live_lookup_endpoint_invalid_isin_format(self, auth_headers):
        """Test: Live lookup returns 400 for invalid ISIN format"""
        response = requests.post(
            f"{BASE_URL}/api/fixed-income/instruments/live-lookup/INVALID",
            headers=auth_headers
        )
        
        assert response.status_code == 400, f"Expected 400 for invalid ISIN, got {response.status_code}"
        
        data = response.json()
        assert "Invalid ISIN format" in data.get("detail", "")
    
    def test_live_lookup_endpoint_short_isin(self, auth_headers):
        """Test: Live lookup returns 400 for short ISIN"""
        response = requests.post(
            f"{BASE_URL}/api/fixed-income/instruments/live-lookup/IN12345",
            headers=auth_headers
        )
        
        # Should fail validation (ISIN too short)
        assert response.status_code == 400, f"Expected 400 for short ISIN, got {response.status_code}"
    
    def test_live_lookup_endpoint_requires_auth(self):
        """Test: Live lookup endpoint requires authentication"""
        response = requests.post(
            f"{BASE_URL}/api/fixed-income/instruments/live-lookup/INE123A12345"
        )
        
        # Should return 401 or 403
        assert response.status_code in [401, 403], \
            f"Expected 401/403 without auth, got {response.status_code}"

    # ========== Response Structure Tests ==========
    
    def test_nsdl_search_response_structure(self, auth_headers):
        """Test: NSDL search response has correct structure"""
        response = requests.get(
            f"{BASE_URL}/api/fixed-income/instruments/nsdl-search",
            params={"query": "HDFC", "search_type": "company"},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Required response fields
        assert "query" in data, "Response missing 'query' field"
        assert "search_type" in data, "Response missing 'search_type' field"
        assert "total_results" in data, "Response missing 'total_results' field"
        assert "results" in data, "Response missing 'results' field"
        
        # Verify query echo
        assert data["query"] == "HDFC"
        assert data["search_type"] == "company"
    
    def test_live_lookup_response_includes_badge_info(self, auth_headers):
        """Test: Live lookup results include 'live_lookup' flag for badge display"""
        # This test verifies the frontend can show a "LIVE" badge
        # When live lookup is attempted, results should have live_lookup flag
        response = requests.get(
            f"{BASE_URL}/api/fixed-income/instruments/nsdl-search",
            params={"query": "INE333Z33333", "search_type": "isin", "live_lookup": "true"},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # If live lookup succeeded, result should have live_lookup=True
        if data.get("live_lookup_result", {}).get("success"):
            for result in data["results"]:
                if result.get("source") == "LIVE_LOOKUP":
                    assert result.get("live_lookup") == True

    # ========== Edge Cases ==========
    
    def test_nsdl_search_partial_isin_no_live_lookup(self, auth_headers):
        """Test: Partial ISIN (e.g., INE002A) doesn't trigger live lookup"""
        response = requests.get(
            f"{BASE_URL}/api/fixed-income/instruments/nsdl-search",
            params={"query": "INE002A", "search_type": "isin", "live_lookup": "true"},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Partial ISIN should return local matches without live lookup
        # (live lookup only for full valid ISINs that aren't found)
        if data["total_results"] > 0:
            # Found local results, should not attempt live lookup
            assert data.get("live_lookup_attempted") in [None, False]
    
    def test_nsdl_search_uppercase_normalization(self, auth_headers):
        """Test: ISIN is normalized to uppercase for search"""
        response = requests.get(
            f"{BASE_URL}/api/fixed-income/instruments/nsdl-search",
            params={"query": "ine002a08427", "search_type": "isin"},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Should still find the result despite lowercase input
        assert data["total_results"] >= 1, "ISIN search should be case-insensitive"


class TestLiveNSDLLookupService:
    """Tests for the LiveBondLookup service class validation"""
    
    @pytest.fixture(scope='class')
    def auth_headers(self):
        """Get authentication headers"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "pe@smifs.com", "password": "Kutta@123"}
        )
        token = response.json().get("token")
        return {"Authorization": f"Bearer {token}"}
    
    def test_gsec_isin_format_valid(self, auth_headers):
        """Test: G-Sec ISIN format (IN002...) is valid for live lookup"""
        # G-Sec ISINs start with IN002 or similar
        response = requests.post(
            f"{BASE_URL}/api/fixed-income/instruments/live-lookup/IN0020240123",
            headers=auth_headers
        )
        
        # Should accept the format (404 if not found, but not 400)
        assert response.status_code in [404, 200], \
            f"G-Sec ISIN format should be accepted, got {response.status_code}"
    
    def test_corporate_isin_format_valid(self, auth_headers):
        """Test: Corporate ISIN format (INE...) is valid for live lookup"""
        response = requests.post(
            f"{BASE_URL}/api/fixed-income/instruments/live-lookup/INE123A12345",
            headers=auth_headers
        )
        
        # Should accept the format
        assert response.status_code in [404, 200], \
            f"Corporate ISIN format should be accepted, got {response.status_code}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
