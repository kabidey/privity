"""
Audit Logs Router
Handles audit log retrieval and statistics
"""
from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends, Query

from database import db
from config import is_pe_level
from utils.auth import get_current_user

router = APIRouter(prefix="/audit-logs", tags=["Audit Logs"])


@router.get("")
async def get_audit_logs(
    entity_type: Optional[str] = None,
    action: Optional[str] = None,
    user_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = Query(100, ge=1, le=1000),
    skip: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user)
):
    """Get audit logs with filters"""
    user_role = current_user.get("role", 6)
    
    # Only PE level can view all audit logs
    if not is_pe_level(user_role):
        raise HTTPException(status_code=403, detail="Insufficient permissions to view audit logs")
    
    query = {}
    
    if entity_type:
        query["entity_type"] = entity_type
    if action:
        query["action"] = action
    if user_id:
        query["user_id"] = user_id
    if start_date:
        query["created_at"] = {"$gte": start_date}
    if end_date:
        if "created_at" in query:
            query["created_at"]["$lte"] = end_date
        else:
            query["created_at"] = {"$lte": end_date}
    
    total = await db.audit_logs.count_documents(query)
    logs = await db.audit_logs.find(query, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    
    return {
        "total": total,
        "logs": logs,
        "limit": limit,
        "skip": skip
    }


@router.get("/stats")
async def get_audit_stats(
    days: int = Query(7, ge=1, le=90),
    current_user: dict = Depends(get_current_user)
):
    """Get audit log statistics"""
    user_role = current_user.get("role", 6)
    
    if not is_pe_level(user_role):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    from datetime import timedelta
    start_date = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    
    # Get action distribution
    action_pipeline = [
        {"$match": {"created_at": {"$gte": start_date}}},
        {"$group": {"_id": "$action", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 20}
    ]
    action_stats = await db.audit_logs.aggregate(action_pipeline).to_list(20)
    
    # Get entity type distribution
    entity_pipeline = [
        {"$match": {"created_at": {"$gte": start_date}}},
        {"$group": {"_id": "$entity_type", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    entity_stats = await db.audit_logs.aggregate(entity_pipeline).to_list(20)
    
    # Get user activity
    user_pipeline = [
        {"$match": {"created_at": {"$gte": start_date}}},
        {"$group": {"_id": {"user_id": "$user_id", "user_name": "$user_name"}, "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 10}
    ]
    user_stats = await db.audit_logs.aggregate(user_pipeline).to_list(10)
    
    total_logs = await db.audit_logs.count_documents({"created_at": {"$gte": start_date}})
    
    return {
        "period_days": days,
        "total_logs": total_logs,
        "by_action": {item["_id"]: item["count"] for item in action_stats if item["_id"]},
        "by_entity_type": {item["_id"]: item["count"] for item in entity_stats if item["_id"]},
        "by_user": [
            {"user_id": item["_id"]["user_id"], "user_name": item["_id"]["user_name"], "count": item["count"]}
            for item in user_stats if item["_id"]
        ]
    }
