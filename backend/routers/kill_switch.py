"""
Kill Switch Router
Emergency system freeze functionality - PE Desk only
"""
from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime, timezone, timedelta
from typing import Optional
import uuid

from database import db
from routers.auth import get_current_user
from services.permission_service import (
    require_permission,
    is_pe_desk
)

router = APIRouter(prefix="/kill-switch", tags=["Kill Switch"])


# Cooldown period in seconds (3 minutes)
COOLDOWN_SECONDS = 180


async def get_kill_switch_status():
    """Get current kill switch status from database"""
    status = await db.system_settings.find_one({"setting": "kill_switch"}, {"_id": 0})
    if not status:
        return {
            "is_active": False,
            "activated_at": None,
            "activated_by": None,
            "activated_by_name": None,
            "can_deactivate_at": None,
            "reason": None
        }
    return status


async def is_system_frozen():
    """Check if the system is currently frozen"""
    status = await get_kill_switch_status()
    return status.get("is_active", False)


@router.get("/status")
async def get_status():
    """Get kill switch status - public endpoint for all users to check system state"""
    status = await get_kill_switch_status()
    
    # Calculate remaining cooldown time
    remaining_seconds = 0
    if status.get("is_active") and status.get("can_deactivate_at"):
        can_deactivate = datetime.fromisoformat(status["can_deactivate_at"].replace('Z', '+00:00'))
        now = datetime.now(timezone.utc)
        if can_deactivate > now:
            remaining_seconds = int((can_deactivate - now).total_seconds())
    
    return {
        "is_active": status.get("is_active", False),
        "activated_at": status.get("activated_at"),
        "activated_by_name": status.get("activated_by_name"),
        "can_deactivate_at": status.get("can_deactivate_at"),
        "remaining_seconds": remaining_seconds,
        "reason": status.get("reason")
    }


@router.post("/activate", dependencies=[Depends(require_permission("system.kill_switch", "activate kill switch"))])
async def activate_kill_switch(
    reason: Optional[str] = "Emergency system freeze",
    current_user: dict = Depends(get_current_user)
):
    """Activate kill switch - PE Desk only
    
    This will:
    - Freeze all user activities
    - Block all API calls except kill switch and auth endpoints
    - Stop all email sending
    - Start 3-minute cooldown before deactivation is allowed
    """
    if not is_pe_desk_only(current_user.get("role", 6)):
        raise HTTPException(status_code=403, detail="Only PE Desk can activate the kill switch")
    
    # Check if already active
    status = await get_kill_switch_status()
    if status.get("is_active"):
        raise HTTPException(status_code=400, detail="Kill switch is already active")
    
    now = datetime.now(timezone.utc)
    can_deactivate_at = now + timedelta(seconds=COOLDOWN_SECONDS)
    
    kill_switch_data = {
        "setting": "kill_switch",
        "is_active": True,
        "activated_at": now.isoformat(),
        "activated_by": current_user["id"],
        "activated_by_name": current_user["name"],
        "can_deactivate_at": can_deactivate_at.isoformat(),
        "reason": reason
    }
    
    await db.system_settings.update_one(
        {"setting": "kill_switch"},
        {"$set": kill_switch_data},
        upsert=True
    )
    
    # Log the activation
    await db.audit_logs.insert_one({
        "id": str(uuid.uuid4()),
        "action": "KILL_SWITCH_ACTIVATED",
        "entity_type": "system",
        "entity_id": "kill_switch",
        "user_id": current_user["id"],
        "user_name": current_user["name"],
        "user_role": current_user.get("role", 1),
        "details": {
            "reason": reason,
            "cooldown_seconds": COOLDOWN_SECONDS
        },
        "timestamp": now.isoformat()
    })
    
    return {
        "message": "Kill switch activated - System is now frozen",
        "activated_at": now.isoformat(),
        "can_deactivate_at": can_deactivate_at.isoformat(),
        "cooldown_seconds": COOLDOWN_SECONDS
    }


@router.post("/deactivate", dependencies=[Depends(require_permission("system.kill_switch", "deactivate kill switch"))])
async def deactivate_kill_switch(current_user: dict = Depends(get_current_user)):
    """Deactivate kill switch - PE Desk only, after cooldown period"""
    if not is_pe_desk_only(current_user.get("role", 6)):
        raise HTTPException(status_code=403, detail="Only PE Desk can deactivate the kill switch")
    
    status = await get_kill_switch_status()
    
    if not status.get("is_active"):
        raise HTTPException(status_code=400, detail="Kill switch is not active")
    
    # Check cooldown
    can_deactivate_at = datetime.fromisoformat(status["can_deactivate_at"].replace('Z', '+00:00'))
    now = datetime.now(timezone.utc)
    
    if now < can_deactivate_at:
        remaining = int((can_deactivate_at - now).total_seconds())
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot deactivate yet. {remaining} seconds remaining in cooldown period."
        )
    
    # Deactivate
    await db.system_settings.update_one(
        {"setting": "kill_switch"},
        {"$set": {
            "is_active": False,
            "deactivated_at": now.isoformat(),
            "deactivated_by": current_user["id"],
            "deactivated_by_name": current_user["name"]
        }}
    )
    
    # Log the deactivation
    await db.audit_logs.insert_one({
        "id": str(uuid.uuid4()),
        "action": "KILL_SWITCH_DEACTIVATED",
        "entity_type": "system",
        "entity_id": "kill_switch",
        "user_id": current_user["id"],
        "user_name": current_user["name"],
        "user_role": current_user.get("role", 1),
        "details": {
            "was_activated_by": status.get("activated_by_name"),
            "was_activated_at": status.get("activated_at"),
            "reason_was": status.get("reason")
        },
        "timestamp": now.isoformat()
    })
    
    return {
        "message": "Kill switch deactivated - System is now operational",
        "deactivated_at": now.isoformat()
    }
