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

router = APIRouter(prefix="/users", tags=["Users"])


# ============== Pydantic Models ==============
class UserCreate(BaseModel):
    email: str
    password: str
    name: str
    role: int = 5  # Default to Employee


class UserUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[int] = None
    is_active: Optional[bool] = None


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


# ============== User Endpoints ==============
@router.get("", response_model=List[User])
async def get_users(current_user: dict = Depends(get_current_user)):
    """Get all users (requires manage_users permission)"""
    check_permission(current_user, "manage_users")
    users = await db.users.find({}, {"_id": 0, "password": 0}).to_list(1000)
    return [User(**{**u, "role_name": ROLES.get(u.get("role", 5), "Viewer")}) for u in users]


@router.post("")
async def create_user(user_data: UserCreate, current_user: dict = Depends(get_current_user)):
    """Create a new user (PE Desk only)"""
    if current_user.get("role", 5) != 1:
        raise HTTPException(status_code=403, detail="Only PE Desk can create users")
    
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
            "role_name": ROLES.get(user_data.role, "Viewer")
        }
    }


@router.put("/{user_id}")
async def update_user(user_id: str, user_data: UserUpdate, current_user: dict = Depends(get_current_user)):
    """Update a user (PE Desk only)"""
    if current_user.get("role", 5) != 1:
        raise HTTPException(status_code=403, detail="Only PE Desk can update users")
    
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Prevent modifying the super admin (pedesk@smifs.com)
    if user.get("email") == "pedesk@smifs.com" and current_user.get("email") != "pedesk@smifs.com":
        raise HTTPException(status_code=403, detail="Cannot modify the super admin account")
    
    update_data = {}
    if user_data.name is not None:
        update_data["name"] = user_data.name
    if user_data.role is not None:
        if user_data.role not in ROLES:
            raise HTTPException(status_code=400, detail="Invalid role")
        update_data["role"] = user_data.role
    if user_data.is_active is not None:
        update_data["is_active"] = user_data.is_active
    
    if update_data:
        update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
        update_data["updated_by"] = current_user["id"]
        await db.users.update_one({"id": user_id}, {"$set": update_data})
    
    return {"message": "User updated successfully"}


@router.put("/{user_id}/role")
async def update_user_role(user_id: str, role: int, current_user: dict = Depends(get_current_user)):
    """Update user role (requires manage_users permission)"""
    check_permission(current_user, "manage_users")
    
    if role not in ROLES:
        raise HTTPException(status_code=400, detail="Invalid role")
    
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Prevent modifying the super admin
    if user.get("email") == "pedesk@smifs.com":
        raise HTTPException(status_code=403, detail="Cannot modify the super admin role")
    
    result = await db.users.update_one({"id": user_id}, {"$set": {"role": role}})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {"message": "User role updated successfully"}


@router.delete("/{user_id}")
async def delete_user(user_id: str, current_user: dict = Depends(get_current_user)):
    """Delete a user (PE Desk only)"""
    if current_user.get("role", 5) != 1:
        raise HTTPException(status_code=403, detail="Only PE Desk can delete users")
    
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Prevent deleting the super admin
    if user.get("email") == "pedesk@smifs.com":
        raise HTTPException(status_code=403, detail="Cannot delete the super admin account")
    
    # Prevent self-deletion
    if user_id == current_user["id"]:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    
    await db.users.delete_one({"id": user_id})
    
    return {"message": f"User {user.get('name')} deleted successfully"}


@router.post("/{user_id}/reset-password")
async def reset_user_password(user_id: str, new_password: str, current_user: dict = Depends(get_current_user)):
    """Reset a user's password (PE Desk only)"""
    if current_user.get("role", 5) != 1:
        raise HTTPException(status_code=403, detail="Only PE Desk can reset passwords")
    
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
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

