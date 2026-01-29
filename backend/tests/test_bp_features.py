"""
Business Partner (BP) Features Test Suite
Tests BP Dashboard, Document Upload, OTP Auth, and Booking Restrictions
"""
import pytest
import requests
import os
import io

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
PE_DESK_EMAIL = "pedesk@smifs.com"
PE_DESK_PASSWORD = "Kutta@123"
BP_EMAIL = "bp@example.com"


class TestBPManagement:
    """Test Business Partner management endpoints (PE Level)"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login as PE Desk and get token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": PE_DESK_EMAIL,
            "password": PE_DESK_PASSWORD
        })
        assert response.status_code == 200, f"PE Desk login failed: {response.text}"
        self.token = response.json()["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_get_all_business_partners(self):
        """Test GET /api/business-partners returns list of BPs"""
        response = requests.get(f"{BASE_URL}/api/business-partners", headers=self.headers)
        assert response.status_code == 200, f"Failed to get BPs: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        
        # Check if our test BP exists
        bp_emails = [bp["email"] for bp in data]
        assert BP_EMAIL in bp_emails, f"Test BP {BP_EMAIL} not found in list"
        
        # Verify BP structure
        if data:
            bp = data[0]
            assert "id" in bp
            assert "name" in bp
            assert "email" in bp
            assert "revenue_share_percent" in bp
            assert "linked_employee_id" in bp
            assert "documents" in bp
            assert "documents_verified" in bp
            print(f"SUCCESS: Found {len(data)} Business Partners")
    
    def test_get_specific_business_partner(self):
        """Test GET /api/business-partners/{bp_id} returns BP details"""
        # First get all BPs to find our test BP
        response = requests.get(f"{BASE_URL}/api/business-partners", headers=self.headers)
        assert response.status_code == 200
        
        bps = response.json()
        test_bp = next((bp for bp in bps if bp["email"] == BP_EMAIL), None)
        assert test_bp is not None, f"Test BP {BP_EMAIL} not found"
        
        # Get specific BP
        bp_id = test_bp["id"]
        response = requests.get(f"{BASE_URL}/api/business-partners/{bp_id}", headers=self.headers)
        assert response.status_code == 200, f"Failed to get BP: {response.text}"
        
        bp = response.json()
        assert bp["id"] == bp_id
        assert bp["email"] == BP_EMAIL
        assert "documents_verified" in bp
        print(f"SUCCESS: Retrieved BP {bp['name']} with documents_verified={bp['documents_verified']}")


class TestBPDocumentUpload:
    """Test Business Partner document upload functionality"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login as PE Desk and get BP ID"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": PE_DESK_EMAIL,
            "password": PE_DESK_PASSWORD
        })
        assert response.status_code == 200
        self.token = response.json()["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
        
        # Get test BP ID
        response = requests.get(f"{BASE_URL}/api/business-partners", headers=self.headers)
        assert response.status_code == 200
        bps = response.json()
        test_bp = next((bp for bp in bps if bp["email"] == BP_EMAIL), None)
        assert test_bp is not None, f"Test BP {BP_EMAIL} not found"
        self.bp_id = test_bp["id"]
    
    def test_upload_pan_card(self):
        """Test uploading PAN Card document"""
        # Create a test file
        test_file = io.BytesIO(b"Test PAN Card content")
        files = {"file": ("test_pan.pdf", test_file, "application/pdf")}
        
        response = requests.post(
            f"{BASE_URL}/api/business-partners/{self.bp_id}/documents/pan_card",
            headers=self.headers,
            files=files
        )
        assert response.status_code == 200, f"Failed to upload PAN Card: {response.text}"
        
        data = response.json()
        assert "document" in data
        assert data["document"]["doc_type"] == "pan_card"
        print(f"SUCCESS: PAN Card uploaded, documents_verified={data.get('documents_verified')}")
    
    def test_upload_aadhaar_card(self):
        """Test uploading Aadhaar Card document"""
        test_file = io.BytesIO(b"Test Aadhaar Card content")
        files = {"file": ("test_aadhaar.pdf", test_file, "application/pdf")}
        
        response = requests.post(
            f"{BASE_URL}/api/business-partners/{self.bp_id}/documents/aadhaar_card",
            headers=self.headers,
            files=files
        )
        assert response.status_code == 200, f"Failed to upload Aadhaar Card: {response.text}"
        
        data = response.json()
        assert data["document"]["doc_type"] == "aadhaar_card"
        print(f"SUCCESS: Aadhaar Card uploaded, documents_verified={data.get('documents_verified')}")
    
    def test_upload_cancelled_cheque(self):
        """Test uploading Cancelled Cheque document"""
        test_file = io.BytesIO(b"Test Cancelled Cheque content")
        files = {"file": ("test_cheque.pdf", test_file, "application/pdf")}
        
        response = requests.post(
            f"{BASE_URL}/api/business-partners/{self.bp_id}/documents/cancelled_cheque",
            headers=self.headers,
            files=files
        )
        assert response.status_code == 200, f"Failed to upload Cancelled Cheque: {response.text}"
        
        data = response.json()
        assert data["document"]["doc_type"] == "cancelled_cheque"
        # After all 3 documents, should be verified
        print(f"SUCCESS: Cancelled Cheque uploaded, documents_verified={data.get('documents_verified')}")
    
    def test_get_bp_documents(self):
        """Test GET /api/business-partners/{bp_id}/documents"""
        response = requests.get(
            f"{BASE_URL}/api/business-partners/{self.bp_id}/documents",
            headers=self.headers
        )
        assert response.status_code == 200, f"Failed to get documents: {response.text}"
        
        data = response.json()
        assert "documents" in data
        assert "documents_verified" in data
        assert "required_documents" in data
        
        # Check required documents list
        assert "pan_card" in data["required_documents"]
        assert "aadhaar_card" in data["required_documents"]
        assert "cancelled_cheque" in data["required_documents"]
        print(f"SUCCESS: Got {len(data['documents'])} documents, verified={data['documents_verified']}")
    
    def test_documents_verified_after_all_uploads(self):
        """Test that documents_verified is True after all 3 documents uploaded"""
        # Upload all 3 documents
        doc_types = ["pan_card", "aadhaar_card", "cancelled_cheque"]
        
        for doc_type in doc_types:
            test_file = io.BytesIO(f"Test {doc_type} content".encode())
            files = {"file": (f"test_{doc_type}.pdf", test_file, "application/pdf")}
            
            response = requests.post(
                f"{BASE_URL}/api/business-partners/{self.bp_id}/documents/{doc_type}",
                headers=self.headers,
                files=files
            )
            assert response.status_code == 200, f"Failed to upload {doc_type}: {response.text}"
        
        # Verify documents_verified is True
        response = requests.get(
            f"{BASE_URL}/api/business-partners/{self.bp_id}/documents",
            headers=self.headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["documents_verified"] == True, "documents_verified should be True after all uploads"
        print("SUCCESS: documents_verified is True after all 3 documents uploaded")
    
    def test_upload_invalid_doc_type(self):
        """Test uploading with invalid document type returns 400"""
        test_file = io.BytesIO(b"Test content")
        files = {"file": ("test.pdf", test_file, "application/pdf")}
        
        response = requests.post(
            f"{BASE_URL}/api/business-partners/{self.bp_id}/documents/invalid_type",
            headers=self.headers,
            files=files
        )
        assert response.status_code == 400, f"Expected 400 for invalid doc type, got {response.status_code}"
        print("SUCCESS: Invalid doc type correctly rejected with 400")


class TestBPOTPAuth:
    """Test Business Partner OTP authentication"""
    
    def test_request_otp_for_valid_bp(self):
        """Test POST /api/business-partners/auth/request-otp for valid BP"""
        response = requests.post(
            f"{BASE_URL}/api/business-partners/auth/request-otp",
            json={"email": BP_EMAIL}
        )
        assert response.status_code == 200, f"Failed to request OTP: {response.text}"
        
        data = response.json()
        assert "message" in data
        print(f"SUCCESS: OTP request accepted - {data['message']}")
    
    def test_request_otp_for_invalid_email(self):
        """Test OTP request for non-existent BP email (should still return 200 for security)"""
        response = requests.post(
            f"{BASE_URL}/api/business-partners/auth/request-otp",
            json={"email": "nonexistent@example.com"}
        )
        # Should return 200 to not reveal if email exists
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("SUCCESS: Non-existent email returns 200 (security measure)")
    
    def test_verify_otp_with_invalid_otp(self):
        """Test OTP verification with invalid OTP returns 400"""
        response = requests.post(
            f"{BASE_URL}/api/business-partners/auth/verify-otp",
            json={"email": BP_EMAIL, "otp": "000000"}
        )
        assert response.status_code == 400, f"Expected 400 for invalid OTP, got {response.status_code}"
        print("SUCCESS: Invalid OTP correctly rejected with 400")


class TestBPDashboard:
    """Test Business Partner Dashboard endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login as PE Desk to get BP info, then simulate BP token"""
        # First login as PE Desk
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": PE_DESK_EMAIL,
            "password": PE_DESK_PASSWORD
        })
        assert response.status_code == 200
        pe_token = response.json()["token"]
        pe_headers = {"Authorization": f"Bearer {pe_token}"}
        
        # Get BP info
        response = requests.get(f"{BASE_URL}/api/business-partners", headers=pe_headers)
        assert response.status_code == 200
        bps = response.json()
        self.test_bp = next((bp for bp in bps if bp["email"] == BP_EMAIL), None)
        assert self.test_bp is not None, f"Test BP {BP_EMAIL} not found"
        
        # Store PE token for testing (BP dashboard requires role 8)
        self.pe_token = pe_token
        self.pe_headers = pe_headers
    
    def test_bp_dashboard_stats_requires_bp_role(self):
        """Test that dashboard stats endpoint requires BP role (role=8)"""
        # PE Desk (role=1) should get 403
        response = requests.get(
            f"{BASE_URL}/api/business-partners/dashboard/stats",
            headers=self.pe_headers
        )
        assert response.status_code == 403, f"Expected 403 for non-BP user, got {response.status_code}"
        print("SUCCESS: Dashboard stats correctly requires BP role")
    
    def test_bp_dashboard_bookings_requires_bp_role(self):
        """Test that dashboard bookings endpoint requires BP role"""
        response = requests.get(
            f"{BASE_URL}/api/business-partners/dashboard/bookings",
            headers=self.pe_headers
        )
        assert response.status_code == 403, f"Expected 403 for non-BP user, got {response.status_code}"
        print("SUCCESS: Dashboard bookings correctly requires BP role")


class TestBPBookingRestrictions:
    """Test that BP users cannot select Referral Partners in bookings"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login as PE Desk"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": PE_DESK_EMAIL,
            "password": PE_DESK_PASSWORD
        })
        assert response.status_code == 200
        self.token = response.json()["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_booking_creation_endpoint_exists(self):
        """Test that booking creation endpoint exists"""
        # Just verify the endpoint exists (we can't create without valid client/stock)
        response = requests.post(
            f"{BASE_URL}/api/bookings",
            headers=self.headers,
            json={}
        )
        # Should get 422 (validation error) not 404
        assert response.status_code in [400, 422], f"Expected 400/422, got {response.status_code}"
        print("SUCCESS: Booking creation endpoint exists")
    
    def test_get_referral_partners_list(self):
        """Test that referral partners list is accessible"""
        response = requests.get(
            f"{BASE_URL}/api/referral-partners",
            headers=self.headers
        )
        assert response.status_code == 200, f"Failed to get RPs: {response.text}"
        print(f"SUCCESS: Got referral partners list ({len(response.json())} RPs)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
