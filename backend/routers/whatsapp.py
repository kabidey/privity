"""
WhatsApp Notification System - Wati.io API Integration
Replaces QR-based system with official Wati.io Business API
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, List
from datetime import datetime, timezone
from pydantic import BaseModel
import uuid
import httpx
import logging
import os

from database import db
from utils.auth import get_current_user
from services.permission_service import require_permission
from services.audit_service import create_audit_log

router = APIRouter(prefix="/whatsapp", tags=["WhatsApp Notifications"])
logger = logging.getLogger(__name__)


# ============== MODELS ==============

class WatiConfig(BaseModel):
    api_endpoint: str
    api_token: str
    enabled: bool = False


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


class SendTemplateRequest(BaseModel):
    phone_number: str
    template_name: str
    parameters: Optional[List[str]] = None
    broadcast_name: Optional[str] = None


class BulkSendRequest(BaseModel):
    phone_numbers: List[str]
    template_name: str
    parameters: Optional[List[str]] = None
    broadcast_name: Optional[str] = None


# ============== WATI SERVICE ==============

class WatiService:
    """Wati.io WhatsApp Business API Service - v3 API"""
    
    def __init__(self, endpoint: str, token: str):
        self.endpoint = endpoint.rstrip('/')
        self.token = token
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
    
    async def send_session_message(self, phone_number: str, message: str) -> dict:
        """Send a message within active WhatsApp session (24-hour window)"""
        # Remove non-digits and ensure proper format
        phone = ''.join(filter(str.isdigit, phone_number))
        if not phone.startswith('91'):
            phone = '91' + phone
        
        # v3 API endpoint for sending session messages
        url = f"{self.endpoint}/api/ext/v3/conversations/{phone}/messages"
        payload = {"text": message}
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url, json=payload, headers=self.headers, timeout=30.0
                )
                response.raise_for_status()
                return {"result": True, **response.json()}
        except httpx.HTTPStatusError as e:
            logger.error(f"Wati session message error: {e.response.status_code} - {e.response.text}")
            # Try v1 API as fallback
            return await self._send_session_message_v1(phone, message)
        except httpx.HTTPError as e:
            logger.error(f"Wati session message error: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to send message: {str(e)}")
    
    async def _send_session_message_v1(self, phone: str, message: str) -> dict:
        """Fallback to v1 API for session messages"""
        url = f"{self.endpoint}/api/v1/sendSessionMessage/{phone}"
        payload = {"messageText": message}
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url, json=payload, headers=self.headers, timeout=30.0
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Wati v1 session message error: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to send message: {str(e)}")
    
    async def send_template_message(
        self, 
        phone_number: str, 
        template_name: str,
        parameters: Optional[List[str]] = None,
        broadcast_name: Optional[str] = None
    ) -> dict:
        """Send a pre-approved template message using v3 API"""
        phone = ''.join(filter(str.isdigit, phone_number))
        if not phone.startswith('91'):
            phone = '91' + phone
        
        # v3 API endpoint for sending template messages
        url = f"{self.endpoint}/api/ext/v3/messageTemplates/send"
        payload = {
            "whatsappNumber": phone,
            "templateName": template_name,
            "broadcastName": broadcast_name or f"template_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "parameters": [{"name": f"param{i+1}", "value": p} for i, p in enumerate(parameters or [])]
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url, json=payload, headers=self.headers, timeout=30.0
                )
                response.raise_for_status()
                return {"result": True, **response.json()}
        except httpx.HTTPStatusError as e:
            logger.error(f"Wati v3 template error: {e.response.status_code} - {e.response.text}")
            # Try v2 API as fallback
            return await self._send_template_message_v2(phone, template_name, parameters, broadcast_name)
        except httpx.HTTPError as e:
            logger.error(f"Wati template message error: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to send template: {str(e)}")
    
    async def _send_template_message_v2(
        self, 
        phone: str, 
        template_name: str,
        parameters: Optional[List[str]] = None,
        broadcast_name: Optional[str] = None
    ) -> dict:
        """Fallback to v2 API for template messages"""
        url = f"{self.endpoint}/api/v2/sendTemplateMessage?whatsappNumber={phone}"
        payload = {
            "template_name": template_name,
            "parameters": parameters or []
        }
        if broadcast_name:
            payload["broadcast_name"] = broadcast_name
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url, json=payload, headers=self.headers, timeout=30.0
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Wati v2 template message error: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to send template: {str(e)}")
                    url, json=payload, headers=self.headers, timeout=30.0
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Wati template message error: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to send template: {str(e)}")
    
    async def send_bulk_template(
        self,
        phone_numbers: List[str],
        template_name: str,
        parameters: Optional[List[str]] = None,
        broadcast_name: Optional[str] = None
    ) -> dict:
        """Send template to multiple recipients"""
        url = f"{self.endpoint}/api/v1/sendTemplateMessage"
        
        receivers = []
        for phone in phone_numbers:
            clean_phone = ''.join(filter(str.isdigit, phone))
            if not clean_phone.startswith('91'):
                clean_phone = '91' + clean_phone
            receivers.append({
                "whatsappNumber": clean_phone,
                "customParams": parameters or []
            })
        
        payload = {
            "template_name": template_name,
            "broadcast_name": broadcast_name or f"bulk_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "receivers": receivers
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url, json=payload, headers=self.headers, timeout=60.0
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Wati bulk message error: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to send bulk messages: {str(e)}")
    
    async def get_templates(self) -> dict:
        """Get all templates from Wati account"""
        url = f"{self.endpoint}/api/v1/getMessageTemplates"
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url, headers=self.headers, timeout=10.0
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Wati get templates error: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to get templates: {str(e)}")
    
    async def test_connection(self) -> bool:
        """Test if Wati connection is working"""
        try:
            result = await self.get_templates()
            return result.get("result", False)
        except Exception:
            return False


async def get_wati_service() -> Optional[WatiService]:
    """Get Wati service instance from database config"""
    config = await db.system_config.find_one({"config_type": "whatsapp"}, {"_id": 0})
    
    if not config or not config.get("enabled"):
        return None
    
    api_endpoint = config.get("api_endpoint")
    api_token = config.get("api_token")
    
    if not api_endpoint or not api_token:
        return None
    
    return WatiService(api_endpoint, api_token)


# ============== CONFIG ENDPOINTS ==============

@router.get("/config")
async def get_whatsapp_config(
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("notifications.whatsapp_view", "view WhatsApp config"))
):
    """Get current WhatsApp/Wati configuration"""
    config = await db.system_config.find_one(
        {"config_type": "whatsapp"},
        {"_id": 0}
    )
    
    if not config:
        config = {
            "config_type": "whatsapp",
            "enabled": False,
            "api_endpoint": None,
            "api_token": None,
            "status": "disconnected",
            "connected_at": None
        }
    
    # Mask the API token for security
    if config.get("api_token"):
        token = config["api_token"]
        config["api_token_masked"] = f"{'*' * 20}...{token[-4:]}" if len(token) > 4 else "****"
        # Don't expose full token
        del config["api_token"]
    
    return config


@router.post("/config")
async def save_wati_config(
    api_endpoint: str = Query(..., description="Wati API endpoint URL"),
    api_token: str = Query(..., description="Wati API access token"),
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("notifications.whatsapp_connect", "configure WhatsApp"))
):
    """Save Wati.io API configuration and test connection"""
    # Clean the endpoint
    api_endpoint = api_endpoint.rstrip('/')
    
    # Create service and test connection
    service = WatiService(api_endpoint, api_token)
    is_connected = await service.test_connection()
    
    if not is_connected:
        raise HTTPException(
            status_code=400, 
            detail="Failed to connect to Wati.io. Please check your API endpoint and token."
        )
    
    # Save config
    await db.system_config.update_one(
        {"config_type": "whatsapp"},
        {"$set": {
            "config_type": "whatsapp",
            "api_endpoint": api_endpoint,
            "api_token": api_token,
            "enabled": True,
            "status": "connected",
            "connected_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "updated_by": current_user["id"]
        }},
        upsert=True
    )
    
    await create_audit_log(
        action="WHATSAPP_WATI_CONNECTED",
        entity_type="system_config",
        entity_id="whatsapp",
        user_id=current_user["id"],
        user_name=current_user["name"],
        user_role=current_user.get("role", 6),
        details={"api_endpoint": api_endpoint}
    )
    
    return {"message": "Wati.io connected successfully", "status": "connected"}


@router.post("/disconnect")
async def disconnect_whatsapp(
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("notifications.whatsapp_connect", "disconnect WhatsApp"))
):
    """Disconnect Wati.io integration"""
    await db.system_config.update_one(
        {"config_type": "whatsapp"},
        {"$set": {
            "enabled": False,
            "status": "disconnected",
            "api_token": None,
            "disconnected_at": datetime.now(timezone.utc).isoformat()
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


@router.post("/test-connection")
async def test_wati_connection(
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("notifications.whatsapp_connect", "test WhatsApp connection"))
):
    """Test current Wati.io connection"""
    service = await get_wati_service()
    
    if not service:
        return {"connected": False, "message": "Wati.io not configured"}
    
    is_connected = await service.test_connection()
    
    if is_connected:
        # Update status
        await db.system_config.update_one(
            {"config_type": "whatsapp"},
            {"$set": {"status": "connected", "last_tested": datetime.now(timezone.utc).isoformat()}}
        )
        return {"connected": True, "message": "Connection successful"}
    else:
        await db.system_config.update_one(
            {"config_type": "whatsapp"},
            {"$set": {"status": "error"}}
        )
        return {"connected": False, "message": "Connection failed - check credentials"}


# ============== TEMPLATES ==============

DEFAULT_TEMPLATES = [
    {
        "id": "booking_confirmation",
        "name": "Booking Confirmation",
        "category": "booking",
        "message_template": "Dear {{client_name}},\n\nYour booking #{{booking_number}} for {{quantity}} shares of {{stock_symbol}} has been confirmed.\n\nTotal Amount: ₹{{total_amount}}\n\nThank you for choosing SMIFS Private Equity.",
        "variables": ["client_name", "booking_number", "quantity", "stock_symbol", "total_amount"],
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
        "message_template": "Dear {{client_name}},\n\n{{quantity}} shares of {{stock_symbol}} have been transferred to your DP account.\n\nDP ID: {{dp_id}}\nBooking: #{{booking_number}}\n\nThank you for your business.",
        "variables": ["client_name", "quantity", "stock_symbol", "dp_id", "booking_number"],
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
    """Get all message templates (local + Wati)"""
    # Get local templates
    templates = await db.whatsapp_templates.find({}, {"_id": 0}).to_list(100)
    
    # If no templates exist, initialize with defaults
    if not templates:
        for template in DEFAULT_TEMPLATES:
            template["created_at"] = datetime.now(timezone.utc).isoformat()
            await db.whatsapp_templates.insert_one(template)
        templates = DEFAULT_TEMPLATES.copy()
    
    # Try to get Wati templates if connected
    service = await get_wati_service()
    if service:
        try:
            wati_templates = await service.get_templates()
            if wati_templates.get("result"):
                # Mark these as wati templates
                for wt in wati_templates.get("messageTemplates", []):
                    wt["is_wati"] = True
                    wt["source"] = "wati"
                return {
                    "local_templates": templates,
                    "wati_templates": wati_templates.get("messageTemplates", [])
                }
        except Exception as e:
            logger.warning(f"Could not fetch Wati templates: {e}")
    
    return {"local_templates": templates, "wati_templates": []}


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
    """Send a WhatsApp message via Wati.io"""
    service = await get_wati_service()
    if not service:
        raise HTTPException(status_code=400, detail="WhatsApp not configured. Please set up Wati.io API credentials.")
    
    # Send message
    result = await service.send_session_message(request.phone_number, request.message)
    
    # Log the message
    message_log = {
        "id": str(uuid.uuid4()),
        "phone_number": request.phone_number,
        "message": request.message,
        "template_id": request.template_id,
        "status": "sent" if result.get("result") else "failed",
        "wati_message_id": result.get("localMessageId"),
        "sent_at": datetime.now(timezone.utc).isoformat(),
        "sent_by": current_user["id"],
        "sent_by_name": current_user["name"]
    }
    await db.whatsapp_messages.insert_one(message_log)
    
    return {
        "message": "Message sent successfully" if result.get("result") else "Message sending failed",
        "result": result.get("result", False),
        "message_id": result.get("localMessageId")
    }


@router.post("/send-template")
async def send_template_message(
    request: SendTemplateRequest,
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("notifications.whatsapp_send", "send WhatsApp template"))
):
    """Send a pre-approved Wati template message"""
    service = await get_wati_service()
    if not service:
        raise HTTPException(status_code=400, detail="WhatsApp not configured. Please set up Wati.io API credentials.")
    
    result = await service.send_template_message(
        request.phone_number,
        request.template_name,
        request.parameters,
        request.broadcast_name
    )
    
    # Log the message
    message_log = {
        "id": str(uuid.uuid4()),
        "phone_number": request.phone_number,
        "template_name": request.template_name,
        "parameters": request.parameters,
        "status": "sent" if result.get("result") else "failed",
        "wati_message_id": result.get("localMessageId"),
        "sent_at": datetime.now(timezone.utc).isoformat(),
        "sent_by": current_user["id"],
        "sent_by_name": current_user["name"]
    }
    await db.whatsapp_messages.insert_one(message_log)
    
    return {
        "message": "Template sent successfully" if result.get("result") else "Template sending failed",
        "result": result.get("result", False),
        "message_id": result.get("localMessageId")
    }


@router.post("/send-bulk")
async def send_bulk_messages(
    request: BulkSendRequest,
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("notifications.whatsapp_bulk", "send bulk WhatsApp messages"))
):
    """Send template message to multiple recipients via Wati.io"""
    service = await get_wati_service()
    if not service:
        raise HTTPException(status_code=400, detail="WhatsApp not configured. Please set up Wati.io API credentials.")
    
    if len(request.phone_numbers) > 1000:
        raise HTTPException(status_code=400, detail="Maximum 1000 recipients per bulk send")
    
    result = await service.send_bulk_template(
        request.phone_numbers,
        request.template_name,
        request.parameters,
        request.broadcast_name
    )
    
    # Log bulk send
    bulk_log = {
        "id": str(uuid.uuid4()),
        "type": "bulk",
        "recipient_count": len(request.phone_numbers),
        "template_name": request.template_name,
        "broadcast_name": request.broadcast_name,
        "status": "sent" if result.get("result") else "failed",
        "sent_at": datetime.now(timezone.utc).isoformat(),
        "sent_by": current_user["id"],
        "sent_by_name": current_user["name"]
    }
    await db.whatsapp_messages.insert_one(bulk_log)
    
    return {
        "message": f"Bulk message sent to {len(request.phone_numbers)} recipients",
        "result": result.get("result", False),
        "recipients_count": len(request.phone_numbers)
    }


# ============== MESSAGE HISTORY ==============

@router.get("/messages")
async def get_messages(
    limit: int = Query(50, ge=1, le=500),
    skip: int = Query(0, ge=0),
    phone_filter: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("notifications.whatsapp_history", "view WhatsApp history"))
):
    """Get message history"""
    query = {}
    if phone_filter:
        query["phone_number"] = {"$regex": phone_filter, "$options": "i"}
    
    messages = await db.whatsapp_messages.find(
        query, {"_id": 0}
    ).sort("sent_at", -1).skip(skip).limit(limit).to_list(limit)
    
    total = await db.whatsapp_messages.count_documents(query)
    
    return {
        "messages": messages,
        "total": total,
        "limit": limit,
        "skip": skip
    }


@router.get("/stats")
async def get_stats(
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("notifications.whatsapp_view", "view WhatsApp stats"))
):
    """Get WhatsApp messaging statistics"""
    # Get config status
    config = await db.system_config.find_one({"config_type": "whatsapp"}, {"_id": 0})
    is_connected = config.get("status") == "connected" if config else False
    
    # Get message counts
    total_messages = await db.whatsapp_messages.count_documents({})
    sent_count = await db.whatsapp_messages.count_documents({"status": "sent"})
    failed_count = await db.whatsapp_messages.count_documents({"status": "failed"})
    
    # Get today's stats
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    today_messages = await db.whatsapp_messages.count_documents({
        "sent_at": {"$gte": today_start}
    })
    
    return {
        "connected": is_connected,
        "total_messages": total_messages,
        "sent": sent_count,
        "failed": failed_count,
        "today_messages": today_messages,
        "connection_type": "wati_api"
    }
