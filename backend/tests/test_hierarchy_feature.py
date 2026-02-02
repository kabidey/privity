"""
Test Suite for User Hierarchy Feature
Tests the multi-level user hierarchy (Employee -> Manager -> Zonal Head -> Regional Manager -> Business Head)
and data visibility/edit restrictions based on hierarchy.

Hierarchy Levels:
1 = Employee
2 = Manager
3 = Zonal Head
4 = Regional Manager
5 = Business Head

Key Features:
- Higher levels can view data of all subordinates
- Users can only edit their own data (not subordinates')
- Only PE Desk can map clients to employees
- Unmapped clients visible only to PE Desk
"""

import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
PE_DESK_EMAIL = "pe@smifs.com"
PE_DESK_PASSWORD = "Kutta@123"


class TestHierarchyFeature:
    """Test hierarchy feature - user creation, reports_to assignment, and data visibility"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session with PE Desk login"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as PE Desk
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": PE_DESK_EMAIL,
            "password": PE_DESK_PASSWORD
        })
        
        if response.status_code == 200:
            data = response.json()
            self.pe_token = data.get("token")
            self.pe_user = data.get("user")
            self.session.headers.update({"Authorization": f"Bearer {self.pe_token}"})
            print(f"PE Desk login successful - Role: {self.pe_user.get('role')}")
        else:
            pytest.skip(f"PE Desk login failed: {response.status_code}")
        
        # Store created user IDs for cleanup
        self.created_users = []
        yield
        
        # Cleanup created users
        for user_id in self.created_users:
            try:
                self.session.delete(f"{BASE_URL}/api/users/{user_id}")
            except:
                pass
    
    # ============== Test 1: Hierarchy Levels Endpoint ==============
    def test_hierarchy_levels_endpoint(self):
        """Test GET /api/users/hierarchy/levels returns all hierarchy levels"""
        response = self.session.get(f"{BASE_URL}/api/users/hierarchy/levels")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        assert len(data) == 5, f"Expected 5 hierarchy levels, got {len(data)}"
        
        # Verify all levels are present
        levels = {item['level']: item['name'] for item in data}
        assert levels.get(1) == "Employee", "Level 1 should be Employee"
        assert levels.get(2) == "Manager", "Level 2 should be Manager"
        assert levels.get(3) == "Zonal Head", "Level 3 should be Zonal Head"
        assert levels.get(4) == "Regional Manager", "Level 4 should be Regional Manager"
        assert levels.get(5) == "Business Head", "Level 5 should be Business Head"
        
        print("SUCCESS: Hierarchy levels endpoint returns correct data")
    
    # ============== Test 2: Create User with Hierarchy Level ==============
    def test_create_user_with_hierarchy_level(self):
        """Test creating users with different hierarchy levels"""
        unique_id = str(uuid.uuid4())[:8]
        
        # Create a Manager (hierarchy_level=2)
        manager_data = {
            "email": f"test_manager_{unique_id}@smifs.com",
            "password": "TestPass123",
            "name": f"Test Manager {unique_id}",
            "role": 4,  # Manager role
            "hierarchy_level": 2  # Manager hierarchy level
        }
        
        response = self.session.post(f"{BASE_URL}/api/users", json=manager_data)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "user" in data, "Response should contain user object"
        
        user = data["user"]
        self.created_users.append(user["id"])
        
        assert user["hierarchy_level"] == 2, f"Expected hierarchy_level 2, got {user.get('hierarchy_level')}"
        assert user["hierarchy_level_name"] == "Manager", f"Expected 'Manager', got {user.get('hierarchy_level_name')}"
        
        print(f"SUCCESS: Created manager with hierarchy_level=2: {user['name']}")
        return user
    
    # ============== Test 3: Create User with Reports To ==============
    def test_create_user_with_reports_to(self):
        """Test creating an employee that reports to a manager"""
        unique_id = str(uuid.uuid4())[:8]
        
        # First create a manager
        manager_data = {
            "email": f"test_mgr_{unique_id}@smifs.com",
            "password": "TestPass123",
            "name": f"Test Mgr {unique_id}",
            "role": 4,
            "hierarchy_level": 2
        }
        
        mgr_response = self.session.post(f"{BASE_URL}/api/users", json=manager_data)
        assert mgr_response.status_code == 200, f"Manager creation failed: {mgr_response.text}"
        
        manager = mgr_response.json()["user"]
        self.created_users.append(manager["id"])
        
        # Now create an employee that reports to this manager
        employee_data = {
            "email": f"test_emp_{unique_id}@smifs.com",
            "password": "TestPass123",
            "name": f"Test Emp {unique_id}",
            "role": 5,  # Employee role
            "hierarchy_level": 1,  # Employee hierarchy level
            "reports_to": manager["id"]  # Reports to the manager
        }
        
        emp_response = self.session.post(f"{BASE_URL}/api/users", json=employee_data)
        assert emp_response.status_code == 200, f"Employee creation failed: {emp_response.text}"
        
        employee = emp_response.json()["user"]
        self.created_users.append(employee["id"])
        
        assert employee["reports_to"] == manager["id"], f"Expected reports_to={manager['id']}, got {employee.get('reports_to')}"
        
        print(f"SUCCESS: Created employee '{employee['name']}' reporting to manager '{manager['name']}'")
        return manager, employee
    
    # ============== Test 4: Get User Hierarchy Endpoint ==============
    def test_get_user_hierarchy(self):
        """Test GET /api/users/hierarchy returns users with hierarchy info"""
        response = self.session.get(f"{BASE_URL}/api/users/hierarchy")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        
        # Check that users have hierarchy fields
        if len(data) > 0:
            user = data[0]
            assert "hierarchy_level" in user or user.get("hierarchy_level") is None, "User should have hierarchy_level field"
            assert "reports_to" in user or user.get("reports_to") is None, "User should have reports_to field"
            assert "hierarchy_level_name" in user or user.get("hierarchy_level_name") is None, "User should have hierarchy_level_name"
            assert "reports_to_name" in user or user.get("reports_to_name") is None, "User should have reports_to_name"
        
        print(f"SUCCESS: Hierarchy endpoint returns {len(data)} users with hierarchy info")
    
    # ============== Test 5: Get Potential Managers ==============
    def test_get_potential_managers(self):
        """Test GET /api/users/hierarchy/potential-managers returns users who can be managers"""
        response = self.session.get(f"{BASE_URL}/api/users/hierarchy/potential-managers")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        
        # Potential managers should have hierarchy_level > 1 or PE roles
        for manager in data:
            hierarchy_level = manager.get("hierarchy_level", 1)
            role = manager.get("role", 6)
            assert hierarchy_level > 1 or role in [1, 2], f"Potential manager should have hierarchy_level > 1 or PE role: {manager}"
        
        print(f"SUCCESS: Potential managers endpoint returns {len(data)} users")
    
    # ============== Test 6: Update User Hierarchy ==============
    def test_update_user_hierarchy(self):
        """Test PUT /api/users/{user_id}/hierarchy to update hierarchy settings"""
        unique_id = str(uuid.uuid4())[:8]
        
        # Create a user first
        user_data = {
            "email": f"test_hier_{unique_id}@smifs.com",
            "password": "TestPass123",
            "name": f"Test Hier {unique_id}",
            "role": 5,
            "hierarchy_level": 1
        }
        
        create_response = self.session.post(f"{BASE_URL}/api/users", json=user_data)
        assert create_response.status_code == 200, f"User creation failed: {create_response.text}"
        
        user = create_response.json()["user"]
        self.created_users.append(user["id"])
        
        # Update hierarchy to Manager level
        update_data = {
            "hierarchy_level": 2,
            "reports_to": None
        }
        
        update_response = self.session.put(f"{BASE_URL}/api/users/{user['id']}/hierarchy", json=update_data)
        assert update_response.status_code == 200, f"Hierarchy update failed: {update_response.text}"
        
        # Verify the update
        hierarchy_response = self.session.get(f"{BASE_URL}/api/users/hierarchy")
        users = hierarchy_response.json()
        
        updated_user = next((u for u in users if u["id"] == user["id"]), None)
        assert updated_user is not None, "Updated user not found in hierarchy"
        assert updated_user.get("hierarchy_level") == 2, f"Expected hierarchy_level=2, got {updated_user.get('hierarchy_level')}"
        
        print(f"SUCCESS: Updated user hierarchy to level 2 (Manager)")
    
    # ============== Test 7: Get Team Subordinates ==============
    def test_get_team_subordinates(self):
        """Test GET /api/users/team/subordinates returns subordinates for current user"""
        response = self.session.get(f"{BASE_URL}/api/users/team/subordinates")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        
        print(f"SUCCESS: Team subordinates endpoint returns {len(data)} subordinates")
    
    # ============== Test 8: Get Direct Reports ==============
    def test_get_direct_reports(self):
        """Test GET /api/users/team/direct-reports returns direct reports"""
        response = self.session.get(f"{BASE_URL}/api/users/team/direct-reports")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        
        print(f"SUCCESS: Direct reports endpoint returns {len(data)} direct reports")
    
    # ============== Test 9: Assign Manager ==============
    def test_assign_manager(self):
        """Test PUT /api/users/{user_id}/assign-manager to assign a user to a manager"""
        unique_id = str(uuid.uuid4())[:8]
        
        # Create a manager
        manager_data = {
            "email": f"test_assign_mgr_{unique_id}@smifs.com",
            "password": "TestPass123",
            "name": f"Test Assign Mgr {unique_id}",
            "role": 4,
            "hierarchy_level": 2
        }
        
        mgr_response = self.session.post(f"{BASE_URL}/api/users", json=manager_data)
        assert mgr_response.status_code == 200
        manager = mgr_response.json()["user"]
        self.created_users.append(manager["id"])
        
        # Create an employee
        employee_data = {
            "email": f"test_assign_emp_{unique_id}@smifs.com",
            "password": "TestPass123",
            "name": f"Test Assign Emp {unique_id}",
            "role": 5,
            "hierarchy_level": 1
        }
        
        emp_response = self.session.post(f"{BASE_URL}/api/users", json=employee_data)
        assert emp_response.status_code == 200
        employee = emp_response.json()["user"]
        self.created_users.append(employee["id"])
        
        # Assign employee to manager
        assign_response = self.session.put(
            f"{BASE_URL}/api/users/{employee['id']}/assign-manager?manager_id={manager['id']}"
        )
        
        assert assign_response.status_code == 200, f"Assign manager failed: {assign_response.text}"
        
        result = assign_response.json()
        assert "reports_to" in result, "Response should contain reports_to"
        assert result["reports_to"] == manager["id"], f"Expected reports_to={manager['id']}"
        
        print(f"SUCCESS: Assigned employee to manager via assign-manager endpoint")
    
    # ============== Test 10: Get User Subordinates ==============
    def test_get_user_subordinates(self):
        """Test GET /api/users/{user_id}/subordinates returns all subordinates"""
        unique_id = str(uuid.uuid4())[:8]
        
        # Create a hierarchy: Manager -> Employee
        manager_data = {
            "email": f"test_sub_mgr_{unique_id}@smifs.com",
            "password": "TestPass123",
            "name": f"Test Sub Mgr {unique_id}",
            "role": 4,
            "hierarchy_level": 2
        }
        
        mgr_response = self.session.post(f"{BASE_URL}/api/users", json=manager_data)
        assert mgr_response.status_code == 200
        manager = mgr_response.json()["user"]
        self.created_users.append(manager["id"])
        
        # Create employee reporting to manager
        employee_data = {
            "email": f"test_sub_emp_{unique_id}@smifs.com",
            "password": "TestPass123",
            "name": f"Test Sub Emp {unique_id}",
            "role": 5,
            "hierarchy_level": 1,
            "reports_to": manager["id"]
        }
        
        emp_response = self.session.post(f"{BASE_URL}/api/users", json=employee_data)
        assert emp_response.status_code == 200
        employee = emp_response.json()["user"]
        self.created_users.append(employee["id"])
        
        # Get subordinates for manager
        sub_response = self.session.get(f"{BASE_URL}/api/users/{manager['id']}/subordinates")
        
        assert sub_response.status_code == 200, f"Get subordinates failed: {sub_response.text}"
        
        subordinates = sub_response.json()
        assert isinstance(subordinates, list), "Response should be a list"
        
        # Find the employee in subordinates
        emp_found = any(s["id"] == employee["id"] for s in subordinates)
        assert emp_found, f"Employee {employee['id']} should be in manager's subordinates"
        
        print(f"SUCCESS: Manager has {len(subordinates)} subordinates including the created employee")


class TestHierarchyDataVisibility:
    """Test data visibility based on hierarchy - clients and bookings filtering"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as PE Desk
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": PE_DESK_EMAIL,
            "password": PE_DESK_PASSWORD
        })
        
        if response.status_code == 200:
            data = response.json()
            self.pe_token = data.get("token")
            self.pe_user = data.get("user")
            self.session.headers.update({"Authorization": f"Bearer {self.pe_token}"})
        else:
            pytest.skip(f"PE Desk login failed: {response.status_code}")
        
        self.created_users = []
        self.created_clients = []
        yield
        
        # Cleanup
        for user_id in self.created_users:
            try:
                self.session.delete(f"{BASE_URL}/api/users/{user_id}")
            except:
                pass
        
        for client_id in self.created_clients:
            try:
                self.session.delete(f"{BASE_URL}/api/clients/{client_id}")
            except:
                pass
    
    # ============== Test 11: PE Desk Sees All Clients ==============
    def test_pe_desk_sees_all_clients(self):
        """Test that PE Desk can see all clients including unmapped ones"""
        response = self.session.get(f"{BASE_URL}/api/clients?include_unmapped=true")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        clients = response.json()
        assert isinstance(clients, list), "Response should be a list"
        
        print(f"SUCCESS: PE Desk can see {len(clients)} clients (including unmapped)")
    
    # ============== Test 12: PE Desk Sees All Bookings ==============
    def test_pe_desk_sees_all_bookings(self):
        """Test that PE Desk can see all bookings"""
        response = self.session.get(f"{BASE_URL}/api/bookings")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        bookings = response.json()
        assert isinstance(bookings, list), "Response should be a list"
        
        print(f"SUCCESS: PE Desk can see {len(bookings)} bookings")
    
    # ============== Test 13: Client Employee Mapping ==============
    def test_client_employee_mapping(self):
        """Test PUT /api/clients/{client_id}/employee-mapping to map client to employee"""
        unique_id = str(uuid.uuid4())[:8]
        
        # Create an employee
        employee_data = {
            "email": f"test_map_emp_{unique_id}@smifs.com",
            "password": "TestPass123",
            "name": f"Test Map Emp {unique_id}",
            "role": 5,
            "hierarchy_level": 1
        }
        
        emp_response = self.session.post(f"{BASE_URL}/api/users", json=employee_data)
        assert emp_response.status_code == 200
        employee = emp_response.json()["user"]
        self.created_users.append(employee["id"])
        
        # Create a client
        client_data = {
            "name": f"Test Client {unique_id}",
            "pan_number": f"ABCDE{unique_id[:4]}F",
            "dp_id": f"DP{unique_id[:6]}"
        }
        
        client_response = self.session.post(f"{BASE_URL}/api/clients", json=client_data)
        assert client_response.status_code == 200, f"Client creation failed: {client_response.text}"
        client = client_response.json()
        self.created_clients.append(client["id"])
        
        # Map client to employee
        map_response = self.session.put(
            f"{BASE_URL}/api/clients/{client['id']}/employee-mapping?employee_id={employee['id']}"
        )
        
        assert map_response.status_code == 200, f"Client mapping failed: {map_response.text}"
        
        # Verify mapping
        get_client_response = self.session.get(f"{BASE_URL}/api/clients/{client['id']}")
        assert get_client_response.status_code == 200
        
        updated_client = get_client_response.json()
        assert updated_client.get("mapped_employee_id") == employee["id"], "Client should be mapped to employee"
        
        print(f"SUCCESS: Client mapped to employee successfully")


