"""
Test Client Management Features:
1. Client modification/deletion restricted to PE Desk only
2. DP Type field (SMIFS or Outside)
3. Trading UCC field (mandatory when DP is with SMIFS)
4. Backend validation for dp_type and trading_ucc
"""

import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
PE_DESK_ADMIN = {
    "email": "admin@privity.com",
    "password": "Admin@123"
}

EMPLOYEE = {
    "email": "test_emp_dp_8a1404fd@smifs.com",
    "password": "Test@123"
}


class TestAuthentication:
    """Test login for both PE Desk and Employee"""
    
    def test_pe_desk_login(self):
        """Test PE Desk admin login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=PE_DESK_ADMIN)
        assert response.status_code == 200, f"PE Desk login failed: {response.text}"
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == 1, "PE Desk should have role 1"
        print(f"✓ PE Desk login successful - role: {data['user']['role']}")
    
    def test_employee_login(self):
        """Test Employee login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=EMPLOYEE)
        assert response.status_code == 200, f"Employee login failed: {response.text}"
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == 4, "Employee should have role 4"
        print(f"✓ Employee login successful - role: {data['user']['role']}")


class TestDPTypeAndTradingUCC:
    """Test DP Type and Trading UCC validation"""
    
    @pytest.fixture
    def pe_desk_token(self):
        """Get PE Desk auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=PE_DESK_ADMIN)
        return response.json()["token"]
    
    @pytest.fixture
    def employee_token(self):
        """Get Employee auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=EMPLOYEE)
        return response.json()["token"]
    
    def test_create_client_dp_outside_without_trading_ucc(self, pe_desk_token):
        """Create client with DP Type = 'Outside' - should succeed without Trading UCC"""
        headers = {"Authorization": f"Bearer {pe_desk_token}"}
        unique_id = str(uuid.uuid4())[:8]
        client_data = {
            "name": f"TEST_Client_Outside_{unique_id}",
            "pan_number": f"ABCDE{unique_id[:4].upper()}F",
            "dp_id": f"DP{unique_id}",
            "dp_type": "outside",
            "trading_ucc": ""  # Empty trading UCC
        }
        
        response = requests.post(f"{BASE_URL}/api/clients", json=client_data, headers=headers)
        assert response.status_code == 200, f"Failed to create client with DP Outside: {response.text}"
        data = response.json()
        assert data["dp_type"] == "outside"
        print(f"✓ Created client with DP Type 'Outside' without Trading UCC - ID: {data['id']}")
        return data["id"]
    
    def test_create_client_dp_smifs_without_trading_ucc_fails(self, pe_desk_token):
        """Try to create client with DP Type = 'SMIFS' without Trading UCC - should fail"""
        headers = {"Authorization": f"Bearer {pe_desk_token}"}
        unique_id = str(uuid.uuid4())[:8]
        client_data = {
            "name": f"TEST_Client_SMIFS_NoUCC_{unique_id}",
            "pan_number": f"FGHIJ{unique_id[:4].upper()}K",
            "dp_id": f"DP{unique_id}",
            "dp_type": "smifs",
            "trading_ucc": ""  # Empty trading UCC - should fail
        }
        
        response = requests.post(f"{BASE_URL}/api/clients", json=client_data, headers=headers)
        assert response.status_code == 400, f"Expected 400 error but got {response.status_code}: {response.text}"
        data = response.json()
        assert "Trading UCC is required" in data.get("detail", ""), f"Expected Trading UCC error: {data}"
        print("✓ Correctly rejected client with DP Type 'SMIFS' without Trading UCC")
    
    def test_create_client_dp_smifs_with_trading_ucc(self, pe_desk_token):
        """Create client with DP Type = 'SMIFS' and Trading UCC - should succeed"""
        headers = {"Authorization": f"Bearer {pe_desk_token}"}
        unique_id = str(uuid.uuid4())[:8]
        client_data = {
            "name": f"TEST_Client_SMIFS_{unique_id}",
            "pan_number": f"LMNOP{unique_id[:4].upper()}Q",
            "dp_id": f"DP{unique_id}",
            "dp_type": "smifs",
            "trading_ucc": f"UCC{unique_id.upper()}"
        }
        
        response = requests.post(f"{BASE_URL}/api/clients", json=client_data, headers=headers)
        assert response.status_code == 200, f"Failed to create client with DP SMIFS: {response.text}"
        data = response.json()
        assert data["dp_type"] == "smifs"
        assert data["trading_ucc"] == f"UCC{unique_id.upper()}"
        print(f"✓ Created client with DP Type 'SMIFS' and Trading UCC - ID: {data['id']}")
        return data["id"]


