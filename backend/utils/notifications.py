"""
WebSocket manager for real-time notifications
"""
import json
import logging
from typing import Dict, List
from fastapi import WebSocket
from datetime import datetime, timezone
import uuid
from database import db

class ConnectionManager:
    def __init__(self):
        # Map user_id to list of websocket connections
        self.active_connections: Dict[str, List[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, user_id: str):
        """Accept websocket connection and add to user's connections"""
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
        logging.info(f"WebSocket connected for user {user_id}")
    
    def disconnect(self, websocket: WebSocket, user_id: str):
        """Remove websocket connection"""
        if user_id in self.active_connections:
            if websocket in self.active_connections[user_id]:
                self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        logging.info(f"WebSocket disconnected for user {user_id}")
    
    async def send_to_user(self, user_id: str, message: dict):
        """Send message to specific user"""
        if user_id in self.active_connections:
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logging.error(f"Failed to send to user {user_id}: {e}")
    
    async def send_to_role(self, role: int, message: dict):
        """Send message to all users with specific role"""
        # Get all users with this role
        users = await db.users.find({"role": role}, {"id": 1}).to_list(1000)
        for user in users:
            await self.send_to_user(user["id"], message)
    
    async def send_to_roles(self, roles: List[int], message: dict):
        """Send message to all users with any of the specified roles"""
        users = await db.users.find({"role": {"$in": roles}}, {"id": 1}).to_list(1000)
        for user in users:
            await self.send_to_user(user["id"], message)
    
    async def broadcast(self, message: dict):
        """Send message to all connected users"""
        for user_id in self.active_connections:
            await self.send_to_user(user_id, message)

# Global connection manager
manager = ConnectionManager()

async def create_notification(
    user_id: str,
    notification_type: str,
    title: str,
    message: str,
    data: dict = None
) -> dict:
    """Create and store notification, then send via WebSocket"""
    notification = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "type": notification_type,
        "title": title,
        "message": message,
        "data": data or {},
        "read": False,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    # Store in database
    await db.notifications.insert_one({**notification, "_id": notification["id"]})
    
    # Send via WebSocket
    await manager.send_to_user(user_id, {
        "event": "notification",
        "data": notification
    })
    
    return notification

async def notify_role(
    role: int,
    notification_type: str,
    title: str,
    message: str,
    data: dict = None
):
    """Create notifications for all users with specific role"""
    users = await db.users.find({"role": role}, {"id": 1}).to_list(1000)
    for user in users:
        await create_notification(user["id"], notification_type, title, message, data)

async def notify_roles(
    roles: List[int],
    notification_type: str,
    title: str,
    message: str,
    data: dict = None
):
    """Create notifications for all users with any of the specified roles"""
    users = await db.users.find({"role": {"$in": roles}}, {"id": 1}).to_list(1000)
    for user in users:
        await create_notification(user["id"], notification_type, title, message, data)
