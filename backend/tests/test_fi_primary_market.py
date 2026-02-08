"""
Fixed Income - Primary Market (IPO/NFO) API Tests

Tests for:
- Issue CRUD operations (Create, List, Get, Update Status)
- Bid submission and listing
- Allotment processing
- Active issues endpoint
"""

import pytest
import requests
import os
import uuid
from datetime import date, timedelta

# Base URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_EMAIL = "pe@smifs.com"
TEST_PASSWORD = "Kutta@123"

# Headers with User-Agent to bypass bot protection
HEADERS = {
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}


class TestAuthSetup:
    """Authentication setup for all tests"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
            headers=HEADERS
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "token" in data, f"No token in response: {data}"
        return data["token"]
    
    @pytest.fixture(scope="class")
    def api_client(self, auth_token):
        """Create authenticated session"""
        session = requests.Session()
        session.headers.update({
            **HEADERS,
            "Authorization": f"Bearer {auth_token}"
        })
        return session


class TestPrimaryMarketIssues(TestAuthSetup):
    """Test Issue CRUD operations"""
    
    def test_list_issues(self, api_client):
        """GET /api/fixed-income/primary-market/issues - List all issues"""
        response = api_client.get(f"{BASE_URL}/api/fixed-income/primary-market/issues")
        assert response.status_code == 200, f"Failed to list issues: {response.text}"
        
        data = response.json()
        assert "issues" in data
        assert "total" in data
        assert isinstance(data["issues"], list)
        print(f"Found {len(data['issues'])} existing issues")
    
    def test_create_issue(self, api_client):
        """POST /api/fixed-income/primary-market/issues - Create new issue"""
        # Generate unique ISIN for test
        test_isin = f"INE{uuid.uuid4().hex[:6].upper()}01010"
        
        # Set dates in future for valid subscription window
        today = date.today()
        open_date = today + timedelta(days=1)
        close_date = today + timedelta(days=15)
        maturity_date = today + timedelta(days=365*3)
        
        issue_data = {
            "isin": test_isin,
            "issuer_name": "TEST Corp Ltd",
            "issue_name": f"TEST NCD Tranche I - {uuid.uuid4().hex[:6]}",
            "issue_type": "NCD",
            "face_value": "1000",
            "issue_price": "1000",
            "coupon_rate": "9.5",
            "coupon_frequency": "annual",
            "tenure_years": 3,
            "maturity_date": maturity_date.isoformat(),
            "credit_rating": "AA",
            "rating_agency": "CRISIL",
            "issue_open_date": open_date.isoformat(),
            "issue_close_date": close_date.isoformat(),
            "min_application_size": 10,
            "lot_size": 1,
            "base_issue_size": "100"
        }
        
        response = api_client.post(
            f"{BASE_URL}/api/fixed-income/primary-market/issues",
            json=issue_data
        )
        
        assert response.status_code == 200, f"Failed to create issue: {response.text}"
        
        data = response.json()
        assert "issue_id" in data
        assert "issue_number" in data
        assert data["message"] == "Issue created"
        
        print(f"Created issue: {data['issue_number']} (ID: {data['issue_id']})")
        
        # Store for other tests
        TestPrimaryMarketIssues.created_issue_id = data["issue_id"]
        TestPrimaryMarketIssues.created_issue_number = data["issue_number"]
        
        return data["issue_id"]
    
    def test_get_issue_by_id(self, api_client):
        """GET /api/fixed-income/primary-market/issues/{id} - Get issue details"""
        # Use previously created issue or skip
        issue_id = getattr(TestPrimaryMarketIssues, 'created_issue_id', None)
        if not issue_id:
            pytest.skip("No issue created yet")
        
        response = api_client.get(f"{BASE_URL}/api/fixed-income/primary-market/issues/{issue_id}")
        assert response.status_code == 200, f"Failed to get issue: {response.text}"
        
        data = response.json()
        assert data["id"] == issue_id
        assert data["status"] == "draft"  # New issues start as draft
        assert "issuer_name" in data
        assert "coupon_rate" in data
        print(f"Got issue: {data['issue_name']} - Status: {data['status']}")
    
    def test_update_issue_status_draft_to_open(self, api_client):
        """PATCH /api/fixed-income/primary-market/issues/{id}/status - Open issue"""
        issue_id = getattr(TestPrimaryMarketIssues, 'created_issue_id', None)
        if not issue_id:
            pytest.skip("No issue created yet")
        
        response = api_client.patch(
            f"{BASE_URL}/api/fixed-income/primary-market/issues/{issue_id}/status?new_status=open"
        )
        
        assert response.status_code == 200, f"Failed to update status: {response.text}"
        
        data = response.json()
        assert data["message"] == "Status updated to open"
        print(f"Issue {issue_id} status updated to OPEN")
    
    def test_get_active_issues(self, api_client):
        """GET /api/fixed-income/primary-market/active-issues - Get open issues"""
        response = api_client.get(f"{BASE_URL}/api/fixed-income/primary-market/active-issues")
        assert response.status_code == 200, f"Failed to get active issues: {response.text}"
        
        data = response.json()
        assert "issues" in data
        assert "count" in data
        
        # Note: Active issues filter by date, so our test issue might not show
        # if open_date is in the future
        print(f"Found {data['count']} active issues (within subscription window)")
    
    def test_list_issues_with_status_filter(self, api_client):
        """GET /api/fixed-income/primary-market/issues?status=open"""
        response = api_client.get(f"{BASE_URL}/api/fixed-income/primary-market/issues?status=open")
        assert response.status_code == 200, f"Failed to filter issues: {response.text}"
        
        data = response.json()
        assert "issues" in data
        
        # All returned issues should be 'open'
        for issue in data["issues"]:
            assert issue["status"] == "open", f"Got non-open issue: {issue['status']}"
        
        print(f"Found {len(data['issues'])} open issues")


class TestPrimaryMarketBids(TestAuthSetup):
    """Test Bid submission and listing"""
    
    @pytest.fixture(scope="class")
    def test_client(self, api_client):
        """Get or create a test client for bid submission"""
        # First try to get existing client
        response = api_client.get(f"{BASE_URL}/api/clients?limit=1")
        if response.status_code == 200:
            data = response.json()
            if data.get("clients") and len(data["clients"]) > 0:
                return data["clients"][0]
        
        # Create a test client if none exists
        client_data = {
            "name": "TEST Investor - Primary Market",
            "pan_number": f"TEST{uuid.uuid4().hex[:5].upper()}P",
            "email": "test.investor@example.com",
            "mobile": "9999999999"
        }
        
        response = api_client.post(f"{BASE_URL}/api/clients", json=client_data)
        if response.status_code in [200, 201]:
            return response.json().get("client", response.json())
        
        pytest.skip("Could not create/get test client")
    
    @pytest.fixture(scope="class")
    def open_issue(self, api_client):
        """Get or create an open issue for testing bids"""
        # Check for existing open issue
        response = api_client.get(f"{BASE_URL}/api/fixed-income/primary-market/issues?status=open")
        if response.status_code == 200:
            data = response.json()
            if data.get("issues") and len(data["issues"]) > 0:
                return data["issues"][0]
        
        # Create a new issue and open it
        today = date.today()
        test_isin = f"INE{uuid.uuid4().hex[:6].upper()}02010"
        
        issue_data = {
            "isin": test_isin,
            "issuer_name": "TEST Bid Corp",
            "issue_name": f"TEST BID NCD - {uuid.uuid4().hex[:4]}",
            "issue_type": "NCD",
            "face_value": "1000",
            "issue_price": "1000",
            "coupon_rate": "10",
            "coupon_frequency": "annual",
            "tenure_years": 3,
            "maturity_date": (today + timedelta(days=365*3)).isoformat(),
            "credit_rating": "AA",
            "rating_agency": "CRISIL",
            "issue_open_date": (today - timedelta(days=1)).isoformat(),  # Already open
            "issue_close_date": (today + timedelta(days=30)).isoformat(),
            "min_application_size": 1,
            "lot_size": 1,
            "base_issue_size": "100"
        }
        
        response = api_client.post(f"{BASE_URL}/api/fixed-income/primary-market/issues", json=issue_data)
        if response.status_code != 200:
            pytest.skip(f"Failed to create issue for bid testing: {response.text}")
        
        issue_id = response.json()["issue_id"]
        
        # Open the issue
        api_client.patch(f"{BASE_URL}/api/fixed-income/primary-market/issues/{issue_id}/status?new_status=open")
        
        # Get the full issue
        response = api_client.get(f"{BASE_URL}/api/fixed-income/primary-market/issues/{issue_id}")
        return response.json()
    
    def test_list_bids_empty_or_existing(self, api_client):
        """GET /api/fixed-income/primary-market/bids - List all bids"""
        response = api_client.get(f"{BASE_URL}/api/fixed-income/primary-market/bids")
        assert response.status_code == 200, f"Failed to list bids: {response.text}"
        
        data = response.json()
        assert "bids" in data
        assert "total" in data
        print(f"Found {len(data['bids'])} existing bids")
    
    def test_submit_bid(self, api_client, test_client, open_issue):
        """POST /api/fixed-income/primary-market/bids - Submit a bid"""
        bid_data = {
            "issue_id": open_issue["id"],
            "client_id": test_client["id"],
            "category": "retail",
            "quantity": 10,
            "price": float(open_issue.get("issue_price", 1000)),
            "payment_mode": "upi",
            "upi_id": "test@ybl"
        }
        
        response = api_client.post(f"{BASE_URL}/api/fixed-income/primary-market/bids", json=bid_data)
        assert response.status_code == 200, f"Failed to submit bid: {response.text}"
        
        data = response.json()
        assert "bid_id" in data
        assert "bid_number" in data
        assert data["message"] == "Bid submitted successfully"
        
        print(f"Submitted bid: {data['bid_number']} for amount {data['amount']}")
        
        # Store for subsequent tests
        TestPrimaryMarketBids.created_bid_id = data["bid_id"]
        TestPrimaryMarketBids.created_bid_number = data["bid_number"]
        TestPrimaryMarketBids.test_issue_id = open_issue["id"]
    
    def test_list_bids_with_issue_filter(self, api_client):
        """GET /api/fixed-income/primary-market/bids?issue_id=xxx"""
        issue_id = getattr(TestPrimaryMarketBids, 'test_issue_id', None)
        if not issue_id:
            pytest.skip("No issue available for filtering")
        
        response = api_client.get(f"{BASE_URL}/api/fixed-income/primary-market/bids?issue_id={issue_id}")
        assert response.status_code == 200, f"Failed to filter bids: {response.text}"
        
        data = response.json()
        assert "bids" in data
        
        # All bids should be for the specified issue
        for bid in data["bids"]:
            assert bid["issue_id"] == issue_id
        
        print(f"Found {len(data['bids'])} bids for issue {issue_id}")
    
    def test_submit_bid_invalid_issue(self, api_client, test_client):
        """POST /api/fixed-income/primary-market/bids - Invalid issue should fail"""
        bid_data = {
            "issue_id": "non-existent-issue-id",
            "client_id": test_client["id"],
            "category": "retail",
            "quantity": 10,
            "price": 1000,
            "payment_mode": "upi"
        }
        
        response = api_client.post(f"{BASE_URL}/api/fixed-income/primary-market/bids", json=bid_data)
        assert response.status_code == 404, f"Should fail for invalid issue: {response.text}"
    
    def test_submit_bid_invalid_client(self, api_client, open_issue):
        """POST /api/fixed-income/primary-market/bids - Invalid client should fail"""
        bid_data = {
            "issue_id": open_issue["id"],
            "client_id": "non-existent-client-id",
            "category": "retail",
            "quantity": 10,
            "price": float(open_issue.get("issue_price", 1000)),
            "payment_mode": "upi"
        }
        
        response = api_client.post(f"{BASE_URL}/api/fixed-income/primary-market/bids", json=bid_data)
        assert response.status_code == 404, f"Should fail for invalid client: {response.text}"


class TestIssueStatusWorkflow(TestAuthSetup):
    """Test issue status transitions"""
    
    def test_invalid_status_update(self, api_client):
        """PATCH status with invalid value should fail"""
        # Create a test issue
        today = date.today()
        test_isin = f"INE{uuid.uuid4().hex[:6].upper()}03010"
        
        issue_data = {
            "isin": test_isin,
            "issuer_name": "TEST Status Corp",
            "issue_name": f"TEST STATUS NCD - {uuid.uuid4().hex[:4]}",
            "issue_type": "NCD",
            "face_value": "1000",
            "issue_price": "1000",
            "coupon_rate": "9",
            "coupon_frequency": "quarterly",
            "tenure_years": 2,
            "maturity_date": (today + timedelta(days=730)).isoformat(),
            "credit_rating": "A+",
            "rating_agency": "ICRA",
            "issue_open_date": (today + timedelta(days=5)).isoformat(),
            "issue_close_date": (today + timedelta(days=20)).isoformat(),
            "min_application_size": 5,
            "lot_size": 1,
            "base_issue_size": "50"
        }
        
        response = api_client.post(f"{BASE_URL}/api/fixed-income/primary-market/issues", json=issue_data)
        if response.status_code != 200:
            pytest.skip(f"Failed to create test issue: {response.text}")
        
        issue_id = response.json()["issue_id"]
        
        # Try invalid status
        response = api_client.patch(
            f"{BASE_URL}/api/fixed-income/primary-market/issues/{issue_id}/status?new_status=invalid_status"
        )
        assert response.status_code == 400, f"Should reject invalid status: {response.text}"
        print("Invalid status correctly rejected")
    
    def test_status_workflow_draft_to_closed(self, api_client):
        """Test full status workflow: draft -> open -> closed"""
        # Create a test issue
        today = date.today()
        test_isin = f"INE{uuid.uuid4().hex[:6].upper()}04010"
        
        issue_data = {
            "isin": test_isin,
            "issuer_name": "TEST Workflow Corp",
            "issue_name": f"TEST WORKFLOW NCD - {uuid.uuid4().hex[:4]}",
            "issue_type": "BOND",
            "face_value": "1000",
            "issue_price": "1000",
            "coupon_rate": "8.5",
            "coupon_frequency": "semi_annual",
            "tenure_years": 5,
            "maturity_date": (today + timedelta(days=365*5)).isoformat(),
            "credit_rating": "AAA",
            "rating_agency": "CRISIL",
            "issue_open_date": (today - timedelta(days=1)).isoformat(),
            "issue_close_date": (today + timedelta(days=30)).isoformat(),
            "min_application_size": 1,
            "lot_size": 1,
            "base_issue_size": "200"
        }
        
        response = api_client.post(f"{BASE_URL}/api/fixed-income/primary-market/issues", json=issue_data)
        assert response.status_code == 200, f"Failed to create issue: {response.text}"
        issue_id = response.json()["issue_id"]
        
        # Verify initial status is draft
        response = api_client.get(f"{BASE_URL}/api/fixed-income/primary-market/issues/{issue_id}")
        assert response.json()["status"] == "draft"
        print("Issue created in DRAFT status")
        
        # Transition to open
        response = api_client.patch(
            f"{BASE_URL}/api/fixed-income/primary-market/issues/{issue_id}/status?new_status=open"
        )
        assert response.status_code == 200
        
        response = api_client.get(f"{BASE_URL}/api/fixed-income/primary-market/issues/{issue_id}")
        assert response.json()["status"] == "open"
        print("Status updated to OPEN")
        
        # Transition to closed
        response = api_client.patch(
            f"{BASE_URL}/api/fixed-income/primary-market/issues/{issue_id}/status?new_status=closed"
        )
        assert response.status_code == 200
        
        response = api_client.get(f"{BASE_URL}/api/fixed-income/primary-market/issues/{issue_id}")
        assert response.json()["status"] == "closed"
        print("Status updated to CLOSED")
        
        # Store for allotment test
        TestIssueStatusWorkflow.closed_issue_id = issue_id


class TestAllotmentProcessing(TestAuthSetup):
    """Test allotment processing"""
    
    def test_allotment_requires_closed_status(self, api_client):
        """Process allotment should fail if issue is not closed"""
        # Get an open issue
        response = api_client.get(f"{BASE_URL}/api/fixed-income/primary-market/issues?status=open&limit=1")
        if response.status_code != 200 or not response.json().get("issues"):
            pytest.skip("No open issues to test allotment failure")
        
        issue = response.json()["issues"][0]
        
        # Try to process allotment on open issue
        response = api_client.post(
            f"{BASE_URL}/api/fixed-income/primary-market/issues/{issue['id']}/process-allotment"
        )
        assert response.status_code == 400, f"Should fail for non-closed issue: {response.text}"
        assert "must be closed" in response.json().get("detail", "").lower()
        print("Allotment correctly rejected for non-closed issue")
    
    def test_allotment_full_flow(self, api_client):
        """Test complete allotment flow with a confirmed bid"""
        today = date.today()
        test_isin = f"INE{uuid.uuid4().hex[:6].upper()}05010"
        
        # 1. Create issue
        issue_data = {
            "isin": test_isin,
            "issuer_name": "TEST Allotment Corp",
            "issue_name": f"TEST ALLOT NCD - {uuid.uuid4().hex[:4]}",
            "issue_type": "NCD",
            "face_value": "1000",
            "issue_price": "1000",
            "coupon_rate": "9",
            "coupon_frequency": "annual",
            "tenure_years": 3,
            "maturity_date": (today + timedelta(days=365*3)).isoformat(),
            "credit_rating": "AA",
            "rating_agency": "CRISIL",
            "issue_open_date": (today - timedelta(days=1)).isoformat(),
            "issue_close_date": (today + timedelta(days=30)).isoformat(),
            "min_application_size": 1,
            "lot_size": 1,
            "base_issue_size": "100"
        }
        
        response = api_client.post(f"{BASE_URL}/api/fixed-income/primary-market/issues", json=issue_data)
        assert response.status_code == 200
        issue_id = response.json()["issue_id"]
        print(f"1. Created issue {issue_id}")
        
        # 2. Open the issue
        response = api_client.patch(f"{BASE_URL}/api/fixed-income/primary-market/issues/{issue_id}/status?new_status=open")
        assert response.status_code == 200
        print("2. Opened issue")
        
        # 3. Get a client
        response = api_client.get(f"{BASE_URL}/api/clients?limit=1")
        if not response.json().get("clients"):
            pytest.skip("No clients available for bid")
        client = response.json()["clients"][0]
        
        # 4. Submit a bid
        bid_data = {
            "issue_id": issue_id,
            "client_id": client["id"],
            "category": "retail",
            "quantity": 10,
            "price": 1000,
            "payment_mode": "upi"
        }
        response = api_client.post(f"{BASE_URL}/api/fixed-income/primary-market/bids", json=bid_data)
        assert response.status_code == 200
        bid_id = response.json()["bid_id"]
        print(f"3. Submitted bid {bid_id}")
        
        # 5. Confirm payment for the bid
        response = api_client.patch(
            f"{BASE_URL}/api/fixed-income/primary-market/bids/{bid_id}/confirm-payment",
            params={"payment_reference": "TEST-PAY-001", "payment_amount": 10000}
        )
        assert response.status_code == 200
        print("4. Confirmed payment")
        
        # 6. Close the issue
        response = api_client.patch(f"{BASE_URL}/api/fixed-income/primary-market/issues/{issue_id}/status?new_status=closed")
        assert response.status_code == 200
        print("5. Closed issue")
        
        # 7. Process allotment
        response = api_client.post(f"{BASE_URL}/api/fixed-income/primary-market/issues/{issue_id}/process-allotment")
        assert response.status_code == 200
        
        data = response.json()
        assert data["message"] == "Allotment processed"
        assert "total_bids" in data
        assert "allotted_bids" in data
        assert "allotment_ratio" in data
        print(f"6. Allotment processed: {data['allotted_bids']}/{data['total_bids']} bids allotted (ratio: {data['allotment_ratio']})")


class TestEdgeCases(TestAuthSetup):
    """Test edge cases and validation"""
    
    def test_create_issue_invalid_dates(self, api_client):
        """Close date before open date should fail"""
        today = date.today()
        test_isin = f"INE{uuid.uuid4().hex[:6].upper()}99010"
        
        issue_data = {
            "isin": test_isin,
            "issuer_name": "TEST Invalid Dates",
            "issue_name": "TEST Invalid Dates NCD",
            "issue_type": "NCD",
            "face_value": "1000",
            "issue_price": "1000",
            "coupon_rate": "9",
            "coupon_frequency": "annual",
            "tenure_years": 3,
            "maturity_date": (today + timedelta(days=365*3)).isoformat(),
            "credit_rating": "AA",
            "rating_agency": "CRISIL",
            "issue_open_date": (today + timedelta(days=10)).isoformat(),
            "issue_close_date": (today + timedelta(days=5)).isoformat(),  # Before open!
            "min_application_size": 1,
            "lot_size": 1,
            "base_issue_size": "100"
        }
        
        response = api_client.post(f"{BASE_URL}/api/fixed-income/primary-market/issues", json=issue_data)
        assert response.status_code == 400, f"Should fail for invalid dates: {response.text}"
        assert "close date" in response.json().get("detail", "").lower()
        print("Invalid dates correctly rejected")
    
    def test_bid_quantity_validation(self, api_client):
        """Bid below minimum quantity should fail"""
        # Get an open issue with min_application_size > 1
        response = api_client.get(f"{BASE_URL}/api/fixed-income/primary-market/issues?status=open&limit=10")
        if response.status_code != 200:
            pytest.skip("Cannot get issues")
        
        issues = response.json().get("issues", [])
        issue = None
        for i in issues:
            if i.get("min_application_size", 1) > 1:
                issue = i
                break
        
        if not issue:
            # Create an issue with min_application_size > 1
            today = date.today()
            test_isin = f"INE{uuid.uuid4().hex[:6].upper()}98010"
            
            issue_data = {
                "isin": test_isin,
                "issuer_name": "TEST Min Qty Corp",
                "issue_name": f"TEST MIN QTY - {uuid.uuid4().hex[:4]}",
                "issue_type": "NCD",
                "face_value": "1000",
                "issue_price": "1000",
                "coupon_rate": "9",
                "coupon_frequency": "annual",
                "tenure_years": 3,
                "maturity_date": (today + timedelta(days=365*3)).isoformat(),
                "credit_rating": "AA",
                "rating_agency": "CRISIL",
                "issue_open_date": (today - timedelta(days=1)).isoformat(),
                "issue_close_date": (today + timedelta(days=30)).isoformat(),
                "min_application_size": 100,  # High minimum
                "lot_size": 10,
                "base_issue_size": "100"
            }
            
            response = api_client.post(f"{BASE_URL}/api/fixed-income/primary-market/issues", json=issue_data)
            if response.status_code != 200:
                pytest.skip("Cannot create test issue")
            
            issue_id = response.json()["issue_id"]
            api_client.patch(f"{BASE_URL}/api/fixed-income/primary-market/issues/{issue_id}/status?new_status=open")
            
            response = api_client.get(f"{BASE_URL}/api/fixed-income/primary-market/issues/{issue_id}")
            issue = response.json()
        
        # Get a client
        response = api_client.get(f"{BASE_URL}/api/clients?limit=1")
        if not response.json().get("clients"):
            pytest.skip("No clients available")
        client = response.json()["clients"][0]
        
        # Submit bid below minimum
        bid_data = {
            "issue_id": issue["id"],
            "client_id": client["id"],
            "category": "retail",
            "quantity": 1,  # Below minimum
            "price": float(issue.get("issue_price", 1000)),
            "payment_mode": "upi"
        }
        
        response = api_client.post(f"{BASE_URL}/api/fixed-income/primary-market/bids", json=bid_data)
        # Should fail with 400 for minimum quantity violation
        assert response.status_code == 400, f"Should fail for below-minimum quantity: {response.text}"
        print("Below-minimum quantity bid correctly rejected")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
