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
    
    def test_01_setup_test_data(self):
        """Create test client, stock, and RP for commission testing"""
        headers = self.get_pe_headers()
        
        # Create test client
        client_data = {
            "name": f"TEST_Commission_Client_{uuid.uuid4().hex[:6]}",
            "email": f"test_commission_{uuid.uuid4().hex[:6]}@example.com",
            "phone": "9876543210",
            "pan_number": f"ABCDE{uuid.uuid4().hex[:4].upper()}F",
            "address": "Test Address",
            "city": "Mumbai",
            "state": "Maharashtra",
            "pincode": "400001",
            "client_type": "individual",
            "bank_accounts": [{
                "bank_name": "Test Bank",
                "account_number": "1234567890",
                "ifsc_code": "TEST0001234",
                "account_holder_name": "Test Client"
            }]
        }
        response = requests.post(f"{BASE_URL}/api/clients", json=client_data, headers=headers)
        assert response.status_code == 200, f"Client creation failed: {response.text}"
        TestEmployeeCommissionFeature.test_client_id = response.json()["id"]
        
        # Approve client
        response = requests.put(
            f"{BASE_URL}/api/clients/{TestEmployeeCommissionFeature.test_client_id}/approve",
            headers=headers
        )
        assert response.status_code == 200, f"Client approval failed: {response.text}"
        
        # Get existing stock or create one
        response = requests.get(f"{BASE_URL}/api/stocks", headers=headers)
        assert response.status_code == 200
        stocks = response.json()
        
        if stocks:
            TestEmployeeCommissionFeature.test_stock_id = stocks[0]["id"]
        else:
            # Create stock
            stock_data = {
                "symbol": f"TEST{uuid.uuid4().hex[:4].upper()}",
                "name": "Test Commission Stock",
                "isin": f"INE{uuid.uuid4().hex[:9].upper()}",
                "exchange": "NSE"
            }
            response = requests.post(f"{BASE_URL}/api/stocks", json=stock_data, headers=headers)
            assert response.status_code == 200, f"Stock creation failed: {response.text}"
            TestEmployeeCommissionFeature.test_stock_id = response.json()["id"]
        
        # Create purchase for inventory
        purchase_data = {
            "stock_id": TestEmployeeCommissionFeature.test_stock_id,
            "vendor_id": TestEmployeeCommissionFeature.test_client_id,
            "quantity": 1000,
            "price_per_unit": 100.0,
            "purchase_date": datetime.now().strftime("%Y-%m-%d")
        }
        response = requests.post(f"{BASE_URL}/api/purchases", json=purchase_data, headers=headers)
        # May fail if purchase already exists, that's ok
        
        # Get approved RP or create one
        response = requests.get(f"{BASE_URL}/api/referral-partners-approved", headers=headers)
        assert response.status_code == 200
        rps = response.json()
        
        if rps:
            TestEmployeeCommissionFeature.test_rp_id = rps[0]["id"]
        else:
            # Create RP
            rp_data = {
                "name": f"TEST_Commission_RP_{uuid.uuid4().hex[:6]}",
                "email": f"test_rp_{uuid.uuid4().hex[:6]}@example.com",
                "phone": "9876543211",
                "pan_number": f"ABCDE{uuid.uuid4().hex[:4].upper()}G",
                "address": "Test RP Address"
            }
            response = requests.post(f"{BASE_URL}/api/referral-partners", json=rp_data, headers=headers)
            assert response.status_code == 200, f"RP creation failed: {response.text}"
            TestEmployeeCommissionFeature.test_rp_id = response.json()["id"]
        
        print(f"Test data created - Client: {TestEmployeeCommissionFeature.test_client_id}, Stock: {TestEmployeeCommissionFeature.test_stock_id}, RP: {TestEmployeeCommissionFeature.test_rp_id}")
    
    def test_02_booking_with_rp_calculates_employee_share(self):
        """Test that booking creation calculates employee_revenue_share_percent = 100 - rp_revenue_share_percent"""
        headers = self.get_pe_headers()
        
        # Create booking with 20% RP share
        booking_data = {
            "client_id": TestEmployeeCommissionFeature.test_client_id,
            "stock_id": TestEmployeeCommissionFeature.test_stock_id,
            "quantity": 10,
            "buying_price": 100.0,
            "selling_price": 150.0,  # Profit = 50 per share = 500 total
            "booking_date": datetime.now().strftime("%Y-%m-%d"),
            "status": "pending",
            "booking_type": "normal",
            "referral_partner_id": TestEmployeeCommissionFeature.test_rp_id,
            "rp_revenue_share_percent": 20.0  # RP gets 20%, employee gets 80%
        }
        
        response = requests.post(f"{BASE_URL}/api/bookings", json=booking_data, headers=headers)
        assert response.status_code == 200, f"Booking creation failed: {response.text}"
        
        booking = response.json()
        TestEmployeeCommissionFeature.test_booking_id = booking["id"]
        TestEmployeeCommissionFeature.test_booking_number = booking.get("booking_number")
        
        # Verify employee share calculation
        assert booking.get("base_employee_share_percent") == 100.0, "Base employee share should be 100%"
        assert booking.get("employee_revenue_share_percent") == 80.0, f"Employee share should be 80% (100 - 20), got {booking.get('employee_revenue_share_percent')}"
        assert booking.get("rp_revenue_share_percent") == 20.0, "RP share should be 20%"
        assert booking.get("employee_commission_status") == "pending", "Commission status should be pending initially"
        
        print(f"Booking created: {TestEmployeeCommissionFeature.test_booking_number}")
        print(f"Employee share: {booking.get('employee_revenue_share_percent')}%")
    
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
            "booking_type": "normal"
            # No referral_partner_id
        }
        
        response = requests.post(f"{BASE_URL}/api/bookings", json=booking_data, headers=headers)
        assert response.status_code == 200, f"Booking creation failed: {response.text}"
        
        booking = response.json()
        
        # Verify full employee share
        assert booking.get("employee_revenue_share_percent") == 100.0, f"Employee share should be 100% without RP, got {booking.get('employee_revenue_share_percent')}"
        assert booking.get("rp_revenue_share_percent") is None or booking.get("rp_revenue_share_percent") == 0, "RP share should be 0 or None"
        
        print(f"Booking without RP - Employee share: {booking.get('employee_revenue_share_percent')}%")
    
    def test_04_approve_booking(self):
        """Approve the test booking"""
        headers = self.get_pe_headers()
        
        response = requests.put(
            f"{BASE_URL}/api/bookings/{TestEmployeeCommissionFeature.test_booking_id}/approve?approve=true",
            headers=headers
        )
        assert response.status_code == 200, f"Booking approval failed: {response.text}"
        print("Booking approved")
    
    def test_05_client_confirms_booking(self):
        """Client confirms the booking"""
        headers = self.get_pe_headers()
        
        # Get booking to get confirmation token
        response = requests.get(
            f"{BASE_URL}/api/bookings/{TestEmployeeCommissionFeature.test_booking_id}",
            headers=headers
        )
        assert response.status_code == 200
        booking = response.json()
        token = booking.get("client_confirmation_token")
        
        # Confirm booking
        response = requests.post(
            f"{BASE_URL}/api/bookings/{TestEmployeeCommissionFeature.test_booking_id}/client-confirm",
            json={"token": token, "action": "accept"}
        )
        # May fail if already confirmed or different flow
        print(f"Client confirmation response: {response.status_code}")
    
    def test_06_record_payment(self):
        """Record payment for the booking"""
        headers = self.get_pe_headers()
        
        # Get booking details
        response = requests.get(
            f"{BASE_URL}/api/bookings/{TestEmployeeCommissionFeature.test_booking_id}",
            headers=headers
        )
        assert response.status_code == 200
        booking = response.json()
        
        total_amount = booking.get("quantity", 0) * booking.get("selling_price", 0)
        
        # Record payment
        payment_data = {
            "amount": total_amount,
            "payment_date": datetime.now().strftime("%Y-%m-%d"),
            "notes": "Test payment for commission testing"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/bookings/{TestEmployeeCommissionFeature.test_booking_id}/payments",
            json=payment_data,
            headers=headers
        )
        # May fail if payment already recorded
        print(f"Payment recording response: {response.status_code}")
    
    def test_07_confirm_stock_transfer_calculates_commission(self):
        """Test that stock transfer confirmation calculates employee_commission_amount"""
        headers = self.get_pe_headers()
        
        # Confirm stock transfer
        response = requests.put(
            f"{BASE_URL}/api/bookings/{TestEmployeeCommissionFeature.test_booking_id}/confirm-transfer",
            headers=headers
        )
        assert response.status_code == 200, f"Stock transfer confirmation failed: {response.text}"
        
        result = response.json()
        print(f"Stock transfer result: {result}")
        
        # Verify employee commission was calculated
        assert "employee_commission_amount" in result, "Response should include employee_commission_amount"
        
        # Get booking to verify commission details
        response = requests.get(
            f"{BASE_URL}/api/bookings/{TestEmployeeCommissionFeature.test_booking_id}",
            headers=headers
        )
        assert response.status_code == 200
        booking = response.json()
        
        # Calculate expected commission
        # Profit = (150 - 100) * 10 = 500
        # Employee share = 80%
        # Commission = 500 * 0.80 = 400
        expected_profit = (booking.get("selling_price", 0) - booking.get("buying_price", 0)) * booking.get("quantity", 0)
        expected_commission = expected_profit * (booking.get("employee_revenue_share_percent", 100) / 100)
        
        assert booking.get("employee_commission_amount") is not None, "Employee commission amount should be set"
        assert booking.get("employee_commission_amount") > 0, "Employee commission should be positive for profitable booking"
        assert booking.get("employee_commission_status") == "calculated", f"Commission status should be 'calculated', got {booking.get('employee_commission_status')}"
        assert booking.get("stock_transferred") == True, "Stock should be marked as transferred"
        
        print(f"Profit: {expected_profit}")
        print(f"Employee share: {booking.get('employee_revenue_share_percent')}%")
        print(f"Employee commission: {booking.get('employee_commission_amount')}")
        print(f"Commission status: {booking.get('employee_commission_status')}")
    
    def test_08_get_employee_commissions_list(self):
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
        
        print(f"Found {len(commissions)} commissions")
        print(f"Test commission: {test_commission}")
    
    def test_09_get_employee_commissions_summary(self):
        """Test GET /api/finance/employee-commissions/summary returns aggregated stats"""
        headers = self.get_pe_headers()
        
        response = requests.get(f"{BASE_URL}/api/finance/employee-commissions/summary", headers=headers)
        assert response.status_code == 200, f"Get commission summary failed: {response.text}"
        
        summary = response.json()
        assert isinstance(summary, list), "Response should be a list of employee summaries"
        
        if len(summary) > 0:
            # Verify summary structure
            emp_summary = summary[0]
            assert "employee_id" in emp_summary, "Summary should have employee_id"
            assert "employee_name" in emp_summary, "Summary should have employee_name"
            assert "total_bookings" in emp_summary, "Summary should have total_bookings"
            assert "total_profit" in emp_summary, "Summary should have total_profit"
            assert "total_commission" in emp_summary, "Summary should have total_commission"
            assert "pending_commission" in emp_summary, "Summary should have pending_commission"
            assert "paid_commission" in emp_summary, "Summary should have paid_commission"
            
            print(f"Commission summary for {len(summary)} employees")
            for emp in summary[:3]:
                print(f"  {emp.get('employee_name')}: Total={emp.get('total_commission')}, Pending={emp.get('pending_commission')}, Paid={emp.get('paid_commission')}")
    
    def test_10_mark_commission_as_paid(self):
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
        assert booking.get("employee_commission_paid_at") is not None, "Commission paid_at should be set"
        
        print(f"Commission marked as paid at: {booking.get('employee_commission_paid_at')}")
    
    def test_11_commission_summary_reflects_paid_status(self):
        """Verify commission summary reflects paid status"""
        headers = self.get_pe_headers()
        
        response = requests.get(f"{BASE_URL}/api/finance/employee-commissions/summary", headers=headers)
        assert response.status_code == 200
        
        summary = response.json()
        
        # Check that paid_commission is reflected
        total_paid = sum(emp.get("paid_commission", 0) for emp in summary)
        assert total_paid > 0, "There should be some paid commissions after marking as paid"
        
        print(f"Total paid commissions across all employees: {total_paid}")
    
    def test_12_non_finance_user_cannot_access_commissions(self):
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
        
        print("Non-finance user correctly denied access to commission endpoints")
    
    def test_13_filter_commissions_by_status(self):
        """Test filtering commissions by status"""
        headers = self.get_pe_headers()
        
        # Filter by paid status
        response = requests.get(f"{BASE_URL}/api/finance/employee-commissions?status=paid", headers=headers)
        assert response.status_code == 200
        
        paid_commissions = response.json()
        for comm in paid_commissions:
            assert comm.get("status") == "paid", f"All commissions should be paid, got {comm.get('status')}"
        
        print(f"Found {len(paid_commissions)} paid commissions")
        
        # Filter by calculated status
        response = requests.get(f"{BASE_URL}/api/finance/employee-commissions?status=calculated", headers=headers)
        assert response.status_code == 200
        
        calculated_commissions = response.json()
        for comm in calculated_commissions:
            assert comm.get("status") == "calculated", f"All commissions should be calculated, got {comm.get('status')}"
        
        print(f"Found {len(calculated_commissions)} calculated commissions")
    
    def test_14_rp_share_cap_at_30_percent(self):
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
            "booking_type": "normal",
            "referral_partner_id": TestEmployeeCommissionFeature.test_rp_id,
            "rp_revenue_share_percent": 35.0  # Exceeds 30% cap
        }
        
        response = requests.post(f"{BASE_URL}/api/bookings", json=booking_data, headers=headers)
        assert response.status_code == 400, f"Should reject RP share > 30%, got {response.status_code}"
        
        error = response.json()
        assert "30%" in str(error.get("detail", "")), "Error should mention 30% cap"
        
        print("RP share cap at 30% correctly enforced")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
