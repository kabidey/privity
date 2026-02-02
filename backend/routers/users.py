"""
User management routes
"""
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from datetime import datetime, timezone
import uuid
import bcrypt

from database import db
from config import ROLES, is_pe_level, is_pe_desk_only, can_manage_business_partners
from models import User
from utils.auth import get_current_user, check_permission

router = APIRouter(prefix="/users", tags=["Users"])


# ============== Pydantic Models ==============
class UserCreate(BaseModel):
    email: str
    password: str
    name: str
    role: int = 5  # Default to Employee
    hierarchy_level: int = 1  # Default to Employee level
    reports_to: Optional[str] = None  # Manager's user ID


class UserUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[int] = None
    is_active: Optional[bool] = None
    hierarchy_level: Optional[int] = None
    reports_to: Optional[str] = None


class HierarchyUpdate(BaseModel):
    hierarchy_level: int
    reports_to: Optional[str] = None


# Hierarchy level names
HIERARCHY_LEVELS = {
    1: "Employee",
    2: "Manager",
    3: "Zonal Head",
    4: "Regional Manager",
    5: "Business Head"
}


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


async def enrich_user_with_hierarchy(user: dict) -> dict:
    """Add hierarchy level name and manager name to user dict"""
    hierarchy_level = user.get("hierarchy_level", 1)
    user["hierarchy_level_name"] = HIERARCHY_LEVELS.get(hierarchy_level, "Employee")
    
    reports_to = user.get("reports_to")
    if reports_to:
        manager = await db.users.find_one({"id": reports_to}, {"name": 1})
        user["reports_to_name"] = manager.get("name") if manager else None
    else:
        user["reports_to_name"] = None
    
    return user


# ============== Employee Endpoints (for Partners Desk) ==============
@router.get("/employees")
async def get_employees(current_user: dict = Depends(get_current_user)):
    """Get list of employees for BP linking (PE Level or Partners Desk)"""
    if not can_manage_business_partners(current_user.get("role", 6)):
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Return only employees (roles 3-7) for BP linking
    users = await db.users.find(
        {"role": {"$in": [3, 4, 5, 6, 7]}},
        {"_id": 0, "id": 1, "name": 1, "email": 1, "role": 1}
    ).to_list(1000)
    
    return [{"id": u["id"], "name": u["name"], "email": u["email"], "role": u.get("role", 5), "role_name": ROLES.get(u.get("role", 5), "Employee")} for u in users]


# ============== User Endpoints ==============
@router.get("", response_model=List[User])
async def get_users(current_user: dict = Depends(get_current_user)):
    """Get all users (PE Level)"""
    if not is_pe_level(current_user.get("role", 6)):
        raise HTTPException(status_code=403, detail="Only PE Desk or PE Manager can view users")
    users = await db.users.find({}, {"_id": 0, "password": 0}).to_list(1000)
    
    result = []
    for u in users:
        enriched = await enrich_user_with_hierarchy(u)
        result.append(User(**{
            **enriched, 
            "role_name": ROLES.get(u.get("role", 6), "Viewer"),
            "agreement_accepted": u.get("agreement_accepted", False),
            "agreement_accepted_at": u.get("agreement_accepted_at")
        }))
    return result


@router.post("")
async def create_user(user_data: UserCreate, current_user: dict = Depends(get_current_user)):
    """Create a new user (PE Level)"""
    if not is_pe_level(current_user.get("role", 6)):
        raise HTTPException(status_code=403, detail="Only PE Desk or PE Manager can create users")
    
    # PE Manager cannot create PE Desk or PE Manager users
    if current_user.get("role") == 2 and user_data.role in [1, 2]:
        raise HTTPException(status_code=403, detail="PE Manager cannot create PE Desk or PE Manager users")
    
    # Check if email already exists
    existing = await db.users.find_one({"email": user_data.email.lower()})
    if existing:
        raise HTTPException(status_code=400, detail="User with this email already exists")
    
    # Validate role
    if user_data.role not in ROLES:
        raise HTTPException(status_code=400, detail="Invalid role")
    
    # Create user
    user_id = str(uuid.uuid4())
    user_doc = {
        "id": user_id,
        "email": user_data.email.lower(),
        "password": hash_password(user_data.password),
        "name": user_data.name,
        "role": user_data.role,
        "hierarchy_level": user_data.hierarchy_level,
        "reports_to": user_data.reports_to,
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": current_user["id"]
    }
    
    await db.users.insert_one(user_doc)
    
    return {
        "message": "User created successfully",
        "user": {
            "id": user_id,
            "email": user_data.email.lower(),
            "name": user_data.name,
            "role": user_data.role,
            "role_name": ROLES.get(user_data.role, "Viewer"),
            "hierarchy_level": user_data.hierarchy_level,
            "hierarchy_level_name": HIERARCHY_LEVELS.get(user_data.hierarchy_level, "Employee"),
            "reports_to": user_data.reports_to
        }
    }


