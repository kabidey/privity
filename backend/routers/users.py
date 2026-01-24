"""
User management routes
"""
from typing import List
from fastapi import APIRouter, HTTPException, Depends

from database import db
from config import ROLES
from models import User
from utils.auth import get_current_user, check_permission

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("", response_model=List[User])
async def get_users(current_user: dict = Depends(get_current_user)):
    """Get all users (requires manage_users permission)"""
    check_permission(current_user, "manage_users")
    users = await db.users.find({}, {"_id": 0, "password": 0}).to_list(1000)
    return [User(**{**u, "role_name": ROLES.get(u.get("role", 5), "Viewer")}) for u in users]


@router.put("/{user_id}/role")
async def update_user_role(user_id: str, role: int, current_user: dict = Depends(get_current_user)):
    """Update user role (requires manage_users permission)"""
    check_permission(current_user, "manage_users")
    
    if role not in ROLES:
        raise HTTPException(status_code=400, detail="Invalid role")
    
    result = await db.users.update_one({"id": user_id}, {"$set": {"role": role}})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {"message": "User role updated successfully"}
