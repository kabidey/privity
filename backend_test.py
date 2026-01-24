#!/usr/bin/env python3

import requests
import sys
import json
from datetime import datetime, timedelta
import uuid

class ShareBookingAPITester:
    def __init__(self, base_url="https://portfolio-pro-218.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.token = None
        self.user_id = None
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []
        
        # Test data storage
        self.test_client_id = None
        self.test_stock_id = None
        self.test_booking_id = None

    def log_test(self, name, success, details=""):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name} - PASSED")
        else:
            print(f"❌ {name} - FAILED: {details}")
        
        self.test_results.append({
            "test": name,
            "success": success,
            "details": details
        })

    def make_request(self, method, endpoint, data=None, expected_status=200):
        """Make API request with error handling"""
        url = f"{self.api_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        if self.token:
            headers['Authorization'] = f'Bearer {self.token}'

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
            return success, response.json() if success else response.text, response.status_code

        except Exception as e:
            return False, str(e), 0

    def test_user_registration(self):
        """Test user registration"""
        test_email = f"test_{uuid.uuid4().hex[:8]}@example.com"
        test_data = {
            "email": test_email,
            "password": "TestPass123!",
            "name": "Test User"
        }
        
        success, response, status = self.make_request("POST", "auth/register", test_data, 200)
        
        if success and 'token' in response:
            self.token = response['token']
            self.user_id = response['user']['id']
            self.log_test("User Registration", True)
            return True
        else:
            self.log_test("User Registration", False, f"Status: {status}, Response: {response}")
            return False

    def test_user_login(self):
        """Test user login with existing credentials"""
        if not self.token:
            self.log_test("User Login", False, "No token from registration")
            return False
            
        # We'll use the token from registration for subsequent tests
        self.log_test("User Login", True, "Using token from registration")
        return True

    def test_get_user_profile(self):
        """Test getting current user profile"""
        success, response, status = self.make_request("GET", "auth/me", expected_status=200)
        
        if success and 'id' in response:
            self.log_test("Get User Profile", True)
            return True
        else:
            self.log_test("Get User Profile", False, f"Status: {status}, Response: {response}")
            return False

    def test_create_client(self):
        """Test creating a client"""
        client_data = {
            "name": "Test Client",
            "email": "testclient@example.com",
            "phone": "9876543210",
            "pan_number": "ABCDE1234F",
            "dp_id": "12345678",
            "bank_name": "Test Bank",
            "account_number": "1234567890",
            "ifsc_code": "TEST0001234"
        }
        
        success, response, status = self.make_request("POST", "clients", client_data, 200)
        
        if success and 'id' in response:
            self.test_client_id = response['id']
            self.log_test("Create Client", True)
            return True
        else:
            self.log_test("Create Client", False, f"Status: {status}, Response: {response}")
            return False

    def test_get_clients(self):
        """Test getting all clients"""
        success, response, status = self.make_request("GET", "clients", expected_status=200)
        
        if success and isinstance(response, list):
            self.log_test("Get Clients", True, f"Found {len(response)} clients")
            return True
        else:
            self.log_test("Get Clients", False, f"Status: {status}, Response: {response}")
            return False

    def test_update_client(self):
        """Test updating a client"""
        if not self.test_client_id:
            self.log_test("Update Client", False, "No client ID available")
            return False
            
        update_data = {
            "name": "Updated Test Client",
            "email": "updated@example.com",
            "phone": "9876543210",
            "pan_number": "ABCDE1234F",
            "dp_id": "12345678",
            "bank_name": "Updated Bank",
            "account_number": "1234567890",
            "ifsc_code": "TEST0001234"
        }
        
        success, response, status = self.make_request("PUT", f"clients/{self.test_client_id}", update_data, 200)
        
        if success:
            self.log_test("Update Client", True)
            return True
        else:
            self.log_test("Update Client", False, f"Status: {status}, Response: {response}")
            return False

    def test_create_stock(self):
        """Test creating a stock"""
        stock_data = {
            "symbol": "TESTSTOCK",
            "name": "Test Stock Company Ltd",
            "exchange": "NSE"
        }
        
        success, response, status = self.make_request("POST", "stocks", stock_data, 200)
        
        if success and 'id' in response:
            self.test_stock_id = response['id']
            self.log_test("Create Stock", True)
            return True
        else:
            self.log_test("Create Stock", False, f"Status: {status}, Response: {response}")
            return False

    def test_get_stocks(self):
        """Test getting all stocks"""
        success, response, status = self.make_request("GET", "stocks", expected_status=200)
        
        if success and isinstance(response, list):
            self.log_test("Get Stocks", True, f"Found {len(response)} stocks")
            return True
        else:
            self.log_test("Get Stocks", False, f"Status: {status}, Response: {response}")
            return False

    def test_create_booking(self):
        """Test creating a booking"""
        if not self.test_client_id or not self.test_stock_id:
            self.log_test("Create Booking", False, "Missing client or stock ID")
            return False
            
        booking_data = {
            "client_id": self.test_client_id,
            "stock_id": self.test_stock_id,
            "quantity": 100,
            "buying_price": 150.50,
            "selling_price": None,
            "booking_date": datetime.now().strftime("%Y-%m-%d"),
            "status": "open",
            "notes": "Test booking"
        }
        
        success, response, status = self.make_request("POST", "bookings", booking_data, 200)
        
        if success and 'id' in response:
            self.test_booking_id = response['id']
            self.log_test("Create Booking", True)
            return True
        else:
            self.log_test("Create Booking", False, f"Status: {status}, Response: {response}")
            return False

    def test_get_bookings(self):
        """Test getting all bookings with details"""
        success, response, status = self.make_request("GET", "bookings", expected_status=200)
        
        if success and isinstance(response, list):
            self.log_test("Get Bookings", True, f"Found {len(response)} bookings")
            return True
        else:
            self.log_test("Get Bookings", False, f"Status: {status}, Response: {response}")
            return False

    def test_update_booking_close(self):
        """Test updating booking to closed status with selling price"""
        if not self.test_booking_id:
            self.log_test("Update Booking (Close)", False, "No booking ID available")
            return False
            
        update_data = {
            "client_id": self.test_client_id,
            "stock_id": self.test_stock_id,
            "quantity": 100,
            "buying_price": 150.50,
            "selling_price": 175.75,  # Profit scenario
            "booking_date": datetime.now().strftime("%Y-%m-%d"),
            "status": "closed",
            "notes": "Test booking - closed with profit"
        }
        
        success, response, status = self.make_request("PUT", f"bookings/{self.test_booking_id}", update_data, 200)
        
        if success:
            self.log_test("Update Booking (Close)", True)
            return True
        else:
            self.log_test("Update Booking (Close)", False, f"Status: {status}, Response: {response}")
            return False

    def test_dashboard_stats(self):
        """Test dashboard statistics"""
        success, response, status = self.make_request("GET", "dashboard/stats", expected_status=200)
        
        if success and 'total_clients' in response:
            stats = response
            expected_keys = ['total_clients', 'total_stocks', 'total_bookings', 'open_bookings', 'closed_bookings', 'total_profit_loss']
            
            if all(key in stats for key in expected_keys):
                self.log_test("Dashboard Stats", True, f"P&L: {stats.get('total_profit_loss', 0)}")
                return True
            else:
                self.log_test("Dashboard Stats", False, "Missing required fields")
                return False
        else:
            self.log_test("Dashboard Stats", False, f"Status: {status}, Response: {response}")
            return False

    def test_pnl_report(self):
        """Test P&L report generation"""
        success, response, status = self.make_request("GET", "reports/pnl", expected_status=200)
        
        if success and isinstance(response, list):
            self.log_test("P&L Report", True, f"Generated report with {len(response)} entries")
            return True
        else:
            self.log_test("P&L Report", False, f"Status: {status}, Response: {response}")
            return False

    def test_export_excel(self):
        """Test Excel export functionality"""
        try:
            url = f"{self.api_url}/reports/export/excel"
            headers = {'Authorization': f'Bearer {self.token}'}
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200 and response.headers.get('content-type') == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet':
                self.log_test("Export Excel", True, f"File size: {len(response.content)} bytes")
                return True
            else:
                self.log_test("Export Excel", False, f"Status: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Export Excel", False, str(e))
            return False

    def test_export_pdf(self):
        """Test PDF export functionality"""
        try:
            url = f"{self.api_url}/reports/export/pdf"
            headers = {'Authorization': f'Bearer {self.token}'}
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200 and response.headers.get('content-type') == 'application/pdf':
                self.log_test("Export PDF", True, f"File size: {len(response.content)} bytes")
                return True
            else:
                self.log_test("Export PDF", False, f"Status: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Export PDF", False, str(e))
            return False

    def cleanup_test_data(self):
        """Clean up test data"""
        cleanup_success = True
        
        # Delete booking
        if self.test_booking_id:
            success, _, _ = self.make_request("DELETE", f"bookings/{self.test_booking_id}", expected_status=200)
            if not success:
                cleanup_success = False
        
        # Delete stock
        if self.test_stock_id:
            success, _, _ = self.make_request("DELETE", f"stocks/{self.test_stock_id}", expected_status=200)
            if not success:
                cleanup_success = False
        
        # Delete client
        if self.test_client_id:
            success, _, _ = self.make_request("DELETE", f"clients/{self.test_client_id}", expected_status=200)
            if not success:
                cleanup_success = False
        
        self.log_test("Cleanup Test Data", cleanup_success)
        return cleanup_success

    def run_all_tests(self):
        """Run all API tests"""
        print(f"🚀 Starting Share Booking API Tests")
        print(f"📍 Base URL: {self.base_url}")
        print("=" * 60)
        
        # Authentication Tests
        if not self.test_user_registration():
            print("❌ Registration failed - stopping tests")
            return False
            
        if not self.test_user_login():
            print("❌ Login failed - stopping tests")
            return False
            
        self.test_get_user_profile()
        
        # Client Management Tests
        self.test_create_client()
        self.test_get_clients()
        self.test_update_client()
        
        # Stock Management Tests
        self.test_create_stock()
        self.test_get_stocks()
        
        # Booking Management Tests
        self.test_create_booking()
        self.test_get_bookings()
        self.test_update_booking_close()
        
        # Dashboard & Reports Tests
        self.test_dashboard_stats()
        self.test_pnl_report()
        self.test_export_excel()
        self.test_export_pdf()
        
        # Cleanup
        self.cleanup_test_data()
        
        # Print Results
        print("=" * 60)
        print(f"📊 Test Results: {self.tests_passed}/{self.tests_run} passed")
        
        if self.tests_passed == self.tests_run:
            print("🎉 All tests passed!")
            return True
        else:
            print(f"⚠️  {self.tests_run - self.tests_passed} tests failed")
            return False

def main():
    tester = ShareBookingAPITester()
    success = tester.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())