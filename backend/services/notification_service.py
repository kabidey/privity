"""
Notification service for real-time notifications
"""
import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from fastapi import WebSocket

from database import db


class ConnectionManager:
    """WebSocket Connection Manager for Real-time Notifications"""
    
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
        logging.info(f"WebSocket connected for user {user_id}")
    
    def disconnect(self, websocket: WebSocket, user_id: str):
        if user_id in self.active_connections:
            if websocket in self.active_connections[user_id]:
                self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        logging.info(f"WebSocket disconnected for user {user_id}")
    
    async def send_to_user(self, user_id: str, message: dict):
        if user_id in self.active_connections:
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logging.error(f"Failed to send to user {user_id}: {e}")
    
    async def send_to_roles(self, roles: List[int], message: dict):
        users = await db.users.find({"role": {"$in": roles}}, {"id": 1}).to_list(1000)
        for user in users:
            await self.send_to_user(user["id"], message)


# Global WebSocket manager instance
ws_manager = ConnectionManager()


async def create_notification(
    user_id: str,
    notif_type: str,
    title: str,
    message: str,
    data: Optional[Dict[str, Any]] = None
) -> dict:
    """Create and store notification, then send via WebSocket"""
    notification = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "type": notif_type,
        "title": title,
        "message": message,
        "data": data or {},
        "read": False,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    # Insert a copy to avoid _id being added to original dict
    await db.notifications.insert_one(notification.copy())
    
    # Send via WebSocket (without _id)
    await ws_manager.send_to_user(user_id, {
        "event": "notification",
        "data": notification
    })
    
    return notification


async def notify_roles(
    roles: List[int],
    notif_type: str,
    title: str,
    message: str,
    data: Optional[Dict[str, Any]] = None
):
    """Create notifications for all users with specified roles"""
    users = await db.users.find({"role": {"$in": roles}}, {"id": 1}).to_list(1000)
    for user in users:
        await create_notification(user["id"], notif_type, title, message, data)
