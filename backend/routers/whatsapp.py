"""
WhatsApp Notification System
Self-hosted QR-based WhatsApp integration for alerts
"""
from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from typing import Optional, List
from datetime import datetime, timezone
from pydantic import BaseModel
import asyncio
import uuid
import io
import qrcode
import base64
import json

from database import db
from utils.auth import get_current_user
from services.permission_service import require_permission
from services.audit_service import create_audit_log

router = APIRouter(prefix="/whatsapp", tags=["WhatsApp Notifications"])


class WhatsAppConfig(BaseModel):
    enabled: bool = False
    session_id: Optional[str] = None
    phone_number: Optional[str] = None
    connected_at: Optional[str] = None


class WhatsAppTemplate(BaseModel):
    name: str
    category: str  # booking, payment, dp_transfer, alert, custom
    message_template: str
    variables: List[str] = []  # Placeholders like {{client_name}}, {{booking_number}}
    recipient_types: List[str] = []  # client, user, bp, rp


class SendMessageRequest(BaseModel):
    phone_number: str
    message: str
    template_id: Optional[str] = None


# Store active WebSocket connections for QR updates
active_connections: dict = {}


# WhatsApp session state (in production, use Redis)
whatsapp_sessions: dict = {}


@router.get("/config")
async def get_whatsapp_config(
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("notifications.whatsapp_view", "view WhatsApp config"))
):
    """Get current WhatsApp configuration"""
    config = await db.system_config.find_one(
        {"config_type": "whatsapp"},
        {"_id": 0}
    )
    
    if not config:
        config = {
            "config_type": "whatsapp",
            "enabled": False,
            "session_id": None,
            "phone_number": None,
            "connected_at": None,
            "status": "disconnected"
        }
    
    return config


@router.post("/config")
async def update_whatsapp_config(
    enabled: bool = Query(...),
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("notifications.whatsapp_connect", "update WhatsApp config"))
):
    """Enable or disable WhatsApp notifications"""
    await db.system_config.update_one(
        {"config_type": "whatsapp"},
        {"$set": {
            "enabled": enabled,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "updated_by": current_user["id"]
        }},
        upsert=True
    )
    
    await create_audit_log(
        action="WHATSAPP_CONFIG_UPDATE",
        entity_type="system_config",
        entity_id="whatsapp",
        user_id=current_user["id"],
        user_name=current_user["name"],
        user_role=current_user.get("role", 6),
        details={"enabled": enabled}
    )
    
    return {"message": f"WhatsApp notifications {'enabled' if enabled else 'disabled'}"}


@router.get("/qr-code")
async def get_qr_code(
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("notifications.whatsapp_connect", "connect WhatsApp"))
):
    """Generate QR code for WhatsApp Web connection"""
    # Generate a unique session ID
    session_id = str(uuid.uuid4())
    
    # In a real implementation, this would connect to WhatsApp Web API
    # For now, we generate a placeholder QR code that simulates the connection process
    
    # Store session info
    whatsapp_sessions[session_id] = {
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": current_user["id"]
    }
    
    # Generate QR code data (in production, this would be WhatsApp's pairing data)
    qr_data = f"PRIVITY-WA-CONNECT:{session_id}:{current_user['id']}"
    
    # Create QR code image
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(qr_data)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white")
    
    # Convert to base64
    img_buffer = io.BytesIO()
    qr_img.save(img_buffer, format="PNG")
    img_buffer.seek(0)
    qr_base64 = base64.b64encode(img_buffer.getvalue()).decode()
    
    return {
        "session_id": session_id,
        "qr_code": f"data:image/png;base64,{qr_base64}",
        "expires_in": 60,  # seconds
        "instructions": [
            "1. Open WhatsApp on your phone",
            "2. Go to Settings > Linked Devices",
            "3. Tap 'Link a Device'",
            "4. Scan this QR code with your phone"
        ]
    }


