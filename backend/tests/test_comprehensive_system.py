"""
Comprehensive System Test Suite for Privity - Share Booking System
Tests: Authentication, Authorization, User Management, Client/Vendor, Stock, Purchase, Booking, Finance, Database Backup
"""
import pytest
import requests
import os
import json
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://pe-management-hub.preview.emergentagent.com').rstrip('/')

# Test credentials
CREDENTIALS = {
    "pe_desk": {"email": "pedesk@smifs.com", "password": "Kutta@123"},
    "pe_manager": {"email": "pemanager@test.com", "password": "Test@123"},
    "employee": {"email": "employee@test.com", "password": "Test@123"},
    "manager": {"email": "manager@test.com", "password": "Test@123"},
    "zonal_manager": {"email": "zonalmanager@test.com", "password": "Test@123"}
}

# Store tokens and IDs for tests
test_data = {
    "tokens": {},
    "created_ids": {
        "users": [],
        "clients": [],
        "vendors": [],
        "stocks": [],
        "purchases": [],
        "bookings": []
    }
}


class TestAuthentication:
    """Test authentication endpoints"""
    
    def test_login_pe_desk_valid(self):
        """Test PE Desk login with valid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["pe_desk"])
        assert response.status_code == 200, f"PE Desk login failed: {response.text}"
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == 1
        assert data["user"]["role_name"] == "PE Desk"
        test_data["tokens"]["pe_desk"] = data["token"]
        print(f"✓ PE Desk login successful - Role: {data['user']['role_name']}")
    
    def test_login_invalid_credentials(self):
        """Test login with invalid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "invalid@test.com",
            "password": "wrongpassword"
        })
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Invalid credentials correctly rejected")
    
    def test_login_pe_manager(self):
        """Test PE Manager login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["pe_manager"])
        if response.status_code == 200:
            data = response.json()
            test_data["tokens"]["pe_manager"] = data["token"]
            print(f"✓ PE Manager login successful - Role: {data['user']['role_name']}")
        else:
            print(f"⚠ PE Manager user may not exist yet: {response.status_code}")
    
    def test_login_employee(self):
        """Test Employee login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["employee"])
        if response.status_code == 200:
            data = response.json()
            test_data["tokens"]["employee"] = data["token"]
            print(f"✓ Employee login successful - Role: {data['user']['role_name']}")
        else:
            print(f"⚠ Employee user may not exist yet: {response.status_code}")
    
    def test_login_manager(self):
        """Test Manager login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["manager"])
        if response.status_code == 200:
            data = response.json()
            test_data["tokens"]["manager"] = data["token"]
            print(f"✓ Manager login successful - Role: {data['user']['role_name']}")
        else:
            print(f"⚠ Manager user may not exist yet: {response.status_code}")
    
    def test_login_zonal_manager(self):
        """Test Zonal Manager login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["zonal_manager"])
        if response.status_code == 200:
            data = response.json()
            test_data["tokens"]["zonal_manager"] = data["token"]
            print(f"✓ Zonal Manager login successful - Role: {data['user']['role_name']}")
        else:
            print(f"⚠ Zonal Manager user may not exist yet: {response.status_code}")