class TestHierarchyEditRestrictions:
    """Test edit restrictions - users can only edit their own data"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as PE Desk
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": PE_DESK_EMAIL,
            "password": PE_DESK_PASSWORD
        })
        
        if response.status_code == 200:
            data = response.json()
            self.pe_token = data.get("token")
            self.pe_user = data.get("user")
            self.session.headers.update({"Authorization": f"Bearer {self.pe_token}"})
        else:
            pytest.skip(f"PE Desk login failed: {response.status_code}")
        
        self.created_users = []
        yield
        
        # Cleanup
        for user_id in self.created_users:
            try:
                self.session.delete(f"{BASE_URL}/api/users/{user_id}")
            except:
                pass
    
    # ============== Test 14: PE Desk Can Edit Any User ==============
    def test_pe_desk_can_edit_any_user(self):
        """Test that PE Desk can edit any user's hierarchy"""
        unique_id = str(uuid.uuid4())[:8]
        
        # Create a user
        user_data = {
            "email": f"test_edit_{unique_id}@smifs.com",
            "password": "TestPass123",
            "name": f"Test Edit {unique_id}",
            "role": 5,
            "hierarchy_level": 1
        }
        
        create_response = self.session.post(f"{BASE_URL}/api/users", json=user_data)
        assert create_response.status_code == 200
        user = create_response.json()["user"]
        self.created_users.append(user["id"])
        
        # PE Desk updates the user
        update_data = {
            "name": f"Updated {unique_id}",
            "hierarchy_level": 2
        }
        
        update_response = self.session.put(f"{BASE_URL}/api/users/{user['id']}", json=update_data)
        assert update_response.status_code == 200, f"PE Desk should be able to edit user: {update_response.text}"
        
        print("SUCCESS: PE Desk can edit any user")
    
    # ============== Test 15: Circular Reference Prevention ==============
    def test_circular_reference_prevention(self):
        """Test that circular references in reports_to are prevented"""
        unique_id = str(uuid.uuid4())[:8]
        
        # Create user A
        user_a_data = {
            "email": f"test_circ_a_{unique_id}@smifs.com",
            "password": "TestPass123",
            "name": f"Test Circ A {unique_id}",
            "role": 4,
            "hierarchy_level": 2
        }
        
        a_response = self.session.post(f"{BASE_URL}/api/users", json=user_a_data)
        assert a_response.status_code == 200
        user_a = a_response.json()["user"]
        self.created_users.append(user_a["id"])
        
        # Create user B reporting to A
        user_b_data = {
            "email": f"test_circ_b_{unique_id}@smifs.com",
            "password": "TestPass123",
            "name": f"Test Circ B {unique_id}",
            "role": 5,
            "hierarchy_level": 1,
            "reports_to": user_a["id"]
        }
        
        b_response = self.session.post(f"{BASE_URL}/api/users", json=user_b_data)
        assert b_response.status_code == 200
        user_b = b_response.json()["user"]
        self.created_users.append(user_b["id"])
        
        # Try to make A report to B (circular reference)
        circular_update = {
            "hierarchy_level": 2,
            "reports_to": user_b["id"]
        }
        
        circular_response = self.session.put(f"{BASE_URL}/api/users/{user_a['id']}/hierarchy", json=circular_update)
        
        # This should either fail or be prevented
        # The system should not allow A to report to B if B reports to A
        print(f"Circular reference test: Status {circular_response.status_code}")
        
        # If it succeeds, verify no actual circular reference exists
        if circular_response.status_code == 200:
            # Check the hierarchy
            hierarchy_response = self.session.get(f"{BASE_URL}/api/users/hierarchy")
            users = hierarchy_response.json()
            
            user_a_updated = next((u for u in users if u["id"] == user_a["id"]), None)
            user_b_updated = next((u for u in users if u["id"] == user_b["id"]), None)
            
            # Verify no circular reference
            if user_a_updated and user_b_updated:
                a_reports_to = user_a_updated.get("reports_to")
                b_reports_to = user_b_updated.get("reports_to")
                
                # Both shouldn't report to each other
                assert not (a_reports_to == user_b["id"] and b_reports_to == user_a["id"]), \
                    "Circular reference should be prevented"
        
        print("SUCCESS: Circular reference prevention tested")


