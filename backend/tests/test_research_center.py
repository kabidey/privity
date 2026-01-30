"""
Research Center Feature Tests
Tests for:
- Research reports upload, listing, deletion
- AI Research Assistant endpoint
- Research stats endpoint
- Role-based access control (PE Level vs Employee)
"""
import pytest
import requests
import os
import tempfile

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
PE_DESK_EMAIL = "pedesk@smifs.com"
PE_DESK_PASSWORD = "Kutta@123"
EMPLOYEE_EMAIL = "employee@test.com"
EMPLOYEE_PASSWORD = "Test@123"


class TestResearchCenterAuth:
    """Test authentication for Research Center"""
    
    @pytest.fixture(scope="class")
    def pe_desk_token(self):
        """Get PE Desk authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": PE_DESK_EMAIL,
            "password": PE_DESK_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip(f"PE Desk login failed: {response.status_code}")
    
    @pytest.fixture(scope="class")
    def employee_token(self):
        """Get Employee authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": EMPLOYEE_EMAIL,
            "password": EMPLOYEE_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip(f"Employee login failed: {response.status_code}")
    
    def test_pe_desk_login(self):
        """Test PE Desk can login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": PE_DESK_EMAIL,
            "password": PE_DESK_PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert "user" in data
        # PE Desk should have role 1 or 2
        assert data["user"]["role"] in [1, 2]
        print(f"PE Desk login successful - Role: {data['user']['role']}")


class TestResearchStats:
    """Test Research Stats endpoint"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers for PE Desk"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": PE_DESK_EMAIL,
            "password": PE_DESK_PASSWORD
        })
        if response.status_code == 200:
            token = response.json().get("token")
            return {"Authorization": f"Bearer {token}"}
        pytest.skip("Login failed")
    
    def test_get_research_stats(self, auth_headers):
        """Test GET /api/research/stats returns statistics"""
        response = requests.get(f"{BASE_URL}/api/research/stats", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "total_reports" in data
        assert "by_type" in data
        assert "top_stocks" in data
        assert "recent_uploads" in data
        
        # Verify data types
        assert isinstance(data["total_reports"], int)
        assert isinstance(data["by_type"], dict)
        assert isinstance(data["top_stocks"], list)
        assert isinstance(data["recent_uploads"], list)
        
        print(f"Research stats: {data['total_reports']} total reports")


class TestResearchReportsListing:
    """Test Research Reports listing endpoint"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": PE_DESK_EMAIL,
            "password": PE_DESK_PASSWORD
        })
        if response.status_code == 200:
            token = response.json().get("token")
            return {"Authorization": f"Bearer {token}"}
        pytest.skip("Login failed")
    
    def test_list_research_reports(self, auth_headers):
        """Test GET /api/research/reports returns list"""
        response = requests.get(f"{BASE_URL}/api/research/reports", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        # Should return a list
        assert isinstance(data, list)
        print(f"Found {len(data)} research reports")
        
        # If reports exist, verify structure
        if len(data) > 0:
            report = data[0]
            expected_fields = ["id", "stock_id", "title", "report_type", "file_url", "file_name"]
            for field in expected_fields:
                assert field in report, f"Missing field: {field}"
    
    def test_list_reports_with_stock_filter(self, auth_headers):
        """Test filtering reports by stock_id"""
        # First get stocks to find a valid stock_id
        stocks_response = requests.get(f"{BASE_URL}/api/stocks", headers=auth_headers)
        if stocks_response.status_code == 200 and len(stocks_response.json()) > 0:
            stock_id = stocks_response.json()[0]["id"]
            
            response = requests.get(
                f"{BASE_URL}/api/research/reports",
                params={"stock_id": stock_id},
                headers=auth_headers
            )
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
            print(f"Found {len(data)} reports for stock {stock_id}")
    
    def test_list_reports_with_type_filter(self, auth_headers):
        """Test filtering reports by report_type"""
        response = requests.get(
            f"{BASE_URL}/api/research/reports",
            params={"report_type": "general"},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
        # All returned reports should have type "general"
        for report in data:
            assert report.get("report_type") == "general"
        print(f"Found {len(data)} general reports")


class TestResearchReportUpload:
    """Test Research Report upload endpoint (PE Level only)"""
    
    @pytest.fixture(scope="class")
    def pe_headers(self):
        """Get PE Desk auth headers"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": PE_DESK_EMAIL,
            "password": PE_DESK_PASSWORD
        })
        if response.status_code == 200:
            token = response.json().get("token")
            return {"Authorization": f"Bearer {token}"}
        pytest.skip("PE Desk login failed")
    
    @pytest.fixture(scope="class")
    def employee_headers(self):
        """Get Employee auth headers"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": EMPLOYEE_EMAIL,
            "password": EMPLOYEE_PASSWORD
        })
        if response.status_code == 200:
            token = response.json().get("token")
            return {"Authorization": f"Bearer {token}"}
        pytest.skip("Employee login failed")
    
    @pytest.fixture(scope="class")
    def test_stock_id(self, pe_headers):
        """Get a valid stock ID for testing"""
        response = requests.get(f"{BASE_URL}/api/stocks", headers=pe_headers)
        if response.status_code == 200 and len(response.json()) > 0:
            return response.json()[0]["id"]
        pytest.skip("No stocks available for testing")
    
    def test_upload_report_pe_desk(self, pe_headers, test_stock_id):
        """Test PE Desk can upload research report"""
        # Create a test file
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            f.write(b"TEST_RESEARCH_REPORT: This is a test research report content for testing purposes.")
            temp_file_path = f.name
        
        try:
            with open(temp_file_path, 'rb') as f:
                files = {'file': ('TEST_research_report.txt', f, 'text/plain')}
                data = {
                    'stock_id': test_stock_id,
                    'title': 'TEST_Q4 2024 Analysis Report',
                    'description': 'Test report for automated testing',
                    'report_type': 'analysis'
                }
                
                response = requests.post(
                    f"{BASE_URL}/api/research/reports",
                    headers=pe_headers,
                    files=files,
                    data=data
                )
            
            assert response.status_code == 200
            result = response.json()
            assert "message" in result
            assert "report" in result
            assert result["report"]["title"] == "TEST_Q4 2024 Analysis Report"
            assert result["report"]["report_type"] == "analysis"
            print(f"Report uploaded successfully: {result['report']['id']}")
            
            # Store report ID for cleanup
            return result["report"]["id"]
        finally:
            os.unlink(temp_file_path)
    
    def test_upload_report_employee_forbidden(self, employee_headers, test_stock_id):
        """Test Employee cannot upload research report (403)"""
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            f.write(b"TEST: Employee upload attempt")
            temp_file_path = f.name
        
        try:
            with open(temp_file_path, 'rb') as f:
                files = {'file': ('test.txt', f, 'text/plain')}
                data = {
                    'stock_id': test_stock_id,
                    'title': 'TEST_Employee Upload Attempt',
                    'report_type': 'general'
                }
                
                response = requests.post(
                    f"{BASE_URL}/api/research/reports",
                    headers=employee_headers,
                    files=files,
                    data=data
                )
            
            # Should be forbidden for employee
            assert response.status_code == 403
            print("Employee correctly denied upload access (403)")
        finally:
            os.unlink(temp_file_path)
    
    def test_upload_invalid_file_type(self, pe_headers, test_stock_id):
        """Test upload rejects invalid file types"""
        with tempfile.NamedTemporaryFile(suffix=".exe", delete=False) as f:
            f.write(b"TEST: Invalid file type")
            temp_file_path = f.name
        
        try:
            with open(temp_file_path, 'rb') as f:
                files = {'file': ('test.exe', f, 'application/octet-stream')}
                data = {
                    'stock_id': test_stock_id,
                    'title': 'TEST_Invalid File Type',
                    'report_type': 'general'
                }
                
                response = requests.post(
                    f"{BASE_URL}/api/research/reports",
                    headers=pe_headers,
                    files=files,
                    data=data
                )
            
            # Should reject invalid file type
            assert response.status_code == 400
            assert "not allowed" in response.json().get("detail", "").lower()
            print("Invalid file type correctly rejected (400)")
        finally:
            os.unlink(temp_file_path)
    
    def test_upload_missing_required_fields(self, pe_headers):
        """Test upload requires stock_id and title"""
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            f.write(b"TEST: Missing fields")
            temp_file_path = f.name
        
        try:
            with open(temp_file_path, 'rb') as f:
                files = {'file': ('test.txt', f, 'text/plain')}
                # Missing stock_id and title
                data = {'report_type': 'general'}
                
                response = requests.post(
                    f"{BASE_URL}/api/research/reports",
                    headers=pe_headers,
                    files=files,
                    data=data
                )
            
            # Should fail validation
            assert response.status_code == 422
            print("Missing required fields correctly rejected (422)")
        finally:
            os.unlink(temp_file_path)


class TestResearchReportDelete:
    """Test Research Report deletion (PE Level only)"""
    
    @pytest.fixture(scope="class")
    def pe_headers(self):
        """Get PE Desk auth headers"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": PE_DESK_EMAIL,
            "password": PE_DESK_PASSWORD
        })
        if response.status_code == 200:
            token = response.json().get("token")
            return {"Authorization": f"Bearer {token}"}
        pytest.skip("PE Desk login failed")
    
    @pytest.fixture(scope="class")
    def employee_headers(self):
        """Get Employee auth headers"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": EMPLOYEE_EMAIL,
            "password": EMPLOYEE_PASSWORD
        })
        if response.status_code == 200:
            token = response.json().get("token")
            return {"Authorization": f"Bearer {token}"}
        pytest.skip("Employee login failed")
    
    def test_delete_nonexistent_report(self, pe_headers):
        """Test deleting non-existent report returns 404"""
        response = requests.delete(
            f"{BASE_URL}/api/research/reports/nonexistent-id-12345",
            headers=pe_headers
        )
        assert response.status_code == 404
        print("Non-existent report deletion correctly returns 404")
    
    def test_employee_cannot_delete(self, employee_headers):
        """Test Employee cannot delete reports (403)"""
        # First get a report ID if any exist
        pe_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": PE_DESK_EMAIL,
            "password": PE_DESK_PASSWORD
        })
        pe_token = pe_response.json().get("token")
        pe_headers_temp = {"Authorization": f"Bearer {pe_token}"}
        
        reports_response = requests.get(f"{BASE_URL}/api/research/reports", headers=pe_headers_temp)
        if reports_response.status_code == 200 and len(reports_response.json()) > 0:
            report_id = reports_response.json()[0]["id"]
            
            response = requests.delete(
                f"{BASE_URL}/api/research/reports/{report_id}",
                headers=employee_headers
            )
            assert response.status_code == 403
            print("Employee correctly denied delete access (403)")
        else:
            print("No reports to test delete - skipping")


class TestAIResearchAssistant:
    """Test AI Research Assistant endpoint"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": PE_DESK_EMAIL,
            "password": PE_DESK_PASSWORD
        })
        if response.status_code == 200:
            token = response.json().get("token")
            return {"Authorization": f"Bearer {token}"}
        pytest.skip("Login failed")
    
    @pytest.fixture(scope="class")
    def test_stock_id(self, auth_headers):
        """Get a valid stock ID for testing"""
        response = requests.get(f"{BASE_URL}/api/stocks", headers=auth_headers)
        if response.status_code == 200 and len(response.json()) > 0:
            return response.json()[0]["id"]
        return None
    
    def test_ai_research_general_query(self, auth_headers):
        """Test AI research with general query (no stock)"""
        data = {'query': 'What are key factors for analyzing unlisted stocks?'}
        
        response = requests.post(
            f"{BASE_URL}/api/research/ai-research",
            headers=auth_headers,
            data=data
        )
        
        assert response.status_code == 200
        result = response.json()
        
        # Verify response structure
        assert "response" in result
        assert "disclaimer" in result
        assert len(result["response"]) > 0
        
        print(f"AI response received: {result['response'][:100]}...")
        print(f"Disclaimer: {result['disclaimer'][:50]}...")
    
    def test_ai_research_with_stock(self, auth_headers, test_stock_id):
        """Test AI research with specific stock context"""
        if not test_stock_id:
            pytest.skip("No stock available for testing")
        
        data = {
            'query': 'What is the investment potential of this stock?',
            'stock_id': test_stock_id
        }
        
        response = requests.post(
            f"{BASE_URL}/api/research/ai-research",
            headers=auth_headers,
            data=data
        )
        
        assert response.status_code == 200
        result = response.json()
        
        assert "response" in result
        assert "stock_id" in result
        assert result["stock_id"] == test_stock_id
        
        print(f"AI response for stock {test_stock_id}: {result['response'][:100]}...")
    
    def test_ai_research_empty_query(self, auth_headers):
        """Test AI research rejects empty query"""
        data = {'query': ''}
        
        response = requests.post(
            f"{BASE_URL}/api/research/ai-research",
            headers=auth_headers,
            data=data
        )
        
        # Should fail validation
        assert response.status_code in [400, 422]
        print("Empty query correctly rejected")