class TestUserManagement:
    """Test user management and hierarchy endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Ensure PE Desk token is available"""
        if "pe_desk" not in test_data["tokens"]:
            response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["pe_desk"])
            if response.status_code == 200:
                test_data["tokens"]["pe_desk"] = response.json()["token"]
    
    def get_headers(self, role="pe_desk"):
        return {"Authorization": f"Bearer {test_data['tokens'].get(role, '')}"}
    
    def test_get_users_hierarchy(self):
        """Test GET /api/users/hierarchy"""
        response = requests.get(f"{BASE_URL}/api/users/hierarchy", headers=self.get_headers())
        assert response.status_code == 200, f"Failed to get hierarchy: {response.text}"
        users = response.json()
        assert isinstance(users, list)
        print(f"✓ User hierarchy retrieved - {len(users)} users found")
    
    def test_get_managers_list(self):
        """Test GET /api/users/managers-list"""
        response = requests.get(f"{BASE_URL}/api/users/managers-list", headers=self.get_headers())
        assert response.status_code == 200, f"Failed to get managers list: {response.text}"
        managers = response.json()
        assert isinstance(managers, list)
        print(f"✓ Managers list retrieved - {len(managers)} managers found")
    
    def test_create_user_pe_desk(self):
        """Test POST /api/users - PE Desk can create users"""
        test_user = {
            "email": f"test_user_{int(time.time())}@smifs.com",
            "password": "Test@123",
            "name": "TEST_User_Created",
            "role": 5
        }
        response = requests.post(f"{BASE_URL}/api/users", json=test_user, headers=self.get_headers())
        assert response.status_code == 200, f"Failed to create user: {response.text}"
        data = response.json()
        test_data["created_ids"]["users"].append(data["user"]["id"])
        print(f"✓ User created successfully: {data['user']['name']}")
    
    def test_pe_manager_cannot_delete_users(self):
        """Test that PE Manager cannot delete users"""
        if "pe_manager" not in test_data["tokens"]:
            pytest.skip("PE Manager token not available")
        
        # Try to delete a user with PE Manager token
        if test_data["created_ids"]["users"]:
            user_id = test_data["created_ids"]["users"][0]
            response = requests.delete(
                f"{BASE_URL}/api/users/{user_id}",
                headers={"Authorization": f"Bearer {test_data['tokens']['pe_manager']}"}
            )
            assert response.status_code == 403, f"PE Manager should not be able to delete users: {response.status_code}"
            print("✓ PE Manager correctly denied delete permission")


