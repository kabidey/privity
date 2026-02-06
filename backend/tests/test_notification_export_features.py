"""
Test suite for Notification Dashboard, Wati Webhook, and Export Features
Tests: 
- Wati webhook endpoint POST /api/whatsapp/webhook
- Delivery stats GET /api/whatsapp/delivery-stats  
- Clients export GET /api/clients-export
- Inventory export GET /api/inventory/export
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_EMAIL = "pedesk@smifs.com"
TEST_PASSWORD = "password"


class TestAuthentication:
    """Get auth token for protected endpoints"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert response.status_code == 200, f"Auth failed: {response.text}"
        data = response.json()
        return data.get("access_token") or data.get("token")
    
    @pytest.fixture(scope="class")
    def auth_headers(self, auth_token):
        return {"Authorization": f"Bearer {auth_token}"}


class TestWatiWebhook(TestAuthentication):
    """Test Wati.io webhook endpoint for delivery status"""
    
    def test_webhook_accepts_delivery_status(self):
        """Test POST /api/whatsapp/webhook accepts delivery status payload"""
        # Webhook endpoint is public (no auth required)
        payload = {
            "eventType": "message_status",
            "waId": "919876543210",
            "id": "test-message-123",
            "status": "delivered",
            "timestamp": "2026-01-15T10:30:00Z"
        }
        
        response = requests.post(f"{BASE_URL}/api/whatsapp/webhook", json=payload)
        assert response.status_code == 200, f"Webhook failed: {response.text}"
        
        data = response.json()
        assert data.get("status") == "ok"
        assert "event_id" in data
        print(f"Webhook delivery status accepted: event_id={data.get('event_id')}")
    
    def test_webhook_accepts_incoming_message(self):
        """Test POST /api/whatsapp/webhook accepts incoming message"""
        payload = {
            "eventType": "message_received",
            "waId": "919876543210",
            "id": "incoming-msg-456",
            "text": "Test incoming message",
            "type": "text",
            "timestamp": "2026-01-15T10:35:00Z"
        }
        
        response = requests.post(f"{BASE_URL}/api/whatsapp/webhook", json=payload)
        assert response.status_code == 200, f"Webhook failed: {response.text}"
        
        data = response.json()
        assert data.get("status") == "ok"
        print(f"Webhook incoming message accepted: event_id={data.get('event_id')}")
    
    def test_webhook_accepts_failed_status(self):
        """Test POST /api/whatsapp/webhook accepts failed status"""
        payload = {
            "eventType": "message_failed",
            "waId": "919876543210",
            "id": "failed-msg-789",
            "status": "failed",
            "timestamp": "2026-01-15T10:40:00Z"
        }
        
        response = requests.post(f"{BASE_URL}/api/whatsapp/webhook", json=payload)
        assert response.status_code == 200, f"Webhook failed: {response.text}"
        
        data = response.json()
        assert data.get("status") == "ok"
        print(f"Webhook failed status accepted: event_id={data.get('event_id')}")
    
    def test_webhook_handles_malformed_payload(self):
        """Test webhook handles malformed payload gracefully"""
        payload = {
            "unknown_field": "test"
        }
        
        response = requests.post(f"{BASE_URL}/api/whatsapp/webhook", json=payload)
        # Should still return 200 to prevent retries
        assert response.status_code == 200
        print("Webhook handles malformed payload gracefully")