class TestClientModificationRestrictions:
    """Test that only PE Desk can modify/delete clients"""
    
    @pytest.fixture
    def pe_desk_token(self):
        """Get PE Desk auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=PE_DESK_ADMIN)
        return response.json()["token"]
    
    @pytest.fixture
    def employee_token(self):
        """Get Employee auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=EMPLOYEE)
        return response.json()["token"]
    
    @pytest.fixture
    def test_client(self, pe_desk_token):
        """Create a test client for modification tests"""
        headers = {"Authorization": f"Bearer {pe_desk_token}"}
        unique_id = str(uuid.uuid4())[:8]
        client_data = {
            "name": f"TEST_ModifyTest_{unique_id}",
            "pan_number": f"RSTUV{unique_id[:4].upper()}W",
            "dp_id": f"DP{unique_id}",
            "dp_type": "outside"
        }
        response = requests.post(f"{BASE_URL}/api/clients", json=client_data, headers=headers)
        return response.json()
    
    def test_employee_cannot_update_client(self, employee_token, test_client):
        """Employee should NOT be able to update client via API (403 error)"""
        headers = {"Authorization": f"Bearer {employee_token}"}
        update_data = {
            "name": "Updated Name By Employee",
            "pan_number": test_client["pan_number"],
            "dp_id": test_client["dp_id"],
            "dp_type": "outside"
        }
        
        response = requests.put(f"{BASE_URL}/api/clients/{test_client['id']}", json=update_data, headers=headers)
        assert response.status_code == 403, f"Expected 403 but got {response.status_code}: {response.text}"
        print("✓ Employee correctly blocked from updating client (403)")
    
    def test_employee_cannot_delete_client(self, employee_token, test_client):
        """Employee should NOT be able to delete client via API (403 error)"""
        headers = {"Authorization": f"Bearer {employee_token}"}
        
        response = requests.delete(f"{BASE_URL}/api/clients/{test_client['id']}", headers=headers)
        assert response.status_code == 403, f"Expected 403 but got {response.status_code}: {response.text}"
        print("✓ Employee correctly blocked from deleting client (403)")
    
    def test_pe_desk_can_update_client(self, pe_desk_token, test_client):
        """PE Desk should be able to update client"""
        headers = {"Authorization": f"Bearer {pe_desk_token}"}
        update_data = {
            "name": f"Updated_{test_client['name']}",
            "pan_number": test_client["pan_number"],
            "dp_id": test_client["dp_id"],
            "dp_type": "outside"
        }
        
        response = requests.put(f"{BASE_URL}/api/clients/{test_client['id']}", json=update_data, headers=headers)
        assert response.status_code == 200, f"PE Desk update failed: {response.text}"
        data = response.json()
        assert data["name"] == f"Updated_{test_client['name']}"
        print("✓ PE Desk successfully updated client")
    
    def test_pe_desk_can_delete_client(self, pe_desk_token):
        """PE Desk should be able to delete client"""
        headers = {"Authorization": f"Bearer {pe_desk_token}"}
        
        # First create a client to delete
        unique_id = str(uuid.uuid4())[:8]
        client_data = {
            "name": f"TEST_ToDelete_{unique_id}",
            "pan_number": f"XYZAB{unique_id[:4].upper()}C",
            "dp_id": f"DP{unique_id}",
            "dp_type": "outside"
        }
        create_response = requests.post(f"{BASE_URL}/api/clients", json=client_data, headers=headers)
        client_id = create_response.json()["id"]
        
        # Now delete it
        response = requests.delete(f"{BASE_URL}/api/clients/{client_id}", headers=headers)
        assert response.status_code == 200, f"PE Desk delete failed: {response.text}"
        print("✓ PE Desk successfully deleted client")
        
        # Verify deletion
        get_response = requests.get(f"{BASE_URL}/api/clients/{client_id}", headers=headers)
        assert get_response.status_code == 404, "Client should not exist after deletion"
        print("✓ Verified client no longer exists")


