"""
Employee Commission Feature Tests

Tests for:
1. Booking creation calculates employee_revenue_share_percent = 100 - rp_revenue_share_percent
2. Stock transfer confirmation calculates employee_commission_amount from profit
3. GET /api/finance/employee-commissions returns list of commissions from confirmed bookings
4. GET /api/finance/employee-commissions/summary returns aggregated stats by employee
5. PUT /api/finance/employee-commissions/{booking_id}/mark-paid updates status to paid
"""
import pytest
import requests
import os
import uuid
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
PE_DESK_EMAIL = "pedesk@smifs.com"
PE_DESK_PASSWORD = "Kutta@123"
EMPLOYEE_EMAIL = "employee@test.com"
EMPLOYEE_PASSWORD = "Test@123"


class TestEmployeeCommissionFeature:
    """Test employee commission calculation and tracking"""
    
    pe_token = None
    employee_token = None
    test_client_id = None
    test_stock_id = None
    test_rp_id = None
    test_booking_id = None
    test_booking_number = None
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test data"""
        # Login as PE Desk
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": PE_DESK_EMAIL,
            "password": PE_DESK_PASSWORD
        })
        assert response.status_code == 200, f"PE Desk login failed: {response.text}"
        TestEmployeeCommissionFeature.pe_token = response.json()["token"]
        
        # Try to login as employee (may not exist)
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": EMPLOYEE_EMAIL,
            "password": EMPLOYEE_PASSWORD
        })
        if response.status_code == 200:
            TestEmployeeCommissionFeature.employee_token = response.json()["token"]
    
    def get_pe_headers(self):
        return {"Authorization": f"Bearer {TestEmployeeCommissionFeature.pe_token}"}
    
    def get_employee_headers(self):
        return {"Authorization": f"Bearer {TestEmployeeCommissionFeature.employee_token}"}
    
    def test_01_get_existing_test_data(self):
        """Get existing test data for commission testing"""
        headers = self.get_pe_headers()
        
        # Get existing approved client
        response = requests.get(f"{BASE_URL}/api/clients", headers=headers)
        assert response.status_code == 200
        clients = [c for c in response.json() if c.get("approval_status") == "approved"]
        assert len(clients) > 0, "No approved clients found"
        TestEmployeeCommissionFeature.test_client_id = clients[0]["id"]
        
        # Get existing stock with inventory
        response = requests.get(f"{BASE_URL}/api/inventory", headers=headers)
        assert response.status_code == 200
        inventory = response.json()
        assert len(inventory) > 0, "No inventory found"
        TestEmployeeCommissionFeature.test_stock_id = inventory[0]["stock_id"]
        
        # Get approved RP
        response = requests.get(f"{BASE_URL}/api/referral-partners-approved", headers=headers)
        assert response.status_code == 200
        rps = response.json()
        assert len(rps) > 0, "No approved RPs found"
        TestEmployeeCommissionFeature.test_rp_id = rps[0]["id"]
        
        print(f"Test data - Client: {TestEmployeeCommissionFeature.test_client_id}")
        print(f"Test data - Stock: {TestEmployeeCommissionFeature.test_stock_id}")
        print(f"Test data - RP: {TestEmployeeCommissionFeature.test_rp_id}")
    
    def test_02_booking_with_rp_calculates_employee_share(self):
        """Test that booking creation calculates employee_revenue_share_percent = 100 - rp_revenue_share_percent"""
        headers = self.get_pe_headers()
        
        # Create booking with 25% RP share
        booking_data = {
            "client_id": TestEmployeeCommissionFeature.test_client_id,
            "stock_id": TestEmployeeCommissionFeature.test_stock_id,
            "quantity": 10,
            "buying_price": 100.0,
            "selling_price": 160.0,  # Profit = 60 per share = 600 total
            "booking_date": datetime.now().strftime("%Y-%m-%d"),
            "status": "pending",
            "booking_type": "regular",
            "referral_partner_id": TestEmployeeCommissionFeature.test_rp_id,
            "rp_revenue_share_percent": 25.0  # RP gets 25%, employee gets 75%
        }
        
        response = requests.post(f"{BASE_URL}/api/bookings", json=booking_data, headers=headers)
        assert response.status_code == 200, f"Booking creation failed: {response.text}"
        
        booking = response.json()
        TestEmployeeCommissionFeature.test_booking_id = booking["id"]
        TestEmployeeCommissionFeature.test_booking_number = booking.get("booking_number")
        
        # Verify employee share calculation
        assert booking.get("base_employee_share_percent") == 100.0, "Base employee share should be 100%"
        assert booking.get("employee_revenue_share_percent") == 75.0, f"Employee share should be 75% (100 - 25), got {booking.get('employee_revenue_share_percent')}"
        assert booking.get("rp_revenue_share_percent") == 25.0, "RP share should be 25%"
        assert booking.get("employee_commission_status") == "pending", "Commission status should be pending initially"
        
        print(f"SUCCESS: Booking created: {TestEmployeeCommissionFeature.test_booking_number}")
        print(f"SUCCESS: Employee share calculated: {booking.get('employee_revenue_share_percent')}%")
    
    def test_03_booking_without_rp_has_full_employee_share(self):
        """Test that booking without RP has 100% employee share"""
        headers = self.get_pe_headers()
        
        # Create booking without RP
        booking_data = {
            "client_id": TestEmployeeCommissionFeature.test_client_id,
            "stock_id": TestEmployeeCommissionFeature.test_stock_id,
            "quantity": 5,
            "buying_price": 100.0,
            "selling_price": 120.0,
            "booking_date": datetime.now().strftime("%Y-%m-%d"),
            "status": "pending",
            "booking_type": "regular"
            # No referral_partner_id
        }
        
        response = requests.post(f"{BASE_URL}/api/bookings", json=booking_data, headers=headers)
        assert response.status_code == 200, f"Booking creation failed: {response.text}"
        
        booking = response.json()
        
        # Verify full employee share
        assert booking.get("employee_revenue_share_percent") == 100.0, f"Employee share should be 100% without RP, got {booking.get('employee_revenue_share_percent')}"
        
        print(f"SUCCESS: Booking without RP - Employee share: {booking.get('employee_revenue_share_percent')}%")
    
    def test_04_approve_and_process_booking(self):
        """Approve booking, record payment, and confirm transfer"""
        headers = self.get_pe_headers()
        
        # Step 1: Approve booking
        response = requests.put(
            f"{BASE_URL}/api/bookings/{TestEmployeeCommissionFeature.test_booking_id}/approve?approve=true",
            headers=headers
        )
        assert response.status_code == 200, f"Booking approval failed: {response.text}"
        print("SUCCESS: Booking approved")
        
        # Step 2: Record payment
        payment_data = {
            "amount": 1600,  # 10 * 160
            "payment_date": datetime.now().strftime("%Y-%m-%d"),
            "notes": "Test payment for commission testing"
        }
        response = requests.post(
            f"{BASE_URL}/api/bookings/{TestEmployeeCommissionFeature.test_booking_id}/payments",
            json=payment_data,
            headers=headers
        )
        assert response.status_code == 200, f"Payment recording failed: {response.text}"
        print("SUCCESS: Payment recorded")
    
    def test_05_confirm_stock_transfer_calculates_commission(self):
        """Test that stock transfer confirmation calculates employee_commission_amount"""
        headers = self.get_pe_headers()
        
        # Confirm stock transfer
        response = requests.put(
            f"{BASE_URL}/api/bookings/{TestEmployeeCommissionFeature.test_booking_id}/confirm-transfer",
            headers=headers
        )
        assert response.status_code == 200, f"Stock transfer confirmation failed: {response.text}"
        
        result = response.json()
        
        # Verify employee commission was calculated
        assert "employee_commission_amount" in result, "Response should include employee_commission_amount"
        assert result["employee_commission_amount"] > 0, "Employee commission should be positive"
        
        # Expected: Profit = (160 - 100) * 10 = 600, Employee share = 75%, Commission = 450
        expected_commission = 600 * 0.75
        assert result["employee_commission_amount"] == expected_commission, f"Expected commission {expected_commission}, got {result['employee_commission_amount']}"
        
        # Get booking to verify commission details
        response = requests.get(
            f"{BASE_URL}/api/bookings/{TestEmployeeCommissionFeature.test_booking_id}",
            headers=headers
        )
        assert response.status_code == 200
        booking = response.json()
        
        assert booking.get("employee_commission_amount") == expected_commission, "Commission amount should match"
        assert booking.get("employee_commission_status") == "calculated", f"Commission status should be 'calculated', got {booking.get('employee_commission_status')}"
        assert booking.get("stock_transferred") == True, "Stock should be marked as transferred"
        
        print(f"SUCCESS: Employee commission calculated: {booking.get('employee_commission_amount')}")
        print(f"SUCCESS: Commission status: {booking.get('employee_commission_status')}")
    
    def test_06_get_employee_commissions_list(self):
        """Test GET /api/finance/employee-commissions returns list of commissions"""
        headers = self.get_pe_headers()
        
        response = requests.get(f"{BASE_URL}/api/finance/employee-commissions", headers=headers)
        assert response.status_code == 200, f"Get commissions failed: {response.text}"
        
        commissions = response.json()
        assert isinstance(commissions, list), "Response should be a list"
        
        # Find our test booking commission
        test_commission = None
        for comm in commissions:
            if comm.get("booking_id") == TestEmployeeCommissionFeature.test_booking_id:
                test_commission = comm
                break
        
        assert test_commission is not None, "Test booking commission should be in the list"
        
        # Verify commission data structure
        assert "booking_number" in test_commission, "Commission should have booking_number"
        assert "employee_name" in test_commission, "Commission should have employee_name"
        assert "profit" in test_commission, "Commission should have profit"
        assert "employee_share_percent" in test_commission, "Commission should have employee_share_percent"
        assert "employee_commission_amount" in test_commission, "Commission should have employee_commission_amount"
        assert "status" in test_commission, "Commission should have status"
        
        # Verify values
        assert test_commission["profit"] == 600, f"Profit should be 600, got {test_commission['profit']}"
        assert test_commission["employee_share_percent"] == 75, f"Employee share should be 75%, got {test_commission['employee_share_percent']}"
        assert test_commission["employee_commission_amount"] == 450, f"Commission should be 450, got {test_commission['employee_commission_amount']}"
        
        print(f"SUCCESS: Found {len(commissions)} commissions")
        print(f"SUCCESS: Test commission verified with correct values")
    
    def test_07_get_employee_commissions_summary(self):
        """Test GET /api/finance/employee-commissions/summary returns aggregated stats"""
        headers = self.get_pe_headers()
        
        response = requests.get(f"{BASE_URL}/api/finance/employee-commissions/summary", headers=headers)
        assert response.status_code == 200, f"Get commission summary failed: {response.text}"
        
        summary = response.json()
        assert isinstance(summary, list), "Response should be a list of employee summaries"
        assert len(summary) > 0, "Summary should have at least one employee"
        
        # Verify summary structure
        emp_summary = summary[0]
        assert "employee_id" in emp_summary, "Summary should have employee_id"
        assert "employee_name" in emp_summary, "Summary should have employee_name"
        assert "total_bookings" in emp_summary, "Summary should have total_bookings"
        assert "total_profit" in emp_summary, "Summary should have total_profit"
        assert "total_commission" in emp_summary, "Summary should have total_commission"
        assert "pending_commission" in emp_summary, "Summary should have pending_commission"
        assert "calculated_commission" in emp_summary, "Summary should have calculated_commission"
        assert "paid_commission" in emp_summary, "Summary should have paid_commission"
        
        print(f"SUCCESS: Commission summary for {len(summary)} employees")
        for emp in summary[:3]:
            print(f"  {emp.get('employee_name')}: Total={emp.get('total_commission')}, Calculated={emp.get('calculated_commission')}, Paid={emp.get('paid_commission')}")
    
    def test_08_mark_commission_as_paid(self):
        """Test PUT /api/finance/employee-commissions/{booking_id}/mark-paid"""
        headers = self.get_pe_headers()
        
        response = requests.put(
            f"{BASE_URL}/api/finance/employee-commissions/{TestEmployeeCommissionFeature.test_booking_id}/mark-paid",
            headers=headers
        )
        assert response.status_code == 200, f"Mark commission paid failed: {response.text}"
        
        result = response.json()
        assert "message" in result, "Response should have message"
        
        # Verify commission status updated
        response = requests.get(
            f"{BASE_URL}/api/bookings/{TestEmployeeCommissionFeature.test_booking_id}",
            headers=headers
        )
        assert response.status_code == 200
        booking = response.json()
        
        assert booking.get("employee_commission_status") == "paid", f"Commission status should be 'paid', got {booking.get('employee_commission_status')}"
        
        print(f"SUCCESS: Commission marked as paid")
    
    def test_09_commission_summary_reflects_paid_status(self):
        """Verify commission summary reflects paid status"""
        headers = self.get_pe_headers()
        
        response = requests.get(f"{BASE_URL}/api/finance/employee-commissions/summary", headers=headers)
        assert response.status_code == 200
        
        summary = response.json()
        
        # Check that paid_commission is reflected
        total_paid = sum(emp.get("paid_commission", 0) for emp in summary)
        assert total_paid > 0, "There should be some paid commissions after marking as paid"
        
        print(f"SUCCESS: Total paid commissions across all employees: {total_paid}")
    
    def test_10_non_finance_user_cannot_access_commissions(self):
        """Test that non-finance users cannot access commission endpoints"""
        # Skip if no employee token
        if not TestEmployeeCommissionFeature.employee_token:
            pytest.skip("Employee user not available")
        
        headers = self.get_employee_headers()
        
        # Try to access commissions
        response = requests.get(f"{BASE_URL}/api/finance/employee-commissions", headers=headers)
        assert response.status_code == 403, f"Employee should not access commissions, got {response.status_code}"
        
        # Try to access summary
        response = requests.get(f"{BASE_URL}/api/finance/employee-commissions/summary", headers=headers)
        assert response.status_code == 403, f"Employee should not access commission summary, got {response.status_code}"
        
        print("SUCCESS: Non-finance user correctly denied access to commission endpoints")
    
    def test_11_filter_commissions_by_status(self):
        """Test filtering commissions by status"""
        headers = self.get_pe_headers()
        
        # Filter by paid status
        response = requests.get(f"{BASE_URL}/api/finance/employee-commissions?status=paid", headers=headers)
        assert response.status_code == 200
        
        paid_commissions = response.json()
        for comm in paid_commissions:
            assert comm.get("status") == "paid", f"All commissions should be paid, got {comm.get('status')}"
        
        print(f"SUCCESS: Found {len(paid_commissions)} paid commissions")
    
    def test_12_rp_share_cap_at_30_percent(self):
        """Test that RP revenue share cannot exceed 30%"""
        headers = self.get_pe_headers()
        
        # Try to create booking with 35% RP share
        booking_data = {
            "client_id": TestEmployeeCommissionFeature.test_client_id,
            "stock_id": TestEmployeeCommissionFeature.test_stock_id,
            "quantity": 5,
            "buying_price": 100.0,
            "selling_price": 120.0,
            "booking_date": datetime.now().strftime("%Y-%m-%d"),
            "status": "pending",
            "booking_type": "regular",
            "referral_partner_id": TestEmployeeCommissionFeature.test_rp_id,
            "rp_revenue_share_percent": 35.0  # Exceeds 30% cap
        }
        
        response = requests.post(f"{BASE_URL}/api/bookings", json=booking_data, headers=headers)
        assert response.status_code == 400, f"Should reject RP share > 30%, got {response.status_code}"
        
        error = response.json()
        assert "30%" in str(error.get("detail", "")), "Error should mention 30% cap"
        
        print("SUCCESS: RP share cap at 30% correctly enforced")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
