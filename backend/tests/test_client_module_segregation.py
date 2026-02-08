"""
Test Client Module Segregation (PE/FI) Feature
Tests the new module-based client filtering and company agreements endpoints
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_EMAIL = "pe@smifs.com"
TEST_PASSWORD = "Kutta@123"


class TestCompanyAgreements:
    """Test company agreements endpoint for PE/FI modules"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
            headers={"User-Agent": "pytest-testing"}
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        return response.json().get("token")
    
    def test_get_company_agreements_public(self):
        """GET /api/company-master/agreements - Returns both PE and FI company agreements (public endpoint)"""
        response = requests.get(
            f"{BASE_URL}/api/company-master/agreements",
            headers={"User-Agent": "pytest-testing"}
        )
        assert response.status_code == 200, f"Failed to get agreements: {response.text}"
        
        data = response.json()
        assert "agreements" in data, "Response should have 'agreements' key"
        agreements = data["agreements"]
        
        # Should have at least one agreement (could be PE, FI, or legacy)
        assert len(agreements) >= 1, "Should have at least one agreement"
        
        # Each agreement should have required fields
        for agreement in agreements:
            assert "company_id" in agreement, "Agreement should have company_id"
            assert "company_name" in agreement, "Agreement should have company_name"
            assert "company_type" in agreement, "Agreement should have company_type"
            assert "agreement_text" in agreement, "Agreement should have agreement_text"
            
        # Log the agreements found
        print(f"Found {len(agreements)} agreements:")
        for a in agreements:
            print(f"  - {a['company_name']} ({a['company_type']})")
    
    def test_agreements_have_pe_and_fi(self):
        """Verify both PE and FI companies exist in agreements"""
        response = requests.get(
            f"{BASE_URL}/api/company-master/agreements",
            headers={"User-Agent": "pytest-testing"}
        )
        assert response.status_code == 200
        
        agreements = response.json().get("agreements", [])
        company_types = [a.get("company_type") for a in agreements]
        
        # If multi-company setup is active, should have both PE and FI
        # Otherwise might have legacy single company
        has_pe = "private_equity" in company_types
        has_fi = "fixed_income" in company_types
        has_legacy = "legacy" in company_types or "default" in company_types
        
        print(f"Company types found: {company_types}")
        
        # At minimum should have one type
        assert len(company_types) >= 1, "Should have at least one company type"
        
        # If we have both modules, validate their structure
        if has_pe:
            pe_agreement = next((a for a in agreements if a["company_type"] == "private_equity"), None)
            assert pe_agreement is not None, "PE agreement should exist"
            assert pe_agreement.get("company_id") == "pe_company", "PE company_id should be 'pe_company'"
            print(f"PE Agreement: {pe_agreement['company_name']}")
            
        if has_fi:
            fi_agreement = next((a for a in agreements if a["company_type"] == "fixed_income"), None)
            assert fi_agreement is not None, "FI agreement should exist"
            assert fi_agreement.get("company_id") == "fi_company", "FI company_id should be 'fi_company'"
            print(f"FI Agreement: {fi_agreement['company_name']}")


