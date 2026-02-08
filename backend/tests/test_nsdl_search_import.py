"""
NSDL Search and Import Feature Tests
Tests for the ISIN/Company search and import functionality in Fixed Income Security Master

Features tested:
- NSDL Search API (company name search, ISIN search)
- NSDL Import API (single import, duplicate detection)
- NSDL Statistics API
- NSDL Import Multiple API
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestNSDLSearchImport:
    """Tests for NSDL Search and Import APIs"""
    
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

    # ========== NSDL Search Tests ==========
    
    def test_nsdl_search_by_company_name_reliance(self, auth_headers):
        """Test NSDL search by company name 'Reliance'"""
        response = requests.get(
            f"{BASE_URL}/api/fixed-income/instruments/nsdl-search",
            params={"query": "Reliance", "search_type": "company"},
            headers=auth_headers
        )
        assert response.status_code == 200, f"Search failed: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "results" in data
        assert "total_results" in data
        assert data["total_results"] > 0, "Expected at least one Reliance instrument"
        
        # Verify result contains Reliance
        for result in data["results"]:
            assert "reliance" in result["issuer_name"].lower()
            # Check expected fields
            assert "isin" in result
            assert "instrument_type" in result
            assert "coupon_rate" in result
            assert "credit_rating" in result
            assert "maturity_date" in result
            assert "can_import" in result
            assert "already_imported" in result
    
    def test_nsdl_search_by_company_name_hdfc(self, auth_headers):
        """Test NSDL search by company name 'HDFC'"""
        response = requests.get(
            f"{BASE_URL}/api/fixed-income/instruments/nsdl-search",
            params={"query": "HDFC", "search_type": "company"},
            headers=auth_headers
        )
        assert response.status_code == 200, f"Search failed: {response.text}"
        data = response.json()
        
        assert data["total_results"] > 0, "Expected at least one HDFC instrument"
        
        # Verify HDFC is in results
        found_hdfc = any("hdfc" in r["issuer_name"].lower() for r in data["results"])
        assert found_hdfc, "Expected HDFC instruments in results"
    
    def test_nsdl_search_by_isin_partial(self, auth_headers):
        """Test NSDL search by partial ISIN 'INE002A'"""
        response = requests.get(
            f"{BASE_URL}/api/fixed-income/instruments/nsdl-search",
            params={"query": "INE002A", "search_type": "isin"},
            headers=auth_headers
        )
        assert response.status_code == 200, f"Search failed: {response.text}"
        data = response.json()
        
        assert data["total_results"] > 0, "Expected results for partial ISIN INE002A"
        
        # All results should have ISIN starting with INE002A
        for result in data["results"]:
            assert "INE002A" in result["isin"]
    
    def test_nsdl_search_by_isin_full(self, auth_headers):
        """Test NSDL search by full ISIN 'INE002A08427'"""
        response = requests.get(
            f"{BASE_URL}/api/fixed-income/instruments/nsdl-search",
            params={"query": "INE002A08427", "search_type": "isin"},
            headers=auth_headers
        )
        assert response.status_code == 200, f"Search failed: {response.text}"
        data = response.json()
        
        # Should find exactly one or return with already_imported flag
        assert data["total_results"] >= 1, "Expected result for full ISIN"
        assert data["results"][0]["isin"] == "INE002A08427"
    
    def test_nsdl_search_all_fields(self, auth_headers):
        """Test NSDL search with 'all' search type"""
        response = requests.get(
            f"{BASE_URL}/api/fixed-income/instruments/nsdl-search",
            params={"query": "Bajaj", "search_type": "all"},
            headers=auth_headers
        )
        assert response.status_code == 200, f"Search failed: {response.text}"
        data = response.json()
        
        assert data["total_results"] > 0, "Expected results for 'Bajaj' in all fields"
    
    def test_nsdl_search_by_rating(self, auth_headers):
        """Test NSDL search by credit rating 'AAA'"""
        response = requests.get(
            f"{BASE_URL}/api/fixed-income/instruments/nsdl-search",
            params={"query": "AAA", "search_type": "rating"},
            headers=auth_headers
        )
        assert response.status_code == 200, f"Search failed: {response.text}"
        data = response.json()
        
        assert data["total_results"] > 0, "Expected AAA rated instruments"
        
        # All results should be AAA rated
        for result in data["results"]:
            assert result["credit_rating"] == "AAA"
    
    def test_nsdl_search_minimum_query_length(self, auth_headers):
        """Test NSDL search requires minimum 2 character query"""
        response = requests.get(
            f"{BASE_URL}/api/fixed-income/instruments/nsdl-search",
            params={"query": "A", "search_type": "all"},
            headers=auth_headers
        )
        # Should return 422 validation error for query < 2 chars
        assert response.status_code == 422, f"Expected 422 for short query, got: {response.status_code}"
    
    def test_nsdl_search_no_results(self, auth_headers):
        """Test NSDL search with non-existent company"""
        response = requests.get(
            f"{BASE_URL}/api/fixed-income/instruments/nsdl-search",
            params={"query": "XYZNONEXISTENT", "search_type": "company"},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data["total_results"] == 0
        assert len(data["results"]) == 0
    
    def test_nsdl_search_filter_by_instrument_type(self, auth_headers):
        """Test NSDL search filtered by instrument type NCD"""
        response = requests.get(
            f"{BASE_URL}/api/fixed-income/instruments/nsdl-search",
            params={"query": "Bajaj", "search_type": "all", "instrument_type": "NCD"},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # All results should be NCDs
        for result in data["results"]:
            assert result["instrument_type"] == "NCD"

    # ========== NSDL Import Tests ==========
    
    def test_nsdl_import_single_instrument(self, auth_headers):
        """Test importing a single instrument from NSDL database"""
        # First search to find an available instrument
        search_resp = requests.get(
            f"{BASE_URL}/api/fixed-income/instruments/nsdl-search",
            params={"query": "Tata Capital", "search_type": "company"},
            headers=auth_headers
        )
        assert search_resp.status_code == 200
        search_data = search_resp.json()
        
        # Find an instrument that can be imported
        importable = [r for r in search_data["results"] if r.get("can_import")]
        
        if not importable:
            pytest.skip("No importable instruments found for Tata Capital")
        
        isin_to_import = importable[0]["isin"]
        
        # Import the instrument
        import_resp = requests.post(
            f"{BASE_URL}/api/fixed-income/instruments/nsdl-import/{isin_to_import}",
            headers=auth_headers
        )
        
        # Should succeed or fail with already exists
        if import_resp.status_code == 200:
            data = import_resp.json()
            assert data["success"] == True
            assert "instrument_id" in data
            assert data["instrument"]["isin"] == isin_to_import
        elif import_resp.status_code == 400:
            # Already imported
            assert "already exists" in import_resp.json().get("detail", "").lower()
        else:
            pytest.fail(f"Unexpected status: {import_resp.status_code} - {import_resp.text}")
    
    def test_nsdl_import_already_imported_error(self, auth_headers):
        """Test importing already imported instrument returns error"""
        # First import an instrument
        test_isin = "INE752E08288"  # Sundaram Finance - likely not imported
        
        # Try to import
        import_resp1 = requests.post(
            f"{BASE_URL}/api/fixed-income/instruments/nsdl-import/{test_isin}",
            headers=auth_headers
        )
        
        # First import should succeed or already exist
        if import_resp1.status_code == 200:
            # Try importing again - should fail
            import_resp2 = requests.post(
                f"{BASE_URL}/api/fixed-income/instruments/nsdl-import/{test_isin}",
                headers=auth_headers
            )
            assert import_resp2.status_code == 400
            assert "already exists" in import_resp2.json().get("detail", "").lower()
        elif import_resp1.status_code == 400:
            # Already exists is expected
            assert "already exists" in import_resp1.json().get("detail", "").lower()
    
    def test_nsdl_import_invalid_isin(self, auth_headers):
        """Test importing non-existent ISIN returns error"""
        response = requests.post(
            f"{BASE_URL}/api/fixed-income/instruments/nsdl-import/INVALID123456",
            headers=auth_headers
        )
        assert response.status_code == 400
        assert "not found" in response.json().get("detail", "").lower()

    # ========== NSDL Statistics Tests ==========
    
    def test_nsdl_statistics_endpoint(self, auth_headers):
        """Test NSDL statistics endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/fixed-income/instruments/nsdl-statistics",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify statistics structure
        assert "total_instruments" in data
        assert "unique_issuers" in data
        assert "already_imported" in data
        assert "available_to_import" in data
        assert "by_instrument_type" in data
        assert "by_credit_rating" in data
        assert "by_sector" in data
        
        # Verify counts
        assert data["total_instruments"] > 0
        assert data["unique_issuers"] > 0

    # ========== NSDL Import Multiple Tests ==========
    
    def test_nsdl_import_multiple(self, auth_headers):
        """Test importing multiple instruments at once"""
        # Search for some instruments
        search_resp = requests.get(
            f"{BASE_URL}/api/fixed-income/instruments/nsdl-search",
            params={"query": "Shriram", "search_type": "company"},
            headers=auth_headers
        )
        assert search_resp.status_code == 200
        
        importable = [r["isin"] for r in search_resp.json()["results"] if r.get("can_import")]
        
        if len(importable) < 2:
            pytest.skip("Not enough importable instruments for multiple import test")
        
        # Try to import first 2
        response = requests.post(
            f"{BASE_URL}/api/fixed-income/instruments/nsdl-import-multiple",
            json=importable[:2],
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "total" in data
        assert "successful" in data
        assert "failed" in data
        assert "imports" in data

    # ========== Authorization Tests ==========
    
    def test_nsdl_search_requires_auth(self):
        """Test NSDL search requires authentication"""
        response = requests.get(
            f"{BASE_URL}/api/fixed-income/instruments/nsdl-search",
            params={"query": "Reliance", "search_type": "company"}
        )
        assert response.status_code == 401

    def test_nsdl_import_requires_auth(self):
        """Test NSDL import requires authentication"""
        response = requests.post(
            f"{BASE_URL}/api/fixed-income/instruments/nsdl-import/INE002A08427"
        )
        assert response.status_code == 401


class TestNSDLSearchResponseFields:
    """Test response field structure and values"""
    
    @pytest.fixture(scope='class')
    def auth_headers(self):
        """Get authentication headers"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "pe@smifs.com", "password": "Kutta@123"}
        )
        token = response.json().get("token")
        return {"Authorization": f"Bearer {token}"}
    
    def test_search_result_has_all_required_fields(self, auth_headers):
        """Verify search results contain all required display fields"""
        response = requests.get(
            f"{BASE_URL}/api/fixed-income/instruments/nsdl-search",
            params={"query": "Bajaj Finance", "search_type": "company"},
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
    
    def test_import_result_structure(self, auth_headers):
        """Verify import result structure"""
        # Search for an importable instrument
        search_resp = requests.get(
            f"{BASE_URL}/api/fixed-income/instruments/nsdl-search",
            params={"query": "Aditya Birla", "search_type": "company"},
            headers=auth_headers
        )
        
        importable = [r for r in search_resp.json().get("results", []) if r.get("can_import")]
        
        if not importable:
            pytest.skip("No importable instruments found")
        
        isin = importable[0]["isin"]
        
        # Try to import
        import_resp = requests.post(
            f"{BASE_URL}/api/fixed-income/instruments/nsdl-import/{isin}",
            headers=auth_headers
        )
        
        if import_resp.status_code == 200:
            data = import_resp.json()
            assert "success" in data
            assert "message" in data
            assert "instrument_id" in data
            assert "instrument" in data
        elif import_resp.status_code == 400:
            # Already imported is acceptable
            assert "detail" in import_resp.json()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
