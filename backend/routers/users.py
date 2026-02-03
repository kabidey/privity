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
from config import ROLES
from models import User
from utils.auth import get_current_user, check_permission
from services.permission_service import (
    has_permission,
    check_permission as check_dynamic_permission,
    is_pe_level_dynamic,
    require_permission
)

router = APIRouter(prefix="/users", tags=["Users"])


# Helper functions for backward compatibility
def is_pe_level(role: int) -> bool:
    """Check if role is PE level (PE Desk or PE Manager)."""
    return role in [1, 2]


def is_pe_desk_only(role: int) -> bool:
    """Check if role is PE Desk only."""
    return role == 1


def can_manage_business_partners(role: int) -> bool:
    """Check if role can manage business partners."""
    return role in [1, 2, 5]  # PE Desk, PE Manager, Partners Desk


# ============== Pydantic Models ==============
class UserCreate(BaseModel):
    email: str
    password: str
    name: str
    role: int = 7  # Default to Employee
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
async def get_employees(
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("users.view", "view employee list"))
):
    """Get list of all users for client mapping (requires users.view permission)"""
    # Return all users for client mapping
    users = await db.users.find(
        {},
        {"_id": 0, "id": 1, "name": 1, "email": 1, "role": 1}
    ).to_list(1000)
    
    return [{"id": u["id"], "name": u["name"], "email": u["email"], "role": u.get("role", 7), "role_name": ROLES.get(u.get("role", 7), "Employee")} for u in users]


# ============== User Endpoints ==============
@router.get("", response_model=List[User])
async def get_users(
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("users.view", "view users"))
):
    """Get all users (requires users.view permission)"""
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
async def create_user(
    user_data: UserCreate,
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("users.create", "create users"))
):
    """Create a new user (requires users.create permission)"""
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
async def update_user(
    user_id: str,
    user_data: UserUpdate,
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("users.edit", "update users"))
):
    """Update a user (requires users.edit permission)"""
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


@router.put("/{user_id}/hierarchy")
async def update_user_hierarchy(
    user_id: str,
    hierarchy_data: HierarchyUpdate,
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("users.edit", "update user hierarchy"))
):
    """Update user hierarchy (requires users.edit permission)"""
    from services.hierarchy_service import get_manager_chain
    
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if hierarchy_data.hierarchy_level not in HIERARCHY_LEVELS:
        raise HTTPException(status_code=400, detail="Invalid hierarchy level")
    
    update_data = {
        "hierarchy_level": hierarchy_data.hierarchy_level,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "updated_by": current_user["id"]
    }
    
    # Handle reports_to
    if hierarchy_data.reports_to:
        if hierarchy_data.reports_to == user_id:
            raise HTTPException(status_code=400, detail="User cannot report to themselves")
        manager = await db.users.find_one({"id": hierarchy_data.reports_to})
        if not manager:
            raise HTTPException(status_code=400, detail="Manager not found")
        
        # Check for circular reference: ensure user_id is not in the manager's chain
        manager_chain = await get_manager_chain(hierarchy_data.reports_to)
        if any(m["id"] == user_id for m in manager_chain):
            raise HTTPException(
                status_code=400, 
                detail="Cannot assign this manager - it would create a circular reporting structure"
            )
        
        update_data["reports_to"] = hierarchy_data.reports_to
    else:
        update_data["reports_to"] = None
    
    await db.users.update_one({"id": user_id}, {"$set": update_data})
    
    return {"message": "User hierarchy updated successfully"}


@router.get("/hierarchy/levels")
async def get_hierarchy_levels(current_user: dict = Depends(get_current_user)):
    """Get available hierarchy levels"""
    return [{"level": k, "name": v} for k, v in HIERARCHY_LEVELS.items()]


@router.get("/hierarchy/potential-managers")
async def get_potential_managers(current_user: dict = Depends(get_current_user)):
    """Get list of users who can be managers (hierarchy level > 1 or PE Level)"""
    if not is_pe_level(current_user.get("role", 6)):
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Get users with hierarchy level > 1 or PE roles
    users = await db.users.find(
        {"$or": [
            {"hierarchy_level": {"$gt": 1}},
            {"role": {"$in": [1, 2]}}
        ]},
        {"_id": 0, "id": 1, "name": 1, "email": 1, "hierarchy_level": 1, "role": 1}
    ).to_list(1000)
    
    return [{
        "id": u["id"],
        "name": u["name"],
        "email": u["email"],
        "hierarchy_level": u.get("hierarchy_level", 1),
        "hierarchy_level_name": HIERARCHY_LEVELS.get(u.get("hierarchy_level", 1), "Employee")
    } for u in users]