class TestDeliveryStats(TestAuthentication):
    """Test delivery stats endpoint"""
    
    def test_delivery_stats_returns_data(self, auth_headers):
        """Test GET /api/whatsapp/delivery-stats returns stats"""
        response = requests.get(f"{BASE_URL}/api/whatsapp/delivery-stats?days=7", headers=auth_headers)
        assert response.status_code == 200, f"Delivery stats failed: {response.text}"
        
        data = response.json()
        # Verify expected fields
        assert "period_days" in data
        assert "total_sent" in data
        assert "delivered" in data
        assert "read" in data
        assert "failed" in data
        assert "delivery_rate" in data
        assert "read_rate" in data
        
        print(f"Delivery stats: total_sent={data.get('total_sent')}, delivery_rate={data.get('delivery_rate')}%")
    
    def test_delivery_stats_respects_days_param(self, auth_headers):
        """Test delivery stats uses days parameter"""
        response = requests.get(f"{BASE_URL}/api/whatsapp/delivery-stats?days=30", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("period_days") == 30
        print(f"Delivery stats with 30 days: total_sent={data.get('total_sent')}")


class TestNotificationEndpoints(TestAuthentication):
    """Test notification-related endpoints"""
    
    def test_get_notifications(self, auth_headers):
        """Test GET /api/notifications returns notifications"""
        response = requests.get(f"{BASE_URL}/api/notifications?limit=50", headers=auth_headers)
        assert response.status_code == 200, f"Get notifications failed: {response.text}"
        
        # Response should be a list
        data = response.json()
        assert isinstance(data, list)
        print(f"Found {len(data)} notifications")
    
    def test_mark_all_notifications_read(self, auth_headers):
        """Test PUT /api/notifications/read-all"""
        response = requests.put(f"{BASE_URL}/api/notifications/read-all", headers=auth_headers)
        assert response.status_code == 200, f"Mark all read failed: {response.text}"
        print("Mark all notifications as read: success")


class TestClientsExport(TestAuthentication):
    """Test clients export functionality"""
    
    def test_export_clients_xlsx(self, auth_headers):
        """Test GET /api/clients-export?format=xlsx"""
        response = requests.get(
            f"{BASE_URL}/api/clients-export?format=xlsx&is_vendor=false",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Export XLSX failed: {response.text}"
        
        # Verify content type
        content_type = response.headers.get("Content-Type", "")
        assert "spreadsheetml" in content_type or "octet-stream" in content_type, f"Wrong content type: {content_type}"
        
        # Verify content disposition
        disposition = response.headers.get("Content-Disposition", "")
        assert "clients_export.xlsx" in disposition, f"Wrong filename: {disposition}"
        
        # Verify we got binary content
        assert len(response.content) > 0
        print(f"Clients XLSX export: {len(response.content)} bytes")
    
    def test_export_clients_csv(self, auth_headers):
        """Test GET /api/clients-export?format=csv"""
        response = requests.get(
            f"{BASE_URL}/api/clients-export?format=csv&is_vendor=false",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Export CSV failed: {response.text}"
        
        # Verify content type
        content_type = response.headers.get("Content-Type", "")
        assert "text/csv" in content_type or "octet-stream" in content_type, f"Wrong content type: {content_type}"
        
        # Verify content disposition
        disposition = response.headers.get("Content-Disposition", "")
        assert "clients_export.csv" in disposition, f"Wrong filename: {disposition}"
        
        # Verify we got content
        assert len(response.content) > 0
        
        # Verify CSV has expected headers
        content = response.content.decode('utf-8')
        assert "OTC UCC" in content
        assert "Name" in content
        assert "PAN Number" in content
        print(f"Clients CSV export: {len(content.split(chr(10)))} rows")
    
    def test_export_vendors_xlsx(self, auth_headers):
        """Test exporting vendors (is_vendor=true)"""
        response = requests.get(
            f"{BASE_URL}/api/clients-export?format=xlsx&is_vendor=true",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Export vendors failed: {response.text}"
        print(f"Vendors XLSX export: {len(response.content)} bytes")


class TestInventoryExport(TestAuthentication):
    """Test inventory export functionality"""
    
    def test_export_inventory_xlsx(self, auth_headers):
        """Test GET /api/inventory/export?format=xlsx"""
        response = requests.get(
            f"{BASE_URL}/api/inventory/export?format=xlsx",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Export XLSX failed: {response.text}"
        
        # Verify content type
        content_type = response.headers.get("Content-Type", "")
        assert "spreadsheetml" in content_type or "octet-stream" in content_type, f"Wrong content type: {content_type}"
        
        # Verify content disposition
        disposition = response.headers.get("Content-Disposition", "")
        assert "inventory_export.xlsx" in disposition, f"Wrong filename: {disposition}"
        
        # Verify we got binary content
        assert len(response.content) > 0
        print(f"Inventory XLSX export: {len(response.content)} bytes")
    
    def test_export_inventory_csv(self, auth_headers):
        """Test GET /api/inventory/export?format=csv"""
        response = requests.get(
            f"{BASE_URL}/api/inventory/export?format=csv",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Export CSV failed: {response.text}"
        
        # Verify content type
        content_type = response.headers.get("Content-Type", "")
        assert "text/csv" in content_type or "octet-stream" in content_type, f"Wrong content type: {content_type}"
        
        # Verify content disposition
        disposition = response.headers.get("Content-Disposition", "")
        assert "inventory_export.csv" in disposition, f"Wrong filename: {disposition}"
        
        # Verify we got content
        assert len(response.content) > 0
        
        # Verify CSV has expected headers
        content = response.content.decode('utf-8')
        assert "Stock Symbol" in content
        assert "Stock Name" in content
        assert "Available Qty" in content
        print(f"Inventory CSV export: {len(content.split(chr(10)))} rows")


class TestWebhookEventsEndpoint(TestAuthentication):
    """Test webhook events listing endpoint"""
    
    def test_get_webhook_events(self, auth_headers):
        """Test GET /api/whatsapp/webhook/events"""
        response = requests.get(
            f"{BASE_URL}/api/whatsapp/webhook/events?limit=50",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Get webhook events failed: {response.text}"
        
        data = response.json()
        assert "events" in data
        assert "total" in data
        print(f"Webhook events: {data.get('total')} total")


class TestIncomingMessages(TestAuthentication):
    """Test incoming messages endpoint"""
    
    def test_get_incoming_messages(self, auth_headers):
        """Test GET /api/whatsapp/incoming-messages"""
        response = requests.get(
            f"{BASE_URL}/api/whatsapp/incoming-messages?limit=50",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Get incoming messages failed: {response.text}"
        
        data = response.json()
        assert "messages" in data
        assert "total" in data
        print(f"Incoming messages: {data.get('total')} total, {data.get('unread_count')} unread")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
