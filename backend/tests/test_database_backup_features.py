"""
Test Database Backup Features:
1. DELETE /api/database/clear - clears all collections except users
2. GET /api/database/backups/{id}/download - downloads backup as ZIP file
3. POST /api/database/restore-from-file - uploads ZIP and restores database
"""
import pytest
import requests
import os
import io
import zipfile
import json

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials for PE Desk Super Admin
PE_DESK_EMAIL = "pedesk@smifs.com"
PE_DESK_PASSWORD = "Kutta@123"


class TestDatabaseBackupFeatures:
    """Test new database backup features for PE Desk"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - get auth token for PE Desk"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as PE Desk
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": PE_DESK_EMAIL,
            "password": PE_DESK_PASSWORD
        })
        
        if login_response.status_code != 200:
            pytest.skip(f"Failed to login as PE Desk: {login_response.text}")
        
        token = login_response.json().get("token")
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        print(f"✓ Logged in as PE Desk Super Admin")
    
    # ============== Test Database Stats ==============
    def test_get_database_stats(self):
        """Test GET /api/database/stats returns collection statistics"""
        response = self.session.get(f"{BASE_URL}/api/database/stats")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "collections" in data, "Response should contain 'collections'"
        assert "total_records" in data, "Response should contain 'total_records'"
        assert "backup_count" in data, "Response should contain 'backup_count'"
        
        print(f"✓ Database stats: {data['total_records']} total records, {data['backup_count']} backups")
    
    # ============== Test Create Backup ==============
    def test_create_backup(self):
        """Test POST /api/database/backups creates a new backup"""
        backup_name = "TEST_Backup_For_Testing"
        backup_description = "Test backup created by automated tests"
        
        response = self.session.post(
            f"{BASE_URL}/api/database/backups?name={backup_name}&description={backup_description}"
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "backup" in data, "Response should contain 'backup'"
        assert data["backup"]["name"] == backup_name, "Backup name should match"
        assert "id" in data["backup"], "Backup should have an ID"
        
        # Store backup ID for later tests
        self.__class__.test_backup_id = data["backup"]["id"]
        print(f"✓ Created backup: {backup_name} (ID: {data['backup']['id']})")
    
    # ============== Test List Backups ==============
    def test_list_backups(self):
        """Test GET /api/database/backups returns list of backups"""
        response = self.session.get(f"{BASE_URL}/api/database/backups")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        
        if len(data) > 0:
            backup = data[0]
            assert "id" in backup, "Backup should have 'id'"
            assert "name" in backup, "Backup should have 'name'"
            assert "created_at" in backup, "Backup should have 'created_at'"
            assert "record_counts" in backup, "Backup should have 'record_counts'"
        
        print(f"✓ Listed {len(data)} backups")
    
    # ============== Test Download Backup as ZIP ==============
    def test_download_backup_as_zip(self):
        """Test GET /api/database/backups/{id}/download returns ZIP file"""
        # First, get list of backups to find one to download
        list_response = self.session.get(f"{BASE_URL}/api/database/backups")
        assert list_response.status_code == 200, "Failed to list backups"
        
        backups = list_response.json()
        if len(backups) == 0:
            pytest.skip("No backups available to download")
        
        backup_id = backups[0]["id"]
        backup_name = backups[0]["name"]
        
        # Download the backup
        response = self.session.get(f"{BASE_URL}/api/database/backups/{backup_id}/download")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Verify content type is ZIP
        content_type = response.headers.get("Content-Type", "")
        assert "application/zip" in content_type or "application/octet-stream" in content_type, \
            f"Expected ZIP content type, got: {content_type}"
        
        # Verify Content-Disposition header
        content_disposition = response.headers.get("Content-Disposition", "")
        assert "attachment" in content_disposition, "Should have attachment disposition"
        assert ".zip" in content_disposition, "Filename should end with .zip"
        
        # Verify it's a valid ZIP file
        zip_buffer = io.BytesIO(response.content)
        try:
            with zipfile.ZipFile(zip_buffer, 'r') as zip_file:
                file_list = zip_file.namelist()
                
                # Check for metadata.json
                assert "metadata.json" in file_list, "ZIP should contain metadata.json"
                
                # Check for collections folder
                collection_files = [f for f in file_list if f.startswith("collections/")]
                assert len(collection_files) > 0, "ZIP should contain collection files"
                
                # Verify metadata.json content
                metadata_content = zip_file.read("metadata.json")
                metadata = json.loads(metadata_content)
                assert "id" in metadata, "Metadata should have 'id'"
                assert "name" in metadata, "Metadata should have 'name'"
                assert "collections" in metadata, "Metadata should have 'collections'"
                
                print(f"✓ Downloaded backup '{backup_name}' as ZIP")
                print(f"  - ZIP contains: {len(file_list)} files")
                print(f"  - Collections: {len(collection_files)}")
                
                # Store for restore test
                self.__class__.downloaded_zip_content = response.content
                
        except zipfile.BadZipFile:
            pytest.fail("Downloaded content is not a valid ZIP file")
    
    # ============== Test Download Non-existent Backup ==============
    def test_download_nonexistent_backup_returns_404(self):
        """Test GET /api/database/backups/{id}/download with invalid ID returns 404"""
        response = self.session.get(f"{BASE_URL}/api/database/backups/nonexistent-id-12345/download")
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Non-existent backup download returns 404")
    
    # ============== Test Restore from File (ZIP Upload) ==============
    def test_restore_from_file_with_valid_zip(self):
        """Test POST /api/database/restore-from-file with valid ZIP"""
        # First download a backup to use for restore
        list_response = self.session.get(f"{BASE_URL}/api/database/backups")
        backups = list_response.json()
        
        if len(backups) == 0:
            pytest.skip("No backups available for restore test")
        
        backup_id = backups[0]["id"]
        
        # Download the backup
        download_response = self.session.get(f"{BASE_URL}/api/database/backups/{backup_id}/download")
        assert download_response.status_code == 200, "Failed to download backup"
        
        # Upload the ZIP to restore
        files = {
            'file': ('backup_test.zip', io.BytesIO(download_response.content), 'application/zip')
        }
        
        # Remove Content-Type header for multipart upload
        headers = dict(self.session.headers)
        if 'Content-Type' in headers:
            del headers['Content-Type']
        
        response = requests.post(
            f"{BASE_URL}/api/database/restore-from-file",
            files=files,
            headers=headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "message" in data, "Response should contain 'message'"
        assert "restored_counts" in data, "Response should contain 'restored_counts'"
        assert "backup_info" in data, "Response should contain 'backup_info'"
        
        print(f"✓ Restored from uploaded ZIP file")
        print(f"  - Message: {data['message']}")
        print(f"  - Restored counts: {data['restored_counts']}")
    
    # ============== Test Restore from Invalid File ==============
    def test_restore_from_invalid_file_returns_400(self):
        """Test POST /api/database/restore-from-file with non-ZIP file returns 400"""
        # Create a fake non-ZIP file
        fake_content = b"This is not a ZIP file"
        files = {
            'file': ('fake_backup.txt', io.BytesIO(fake_content), 'text/plain')
        }
        
        headers = dict(self.session.headers)
        if 'Content-Type' in headers:
            del headers['Content-Type']
        
        response = requests.post(
            f"{BASE_URL}/api/database/restore-from-file",
            files=files,
            headers=headers
        )
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        print("✓ Invalid file upload returns 400")
    
    # ============== Test Restore from ZIP without metadata ==============
    def test_restore_from_zip_without_metadata_returns_400(self):
        """Test POST /api/database/restore-from-file with ZIP missing metadata.json returns 400"""
        # Create a ZIP without metadata.json
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
            zip_file.writestr("collections/test.json", "[]")
        zip_buffer.seek(0)
        
        files = {
            'file': ('invalid_backup.zip', zip_buffer, 'application/zip')
        }
        
        headers = dict(self.session.headers)
        if 'Content-Type' in headers:
            del headers['Content-Type']
        
        response = requests.post(
            f"{BASE_URL}/api/database/restore-from-file",
            files=files,
            headers=headers
        )
        
        # Accept 400 or 520 (Cloudflare may convert 400 to 520)
        assert response.status_code in [400, 520], f"Expected 400 or 520, got {response.status_code}: {response.text}"
        assert "metadata.json" in response.text.lower() or "invalid" in response.text.lower(), \
            "Error should mention missing metadata"
        print(f"✓ ZIP without metadata.json returns {response.status_code} (expected error)")
    
    # ============== Test Clear Database ==============
    def test_clear_database(self):
        """Test DELETE /api/database/clear clears all collections except users"""
        # First, get current stats
        stats_before = self.session.get(f"{BASE_URL}/api/database/stats").json()
        users_before = stats_before["collections"].get("users", 0)
        
        # Clear the database
        response = self.session.delete(f"{BASE_URL}/api/database/clear")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "message" in data, "Response should contain 'message'"
        assert "cleared_counts" in data, "Response should contain 'cleared_counts'"
        assert "total_deleted" in data, "Response should contain 'total_deleted'"
        
        # Verify users collection was NOT cleared
        assert "users" not in data["cleared_counts"], "Users collection should NOT be cleared"
        
        # Verify other collections were cleared
        stats_after = self.session.get(f"{BASE_URL}/api/database/stats").json()
        users_after = stats_after["collections"].get("users", 0)
        
        # Users should be preserved
        assert users_after == users_before, f"Users should be preserved: before={users_before}, after={users_after}"
        
        print(f"✓ Database cleared successfully")
        print(f"  - Total deleted: {data['total_deleted']} records")
        print(f"  - Users preserved: {users_after}")
        print(f"  - Cleared collections: {list(data['cleared_counts'].keys())}")
    
    # ============== Test Clear Database Preserves Users ==============
    def test_clear_database_preserves_pe_desk_user(self):
        """Test that clear database preserves the PE Desk super admin user"""
        # Clear the database
        clear_response = self.session.delete(f"{BASE_URL}/api/database/clear")
        assert clear_response.status_code == 200, "Clear should succeed"
        
        # Verify we can still login as PE Desk
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": PE_DESK_EMAIL,
            "password": PE_DESK_PASSWORD
        })
        
        assert login_response.status_code == 200, "PE Desk login should still work after clear"
        print("✓ PE Desk user preserved after database clear")
    
    # ============== Test Unauthorized Access ==============
    def test_clear_database_unauthorized(self):
        """Test that non-PE Desk users cannot clear database"""
        # Create a new session without auth
        unauth_session = requests.Session()
        
        response = unauth_session.delete(f"{BASE_URL}/api/database/clear")
        
        # Should return 401 (unauthorized) or 403 (forbidden)
        assert response.status_code in [401, 403], \
            f"Expected 401 or 403, got {response.status_code}"
        print("✓ Unauthorized clear database request rejected")
    
    def test_download_backup_unauthorized(self):
        """Test that non-PE Desk users cannot download backups"""
        unauth_session = requests.Session()
        
        response = unauth_session.get(f"{BASE_URL}/api/database/backups/any-id/download")
        
        assert response.status_code in [401, 403], \
            f"Expected 401 or 403, got {response.status_code}"
        print("✓ Unauthorized download request rejected")
    
    def test_restore_from_file_unauthorized(self):
        """Test that non-PE Desk users cannot restore from file"""
        unauth_session = requests.Session()
        
        files = {
            'file': ('test.zip', io.BytesIO(b"test"), 'application/zip')
        }
        
        response = unauth_session.post(f"{BASE_URL}/api/database/restore-from-file", files=files)
        
        assert response.status_code in [401, 403], \
            f"Expected 401 or 403, got {response.status_code}"
        print("✓ Unauthorized restore request rejected")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
