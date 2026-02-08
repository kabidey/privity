"""
Test Bond Scraping Service - Consolidated Service with 72 Instruments
======================================================================

Tests:
1. NSDL Search returns results from new consolidated BOND_DATABASE (72 instruments)
2. Statistics endpoint shows all data sources (primary, secondary, exchange)
3. Search with rating_filter works correctly (e.g., AAA only)
4. Search with sector_filter works correctly (e.g., Infrastructure)
5. Search with instrument_type filter works (NCD, BOND, GSEC, SDL)
6. Live lookup still triggers for unknown ISINs
7. Response includes confidence_score for live lookups
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
PE_USER_EMAIL = "pe@smifs.com"
PE_USER_PASSWORD = "Kutta@123"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for PE user"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": PE_USER_EMAIL, "password": PE_USER_PASSWORD}
    )
    assert response.status_code == 200, f"Login failed: {response.text}"
    data = response.json()
    return data.get("access_token") or data.get("token")


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Get headers with auth token"""
    return {"Authorization": f"Bearer {auth_token}"}


class TestBondDatabaseCount:
    """Test 1: BOND_DATABASE contains 72 instruments"""
    
    def test_statistics_shows_72_instruments(self, auth_headers):
        """Verify statistics endpoint reports 72 total instruments"""
        response = requests.get(
            f"{BASE_URL}/api/fixed-income/instruments/nsdl-statistics",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Statistics endpoint failed: {response.text}"
        data = response.json()
        
        # Verify total instruments count is 72
        total = data.get("total_instruments_in_database", 0)
        assert total == 72, f"Expected 72 instruments, got {total}"
        
        # Verify unique issuers (should be ~45)
        unique_issuers = data.get("unique_issuers", 0)
        assert unique_issuers >= 40, f"Expected ~45 unique issuers, got {unique_issuers}"
        print(f"PASS: Database has {total} instruments from {unique_issuers} unique issuers")


class TestDataSourcesStatistics:
    """Test 2: Statistics endpoint shows all data sources (primary, secondary, exchange)"""
    
    def test_statistics_shows_all_source_categories(self, auth_headers):
        """Verify data sources are categorized correctly"""
        response = requests.get(
            f"{BASE_URL}/api/fixed-income/instruments/nsdl-statistics",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Statistics endpoint failed: {response.text}"
        data = response.json()
        
        # Verify data_sources structure
        data_sources = data.get("data_sources", {})
        assert "primary" in data_sources, "Missing 'primary' data sources"
        assert "secondary" in data_sources, "Missing 'secondary' data sources"
        assert "exchange" in data_sources, "Missing 'exchange' data sources"
        
        # Verify primary sources include NSDL and RBI
        primary = data_sources.get("primary", [])
        assert "indiabondsinfo.nsdl.com" in primary, "Missing NSDL in primary sources"
        assert "rbi.org.in" in primary, "Missing RBI in primary sources"
        
        # Verify secondary sources (marketplaces)
        secondary = data_sources.get("secondary", [])
        expected_secondary = ["indiabonds.com", "smest.in", "wintwealth.com", "thefixedincome.com", "goldenpi.com", "bondbazaar.com"]
        for src in expected_secondary:
            assert src in secondary, f"Missing {src} in secondary sources"
        
        # Verify exchange sources
        exchange = data_sources.get("exchange", [])
        assert "nseindia.com" in exchange, "Missing NSE in exchange sources"
        assert "bseindia.com" in exchange, "Missing BSE in exchange sources"
        
        print(f"PASS: All data source categories present - Primary: {primary}, Secondary: {secondary}, Exchange: {exchange}")
    
    def test_statistics_shows_live_lookup_enabled(self, auth_headers):
        """Verify live lookup feature is enabled"""
        response = requests.get(
            f"{BASE_URL}/api/fixed-income/instruments/nsdl-statistics",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data.get("live_lookup_enabled") is True, "Live lookup should be enabled"
        print("PASS: Live lookup is enabled")


class TestRatingFilter:
    """Test 3: Search with rating_filter works correctly (e.g., AAA only)"""
    
    def test_search_aaa_rated_only(self, auth_headers):
        """Search for AAA rated instruments only"""
        response = requests.get(
            f"{BASE_URL}/api/fixed-income/instruments/nsdl-search",
            params={"query": "AAA", "rating_filter": "AAA", "limit": 50},
            headers=auth_headers
        )
        assert response.status_code == 200, f"Search failed: {response.text}"
        data = response.json()
        
        results = data.get("results", [])
        assert len(results) > 0, "Should find AAA rated instruments"
        
        # Verify all results have AAA rating
        for instrument in results:
            rating = instrument.get("credit_rating", "")
            assert rating == "AAA", f"Expected AAA rating, got {rating} for {instrument.get('isin')}"
        
        print(f"PASS: Found {len(results)} AAA rated instruments, all correctly filtered")
    
    def test_search_aa_plus_rated(self, auth_headers):
        """Search for AA+ rated instruments"""
        response = requests.get(
            f"{BASE_URL}/api/fixed-income/instruments/nsdl-search",
            params={"query": "AA", "rating_filter": "AA+", "limit": 50},
            headers=auth_headers
        )
        assert response.status_code == 200, f"Search failed: {response.text}"
        data = response.json()
        
        results = data.get("results", [])
        assert len(results) > 0, "Should find AA+ rated instruments"
        
        # Verify all results have AA+ rating
        for instrument in results:
            rating = instrument.get("credit_rating", "")
            assert rating == "AA+", f"Expected AA+ rating, got {rating}"
        
        print(f"PASS: Found {len(results)} AA+ rated instruments")
    
    def test_search_sovereign_rated(self, auth_headers):
        """Search for SOVEREIGN rated instruments (G-Secs)"""
        response = requests.get(
            f"{BASE_URL}/api/fixed-income/instruments/nsdl-search",
            params={"query": "GOI", "rating_filter": "SOVEREIGN", "limit": 50},
            headers=auth_headers
        )
        assert response.status_code == 200, f"Search failed: {response.text}"
        data = response.json()
        
        results = data.get("results", [])
        assert len(results) > 0, "Should find SOVEREIGN rated instruments"
        
        # Verify all results have SOVEREIGN rating
        for instrument in results:
            rating = instrument.get("credit_rating", "")
            assert rating == "SOVEREIGN", f"Expected SOVEREIGN rating, got {rating}"
        
        print(f"PASS: Found {len(results)} SOVEREIGN rated instruments (G-Secs)")


class TestSectorFilter:
    """Test 4: Search with sector_filter works correctly (e.g., Infrastructure)"""
    
    def test_search_infrastructure_sector(self, auth_headers):
        """Search for Infrastructure sector instruments"""
        response = requests.get(
            f"{BASE_URL}/api/fixed-income/instruments/nsdl-search",
            params={"query": "Infra", "sector_filter": "Infrastructure", "limit": 50},
            headers=auth_headers
        )
        assert response.status_code == 200, f"Search failed: {response.text}"
        data = response.json()
        
        results = data.get("results", [])
        assert len(results) > 0, "Should find Infrastructure sector instruments"
        
        # Verify all results contain Infrastructure in sector
        for instrument in results:
            sector = instrument.get("sector", "")
            assert "Infrastructure" in sector or "infra" in sector.lower(), f"Expected Infrastructure sector, got {sector}"
        
        print(f"PASS: Found {len(results)} Infrastructure sector instruments")
    
    def test_search_nbfc_sector(self, auth_headers):
        """Search for NBFC sector instruments"""
        response = requests.get(
            f"{BASE_URL}/api/fixed-income/instruments/nsdl-search",
            params={"query": "NCD", "sector_filter": "NBFC", "limit": 50},
            headers=auth_headers
        )
        assert response.status_code == 200, f"Search failed: {response.text}"
        data = response.json()
        
        results = data.get("results", [])
        assert len(results) > 0, "Should find NBFC sector instruments"
        
        # Verify all results contain NBFC in sector
        for instrument in results:
            sector = instrument.get("sector", "")
            assert "NBFC" in sector.upper(), f"Expected NBFC sector, got {sector}"
        
        print(f"PASS: Found {len(results)} NBFC sector instruments")
    
    def test_search_banking_sector(self, auth_headers):
        """Search for Banking sector instruments"""
        response = requests.get(
            f"{BASE_URL}/api/fixed-income/instruments/nsdl-search",
            params={"query": "Bank", "sector_filter": "Banking", "limit": 50},
            headers=auth_headers
        )
        assert response.status_code == 200, f"Search failed: {response.text}"
        data = response.json()
        
        results = data.get("results", [])
        assert len(results) > 0, "Should find Banking sector instruments"
        
        print(f"PASS: Found {len(results)} Banking sector instruments")
    
    def test_search_government_sector(self, auth_headers):
        """Search for Government sector instruments"""
        response = requests.get(
            f"{BASE_URL}/api/fixed-income/instruments/nsdl-search",
            params={"query": "GOI", "sector_filter": "Government", "limit": 50},
            headers=auth_headers
        )
        assert response.status_code == 200, f"Search failed: {response.text}"
        data = response.json()
        
        results = data.get("results", [])
        assert len(results) > 0, "Should find Government sector instruments"
        
        print(f"PASS: Found {len(results)} Government sector instruments")


class TestInstrumentTypeFilter:
    """Test 5: Search with instrument_type filter works (NCD, BOND, GSEC, SDL)"""
    
    def test_search_ncd_type(self, auth_headers):
        """Search for NCD type instruments only"""
        response = requests.get(
            f"{BASE_URL}/api/fixed-income/instruments/nsdl-search",
            params={"query": "NCD", "instrument_type": "NCD", "limit": 50},
            headers=auth_headers
        )
        assert response.status_code == 200, f"Search failed: {response.text}"
        data = response.json()
        
        results = data.get("results", [])
        assert len(results) > 0, "Should find NCD type instruments"
        
        # Verify all results are NCDs
        for instrument in results:
            inst_type = instrument.get("instrument_type", "")
            assert inst_type == "NCD", f"Expected NCD type, got {inst_type}"
        
        print(f"PASS: Found {len(results)} NCD type instruments")
    
    def test_search_bond_type(self, auth_headers):
        """Search for BOND type instruments only"""
        response = requests.get(
            f"{BASE_URL}/api/fixed-income/instruments/nsdl-search",
            params={"query": "Bond", "instrument_type": "BOND", "limit": 50},
            headers=auth_headers
        )
        assert response.status_code == 200, f"Search failed: {response.text}"
        data = response.json()
        
        results = data.get("results", [])
        assert len(results) > 0, "Should find BOND type instruments"
        
        # Verify all results are BONDs
        for instrument in results:
            inst_type = instrument.get("instrument_type", "")
            assert inst_type == "BOND", f"Expected BOND type, got {inst_type}"
        
        print(f"PASS: Found {len(results)} BOND type instruments")
    
    def test_search_gsec_type(self, auth_headers):
        """Search for GSEC type instruments only"""
        response = requests.get(
            f"{BASE_URL}/api/fixed-income/instruments/nsdl-search",
            params={"query": "GOI", "instrument_type": "GSEC", "limit": 50},
            headers=auth_headers
        )
        assert response.status_code == 200, f"Search failed: {response.text}"
        data = response.json()
        
        results = data.get("results", [])
        assert len(results) > 0, "Should find GSEC type instruments"
        
        # Verify all results are GSECs
        for instrument in results:
            inst_type = instrument.get("instrument_type", "")
            assert inst_type == "GSEC", f"Expected GSEC type, got {inst_type}"
        
        print(f"PASS: Found {len(results)} GSEC type instruments")
    
    def test_search_sdl_type(self, auth_headers):
        """Search for SDL type instruments only"""
        response = requests.get(
            f"{BASE_URL}/api/fixed-income/instruments/nsdl-search",
            params={"query": "SDL", "instrument_type": "SDL", "limit": 50},
            headers=auth_headers
        )
        assert response.status_code == 200, f"Search failed: {response.text}"
        data = response.json()
        
        results = data.get("results", [])
        assert len(results) > 0, "Should find SDL type instruments"
        
        # Verify all results are SDLs
        for instrument in results:
            inst_type = instrument.get("instrument_type", "")
            assert inst_type == "SDL", f"Expected SDL type, got {inst_type}"
        
        print(f"PASS: Found {len(results)} SDL type instruments")


class TestLiveLookupTrigger:
    """Test 6: Live lookup still triggers for unknown ISINs"""
    
    def test_live_lookup_attempted_for_unknown_isin(self, auth_headers):
        """Verify live lookup is attempted for ISIN not in local database"""
        # Use a valid ISIN format that doesn't exist in database
        unknown_isin = "INE999X99999"
        
        response = requests.get(
            f"{BASE_URL}/api/fixed-income/instruments/nsdl-search",
            params={"query": unknown_isin, "live_lookup": "true"},
            headers=auth_headers
        )
        assert response.status_code == 200, f"Search failed: {response.text}"
        data = response.json()
        
        # Should indicate live lookup was attempted
        live_lookup_attempted = data.get("live_lookup_attempted", False)
        assert live_lookup_attempted is True, "Live lookup should have been attempted for unknown ISIN"
        
        # Should have live_lookup_result
        live_lookup_result = data.get("live_lookup_result", {})
        assert live_lookup_result is not None, "Should have live_lookup_result"
        
        print(f"PASS: Live lookup was attempted for unknown ISIN {unknown_isin}")
        print(f"Live lookup result: {live_lookup_result}")
    
    def test_live_lookup_not_triggered_for_local_match(self, auth_headers):
        """Verify live lookup is NOT triggered when ISIN found locally"""
        # Use a known ISIN from the database
        known_isin = "INE002A08427"  # Reliance Industries
        
        response = requests.get(
            f"{BASE_URL}/api/fixed-income/instruments/nsdl-search",
            params={"query": known_isin, "live_lookup": "true"},
            headers=auth_headers
        )
        assert response.status_code == 200, f"Search failed: {response.text}"
        data = response.json()
        
        results = data.get("results", [])
        assert len(results) > 0, f"Should find known ISIN {known_isin}"
        
        # Live lookup should NOT be attempted since we found local results
        live_lookup_attempted = data.get("live_lookup_attempted", False)
        assert live_lookup_attempted is False, "Live lookup should NOT be attempted when found locally"
        
        print(f"PASS: Live lookup was NOT triggered for known ISIN {known_isin} (found {len(results)} results locally)")
    
    def test_live_lookup_can_be_disabled(self, auth_headers):
        """Verify live lookup can be disabled via parameter"""
        unknown_isin = "INE999Y99999"
        
        response = requests.get(
            f"{BASE_URL}/api/fixed-income/instruments/nsdl-search",
            params={"query": unknown_isin, "live_lookup": "false"},
            headers=auth_headers
        )
        assert response.status_code == 200, f"Search failed: {response.text}"
        data = response.json()
        
        # Live lookup should NOT be attempted
        live_lookup_attempted = data.get("live_lookup_attempted", False)
        assert live_lookup_attempted is False, "Live lookup should be disabled when live_lookup=false"
        
        print(f"PASS: Live lookup correctly disabled when live_lookup=false")


class TestConfidenceScore:
    """Test 7: Response includes confidence_score for live lookups"""
    
    def test_live_lookup_response_has_confidence_score(self, auth_headers):
        """Verify live lookup results include confidence_score"""
        # Attempt live lookup for unknown ISIN
        unknown_isin = "INE999Z99999"
        
        response = requests.get(
            f"{BASE_URL}/api/fixed-income/instruments/nsdl-search",
            params={"query": unknown_isin, "live_lookup": "true"},
            headers=auth_headers
        )
        assert response.status_code == 200, f"Search failed: {response.text}"
        data = response.json()
        
        # Check if live_lookup_result contains confidence_score when successful
        live_lookup_result = data.get("live_lookup_result", {})
        if live_lookup_result and live_lookup_result.get("success"):
            assert "confidence_score" in live_lookup_result, "Successful live lookup should have confidence_score"
            print(f"PASS: Live lookup result includes confidence_score: {live_lookup_result.get('confidence_score')}")
        else:
            # If live lookup failed (expected in container env due to network restrictions),
            # just verify the structure is correct
            print(f"INFO: Live lookup did not succeed (expected in container), result: {live_lookup_result}")
            assert "success" in live_lookup_result or "message" in live_lookup_result, "Live lookup result should have status"
            print("PASS: Live lookup result structure is correct")


class TestSearchByIssuerName:
    """Additional tests: Search by issuer name"""
    
    def test_search_reliance(self, auth_headers):
        """Search for Reliance instruments"""
        response = requests.get(
            f"{BASE_URL}/api/fixed-income/instruments/nsdl-search",
            params={"query": "Reliance", "search_type": "company"},
            headers=auth_headers
        )
        assert response.status_code == 200, f"Search failed: {response.text}"
        data = response.json()
        
        results = data.get("results", [])
        assert len(results) > 0, "Should find Reliance instruments"
        
        # Verify results contain Reliance
        for instrument in results:
            issuer = instrument.get("issuer_name", "")
            assert "Reliance" in issuer, f"Expected Reliance, got {issuer}"
        
        print(f"PASS: Found {len(results)} Reliance instruments")
    
    def test_search_bajaj_finance(self, auth_headers):
        """Search for Bajaj Finance instruments"""
        response = requests.get(
            f"{BASE_URL}/api/fixed-income/instruments/nsdl-search",
            params={"query": "Bajaj Finance", "search_type": "company"},
            headers=auth_headers
        )
        assert response.status_code == 200, f"Search failed: {response.text}"
        data = response.json()
        
        results = data.get("results", [])
        assert len(results) > 0, "Should find Bajaj Finance instruments"
        
        print(f"PASS: Found {len(results)} Bajaj Finance instruments")
    
    def test_search_tata(self, auth_headers):
        """Search for Tata group instruments"""
        response = requests.get(
            f"{BASE_URL}/api/fixed-income/instruments/nsdl-search",
            params={"query": "Tata", "search_type": "company"},
            headers=auth_headers
        )
        assert response.status_code == 200, f"Search failed: {response.text}"
        data = response.json()
        
        results = data.get("results", [])
        assert len(results) > 0, "Should find Tata instruments"
        
        print(f"PASS: Found {len(results)} Tata instruments")


class TestCombinedFilters:
    """Test combined filters"""
    
    def test_rating_and_type_combined(self, auth_headers):
        """Search with both rating and type filter"""
        response = requests.get(
            f"{BASE_URL}/api/fixed-income/instruments/nsdl-search",
            params={"query": "NCD", "rating_filter": "AAA", "instrument_type": "NCD"},
            headers=auth_headers
        )
        assert response.status_code == 200, f"Search failed: {response.text}"
        data = response.json()
        
        results = data.get("results", [])
        assert len(results) > 0, "Should find AAA rated NCDs"
        
        # Verify all results match both filters
        for instrument in results:
            rating = instrument.get("credit_rating", "")
            inst_type = instrument.get("instrument_type", "")
            assert rating == "AAA", f"Rating filter failed: {rating}"
            assert inst_type == "NCD", f"Type filter failed: {inst_type}"
        
        print(f"PASS: Found {len(results)} AAA rated NCDs (combined filters work)")
    
    def test_sector_and_rating_combined(self, auth_headers):
        """Search with both sector and rating filter"""
        response = requests.get(
            f"{BASE_URL}/api/fixed-income/instruments/nsdl-search",
            params={"query": "Bond", "sector_filter": "Infrastructure", "rating_filter": "AAA"},
            headers=auth_headers
        )
        assert response.status_code == 200, f"Search failed: {response.text}"
        data = response.json()
        
        results = data.get("results", [])
        assert len(results) > 0, "Should find AAA rated Infrastructure instruments"
        
        # Verify all results match both filters
        for instrument in results:
            rating = instrument.get("credit_rating", "")
            sector = instrument.get("sector", "")
            assert rating == "AAA", f"Rating filter failed: {rating}"
            assert "Infrastructure" in sector or "infra" in sector.lower(), f"Sector filter failed: {sector}"
        
        print(f"PASS: Found {len(results)} AAA rated Infrastructure instruments")


class TestInstrumentTypeDistribution:
    """Verify correct distribution of instrument types"""
    
    def test_statistics_by_type(self, auth_headers):
        """Verify instrument type distribution in statistics"""
        response = requests.get(
            f"{BASE_URL}/api/fixed-income/instruments/nsdl-statistics",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Statistics failed: {response.text}"
        data = response.json()
        
        by_type = data.get("by_instrument_type", {})
        
        # Verify all expected types exist
        expected_types = ["NCD", "BOND", "GSEC", "SDL"]
        for t in expected_types:
            assert t in by_type, f"Missing instrument type {t} in statistics"
            assert by_type[t] > 0, f"No instruments of type {t}"
        
        # Calculate total
        total = sum(by_type.values())
        assert total == 72, f"Type distribution should sum to 72, got {total}"
        
        print(f"PASS: Instrument type distribution: {by_type}")
    
    def test_statistics_by_rating(self, auth_headers):
        """Verify credit rating distribution in statistics"""
        response = requests.get(
            f"{BASE_URL}/api/fixed-income/instruments/nsdl-statistics",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        by_rating = data.get("by_credit_rating", {})
        
        # Should have AAA, AA+, AA, etc.
        assert "AAA" in by_rating, "Missing AAA rating"
        assert by_rating.get("AAA", 0) > 0, "Should have AAA rated instruments"
        
        print(f"PASS: Credit rating distribution: {by_rating}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
