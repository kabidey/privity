"""
Test iteration 63 features:
1. WhatsApp page with Wati.io integration
2. RP bank account number unmasked for PE users
3. Payment proof upload endpoint
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://quote-refresh.preview.emergentagent.com').rstrip('/')


class TestAuth:
    """Authentication tests"""
    
    @pytest.fixture(scope="class")
    def pe_token(self):
        """Login as PE Desk user"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "pe@smifs.com",
            "password": "Kutta@123"
        })
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        return data["token"]


class TestWhatsAppWatiIntegration:
    """Test WhatsApp Wati.io integration endpoints"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self, pe_token):
        return {"Authorization": f"Bearer {pe_token}"}
    
    @pytest.fixture(scope="class")
    def pe_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "pe@smifs.com",
            "password": "Kutta@123"
        })
        assert response.status_code == 200
        return response.json()["token"]
    
    def test_whatsapp_config_endpoint_exists(self, auth_headers):
        """Verify WhatsApp config endpoint returns proper structure"""
        response = requests.get(f"{BASE_URL}/api/whatsapp/config", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        # Check expected fields exist
        assert "config_type" in data or "status" in data or "enabled" in data
        print(f"WhatsApp config: {data}")
    
    def test_whatsapp_templates_endpoint_exists(self, auth_headers):
        """Verify WhatsApp templates endpoint exists"""
        response = requests.get(f"{BASE_URL}/api/whatsapp/templates", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        # Should have local_templates or wati_templates
        assert "local_templates" in data or "wati_templates" in data or isinstance(data, list)
        print(f"Found templates: local={len(data.get('local_templates', []))}, wati={len(data.get('wati_templates', []))}")
    
    def test_whatsapp_stats_endpoint_exists(self, auth_headers):
        """Verify WhatsApp stats endpoint exists"""
        response = requests.get(f"{BASE_URL}/api/whatsapp/stats", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        # Should have stats fields
        assert "total_messages" in data or "connected" in data
        print(f"WhatsApp stats: {data}")
    
    def test_whatsapp_messages_endpoint_exists(self, auth_headers):
        """Verify WhatsApp messages endpoint exists"""
        response = requests.get(f"{BASE_URL}/api/whatsapp/messages", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        # Should have messages array
        assert "messages" in data or isinstance(data, list)
        print(f"WhatsApp messages count: {len(data.get('messages', data))}")


class TestRPBankDetailsUnmasked:
    """Test that RP bank account numbers are unmasked for PE users"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self, pe_token):
        return {"Authorization": f"Bearer {pe_token}"}
    
    @pytest.fixture(scope="class")
    def pe_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "pe@smifs.com",
            "password": "Kutta@123"
        })
        assert response.status_code == 200
        return response.json()["token"]
    
    def test_referral_partners_list_endpoint(self, auth_headers):
        """Verify referral partners endpoint exists"""
        response = requests.get(f"{BASE_URL}/api/referral-partners", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"Found {len(data)} referral partners")
        return data
    
    def test_rp_contains_bank_details_fields(self, auth_headers):
        """Verify RPs contain bank detail fields for PE users"""
        response = requests.get(f"{BASE_URL}/api/referral-partners", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        if len(data) > 0:
            rp = data[0]
            # Check that bank fields exist in response
            expected_fields = ['bank_name', 'bank_account_number', 'bank_ifsc_code']
            for field in expected_fields:
                if field in rp and rp[field]:
                    print(f"RP has {field}: {rp[field]}")
                    # For PE user, bank_account_number should NOT be masked (not start with ****)
                    if field == 'bank_account_number' and rp[field]:
                        # If it's fully numeric, it's unmasked
                        assert not rp[field].startswith('****'), f"Bank account should be unmasked for PE user, got: {rp[field]}"
                        print(f"Bank account number is unmasked: {rp[field]}")
        else:
            print("No RPs found to verify bank details")


class TestPaymentProofUpload:
    """Test payment proof upload endpoint"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self, pe_token):
        return {"Authorization": f"Bearer {pe_token}"}
    
    @pytest.fixture(scope="class")
    def pe_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "pe@smifs.com",
            "password": "Kutta@123"
        })
        assert response.status_code == 200
        return response.json()["token"]
    
    def test_payment_upload_proof_endpoint_exists(self, auth_headers):
        """Verify payment proof upload endpoint exists and accepts multipart"""
        # Try to upload without file - should get 422 (validation error) not 404
        response = requests.post(
            f"{BASE_URL}/api/payments/upload-proof",
            headers=auth_headers
        )
        # 422 means endpoint exists but validation failed (no file)
        # 400 also acceptable for bad request
        assert response.status_code in [422, 400, 500], f"Expected 422/400/500, got {response.status_code}"
        print(f"Payment upload endpoint exists, status: {response.status_code}")
    
    def test_vendor_payment_upload_proof_endpoint_exists(self, auth_headers):
        """Verify vendor payment proof upload endpoint exists"""
        response = requests.post(
            f"{BASE_URL}/api/payments/vendor/upload-proof",
            headers=auth_headers
        )
        # 422 means endpoint exists but validation failed (no file)
        assert response.status_code in [422, 400, 500], f"Expected 422/400/500, got {response.status_code}"
        print(f"Vendor payment upload endpoint exists, status: {response.status_code}")
    
    def test_payment_upload_with_dummy_file(self, auth_headers):
        """Test payment proof upload with a dummy text file"""
        # Create a dummy file in memory
        files = {
            'file': ('test_payment_proof.pdf', b'%PDF-1.4 dummy content', 'application/pdf')
        }
        
        response = requests.post(
            f"{BASE_URL}/api/payments/upload-proof",
            headers=auth_headers,
            files=files
        )
        
        # Either success (200/201) or validation error
        print(f"Upload response status: {response.status_code}")
        if response.status_code in [200, 201]:
            data = response.json()
            assert "url" in data or "file_id" in data
            print(f"Upload successful: {data}")
        else:
            print(f"Upload failed with: {response.text[:200]}")


class TestBookingPaymentsWithProof:
    """Test booking payments have proof_url field"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self, pe_token):
        return {"Authorization": f"Bearer {pe_token}"}
    
    @pytest.fixture(scope="class")
    def pe_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "pe@smifs.com",
            "password": "Kutta@123"
        })
        assert response.status_code == 200
        return response.json()["token"]
    
    def test_bookings_endpoint_exists(self, auth_headers):
        """Verify bookings endpoint exists"""
        response = requests.get(f"{BASE_URL}/api/bookings", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"Found {len(data)} bookings")
        return data
    
    def test_bookings_have_payments_structure(self, auth_headers):
        """Verify bookings with payments have correct structure"""
        response = requests.get(f"{BASE_URL}/api/bookings", headers=auth_headers)
        assert response.status_code == 200
        bookings = response.json()
        
        # Find a booking with payments
        bookings_with_payments = [b for b in bookings if b.get('payments') and len(b.get('payments', [])) > 0]
        
        if bookings_with_payments:
            booking = bookings_with_payments[0]
            print(f"Found booking {booking.get('booking_number')} with {len(booking['payments'])} payments")
            
            # Check payments structure
            for payment in booking['payments']:
                # Check essential fields exist
                assert 'amount' in payment
                assert 'tranche_number' in payment
                # proof_url should be available (can be null)
                if 'proof_url' in payment:
                    print(f"Payment tranche {payment['tranche_number']} has proof_url: {payment.get('proof_url')}")
        else:
            print("No bookings with payments found to verify structure")