class TestResearchReportsByStock:
    """Test getting reports by stock endpoint"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": PE_DESK_EMAIL,
            "password": PE_DESK_PASSWORD
        })
        if response.status_code == 200:
            token = response.json().get("token")
            return {"Authorization": f"Bearer {token}"}
        pytest.skip("Login failed")
    
    @pytest.fixture(scope="class")
    def test_stock_id(self, auth_headers):
        """Get a valid stock ID for testing"""
        response = requests.get(f"{BASE_URL}/api/stocks", headers=auth_headers)
        if response.status_code == 200 and len(response.json()) > 0:
            return response.json()[0]["id"]
        pytest.skip("No stocks available")
    
    def test_get_reports_by_stock(self, auth_headers, test_stock_id):
        """Test GET /api/research/reports/stock/{stock_id}"""
        response = requests.get(
            f"{BASE_URL}/api/research/reports/stock/{test_stock_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "stock" in data
        assert "reports" in data
        assert "total_reports" in data
        
        assert isinstance(data["reports"], list)
        assert isinstance(data["total_reports"], int)
        
        print(f"Found {data['total_reports']} reports for stock")
    
    def test_get_reports_invalid_stock(self, auth_headers):
        """Test getting reports for non-existent stock returns 404"""
        response = requests.get(
            f"{BASE_URL}/api/research/reports/stock/invalid-stock-id-12345",
            headers=auth_headers
        )
        
        assert response.status_code == 404
        print("Invalid stock ID correctly returns 404")


class TestCleanupTestData:
    """Cleanup test data created during tests"""
    
    @pytest.fixture(scope="class")
    def pe_headers(self):
        """Get PE Desk auth headers"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": PE_DESK_EMAIL,
            "password": PE_DESK_PASSWORD
        })
        if response.status_code == 200:
            token = response.json().get("token")
            return {"Authorization": f"Bearer {token}"}
        pytest.skip("PE Desk login failed")
    
    def test_cleanup_test_reports(self, pe_headers):
        """Delete all TEST_ prefixed reports"""
        response = requests.get(f"{BASE_URL}/api/research/reports", headers=pe_headers)
        if response.status_code == 200:
            reports = response.json()
            deleted_count = 0
            for report in reports:
                if report.get("title", "").startswith("TEST_"):
                    delete_response = requests.delete(
                        f"{BASE_URL}/api/research/reports/{report['id']}",
                        headers=pe_headers
                    )
                    if delete_response.status_code == 200:
                        deleted_count += 1
            print(f"Cleaned up {deleted_count} test reports")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
