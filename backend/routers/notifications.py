"""
Notification routes and WebSocket endpoint
"""
import logging
import jwt
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query, HTTPException

from database import db
from config import JWT_SECRET, JWT_ALGORITHM
from utils.auth import get_current_user
from services.notification_service import ws_manager

router = APIRouter(prefix="/notifications", tags=["Notifications"])


def decode_ws_token(token: str) -> dict:
    """Decode JWT token for WebSocket authentication"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


@router.get("")
async def get_notifications(
    unread_only: bool = False,
    limit: int = 50,
    current_user: dict = Depends(get_current_user)
):
    """Get user notifications"""
    query = {"user_id": current_user["id"]}
    if unread_only:
        query["read"] = False
    
    notifications = await db.notifications.find(
        query, {"_id": 0}
    ).sort("created_at", -1).limit(limit).to_list(limit)
    
    return notifications


@router.get("/unread-count")
async def get_unread_count(current_user: dict = Depends(get_current_user)):
    """Get count of unread notifications"""
    count = await db.notifications.count_documents({
        "user_id": current_user["id"],
        "read": False
    })
    return {"count": count}


@router.put("/{notification_id}/read")
async def mark_as_read(notification_id: str, current_user: dict = Depends(get_current_user)):
    """Mark notification as read"""
    result = await db.notifications.update_one(
        {"id": notification_id, "user_id": current_user["id"]},
        {"$set": {"read": True}}
    )
    
    if result.modified_count == 0:
        return {"message": "Notification not found or already read"}
    
    return {"message": "Notification marked as read"}


@router.put("/read-all")
async def mark_all_as_read(current_user: dict = Depends(get_current_user)):
    """Mark all notifications as read"""
    result = await db.notifications.update_many(
        {"user_id": current_user["id"], "read": False},
        {"$set": {"read": True}}
    )
    
    return {"message": f"Marked {result.modified_count} notifications as read"}


@router.delete("/{notification_id}")
async def delete_notification(notification_id: str, current_user: dict = Depends(get_current_user)):
    """Delete a notification"""
    result = await db.notifications.delete_one({
        "id": notification_id,
        "user_id": current_user["id"]
    })
    
    if result.deleted_count == 0:
        return {"message": "Notification not found"}
    
    return {"message": "Notification deleted"}
