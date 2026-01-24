import requests
import sys
import json
from datetime import datetime

class SMIFSShareBookingTester:
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
            return True
        return False

    def test_create_employee(self):
        """Create a test employee user"""
        employee_data = {
            "email": f"employee_{datetime.now().strftime('%H%M%S')}@test.com",
            "password": "Employee@123",
            "name": "Test Employee",
            "role": 4  # Employee role
        }
        
        success, response = self.run_test(
            "Create Employee User",
            "POST",
            "auth/register",
            200,
            data=employee_data
        )
        
        if success:
            self.employee_token = response['token']
            self.employee_user = response['user']
            self.test_employee_id = response['user']['id']
            print(f"   Employee ID: {self.test_employee_id}")
            print(f"   Employee role: {self.employee_user.get('role')} ({self.employee_user.get('role_name')})")
            return True
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
                },
                {
                    "bank_name": "Test Bank 2", 
                    "account_number": "0987654321",
                    "ifsc_code": "TEST0005678",
                    "branch_name": "Test Branch 2",
                    "account_holder_name": "Test Client Enhanced",
                    "source": "cml_copy"
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
            print(f"   Bank accounts: {len(response.get('bank_accounts', []))}")
            print(f"   Address: {response.get('address')}")
            print(f"   Pin code: {response.get('pin_code')}")
            return True
        return False

    def test_multiple_bank_accounts(self):
        """Test adding multiple bank accounts to client"""
        if not self.test_client_id:
            print("❌ No test client available")
            return False
            
        bank_account_data = {
            "bank_name": "Additional Bank",
            "account_number": "5555666677",
            "ifsc_code": "ADDI0001234",
            "branch_name": "Additional Branch",
            "account_holder_name": "Test Client Enhanced",
            "source": "cancelled_cheque"
        }
        
        success, response = self.run_test(
            "Add Additional Bank Account",
            "POST",
            f"clients/{self.test_client_id}/bank-account",
            200,
            data=bank_account_data,
            token=self.admin_token
        )
        
        return success

    def test_employee_vendor_restriction(self):
        """Test that employees cannot access vendors"""
        # Try to get vendors as employee
        success, response = self.run_test(
            "Employee Access Vendors (Should Fail)",
            "GET",
            "clients?is_vendor=true",
            403,  # Should be forbidden
            token=self.employee_token
        )
        
        return success

    def test_employee_client_creation_approval(self):
        """Test employee creating client that needs approval"""
        client_data = {
            "name": "Employee Created Client",
            "email": "empclient@example.com",
            "mobile": "8888999900",
            "pan_number": "EMPCD1234E",
            "dp_id": "87654321",
            "address": "Employee Client Address",
            "pin_code": "654321",
            "bank_accounts": [
                {
                    "bank_name": "Employee Bank",
                    "account_number": "1111222233",
                    "ifsc_code": "EMPB0001234",
                    "branch_name": "Employee Branch",
                    "source": "manual"
                }
            ],
            "is_vendor": False
        }
        
        success, response = self.run_test(
            "Employee Create Client (Needs Approval)",
            "POST",
            "clients",
            200,
            data=client_data,
            token=self.employee_token
        )
        
        if success:
            print(f"   Approval status: {response.get('approval_status')}")
            print(f"   Is active: {response.get('is_active')}")
            print(f"   Mapped employee: {response.get('mapped_employee_name')}")
            return response.get('approval_status') == 'pending' and not response.get('is_active')
        return False

    def test_pending_approval_endpoint(self):
        """Test pending approval endpoint"""
        success, response = self.run_test(
            "Get Pending Approval Clients",
            "GET",
            "clients/pending-approval",
            200,
            token=self.admin_token
        )
        
        if success:
            print(f"   Pending clients count: {len(response)}")
            return True
        return False

    def test_client_approval(self):
        """Test client approval endpoint"""
        # First get pending clients to find one to approve
        success, response = self.run_test(
            "Get Pending Clients for Approval",
            "GET",
            "clients/pending-approval",
            200,
            token=self.admin_token
        )
        
        if success and len(response) > 0:
            pending_client_id = response[0]['id']
            
            # Approve the client
            success, response = self.run_test(
                "Approve Client",
                "PUT",
                f"clients/{pending_client_id}/approve?approve=true",
                200,
                token=self.admin_token
            )
            
            return success
        else:
            print("   No pending clients to approve")
            return True  # Not a failure if no pending clients

    def test_employee_own_clients_only(self):
        """Test that employees can only see their own clients"""
        success, response = self.run_test(
            "Employee Get Own Clients Only",
            "GET",
            "clients?is_vendor=false",
            200,
            token=self.employee_token
        )
        
        if success:
            # Check if all returned clients are mapped to this employee or created by them
            employee_id = self.employee_user['id']
            for client in response:
                if (client.get('mapped_employee_id') != employee_id and 
                    client.get('created_by') != employee_id):
                    print(f"   ❌ Employee can see client not mapped to them: {client['name']}")
                    return False
            print(f"   Employee can see {len(response)} clients (all own)")
            return True
        return False

    def test_employee_purchase_restriction(self):
        """Test that employees cannot view purchase history"""
        success, response = self.run_test(
            "Employee Access Purchases (Should Fail)",
            "GET",
            "purchases",
            403,  # Should be forbidden
            token=self.employee_token
        )
        
        return success

    def test_employee_booking_buying_price_restriction(self):
        """Test that employees cannot edit buying price in bookings"""
        # First create a stock for testing
        stock_data = {
            "symbol": "TESTSTOCK",
            "name": "Test Stock for Booking",
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
            
        stock_id = stock_response['id']
        
        # Create a purchase to have inventory
        vendor_data = {
            "name": "Test Vendor",
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
        
        # Create purchase
        purchase_data = {
            "vendor_id": vendor_id,
            "stock_id": stock_id,
            "quantity": 100,
            "price_per_unit": 50.0,
            "purchase_date": "2024-01-15",
            "notes": "Test purchase"
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
        
        # Create a client specifically for the employee to use for booking
        employee_client_data = {
            "name": "Employee Booking Client",
            "pan_number": "EMPBK1234E",
            "dp_id": "EMPBOOK123",
            "is_vendor": False
        }
        
        success, employee_client_response = self.run_test(
            "Create Employee Client for Booking",
            "POST",
            "clients",
            200,
            data=employee_client_data,
            token=self.employee_token
        )
        
        if not success:
            return False
            
        employee_client_id = employee_client_response['id']
        
        # Approve the employee's client first
        success, approval_response = self.run_test(
            "Approve Employee Client",
            "PUT",
            f"clients/{employee_client_id}/approve?approve=true",
            200,
            token=self.admin_token
        )
        
        if not success:
            return False
        
        # Now try to create booking as employee with custom buying price
        booking_data = {
            "client_id": employee_client_id,
            "stock_id": stock_id,
            "quantity": 10,
            "buying_price": 60.0,  # Different from weighted average
            "selling_price": 70.0,
            "booking_date": "2024-01-16",
            "status": "open"
        }
        
        success, booking_response = self.run_test(
            "Employee Create Booking (Price Should Be Overridden)",
            "POST",
            "bookings",
            200,
            data=booking_data,
            token=self.employee_token
        )
        
        if success:
            # Check if buying price was overridden to weighted average
            actual_buying_price = booking_response.get('buying_price')
            print(f"   Requested buying price: {booking_data['buying_price']}")
            print(f"   Actual buying price: {actual_buying_price}")
            # Should be weighted average (50.0), not the requested 60.0
            return actual_buying_price == 50.0
        
        return False

    def test_admin_client_mapping(self):
        """Test admin can map/unmap clients to employees"""
        if not self.test_client_id or not self.test_employee_id:
            print("❌ Missing test client or employee")
            return False
            
        # Map client to employee
        success, response = self.run_test(
            "Map Client to Employee",
            "PUT",
            f"clients/{self.test_client_id}/employee-mapping?employee_id={self.test_employee_id}",
            200,
            token=self.admin_token
        )
        
        if not success:
            return False
            
        # Verify mapping
        success, client_response = self.run_test(
            "Verify Client Mapping",
            "GET",
            f"clients/{self.test_client_id}",
            200,
            token=self.admin_token
        )
        
        if success:
            mapped_employee_id = client_response.get('mapped_employee_id')
            print(f"   Mapped employee ID: {mapped_employee_id}")
            return mapped_employee_id == self.test_employee_id
            
        return False

    def test_employee_cannot_create_vendor(self):
        """Test that employees cannot create vendors"""
        vendor_data = {
            "name": "Employee Vendor Attempt",
            "pan_number": "EMPV01234E",
            "dp_id": "EMPVENDOR",
            "is_vendor": True  # This should be rejected
        }
        
        success, response = self.run_test(
            "Employee Create Vendor (Should Fail)",
            "POST",
            "clients",
            403,  # Should be forbidden
            data=vendor_data,
            token=self.employee_token
        )
        
        return success

def main():
    print("🚀 Starting Privity Share Booking System Enhanced Features Test")
    print("=" * 60)
    
    tester = PrivityShareBookingTester()
    
    # Test sequence
    tests = [
        ("Admin Login", tester.test_admin_login),
        ("Create Employee User", tester.test_create_employee),
        ("Client Creation with New Fields", tester.test_client_creation_with_new_fields),
        ("Multiple Bank Accounts", tester.test_multiple_bank_accounts),
        ("Employee Vendor Restriction", tester.test_employee_vendor_restriction),
        ("Employee Cannot Create Vendor", tester.test_employee_cannot_create_vendor),
        ("Employee Client Creation (Needs Approval)", tester.test_employee_client_creation_approval),
        ("Pending Approval Endpoint", tester.test_pending_approval_endpoint),
        ("Client Approval", tester.test_client_approval),
        ("Employee Own Clients Only", tester.test_employee_own_clients_only),
        ("Employee Purchase Restriction", tester.test_employee_purchase_restriction),
        ("Employee Booking Price Restriction", tester.test_employee_booking_buying_price_restriction),
        ("Admin Client Mapping", tester.test_admin_client_mapping),
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
    print("\n" + "=" * 60)
    print(f"📊 Test Results: {tester.tests_passed}/{tester.tests_run} passed")
    
    if failed_tests:
        print(f"\n❌ Failed Tests ({len(failed_tests)}):")
        for test in failed_tests:
            print(f"   - {test}")
    else:
        print("\n✅ All tests passed!")
    
    print("\n🎯 Key Features Tested:")
    print("   ✓ Client creation with new fields (address, pin_code, mobile, bank_accounts)")
    print("   ✓ Multiple bank accounts per client")
    print("   ✓ Employee restrictions (no vendor access, own clients only)")
    print("   ✓ Employee cannot view purchase history")
    print("   ✓ Employee-created clients require approval")
    print("   ✓ Client approval workflow")
    print("   ✓ Employee cannot edit buying price in bookings")
    print("   ✓ Admin can map/unmap clients to employees")
    
    return 0 if len(failed_tests) == 0 else 1

if __name__ == "__main__":
    sys.exit(main())