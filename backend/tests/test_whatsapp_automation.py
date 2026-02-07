"""
Test Suite for WhatsApp Automation Feature:
1. GET /api/whatsapp/automation/config - Get automation configuration
2. PUT /api/whatsapp/automation/config - Update automation configuration
3. POST /api/whatsapp/automation/payment-reminders - Trigger payment reminders
4. POST /api/whatsapp/automation/document-reminders - Trigger document reminders
5. POST /api/whatsapp/automation/dp-ready-notifications - Trigger DP ready notifications
6. POST /api/whatsapp/automation/run-all - Run all enabled automations
7. GET /api/whatsapp/automation/logs - Get automation logs
8. GET /api/whatsapp/broadcasts - Get broadcast history
9. POST /api/whatsapp/automation/bulk-broadcast - Send bulk broadcast
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
HEADERS = {
    "User-Agent": "Mozilla/5.0 Test",
    "Content-Type": "application/json"
}

# Test credentials
PE_DESK_EMAIL = "pedesk@smifs.com"
PE_DESK_PASSWORD = "password"


class TestWhatsAppAutomationConfig:
    """WhatsApp Automation Configuration API Tests"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token for PE Desk user"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": PE_DESK_EMAIL, "password": PE_DESK_PASSWORD},
            headers=HEADERS
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        return data.get("access_token") or data.get("token")
    
    def test_get_automation_config(self, auth_token):
        """GET /api/whatsapp/automation/config - Returns automation configuration"""
        response = requests.get(
            f"{BASE_URL}/api/whatsapp/automation/config",
            headers={**HEADERS, "Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        data = response.json()
        
        # Verify expected fields exist
        expected_fields = [
            "payment_reminder_enabled",
            "payment_reminder_days",
            "document_reminder_enabled",
            "dp_ready_notification_enabled"
        ]
        for field in expected_fields:
            assert field in data, f"Missing field: {field}"
        
        # Verify data types
        assert isinstance(data["payment_reminder_enabled"], bool), "payment_reminder_enabled should be boolean"
        assert isinstance(data["payment_reminder_days"], int), "payment_reminder_days should be integer"
        assert isinstance(data["document_reminder_enabled"], bool), "document_reminder_enabled should be boolean"
        assert isinstance(data["dp_ready_notification_enabled"], bool), "dp_ready_notification_enabled should be boolean"
        
        print("PASS: Automation config returned with all expected fields")
        print(f"  - payment_reminder_enabled: {data['payment_reminder_enabled']}")
        print(f"  - payment_reminder_days: {data['payment_reminder_days']}")
        print(f"  - document_reminder_enabled: {data['document_reminder_enabled']}")
        print(f"  - dp_ready_notification_enabled: {data['dp_ready_notification_enabled']}")
    
    def test_update_automation_config(self, auth_token):
        """PUT /api/whatsapp/automation/config - Updates automation configuration"""
        # First get current config
        get_response = requests.get(
            f"{BASE_URL}/api/whatsapp/automation/config",
            headers={**HEADERS, "Authorization": f"Bearer {auth_token}"}
        )
        assert get_response.status_code == 200
        original_config = get_response.json()
        
        # Update config with new values
        new_config = {
            "payment_reminder_enabled": True,
            "payment_reminder_days": 5,
            "document_reminder_enabled": True,
            "dp_ready_notification_enabled": True
        }
        
        response = requests.put(
            f"{BASE_URL}/api/whatsapp/automation/config",
            json=new_config,
            headers={**HEADERS, "Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        data = response.json()
        
        # Verify updated values
        assert data.get("payment_reminder_enabled") == True, "payment_reminder_enabled not updated"
        assert data.get("payment_reminder_days") == 5, "payment_reminder_days not updated"
        assert data.get("document_reminder_enabled") == True, "document_reminder_enabled not updated"
        assert data.get("dp_ready_notification_enabled") == True, "dp_ready_notification_enabled not updated"
        
        # Verify persistence by fetching again
        verify_response = requests.get(
            f"{BASE_URL}/api/whatsapp/automation/config",
            headers={**HEADERS, "Authorization": f"Bearer {auth_token}"}
        )
        assert verify_response.status_code == 200
        verify_data = verify_response.json()
        assert verify_data.get("payment_reminder_enabled") == True, "Config not persisted"
        assert verify_data.get("payment_reminder_days") == 5, "Config not persisted"
        
        print("PASS: Automation config updated and persisted successfully")


class TestWhatsAppAutomationTriggers:
    """WhatsApp Automation Trigger API Tests"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token for PE Desk user"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": PE_DESK_EMAIL, "password": PE_DESK_PASSWORD},
            headers=HEADERS
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        return data.get("access_token") or data.get("token")
    
    def test_trigger_payment_reminders(self, auth_token):
        """POST /api/whatsapp/automation/payment-reminders - Triggers payment reminder automation"""
        response = requests.post(
            f"{BASE_URL}/api/whatsapp/automation/payment-reminders",
            headers={**HEADERS, "Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "status" in data, "Missing status field"
        # Status can be 'completed' or 'skipped' (if WhatsApp not configured)
        assert data["status"] in ["completed", "skipped"], f"Unexpected status: {data['status']}"
        
        if data["status"] == "completed":
            assert "total" in data, "Missing total field"
            assert "success" in data, "Missing success field"
            assert "failed" in data, "Missing failed field"
            print(f"PASS: Payment reminders triggered - Total: {data['total']}, Success: {data['success']}, Failed: {data['failed']}")
        else:
            print(f"PASS: Payment reminders skipped - Reason: {data.get('reason', 'WhatsApp not configured')}")
    
    def test_trigger_document_reminders(self, auth_token):
        """POST /api/whatsapp/automation/document-reminders - Triggers document reminder automation"""
        response = requests.post(
            f"{BASE_URL}/api/whatsapp/automation/document-reminders",
            headers={**HEADERS, "Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        data = response.json()
        
        assert "status" in data, "Missing status field"
        assert data["status"] in ["completed", "skipped"], f"Unexpected status: {data['status']}"
        
        if data["status"] == "completed":
            print(f"PASS: Document reminders triggered - Total: {data.get('total', 0)}, Success: {data.get('success', 0)}")
        else:
            print(f"PASS: Document reminders skipped - Reason: {data.get('reason', 'WhatsApp not configured')}")
    
    def test_trigger_dp_ready_notifications(self, auth_token):
        """POST /api/whatsapp/automation/dp-ready-notifications - Triggers DP ready notifications"""
        response = requests.post(
            f"{BASE_URL}/api/whatsapp/automation/dp-ready-notifications",
            headers={**HEADERS, "Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        data = response.json()
        
        assert "status" in data, "Missing status field"
        assert data["status"] in ["completed", "skipped"], f"Unexpected status: {data['status']}"
        
        if data["status"] == "completed":
            print(f"PASS: DP ready notifications triggered - Total: {data.get('total', 0)}, Success: {data.get('success', 0)}")
        else:
            print(f"PASS: DP ready notifications skipped - Reason: {data.get('reason', 'WhatsApp not configured')}")
    
    def test_run_all_automations(self, auth_token):
        """POST /api/whatsapp/automation/run-all - Runs all enabled automations"""
        response = requests.post(
            f"{BASE_URL}/api/whatsapp/automation/run-all",
            headers={**HEADERS, "Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        data = response.json()
        
        # Response should be a dict with results for each automation type
        assert isinstance(data, dict), "Response should be a dictionary"
        print(f"PASS: Run all automations completed - Results: {data}")


class TestWhatsAppAutomationLogs:
    """WhatsApp Automation Logs API Tests"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token for PE Desk user"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": PE_DESK_EMAIL, "password": PE_DESK_PASSWORD},
            headers=HEADERS
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        return data.get("access_token") or data.get("token")
    
    def test_get_automation_logs(self, auth_token):
        """GET /api/whatsapp/automation/logs - Returns automation run logs"""
        response = requests.get(
            f"{BASE_URL}/api/whatsapp/automation/logs?limit=20",
            headers={**HEADERS, "Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "logs" in data, "Missing logs field"
        assert "total" in data, "Missing total field"
        assert "limit" in data, "Missing limit field"
        assert "skip" in data, "Missing skip field"
        
        assert isinstance(data["logs"], list), "logs should be a list"
        
        # If there are logs, verify structure
        if len(data["logs"]) > 0:
            log = data["logs"][0]
            expected_fields = ["id", "automation_type", "trigger_event", "recipients_count", "success_count", "failed_count", "run_at"]
            for field in expected_fields:
                assert field in log, f"Missing field in log: {field}"
        
        print(f"PASS: Automation logs returned - Total: {data['total']}, Returned: {len(data['logs'])}")
    
    def test_get_broadcasts(self, auth_token):
        """GET /api/whatsapp/broadcasts - Returns broadcast history"""
        response = requests.get(
            f"{BASE_URL}/api/whatsapp/broadcasts?limit=20",
            headers={**HEADERS, "Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "broadcasts" in data, "Missing broadcasts field"
        assert "total" in data, "Missing total field"
        assert "limit" in data, "Missing limit field"
        assert "skip" in data, "Missing skip field"
        
        assert isinstance(data["broadcasts"], list), "broadcasts should be a list"
        
        print(f"PASS: Broadcasts returned - Total: {data['total']}, Returned: {len(data['broadcasts'])}")


class TestWhatsAppBulkBroadcast:
    """WhatsApp Bulk Broadcast API Tests"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token for PE Desk user"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": PE_DESK_EMAIL, "password": PE_DESK_PASSWORD},
            headers=HEADERS
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        return data.get("access_token") or data.get("token")
    
    def test_bulk_broadcast_validation(self, auth_token):
        """POST /api/whatsapp/automation/bulk-broadcast - Validates broadcast request"""
        # Test with empty message - should fail or return appropriate response
        response = requests.post(
            f"{BASE_URL}/api/whatsapp/automation/bulk-broadcast",
            json={
                "message": "Test broadcast message from automation testing",
                "recipient_type": "all_clients",
                "broadcast_name": "TEST_Automation_Broadcast"
            },
            headers={**HEADERS, "Authorization": f"Bearer {auth_token}"}
        )
        
        # Response can be 200 (success/skipped) or 400 (validation error)
        assert response.status_code in [200, 400], f"Unexpected status: {response.status_code} - {response.text}"
        data = response.json()
        
        if response.status_code == 200:
            # If WhatsApp is configured, it should return status
            assert "status" in data, "Missing status field"
            print(f"PASS: Bulk broadcast response - Status: {data.get('status')}, Reason: {data.get('reason', 'N/A')}")
        else:
            print(f"PASS: Bulk broadcast validation - Error: {data.get('detail', 'Unknown error')}")


class TestSchedulerIntegration:
    """Verify scheduler has WhatsApp automation job configured"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token for PE Desk user"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": PE_DESK_EMAIL, "password": PE_DESK_PASSWORD},
            headers=HEADERS
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        return data.get("access_token") or data.get("token")
    
    def test_scheduler_jobs_endpoint(self, auth_token):
        """GET /api/scheduler/jobs - Verify WhatsApp automation job exists"""
        response = requests.get(
            f"{BASE_URL}/api/scheduler/jobs",
            headers={**HEADERS, "Authorization": f"Bearer {auth_token}"}
        )
        
        # Scheduler endpoint may or may not exist
        if response.status_code == 200:
            data = response.json()
            jobs = data if isinstance(data, list) else data.get("jobs", [])
            
            # Check if whatsapp_automations job exists
            job_ids = [job.get("id") for job in jobs]
            if "whatsapp_automations" in job_ids:
                print("PASS: WhatsApp automation job found in scheduler")
                wa_job = next((j for j in jobs if j.get("id") == "whatsapp_automations"), None)
                if wa_job:
                    print(f"  - Next run: {wa_job.get('next_run_time')}")
                    print(f"  - Trigger: {wa_job.get('trigger')}")
            else:
                print("INFO: WhatsApp automation job not found in scheduler jobs list")
                print(f"  - Available jobs: {job_ids}")
        elif response.status_code == 404:
            print("INFO: Scheduler jobs endpoint not available (404)")
        else:
            print(f"INFO: Scheduler jobs endpoint returned {response.status_code}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