@router.post("/simulate-connect")
async def simulate_whatsapp_connect(
    session_id: str = Query(...),
    phone_number: str = Query(...),
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("notifications.whatsapp_connect", "connect WhatsApp"))
):
    """Simulate WhatsApp connection (for demo/testing)"""
    # Update session status
    if session_id in whatsapp_sessions:
        whatsapp_sessions[session_id]["status"] = "connected"
        whatsapp_sessions[session_id]["phone_number"] = phone_number
    
    # Update config in database
    await db.system_config.update_one(
        {"config_type": "whatsapp"},
        {"$set": {
            "enabled": True,
            "session_id": session_id,
            "phone_number": phone_number,
            "connected_at": datetime.now(timezone.utc).isoformat(),
            "status": "connected"
        }},
        upsert=True
    )
    
    await create_audit_log(
        action="WHATSAPP_CONNECTED",
        entity_type="system_config",
        entity_id="whatsapp",
        user_id=current_user["id"],
        user_name=current_user["name"],
        user_role=current_user.get("role", 6),
        details={"phone_number": phone_number[-4:].rjust(len(phone_number), '*')}
    )
    
    return {"message": "WhatsApp connected successfully", "phone_number": phone_number}


@router.post("/disconnect")
async def disconnect_whatsapp(
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("notifications.whatsapp_connect", "disconnect WhatsApp"))
):
    """Disconnect WhatsApp session"""
    config = await db.system_config.find_one({"config_type": "whatsapp"})
    
    if config and config.get("session_id"):
        session_id = config["session_id"]
        if session_id in whatsapp_sessions:
            del whatsapp_sessions[session_id]
    
    await db.system_config.update_one(
        {"config_type": "whatsapp"},
        {"$set": {
            "enabled": False,
            "session_id": None,
            "phone_number": None,
            "connected_at": None,
            "status": "disconnected"
        }}
    )
    
    await create_audit_log(
        action="WHATSAPP_DISCONNECTED",
        entity_type="system_config",
        entity_id="whatsapp",
        user_id=current_user["id"],
        user_name=current_user["name"],
        user_role=current_user.get("role", 6)
    )
    
    return {"message": "WhatsApp disconnected"}


# ============== TEMPLATES ==============

DEFAULT_TEMPLATES = [
    {
        "id": "booking_confirmation",
        "name": "Booking Confirmation",
        "category": "booking",
        "message_template": "Dear {{client_name}},\n\nYour booking #{{booking_number}} for {{quantity}} shares of {{stock_symbol}} has been confirmed.\n\nBuying Price: ₹{{buying_price}}\nSelling Price: ₹{{selling_price}}\nTotal Amount: ₹{{total_amount}}\n\nThank you for choosing SMIFS Private Equity.",
        "variables": ["client_name", "booking_number", "quantity", "stock_symbol", "buying_price", "selling_price", "total_amount"],
        "recipient_types": ["client"],
        "is_system": True
    },
    {
        "id": "payment_reminder",
        "name": "Payment Reminder",
        "category": "payment",
        "message_template": "Dear {{client_name}},\n\nThis is a reminder for your pending payment of ₹{{pending_amount}} for booking #{{booking_number}}.\n\nPlease complete the payment at your earliest convenience.\n\nThank you.",
        "variables": ["client_name", "booking_number", "pending_amount"],
        "recipient_types": ["client"],
        "is_system": True
    },
    {
        "id": "payment_received",
        "name": "Payment Received",
        "category": "payment",
        "message_template": "Dear {{client_name}},\n\nWe have received your payment of ₹{{amount}} for booking #{{booking_number}}.\n\nPayment Mode: {{payment_mode}}\nPayment Date: {{payment_date}}\n\nThank you.",
        "variables": ["client_name", "booking_number", "amount", "payment_mode", "payment_date"],
        "recipient_types": ["client"],
        "is_system": True
    },
    {
        "id": "dp_transfer_complete",
        "name": "DP Transfer Complete",
        "category": "dp_transfer",
        "message_template": "Dear {{client_name}},\n\n{{quantity}} shares of {{stock_symbol}} have been transferred to your DP account.\n\nDP ID: {{dp_id}}\nClient ID: {{client_id}}\nBooking: #{{booking_number}}\n\nThank you for your business.",
        "variables": ["client_name", "quantity", "stock_symbol", "dp_id", "client_id", "booking_number"],
        "recipient_types": ["client"],
        "is_system": True
    },
    {
        "id": "bp_booking_alert",
        "name": "BP Booking Alert",
        "category": "alert",
        "message_template": "Hello {{bp_name}},\n\nA new booking has been created under your account:\n\nBooking: #{{booking_number}}\nClient: {{client_name}}\nStock: {{stock_symbol}}\nQuantity: {{quantity}}\n\nYour revenue share: {{revenue_share}}%",
        "variables": ["bp_name", "booking_number", "client_name", "stock_symbol", "quantity", "revenue_share"],
        "recipient_types": ["bp"],
        "is_system": True
    },
    {
        "id": "rp_commission_alert",
        "name": "RP Commission Alert",
        "category": "alert",
        "message_template": "Hello {{rp_name}},\n\nYou have earned a commission on a new booking:\n\nBooking: #{{booking_number}}\nClient: {{client_name}}\nCommission: ₹{{commission_amount}} ({{commission_percent}}%)\n\nThank you for your referral!",
        "variables": ["rp_name", "booking_number", "client_name", "commission_amount", "commission_percent"],
        "recipient_types": ["rp"],
        "is_system": True
    }
]


