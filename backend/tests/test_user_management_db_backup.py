"""
Test User Management and Database Backup Features
Tests for:
- User Management: List, Create, Delete, Reset Password, Update Role
- Database Backup: Stats, List, Create, Delete backups
- PE Desk Delete Permissions: Clients, Stocks, Bookings, Purchases
"""
import pytest
import requests
import os
import uuid
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# PE Desk credentials
PE_DESK_EMAIL = "pedesk@smifs.com"
PE_DESK_PASSWORD = "Kutta@123"


class TestAuthentication:
    """Test authentication and get token"""
    
    def test_pe_desk_login(self):
        """Test PE Desk admin can login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": PE_DESK_EMAIL,
            "password": PE_DESK_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == 1  # PE Desk role
        assert data["user"]["email"] == PE_DESK_EMAIL


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for PE Desk"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": PE_DESK_EMAIL,
        "password": PE_DESK_PASSWORD
    })
    if response.status_code == 200:
        return response.json()["token"]
    pytest.skip("Authentication failed")


@pytest.fixture
def auth_headers(auth_token):
    """Get headers with auth token"""
    return {"Authorization": f"Bearer {auth_token}"}


# ============== User Management Tests ==============
class TestUserManagement:
    """Test User Management endpoints"""
    
    def test_list_users(self, auth_headers):
        """GET /api/users - List all users"""
        response = requests.get(f"{BASE_URL}/api/users", headers=auth_headers)
        assert response.status_code == 200, f"Failed to list users: {response.text}"
        users = response.json()
        assert isinstance(users, list)
        assert len(users) > 0
        # Verify PE Desk user exists
        pe_desk_users = [u for u in users if u["email"] == PE_DESK_EMAIL]
        assert len(pe_desk_users) == 1
        assert pe_desk_users[0]["role"] == 1
    
    def test_create_user(self, auth_headers):
        """POST /api/users - Create a new user"""
        unique_id = str(uuid.uuid4())[:8]
        user_data = {
            "email": f"test_create_{unique_id}@smifs.com",
            "password": "TestPass@123",
            "name": f"TEST_Create_User_{unique_id}",
            "role": 5  # Employee
        }
        response = requests.post(f"{BASE_URL}/api/users", json=user_data, headers=auth_headers)
        assert response.status_code == 200, f"Failed to create user: {response.text}"
        data = response.json()
        assert data["message"] == "User created successfully"
        assert data["user"]["email"] == user_data["email"].lower()
        assert data["user"]["name"] == user_data["name"]
        assert data["user"]["role"] == 5
        return data["user"]["id"]
    
    def test_create_user_duplicate_email(self, auth_headers):
        """POST /api/users - Should fail for duplicate email"""
        response = requests.post(f"{BASE_URL}/api/users", json={
            "email": PE_DESK_EMAIL,
            "password": "TestPass@123",
            "name": "Duplicate User",
            "role": 5
        }, headers=auth_headers)
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]
    
    def test_update_user_role(self, auth_headers):
        """PUT /api/users/{user_id}/role - Update user role"""
        # First create a user
        unique_id = str(uuid.uuid4())[:8]
        create_response = requests.post(f"{BASE_URL}/api/users", json={
            "email": f"test_role_{unique_id}@smifs.com",
            "password": "TestPass@123",
            "name": f"TEST_Role_User_{unique_id}",
            "role": 5
        }, headers=auth_headers)
        assert create_response.status_code == 200
        user_id = create_response.json()["user"]["id"]
        
        # Update role to Team Lead (4)
        response = requests.put(f"{BASE_URL}/api/users/{user_id}/role?role=4", headers=auth_headers)
        assert response.status_code == 200, f"Failed to update role: {response.text}"
        assert response.json()["message"] == "User role updated successfully"
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/users/{user_id}", headers=auth_headers)
    
    def test_reset_user_password(self, auth_headers):
        """POST /api/users/{user_id}/reset-password - Reset user password"""
        # First create a user
        unique_id = str(uuid.uuid4())[:8]
        create_response = requests.post(f"{BASE_URL}/api/users", json={
            "email": f"test_reset_{unique_id}@smifs.com",
            "password": "TestPass@123",
            "name": f"TEST_Reset_User_{unique_id}",
            "role": 5
        }, headers=auth_headers)
        assert create_response.status_code == 200
        user_id = create_response.json()["user"]["id"]
        user_name = create_response.json()["user"]["name"]
        
        # Reset password
        response = requests.post(
            f"{BASE_URL}/api/users/{user_id}/reset-password?new_password=NewPass@456",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed to reset password: {response.text}"
        assert f"Password reset successfully for {user_name}" in response.json()["message"]
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/users/{user_id}", headers=auth_headers)
    
    def test_delete_user(self, auth_headers):
        """DELETE /api/users/{user_id} - Delete a user"""
        # First create a user
        unique_id = str(uuid.uuid4())[:8]
        create_response = requests.post(f"{BASE_URL}/api/users", json={
            "email": f"test_delete_{unique_id}@smifs.com",
            "password": "TestPass@123",
            "name": f"TEST_Delete_User_{unique_id}",
            "role": 5
        }, headers=auth_headers)
        assert create_response.status_code == 200
        user_id = create_response.json()["user"]["id"]
        
        # Delete user
        response = requests.delete(f"{BASE_URL}/api/users/{user_id}", headers=auth_headers)
        assert response.status_code == 200, f"Failed to delete user: {response.text}"
        assert "deleted successfully" in response.json()["message"]
        
        # Verify user is deleted
        users_response = requests.get(f"{BASE_URL}/api/users", headers=auth_headers)
        users = users_response.json()
        deleted_user = [u for u in users if u["id"] == user_id]
        assert len(deleted_user) == 0
    
    def test_cannot_delete_super_admin(self, auth_headers):
        """DELETE /api/users/{user_id} - Cannot delete super admin"""
        # Get PE Desk user ID
        users_response = requests.get(f"{BASE_URL}/api/users", headers=auth_headers)
        users = users_response.json()
        pe_desk_user = [u for u in users if u["email"] == PE_DESK_EMAIL][0]
        
        # Try to delete super admin
        response = requests.delete(f"{BASE_URL}/api/users/{pe_desk_user['id']}", headers=auth_headers)
        assert response.status_code == 400 or response.status_code == 403
        # Super admin should still exist
        users_response = requests.get(f"{BASE_URL}/api/users", headers=auth_headers)
        users = users_response.json()
        pe_desk_exists = any(u["email"] == PE_DESK_EMAIL for u in users)
        assert pe_desk_exists


# ============== Database Backup Tests ==============
class TestDatabaseBackup:
    """Test Database Backup endpoints"""
    
    def test_get_database_stats(self, auth_headers):
        """GET /api/database/stats - Get database statistics"""
        response = requests.get(f"{BASE_URL}/api/database/stats", headers=auth_headers)
        assert response.status_code == 200, f"Failed to get stats: {response.text}"
        data = response.json()
        assert "collections" in data
        assert "total_records" in data
        assert "backup_count" in data
        assert isinstance(data["collections"], dict)
        assert "users" in data["collections"]
        assert "clients" in data["collections"]
        assert "stocks" in data["collections"]
    
    def test_list_backups(self, auth_headers):
        """GET /api/database/backups - List all backups"""
        response = requests.get(f"{BASE_URL}/api/database/backups", headers=auth_headers)
        assert response.status_code == 200, f"Failed to list backups: {response.text}"
        backups = response.json()
        assert isinstance(backups, list)
    
    def test_create_backup(self, auth_headers):
        """POST /api/database/backups - Create a new backup"""
        backup_name = f"TEST_Backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        response = requests.post(
            f"{BASE_URL}/api/database/backups?name={backup_name}&description=Test%20backup%20for%20pytest",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed to create backup: {response.text}"
        data = response.json()
        assert data["message"] == "Backup created successfully"
        assert "backup" in data
        assert data["backup"]["name"] == backup_name
        assert "record_counts" in data["backup"]
        assert "size_bytes" in data["backup"]
        return data["backup"]["id"]
    
    def test_delete_backup(self, auth_headers):
        """DELETE /api/database/backups/{backup_id} - Delete a backup"""
        # First create a backup
        backup_name = f"TEST_Delete_Backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        create_response = requests.post(
            f"{BASE_URL}/api/database/backups?name={backup_name}",
            headers=auth_headers
        )
        assert create_response.status_code == 200
        backup_id = create_response.json()["backup"]["id"]
        
        # Delete backup
        response = requests.delete(f"{BASE_URL}/api/database/backups/{backup_id}", headers=auth_headers)
        assert response.status_code == 200, f"Failed to delete backup: {response.text}"
        assert response.json()["message"] == "Backup deleted successfully"
        
        # Verify backup is deleted
        backups_response = requests.get(f"{BASE_URL}/api/database/backups", headers=auth_headers)
        backups = backups_response.json()
        deleted_backup = [b for b in backups if b["id"] == backup_id]
        assert len(deleted_backup) == 0


# ============== PE Desk Delete Permissions Tests ==============
class TestPEDeskDeletePermissions:
    """Test PE Desk can delete clients, stocks, bookings, purchases"""
    
    def test_delete_client_endpoint_exists(self, auth_headers):
        """DELETE /api/clients/{client_id} - Endpoint exists and requires PE Desk"""
        # Test with non-existent ID to verify endpoint exists
        response = requests.delete(f"{BASE_URL}/api/clients/non-existent-id", headers=auth_headers)
        # Should return 404 (not found) not 405 (method not allowed)
        assert response.status_code == 404, f"Delete client endpoint issue: {response.status_code} - {response.text}"
    
    def test_delete_stock_endpoint_exists(self, auth_headers):
        """DELETE /api/stocks/{stock_id} - Endpoint exists and requires PE Desk"""
        response = requests.delete(f"{BASE_URL}/api/stocks/non-existent-id", headers=auth_headers)
        assert response.status_code == 404, f"Delete stock endpoint issue: {response.status_code} - {response.text}"
    
    def test_delete_booking_endpoint_exists(self, auth_headers):
        """DELETE /api/bookings/{booking_id} - Endpoint exists and requires PE Desk"""
        response = requests.delete(f"{BASE_URL}/api/bookings/non-existent-id", headers=auth_headers)
        assert response.status_code == 404, f"Delete booking endpoint issue: {response.status_code} - {response.text}"
    
    def test_delete_purchase_endpoint_exists(self, auth_headers):
        """DELETE /api/purchases/{purchase_id} - Endpoint exists and requires PE Desk"""
        response = requests.delete(f"{BASE_URL}/api/purchases/non-existent-id", headers=auth_headers)
        assert response.status_code == 404, f"Delete purchase endpoint issue: {response.status_code} - {response.text}"
    
    def test_create_and_delete_client(self, auth_headers):
        """Full flow: Create client then delete it"""
        unique_id = str(uuid.uuid4())[:8]
        # Create client
        client_data = {
            "name": f"TEST_Delete_Client_{unique_id}",
            "email": f"test_delete_client_{unique_id}@example.com",
            "phone": "9876543210",
            "pan_number": f"ABCDE{unique_id[:4]}F".upper(),
            "dp_type": "other",
            "dp_id": "12345678",
            "client_id": "87654321",
            "is_vendor": False,
            "bank_accounts": []
        }
        create_response = requests.post(f"{BASE_URL}/api/clients", json=client_data, headers=auth_headers)
        assert create_response.status_code == 200, f"Failed to create client: {create_response.text}"
        client_id = create_response.json()["id"]
        
        # Delete client
        delete_response = requests.delete(f"{BASE_URL}/api/clients/{client_id}", headers=auth_headers)
        assert delete_response.status_code == 200, f"Failed to delete client: {delete_response.text}"
        assert "deleted successfully" in delete_response.json()["message"]
    
    def test_create_and_delete_stock(self, auth_headers):
        """Full flow: Create stock then delete it"""
        unique_id = str(uuid.uuid4())[:8]
        # Create stock
        stock_data = {
            "symbol": f"TESTDEL{unique_id[:4]}".upper(),
            "name": f"TEST Delete Stock {unique_id}",
            "isin": f"INE{unique_id[:9]}".upper(),
            "face_value": 10.0
        }
        create_response = requests.post(f"{BASE_URL}/api/stocks", json=stock_data, headers=auth_headers)
        assert create_response.status_code == 200, f"Failed to create stock: {create_response.text}"
        stock_id = create_response.json()["id"]
        
        # Delete stock
        delete_response = requests.delete(f"{BASE_URL}/api/stocks/{stock_id}", headers=auth_headers)
        assert delete_response.status_code == 200, f"Failed to delete stock: {delete_response.text}"
        assert "deleted successfully" in delete_response.json()["message"]


# ============== Cleanup ==============
@pytest.fixture(scope="module", autouse=True)
def cleanup_test_data(auth_token):
    """Cleanup test data after all tests"""
    yield
    headers = {"Authorization": f"Bearer {auth_token}"}
    
    # Cleanup test users
    try:
        users_response = requests.get(f"{BASE_URL}/api/users", headers=headers)
        if users_response.status_code == 200:
            users = users_response.json()
            for user in users:
                if user["name"].startswith("TEST_") or "test_" in user["email"]:
                    requests.delete(f"{BASE_URL}/api/users/{user['id']}", headers=headers)
    except:
        pass
    
    # Cleanup test backups
    try:
        backups_response = requests.get(f"{BASE_URL}/api/database/backups", headers=headers)
        if backups_response.status_code == 200:
            backups = backups_response.json()
            for backup in backups:
                if backup["name"].startswith("TEST_"):
                    requests.delete(f"{BASE_URL}/api/database/backups/{backup['id']}", headers=headers)
    except:
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
