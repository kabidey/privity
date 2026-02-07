"""
Backend API Tests for Login/Notification Features
Tests for:
- Health endpoint
- Email templates verify endpoint
- Basic auth flow
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://login-ui-revamp-5.preview.emergentagent.com')
BASE_URL = BASE_URL.rstrip('/')


class TestHealthEndpoint:
    """Health endpoint tests"""
    
    def test_health_returns_ok(self):
        """Health endpoint should return ok status"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "ok"
        assert "timestamp" in data
        assert "version" in data


class TestAuthFlow:
    """Authentication flow tests"""
    
    def test_login_with_valid_credentials(self):
        """Should login with valid PE Desk credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "pedesk@smifs.com",
            "password": "password"
        })
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert "user" in data
        assert data["user"]["email"] == "pedesk@smifs.com"
    
    def test_login_with_invalid_credentials(self):
        """Should reject invalid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "invalid@smifs.com",
            "password": "wrongpassword"
        })
        assert response.status_code == 401 or response.status_code == 400


class TestEmailTemplatesVerify:
    """Email templates verify endpoint tests"""
    
    @pytest.fixture
    def auth_token(self):
        """Get auth token for PE Desk user"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "pedesk@smifs.com",
            "password": "password"
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Unable to authenticate")
    
    def test_verify_requires_auth(self):
        """Email templates verify should require authentication"""
        response = requests.get(f"{BASE_URL}/api/email-templates/verify")
        assert response.status_code == 401 or response.status_code == 403
    
    def test_verify_with_auth(self, auth_token):
        """Email templates verify should work with valid auth"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/email-templates/verify", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "total_templates" in data
        assert "templates_with_issues" in data


class TestNotificationsEndpoint:
    """Notifications endpoint tests"""
    
    @pytest.fixture
    def auth_token(self):
        """Get auth token for PE Desk user"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "pedesk@smifs.com",
            "password": "password"
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Unable to authenticate")
    
    def test_get_notifications_requires_auth(self):
        """Notifications endpoint should require authentication"""
        response = requests.get(f"{BASE_URL}/api/notifications")
        assert response.status_code == 401 or response.status_code == 403
    
    def test_get_notifications_with_auth(self, auth_token):
        """Should get notifications list with valid auth"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/notifications?limit=50", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