@router.put("/{user_id}")
async def update_user(user_id: str, user_data: UserUpdate, current_user: dict = Depends(get_current_user)):
    """Update a user (PE Level)"""
    if not is_pe_level(current_user.get("role", 6)):
        raise HTTPException(status_code=403, detail="Only PE Desk or PE Manager can update users")
    
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Prevent modifying the super admin (pe@smifs.com)
    if user.get("email") == "pe@smifs.com" and current_user.get("email") != "pe@smifs.com":
        raise HTTPException(status_code=403, detail="Cannot modify the super admin account")
    
    # PE Manager cannot modify PE Desk or PE Manager users
    if current_user.get("role") == 2 and user.get("role") in [1, 2]:
        raise HTTPException(status_code=403, detail="PE Manager cannot modify PE Desk or PE Manager users")
    
    update_data = {}
    if user_data.name is not None:
        update_data["name"] = user_data.name
    if user_data.role is not None:
        if user_data.role not in ROLES:
            raise HTTPException(status_code=400, detail="Invalid role")
        # PE Manager cannot promote to PE Desk or PE Manager
        if current_user.get("role") == 2 and user_data.role in [1, 2]:
            raise HTTPException(status_code=403, detail="PE Manager cannot assign PE Desk or PE Manager roles")
        update_data["role"] = user_data.role
    if user_data.is_active is not None:
        update_data["is_active"] = user_data.is_active
    if user_data.hierarchy_level is not None:
        if user_data.hierarchy_level not in HIERARCHY_LEVELS:
            raise HTTPException(status_code=400, detail="Invalid hierarchy level")
        update_data["hierarchy_level"] = user_data.hierarchy_level
    if user_data.reports_to is not None:
        # Validate manager exists (empty string means no manager)
        if user_data.reports_to != "":
            manager = await db.users.find_one({"id": user_data.reports_to})
            if not manager:
                raise HTTPException(status_code=400, detail="Manager not found")
            # Prevent circular reference
            if user_data.reports_to == user_id:
                raise HTTPException(status_code=400, detail="User cannot report to themselves")
        update_data["reports_to"] = user_data.reports_to if user_data.reports_to != "" else None
    
    if update_data:
        update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
        update_data["updated_by"] = current_user["id"]
        await db.users.update_one({"id": user_id}, {"$set": update_data})
    
    return {"message": "User updated successfully"}


@router.put("/{user_id}/role")
async def update_user_role(user_id: str, role: int, current_user: dict = Depends(get_current_user)):
    """Update user role (PE Level)"""
    if not is_pe_level(current_user.get("role", 6)):
        raise HTTPException(status_code=403, detail="Only PE Desk or PE Manager can update user roles")
    
    if role not in ROLES:
        raise HTTPException(status_code=400, detail="Invalid role")
    
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Prevent modifying the super admin
    if user.get("email") == "pe@smifs.com":
        raise HTTPException(status_code=403, detail="Cannot modify the super admin role")
    
    # PE Manager restrictions
    if current_user.get("role") == 2:
        if user.get("role") in [1, 2]:
            raise HTTPException(status_code=403, detail="PE Manager cannot modify PE Desk or PE Manager users")
        if role in [1, 2]:
            raise HTTPException(status_code=403, detail="PE Manager cannot assign PE Desk or PE Manager roles")
    
    result = await db.users.update_one({"id": user_id}, {"$set": {"role": role}})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {"message": "User role updated successfully"}


@router.delete("/{user_id}")
async def delete_user(user_id: str, current_user: dict = Depends(get_current_user)):
    """Delete a user (PE Desk only - deletion restricted)"""
    if not is_pe_desk_only(current_user.get("role", 6)):
        raise HTTPException(status_code=403, detail="Only PE Desk can delete users")
    
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Prevent deleting the super admin
    if user.get("email") == "pe@smifs.com":
        raise HTTPException(status_code=403, detail="Cannot delete the super admin account")
    
    # Prevent self-deletion
    if user_id == current_user["id"]:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    
    await db.users.delete_one({"id": user_id})
    
    return {"message": f"User {user.get('name')} deleted successfully"}


