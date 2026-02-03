"""
Audit Logs Router
Handles audit log retrieval and statistics
"""
from typing import List, Optional
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, HTTPException, Depends, Query

from database import db
from config import AUDIT_ACTIONS, ROLES
from utils.auth import get_current_user
from services.permission_service import (
    has_permission,
    check_permission as check_dynamic_permission,
    require_permission
)

router = APIRouter(prefix="/audit-logs", tags=["Audit Logs"])


# Helper function for backward compatibility
def is_pe_level(role: int) -> bool:
    """Check if role is PE level (PE Desk or PE Manager)."""
    return role in [1, 2]


def get_role_name(role: int) -> str:
    """Get role name from role number"""
    return ROLES.get(role, "Unknown")


@router.get("")
async def get_audit_logs(
    entity_type: Optional[str] = None,
    action: Optional[str] = None,
    user_id: Optional[str] = None,
    user_name: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = Query(100, ge=1, le=1000),
    skip: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("audit_logs.view", "view audit logs"))
):
    """Get audit logs with filters (requires audit_logs.view permission)"""
    user_role = current_user.get("role", 6)
    
    query = {}
    
    if entity_type:
        query["entity_type"] = entity_type
    if action:
        query["action"] = action
    if user_id:
        query["user_id"] = user_id
    if user_name:
        query["user_name"] = {"$regex": user_name, "$options": "i"}
    if start_date:
        query["timestamp"] = {"$gte": start_date}
    if end_date:
        if "timestamp" in query:
            query["timestamp"]["$lte"] = end_date + "T23:59:59"
        else:
            query["timestamp"] = {"$lte": end_date + "T23:59:59"}
    
    total = await db.audit_logs.count_documents(query)
    logs = await db.audit_logs.find(query, {"_id": 0}).sort("timestamp", -1).skip(skip).limit(limit).to_list(limit)
    
    # Enrich logs with role name
    for log in logs:
        log["role_name"] = get_role_name(log.get("user_role", 6))
    
    return {
        "total": total,
        "logs": logs,
        "limit": limit,
        "skip": skip
    }


@router.get("/actions")
async def get_available_actions(
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("audit_logs.view", "view audit actions"))
):
    """Get list of available audit actions (requires audit_logs.view permission)"""
    user_role = current_user.get("role", 6)
    
    return {
        "actions": AUDIT_ACTIONS
    }


@router.get("/entity-types")
async def get_entity_types(
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("audit_logs.view", "view entity types"))
):
    """Get distinct entity types from audit logs (requires audit_logs.view permission)"""
    user_role = current_user.get("role", 6)
    
    entity_types = await db.audit_logs.distinct("entity_type")
    return {"entity_types": [et for et in entity_types if et]}


@router.get("/stats")
async def get_audit_stats(
    days: int = Query(7, ge=1, le=90),
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("audit_logs.view", "view audit stats"))
):
    """Get audit log statistics (requires audit_logs.view permission)"""
    user_role = current_user.get("role", 6)
    
    start_date = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    
    # Get action distribution
    action_pipeline = [
        {"$match": {"timestamp": {"$gte": start_date}}},
        {"$group": {"_id": "$action", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 20}
    ]
    action_stats = await db.audit_logs.aggregate(action_pipeline).to_list(20)
    
    # Get entity type distribution
    entity_pipeline = [
        {"$match": {"timestamp": {"$gte": start_date}}},
        {"$group": {"_id": "$entity_type", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    entity_stats = await db.audit_logs.aggregate(entity_pipeline).to_list(20)
    
    # Get user activity
    user_pipeline = [
        {"$match": {"timestamp": {"$gte": start_date}}},
        {"$group": {"_id": {"user_id": "$user_id", "user_name": "$user_name"}, "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 10}
    ]
    user_stats = await db.audit_logs.aggregate(user_pipeline).to_list(10)
    
    # Get daily activity for chart
    daily_pipeline = [
        {"$match": {"timestamp": {"$gte": start_date}}},
        {"$addFields": {"date": {"$substr": ["$timestamp", 0, 10]}}},
        {"$group": {"_id": "$date", "count": {"$sum": 1}}},
        {"$sort": {"_id": 1}}
    ]
    daily_stats = await db.audit_logs.aggregate(daily_pipeline).to_list(days)
    
    total_logs = await db.audit_logs.count_documents({"timestamp": {"$gte": start_date}})
    
    return {
        "period_days": days,
        "total_logs": total_logs,
        "by_action": {item["_id"]: item["count"] for item in action_stats if item["_id"]},
        "by_entity_type": {item["_id"]: item["count"] for item in entity_stats if item["_id"]},
        "by_user": [
            {"user_id": item["_id"]["user_id"], "user_name": item["_id"]["user_name"], "count": item["count"]}
            for item in user_stats if item["_id"]
        ],
        "daily_activity": [{"date": item["_id"], "count": item["count"]} for item in daily_stats]
    }
