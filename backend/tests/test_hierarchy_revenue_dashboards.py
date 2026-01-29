"""
Test suite for User Hierarchy and Revenue Dashboard features
- User hierarchy management (assign-manager, hierarchy view)
- Employee Revenue Dashboard
- RP Revenue Dashboard
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestHierarchyEndpoints:
    """Tests for user hierarchy management endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup authentication"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "pedesk@smifs.com",
            "password": "Kutta@123"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        self.token = response.json()["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_get_user_hierarchy(self):
        """Test GET /api/users/hierarchy returns users with manager info"""
        response = requests.get(f"{BASE_URL}/api/users/hierarchy", headers=self.headers)
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        
        # Verify structure
        for user in data:
            assert "id" in user
            assert "name" in user
            assert "email" in user
            assert "role" in user
            assert "role_name" in user
            # manager_name should be present (can be null)
            assert "manager_name" in user or user.get("manager_id") is None
    
    def test_get_managers_list_all(self):
        """Test GET /api/users/managers-list returns managers and zonal managers"""
        response = requests.get(f"{BASE_URL}/api/users/managers-list", headers=self.headers)
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        
        # Should contain managers (role 4) and zonal managers (role 3)
        roles = set(m["role"] for m in data)
        assert 3 in roles or 4 in roles, "Should return managers or zonal managers"
        
        for manager in data:
            assert "id" in manager
            assert "name" in manager
            assert "role_name" in manager
    
    def test_get_managers_list_for_employees(self):
        """Test GET /api/users/managers-list?role=5 returns only managers (role 4)"""
        response = requests.get(f"{BASE_URL}/api/users/managers-list?role=5", headers=self.headers)
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        
        # All should be managers (role 4)
        for manager in data:
            assert manager["role"] == 4, f"Expected role 4, got {manager['role']}"
            assert manager["role_name"] == "Manager"
    
    def test_get_managers_list_for_managers(self):
        """Test GET /api/users/managers-list?role=4 returns only zonal managers (role 3)"""
        response = requests.get(f"{BASE_URL}/api/users/managers-list?role=4", headers=self.headers)
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        
        # All should be zonal managers (role 3)
        for manager in data:
            assert manager["role"] == 3, f"Expected role 3, got {manager['role']}"
            assert manager["role_name"] == "Zonal Manager"
    
    def test_assign_manager_to_employee(self):
        """Test PUT /api/users/{user_id}/assign-manager assigns employee to manager"""
        # First get an unassigned employee
        hierarchy_response = requests.get(f"{BASE_URL}/api/users/hierarchy", headers=self.headers)
        users = hierarchy_response.json()
        
        unassigned_employee = None
        manager = None
        
        for user in users:
            if user.get("role") == 5 and not user.get("manager_id"):
                unassigned_employee = user
            if user.get("role") == 4:
                manager = user
        
        if not unassigned_employee or not manager:
            pytest.skip("No unassigned employee or manager found for testing")
        
        # Assign employee to manager
        response = requests.put(
            f"{BASE_URL}/api/users/{unassigned_employee['id']}/assign-manager?manager_id={manager['id']}",
            headers=self.headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert unassigned_employee["name"] in data["message"]
        assert manager["name"] in data["message"]
        
        # Verify assignment
        verify_response = requests.get(f"{BASE_URL}/api/users/hierarchy", headers=self.headers)
        updated_users = verify_response.json()
        
        for user in updated_users:
            if user["id"] == unassigned_employee["id"]:
                assert user.get("manager_id") == manager["id"]
                assert user.get("manager_name") == manager["name"]
                break
        
        # Clean up - remove assignment
        requests.put(
            f"{BASE_URL}/api/users/{unassigned_employee['id']}/assign-manager?manager_id=",
            headers=self.headers
        )
    
    def test_remove_manager_assignment(self):
        """Test PUT /api/users/{user_id}/assign-manager with empty manager_id removes assignment"""
        # Get a user with manager assignment
        hierarchy_response = requests.get(f"{BASE_URL}/api/users/hierarchy", headers=self.headers)
        users = hierarchy_response.json()
        
        assigned_employee = None
        for user in users:
            if user.get("role") == 5 and user.get("manager_id"):
                assigned_employee = user
                break
        
        if not assigned_employee:
            pytest.skip("No assigned employee found for testing")
        
        original_manager_id = assigned_employee["manager_id"]
        
        # Remove assignment
        response = requests.put(
            f"{BASE_URL}/api/users/{assigned_employee['id']}/assign-manager?manager_id=",
            headers=self.headers
        )
        assert response.status_code == 200
        assert "removed" in response.json()["message"].lower()
        
        # Restore assignment
        requests.put(
            f"{BASE_URL}/api/users/{assigned_employee['id']}/assign-manager?manager_id={original_manager_id}",
            headers=self.headers
        )
    
    def test_assign_manager_invalid_hierarchy(self):
        """Test that employees can only be assigned to managers, not zonal managers"""
        hierarchy_response = requests.get(f"{BASE_URL}/api/users/hierarchy", headers=self.headers)
        users = hierarchy_response.json()
        
        employee = None
        zonal_manager = None
        
        for user in users:
            if user.get("role") == 5:
                employee = user
            if user.get("role") == 3:
                zonal_manager = user
        
        if not employee or not zonal_manager:
            pytest.skip("No employee or zonal manager found for testing")
        
        # Try to assign employee directly to zonal manager (should fail)
        response = requests.put(
            f"{BASE_URL}/api/users/{employee['id']}/assign-manager?manager_id={zonal_manager['id']}",
            headers=self.headers
        )
        assert response.status_code == 400
        assert "Employees can only be assigned to Managers" in response.json()["detail"]


class TestEmployeeRevenueDashboard:
    """Tests for Employee Revenue Dashboard endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup authentication"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "pedesk@smifs.com",
            "password": "Kutta@123"
        })
        assert response.status_code == 200
        self.token = response.json()["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_get_employee_revenue_dashboard(self):
        """Test GET /api/employee-revenue returns dashboard data"""
        response = requests.get(f"{BASE_URL}/api/employee-revenue", headers=self.headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "total_employees" in data
        assert "total_revenue" in data
        assert "total_commission" in data
        assert "total_bookings" in data
        assert "employee_details" in data
        
        assert isinstance(data["employee_details"], list)
        
        # Verify employee detail structure
        if data["employee_details"]:
            emp = data["employee_details"][0]
            assert "employee_id" in emp
            assert "employee_name" in emp
            assert "employee_email" in emp
            assert "role" in emp
            assert "role_name" in emp
            assert "total_bookings" in emp
            assert "total_revenue" in emp
    
    def test_get_employee_revenue_with_date_filter(self):
        """Test GET /api/employee-revenue with date filters"""
        response = requests.get(
            f"{BASE_URL}/api/employee-revenue?start_date=2026-01-01&end_date=2026-12-31",
            headers=self.headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "total_employees" in data
        assert "employee_details" in data
    
    def test_get_my_team(self):
        """Test GET /api/my-team returns team members"""
        response = requests.get(f"{BASE_URL}/api/my-team", headers=self.headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "team_members" in data
        assert "total" in data
        assert isinstance(data["team_members"], list)
        
        # Verify team member structure
        if data["team_members"]:
            member = data["team_members"][0]
            assert "id" in member
            assert "name" in member
            assert "email" in member
            assert "role" in member
            assert "role_name" in member


class TestRPRevenueDashboard:
    """Tests for RP Revenue Dashboard endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup authentication"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "pedesk@smifs.com",
            "password": "Kutta@123"
        })
        assert response.status_code == 200
        self.token = response.json()["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_get_rp_revenue_dashboard(self):
        """Test GET /api/rp-revenue returns dashboard data"""
        response = requests.get(f"{BASE_URL}/api/rp-revenue", headers=self.headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "total_rps" in data
        assert "total_revenue" in data
        assert "total_commission" in data
        assert "total_bookings" in data
        assert "rp_details" in data
        
        assert isinstance(data["rp_details"], list)
        
        # Verify RP detail structure
        if data["rp_details"]:
            rp = data["rp_details"][0]
            assert "rp_id" in rp
            assert "rp_code" in rp
            assert "rp_name" in rp
            assert "total_bookings" in rp
            assert "total_revenue" in rp
            assert "total_commission" in rp
    
    def test_get_rp_revenue_with_date_filter(self):
        """Test GET /api/rp-revenue with date filters"""
        response = requests.get(
            f"{BASE_URL}/api/rp-revenue?start_date=2026-01-01&end_date=2026-12-31",
            headers=self.headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "total_rps" in data
        assert "rp_details" in data


class TestUserManagement:
    """Tests for User Management endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup authentication"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "pedesk@smifs.com",
            "password": "Kutta@123"
        })
        assert response.status_code == 200
        self.token = response.json()["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_get_users(self):
        """Test GET /api/users returns all users"""
        response = requests.get(f"{BASE_URL}/api/users", headers=self.headers)
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        
        # Verify user structure
        user = data[0]
        assert "id" in user
        assert "name" in user
        assert "email" in user
        assert "role" in user
        assert "role_name" in user


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
