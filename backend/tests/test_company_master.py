"""
Company Master API Tests
Tests for Company Master settings - PE Desk only access
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
PE_DESK_CREDS = {"email": "pedesk@smifs.com", "password": "Kutta@123"}
PE_MANAGER_CREDS = {"email": "pemanager@test.com", "password": "Test@123"}


@pytest.fixture(scope="module")
def pe_desk_token():
    """Get PE Desk (role 1) authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json=PE_DESK_CREDS)
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip("PE Desk authentication failed")


@pytest.fixture(scope="module")
def pe_manager_token():
    """Get PE Manager (role 2) authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json=PE_MANAGER_CREDS)
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip("PE Manager authentication failed")


@pytest.fixture
def pe_desk_client(pe_desk_token):
    """Session with PE Desk auth header"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {pe_desk_token}"
    })
    return session


@pytest.fixture
def pe_manager_client(pe_manager_token):
    """Session with PE Manager auth header"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {pe_manager_token}"
    })
    return session


class TestCompanyMasterAccess:
    """Test access control for Company Master endpoints"""
    
    def test_01_pe_desk_can_get_company_master(self, pe_desk_client):
        """PE Desk (role 1) should be able to GET company master"""
        response = pe_desk_client.get(f"{BASE_URL}/api/company-master")
        assert response.status_code == 200
        
        data = response.json()
        assert "id" in data
        assert "company_name" in data
        assert "company_address" in data
        assert "company_cin" in data
        assert "company_gst" in data
        assert "company_pan" in data
        assert "cdsl_dp_id" in data
        assert "nsdl_dp_id" in data
        assert "company_tan" in data
        assert "company_bank_name" in data
        assert "company_bank_account" in data
        assert "company_bank_ifsc" in data
        assert "company_bank_branch" in data
        # Document URLs
        assert "cml_cdsl_url" in data
        assert "cml_nsdl_url" in data
        assert "cancelled_cheque_url" in data
        assert "pan_card_url" in data
        # Metadata
        assert "updated_at" in data
        assert "updated_by" in data
    
    def test_02_pe_manager_denied_get_company_master(self, pe_manager_client):
        """PE Manager (role 2) should get 403 when accessing company master"""
        response = pe_manager_client.get(f"{BASE_URL}/api/company-master")
        assert response.status_code == 403
        
        data = response.json()
        assert "detail" in data
        assert "PE Desk" in data["detail"]
    
    def test_03_pe_desk_can_update_company_master(self, pe_desk_client):
        """PE Desk (role 1) should be able to PUT company master"""
        update_data = {
            "company_name": "SMIFS Capital Markets Ltd",
            "company_address": "12, India Exchange Place, Kolkata - 700001",
            "company_cin": "U67120WB1994PLC064483",
            "company_gst": "19AABCS1234F1ZP",
            "company_pan": "AABCS1234F",
            "cdsl_dp_id": "12058400",
            "nsdl_dp_id": "IN301774",
            "company_tan": "CALS12345F",
            "company_bank_name": "HDFC Bank",
            "company_bank_account": "50100123456789",
            "company_bank_ifsc": "HDFC0000001",
            "company_bank_branch": "Fort Branch, Mumbai"
        }
        
        response = pe_desk_client.put(f"{BASE_URL}/api/company-master", json=update_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["company_name"] == update_data["company_name"]
        assert data["company_cin"] == update_data["company_cin"]
        assert data["company_gst"] == update_data["company_gst"]
        assert data["company_pan"] == update_data["company_pan"].upper()
        assert data["cdsl_dp_id"] == update_data["cdsl_dp_id"]
        assert data["nsdl_dp_id"] == update_data["nsdl_dp_id"]
        assert data["company_tan"] == update_data["company_tan"].upper()
        assert data["company_bank_name"] == update_data["company_bank_name"]
        assert data["company_bank_account"] == update_data["company_bank_account"]
        assert data["company_bank_ifsc"] == update_data["company_bank_ifsc"].upper()
        assert data["company_bank_branch"] == update_data["company_bank_branch"]
    
    def test_04_pe_manager_denied_update_company_master(self, pe_manager_client):
        """PE Manager (role 2) should get 403 when updating company master"""
        update_data = {"company_name": "Test Company"}
        
        response = pe_manager_client.put(f"{BASE_URL}/api/company-master", json=update_data)
        assert response.status_code == 403
        
        data = response.json()
        assert "detail" in data
        assert "PE Desk" in data["detail"]
    
    def test_05_unauthenticated_access_denied(self):
        """Unauthenticated requests should be denied"""
        response = requests.get(f"{BASE_URL}/api/company-master")
        assert response.status_code in [401, 403]


class TestCompanyMasterDocumentUpload:
    """Test document upload functionality"""
    
    def test_01_pe_desk_can_upload_document(self, pe_desk_token):
        """PE Desk should be able to upload documents"""
        # Create a test file
        files = {"file": ("test_pan.pdf", b"Test PDF content", "application/pdf")}
        headers = {"Authorization": f"Bearer {pe_desk_token}"}
        
        response = requests.post(
            f"{BASE_URL}/api/company-master/upload/pan_card",
            files=files,
            headers=headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert "url" in data
        assert "filename" in data
        assert "pan_card" in data["filename"]
    
    def test_02_pe_manager_denied_upload_document(self, pe_manager_token):
        """PE Manager should get 403 when uploading documents"""
        files = {"file": ("test_pan.pdf", b"Test PDF content", "application/pdf")}
        headers = {"Authorization": f"Bearer {pe_manager_token}"}
        
        response = requests.post(
            f"{BASE_URL}/api/company-master/upload/pan_card",
            files=files,
            headers=headers
        )
        assert response.status_code == 403
    
    def test_03_invalid_document_type_rejected(self, pe_desk_token):
        """Invalid document type should be rejected"""
        files = {"file": ("test.pdf", b"Test PDF content", "application/pdf")}
        headers = {"Authorization": f"Bearer {pe_desk_token}"}
        
        response = requests.post(
            f"{BASE_URL}/api/company-master/upload/invalid_type",
            files=files,
            headers=headers
        )
        assert response.status_code == 400
        
        data = response.json()
        assert "Invalid document type" in data["detail"]
    
    def test_04_all_document_types_accepted(self, pe_desk_token):
        """All valid document types should be accepted"""
        valid_types = ["cml_cdsl", "cml_nsdl", "cancelled_cheque", "pan_card"]
        headers = {"Authorization": f"Bearer {pe_desk_token}"}
        
        for doc_type in valid_types:
            files = {"file": (f"test_{doc_type}.pdf", b"Test PDF content", "application/pdf")}
            response = requests.post(
                f"{BASE_URL}/api/company-master/upload/{doc_type}",
                files=files,
                headers=headers
            )
            assert response.status_code == 200, f"Failed for document type: {doc_type}"


class TestCompanyMasterDocumentDelete:
    """Test document delete functionality"""
    
    def test_01_pe_desk_can_delete_document(self, pe_desk_token):
        """PE Desk should be able to delete documents"""
        headers = {"Authorization": f"Bearer {pe_desk_token}"}
        
        # First upload a document
        files = {"file": ("test_delete.pdf", b"Test PDF content", "application/pdf")}
        upload_response = requests.post(
            f"{BASE_URL}/api/company-master/upload/pan_card",
            files=files,
            headers=headers
        )
        assert upload_response.status_code == 200
        
        # Then delete it
        response = requests.delete(
            f"{BASE_URL}/api/company-master/document/pan_card",
            headers=headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert "deleted" in data["message"].lower()
    
    def test_02_pe_manager_denied_delete_document(self, pe_manager_token):
        """PE Manager should get 403 when deleting documents"""
        headers = {"Authorization": f"Bearer {pe_manager_token}"}
        
        response = requests.delete(
            f"{BASE_URL}/api/company-master/document/pan_card",
            headers=headers
        )
        assert response.status_code == 403
    
    def test_03_invalid_document_type_rejected(self, pe_desk_token):
        """Invalid document type should be rejected for delete"""
        headers = {"Authorization": f"Bearer {pe_desk_token}"}
        
        response = requests.delete(
            f"{BASE_URL}/api/company-master/document/invalid_type",
            headers=headers
        )
        assert response.status_code == 400
        
        data = response.json()
        assert "Invalid document type" in data["detail"]


class TestCompanyMasterDataPersistence:
    """Test data persistence after updates"""
    
    def test_01_update_and_verify_persistence(self, pe_desk_client):
        """Update company master and verify data persists"""
        # Update with specific values
        update_data = {
            "company_name": "TEST_SMIFS Capital Markets Ltd",
            "company_address": "TEST_12, India Exchange Place, Kolkata - 700001",
            "company_cin": "U67120WB1994PLC064483",
            "company_gst": "19AABCS1234F1ZP",
            "company_pan": "aabcs1234f",  # lowercase to test uppercase conversion
            "cdsl_dp_id": "12058400",
            "nsdl_dp_id": "IN301774",
            "company_tan": "cals12345f",  # lowercase to test uppercase conversion
            "company_bank_name": "HDFC Bank",
            "company_bank_account": "50100123456789",
            "company_bank_ifsc": "hdfc0000001",  # lowercase to test uppercase conversion
            "company_bank_branch": "Fort Branch, Mumbai"
        }
        
        # Update
        put_response = pe_desk_client.put(f"{BASE_URL}/api/company-master", json=update_data)
        assert put_response.status_code == 200
        
        # Verify with GET
        get_response = pe_desk_client.get(f"{BASE_URL}/api/company-master")
        assert get_response.status_code == 200
        
        data = get_response.json()
        assert data["company_name"] == update_data["company_name"]
        assert data["company_address"] == update_data["company_address"]
        # Verify uppercase conversion
        assert data["company_pan"] == "AABCS1234F"
        assert data["company_tan"] == "CALS12345F"
        assert data["company_bank_ifsc"] == "HDFC0000001"
        
        # Cleanup - restore original values
        restore_data = {
            "company_name": "SMIFS Capital Markets Ltd",
            "company_address": "12, India Exchange Place, Kolkata - 700001",
            "company_cin": "U67120WB1994PLC064483",
            "company_gst": "19AABCS1234F1ZP",
            "company_pan": "AABCS1234F",
            "cdsl_dp_id": "12058400",
            "nsdl_dp_id": "IN301774",
            "company_tan": "CALS12345F",
            "company_bank_name": "HDFC Bank",
            "company_bank_account": "50100123456789",
            "company_bank_ifsc": "HDFC0000001",
            "company_bank_branch": "Fort Branch, Mumbai"
        }
        pe_desk_client.put(f"{BASE_URL}/api/company-master", json=restore_data)
