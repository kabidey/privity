"""
Audit service for logging actions
"""
import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from database import db
from config import AUDIT_ACTIONS


async def create_audit_log(
    action: str,
    entity_type: str,
    entity_id: str,
    user_id: str,
    user_name: str,
    user_role: int,
    entity_name: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None
):
    """Create an audit log entry"""
    try:
        audit_doc = {
            "id": str(uuid.uuid4()),
            "action": action,
            "action_description": AUDIT_ACTIONS.get(action, action),
            "entity_type": entity_type,
            "entity_id": entity_id,
            "entity_name": entity_name,
            "user_id": user_id,
            "user_name": user_name,
            "user_role": user_role,
            "details": details,
            "ip_address": ip_address,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        await db.audit_logs.insert_one(audit_doc)
        logging.info(f"Audit: {action} by {user_name} on {entity_type}/{entity_id}")
    except Exception as e:
        logging.error(f"Failed to create audit log: {e}")
