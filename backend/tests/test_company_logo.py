"""
Company Logo Upload Feature Tests
Tests for POST /api/company-master/upload-logo and DELETE /api/company-master/logo endpoints
"""
import pytest
import requests
import os
import io

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials for PE Desk (Super Admin)
PE_DESK_EMAIL = "pedesk@smifs.com"
PE_DESK_PASSWORD = "Kutta@123"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for PE Desk user"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": PE_DESK_EMAIL, "password": PE_DESK_PASSWORD}
    )
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip("Authentication failed - skipping tests")


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Get headers with auth token"""
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture
def test_png_file():
    """Create a minimal valid PNG file for testing"""
    # Minimal valid PNG (1x1 pixel, red)
    png_data = bytes([
        0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,  # PNG signature
        0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,  # IHDR chunk
        0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,  # 1x1 pixel
        0x08, 0x02, 0x00, 0x00, 0x00, 0x90, 0x77, 0x53,
        0xDE, 0x00, 0x00, 0x00, 0x0C, 0x49, 0x44, 0x41,  # IDAT chunk
        0x54, 0x08, 0xD7, 0x63, 0xF8, 0xFF, 0xFF, 0x3F,
        0x00, 0x05, 0xFE, 0x02, 0xFE, 0xDC, 0xCC, 0x59,
        0xE7, 0x00, 0x00, 0x00, 0x00, 0x49, 0x45, 0x4E,  # IEND chunk
        0x44, 0xAE, 0x42, 0x60, 0x82
    ])
    return io.BytesIO(png_data)


@pytest.fixture
def test_jpg_file():
    """Create a minimal valid JPEG file for testing"""
    # Minimal valid JPEG (1x1 pixel)
    jpg_data = bytes([
        0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x10, 0x4A, 0x46,
        0x49, 0x46, 0x00, 0x01, 0x01, 0x00, 0x00, 0x01,
        0x00, 0x01, 0x00, 0x00, 0xFF, 0xDB, 0x00, 0x43,
        0x00, 0x08, 0x06, 0x06, 0x07, 0x06, 0x05, 0x08,
        0x07, 0x07, 0x07, 0x09, 0x09, 0x08, 0x0A, 0x0C,
        0x14, 0x0D, 0x0C, 0x0B, 0x0B, 0x0C, 0x19, 0x12,
        0x13, 0x0F, 0x14, 0x1D, 0x1A, 0x1F, 0x1E, 0x1D,
        0x1A, 0x1C, 0x1C, 0x20, 0x24, 0x2E, 0x27, 0x20,
        0x22, 0x2C, 0x23, 0x1C, 0x1C, 0x28, 0x37, 0x29,
        0x2C, 0x30, 0x31, 0x34, 0x34, 0x34, 0x1F, 0x27,
        0x39, 0x3D, 0x38, 0x32, 0x3C, 0x2E, 0x33, 0x34,
        0x32, 0xFF, 0xC0, 0x00, 0x0B, 0x08, 0x00, 0x01,
        0x00, 0x01, 0x01, 0x01, 0x11, 0x00, 0xFF, 0xC4,
        0x00, 0x1F, 0x00, 0x00, 0x01, 0x05, 0x01, 0x01,
        0x01, 0x01, 0x01, 0x01, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x01, 0x02, 0x03, 0x04,
        0x05, 0x06, 0x07, 0x08, 0x09, 0x0A, 0x0B, 0xFF,
        0xC4, 0x00, 0xB5, 0x10, 0x00, 0x02, 0x01, 0x03,
        0x03, 0x02, 0x04, 0x03, 0x05, 0x05, 0x04, 0x04,
        0x00, 0x00, 0x01, 0x7D, 0x01, 0x02, 0x03, 0x00,
        0x04, 0x11, 0x05, 0x12, 0x21, 0x31, 0x41, 0x06,
        0x13, 0x51, 0x61, 0x07, 0x22, 0x71, 0x14, 0x32,
        0x81, 0x91, 0xA1, 0x08, 0x23, 0x42, 0xB1, 0xC1,
        0x15, 0x52, 0xD1, 0xF0, 0x24, 0x33, 0x62, 0x72,
        0x82, 0x09, 0x0A, 0x16, 0x17, 0x18, 0x19, 0x1A,
        0x25, 0x26, 0x27, 0x28, 0x29, 0x2A, 0x34, 0x35,
        0x36, 0x37, 0x38, 0x39, 0x3A, 0x43, 0x44, 0x45,
        0x46, 0x47, 0x48, 0x49, 0x4A, 0x53, 0x54, 0x55,
        0x56, 0x57, 0x58, 0x59, 0x5A, 0x63, 0x64, 0x65,
        0x66, 0x67, 0x68, 0x69, 0x6A, 0x73, 0x74, 0x75,
        0x76, 0x77, 0x78, 0x79, 0x7A, 0x83, 0x84, 0x85,
        0x86, 0x87, 0x88, 0x89, 0x8A, 0x92, 0x93, 0x94,
        0x95, 0x96, 0x97, 0x98, 0x99, 0x9A, 0xA2, 0xA3,
        0xA4, 0xA5, 0xA6, 0xA7, 0xA8, 0xA9, 0xAA, 0xB2,
        0xB3, 0xB4, 0xB5, 0xB6, 0xB7, 0xB8, 0xB9, 0xBA,
        0xC2, 0xC3, 0xC4, 0xC5, 0xC6, 0xC7, 0xC8, 0xC9,
        0xCA, 0xD2, 0xD3, 0xD4, 0xD5, 0xD6, 0xD7, 0xD8,
        0xD9, 0xDA, 0xE1, 0xE2, 0xE3, 0xE4, 0xE5, 0xE6,
        0xE7, 0xE8, 0xE9, 0xEA, 0xF1, 0xF2, 0xF3, 0xF4,
        0xF5, 0xF6, 0xF7, 0xF8, 0xF9, 0xFA, 0xFF, 0xDA,
        0x00, 0x08, 0x01, 0x01, 0x00, 0x00, 0x3F, 0x00,
        0xFB, 0xD5, 0xDB, 0x20, 0xA8, 0xF1, 0x7F, 0xFF,
        0xD9
    ])
    return io.BytesIO(jpg_data)


class TestCompanyLogoUpload:
    """Tests for POST /api/company-master/upload-logo endpoint"""
    
    def test_01_upload_logo_png_success(self, auth_headers, test_png_file):
        """Test uploading a PNG logo successfully"""
        files = {"file": ("test_logo.png", test_png_file, "image/png")}
        response = requests.post(
            f"{BASE_URL}/api/company-master/upload-logo",
            headers=auth_headers,
            files=files
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "message" in data
        assert "url" in data
        assert "filename" in data
        assert data["message"] == "Company logo uploaded successfully"
        assert data["url"].startswith("/uploads/company/")
        assert "company_logo_" in data["filename"]
        assert data["filename"].endswith(".png")
        print(f"✓ PNG logo uploaded: {data['url']}")
    
    def test_02_upload_logo_jpg_success(self, auth_headers, test_jpg_file):
        """Test uploading a JPG logo successfully"""
        files = {"file": ("test_logo.jpg", test_jpg_file, "image/jpeg")}
        response = requests.post(
            f"{BASE_URL}/api/company-master/upload-logo",
            headers=auth_headers,
            files=files
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["message"] == "Company logo uploaded successfully"
        assert data["filename"].endswith(".jpg")
        print(f"✓ JPG logo uploaded: {data['url']}")
    
    def test_03_logo_url_persists_in_company_master(self, auth_headers, test_png_file):
        """Test that logo_url is returned in GET /api/company-master"""
        # First upload a logo
        files = {"file": ("persist_test.png", test_png_file, "image/png")}
        upload_response = requests.post(
            f"{BASE_URL}/api/company-master/upload-logo",
            headers=auth_headers,
            files=files
        )
        assert upload_response.status_code == 200
        uploaded_url = upload_response.json()["url"]
        
        # Then verify it's in company-master response
        get_response = requests.get(
            f"{BASE_URL}/api/company-master",
            headers=auth_headers
        )
        assert get_response.status_code == 200
        
        data = get_response.json()
        assert "logo_url" in data
        assert data["logo_url"] == uploaded_url
        print(f"✓ Logo URL persists: {data['logo_url']}")
    
    def test_04_upload_replaces_old_logo(self, auth_headers, test_png_file, test_jpg_file):
        """Test that uploading a new logo replaces the old one"""
        # Upload first logo
        files1 = {"file": ("first_logo.png", test_png_file, "image/png")}
        response1 = requests.post(
            f"{BASE_URL}/api/company-master/upload-logo",
            headers=auth_headers,
            files=files1
        )
        assert response1.status_code == 200
        first_url = response1.json()["url"]
        
        # Upload second logo
        files2 = {"file": ("second_logo.jpg", test_jpg_file, "image/jpeg")}
        response2 = requests.post(
            f"{BASE_URL}/api/company-master/upload-logo",
            headers=auth_headers,
            files=files2
        )
        assert response2.status_code == 200
        second_url = response2.json()["url"]
        
        # Verify the URL changed
        assert first_url != second_url
        
        # Verify company-master has the new URL
        get_response = requests.get(
            f"{BASE_URL}/api/company-master",
            headers=auth_headers
        )
        assert get_response.status_code == 200
        assert get_response.json()["logo_url"] == second_url
        print(f"✓ Logo replaced: {first_url} -> {second_url}")
    
    def test_05_upload_invalid_file_type_rejected(self, auth_headers):
        """Test that invalid file types are rejected"""
        # Try to upload a text file
        invalid_file = io.BytesIO(b"This is not an image")
        files = {"file": ("test.txt", invalid_file, "text/plain")}
        response = requests.post(
            f"{BASE_URL}/api/company-master/upload-logo",
            headers=auth_headers,
            files=files
        )
        
        assert response.status_code == 400
        assert "Invalid file type" in response.json().get("detail", "")
        print("✓ Invalid file type rejected")
    
    def test_06_upload_without_auth_fails(self, test_png_file):
        """Test that upload without authentication fails"""
        files = {"file": ("test_logo.png", test_png_file, "image/png")}
        response = requests.post(
            f"{BASE_URL}/api/company-master/upload-logo",
            files=files
        )
        
        assert response.status_code in [401, 403]
        print("✓ Unauthenticated upload rejected")


class TestCompanyLogoDelete:
    """Tests for DELETE /api/company-master/logo endpoint"""
    
    def test_01_delete_logo_success(self, auth_headers, test_png_file):
        """Test deleting a logo successfully"""
        # First upload a logo
        files = {"file": ("delete_test.png", test_png_file, "image/png")}
        upload_response = requests.post(
            f"{BASE_URL}/api/company-master/upload-logo",
            headers=auth_headers,
            files=files
        )
        assert upload_response.status_code == 200
        
        # Then delete it
        delete_response = requests.delete(
            f"{BASE_URL}/api/company-master/logo",
            headers=auth_headers
        )
        
        assert delete_response.status_code == 200
        data = delete_response.json()
        assert data["message"] == "Company logo deleted successfully"
        print("✓ Logo deleted successfully")
    
    def test_02_logo_url_null_after_delete(self, auth_headers, test_png_file):
        """Test that logo_url is null after deletion"""
        # Upload a logo
        files = {"file": ("null_test.png", test_png_file, "image/png")}
        requests.post(
            f"{BASE_URL}/api/company-master/upload-logo",
            headers=auth_headers,
            files=files
        )
        
        # Delete it
        requests.delete(
            f"{BASE_URL}/api/company-master/logo",
            headers=auth_headers
        )
        
        # Verify logo_url is null
        get_response = requests.get(
            f"{BASE_URL}/api/company-master",
            headers=auth_headers
        )
        assert get_response.status_code == 200
        assert get_response.json()["logo_url"] is None
        print("✓ Logo URL is null after deletion")
    
    def test_03_delete_without_auth_fails(self):
        """Test that delete without authentication fails"""
        response = requests.delete(
            f"{BASE_URL}/api/company-master/logo"
        )
        
        assert response.status_code in [401, 403]
        print("✓ Unauthenticated delete rejected")
    
    def test_04_delete_nonexistent_logo_succeeds(self, auth_headers):
        """Test that deleting when no logo exists still succeeds"""
        # First ensure no logo exists
        requests.delete(
            f"{BASE_URL}/api/company-master/logo",
            headers=auth_headers
        )
        
        # Try to delete again
        response = requests.delete(
            f"{BASE_URL}/api/company-master/logo",
            headers=auth_headers
        )
        
        # Should still succeed (idempotent)
        assert response.status_code == 200
        print("✓ Delete nonexistent logo succeeds (idempotent)")


class TestCompanyLogoIntegration:
    """Integration tests for logo feature"""
    
    def test_01_full_logo_lifecycle(self, auth_headers, test_png_file, test_jpg_file):
        """Test complete logo lifecycle: upload -> verify -> replace -> delete"""
        # 1. Upload PNG logo
        files1 = {"file": ("lifecycle_test.png", test_png_file, "image/png")}
        upload1 = requests.post(
            f"{BASE_URL}/api/company-master/upload-logo",
            headers=auth_headers,
            files=files1
        )
        assert upload1.status_code == 200
        url1 = upload1.json()["url"]
        print(f"  Step 1: Uploaded PNG logo: {url1}")
        
        # 2. Verify logo persists
        get1 = requests.get(f"{BASE_URL}/api/company-master", headers=auth_headers)
        assert get1.json()["logo_url"] == url1
        print("  Step 2: Logo URL persists in company-master")
        
        # 3. Replace with JPG logo
        files2 = {"file": ("lifecycle_test.jpg", test_jpg_file, "image/jpeg")}
        upload2 = requests.post(
            f"{BASE_URL}/api/company-master/upload-logo",
            headers=auth_headers,
            files=files2
        )
        assert upload2.status_code == 200
        url2 = upload2.json()["url"]
        assert url1 != url2
        print(f"  Step 3: Replaced with JPG logo: {url2}")
        
        # 4. Verify replacement
        get2 = requests.get(f"{BASE_URL}/api/company-master", headers=auth_headers)
        assert get2.json()["logo_url"] == url2
        print("  Step 4: Replacement verified")
        
        # 5. Delete logo
        delete = requests.delete(f"{BASE_URL}/api/company-master/logo", headers=auth_headers)
        assert delete.status_code == 200
        print("  Step 5: Logo deleted")
        
        # 6. Verify deletion
        get3 = requests.get(f"{BASE_URL}/api/company-master", headers=auth_headers)
        assert get3.json()["logo_url"] is None
        print("  Step 6: Deletion verified - logo_url is null")
        
        print("✓ Full logo lifecycle test passed")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