@router.get("/team/subordinates")
async def get_my_subordinates(current_user: dict = Depends(get_current_user)):
    """Get all subordinates under current user"""
    from services.hierarchy_service import get_all_subordinates
    
    subordinate_ids = await get_all_subordinates(current_user["id"])
    
    if not subordinate_ids:
        return []
    
    users = await db.users.find(
        {"id": {"$in": subordinate_ids}},
        {"_id": 0, "password": 0}
    ).to_list(1000)
    
    result = []
    for u in users:
        enriched = await enrich_user_with_hierarchy(u)
        enriched["role_name"] = ROLES.get(u.get("role", 6), "Viewer")
        result.append(enriched)
    
    return result


@router.get("/team/direct-reports")
async def get_my_direct_reports(current_user: dict = Depends(get_current_user)):
    """Get users who directly report to current user"""
    users = await db.users.find(
        {"reports_to": current_user["id"]},
        {"_id": 0, "password": 0}
    ).to_list(1000)
    
    result = []
    for u in users:
        enriched = await enrich_user_with_hierarchy(u)
        enriched["role_name"] = ROLES.get(u.get("role", 6), "Viewer")
        result.append(enriched)
    
    return result


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
    from services.hierarchy_service import get_all_subordinates
    
    user_role = current_user.get("role", 6)
    user_id = current_user.get("id")
    
    # PE Level can see all users
    if is_pe_level(user_role):
        users = await db.users.find({}, {"_id": 0, "password": 0}).to_list(1000)
    else:
        # Get subordinates using new hierarchy
        subordinate_ids = await get_all_subordinates(user_id)
        all_ids = [user_id] + subordinate_ids
        
        users = await db.users.find(
            {"id": {"$in": all_ids}},
            {"_id": 0, "password": 0}
        ).to_list(1000)
    
    # Enrich with hierarchy info
    result = []
    for user in users:
        enriched = await enrich_user_with_hierarchy(user)
        enriched["role_name"] = ROLES.get(user.get("role", 6), "Viewer")
        # Keep backward compatibility - copy reports_to to manager_id
        enriched["manager_id"] = user.get("reports_to")
        enriched["manager_name"] = enriched.get("reports_to_name")
        result.append(enriched)
    
    return result


@router.put("/{user_id}/assign-manager")
async def assign_manager(user_id: str, manager_id: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    """Assign a user to a manager (PE Level only) using reports_to field.
    
    The new hierarchy system uses hierarchy_level and reports_to instead of role-based hierarchy.
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
            {"$set": {"reports_to": None}, "$unset": {"manager_id": ""}}
        )
        return {"message": f"Manager assignment removed for {user['name']}"}
    
    # Get the manager
    manager = await db.users.find_one({"id": manager_id}, {"_id": 0})
    if not manager:
        raise HTTPException(status_code=404, detail="Manager not found")
    
    # Prevent self-assignment
    if user_id == manager_id:
        raise HTTPException(status_code=400, detail="Cannot assign user to themselves")
    
    # PE roles cannot be assigned to managers
    user_role = user.get("role", 6)
    if user_role in [1, 2]:
        raise HTTPException(status_code=400, detail="PE Desk and PE Manager cannot be assigned to managers")
    
    # Validate hierarchy level - user should be lower than manager
    user_level = user.get("hierarchy_level", 1)
    manager_level = manager.get("hierarchy_level", 1)
    manager_role = manager.get("role", 6)
    
    # Manager must be higher level or PE role
    if not is_pe_level(manager_role) and manager_level <= user_level:
        raise HTTPException(status_code=400, detail="Manager must be at a higher hierarchy level than the user")
    
    # Update assignment - use reports_to (and keep manager_id for backward compatibility)
    await db.users.update_one(
        {"id": user_id},
        {"$set": {"reports_to": manager_id, "manager_id": manager_id}}
    )
    
    return {
        "message": f"{user['name']} now reports to {manager['name']}",
        "user_id": user_id,
        "manager_id": manager_id,
        "reports_to": manager_id
    }


@router.get("/{user_id}/subordinates")
async def get_subordinates(user_id: str, current_user: dict = Depends(get_current_user)):
    """Get all subordinates for a user (direct and indirect) using hierarchy service"""
    from services.hierarchy_service import get_all_subordinates
    
    user_role = current_user.get("role", 6)
    
    # Only allow viewing own subordinates or PE Level can view anyone's
    if not is_pe_level(user_role) and current_user["id"] != user_id:
        raise HTTPException(status_code=403, detail="You can only view your own subordinates")
    
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Use hierarchy service to get all subordinates
    subordinate_ids = await get_all_subordinates(user_id)
    
    if not subordinate_ids:
        return []
    
    subordinates = await db.users.find(
        {"id": {"$in": subordinate_ids}},
        {"_id": 0, "password": 0}
    ).to_list(1000)
    
    # Enrich with hierarchy info
    result = []
    for sub in subordinates:
        enriched = await enrich_user_with_hierarchy(sub)
        enriched["role_name"] = ROLES.get(sub.get("role", 6), "Viewer")
        result.append(enriched)
    
    return result


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

