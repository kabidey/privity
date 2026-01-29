"""
Notification service for real-time notifications
"""
import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional
from fastapi import WebSocket

from database import db


class ConnectionManager:
    """WebSocket Connection Manager for Real-time Notifications"""
    
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self.pe_online_users: Dict[str, dict] = {}  # Track PE users online status
    
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
    
    async def broadcast_to_all(self, message: dict):
        """Broadcast a message to all connected users"""
        for user_id in list(self.active_connections.keys()):
            await self.send_to_user(user_id, message)
    
    def update_pe_status(self, user_id: str, user_name: str, user_role: int, role_name: str):
        """Update PE user online status and return if status changed"""
        was_pe_online = self.is_pe_online()
        
        self.pe_online_users[user_id] = {
            "last_seen": datetime.now(timezone.utc),
            "name": user_name,
            "role": user_role,
            "role_name": role_name
        }
        
        is_pe_online_now = self.is_pe_online()
        return was_pe_online != is_pe_online_now
    
    def is_pe_online(self) -> bool:
        """Check if any PE user is currently online (within 60 seconds)"""
        now = datetime.now(timezone.utc)
        stale_threshold = now - timedelta(seconds=60)
        
        # Clean up stale entries
        stale_users = [uid for uid, data in self.pe_online_users.items() 
                       if data["last_seen"] < stale_threshold]
        for uid in stale_users:
            del self.pe_online_users[uid]
        
        return len(self.pe_online_users) > 0
    
    def get_pe_status(self) -> dict:
        """Get current PE online status"""
        now = datetime.now(timezone.utc)
        stale_threshold = now - timedelta(seconds=60)
        
        # Clean up stale entries
        stale_users = [uid for uid, data in self.pe_online_users.items() 
                       if data["last_seen"] < stale_threshold]
        for uid in stale_users:
            del self.pe_online_users[uid]
        
        online_pe_users = []
        for uid, data in self.pe_online_users.items():
            online_pe_users.append({
                "name": data["name"],
                "role_name": data["role_name"],
                "last_seen": data["last_seen"].isoformat()
            })
        
        is_pe_online = len(online_pe_users) > 0
        
        return {
            "pe_online": is_pe_online,
            "online_count": len(online_pe_users),
            "online_users": online_pe_users[:3],  # Limit to 3 for privacy
            "message": "PE Support Available" if is_pe_online else "PE Support Offline"
        }


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
