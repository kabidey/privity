import requests
import sys
import json
from datetime import datetime, date

class SMIFSStockManagementTester:
    def __init__(self, base_url="https://privity-share-1.preview.emergentagent.com"):
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

    def test_stock_creation_pe_desk_only(self):
        """Test that only PE Desk can create stocks"""
        stock_data = {
            "symbol": "NEWSTOCK",
            "name": "New Test Stock",
            "exchange": "NSE",
            "isin_number": "INE123A01018",
            "sector": "IT",
            "product": "Equity",
            "face_value": 10.0
        }
        
        # Test employee cannot create stock
        success, response = self.run_test(
            "Stock Creation by Employee (Should Fail)",
            "POST",
            "stocks",
            403,  # Should be forbidden
            data=stock_data,
            token=self.employee_token
        )
        
        if not success:
            return False
        
        # Test PE Desk can create stock
        success, response = self.run_test(
            "Stock Creation by PE Desk",
            "POST",
            "stocks",
            200,
            data=stock_data,
            token=self.pe_desk_token
        )
        
        if success:
            self.test_stock_id = response['id']
            # Verify new fields are present
            required_fields = ['isin_number', 'sector', 'product', 'face_value']
            for field in required_fields:
                if field not in response:
                    print(f"   ❌ Missing field: {field}")
                    return False
                print(f"   ✓ {field}: {response[field]}")
            return True
        return False

    def test_stock_update_pe_desk_only(self):
        """Test that only PE Desk can update stocks"""
        if not self.test_stock_id:
            print("❌ No test stock available")
            return False
            
        update_data = {
            "symbol": "NEWSTOCK",
            "name": "Updated Test Stock",
            "exchange": "BSE",
            "isin_number": "INE123A01018",
            "sector": "Banking",
            "product": "Preference",
            "face_value": 5.0
        }
        
        # Test employee cannot update stock
        success, response = self.run_test(
            "Stock Update by Employee (Should Fail)",
            "PUT",
            f"stocks/{self.test_stock_id}",
            403,  # Should be forbidden
            data=update_data,
            token=self.employee_token
        )
        
        if not success:
            return False
        
        # Test PE Desk can update stock
        success, response = self.run_test(
            "Stock Update by PE Desk",
            "PUT",
            f"stocks/{self.test_stock_id}",
            200,
            data=update_data,
            token=self.pe_desk_token
        )
        
        if success:
            # Verify updated fields
            if response.get('sector') == 'Banking' and response.get('face_value') == 5.0:
                print(f"   ✓ Updated sector: {response['sector']}")
                print(f"   ✓ Updated face_value: {response['face_value']}")
                return True
        return False

    def test_stock_delete_pe_desk_only(self):
        """Test that only PE Desk can delete stocks"""
        # Create a stock to delete
        stock_data = {
            "symbol": "DELSTOCK",
            "name": "Stock to Delete",
            "exchange": "NSE"
        }
        
        success, response = self.run_test(
            "Create Stock for Deletion Test",
            "POST",
            "stocks",
            200,
            data=stock_data,
            token=self.pe_desk_token
        )
        
        if not success:
            return False
            
        delete_stock_id = response['id']
        
        # Test employee cannot delete stock
        success, response = self.run_test(
            "Stock Deletion by Employee (Should Fail)",
            "DELETE",
            f"stocks/{delete_stock_id}",
            403,  # Should be forbidden
            token=self.employee_token
        )
        
        if not success:
            return False
        
        # Test PE Desk can delete stock
        success, response = self.run_test(
            "Stock Deletion by PE Desk",
            "DELETE",
            f"stocks/{delete_stock_id}",
            200,
            token=self.pe_desk_token
        )
        
        return success

    def test_corporate_action_creation_pe_desk_only(self):
        """Test corporate action creation (PE Desk only)"""
        if not self.test_stock_id:
            print("❌ No test stock available")
            return False
            
        action_data = {
            "stock_id": self.test_stock_id,
            "action_type": "stock_split",
            "ratio_from": 1,
            "ratio_to": 2,
            "new_face_value": 5.0,
            "record_date": date.today().strftime("%Y-%m-%d"),
            "notes": "Test stock split 1:2"
        }
        
        # Test employee cannot create corporate action
        success, response = self.run_test(
            "Corporate Action Creation by Employee (Should Fail)",
            "POST",
            "corporate-actions",
            403,  # Should be forbidden
            data=action_data,
            token=self.employee_token
        )
        
        if not success:
            return False
        
        # Test PE Desk can create corporate action
        success, response = self.run_test(
            "Corporate Action Creation by PE Desk",
            "POST",
            "corporate-actions",
            200,
            data=action_data,
            token=self.pe_desk_token
        )
        
        if success:
            self.test_corporate_action_id = response['id']
            # Verify required fields
            required_fields = ['action_type', 'ratio_from', 'ratio_to', 'record_date', 'status']
            for field in required_fields:
                if field not in response:
                    print(f"   ❌ Missing field: {field}")
                    return False
                print(f"   ✓ {field}: {response[field]}")
            return True
        return False

    def test_corporate_action_types(self):
        """Test both stock_split and bonus action types"""
        if not self.test_stock_id:
            print("❌ No test stock available")
            return False
            
        # Test bonus action
        bonus_data = {
            "stock_id": self.test_stock_id,
            "action_type": "bonus",
            "ratio_from": 1,
            "ratio_to": 1,
            "record_date": date.today().strftime("%Y-%m-%d"),
            "notes": "Test bonus 1:1"
        }
        
        success, response = self.run_test(
            "Corporate Action - Bonus Type",
            "POST",
            "corporate-actions",
            200,
            data=bonus_data,
            token=self.pe_desk_token
        )
        
        if success and response.get('action_type') == 'bonus':
            print(f"   ✓ Bonus action created: {response['ratio_from']}:{response['ratio_to']}")
            return True
        return False

    def test_corporate_action_get_pe_desk_only(self):
        """Test GET /api/corporate-actions (PE Desk only)"""
        # Test employee cannot access corporate actions
        success, response = self.run_test(
            "Get Corporate Actions by Employee (Should Fail)",
            "GET",
            "corporate-actions",
            403,  # Should be forbidden
            token=self.employee_token
        )
        
        if not success:
            return False
        
        # Test PE Desk can access corporate actions
        success, response = self.run_test(
            "Get Corporate Actions by PE Desk",
            "GET",
            "corporate-actions",
            200,
            token=self.pe_desk_token
        )
        
        if success:
            print(f"   ✓ Corporate actions count: {len(response)}")
            return True
        return False

    def test_corporate_action_apply_record_date_validation(self):
        """Test corporate action apply with record date validation"""
        if not self.test_corporate_action_id:
            print("❌ No test corporate action available")
            return False
            
        # Test applying action (should work only on record date)
        success, response = self.run_test(
            "Apply Corporate Action (Record Date Validation)",
            "PUT",
            f"corporate-actions/{self.test_corporate_action_id}/apply",
            200,  # Should work since we set today as record date
            token=self.pe_desk_token
        )
        
        if success:
            print(f"   ✓ Action applied: {response.get('message', 'Success')}")
            adjustment_factor = response.get('adjustment_factor')
            if adjustment_factor:
                print(f"   ✓ Adjustment factor: {adjustment_factor}")
            return True
        return False

    def test_stock_model_new_fields(self):
        """Test that stock model has all new fields"""
        success, response = self.run_test(
            "Get Stock with New Fields",
            "GET",
            f"stocks/{self.test_stock_id}",
            200,
            token=self.pe_desk_token
        )
        
        if success:
            new_fields = ['isin_number', 'sector', 'product', 'face_value']
            all_present = True
            for field in new_fields:
                if field in response:
                    print(f"   ✓ {field}: {response[field]}")
                else:
                    print(f"   ❌ Missing field: {field}")
                    all_present = False
            return all_present
        return False

    def test_price_adjustment_calculation(self):
        """Test price adjustment factor calculation for splits and bonuses"""
        # Create test data for price adjustment
        if not self.test_stock_id:
            return False
            
        # Create vendor and purchase for inventory
        vendor_data = {
            "name": "Price Test Vendor",
            "pan_number": "PRICE1234V",
            "dp_id": "PRICE123",
            "is_vendor": True
        }
        
        success, vendor_response = self.run_test(
            "Create Vendor for Price Test",
            "POST",
            "clients",
            200,
            data=vendor_data,
            token=self.pe_desk_token
        )
        
        if not success:
            return False
            
        vendor_id = vendor_response['id']
        
        # Create purchase
        purchase_data = {
            "vendor_id": vendor_id,
            "stock_id": self.test_stock_id,
            "quantity": 50,
            "price_per_unit": 100.0,
            "purchase_date": "2024-01-15"
        }
        
        success, purchase_response = self.run_test(
            "Create Purchase for Price Test",
            "POST",
            "purchases",
            200,
            data=purchase_data,
            token=self.pe_desk_token
        )
        
        if not success:
            return False
        
        # Get initial inventory
        success, inventory_before = self.run_test(
            "Get Inventory Before Corporate Action",
            "GET",
            f"inventory/{self.test_stock_id}",
            200,
            token=self.pe_desk_token
        )
        
        if success:
            initial_price = inventory_before.get('weighted_avg_price', 0)
            print(f"   Initial weighted avg price: ₹{initial_price}")
            
            # Create and apply a 1:2 stock split
            split_data = {
                "stock_id": self.test_stock_id,
                "action_type": "stock_split",
                "ratio_from": 1,
                "ratio_to": 2,
                "new_face_value": 2.5,
                "record_date": date.today().strftime("%Y-%m-%d"),
                "notes": "Price adjustment test split"
            }
            
            success, split_response = self.run_test(
                "Create Split for Price Test",
                "POST",
                "corporate-actions",
                200,
                data=split_data,
                token=self.pe_desk_token
            )
            
            if success:
                split_id = split_response['id']
                
                # Apply the split
                success, apply_response = self.run_test(
                    "Apply Split for Price Test",
                    "PUT",
                    f"corporate-actions/{split_id}/apply",
                    200,
                    token=self.pe_desk_token
                )
                
                if success:
                    adjustment_factor = apply_response.get('adjustment_factor')
                    expected_factor = 1/2  # 1:2 split should halve the price
                    
                    print(f"   Adjustment factor: {adjustment_factor}")
                    print(f"   Expected factor: {expected_factor}")
                    
                    # Check if adjustment factor is correct (within tolerance)
                    return abs(adjustment_factor - expected_factor) < 0.001
        
        return False