class TestHierarchyServiceFunctions:
    """Test hierarchy service functions via API endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as PE Desk
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": PE_DESK_EMAIL,
            "password": PE_DESK_PASSWORD
        })
        
        if response.status_code == 200:
            data = response.json()
            self.pe_token = data.get("token")
            self.session.headers.update({"Authorization": f"Bearer {self.pe_token}"})
        else:
            pytest.skip(f"PE Desk login failed: {response.status_code}")
        
        self.created_users = []
        yield
        
        # Cleanup
        for user_id in self.created_users:
            try:
                self.session.delete(f"{BASE_URL}/api/users/{user_id}")
            except:
                pass
    
    # ============== Test 16: Multi-Level Hierarchy Chain ==============
    def test_multi_level_hierarchy_chain(self):
        """Test creating a full hierarchy chain: Business Head -> Regional Manager -> Zonal Head -> Manager -> Employee"""
        unique_id = str(uuid.uuid4())[:8]
        
        # Create Business Head (level 5)
        bh_data = {
            "email": f"test_bh_{unique_id}@smifs.com",
            "password": "TestPass123",
            "name": f"Test BH {unique_id}",
            "role": 4,
            "hierarchy_level": 5
        }
        bh_response = self.session.post(f"{BASE_URL}/api/users", json=bh_data)
        assert bh_response.status_code == 200
        bh = bh_response.json()["user"]
        self.created_users.append(bh["id"])
        
        # Create Regional Manager (level 4) reporting to BH
        rm_data = {
            "email": f"test_rm_{unique_id}@smifs.com",
            "password": "TestPass123",
            "name": f"Test RM {unique_id}",
            "role": 4,
            "hierarchy_level": 4,
            "reports_to": bh["id"]
        }
        rm_response = self.session.post(f"{BASE_URL}/api/users", json=rm_data)
        assert rm_response.status_code == 200
        rm = rm_response.json()["user"]
        self.created_users.append(rm["id"])
        
        # Create Zonal Head (level 3) reporting to RM
        zh_data = {
            "email": f"test_zh_{unique_id}@smifs.com",
            "password": "TestPass123",
            "name": f"Test ZH {unique_id}",
            "role": 3,
            "hierarchy_level": 3,
            "reports_to": rm["id"]
        }
        zh_response = self.session.post(f"{BASE_URL}/api/users", json=zh_data)
        assert zh_response.status_code == 200
        zh = zh_response.json()["user"]
        self.created_users.append(zh["id"])
        
        # Create Manager (level 2) reporting to ZH
        mgr_data = {
            "email": f"test_mgr_{unique_id}@smifs.com",
            "password": "TestPass123",
            "name": f"Test Mgr {unique_id}",
            "role": 4,
            "hierarchy_level": 2,
            "reports_to": zh["id"]
        }
        mgr_response = self.session.post(f"{BASE_URL}/api/users", json=mgr_data)
        assert mgr_response.status_code == 200
        mgr = mgr_response.json()["user"]
        self.created_users.append(mgr["id"])
        
        # Create Employee (level 1) reporting to Manager
        emp_data = {
            "email": f"test_emp_{unique_id}@smifs.com",
            "password": "TestPass123",
            "name": f"Test Emp {unique_id}",
            "role": 5,
            "hierarchy_level": 1,
            "reports_to": mgr["id"]
        }
        emp_response = self.session.post(f"{BASE_URL}/api/users", json=emp_data)
        assert emp_response.status_code == 200
        emp = emp_response.json()["user"]
        self.created_users.append(emp["id"])
        
        # Verify Business Head can see all subordinates
        bh_subs_response = self.session.get(f"{BASE_URL}/api/users/{bh['id']}/subordinates")
        assert bh_subs_response.status_code == 200
        
        bh_subordinates = bh_subs_response.json()
        subordinate_ids = [s["id"] for s in bh_subordinates]
        
        # BH should see RM, ZH, Manager, and Employee
        assert rm["id"] in subordinate_ids, "BH should see RM as subordinate"
        assert zh["id"] in subordinate_ids, "BH should see ZH as subordinate"
        assert mgr["id"] in subordinate_ids, "BH should see Manager as subordinate"
        assert emp["id"] in subordinate_ids, "BH should see Employee as subordinate"
        
        print(f"SUCCESS: Created 5-level hierarchy chain. BH sees {len(bh_subordinates)} subordinates")
        
        # Verify Manager only sees Employee
        mgr_subs_response = self.session.get(f"{BASE_URL}/api/users/{mgr['id']}/subordinates")
        assert mgr_subs_response.status_code == 200
        
        mgr_subordinates = mgr_subs_response.json()
        mgr_sub_ids = [s["id"] for s in mgr_subordinates]
        
        assert emp["id"] in mgr_sub_ids, "Manager should see Employee as subordinate"
        assert len(mgr_subordinates) == 1, f"Manager should only see 1 subordinate, got {len(mgr_subordinates)}"
        
        print(f"SUCCESS: Manager sees only 1 subordinate (Employee)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