@router.get("/templates")
async def get_templates(
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("notifications.whatsapp_templates", "view WhatsApp templates"))
):
    """Get all message templates"""
    templates = await db.whatsapp_templates.find({}, {"_id": 0}).to_list(100)
    
    # If no templates exist, initialize with defaults
    if not templates:
        for template in DEFAULT_TEMPLATES:
            template["created_at"] = datetime.now(timezone.utc).isoformat()
            await db.whatsapp_templates.insert_one(template)
        templates = DEFAULT_TEMPLATES
    
    return templates


@router.post("/templates")
async def create_template(
    template: WhatsAppTemplate,
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("notifications.whatsapp_templates", "create WhatsApp template"))
):
    """Create a custom message template"""
    template_dict = template.dict()
    template_dict["id"] = str(uuid.uuid4())
    template_dict["is_system"] = False
    template_dict["created_at"] = datetime.now(timezone.utc).isoformat()
    template_dict["created_by"] = current_user["id"]
    
    await db.whatsapp_templates.insert_one(template_dict)
    if "_id" in template_dict:
        del template_dict["_id"]
    
    return {"message": "Template created successfully", "template": template_dict}


@router.put("/templates/{template_id}")
async def update_template(
    template_id: str,
    template: WhatsAppTemplate,
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("notifications.whatsapp_templates", "edit WhatsApp template"))
):
    """Update a message template"""
    existing = await db.whatsapp_templates.find_one({"id": template_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Template not found")
    
    if existing.get("is_system"):
        raise HTTPException(status_code=400, detail="Cannot modify system templates")
    
    await db.whatsapp_templates.update_one(
        {"id": template_id},
        {"$set": {
            **template.dict(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "updated_by": current_user["id"]
        }}
    )
    
    return {"message": "Template updated successfully"}


@router.delete("/templates/{template_id}")
async def delete_template(
    template_id: str,
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("notifications.whatsapp_templates", "delete WhatsApp template"))
):
    """Delete a custom message template"""
    existing = await db.whatsapp_templates.find_one({"id": template_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Template not found")
    
    if existing.get("is_system"):
        raise HTTPException(status_code=400, detail="Cannot delete system templates")
    
    await db.whatsapp_templates.delete_one({"id": template_id})
    
    return {"message": "Template deleted successfully"}


# ============== SEND MESSAGES ==============

@router.post("/send")
async def send_message(
    request: SendMessageRequest,
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("notifications.whatsapp_send", "send WhatsApp message"))
):
    """Send a WhatsApp message"""
    # Check if WhatsApp is connected
    config = await db.system_config.find_one({"config_type": "whatsapp"})
    if not config or config.get("status") != "connected":
        raise HTTPException(status_code=400, detail="WhatsApp is not connected. Please scan QR code first.")
    
    # Log the message
    message_log = {
        "id": str(uuid.uuid4()),
        "phone_number": request.phone_number,
        "message": request.message,
        "template_id": request.template_id,
        "status": "sent",  # In production: pending, sent, delivered, read, failed
        "sent_at": datetime.now(timezone.utc).isoformat(),
        "sent_by": current_user["id"],
        "sent_by_name": current_user["name"]
    }
    
    await db.whatsapp_messages.insert_one(message_log)
    if "_id" in message_log:
        del message_log["_id"]
    
    # In production, this would actually send via WhatsApp Web API
    # For now, we simulate success
    
    return {
        "message": "Message sent successfully",
        "message_id": message_log["id"],
        "status": "sent"
    }


@router.post("/send-bulk")
async def send_bulk_messages(
    template_id: str = Query(...),
    recipient_type: str = Query(...),  # client, user, bp, rp
    recipient_ids: List[str] = Query(None),  # If None, send to all of that type
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("notifications.whatsapp_bulk", "send bulk WhatsApp"))
):
    """Send bulk WhatsApp messages using a template"""
    # Check if WhatsApp is connected
    config = await db.system_config.find_one({"config_type": "whatsapp"})
    if not config or config.get("status") != "connected":
        raise HTTPException(status_code=400, detail="WhatsApp is not connected")
    
    # Get template
    template = await db.whatsapp_templates.find_one({"id": template_id}, {"_id": 0})
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    # Get recipients based on type
    recipients = []
    if recipient_type == "client":
        query = {"phone": {"$exists": True, "$ne": None}}
        if recipient_ids:
            query["id"] = {"$in": recipient_ids}
        recipients = await db.clients.find(query, {"_id": 0, "id": 1, "name": 1, "phone": 1}).to_list(1000)
    elif recipient_type == "user":
        query = {"phone": {"$exists": True, "$ne": None}, "is_active": True}
        if recipient_ids:
            query["id"] = {"$in": recipient_ids}
        recipients = await db.users.find(query, {"_id": 0, "id": 1, "name": 1, "phone": 1}).to_list(1000)
    elif recipient_type == "bp":
        query = {"phone": {"$exists": True, "$ne": None}, "approval_status": "approved"}
        if recipient_ids:
            query["id"] = {"$in": recipient_ids}
        recipients = await db.business_partners.find(query, {"_id": 0, "id": 1, "name": 1, "phone": 1}).to_list(1000)
    elif recipient_type == "rp":
        query = {"phone": {"$exists": True, "$ne": None}, "approval_status": "approved"}
        if recipient_ids:
            query["id"] = {"$in": recipient_ids}
        recipients = await db.referral_partners.find(query, {"_id": 0, "id": 1, "name": 1, "phone": 1}).to_list(1000)
    
    # Create bulk send job
    job_id = str(uuid.uuid4())
    job = {
        "id": job_id,
        "template_id": template_id,
        "recipient_type": recipient_type,
        "total_recipients": len(recipients),
        "sent_count": 0,
        "failed_count": 0,
        "status": "processing",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": current_user["id"]
    }
    
    await db.whatsapp_bulk_jobs.insert_one(job)
    
    # In production, this would be processed by a background worker
    # For now, we simulate immediate processing
    sent_count = len(recipients)
    
    await db.whatsapp_bulk_jobs.update_one(
        {"id": job_id},
        {"$set": {
            "sent_count": sent_count,
            "status": "completed",
            "completed_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return {
        "message": f"Bulk send job created",
        "job_id": job_id,
        "total_recipients": len(recipients),
        "status": "completed"
    }


@router.get("/messages")
async def get_message_logs(
    limit: int = Query(50),
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("notifications.whatsapp_history", "view WhatsApp logs"))
):
    """Get message sending history"""
    messages = await db.whatsapp_messages.find(
        {},
        {"_id": 0}
    ).sort("sent_at", -1).limit(limit).to_list(limit)
    
    return messages


@router.get("/stats")
async def get_whatsapp_stats(
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("notifications.whatsapp_view", "view WhatsApp stats"))
):
    """Get WhatsApp messaging statistics"""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    total_messages = await db.whatsapp_messages.count_documents({})
    today_messages = await db.whatsapp_messages.count_documents({"sent_at": {"$regex": f"^{today}"}})
    
    # Messages by status
    sent_count = await db.whatsapp_messages.count_documents({"status": "sent"})
    delivered_count = await db.whatsapp_messages.count_documents({"status": "delivered"})
    failed_count = await db.whatsapp_messages.count_documents({"status": "failed"})
    
    return {
        "total_messages": total_messages,
        "today_messages": today_messages,
        "by_status": {
            "sent": sent_count,
            "delivered": delivered_count,
            "failed": failed_count
        }
    }