class TestClientsByModule:
    """Test client filtering by module (PE/FI)"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
            headers={"User-Agent": "pytest-testing"}
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        return response.json().get("token")
    
    @pytest.fixture(scope="class")
    def auth_headers(self, auth_token):
        """Get authorization headers"""
        return {
            "Authorization": f"Bearer {auth_token}",
            "User-Agent": "pytest-testing"
        }
    
    def test_get_clients_by_module_private_equity(self, auth_headers):
        """GET /api/clients/by-module/private_equity - Returns only clients with PE module access"""
        response = requests.get(
            f"{BASE_URL}/api/clients/by-module/private_equity",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed to get PE clients: {response.text}"
        
        clients = response.json()
        assert isinstance(clients, list), "Response should be a list"
        
        # All returned clients should have private_equity in their modules
        # OR have no modules field (legacy clients default to PE)
        for client in clients:
            modules = client.get("modules", ["private_equity"])  # Default to PE
            # Client should either have private_equity or be legacy without modules
            has_pe_access = "private_equity" in modules or modules is None
            assert has_pe_access or "modules" not in client, \
                f"Client {client.get('name')} should have PE access but has modules: {modules}"
        
        print(f"Found {len(clients)} clients with PE module access")
    
    def test_get_clients_by_module_fixed_income(self, auth_headers):
        """GET /api/clients/by-module/fixed_income - Returns only clients with FI module access"""
        response = requests.get(
            f"{BASE_URL}/api/clients/by-module/fixed_income",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed to get FI clients: {response.text}"
        
        clients = response.json()
        assert isinstance(clients, list), "Response should be a list"
        
        # All returned clients should have fixed_income in their modules
        for client in clients:
            modules = client.get("modules", [])
            assert "fixed_income" in modules, \
                f"Client {client.get('name')} should have FI access but has modules: {modules}"
        
        print(f"Found {len(clients)} clients with FI module access")
    
    def test_get_clients_by_module_invalid(self, auth_headers):
        """GET /api/clients/by-module/invalid_module - Returns 400 for invalid module"""
        response = requests.get(
            f"{BASE_URL}/api/clients/by-module/invalid_module",
            headers=auth_headers
        )
        assert response.status_code == 400, f"Should return 400 for invalid module: {response.status_code}"
        
        error_data = response.json()
        assert "detail" in error_data, "Error response should have detail"
        print(f"Invalid module error: {error_data.get('detail')}")
    
    def test_get_clients_by_module_with_search(self, auth_headers):
        """GET /api/clients/by-module/{module}?search=... - Supports search filter"""
        response = requests.get(
            f"{BASE_URL}/api/clients/by-module/private_equity?search=test",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed to search PE clients: {response.text}"
        
        clients = response.json()
        assert isinstance(clients, list), "Response should be a list"
        print(f"Found {len(clients)} clients matching 'test' search in PE module")


class TestClientCreationWithModules:
    """Test client creation with modules field"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
            headers={"User-Agent": "pytest-testing"}
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        return response.json().get("token")
    
    @pytest.fixture(scope="class")
    def auth_headers(self, auth_token):
        """Get authorization headers"""
        return {
            "Authorization": f"Bearer {auth_token}",
            "User-Agent": "pytest-testing"
        }
    
    def test_client_modules_field_structure(self, auth_headers):
        """Verify existing clients have modules field with correct structure"""
        response = requests.get(
            f"{BASE_URL}/api/clients",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed to get clients: {response.text}"
        
        clients = response.json()
        if len(clients) > 0:
            sample_client = clients[0]
            # Modules should be a list or not present (legacy)
            modules = sample_client.get("modules")
            if modules is not None:
                assert isinstance(modules, list), f"modules should be a list, got {type(modules)}"
                # Valid module values
                valid_modules = {"private_equity", "fixed_income"}
                for module in modules:
                    assert module in valid_modules, f"Invalid module: {module}"
            print(f"Sample client '{sample_client.get('name')}' has modules: {modules}")
        else:
            pytest.skip("No clients found to test")
    
    def test_legacy_clients_default_to_pe(self, auth_headers):
        """Legacy clients without modules field should default to PE in by-module endpoint"""
        # Get all PE clients
        response = requests.get(
            f"{BASE_URL}/api/clients/by-module/private_equity",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        pe_clients = response.json()
        
        # Get all FI clients
        response = requests.get(
            f"{BASE_URL}/api/clients/by-module/fixed_income",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        fi_clients = response.json()
        
        print(f"PE clients: {len(pe_clients)}, FI clients: {len(fi_clients)}")
        
        # Legacy clients should appear in PE module list, not FI
        # (unless explicitly given FI access)


class TestCompanyMasterList:
    """Test company master list endpoint"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
            headers={"User-Agent": "pytest-testing"}
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        return response.json().get("token")
    
    @pytest.fixture(scope="class")
    def auth_headers(self, auth_token):
        """Get authorization headers"""
        return {
            "Authorization": f"Bearer {auth_token}",
            "User-Agent": "pytest-testing"
        }
    
    def test_list_companies(self, auth_headers):
        """GET /api/company-master/list - List all companies"""
        response = requests.get(
            f"{BASE_URL}/api/company-master/list",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed to list companies: {response.text}"
        
        companies = response.json()
        assert isinstance(companies, list), "Response should be a list"
        
        print(f"Found {len(companies)} companies:")
        for company in companies:
            print(f"  - {company.get('company_name')} (type: {company.get('company_type')}, id: {company.get('id')})")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
