"""
Test cases for Re-run OCR feature
Tests the POST /api/clients/{client_id}/rerun-ocr endpoint
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
PE_DESK_EMAIL = "pedesk@smifs.com"
PE_DESK_PASSWORD = "password"
TEST_CLIENT_ID = "d6e65ab9-d513-4a95-abec-d01fdfeb38e3"


@pytest.fixture
def pe_desk_token():
    """Get PE Desk authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": PE_DESK_EMAIL,
        "password": PE_DESK_PASSWORD
    })
    assert response.status_code == 200, f"Login failed: {response.text}"
    data = response.json()
    assert "token" in data, "No token in response"
    return data["token"]


@pytest.fixture
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture
def authenticated_client(api_client, pe_desk_token):
    """Session with auth header"""
    api_client.headers.update({"Authorization": f"Bearer {pe_desk_token}"})
    return api_client


class TestRerunOcrEndpoint:
    """Test cases for POST /api/clients/{client_id}/rerun-ocr"""
    
    def test_rerun_ocr_success(self, authenticated_client):
        """Test successful re-run OCR request by PE Level user"""
        response = authenticated_client.post(
            f"{BASE_URL}/api/clients/{TEST_CLIENT_ID}/rerun-ocr"
        )
        
        # Should succeed for PE Level user
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify response structure
        assert "client_id" in data, "Missing client_id in response"
        assert "client_name" in data, "Missing client_name in response"
        assert "rerun_at" in data, "Missing rerun_at in response"
        assert "documents_processed" in data, "Missing documents_processed in response"
        assert "old_vs_new" in data, "Missing old_vs_new in response"
        assert "update_applied" in data, "Missing update_applied in response"
        assert "errors" in data, "Missing errors in response"
        
        # Verify client_id matches
        assert data["client_id"] == TEST_CLIENT_ID
        
        print(f"Successfully processed {len(data['documents_processed'])} document(s)")
    
    def test_rerun_ocr_with_update_client(self, authenticated_client):
        """Test re-run OCR with update_client=true flag"""
        response = authenticated_client.post(
            f"{BASE_URL}/api/clients/{TEST_CLIENT_ID}/rerun-ocr?update_client=true"
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify response structure
        assert "update_applied" in data
        # update_applied depends on whether new data was found
        
        # If fields were updated, should have fields_updated
        if data["update_applied"]:
            assert "fields_updated" in data, "Missing fields_updated when update_applied is true"
    
    def test_rerun_ocr_with_specific_doc_type(self, authenticated_client):
        """Test re-run OCR for specific document type"""
        response = authenticated_client.post(
            f"{BASE_URL}/api/clients/{TEST_CLIENT_ID}/rerun-ocr?doc_types=pan_card"
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Should only process pan_card if present
        if data["documents_processed"]:
            doc_types_processed = [d["doc_type"] for d in data["documents_processed"]]
            for doc_type in doc_types_processed:
                assert doc_type == "pan_card", f"Expected only pan_card, got {doc_type}"
    
    def test_rerun_ocr_response_comparison_structure(self, authenticated_client):
        """Test that old_vs_new comparison data is structured correctly"""
        response = authenticated_client.post(
            f"{BASE_URL}/api/clients/{TEST_CLIENT_ID}/rerun-ocr"
        )
        
        assert response.status_code == 200
        
        data = response.json()
        
        # Check old_vs_new structure
        old_vs_new = data.get("old_vs_new", {})
        
        for doc_type, comparison in old_vs_new.items():
            assert "old_data" in comparison, f"Missing old_data for {doc_type}"
            assert "new_data" in comparison, f"Missing new_data for {doc_type}"
            assert "old_confidence" in comparison, f"Missing old_confidence for {doc_type}"
            assert "new_confidence" in comparison, f"Missing new_confidence for {doc_type}"
            
            # Confidence should be numeric
            assert isinstance(comparison["old_confidence"], (int, float))
            assert isinstance(comparison["new_confidence"], (int, float))
    
    def test_rerun_ocr_invalid_client(self, authenticated_client):
        """Test re-run OCR with invalid client ID"""
        invalid_client_id = "invalid-client-id-12345"
        
        response = authenticated_client.post(
            f"{BASE_URL}/api/clients/{invalid_client_id}/rerun-ocr"
        )
        
        # Should return 404 for invalid client
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
    
    def test_rerun_ocr_documents_processed_structure(self, authenticated_client):
        """Test documents_processed array structure"""
        response = authenticated_client.post(
            f"{BASE_URL}/api/clients/{TEST_CLIENT_ID}/rerun-ocr"
        )
        
        assert response.status_code == 200
        
        data = response.json()
        
        # Check documents_processed structure
        for doc in data.get("documents_processed", []):
            assert "doc_type" in doc, "Missing doc_type"
            assert "old_confidence" in doc, "Missing old_confidence"
            assert "new_confidence" in doc, "Missing new_confidence"
            assert "status" in doc, "Missing status"


class TestRerunOcrAuthentication:
    """Test authentication and authorization for Re-run OCR"""
    
    def test_rerun_ocr_without_auth(self, api_client):
        """Test re-run OCR without authentication"""
        response = api_client.post(
            f"{BASE_URL}/api/clients/{TEST_CLIENT_ID}/rerun-ocr"
        )
        
        # Should return 401 without auth
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
    
    def test_rerun_ocr_pe_desk_success(self, api_client):
        """Test that PE Desk (role 1) can re-run OCR"""
        # Login as PE Desk
        login_response = api_client.post(f"{BASE_URL}/api/auth/login", json={
            "email": PE_DESK_EMAIL,
            "password": PE_DESK_PASSWORD
        })
        
        assert login_response.status_code == 200
        token = login_response.json()["token"]
        user_role = login_response.json()["user"]["role"]
        
        # Verify user is PE Desk (role 1)
        assert user_role == 1, f"Expected role 1 (PE Desk), got role {user_role}"
        
        # Make request with PE Desk token
        api_client.headers.update({"Authorization": f"Bearer {token}"})
        response = api_client.post(
            f"{BASE_URL}/api/clients/{TEST_CLIENT_ID}/rerun-ocr"
        )
        
        # PE Desk should be able to re-run OCR
        assert response.status_code == 200, f"PE Desk should be able to re-run OCR. Got {response.status_code}: {response.text}"


class TestClientWithDocuments:
    """Test client document retrieval"""
    
    def test_get_client_documents(self, authenticated_client):
        """Test getting client with documents"""
        response = authenticated_client.get(
            f"{BASE_URL}/api/clients/{TEST_CLIENT_ID}"
        )
        
        assert response.status_code == 200
        
        data = response.json()
        
        # Verify client has documents
        assert "documents" in data, "Missing documents field"
        
        if data["documents"]:
            doc = data["documents"][0]
            # Verify document structure
            assert "doc_type" in doc, "Missing doc_type in document"
            assert "upload_date" in doc or "uploaded_at" in doc, "Missing upload date"
            
            # Check for OCR data if present
            if "ocr_data" in doc and doc["ocr_data"]:
                ocr = doc["ocr_data"]
                print(f"Document {doc['doc_type']} has OCR data with confidence: {ocr.get('confidence', 'N/A')}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