class TestClientSearch:
    """Test client search functionality (backend search)"""
    
    @pytest.fixture
    def pe_desk_token(self):
        """Get PE Desk auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=PE_DESK_ADMIN)
        return response.json()["token"]
    
    def test_search_by_name(self, pe_desk_token):
        """Test search by client name"""
        headers = {"Authorization": f"Bearer {pe_desk_token}"}
        
        # First create a client with unique name
        unique_id = str(uuid.uuid4())[:8]
        client_data = {
            "name": f"TEST_SearchName_{unique_id}",
            "pan_number": f"DEFGH{unique_id[:4].upper()}I",
            "dp_id": f"DP{unique_id}",
            "dp_type": "outside"
        }
        requests.post(f"{BASE_URL}/api/clients", json=client_data, headers=headers)
        
        # Search by name
        response = requests.get(f"{BASE_URL}/api/clients?search=SearchName_{unique_id}", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1, "Should find at least one client"
        assert any(f"SearchName_{unique_id}" in c["name"] for c in data)
        print(f"✓ Search by name works - found {len(data)} client(s)")
    
    def test_search_by_pan(self, pe_desk_token):
        """Test search by PAN number"""
        headers = {"Authorization": f"Bearer {pe_desk_token}"}
        
        # First create a client with unique PAN
        unique_id = str(uuid.uuid4())[:8]
        pan_number = f"JKLMN{unique_id[:4].upper()}O"
        client_data = {
            "name": f"TEST_SearchPAN_{unique_id}",
            "pan_number": pan_number,
            "dp_id": f"DP{unique_id}",
            "dp_type": "outside"
        }
        requests.post(f"{BASE_URL}/api/clients", json=client_data, headers=headers)
        
        # Search by PAN
        response = requests.get(f"{BASE_URL}/api/clients?search={pan_number}", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1, "Should find at least one client"
        assert any(c["pan_number"] == pan_number for c in data)
        print(f"✓ Search by PAN works - found {len(data)} client(s)")


class TestDPTypeDisplay:
    """Test that DP Type is correctly stored and returned"""
    
    @pytest.fixture
    def pe_desk_token(self):
        """Get PE Desk auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=PE_DESK_ADMIN)
        return response.json()["token"]
    
    def test_dp_type_smifs_displayed(self, pe_desk_token):
        """Verify DP Type 'SMIFS' is correctly stored and returned"""
        headers = {"Authorization": f"Bearer {pe_desk_token}"}
        unique_id = str(uuid.uuid4())[:8]
        client_data = {
            "name": f"TEST_DPDisplay_SMIFS_{unique_id}",
            "pan_number": f"PQRST{unique_id[:4].upper()}U",
            "dp_id": f"DP{unique_id}",
            "dp_type": "smifs",
            "trading_ucc": f"UCC{unique_id.upper()}"
        }
        
        create_response = requests.post(f"{BASE_URL}/api/clients", json=client_data, headers=headers)
        assert create_response.status_code == 200
        client_id = create_response.json()["id"]
        
        # Get client and verify dp_type
        get_response = requests.get(f"{BASE_URL}/api/clients/{client_id}", headers=headers)
        assert get_response.status_code == 200
        data = get_response.json()
        assert data["dp_type"] == "smifs", f"Expected dp_type 'smifs' but got '{data.get('dp_type')}'"
        assert data["trading_ucc"] == f"UCC{unique_id.upper()}"
        print("✓ DP Type 'SMIFS' correctly stored and returned with Trading UCC")
    
    def test_dp_type_outside_displayed(self, pe_desk_token):
        """Verify DP Type 'Outside' is correctly stored and returned"""
        headers = {"Authorization": f"Bearer {pe_desk_token}"}
        unique_id = str(uuid.uuid4())[:8]
        client_data = {
            "name": f"TEST_DPDisplay_Outside_{unique_id}",
            "pan_number": f"VWXYZ{unique_id[:4].upper()}A",
            "dp_id": f"DP{unique_id}",
            "dp_type": "outside"
        }
        
        create_response = requests.post(f"{BASE_URL}/api/clients", json=client_data, headers=headers)
        assert create_response.status_code == 200
        client_id = create_response.json()["id"]
        
        # Get client and verify dp_type
        get_response = requests.get(f"{BASE_URL}/api/clients/{client_id}", headers=headers)
        assert get_response.status_code == 200
        data = get_response.json()
        assert data["dp_type"] == "outside", f"Expected dp_type 'outside' but got '{data.get('dp_type')}'"
        print("✓ DP Type 'Outside' correctly stored and returned")


class TestCleanup:
    """Cleanup test data"""
    
    @pytest.fixture
    def pe_desk_token(self):
        """Get PE Desk auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=PE_DESK_ADMIN)
        return response.json()["token"]
    
    def test_cleanup_test_clients(self, pe_desk_token):
        """Clean up TEST_ prefixed clients"""
        headers = {"Authorization": f"Bearer {pe_desk_token}"}
        
        # Get all clients
        response = requests.get(f"{BASE_URL}/api/clients", headers=headers)
        if response.status_code == 200:
            clients = response.json()
            deleted_count = 0
            for client in clients:
                if client.get("name", "").startswith("TEST_"):
                    del_response = requests.delete(f"{BASE_URL}/api/clients/{client['id']}", headers=headers)
                    if del_response.status_code == 200:
                        deleted_count += 1
            print(f"✓ Cleaned up {deleted_count} test clients")