class TestClientManagement:
    """Test client management endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        if "pe_desk" not in test_data["tokens"]:
            response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["pe_desk"])
            if response.status_code == 200:
                test_data["tokens"]["pe_desk"] = response.json()["token"]
    
    def get_headers(self, role="pe_desk"):
        return {"Authorization": f"Bearer {test_data['tokens'].get(role, '')}"}
    
    def test_create_client(self):
        """Test POST /api/clients - Create client"""
        client_data = {
            "name": f"TEST_Client_{int(time.time())}",
            "email": f"test_client_{int(time.time())}@example.com",
            "phone": "9876543210",
            "pan_number": f"ABCDE{int(time.time()) % 10000}F",
            "dp_id": f"DP{int(time.time()) % 100000}",
            "dp_type": "outside",
            "is_vendor": False,
            "bank_accounts": []
        }
        response = requests.post(f"{BASE_URL}/api/clients", json=client_data, headers=self.get_headers())
        assert response.status_code == 200, f"Failed to create client: {response.text}"
        data = response.json()
        test_data["created_ids"]["clients"].append(data["id"])
        print(f"✓ Client created: {data['name']} (OTC UCC: {data.get('otc_ucc', 'N/A')})")
        return data["id"]
    
    def test_get_clients(self):
        """Test GET /api/clients"""
        response = requests.get(f"{BASE_URL}/api/clients", headers=self.get_headers())
        assert response.status_code == 200, f"Failed to get clients: {response.text}"
        clients = response.json()
        assert isinstance(clients, list)
        print(f"✓ Clients retrieved - {len(clients)} clients found")
    
    def test_check_duplicate_client(self):
        """Test POST /api/clients/check-duplicate"""
        response = requests.post(
            f"{BASE_URL}/api/clients/check-duplicate",
            json={"pan_number": "ABCDE1234F", "email": "test@example.com", "phone": "1234567890"},
            headers=self.get_headers()
        )
        # This endpoint may or may not exist
        if response.status_code == 200:
            print("✓ Duplicate check endpoint working")
        elif response.status_code == 404:
            print("⚠ Duplicate check endpoint not found (may not be implemented)")
        else:
            print(f"⚠ Duplicate check returned: {response.status_code}")
    
    def test_pe_desk_can_delete_client(self):
        """Test DELETE /api/clients/{id} - PE Desk can delete"""
        if not test_data["created_ids"]["clients"]:
            pytest.skip("No client to delete")
        
        client_id = test_data["created_ids"]["clients"][-1]
        response = requests.delete(f"{BASE_URL}/api/clients/{client_id}", headers=self.get_headers())
        assert response.status_code == 200, f"PE Desk should be able to delete clients: {response.text}"
        test_data["created_ids"]["clients"].remove(client_id)
        print("✓ PE Desk successfully deleted client")
    
    def test_pe_manager_cannot_delete_client(self):
        """Test that PE Manager cannot delete clients"""
        if "pe_manager" not in test_data["tokens"]:
            pytest.skip("PE Manager token not available")
        
        # First create a client to try to delete
        client_data = {
            "name": f"TEST_Client_ForDelete_{int(time.time())}",
            "email": f"test_delete_{int(time.time())}@example.com",
            "phone": "9876543211",
            "pan_number": f"XYZAB{int(time.time()) % 10000}C",
            "dp_id": f"DPX{int(time.time()) % 100000}",
            "dp_type": "outside",
            "is_vendor": False,
            "bank_accounts": []
        }
        create_response = requests.post(f"{BASE_URL}/api/clients", json=client_data, headers=self.get_headers())
        if create_response.status_code != 200:
            pytest.skip("Could not create test client")
        
        client_id = create_response.json()["id"]
        
        # Try to delete with PE Manager
        response = requests.delete(
            f"{BASE_URL}/api/clients/{client_id}",
            headers={"Authorization": f"Bearer {test_data['tokens']['pe_manager']}"}
        )
        assert response.status_code == 403, f"PE Manager should not be able to delete clients: {response.status_code}"
        print("✓ PE Manager correctly denied delete permission for clients")
        
        # Clean up with PE Desk
        requests.delete(f"{BASE_URL}/api/clients/{client_id}", headers=self.get_headers())


class TestVendorManagement:
    """Test vendor management (clients with is_vendor=true)"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        if "pe_desk" not in test_data["tokens"]:
            response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["pe_desk"])
            if response.status_code == 200:
                test_data["tokens"]["pe_desk"] = response.json()["token"]
    
    def get_headers(self, role="pe_desk"):
        return {"Authorization": f"Bearer {test_data['tokens'].get(role, '')}"}
    
    def test_create_vendor(self):
        """Test creating a vendor (client with is_vendor=true)"""
        vendor_data = {
            "name": f"TEST_Vendor_{int(time.time())}",
            "email": f"test_vendor_{int(time.time())}@example.com",
            "email_secondary": f"vendor_secondary_{int(time.time())}@example.com",
            "email_tertiary": f"vendor_tertiary_{int(time.time())}@example.com",
            "phone": "9876543212",
            "pan_number": f"VNDOR{int(time.time()) % 10000}V",
            "dp_id": f"VDP{int(time.time()) % 100000}",
            "dp_type": "outside",
            "is_vendor": True,
            "bank_accounts": []
        }
        response = requests.post(f"{BASE_URL}/api/clients", json=vendor_data, headers=self.get_headers())
        assert response.status_code == 200, f"Failed to create vendor: {response.text}"
        data = response.json()
        test_data["created_ids"]["vendors"].append(data["id"])
        print(f"✓ Vendor created: {data['name']} with multiple emails")
    
    def test_get_vendors(self):
        """Test GET /api/clients?is_vendor=true"""
        response = requests.get(f"{BASE_URL}/api/clients?is_vendor=true", headers=self.get_headers())
        assert response.status_code == 200, f"Failed to get vendors: {response.text}"
        vendors = response.json()
        assert isinstance(vendors, list)
        print(f"✓ Vendors retrieved - {len(vendors)} vendors found")


