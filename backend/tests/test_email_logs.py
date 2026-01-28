"""
Test Email Logs Feature - Email Audit Logging System
Tests for:
- GET /api/email-logs - List email logs with filters
- GET /api/email-logs/stats - Get email statistics
- GET /api/email-logs/{log_id} - Get single email log detail
- GET /api/email-logs/by-entity/{entity_type}/{entity_id} - Get emails by related entity
- DELETE /api/email-logs/cleanup - Cleanup old logs (PE Desk only)
"""
import pytest
import requests
import os
import uuid
from datetime import datetime, timezone

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
PE_DESK_EMAIL = "pedesk@smifs.com"
PE_DESK_PASSWORD = "Kutta@123"


@pytest.fixture(scope="module")
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="module")
def pe_desk_token(api_client):
    """Get PE Desk authentication token"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": PE_DESK_EMAIL,
        "password": PE_DESK_PASSWORD
    })
    assert response.status_code == 200, f"PE Desk login failed: {response.text}"
    data = response.json()
    assert "token" in data, "No token in login response"
    return data["token"]


@pytest.fixture(scope="module")
def authenticated_client(api_client, pe_desk_token):
    """Session with PE Desk auth header"""
    api_client.headers.update({"Authorization": f"Bearer {pe_desk_token}"})
    return api_client


class TestEmailLogsEndpoints:
    """Test Email Logs API Endpoints"""
    
    def test_01_get_email_logs_empty_or_with_data(self, authenticated_client):
        """GET /api/email-logs - Should return logs list (may be empty)"""
        response = authenticated_client.get(f"{BASE_URL}/api/email-logs?limit=50&skip=0")
        
        assert response.status_code == 200, f"Failed to get email logs: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "total" in data, "Response missing 'total' field"
        assert "logs" in data, "Response missing 'logs' field"
        assert "limit" in data, "Response missing 'limit' field"
        assert "skip" in data, "Response missing 'skip' field"
        
        # Verify types
        assert isinstance(data["total"], int), "total should be integer"
        assert isinstance(data["logs"], list), "logs should be list"
        assert data["limit"] == 50, "limit should be 50"
        assert data["skip"] == 0, "skip should be 0"
        
        print(f"✓ Email logs endpoint working - Total: {data['total']}, Returned: {len(data['logs'])}")
    
    def test_02_get_email_logs_with_status_filter(self, authenticated_client):
        """GET /api/email-logs?status=sent - Filter by status"""
        response = authenticated_client.get(f"{BASE_URL}/api/email-logs?status=sent&limit=10")
        
        assert response.status_code == 200, f"Failed with status filter: {response.text}"
        data = response.json()
        
        assert "logs" in data
        # If there are logs, verify they all have status=sent
        for log in data["logs"]:
            assert log.get("status") == "sent", f"Log has wrong status: {log.get('status')}"
        
        print(f"✓ Status filter working - Found {len(data['logs'])} sent emails")
    
    def test_03_get_email_logs_with_entity_type_filter(self, authenticated_client):
        """GET /api/email-logs?related_entity_type=booking - Filter by entity type"""
        response = authenticated_client.get(f"{BASE_URL}/api/email-logs?related_entity_type=booking&limit=10")
        
        assert response.status_code == 200, f"Failed with entity type filter: {response.text}"
        data = response.json()
        
        assert "logs" in data
        # If there are logs, verify they all have related_entity_type=booking
        for log in data["logs"]:
            assert log.get("related_entity_type") == "booking", f"Log has wrong entity type: {log.get('related_entity_type')}"
        
        print(f"✓ Entity type filter working - Found {len(data['logs'])} booking-related emails")
    
    def test_04_get_email_logs_with_email_filter(self, authenticated_client):
        """GET /api/email-logs?to_email=test - Filter by recipient email"""
        response = authenticated_client.get(f"{BASE_URL}/api/email-logs?to_email=test&limit=10")
        
        assert response.status_code == 200, f"Failed with email filter: {response.text}"
        data = response.json()
        
        assert "logs" in data
        print(f"✓ Email filter working - Found {len(data['logs'])} emails matching 'test'")
    
    def test_05_get_email_logs_with_date_range(self, authenticated_client):
        """GET /api/email-logs with date range filter"""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        response = authenticated_client.get(f"{BASE_URL}/api/email-logs?start_date={today}&end_date={today}&limit=10")
        
        assert response.status_code == 200, f"Failed with date filter: {response.text}"
        data = response.json()
        
        assert "logs" in data
        print(f"✓ Date range filter working - Found {len(data['logs'])} emails for today")
    
    def test_06_get_email_stats(self, authenticated_client):
        """GET /api/email-logs/stats - Get email statistics"""
        response = authenticated_client.get(f"{BASE_URL}/api/email-logs/stats?days=30")
        
        assert response.status_code == 200, f"Failed to get email stats: {response.text}"
        data = response.json()
        
        # Verify response structure matches EmailLogStats model
        assert "total_sent" in data, "Response missing 'total_sent'"
        assert "total_failed" in data, "Response missing 'total_failed'"
        assert "total_skipped" in data, "Response missing 'total_skipped'"
        assert "by_template" in data, "Response missing 'by_template'"
        assert "by_status" in data, "Response missing 'by_status'"
        assert "by_entity_type" in data, "Response missing 'by_entity_type'"
        assert "recent_failures" in data, "Response missing 'recent_failures'"
        
        # Verify types
        assert isinstance(data["total_sent"], int), "total_sent should be integer"
        assert isinstance(data["total_failed"], int), "total_failed should be integer"
        assert isinstance(data["total_skipped"], int), "total_skipped should be integer"
        assert isinstance(data["by_template"], dict), "by_template should be dict"
        assert isinstance(data["by_status"], dict), "by_status should be dict"
        assert isinstance(data["by_entity_type"], dict), "by_entity_type should be dict"
        assert isinstance(data["recent_failures"], list), "recent_failures should be list"
        
        print(f"✓ Email stats endpoint working - Sent: {data['total_sent']}, Failed: {data['total_failed']}, Skipped: {data['total_skipped']}")
    
    def test_07_get_email_stats_different_days(self, authenticated_client):
        """GET /api/email-logs/stats?days=7 - Stats for different time periods"""
        response = authenticated_client.get(f"{BASE_URL}/api/email-logs/stats?days=7")
        
        assert response.status_code == 200, f"Failed to get 7-day stats: {response.text}"
        data = response.json()
        
        assert "total_sent" in data
        print(f"✓ 7-day stats working - Sent: {data['total_sent']}")
    
    def test_08_get_email_log_detail_not_found(self, authenticated_client):
        """GET /api/email-logs/{log_id} - Non-existent log should return 404"""
        fake_id = str(uuid.uuid4())
        response = authenticated_client.get(f"{BASE_URL}/api/email-logs/{fake_id}")
        
        assert response.status_code == 404, f"Expected 404 for non-existent log, got {response.status_code}"
        print("✓ Non-existent log correctly returns 404")
    
    def test_09_get_emails_by_entity(self, authenticated_client):
        """GET /api/email-logs/by-entity/{entity_type}/{entity_id} - Get emails by entity"""
        fake_entity_id = str(uuid.uuid4())
        response = authenticated_client.get(f"{BASE_URL}/api/email-logs/by-entity/booking/{fake_entity_id}")
        
        assert response.status_code == 200, f"Failed to get emails by entity: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "entity_type" in data, "Response missing 'entity_type'"
        assert "entity_id" in data, "Response missing 'entity_id'"
        assert "total" in data, "Response missing 'total'"
        assert "logs" in data, "Response missing 'logs'"
        
        assert data["entity_type"] == "booking"
        assert data["entity_id"] == fake_entity_id
        assert isinstance(data["logs"], list)
        
        print(f"✓ Get emails by entity working - Found {data['total']} emails for entity")
    
    def test_10_cleanup_endpoint_pe_desk_only(self, authenticated_client):
        """DELETE /api/email-logs/cleanup - Should work for PE Desk"""
        # Note: This will actually delete old logs if any exist
        # Using days_to_keep=365 to minimize impact
        response = authenticated_client.delete(f"{BASE_URL}/api/email-logs/cleanup?days_to_keep=365")
        
        assert response.status_code == 200, f"Cleanup failed: {response.text}"
        data = response.json()
        
        assert "message" in data, "Response missing 'message'"
        assert "deleted_count" in data, "Response missing 'deleted_count'"
        assert isinstance(data["deleted_count"], int), "deleted_count should be integer"
        
        print(f"✓ Cleanup endpoint working - Deleted {data['deleted_count']} old logs")
    
    def test_11_get_email_logs_pagination(self, authenticated_client):
        """Test pagination parameters"""
        response = authenticated_client.get(f"{BASE_URL}/api/email-logs?limit=5&skip=0")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["limit"] == 5
        assert data["skip"] == 0
        
        # Test with skip
        response2 = authenticated_client.get(f"{BASE_URL}/api/email-logs?limit=5&skip=5")
        assert response2.status_code == 200
        data2 = response2.json()
        
        assert data2["limit"] == 5
        assert data2["skip"] == 5
        
        print("✓ Pagination working correctly")


class TestEmailLogsAccessControl:
    """Test access control for email logs endpoints"""
    
    def test_01_unauthenticated_access_denied(self, api_client):
        """Unauthenticated requests should be denied"""
        # Remove auth header if present
        headers = {"Content-Type": "application/json"}
        
        response = requests.get(f"{BASE_URL}/api/email-logs", headers=headers)
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        
        print("✓ Unauthenticated access correctly denied")


class TestEmailLogDataStructure:
    """Test email log data structure when logs exist"""
    
    def test_01_verify_log_structure_if_exists(self, authenticated_client):
        """Verify log entry structure if any logs exist"""
        response = authenticated_client.get(f"{BASE_URL}/api/email-logs?limit=1")
        
        assert response.status_code == 200
        data = response.json()
        
        if len(data["logs"]) > 0:
            log = data["logs"][0]
            
            # Required fields
            assert "id" in log, "Log missing 'id'"
            assert "to_email" in log, "Log missing 'to_email'"
            assert "subject" in log, "Log missing 'subject'"
            assert "status" in log, "Log missing 'status'"
            assert "created_at" in log, "Log missing 'created_at'"
            
            # Status should be one of valid values
            assert log["status"] in ["sent", "failed", "skipped"], f"Invalid status: {log['status']}"
            
            print(f"✓ Log structure verified - ID: {log['id']}, Status: {log['status']}")
        else:
            print("✓ No logs exist yet - structure verification skipped")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