@router.post("/{user_id}/reset-password")
async def reset_user_password(user_id: str, new_password: str, current_user: dict = Depends(get_current_user)):
    """Reset a user's password (PE Level)"""
    if not is_pe_level(current_user.get("role", 6)):
        raise HTTPException(status_code=403, detail="Only PE Desk or PE Manager can reset passwords")
    
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # PE Manager cannot reset passwords for PE Desk or PE Manager
    if current_user.get("role") == 2 and user.get("role") in [1, 2]:
        raise HTTPException(status_code=403, detail="PE Manager cannot reset passwords for PE Desk or PE Manager users")
    
    if len(new_password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    
    await db.users.update_one(
        {"id": user_id},
        {"$set": {
            "password": hash_password(new_password),
            "password_reset_at": datetime.now(timezone.utc).isoformat(),
            "password_reset_by": current_user["id"]
        }}
    )
    
    return {"message": f"Password reset successfully for {user.get('name')}"}


# ============== User Mapping Endpoints ==============
class UserMapping(BaseModel):
    user_id: str
    manager_id: Optional[str] = None


@router.get("/hierarchy")
async def get_user_hierarchy(current_user: dict = Depends(get_current_user)):
    """Get all users with their hierarchy mappings (PE Level or for own subordinates)"""
    user_role = current_user.get("role", 6)
    
    # PE Level can see all users
    if is_pe_level(user_role):
        users = await db.users.find({}, {"_id": 0, "password": 0}).to_list(1000)
    # Manager can see their employees
    elif user_role == 4:
        users = await db.users.find(
            {"$or": [{"id": current_user["id"]}, {"manager_id": current_user["id"]}]},
            {"_id": 0, "password": 0}
        ).to_list(1000)
    # Zonal Manager can see their managers and those managers' employees
    elif user_role == 3:
        # Get direct reports (managers)
        direct_reports = await db.users.find(
            {"manager_id": current_user["id"]},
            {"_id": 0, "password": 0}
        ).to_list(100)
        direct_report_ids = [u["id"] for u in direct_reports]
        
        # Get employees of those managers
        employees = await db.users.find(
            {"manager_id": {"$in": direct_report_ids}},
            {"_id": 0, "password": 0}
        ).to_list(1000)
        
        # Get self
        self_user = await db.users.find_one({"id": current_user["id"]}, {"_id": 0, "password": 0})
        
        users = [self_user] + direct_reports + employees if self_user else direct_reports + employees
    else:
        users = [await db.users.find_one({"id": current_user["id"]}, {"_id": 0, "password": 0})]
        users = [u for u in users if u]
    
    # Add role_name and manager_name to each user
    result = []
    user_map = {u["id"]: u for u in users}
    all_users = await db.users.find({}, {"_id": 0, "id": 1, "name": 1}).to_list(1000)
    all_user_map = {u["id"]: u["name"] for u in all_users}
    
    for user in users:
        user_data = {
            **user,
            "role_name": ROLES.get(user.get("role", 6), "Viewer"),
            "manager_name": all_user_map.get(user.get("manager_id")) if user.get("manager_id") else None
        }
        result.append(user_data)
    
    return result


@router.put("/{user_id}/assign-manager")
async def assign_manager(user_id: str, manager_id: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    """Assign a user to a manager (PE Level only)
    
    Rules:
    - Employee (role 5) can be assigned to Manager (role 4)
    - Manager (role 4) can be assigned to Zonal Manager (role 3)
    """
    if not is_pe_level(current_user.get("role", 6)):
        raise HTTPException(status_code=403, detail="Only PE Desk or PE Manager can assign managers")
    
    # Get the user to be assigned
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # If removing assignment
    if manager_id is None or manager_id == "":
        await db.users.update_one(
            {"id": user_id},
            {"$unset": {"manager_id": ""}}
        )
        return {"message": f"Manager assignment removed for {user['name']}"}
    
    # Get the manager
    manager = await db.users.find_one({"id": manager_id}, {"_id": 0})
    if not manager:
        raise HTTPException(status_code=404, detail="Manager not found")
    
    # Validate hierarchy rules
    user_role = user.get("role", 6)
    manager_role = manager.get("role", 6)
    
    # Employee (5) -> Manager (4)
    if user_role == 5 and manager_role != 4:
        raise HTTPException(status_code=400, detail="Employees can only be assigned to Managers")
    
    # Manager (4) -> Zonal Manager (3)
    if user_role == 4 and manager_role != 3:
        raise HTTPException(status_code=400, detail="Managers can only be assigned to Zonal Managers")
    
    # Zonal Manager (3) -> Cannot be assigned (top of hierarchy below PE)
    if user_role == 3:
        raise HTTPException(status_code=400, detail="Zonal Managers cannot be assigned to other managers")
    
    # PE roles cannot be assigned
    if user_role in [1, 2]:
        raise HTTPException(status_code=400, detail="PE Desk and PE Manager cannot be assigned to managers")
    
    # Prevent self-assignment
    if user_id == manager_id:
        raise HTTPException(status_code=400, detail="Cannot assign user to themselves")
    
    # Update assignment
    await db.users.update_one(
        {"id": user_id},
        {"$set": {"manager_id": manager_id}}
    )
    
    return {
        "message": f"{user['name']} assigned to {manager['name']}",
        "user_id": user_id,
        "manager_id": manager_id
    }


@router.get("/{user_id}/subordinates")
async def get_subordinates(user_id: str, current_user: dict = Depends(get_current_user)):
    """Get all subordinates for a user (direct and indirect)"""
    user_role = current_user.get("role", 6)
    
    # Only allow viewing own subordinates or PE Level can view anyone's
    if not is_pe_level(user_role) and current_user["id"] != user_id:
        raise HTTPException(status_code=403, detail="You can only view your own subordinates")
    
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    target_role = user.get("role", 6)
    
    subordinates = []
    
    # Manager (4) - get direct employees
    if target_role == 4:
        direct_reports = await db.users.find(
            {"manager_id": user_id},
            {"_id": 0, "password": 0}
        ).to_list(100)
        subordinates = direct_reports
    
    # Zonal Manager (3) - get managers and their employees
    elif target_role == 3:
        # Get direct reports (managers)
        managers = await db.users.find(
            {"manager_id": user_id},
            {"_id": 0, "password": 0}
        ).to_list(100)
        
        manager_ids = [m["id"] for m in managers]
        
        # Get employees under those managers
        employees = await db.users.find(
            {"manager_id": {"$in": manager_ids}},
            {"_id": 0, "password": 0}
        ).to_list(1000)
        
        subordinates = managers + employees
    
    # PE Level - can see entire hierarchy
    elif target_role in [1, 2]:
        all_users = await db.users.find(
            {"role": {"$gte": 3}},  # Everyone except PE Desk and PE Manager
            {"_id": 0, "password": 0}
        ).to_list(1000)
        subordinates = all_users
    
    # Add role names
    for sub in subordinates:
        sub["role_name"] = ROLES.get(sub.get("role", 6), "Viewer")
    
    return subordinates


@router.get("/managers-list")
async def get_managers_list(role: Optional[int] = None, current_user: dict = Depends(get_current_user)):
    """Get list of users who can be managers (for dropdown selection)
    
    - For assigning Employees: returns Managers (role 4)
    - For assigning Managers: returns Zonal Managers (role 3)
    """
    if not is_pe_level(current_user.get("role", 6)):
        raise HTTPException(status_code=403, detail="Only PE Desk or PE Manager can access manager list")
    
    if role == 5:  # Getting managers for employees
        managers = await db.users.find(
            {"role": 4, "is_active": {"$ne": False}},
            {"_id": 0, "id": 1, "name": 1, "email": 1, "role": 1}
        ).to_list(100)
    elif role == 4:  # Getting zonal managers for managers
        managers = await db.users.find(
            {"role": 3, "is_active": {"$ne": False}},
            {"_id": 0, "id": 1, "name": 1, "email": 1, "role": 1}
        ).to_list(100)
    else:
        # Return both managers and zonal managers
        managers = await db.users.find(
            {"role": {"$in": [3, 4]}, "is_active": {"$ne": False}},
            {"_id": 0, "id": 1, "name": 1, "email": 1, "role": 1}
        ).to_list(100)
    
    for m in managers:
        m["role_name"] = ROLES.get(m.get("role", 6), "Viewer")
    
    return managers



# ============== PE Online Status Tracking ==============
from services.notification_service import ws_manager

@router.post("/heartbeat")
async def user_heartbeat(current_user: dict = Depends(get_current_user)):
    """Record user heartbeat to track online status.
    PE Desk/Manager users' heartbeats are tracked to show PE availability."""
    user_role = current_user.get("role", 6)
    user_id = current_user.get("id")
    
    # Only track PE level users (role 1 = PE Desk, role 2 = PE Manager)
    if user_role in [1, 2]:
        status_changed = ws_manager.update_pe_status(
            user_id=user_id,
            user_name=current_user.get("name", "Unknown"),
            user_role=user_role,
            role_name=ROLES.get(user_role, "Unknown")
        )
        
        # If PE status changed, broadcast to all connected users
        if status_changed:
            pe_status = ws_manager.get_pe_status()
            await ws_manager.broadcast_to_all({
                "event": "pe_status_change",
                "data": pe_status
            })
    
    return {"status": "ok"}


@router.get("/pe-status")
async def get_pe_online_status(current_user: dict = Depends(get_current_user)):
    """Check if any PE Desk or PE Manager is currently online.
    Returns green status if PE is available, red if not."""
    return ws_manager.get_pe_status()