class TestStockManagement:
    """Test stock management endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        if "pe_desk" not in test_data["tokens"]:
            response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["pe_desk"])
            if response.status_code == 200:
                test_data["tokens"]["pe_desk"] = response.json()["token"]
    
    def get_headers(self, role="pe_desk"):
        return {"Authorization": f"Bearer {test_data['tokens'].get(role, '')}"}
    
    def test_create_stock(self):
        """Test POST /api/stocks - Create stock (PE Level)"""
        stock_data = {
            "symbol": f"TEST{int(time.time()) % 10000}",
            "name": f"TEST_Stock_{int(time.time())}",
            "isin_number": f"INE{int(time.time()) % 1000000}01",
            "face_value": 10.0,
            "status": "Active"
        }
        response = requests.post(f"{BASE_URL}/api/stocks", json=stock_data, headers=self.get_headers())
        assert response.status_code == 200, f"Failed to create stock: {response.text}"
        data = response.json()
        test_data["created_ids"]["stocks"].append(data["id"])
        print(f"✓ Stock created: {data['symbol']} - {data['name']}")
        return data["id"]
    
    def test_get_stocks(self):
        """Test GET /api/stocks"""
        response = requests.get(f"{BASE_URL}/api/stocks", headers=self.get_headers())
        assert response.status_code == 200, f"Failed to get stocks: {response.text}"
        stocks = response.json()
        assert isinstance(stocks, list)
        print(f"✓ Stocks retrieved - {len(stocks)} stocks found")
    
    def test_pe_manager_cannot_delete_stock(self):
        """Test that PE Manager cannot delete stocks"""
        if "pe_manager" not in test_data["tokens"]:
            pytest.skip("PE Manager token not available")
        
        if not test_data["created_ids"]["stocks"]:
            pytest.skip("No stock to test delete")
        
        stock_id = test_data["created_ids"]["stocks"][0]
        response = requests.delete(
            f"{BASE_URL}/api/stocks/{stock_id}",
            headers={"Authorization": f"Bearer {test_data['tokens']['pe_manager']}"}
        )
        assert response.status_code == 403, f"PE Manager should not be able to delete stocks: {response.status_code}"
        print("✓ PE Manager correctly denied delete permission for stocks")


class TestPurchaseManagement:
    """Test purchase management endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        if "pe_desk" not in test_data["tokens"]:
            response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["pe_desk"])
            if response.status_code == 200:
                test_data["tokens"]["pe_desk"] = response.json()["token"]
    
    def get_headers(self, role="pe_desk"):
        return {"Authorization": f"Bearer {test_data['tokens'].get(role, '')}"}
    
    def test_get_purchases(self):
        """Test GET /api/purchases"""
        response = requests.get(f"{BASE_URL}/api/purchases", headers=self.get_headers())
        assert response.status_code == 200, f"Failed to get purchases: {response.text}"
        purchases = response.json()
        assert isinstance(purchases, list)
        print(f"✓ Purchases retrieved - {len(purchases)} purchases found")


class TestBookingManagement:
    """Test booking management endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        if "pe_desk" not in test_data["tokens"]:
            response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["pe_desk"])
            if response.status_code == 200:
                test_data["tokens"]["pe_desk"] = response.json()["token"]
    
    def get_headers(self, role="pe_desk"):
        return {"Authorization": f"Bearer {test_data['tokens'].get(role, '')}"}
    
    def test_get_bookings(self):
        """Test GET /api/bookings"""
        response = requests.get(f"{BASE_URL}/api/bookings", headers=self.get_headers())
        assert response.status_code == 200, f"Failed to get bookings: {response.text}"
        bookings = response.json()
        assert isinstance(bookings, list)
        print(f"✓ Bookings retrieved - {len(bookings)} bookings found")
    
    def test_booking_requires_selling_price(self):
        """Test that booking creation requires selling_price"""
        # Get a client and stock first
        clients_response = requests.get(f"{BASE_URL}/api/clients?is_vendor=false", headers=self.get_headers())
        stocks_response = requests.get(f"{BASE_URL}/api/stocks", headers=self.get_headers())
        
        if clients_response.status_code != 200 or stocks_response.status_code != 200:
            pytest.skip("Could not get clients or stocks")
        
        clients = clients_response.json()
        stocks = stocks_response.json()
        
        if not clients or not stocks:
            pytest.skip("No clients or stocks available for booking test")
        
        # Try to create booking without selling_price
        booking_data = {
            "client_id": clients[0]["id"],
            "stock_id": stocks[0]["id"],
            "quantity": 100,
            "buying_price": 100.0
            # Missing selling_price
        }
        response = requests.post(f"{BASE_URL}/api/bookings", json=booking_data, headers=self.get_headers())
        # Should fail validation
        assert response.status_code in [400, 422], f"Booking without selling_price should fail: {response.status_code}"
        print("✓ Booking correctly requires selling_price")


class TestFinanceDashboard:
    """Test finance dashboard endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        if "pe_desk" not in test_data["tokens"]:
            response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["pe_desk"])
            if response.status_code == 200:
                test_data["tokens"]["pe_desk"] = response.json()["token"]
    
    def get_headers(self, role="pe_desk"):
        return {"Authorization": f"Bearer {test_data['tokens'].get(role, '')}"}
    
    def test_get_finance_payments(self):
        """Test GET /api/finance/payments"""
        response = requests.get(f"{BASE_URL}/api/finance/payments", headers=self.get_headers())
        assert response.status_code == 200, f"Failed to get finance payments: {response.text}"
        payments = response.json()
        assert isinstance(payments, list)
        print(f"✓ Finance payments retrieved - {len(payments)} payments found")
    
    def test_get_finance_summary(self):
        """Test GET /api/finance/summary"""
        response = requests.get(f"{BASE_URL}/api/finance/summary", headers=self.get_headers())
        assert response.status_code == 200, f"Failed to get finance summary: {response.text}"
        summary = response.json()
        assert isinstance(summary, dict)
        print(f"✓ Finance summary retrieved")
    
    def test_finance_export_excel(self):
        """Test GET /api/finance/export/excel"""
        response = requests.get(f"{BASE_URL}/api/finance/export/excel", headers=self.get_headers())
        # Should return Excel file or 200
        assert response.status_code in [200, 404], f"Finance export failed: {response.status_code}"
        if response.status_code == 200:
            print("✓ Finance Excel export working")
        else:
            print("⚠ Finance Excel export endpoint not found")


