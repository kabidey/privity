"""
Security Router
Endpoints for security monitoring and threat dashboard
"""
from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime, timezone, timedelta
from database import db
from utils.auth import get_current_user
from services.permission_service import PermissionService
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/security", tags=["Security"])


@router.get("/threats")
async def get_threats(current_user: dict = Depends(get_current_user)):
    """
    Get comprehensive threat statistics for the Security Dashboard
    Requires security.view_dashboard permission
    """
    # Check permission
    if not PermissionService.user_has_permission(current_user, "security.view_dashboard"):
        if current_user.get("role") not in [1, 2]:  # PE Desk or PE Manager
            raise HTTPException(status_code=403, detail="Permission denied")
    
    try:
        from middleware.bot_protection import get_threat_statistics
        stats = await get_threat_statistics()
        return stats
    except Exception as e:
        logger.error(f"Failed to get threat statistics: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve threat data")


@router.get("/threats/recent")
async def get_recent_threats(
    limit: int = 50,
    threat_type: str = None,
    current_user: dict = Depends(get_current_user)
):
    """
    Get recent blocked threats with optional filtering
    """
    # Check permission
    if not PermissionService.user_has_permission(current_user, "security.view_dashboard"):
        if current_user.get("role") not in [1, 2]:
            raise HTTPException(status_code=403, detail="Permission denied")
    
    try:
        query = {}
        if threat_type:
            query["threat_type"] = threat_type
        
        threats = await db.blocked_threats.find(query).sort("timestamp", -1).limit(limit).to_list(limit)
        
        return [
            {
                "ip_address": t.get("ip_address", "Unknown"),
                "threat_type": t.get("threat_type", "Unknown"),
                "user_agent": t.get("user_agent", "")[:200],
                "path": t.get("path", "/")[:100],
                "details": t.get("details", "")[:200],
                "timestamp": t.get("timestamp", ""),
                "blocked": t.get("blocked", True)
            }
            for t in threats
        ]
    except Exception as e:
        logger.error(f"Failed to get recent threats: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve threats")


@router.get("/threats/by-ip/{ip_address}")
async def get_threats_by_ip(
    ip_address: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get all threats from a specific IP address
    """
    # Check permission
    if not PermissionService.user_has_permission(current_user, "security.view_dashboard"):
        if current_user.get("role") not in [1, 2]:
            raise HTTPException(status_code=403, detail="Permission denied")
    
    try:
        threats = await db.blocked_threats.find(
            {"ip_address": ip_address}
        ).sort("timestamp", -1).limit(100).to_list(100)
        
        # Get unique threat types
        threat_types = list(set(t.get("threat_type", "Unknown") for t in threats))
        
        return {
            "ip_address": ip_address,
            "total_violations": len(threats),
            "threat_types": threat_types,
            "first_seen": threats[-1].get("timestamp", "") if threats else None,
            "last_seen": threats[0].get("timestamp", "") if threats else None,
            "threats": [
                {
                    "threat_type": t.get("threat_type", "Unknown"),
                    "path": t.get("path", "/")[:100],
                    "details": t.get("details", "")[:200],
                    "timestamp": t.get("timestamp", "")
                }
                for t in threats
            ]
        }
    except Exception as e:
        logger.error(f"Failed to get threats for IP {ip_address}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve threats")


@router.get("/threats/summary")
async def get_threat_summary(
    days: int = 7,
    current_user: dict = Depends(get_current_user)
):
    """
    Get threat summary for the specified number of days
    """
    # Check permission
    if not PermissionService.user_has_permission(current_user, "security.view_dashboard"):
        if current_user.get("role") not in [1, 2]:
            raise HTTPException(status_code=403, detail="Permission denied")
    
    try:
        start_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        # Total threats in period
        total_threats = await db.blocked_threats.count_documents({
            "timestamp": {"$gte": start_date.isoformat()}
        })
        
        # Threats by type
        pipeline = [
            {"$match": {"timestamp": {"$gte": start_date.isoformat()}}},
            {"$group": {"_id": "$threat_type", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]
        by_type = await db.blocked_threats.aggregate(pipeline).to_list(50)
        
        # Unique IPs
        unique_ips_pipeline = [
            {"$match": {"timestamp": {"$gte": start_date.isoformat()}}},
            {"$group": {"_id": "$ip_address"}},
            {"$count": "total"}
        ]
        unique_ips_result = await db.blocked_threats.aggregate(unique_ips_pipeline).to_list(1)
        unique_ips = unique_ips_result[0]["total"] if unique_ips_result else 0
        
        # Daily breakdown
        daily_pipeline = [
            {"$match": {"timestamp": {"$gte": start_date.isoformat()}}},
            {
                "$group": {
                    "_id": {
                        "$dateToString": {
                            "format": "%Y-%m-%d",
                            "date": {"$dateFromString": {"dateString": "$timestamp"}}
                        }
                    },
                    "count": {"$sum": 1}
                }
            },
            {"$sort": {"_id": 1}}
        ]
        daily_breakdown = await db.blocked_threats.aggregate(daily_pipeline).to_list(days)
        
        # Top offending IPs
        top_ips_pipeline = [
            {"$match": {"timestamp": {"$gte": start_date.isoformat()}}},
            {"$group": {"_id": "$ip_address", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 10}
        ]
        top_ips = await db.blocked_threats.aggregate(top_ips_pipeline).to_list(10)
        
        return {
            "period_days": days,
            "total_threats": total_threats,
            "unique_attacking_ips": unique_ips,
            "by_type": {item["_id"]: item["count"] for item in by_type},
            "daily_breakdown": [
                {"date": item["_id"], "count": item["count"]}
                for item in daily_breakdown
            ],
            "top_offending_ips": [
                {"ip_address": item["_id"], "count": item["count"]}
                for item in top_ips
            ]
        }
    except Exception as e:
        logger.error(f"Failed to get threat summary: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve summary")


@router.delete("/threats/clear")
async def clear_old_threats(
    days_to_keep: int = 30,
    current_user: dict = Depends(get_current_user)
):
    """
    Clear threats older than specified days (admin only)
    """
    # Only PE Desk can clear threats
    if current_user.get("role") != 1:
        raise HTTPException(status_code=403, detail="Only PE Desk can clear threat logs")
    
    try:
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_to_keep)
        
        result = await db.blocked_threats.delete_many({
            "timestamp": {"$lt": cutoff_date.isoformat()}
        })
        
        return {
            "message": f"Cleared {result.deleted_count} old threat records",
            "deleted_count": result.deleted_count,
            "cutoff_date": cutoff_date.isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to clear threats: {e}")
        raise HTTPException(status_code=500, detail="Failed to clear threats")
