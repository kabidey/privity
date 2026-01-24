import requests
import sys
import json
from datetime import datetime, date

class SMIFSStockManagementTester:
    def __init__(self, base_url="https://last-project-10.preview.emergentagent.com"):
        self.base_url = base_url
        self.admin_token = None
        self.employee_token = None
        self.pe_desk_token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.admin_user = None
        self.employee_user = None
        self.pe_desk_user = None
        self.test_client_id = None
        self.test_booking_id = None
        self.test_stock_id = None
        self.test_corporate_action_id = None

    def run_test(self, name, method, endpoint, expected_status, data=None, token=None):
        """Run a single API test"""
        url = f"{self.base_url}/api/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        if token:
            headers['Authorization'] = f'Bearer {token}'

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    return success, response.json() if response.content else {}
                except:
                    return success, {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                try:
                    error_detail = response.json()
                    print(f"   Error: {error_detail}")
                except:
                    print(f"   Response: {response.text}")
                return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_admin_login(self):
        """Test admin login"""
        success, response = self.run_test(
            "Admin Login",
            "POST",
            "auth/login",
            200,
            data={"email": "admin@privity.com", "password": "Admin@123"}
        )
        if success and 'token' in response:
            self.admin_token = response['token']
            self.admin_user = response['user']
            print(f"   Admin role: {self.admin_user.get('role')} ({self.admin_user.get('role_name')})")
            # Admin should be PE Desk (role 1)
            if self.admin_user.get('role') == 1:
                self.pe_desk_token = self.admin_token
                self.pe_desk_user = self.admin_user
            return True
        return False

    def test_domain_restriction_invalid(self):
        """Test registration with invalid domain (should fail)"""
        employee_data = {
            "email": f"test_{datetime.now().strftime('%H%M%S')}@invalid.com",
            "password": "Employee@123",
            "name": "Invalid Domain User"
        }
        
        success, response = self.run_test(
            "Registration with Invalid Domain (Should Fail)",
            "POST",
            "auth/register",
            400,  # Should fail with 400
            data=employee_data
        )
        
        return success

    def test_domain_restriction_valid(self):
        """Test registration with valid @smifs.com domain"""
        employee_data = {
            "email": f"employee_{datetime.now().strftime('%H%M%S')}@smifs.com",
            "password": "Employee@123",
            "name": "SMIFS Employee"
        }
        
        success, response = self.run_test(
            "Registration with Valid @smifs.com Domain",
            "POST",
            "auth/register",
            200,
            data=employee_data
        )
        
        if success:
            self.employee_token = response['token']
            self.employee_user = response['user']
            print(f"   Employee role: {self.employee_user.get('role')} ({self.employee_user.get('role_name')})")
            # Should be Employee role (4)
            return self.employee_user.get('role') == 4
        return False

    def test_audit_logs_admin_access(self):
        """Test audit logs endpoint (admin only)"""
        success, response = self.run_test(
            "Get Audit Logs (Admin Only)",
            "GET",
            "audit-logs",
            200,
            token=self.admin_token
        )
        
        if success:
            print(f"   Audit logs count: {len(response)}")
            return True
        return False

    def test_audit_logs_employee_denied(self):
        """Test audit logs endpoint denied for employee"""
        success, response = self.run_test(
            "Get Audit Logs as Employee (Should Fail)",
            "GET",
            "audit-logs",
            403,  # Should be forbidden
            token=self.employee_token
        )
        
        return success

    def test_create_test_data(self):
        """Create test stock and client for booking tests"""
        # Create stock
        stock_data = {
            "symbol": "TESTSMIFS",
            "name": "Test SMIFS Stock",
            "exchange": "NSE"
        }
        
        success, stock_response = self.run_test(
            "Create Test Stock",
            "POST",
            "stocks",
            200,
            data=stock_data,
            token=self.admin_token
        )
        
        if not success:
            return False
            
        self.test_stock_id = stock_response['id']
        
        # Create vendor and purchase for inventory
        vendor_data = {
            "name": "Test Vendor SMIFS",
            "pan_number": "VEND01234V",
            "dp_id": "VENDOR123",
            "is_vendor": True
        }
        
        success, vendor_response = self.run_test(
            "Create Test Vendor",
            "POST",
            "clients",
            200,
            data=vendor_data,
            token=self.admin_token
        )
        
        if not success:
            return False
            
        vendor_id = vendor_response['id']
        
        # Create purchase for inventory
        purchase_data = {
            "vendor_id": vendor_id,
            "stock_id": self.test_stock_id,
            "quantity": 100,
            "price_per_unit": 50.0,
            "purchase_date": "2024-01-15",
            "notes": "Test purchase for booking approval"
        }
        
        success, purchase_response = self.run_test(
            "Create Test Purchase",
            "POST",
            "purchases",
            200,
            data=purchase_data,
            token=self.admin_token
        )
        
        if not success:
            return False
        
        # Create client for booking
        client_data = {
            "name": "Test Booking Client",
            "email": "bookingclient@example.com",
            "pan_number": "BOOK01234C",
            "dp_id": "BOOKING123",
            "is_vendor": False
        }
        
        success, client_response = self.run_test(
            "Create Test Client for Booking",
            "POST",
            "clients",
            200,
            data=client_data,
            token=self.admin_token
        )
        
        if success:
            self.test_client_id = client_response['id']
            return True
        return False

    def test_booking_requires_approval(self):
        """Test that booking creation requires PE Desk approval"""
        if not self.test_client_id or not self.test_stock_id:
            print("❌ Missing test data")
            return False
            
        booking_data = {
            "client_id": self.test_client_id,
            "stock_id": self.test_stock_id,
            "quantity": 10,
            "buying_price": 50.0,
            "selling_price": 60.0,
            "booking_date": "2024-01-16",
            "status": "open"
        }
        
        success, booking_response = self.run_test(
            "Create Booking (Should Require Approval)",
            "POST",
            "bookings",
            200,
            data=booking_data,
            token=self.admin_token
        )
        
        if success:
            self.test_booking_id = booking_response['id']
            approval_status = booking_response.get('approval_status')
            print(f"   Approval status: {approval_status}")
            # Should be pending approval
            return approval_status == 'pending'
        return False

    def test_pending_bookings_pe_desk_only(self):
        """Test GET /api/bookings/pending-approval (PE Desk only)"""
        success, response = self.run_test(
            "Get Pending Bookings (PE Desk Only)",
            "GET",
            "bookings/pending-approval",
            200,
            token=self.pe_desk_token
        )
        
        if success:
            print(f"   Pending bookings count: {len(response)}")
            return True
        return False

    def test_pending_bookings_employee_denied(self):
        """Test that employee cannot access pending bookings"""
        success, response = self.run_test(
            "Get Pending Bookings as Employee (Should Fail)",
            "GET",
            "bookings/pending-approval",
            403,  # Should be forbidden
            token=self.employee_token
        )
        
        return success

    def test_booking_approval_pe_desk_only(self):
        """Test PUT /api/bookings/{id}/approve (PE Desk only)"""
        if not self.test_booking_id:
            print("❌ No test booking available")
            return False
            
        success, response = self.run_test(
            "Approve Booking (PE Desk Only)",
            "PUT",
            f"bookings/{self.test_booking_id}/approve?approve=true",
            200,
            token=self.pe_desk_token
        )
        
        return success

    def test_booking_approval_employee_denied(self):
        """Test that employee cannot approve bookings"""
        if not self.test_booking_id:
            print("❌ No test booking available")
            return False
            
        success, response = self.run_test(
            "Approve Booking as Employee (Should Fail)",
            "PUT",
            f"bookings/{self.test_booking_id}/approve?approve=true",
            403,  # Should be forbidden
            token=self.employee_token
        )
        
        return success

    def test_inventory_not_adjusted_until_approved(self):
        """Test that inventory is not adjusted until booking is approved"""
        # Get inventory before approval
        success, inventory_before = self.run_test(
            "Get Inventory Before Approval",
            "GET",
            f"inventory/{self.test_stock_id}",
            200,
            token=self.admin_token
        )
        
        if not success:
            return False
            
        initial_quantity = inventory_before.get('available_quantity', 0)
        print(f"   Initial inventory: {initial_quantity}")
        
        # Create another booking that should be pending
        booking_data = {
            "client_id": self.test_client_id,
            "stock_id": self.test_stock_id,
            "quantity": 5,
            "buying_price": 50.0,
            "booking_date": "2024-01-17",
            "status": "open"
        }
        
        success, booking_response = self.run_test(
            "Create Pending Booking",
            "POST",
            "bookings",
            200,
            data=booking_data,
            token=self.admin_token
        )
        
        if not success:
            return False
            
        pending_booking_id = booking_response['id']
        
        # Check inventory after creating pending booking (should be unchanged)
        success, inventory_after_pending = self.run_test(
            "Get Inventory After Pending Booking",
            "GET",
            f"inventory/{self.test_stock_id}",
            200,
            token=self.admin_token
        )
        
        if not success:
            return False
            
        quantity_after_pending = inventory_after_pending.get('available_quantity', 0)
        print(f"   Inventory after pending booking: {quantity_after_pending}")
        
        # Inventory should be unchanged for pending booking
        if quantity_after_pending != initial_quantity:
            print(f"   ❌ Inventory changed before approval: {initial_quantity} -> {quantity_after_pending}")
            return False
        
        # Now approve the booking
        success, approval_response = self.run_test(
            "Approve Pending Booking",
            "PUT",
            f"bookings/{pending_booking_id}/approve?approve=true",
            200,
            token=self.pe_desk_token
        )
        
        if not success:
            return False
        
        # Check inventory after approval (should be reduced)
        success, inventory_after_approval = self.run_test(
            "Get Inventory After Approval",
            "GET",
            f"inventory/{self.test_stock_id}",
            200,
            token=self.admin_token
        )
        
        if success:
            quantity_after_approval = inventory_after_approval.get('available_quantity', 0)
            print(f"   Inventory after approval: {quantity_after_approval}")
            expected_quantity = initial_quantity - 5  # Should be reduced by booking quantity
            return quantity_after_approval == expected_quantity
        
        return False

    def test_client_creation_with_new_fields(self):
        """Test client creation with new fields (address, pin_code, mobile, bank_accounts)"""
        client_data = {
            "name": "Test Client Enhanced",
            "email": "testclient@example.com",
            "phone": "9876543210",
            "mobile": "9876543211",
            "pan_number": "ABCDE1234F",
            "dp_id": "12345678",
            "address": "123 Test Street, Test City, Test State",
            "pin_code": "123456",
            "bank_accounts": [
                {
                    "bank_name": "Test Bank 1",
                    "account_number": "1234567890",
                    "ifsc_code": "TEST0001234",
                    "branch_name": "Test Branch 1",
                    "account_holder_name": "Test Client Enhanced",
                    "source": "manual"
                }
            ],
            "is_vendor": False
        }
        
        success, response = self.run_test(
            "Create Client with New Fields",
            "POST",
            "clients",
            200,
            data=client_data,
            token=self.admin_token
        )
        
        if success:
            self.test_client_id = response['id']
            print(f"   Client ID: {self.test_client_id}")
            return True
        return False

def main():
    print("🚀 Starting SMIFS Share Booking System - New Features Test")
    print("Testing: Domain restriction, Audit logs, Booking approval workflow")
    print("=" * 70)
    
    tester = SMIFSShareBookingTester()
    
    # Test sequence for NEW features
    tests = [
        ("Admin Login (PE Desk)", tester.test_admin_login),
        ("Domain Restriction - Invalid Domain", tester.test_domain_restriction_invalid),
        ("Domain Restriction - Valid @smifs.com", tester.test_domain_restriction_valid),
        ("Audit Logs - Admin Access", tester.test_audit_logs_admin_access),
        ("Audit Logs - Employee Denied", tester.test_audit_logs_employee_denied),
        ("Create Test Data", tester.test_create_test_data),
        ("Booking Requires PE Desk Approval", tester.test_booking_requires_approval),
        ("Pending Bookings - PE Desk Only", tester.test_pending_bookings_pe_desk_only),
        ("Pending Bookings - Employee Denied", tester.test_pending_bookings_employee_denied),
        ("Booking Approval - PE Desk Only", tester.test_booking_approval_pe_desk_only),
        ("Booking Approval - Employee Denied", tester.test_booking_approval_employee_denied),
        ("Inventory Not Adjusted Until Approved", tester.test_inventory_not_adjusted_until_approved),
    ]
    
    failed_tests = []
    
    for test_name, test_func in tests:
        try:
            if not test_func():
                failed_tests.append(test_name)
        except Exception as e:
            print(f"❌ {test_name} - Exception: {str(e)}")
            failed_tests.append(test_name)
    
    # Print results
    print("\n" + "=" * 70)
    print(f"📊 Test Results: {tester.tests_passed}/{tester.tests_run} passed")
    
    if failed_tests:
        print(f"\n❌ Failed Tests ({len(failed_tests)}):")
        for test in failed_tests:
            print(f"   - {test}")
    else:
        print("\n✅ All tests passed!")
    
    print("\n🎯 NEW Features Tested:")
    print("   ✓ Registration domain restriction (@smifs.com only)")
    print("   ✓ Registration creates Employee role (4)")
    print("   ✓ Audit log API endpoints (admin only)")
    print("   ✓ Booking creation requires PE Desk approval")
    print("   ✓ Booking approval endpoint (PE Desk only)")
    print("   ✓ Pending bookings endpoint (PE Desk only)")
    print("   ✓ Inventory NOT adjusted until booking approved")
    
    return 0 if len(failed_tests) == 0 else 1

if __name__ == "__main__":
    sys.exit(main())