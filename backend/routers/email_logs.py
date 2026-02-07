"""
Email Logs Router
Handles email audit log retrieval and statistics
"""
from typing import List, Optional
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel

from database import db
from utils.auth import get_current_user
from services.permission_service import (
    require_permission,
    is_pe_level
)

router = APIRouter(prefix="/email-logs", tags=["Email Logs"])


class EmailLog(BaseModel):
    id: str
    to_email: str
    cc_email: Optional[str] = None
    subject: str
    template_key: Optional[str] = None
    status: str  # "sent", "failed", "skipped"
    error_message: Optional[str] = None
    variables: dict = {}
    related_entity_type: Optional[str] = None
    related_entity_id: Optional[str] = None
    created_at: str


class EmailLogStats(BaseModel):
    total_sent: int
    total_failed: int
    total_skipped: int
    by_template: dict
    by_status: dict
    by_entity_type: dict
    recent_failures: List[dict]


@router.get("", response_model=dict)
async def get_email_logs(
    status: Optional[str] = None,
    template_key: Optional[str] = None,
    to_email: Optional[str] = None,
    related_entity_type: Optional[str] = None,
    related_entity_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = Query(50, ge=1, le=500),
    skip: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("email.view_logs", "view email logs"))
):
    """
    Get email logs with filters (PE Level only)
    
    Filters:
    - status: "sent", "failed", "skipped"
    - template_key: Filter by email template
    - to_email: Filter by recipient email
    - related_entity_type: Filter by entity type (booking, client, rp, user)
    - related_entity_id: Filter by specific entity ID
    - start_date/end_date: Date range filter (YYYY-MM-DD format)
    """
    query = {}
    
    if status:
        query["status"] = status
    if template_key:
        query["template_key"] = template_key
    if to_email:
        query["to_email"] = {"$regex": to_email, "$options": "i"}
    if related_entity_type:
        query["related_entity_type"] = related_entity_type
    if related_entity_id:
        query["related_entity_id"] = related_entity_id
    if start_date:
        query["created_at"] = {"$gte": start_date}
    if end_date:
        if "created_at" in query:
            query["created_at"]["$lte"] = end_date + "T23:59:59"
        else:
            query["created_at"] = {"$lte": end_date + "T23:59:59"}
    
    total = await db.email_logs.count_documents(query)
    logs = await db.email_logs.find(query, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    
    return {
        "total": total,
        "logs": logs,
        "limit": limit,
        "skip": skip
    }


@router.get("/stats", response_model=EmailLogStats)
async def get_email_log_stats(
    days: int = Query(7, ge=1, le=90),
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("email.view_logs", "view email statistics"))
):
    """Get email log statistics for the last N days (PE Level only)"""
    start_date = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    
    # Get counts by status
    status_pipeline = [
        {"$match": {"created_at": {"$gte": start_date}}},
        {"$group": {"_id": "$status", "count": {"$sum": 1}}}
    ]
    status_stats = await db.email_logs.aggregate(status_pipeline).to_list(10)
    by_status = {item["_id"]: item["count"] for item in status_stats if item["_id"]}
    
    # Get counts by template
    template_pipeline = [
        {"$match": {"created_at": {"$gte": start_date}}},
        {"$group": {"_id": "$template_key", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 20}
    ]
    template_stats = await db.email_logs.aggregate(template_pipeline).to_list(20)
    by_template = {item["_id"] or "direct": item["count"] for item in template_stats}
    
    # Get counts by entity type
    entity_pipeline = [
        {"$match": {"created_at": {"$gte": start_date}, "related_entity_type": {"$ne": None}}},
        {"$group": {"_id": "$related_entity_type", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    entity_stats = await db.email_logs.aggregate(entity_pipeline).to_list(20)
    by_entity_type = {item["_id"]: item["count"] for item in entity_stats if item["_id"]}
    
    # Get recent failures
    recent_failures = await db.email_logs.find(
        {"status": "failed", "created_at": {"$gte": start_date}},
        {"_id": 0, "id": 1, "to_email": 1, "subject": 1, "error_message": 1, "created_at": 1}
    ).sort("created_at", -1).limit(10).to_list(10)
    
    return EmailLogStats(
        total_sent=by_status.get("sent", 0),
        total_failed=by_status.get("failed", 0),
        total_skipped=by_status.get("skipped", 0),
        by_template=by_template,
        by_status=by_status,
        by_entity_type=by_entity_type,
        recent_failures=recent_failures
    )


@router.get("/{log_id}", response_model=EmailLog)
async def get_email_log_detail(
    log_id: str,
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("email.view_logs", "view email log detail"))
):
    """Get detailed email log entry (PE Level only)"""
    log = await db.email_logs.find_one({"id": log_id}, {"_id": 0})
    if not log:
        raise HTTPException(status_code=404, detail="Email log not found")
    
    return EmailLog(**log)


@router.get("/by-entity/{entity_type}/{entity_id}")
async def get_emails_by_entity(
    entity_type: str,
    entity_id: str,
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("email.view_logs", "view entity emails"))
):
    """Get all emails related to a specific entity (PE Level only)"""
    logs = await db.email_logs.find(
        {"related_entity_type": entity_type, "related_entity_id": entity_id},
        {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    
    return {
        "entity_type": entity_type,
        "entity_id": entity_id,
        "total": len(logs),
        "logs": logs
    }


@router.post("/{log_id}/resend")
async def resend_email(
    log_id: str,
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("email.resend", "resend emails"))
):
    """Resend a failed or skipped email (PE Level only)
    
    This will attempt to resend the email using the original template and variables.
    Only emails with status 'failed' or 'skipped' can be resent.
    """
    from services.email_service import send_email, get_email_template, render_template
    
    # Get the original email log
    log = await db.email_logs.find_one({"id": log_id}, {"_id": 0})
    if not log:
        raise HTTPException(status_code=404, detail="Email log not found")
    
    # Check if the email can be resent
    if log.get("status") == "sent":
        raise HTTPException(status_code=400, detail="This email was already sent successfully. Cannot resend.")
    
    to_email = log.get("to_email")
    template_key = log.get("template_key")
    variables = log.get("variables", {})
    cc_email = log.get("cc_email")
    related_entity_type = log.get("related_entity_type")
    related_entity_id = log.get("related_entity_id")
    
    if not to_email:
        raise HTTPException(status_code=400, detail="No recipient email found in log")
    
    try:
        if template_key:
            # Resend using template
            template = await get_email_template(template_key)
            if not template:
                raise HTTPException(status_code=400, detail=f"Template '{template_key}' not found. Cannot resend.")
            
            subject, body = render_template(template, variables)
            await send_email(
                to_email=to_email,
                subject=subject,
                body=body,
                cc_email=cc_email,
                template_key=template_key,
                variables=variables,
                related_entity_type=related_entity_type,
                related_entity_id=related_entity_id
            )
        else:
            # For non-template emails, we can't resend without the original body
            raise HTTPException(status_code=400, detail="Cannot resend non-template emails. Original content not stored.")
        
        return {
            "message": f"Email resent successfully to {to_email}",
            "to_email": to_email,
            "template_key": template_key,
            "resent_by": current_user.get("name"),
            "resent_at": datetime.now(timezone.utc).isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to resend email: {str(e)}")


@router.delete("/cleanup")
async def cleanup_old_email_logs(
    days_to_keep: int = Query(90, ge=30, le=365),
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("email.delete_logs", "cleanup email logs"))
):
    """Delete email logs older than specified days (PE Desk only)"""
    cutoff_date = (datetime.now(timezone.utc) - timedelta(days=days_to_keep)).isoformat()
    
    result = await db.email_logs.delete_many({"created_at": {"$lt": cutoff_date}})
    
    return {
        "message": f"Deleted {result.deleted_count} email logs older than {days_to_keep} days",
        "deleted_count": result.deleted_count
    }