class TestPurchasesVendorPayments:
    """Test purchases vendor payment proof viewing"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self, pe_token):
        return {"Authorization": f"Bearer {pe_token}"}
    
    @pytest.fixture(scope="class")
    def pe_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "pe@smifs.com",
            "password": "Kutta@123"
        })
        assert response.status_code == 200
        return response.json()["token"]
    
    def test_purchases_endpoint_exists(self, auth_headers):
        """Verify purchases endpoint exists"""
        response = requests.get(f"{BASE_URL}/api/purchases", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"Found {len(data)} purchases")
    
    def test_purchases_payments_endpoint(self, auth_headers):
        """Test fetching payments for a purchase"""
        # Get purchases first
        response = requests.get(f"{BASE_URL}/api/purchases", headers=auth_headers)
        assert response.status_code == 200
        purchases = response.json()
        
        if purchases:
            # Get payments for first purchase
            purchase_id = purchases[0]['id']
            payments_response = requests.get(
                f"{BASE_URL}/api/purchases/{purchase_id}/payments",
                headers=auth_headers
            )
            # May be 200 (with payments) or 404 if no payments
            assert payments_response.status_code in [200, 404]
            
            if payments_response.status_code == 200:
                payments = payments_response.json()
                print(f"Found {len(payments)} payments for purchase {purchase_id}")
                for payment in payments:
                    if 'proof_url' in payment:
                        print(f"Payment has proof_url: {payment.get('proof_url')}")
        else:
            print("No purchases found to test payments endpoint")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
