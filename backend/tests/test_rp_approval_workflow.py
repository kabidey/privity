"""
Test RP Approval Workflow Feature

Tests:
1. Employee creates RP -> status is 'pending'
2. PE Level creates RP -> status is 'approved' (auto-approved)
3. PE Level can view pending approvals tab (GET /referral-partners-pending)
4. PE Level can approve pending RP (PUT /referral-partners/{id}/approve)
5. PE Level can reject pending RP with reason
6. Booking form shows only approved RPs (GET /referral-partners-approved)
7. Non-PE Level cannot access pending approvals endpoint
8. Already approved RP cannot be approved again
"""

import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
PE_DESK_EMAIL = "pedesk@smifs.com"
PE_DESK_PASSWORD = "Kutta@123"
EMPLOYEE_EMAIL = "employee@test.com"
EMPLOYEE_PASSWORD = "Test@123"


class TestRPApprovalWorkflow:
    """Test RP Approval Workflow - Employee creates pending, PE Level auto-approves"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        self.pe_token = None
        self.employee_token = None
        self.created_rp_ids = []
    
    def get_pe_token(self):
        """Get PE Desk authentication token"""
        if self.pe_token:
            return self.pe_token
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": PE_DESK_EMAIL,
            "password": PE_DESK_PASSWORD
        })
        if response.status_code == 200:
            self.pe_token = response.json().get("token")
            return self.pe_token
        pytest.skip(f"PE Desk login failed: {response.status_code}")
    
    def get_employee_token(self):
        """Get Employee authentication token"""
        if self.employee_token:
            return self.employee_token
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": EMPLOYEE_EMAIL,
            "password": EMPLOYEE_PASSWORD
        })
        if response.status_code == 200:
            self.employee_token = response.json().get("token")
            return self.employee_token
        # If employee doesn't exist, create one
        return None
    
    def generate_unique_rp_data(self, prefix="TEST"):
        """Generate unique RP data for testing"""
        unique_id = str(uuid.uuid4())[:8]
        return {
            "name": f"{prefix} RP {unique_id}",
            "email": f"testrp_{unique_id}@example.com",
            "phone": f"98765{unique_id[:5].replace('-', '0')}",
            "pan_number": f"ABCDE{unique_id[:4].upper()}F",
            "aadhar_number": f"1234567890{unique_id[:2].replace('-', '0')}",
            "address": f"Test Address {unique_id}"
        }
    
    # ============== Test 1: Employee creates RP -> status is 'pending' ==============
    def test_01_employee_creates_rp_status_pending(self):
        """Employee creates RP - should have status 'pending'"""
        token = self.get_employee_token()
        if not token:
            pytest.skip("Employee account not available")
        
        rp_data = self.generate_unique_rp_data("EMP")
        # Ensure valid phone (10 digits) - use unique
        import random
        rp_data["phone"] = f"98{random.randint(10000000, 99999999)}"
        # Ensure valid aadhar (12 digits) - use unique
        rp_data["aadhar_number"] = f"{random.randint(100000000000, 999999999999)}"
        
        response = self.session.post(
            f"{BASE_URL}/api/referral-partners",
            json=rp_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200, f"Failed to create RP: {response.text}"
        data = response.json()
        
        # Verify status is pending for employee-created RP
        assert data.get("approval_status") == "pending", f"Expected 'pending', got '{data.get('approval_status')}'"
        assert data.get("approved_by") is None, "approved_by should be None for pending RP"
        assert data.get("approved_at") is None, "approved_at should be None for pending RP"
        
        self.created_rp_ids.append(data.get("id"))
        print(f"✓ Employee created RP {data.get('rp_code')} with status 'pending'")
    
    # ============== Test 2: PE Level creates RP -> status is 'approved' (auto-approved) ==============
    def test_02_pe_level_creates_rp_auto_approved(self):
        """PE Level creates RP - should be auto-approved"""
        token = self.get_pe_token()
        
        rp_data = self.generate_unique_rp_data("PE")
        import random
        rp_data["phone"] = f"98{random.randint(10000000, 99999999)}"
        rp_data["aadhar_number"] = f"{random.randint(100000000000, 999999999999)}"
        
        response = self.session.post(
            f"{BASE_URL}/api/referral-partners",
            json=rp_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200, f"Failed to create RP: {response.text}"
        data = response.json()
        
        # Verify status is approved for PE-created RP
        assert data.get("approval_status") == "approved", f"Expected 'approved', got '{data.get('approval_status')}'"
        assert data.get("approved_by") is not None, "approved_by should be set for auto-approved RP"
        assert data.get("approved_at") is not None, "approved_at should be set for auto-approved RP"
        
        self.created_rp_ids.append(data.get("id"))
        print(f"✓ PE Level created RP {data.get('rp_code')} with status 'approved' (auto-approved)")
    
    # ============== Test 3: PE Level can view pending approvals ==============
    def test_03_pe_level_can_view_pending_approvals(self):
        """PE Level can access GET /referral-partners-pending"""
        token = self.get_pe_token()
        
        response = self.session.get(
            f"{BASE_URL}/api/referral-partners-pending",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200, f"Failed to get pending RPs: {response.text}"
        data = response.json()
        
        # Should return a list
        assert isinstance(data, list), "Response should be a list"
        
        # All items should have pending status
        for rp in data:
            assert rp.get("approval_status") == "pending", f"Found non-pending RP in pending list: {rp.get('rp_code')}"
        
        print(f"✓ PE Level can view pending approvals - found {len(data)} pending RPs")
    
    # ============== Test 4: Non-PE Level cannot access pending approvals ==============
    def test_04_non_pe_level_cannot_view_pending_approvals(self):
        """Employee cannot access GET /referral-partners-pending"""
        token = self.get_employee_token()
        if not token:
            pytest.skip("Employee account not available")
        
        response = self.session.get(
            f"{BASE_URL}/api/referral-partners-pending",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print("✓ Non-PE Level correctly denied access to pending approvals")
    
    # ============== Test 5: PE Level can approve pending RP ==============
    def test_05_pe_level_can_approve_pending_rp(self):
        """PE Level can approve a pending RP"""
        pe_token = self.get_pe_token()
        employee_token = self.get_employee_token()
        
        if not employee_token:
            pytest.skip("Employee account not available")
        
        # First create a pending RP as employee
        rp_data = self.generate_unique_rp_data("APPROVE")
        rp_data["phone"] = "9876543212"
        rp_data["aadhar_number"] = "123456789014"
        
        create_response = self.session.post(
            f"{BASE_URL}/api/referral-partners",
            json=rp_data,
            headers={"Authorization": f"Bearer {employee_token}"}
        )
        
        assert create_response.status_code == 200, f"Failed to create RP: {create_response.text}"
        rp_id = create_response.json().get("id")
        rp_code = create_response.json().get("rp_code")
        self.created_rp_ids.append(rp_id)
        
        # Now approve as PE Level
        approve_response = self.session.put(
            f"{BASE_URL}/api/referral-partners/{rp_id}/approve",
            json={"approve": True},
            headers={"Authorization": f"Bearer {pe_token}"}
        )
        
        assert approve_response.status_code == 200, f"Failed to approve RP: {approve_response.text}"
        
        # Verify the RP is now approved
        get_response = self.session.get(
            f"{BASE_URL}/api/referral-partners/{rp_id}",
            headers={"Authorization": f"Bearer {pe_token}"}
        )
        
        assert get_response.status_code == 200
        data = get_response.json()
        assert data.get("approval_status") == "approved", f"Expected 'approved', got '{data.get('approval_status')}'"
        assert data.get("approved_by") is not None, "approved_by should be set"
        assert data.get("approved_at") is not None, "approved_at should be set"
        
        print(f"✓ PE Level approved RP {rp_code}")
    
    # ============== Test 6: PE Level can reject pending RP with reason ==============
    def test_06_pe_level_can_reject_pending_rp_with_reason(self):
        """PE Level can reject a pending RP with reason"""
        pe_token = self.get_pe_token()
        employee_token = self.get_employee_token()
        
        if not employee_token:
            pytest.skip("Employee account not available")
        
        # First create a pending RP as employee
        rp_data = self.generate_unique_rp_data("REJECT")
        rp_data["phone"] = "9876543213"
        rp_data["aadhar_number"] = "123456789015"
        
        create_response = self.session.post(
            f"{BASE_URL}/api/referral-partners",
            json=rp_data,
            headers={"Authorization": f"Bearer {employee_token}"}
        )
        
        assert create_response.status_code == 200, f"Failed to create RP: {create_response.text}"
        rp_id = create_response.json().get("id")
        rp_code = create_response.json().get("rp_code")
        self.created_rp_ids.append(rp_id)
        
        # Now reject as PE Level with reason
        rejection_reason = "Invalid documents provided"
        reject_response = self.session.put(
            f"{BASE_URL}/api/referral-partners/{rp_id}/approve",
            json={"approve": False, "rejection_reason": rejection_reason},
            headers={"Authorization": f"Bearer {pe_token}"}
        )
        
        assert reject_response.status_code == 200, f"Failed to reject RP: {reject_response.text}"
        
        # Verify the RP is now rejected
        get_response = self.session.get(
            f"{BASE_URL}/api/referral-partners/{rp_id}",
            headers={"Authorization": f"Bearer {pe_token}"}
        )
        
        assert get_response.status_code == 200
        data = get_response.json()
        assert data.get("approval_status") == "rejected", f"Expected 'rejected', got '{data.get('approval_status')}'"
        assert data.get("rejection_reason") == rejection_reason, f"Rejection reason mismatch"
        
        print(f"✓ PE Level rejected RP {rp_code} with reason: {rejection_reason}")
    
    # ============== Test 7: Rejection without reason fails ==============
    def test_07_rejection_without_reason_fails(self):
        """Rejection without reason should fail"""
        pe_token = self.get_pe_token()
        employee_token = self.get_employee_token()
        
        if not employee_token:
            pytest.skip("Employee account not available")
        
        # First create a pending RP as employee
        rp_data = self.generate_unique_rp_data("NOREJECT")
        rp_data["phone"] = "9876543214"
        rp_data["aadhar_number"] = "123456789016"
        
        create_response = self.session.post(
            f"{BASE_URL}/api/referral-partners",
            json=rp_data,
            headers={"Authorization": f"Bearer {employee_token}"}
        )
        
        assert create_response.status_code == 200, f"Failed to create RP: {create_response.text}"
        rp_id = create_response.json().get("id")
        self.created_rp_ids.append(rp_id)
        
        # Try to reject without reason
        reject_response = self.session.put(
            f"{BASE_URL}/api/referral-partners/{rp_id}/approve",
            json={"approve": False},  # No rejection_reason
            headers={"Authorization": f"Bearer {pe_token}"}
        )
        
        assert reject_response.status_code == 400, f"Expected 400, got {reject_response.status_code}"
        assert "reason" in reject_response.text.lower(), "Error should mention rejection reason"
        
        print("✓ Rejection without reason correctly fails")
    
    # ============== Test 8: Booking form shows only approved RPs ==============
    def test_08_booking_form_shows_only_approved_rps(self):
        """GET /referral-partners-approved returns only approved and active RPs"""
        token = self.get_pe_token()
        
        response = self.session.get(
            f"{BASE_URL}/api/referral-partners-approved",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200, f"Failed to get approved RPs: {response.text}"
        data = response.json()
        
        # Should return a list
        assert isinstance(data, list), "Response should be a list"
        
        # All items should have approved status and be active
        for rp in data:
            assert rp.get("approval_status") == "approved", f"Found non-approved RP: {rp.get('rp_code')}"
            assert rp.get("is_active") == True, f"Found inactive RP: {rp.get('rp_code')}"
        
        print(f"✓ Booking form endpoint returns only approved RPs - found {len(data)} approved RPs")
    
    # ============== Test 9: Already approved RP cannot be approved again ==============
    def test_09_already_approved_rp_cannot_be_approved_again(self):
        """Already approved RP cannot be approved again"""
        token = self.get_pe_token()
        
        # Create an auto-approved RP as PE Level
        rp_data = self.generate_unique_rp_data("DOUBLE")
        rp_data["phone"] = "9876543215"
        rp_data["aadhar_number"] = "123456789017"
        
        create_response = self.session.post(
            f"{BASE_URL}/api/referral-partners",
            json=rp_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert create_response.status_code == 200, f"Failed to create RP: {create_response.text}"
        rp_id = create_response.json().get("id")
        self.created_rp_ids.append(rp_id)
        
        # Try to approve again
        approve_response = self.session.put(
            f"{BASE_URL}/api/referral-partners/{rp_id}/approve",
            json={"approve": True},
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert approve_response.status_code == 400, f"Expected 400, got {approve_response.status_code}"
        assert "already approved" in approve_response.text.lower(), "Error should mention already approved"
        
        print("✓ Already approved RP correctly cannot be approved again")
    
    # ============== Test 10: Non-PE Level cannot approve RPs ==============
    def test_10_non_pe_level_cannot_approve_rps(self):
        """Employee cannot approve RPs"""
        pe_token = self.get_pe_token()
        employee_token = self.get_employee_token()
        
        if not employee_token:
            pytest.skip("Employee account not available")
        
        # First create a pending RP as employee
        rp_data = self.generate_unique_rp_data("NOAPPROVE")
        rp_data["phone"] = "9876543216"
        rp_data["aadhar_number"] = "123456789018"
        
        create_response = self.session.post(
            f"{BASE_URL}/api/referral-partners",
            json=rp_data,
            headers={"Authorization": f"Bearer {employee_token}"}
        )
        
        assert create_response.status_code == 200, f"Failed to create RP: {create_response.text}"
        rp_id = create_response.json().get("id")
        self.created_rp_ids.append(rp_id)
        
        # Try to approve as employee
        approve_response = self.session.put(
            f"{BASE_URL}/api/referral-partners/{rp_id}/approve",
            json={"approve": True},
            headers={"Authorization": f"Bearer {employee_token}"}
        )
        
        assert approve_response.status_code == 403, f"Expected 403, got {approve_response.status_code}"
        print("✓ Non-PE Level correctly denied from approving RPs")


class TestRPApprovalStatusBadge:
    """Test approval status badge display in API responses"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def get_pe_token(self):
        """Get PE Desk authentication token"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": PE_DESK_EMAIL,
            "password": PE_DESK_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip(f"PE Desk login failed: {response.status_code}")
    
    def test_11_rp_list_includes_approval_status(self):
        """GET /referral-partners includes approval_status field"""
        token = self.get_pe_token()
        
        response = self.session.get(
            f"{BASE_URL}/api/referral-partners?active_only=false",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200, f"Failed to get RPs: {response.text}"
        data = response.json()
        
        if len(data) > 0:
            # Check that approval_status field exists
            rp = data[0]
            assert "approval_status" in rp, "approval_status field missing from RP response"
            assert rp.get("approval_status") in ["pending", "approved", "rejected"], f"Invalid approval_status: {rp.get('approval_status')}"
            
            # Check for approval-related fields
            if rp.get("approval_status") == "approved":
                assert "approved_by" in rp, "approved_by field missing"
                assert "approved_at" in rp, "approved_at field missing"
        
        print("✓ RP list includes approval_status field")
    
    def test_12_rp_detail_includes_approval_info(self):
        """GET /referral-partners/{id} includes full approval info"""
        token = self.get_pe_token()
        
        # Get list first
        list_response = self.session.get(
            f"{BASE_URL}/api/referral-partners?active_only=false",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert list_response.status_code == 200
        rps = list_response.json()
        
        if len(rps) > 0:
            rp_id = rps[0].get("id")
            
            # Get detail
            detail_response = self.session.get(
                f"{BASE_URL}/api/referral-partners/{rp_id}",
                headers={"Authorization": f"Bearer {token}"}
            )
            
            assert detail_response.status_code == 200
            rp = detail_response.json()
            
            # Check all approval-related fields exist
            assert "approval_status" in rp, "approval_status field missing"
            assert "approved_by" in rp, "approved_by field missing"
            assert "approved_by_name" in rp, "approved_by_name field missing"
            assert "approved_at" in rp, "approved_at field missing"
            assert "rejection_reason" in rp, "rejection_reason field missing"
            
            print(f"✓ RP detail includes full approval info - status: {rp.get('approval_status')}")
        else:
            pytest.skip("No RPs available to test")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