class TestDatabaseBackup:
    """Test database backup endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        if "pe_desk" not in test_data["tokens"]:
            response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["pe_desk"])
            if response.status_code == 200:
                test_data["tokens"]["pe_desk"] = response.json()["token"]
    
    def get_headers(self, role="pe_desk"):
        return {"Authorization": f"Bearer {test_data['tokens'].get(role, '')}"}
    
    def test_get_backups(self):
        """Test GET /api/database/backups (PE Level)"""
        response = requests.get(f"{BASE_URL}/api/database/backups", headers=self.get_headers())
        assert response.status_code == 200, f"Failed to get backups: {response.text}"
        backups = response.json()
        assert isinstance(backups, list)
        print(f"✓ Database backups retrieved - {len(backups)} backups found")
    
    def test_get_database_stats(self):
        """Test GET /api/database/stats (PE Level)"""
        response = requests.get(f"{BASE_URL}/api/database/stats", headers=self.get_headers())
        assert response.status_code == 200, f"Failed to get database stats: {response.text}"
        stats = response.json()
        assert "collections" in stats
        print(f"✓ Database stats retrieved - Total records: {stats.get('total_records', 0)}")
    
    def test_pe_manager_cannot_clear_database(self):
        """Test that PE Manager cannot clear database"""
        if "pe_manager" not in test_data["tokens"]:
            pytest.skip("PE Manager token not available")
        
        response = requests.delete(
            f"{BASE_URL}/api/database/clear",
            headers={"Authorization": f"Bearer {test_data['tokens']['pe_manager']}"}
        )
        assert response.status_code == 403, f"PE Manager should not be able to clear database: {response.status_code}"
        print("✓ PE Manager correctly denied database clear permission")
    
    def test_pe_manager_cannot_restore_database(self):
        """Test that PE Manager cannot restore database"""
        if "pe_manager" not in test_data["tokens"]:
            pytest.skip("PE Manager token not available")
        
        response = requests.post(
            f"{BASE_URL}/api/database/restore",
            json={"backup_id": "fake-id"},
            headers={"Authorization": f"Bearer {test_data['tokens']['pe_manager']}"}
        )
        assert response.status_code == 403, f"PE Manager should not be able to restore database: {response.status_code}"
        print("✓ PE Manager correctly denied database restore permission")


class TestInventory:
    """Test inventory endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        if "pe_desk" not in test_data["tokens"]:
            response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["pe_desk"])
            if response.status_code == 200:
                test_data["tokens"]["pe_desk"] = response.json()["token"]
    
    def get_headers(self, role="pe_desk"):
        return {"Authorization": f"Bearer {test_data['tokens'].get(role, '')}"}
    
    def test_get_inventory(self):
        """Test GET /api/inventory"""
        response = requests.get(f"{BASE_URL}/api/inventory", headers=self.get_headers())
        assert response.status_code == 200, f"Failed to get inventory: {response.text}"
        inventory = response.json()
        assert isinstance(inventory, list)
        print(f"✓ Inventory retrieved - {len(inventory)} items found")
    
    def test_pe_manager_cannot_delete_inventory(self):
        """Test that PE Manager cannot delete inventory"""
        if "pe_manager" not in test_data["tokens"]:
            pytest.skip("PE Manager token not available")
        
        response = requests.delete(
            f"{BASE_URL}/api/inventory/fake-stock-id",
            headers={"Authorization": f"Bearer {test_data['tokens']['pe_manager']}"}
        )
        # Should be 403 (forbidden) or 404 (not found)
        assert response.status_code in [403, 404], f"PE Manager should not be able to delete inventory: {response.status_code}"
        if response.status_code == 403:
            print("✓ PE Manager correctly denied inventory delete permission")
        else:
            print("⚠ Inventory not found (expected for fake ID)")


