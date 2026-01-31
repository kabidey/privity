"""
Group Chat Router
Handles real-time group chat functionality for all users.
"""
from fastapi import APIRouter, HTTPException, Depends, WebSocket, WebSocketDisconnect
from datetime import datetime, timezone
from typing import List, Dict, Set
from pydantic import BaseModel
import json
import asyncio
import uuid

from database import db
from utils.auth import get_current_user, decode_token

router = APIRouter(prefix="/group-chat", tags=["Group Chat"])


# WebSocket connection manager for group chat
class GroupChatManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}  # user_id -> websocket
        self.user_info: Dict[str, dict] = {}  # user_id -> {name, role, role_name}
    
    async def connect(self, websocket: WebSocket, user_id: str, user_info: dict):
        self.active_connections[user_id] = websocket
        self.user_info[user_id] = user_info
        # Broadcast user joined
        await self.broadcast_system_message(f"{user_info['name']} joined the chat")
        # Send online users list to all
        await self.broadcast_online_users()
    
    def disconnect(self, user_id: str):
        if user_id in self.active_connections:
            user_info = self.user_info.get(user_id, {})
            del self.active_connections[user_id]
            if user_id in self.user_info:
                del self.user_info[user_id]
            return user_info.get('name', 'Unknown')
        return None
    
    async def broadcast_message(self, message: dict):
        """Broadcast a message to all connected users"""
        message_json = json.dumps(message)
        disconnected = []
        for user_id, connection in self.active_connections.items():
            try:
                await connection.send_text(message_json)
            except Exception:
                disconnected.append(user_id)
        # Clean up disconnected users
        for user_id in disconnected:
            self.disconnect(user_id)
    
    async def broadcast_system_message(self, content: str):
        """Broadcast a system message"""
        await self.broadcast_message({
            "type": "system",
            "content": content,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    
    async def broadcast_online_users(self):
        """Broadcast list of online users to all connections"""
        online_users = [
            {"id": uid, "name": info["name"], "role_name": info["role_name"]}
            for uid, info in self.user_info.items()
        ]
        await self.broadcast_message({
            "type": "online_users",
            "users": online_users,
            "count": len(online_users)
        })
    
    def get_online_count(self) -> int:
        return len(self.active_connections)


# Global chat manager instance
chat_manager = GroupChatManager()


class ChatMessage(BaseModel):
    content: str


@router.get("/messages")
async def get_chat_messages(
    limit: int = 50,
    before_id: str = None,
    current_user: dict = Depends(get_current_user)
):
    """Get recent chat messages"""
    query = {}
    if before_id:
        # Get messages before a specific message ID for pagination
        ref_msg = await db.group_chat_messages.find_one({"id": before_id})
        if ref_msg:
            query["created_at"] = {"$lt": ref_msg["created_at"]}
    
    messages = await db.group_chat_messages.find(
        query,
        {"_id": 0}
    ).sort("created_at", -1).limit(limit).to_list(limit)
    
    # Reverse to get chronological order
    messages.reverse()
    
    return messages


@router.post("/messages")
async def send_chat_message(
    message: ChatMessage,
    current_user: dict = Depends(get_current_user)
):
    """Send a message to the group chat"""
    if not message.content.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    
    if len(message.content) > 1000:
        raise HTTPException(status_code=400, detail="Message too long (max 1000 characters)")
    
    # Get role name
    role_names = {
        1: "PE Desk",
        2: "PE Manager",
        3: "Finance",
        4: "Manager",
        5: "Employee",
        6: "Intern",
        7: "Referral Partner",
        8: "Business Partner"
    }
    
    message_doc = {
        "id": str(uuid.uuid4()),
        "user_id": current_user["id"],
        "user_name": current_user["name"],
        "user_role": current_user.get("role", 5),
        "user_role_name": role_names.get(current_user.get("role", 5), "User"),
        "content": message.content.strip(),
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.group_chat_messages.insert_one(message_doc)
    
    # Broadcast to all connected WebSocket clients
    await chat_manager.broadcast_message({
        "type": "message",
        "message": {k: v for k, v in message_doc.items() if k != "_id"}
    })
    
    return {"status": "sent", "message_id": message_doc["id"]}


@router.get("/online-users")
async def get_online_users(current_user: dict = Depends(get_current_user)):
    """Get list of currently online users"""
    online_users = [
        {"id": uid, "name": info["name"], "role_name": info["role_name"]}
        for uid, info in chat_manager.user_info.items()
    ]
    return {
        "users": online_users,
        "count": len(online_users)
    }


# Export the chat manager for use in server.py WebSocket endpoint
def get_chat_manager():
    return chat_manager