def main():
    print("🚀 Starting SMIFS Share Booking System - Stock Management Enhancements Test")
    print("Testing: Stock CRUD restrictions, Corporate Actions, New Stock Fields, Price Adjustments")
    print("=" * 80)
    
    tester = SMIFSStockManagementTester()
    
    # Test sequence for Stock Management enhancements
    tests = [
        ("Admin Login (PE Desk)", tester.test_admin_login),
        ("Employee Registration", tester.test_domain_restriction_valid),
        ("Stock Creation - PE Desk Only", tester.test_stock_creation_pe_desk_only),
        ("Stock Update - PE Desk Only", tester.test_stock_update_pe_desk_only),
        ("Stock Deletion - PE Desk Only", tester.test_stock_delete_pe_desk_only),
        ("Stock Model - New Fields Verification", tester.test_stock_model_new_fields),
        ("Corporate Action Creation - PE Desk Only", tester.test_corporate_action_creation_pe_desk_only),
        ("Corporate Action Types - Stock Split & Bonus", tester.test_corporate_action_types),
        ("Corporate Actions GET - PE Desk Only", tester.test_corporate_action_get_pe_desk_only),
        ("Corporate Action Apply - Record Date Validation", tester.test_corporate_action_apply_record_date_validation),
        ("Price Adjustment Factor Calculation", tester.test_price_adjustment_calculation),
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
    print("\n" + "=" * 80)
    print(f"📊 Test Results: {tester.tests_passed}/{tester.tests_run} passed")
    
    if failed_tests:
        print(f"\n❌ Failed Tests ({len(failed_tests)}):")
        for test in failed_tests:
            print(f"   - {test}")
    else:
        print("\n✅ All tests passed!")
    
    print("\n🎯 Stock Management Enhancements Tested:")
    print("   ✓ Stock creation restricted to PE Desk only (role=1)")
    print("   ✓ Stock model has new fields: isin_number, sector, product, face_value")
    print("   ✓ Corporate action creation POST /api/corporate-actions (PE Desk only)")
    print("   ✓ Corporate action types: stock_split and bonus")
    print("   ✓ Corporate action apply PUT /api/corporate-actions/{id}/apply (record date validation)")
    print("   ✓ Price adjustment factor for splits and bonuses")
    print("   ✓ GET /api/corporate-actions endpoint (PE Desk only)")
    
    return 0 if len(failed_tests) == 0 else 1

if __name__ == "__main__":
    sys.exit(main())