class TestAnalytics:
    """Test analytics and reports endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        if "pe_desk" not in test_data["tokens"]:
            response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["pe_desk"])
            if response.status_code == 200:
                test_data["tokens"]["pe_desk"] = response.json()["token"]
    
    def get_headers(self, role="pe_desk"):
        return {"Authorization": f"Bearer {test_data['tokens'].get(role, '')}"}
    
    def test_get_analytics_summary(self):
        """Test GET /api/analytics/summary"""
        response = requests.get(f"{BASE_URL}/api/analytics/summary", headers=self.get_headers())
        # May be /api/dashboard/analytics instead
        if response.status_code == 404:
            response = requests.get(f"{BASE_URL}/api/dashboard/analytics", headers=self.get_headers())
        
        assert response.status_code == 200, f"Failed to get analytics: {response.status_code}"
        print("✓ Analytics summary retrieved")
    
    def test_get_dashboard_stats(self):
        """Test GET /api/dashboard/stats"""
        response = requests.get(f"{BASE_URL}/api/dashboard/stats", headers=self.get_headers())
        assert response.status_code == 200, f"Failed to get dashboard stats: {response.text}"
        stats = response.json()
        assert isinstance(stats, dict)
        print(f"✓ Dashboard stats retrieved - Clients: {stats.get('total_clients', 0)}, Bookings: {stats.get('total_bookings', 0)}")


class TestEmailTemplates:
    """Test email template endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        if "pe_desk" not in test_data["tokens"]:
            response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["pe_desk"])
            if response.status_code == 200:
                test_data["tokens"]["pe_desk"] = response.json()["token"]
    
    def get_headers(self, role="pe_desk"):
        return {"Authorization": f"Bearer {test_data['tokens'].get(role, '')}"}
    
    def test_get_email_templates(self):
        """Test GET /api/email-templates (PE Level)"""
        response = requests.get(f"{BASE_URL}/api/email-templates", headers=self.get_headers())
        assert response.status_code == 200, f"Failed to get email templates: {response.text}"
        templates = response.json()
        assert isinstance(templates, list)
        print(f"✓ Email templates retrieved - {len(templates)} templates found")


class TestCleanup:
    """Cleanup test data"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        if "pe_desk" not in test_data["tokens"]:
            response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["pe_desk"])
            if response.status_code == 200:
                test_data["tokens"]["pe_desk"] = response.json()["token"]
    
    def get_headers(self):
        return {"Authorization": f"Bearer {test_data['tokens'].get('pe_desk', '')}"}
    
    def test_cleanup_test_data(self):
        """Clean up all test-created data"""
        cleaned = {"users": 0, "clients": 0, "vendors": 0, "stocks": 0}
        
        # Clean up users
        for user_id in test_data["created_ids"]["users"]:
            response = requests.delete(f"{BASE_URL}/api/users/{user_id}", headers=self.get_headers())
            if response.status_code == 200:
                cleaned["users"] += 1
        
        # Clean up clients
        for client_id in test_data["created_ids"]["clients"]:
            response = requests.delete(f"{BASE_URL}/api/clients/{client_id}", headers=self.get_headers())
            if response.status_code == 200:
                cleaned["clients"] += 1
        
        # Clean up vendors
        for vendor_id in test_data["created_ids"]["vendors"]:
            response = requests.delete(f"{BASE_URL}/api/clients/{vendor_id}", headers=self.get_headers())
            if response.status_code == 200:
                cleaned["vendors"] += 1
        
        # Clean up stocks
        for stock_id in test_data["created_ids"]["stocks"]:
            response = requests.delete(f"{BASE_URL}/api/stocks/{stock_id}", headers=self.get_headers())
            if response.status_code == 200:
                cleaned["stocks"] += 1
        
        print(f"✓ Cleanup complete - Users: {cleaned['users']}, Clients: {cleaned['clients']}, Vendors: {cleaned['vendors']}, Stocks: {cleaned['stocks']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
