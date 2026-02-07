"""
Fixed Income Module - Backend API Tests

Tests for:
- Instrument CRUD (Security Master)
- Pricing calculations (YTM, Dirty Price)
- Order management
- Reports endpoints
- Market data refresh

Note: Market data uses MOCK provider for simulated quotes (not real market data)
"""

import pytest
import requests
import os
from datetime import date, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
HEADERS = {
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

# Test credentials
TEST_EMAIL = "pe@smifs.com"
TEST_PASSWORD = "Kutta@123"

# Track created resources for cleanup
created_instruments = []
created_orders = []


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
        headers=HEADERS
    )
    if response.status_code == 200:
        data = response.json()
        token = data.get("token")  # Note: API returns 'token' not 'access_token'
        if token:
            return token
    pytest.skip(f"Authentication failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Get headers with authentication"""
    return {
        **HEADERS,
        "Authorization": f"Bearer {auth_token}"
    }


class TestHealthCheck:
    """Verify backend is running"""
    
    def test_health_endpoint(self):
        """Test health endpoint"""
        response = requests.get(f"{BASE_URL}/api/health", headers=HEADERS)
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "ok"
        print("Health check passed")


class TestFixedIncomeInstruments:
    """Test Fixed Income Security Master API"""
    
    def test_list_instruments_unauthorized(self):
        """Test listing instruments without auth returns 403"""
        response = requests.get(f"{BASE_URL}/api/fixed-income/instruments", headers=HEADERS)
        # Bot protection returns 403 for unauthorized
        assert response.status_code in [401, 403]
        print("Unauthorized access correctly blocked")
    
    def test_list_instruments(self, auth_headers):
        """Test listing instruments with auth"""
        response = requests.get(f"{BASE_URL}/api/fixed-income/instruments", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "instruments" in data
        assert "total" in data
        assert "skip" in data
        assert "limit" in data
        print(f"Listed {data['total']} instruments successfully")
    
    def test_list_instruments_with_filters(self, auth_headers):
        """Test listing instruments with type filter"""
        response = requests.get(
            f"{BASE_URL}/api/fixed-income/instruments?instrument_type=NCD&limit=10",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "instruments" in data
        print(f"Filtered list returned {len(data['instruments'])} NCDs")
    
    def test_create_instrument(self, auth_headers):
        """Test creating a new instrument"""
        global created_instruments
        
        # Generate unique ISIN for test
        test_isin = f"INE999T{date.today().strftime('%Y%m%d')[:6]}01"
        
        payload = {
            "isin": test_isin,
            "instrument_type": "NCD",
            "issuer_name": "TEST_Automation Corp Ltd",
            "issuer_code": "TESTCORP",
            "face_value": 1000,
            "issue_date": "2024-01-15",
            "maturity_date": "2027-01-15",
            "coupon_rate": 9.50,
            "coupon_frequency": "annual",
            "day_count_convention": "ACT/365",
            "credit_rating": "AA+",
            "rating_agency": "CRISIL",
            "current_market_price": 1050.00,
            "lot_size": 1
        }
        
        response = requests.post(
            f"{BASE_URL}/api/fixed-income/instruments",
            json=payload,
            headers=auth_headers
        )
        
        if response.status_code == 400 and "already exists" in response.text.lower():
            print(f"Instrument {test_isin} already exists - skipping create")
            pytest.skip("Instrument already exists")
        
        assert response.status_code in [200, 201], f"Create failed: {response.text}"
        data = response.json()
        assert "id" in data or "isin" in data
        created_instruments.append(test_isin)
        print(f"Created instrument: {test_isin}")
    
    def test_get_instrument_by_isin(self, auth_headers):
        """Test getting instrument details by ISIN"""
        # First get list to find an ISIN
        response = requests.get(
            f"{BASE_URL}/api/fixed-income/instruments?limit=1",
            headers=auth_headers
        )
        if response.status_code != 200 or not response.json().get("instruments"):
            pytest.skip("No instruments available for testing")
        
        isin = response.json()["instruments"][0]["isin"]
        
        # Get by ISIN
        response = requests.get(
            f"{BASE_URL}/api/fixed-income/instruments/{isin}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["isin"] == isin
        assert "issuer_name" in data
        print(f"Retrieved instrument details for {isin}")


class TestPricingCalculations:
    """Test Fixed Income Pricing & Calculation Engine"""
    
    def test_calculate_pricing(self, auth_headers):
        """Test pricing calculation from clean price"""
        # First get an instrument ISIN
        response = requests.get(
            f"{BASE_URL}/api/fixed-income/instruments?limit=1",
            headers=auth_headers
        )
        if response.status_code != 200 or not response.json().get("instruments"):
            pytest.skip("No instruments available for pricing test")
        
        instrument = response.json()["instruments"][0]
        isin = instrument["isin"]
        clean_price = float(instrument.get("current_market_price") or 1000)
        
        # Calculate pricing
        response = requests.post(
            f"{BASE_URL}/api/fixed-income/instruments/calculate-pricing",
            params={
                "isin": isin,
                "clean_price": clean_price,
                "settlement_date": date.today().isoformat()
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200, f"Pricing calc failed: {response.text}"
        data = response.json()
        
        # Validate response structure
        assert "isin" in data
        assert "clean_price" in data
        assert "accrued_interest" in data
        assert "dirty_price" in data
        assert "ytm" in data
        
        print(f"Calculated pricing for {isin}:")
        print(f"  Clean Price: {data['clean_price']}")
        print(f"  Accrued Interest: {data['accrued_interest']}")
        print(f"  Dirty Price: {data['dirty_price']}")
        print(f"  YTM: {data['ytm']}%")
    
    def test_price_from_yield(self, auth_headers):
        """Test reverse calculation - price from target YTM"""
        # First get an instrument ISIN
        response = requests.get(
            f"{BASE_URL}/api/fixed-income/instruments?limit=1",
            headers=auth_headers
        )
        if response.status_code != 200 or not response.json().get("instruments"):
            pytest.skip("No instruments available for price-from-yield test")
        
        isin = response.json()["instruments"][0]["isin"]
        
        # Calculate price from yield
        target_ytm = 9.0  # 9% yield
        response = requests.post(
            f"{BASE_URL}/api/fixed-income/instruments/price-from-yield",
            params={
                "isin": isin,
                "target_ytm": target_ytm,
                "settlement_date": date.today().isoformat()
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200, f"Price from yield failed: {response.text}"
        data = response.json()
        
        assert "isin" in data
        assert "target_ytm" in data
        assert "clean_price" in data
        assert "dirty_price" in data
        
        print(f"Price from yield for {isin}:")
        print(f"  Target YTM: {data['target_ytm']}%")
        print(f"  Clean Price: {data['clean_price']}")


class TestFixedIncomeOrders:
    """Test Fixed Income Order Management System"""
    
    def test_list_orders_unauthorized(self):
        """Test listing orders without auth"""
        response = requests.get(f"{BASE_URL}/api/fixed-income/orders", headers=HEADERS)
        assert response.status_code in [401, 403]
        print("Orders endpoint correctly protected")
    
    def test_list_orders(self, auth_headers):
        """Test listing orders with auth"""
        response = requests.get(f"{BASE_URL}/api/fixed-income/orders", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "orders" in data
        assert "total" in data
        print(f"Listed {data['total']} orders")
    
    def test_list_orders_with_status_filter(self, auth_headers):
        """Test listing orders filtered by status"""
        response = requests.get(
            f"{BASE_URL}/api/fixed-income/orders?status=draft",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "orders" in data
        print(f"Filtered orders by status 'draft': {len(data['orders'])} found")
    
    def test_create_order_requires_valid_client(self, auth_headers):
        """Test order creation validates client"""
        # First get an instrument
        response = requests.get(
            f"{BASE_URL}/api/fixed-income/instruments?limit=1",
            headers=auth_headers
        )
        if response.status_code != 200 or not response.json().get("instruments"):
            pytest.skip("No instruments available")
        
        isin = response.json()["instruments"][0]["isin"]
        
        # Try to create order with invalid client
        payload = {
            "client_id": "invalid-client-id-12345",
            "isin": isin,
            "order_type": "secondary_buy",
            "quantity": 10,
            "clean_price": 1000.00,
            "settlement_date": (date.today() + timedelta(days=2)).isoformat()
        }
        
        response = requests.post(
            f"{BASE_URL}/api/fixed-income/orders",
            json=payload,
            headers=auth_headers
        )
        
        # Should fail with 404 for invalid client or 400/422 for validation
        assert response.status_code in [404, 400, 422]
        print("Order creation correctly validates client")


class TestFixedIncomeReports:
    """Test Fixed Income Reports API"""
    
    def test_holdings_report_requires_client(self, auth_headers):
        """Test holdings report requires client_id for non-PE users"""
        response = requests.get(
            f"{BASE_URL}/api/fixed-income/reports/holdings",
            headers=auth_headers
        )
        # PE level users should get empty response or data
        # Non-PE users should get error about needing client_id
        assert response.status_code in [200, 400]
        print("Holdings report endpoint accessible")
    
    def test_cash_flow_calendar(self, auth_headers):
        """Test cash flow calendar endpoint"""
        # Get a client first - API returns list directly, not {"clients": [...]}
        client_response = requests.get(
            f"{BASE_URL}/api/clients?limit=1",
            headers=auth_headers
        )
        
        if client_response.status_code != 200:
            pytest.skip("Failed to fetch clients")
        
        clients_data = client_response.json()
        # Handle both list and dict response formats
        if isinstance(clients_data, list):
            clients = clients_data
        else:
            clients = clients_data.get("clients", [])
        
        if not clients:
            pytest.skip("No clients available for cash flow test")
        
        client_id = clients[0]["id"]
        
        response = requests.get(
            f"{BASE_URL}/api/fixed-income/reports/cash-flow-calendar?client_id={client_id}&months_ahead=12",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "client_id" in data
        assert "cash_flows" in data
        assert "summary" in data
        print(f"Cash flow calendar returned {len(data['cash_flows'])} entries")
    
    def test_maturity_schedule(self, auth_headers):
        """Test maturity schedule endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/fixed-income/reports/maturity-schedule?months_ahead=24",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "maturities" in data
        assert "total_principal" in data
        print(f"Maturity schedule returned {data.get('count', 0)} maturities")
    
    def test_portfolio_analytics(self, auth_headers):
        """Test portfolio analytics endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/fixed-income/reports/analytics/portfolio-summary",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        # Should return either analytics data or "No holdings found" message
        assert "message" in data or "total_portfolio_value" in data
        print(f"Portfolio analytics: {data}")
    
    def test_transactions_report(self, auth_headers):
        """Test transactions history endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/fixed-income/reports/transactions?limit=10",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "transactions" in data
        assert "total" in data
        print(f"Transactions report: {data['total']} total transactions")


class TestMarketDataService:
    """Test Market Data Integration (uses MOCK provider)"""
    
    def test_market_data_refresh(self, auth_headers):
        """Test market data refresh endpoint (MOCKED)"""
        response = requests.post(
            f"{BASE_URL}/api/fixed-income/market-data/refresh",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "refresh" in data["message"].lower() or "initiated" in data["message"].lower()
        print(f"Market data refresh: {data['message']} (MOCK provider)")
    
    def test_get_market_quote(self, auth_headers):
        """Test getting market quote for an instrument (MOCKED)"""
        # First get an instrument ISIN
        response = requests.get(
            f"{BASE_URL}/api/fixed-income/instruments?limit=1",
            headers=auth_headers
        )
        if response.status_code != 200 or not response.json().get("instruments"):
            pytest.skip("No instruments available for quote test")
        
        isin = response.json()["instruments"][0]["isin"]
        
        # Get quote
        response = requests.get(
            f"{BASE_URL}/api/fixed-income/market-data/quote/{isin}",
            headers=auth_headers
        )
        
        assert response.status_code == 200, f"Quote failed: {response.text}"
        data = response.json()
        assert "isin" in data
        assert "last_price" in data
        assert "exchange" in data
        # MOCK provider returns "MOCK" as exchange
        print(f"Market quote for {isin}: Price={data['last_price']}, Exchange={data['exchange']} (MOCKED)")


class TestCleanup:
    """Cleanup test data"""
    
    def test_cleanup_instruments(self, auth_headers):
        """Clean up test-created instruments"""
        global created_instruments
        
        for isin in created_instruments:
            try:
                response = requests.delete(
                    f"{BASE_URL}/api/fixed-income/instruments/{isin}",
                    headers=auth_headers
                )
                print(f"Cleanup: Deactivated instrument {isin} - Status: {response.status_code}")
            except Exception as e:
                print(f"Cleanup error for {isin}: {e}")
        
        created_instruments = []


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
