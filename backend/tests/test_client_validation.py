"""
Backend tests for Client Validation, Document Upload, and OCR functionality
Tests the bug fixes:
1. Required fields enforcement (name, pan_number, dp_id)
2. Document storage to /app/uploads/{client_id}/
3. OCR preview endpoint returning extracted_data structure
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestClientValidation:
    """Test client creation validation - required fields enforcement"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token for tests"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@privity.com",
            "password": "Admin@123"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        self.token = response.json()["token"]
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
    
    def test_empty_client_creation_fails_with_422(self):
        """Empty client creation should fail with 422 validation error"""
        response = requests.post(
            f"{BASE_URL}/api/clients",
            headers=self.headers,
            json={}
        )
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"
        
        # Verify error details mention required fields
        data = response.json()
        assert "detail" in data
        error_fields = [err.get("loc", [])[-1] for err in data["detail"]]
        assert "name" in error_fields, "Should require name field"
        assert "pan_number" in error_fields, "Should require pan_number field"
        assert "dp_id" in error_fields, "Should require dp_id field"
        print("PASS: Empty client creation correctly returns 422 with required field errors")
    
    def test_missing_name_fails(self):
        """Client creation without name should fail"""
        response = requests.post(
            f"{BASE_URL}/api/clients",
            headers=self.headers,
            json={"pan_number": "ABCDE1234F", "dp_id": "12345678"}
        )
        assert response.status_code == 422
        data = response.json()
        error_fields = [err.get("loc", [])[-1] for err in data["detail"]]
        assert "name" in error_fields
        print("PASS: Missing name correctly returns 422")
    
    def test_missing_pan_number_fails(self):
        """Client creation without pan_number should fail"""
        response = requests.post(
            f"{BASE_URL}/api/clients",
            headers=self.headers,
            json={"name": "Test Client", "dp_id": "12345678"}
        )
        assert response.status_code == 422
        data = response.json()
        error_fields = [err.get("loc", [])[-1] for err in data["detail"]]
        assert "pan_number" in error_fields
        print("PASS: Missing pan_number correctly returns 422")
    
    def test_missing_dp_id_fails(self):
        """Client creation without dp_id should fail"""
        response = requests.post(
            f"{BASE_URL}/api/clients",
            headers=self.headers,
            json={"name": "Test Client", "pan_number": "ABCDE1234F"}
        )
        assert response.status_code == 422
        data = response.json()
        error_fields = [err.get("loc", [])[-1] for err in data["detail"]]
        assert "dp_id" in error_fields
        print("PASS: Missing dp_id correctly returns 422")
    
    def test_valid_client_creation_succeeds(self):
        """Client creation with all required fields should succeed"""
        response = requests.post(
            f"{BASE_URL}/api/clients",
            headers=self.headers,
            json={
                "name": "TEST_ValidClient_Pytest",
                "pan_number": "PYTEST1234F",
                "dp_id": "PYTEST123"
            }
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["name"] == "TEST_ValidClient_Pytest"
        assert data["pan_number"] == "PYTEST1234F"
        assert data["dp_id"] == "PYTEST123"
        assert "id" in data
        assert "otc_ucc" in data
        print(f"PASS: Valid client created with ID: {data['id']}")
        
        # Cleanup - delete the test client
        delete_response = requests.delete(
            f"{BASE_URL}/api/clients/{data['id']}",
            headers=self.headers
        )
        assert delete_response.status_code == 200


class TestDocumentUpload:
    """Test document upload functionality"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token and create test client"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@privity.com",
            "password": "Admin@123"
        })
        assert response.status_code == 200
        self.token = response.json()["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
        
        # Create a test client for document upload
        create_response = requests.post(
            f"{BASE_URL}/api/clients",
            headers={**self.headers, "Content-Type": "application/json"},
            json={
                "name": "TEST_DocUploadClient",
                "pan_number": "DOCUP1234F",
                "dp_id": "DOCUP123"
            }
        )
        if create_response.status_code == 200:
            self.client_id = create_response.json()["id"]
        else:
            # Use existing client
            clients_response = requests.get(
                f"{BASE_URL}/api/clients?is_vendor=false",
                headers=self.headers
            )
            self.client_id = clients_response.json()[0]["id"]
    
    def test_document_upload_saves_file(self):
        """Document upload should save file and return document info"""
        # Create a simple test file
        test_file_content = b"Test image content for document upload"
        files = {
            "file": ("test_doc.png", test_file_content, "image/png")
        }
        data = {"doc_type": "pan_card"}
        
        response = requests.post(
            f"{BASE_URL}/api/clients/{self.client_id}/documents",
            headers=self.headers,
            files=files,
            data=data
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        result = response.json()
        assert "message" in result
        assert result["message"] == "Document uploaded successfully"
        assert "document" in result
        
        doc = result["document"]
        assert doc["doc_type"] == "pan_card"
        assert "filename" in doc
        assert "file_path" in doc
        assert self.client_id in doc["file_path"], "File path should contain client ID"
        assert "upload_date" in doc
        assert "ocr_data" in doc
        
        print(f"PASS: Document uploaded successfully to {doc['file_path']}")


class TestOCRPreview:
    """Test OCR preview endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@privity.com",
            "password": "Admin@123"
        })
        assert response.status_code == 200
        self.token = response.json()["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_ocr_preview_returns_extracted_data_structure(self):
        """OCR preview should return extracted_data structure"""
        test_file_content = b"Test image content for OCR"
        files = {
            "file": ("test_ocr.png", test_file_content, "image/png")
        }
        data = {"doc_type": "pan_card"}
        
        response = requests.post(
            f"{BASE_URL}/api/ocr/preview",
            headers=self.headers,
            files=files,
            data=data
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        result = response.json()
        assert "processed_at" in result
        assert "doc_type" in result
        assert result["doc_type"] == "pan_card"
        assert "status" in result
        assert "extracted_data" in result, "Response must contain extracted_data field"
        
        # Status can be 'processed', 'error', or 'pdf_uploaded'
        assert result["status"] in ["processed", "error", "pdf_uploaded"]
        
        print(f"PASS: OCR preview returns correct structure with status: {result['status']}")
    
    def test_ocr_preview_cml_copy(self):
        """OCR preview for CML copy should return extracted_data"""
        test_file_content = b"Test CML content"
        files = {
            "file": ("test_cml.png", test_file_content, "image/png")
        }
        data = {"doc_type": "cml_copy"}
        
        response = requests.post(
            f"{BASE_URL}/api/ocr/preview",
            headers=self.headers,
            files=files,
            data=data
        )
        
        assert response.status_code == 200
        result = response.json()
        assert "extracted_data" in result
        assert result["doc_type"] == "cml_copy"
        print("PASS: OCR preview for CML copy returns correct structure")
    
    def test_ocr_preview_cancelled_cheque(self):
        """OCR preview for cancelled cheque should return extracted_data"""
        test_file_content = b"Test cheque content"
        files = {
            "file": ("test_cheque.png", test_file_content, "image/png")
        }
        data = {"doc_type": "cancelled_cheque"}
        
        response = requests.post(
            f"{BASE_URL}/api/ocr/preview",
            headers=self.headers,
            files=files,
            data=data
        )
        
        assert response.status_code == 200
        result = response.json()
        assert "extracted_data" in result
        assert result["doc_type"] == "cancelled_cheque"
        print("PASS: OCR preview for cancelled cheque returns correct structure")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
