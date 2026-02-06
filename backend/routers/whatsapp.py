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
    """
    Wati.io WhatsApp Business API Service
    
    Supports both v1 and v3 APIs:
    - v1 API: https://{endpoint}/api/v1/...
    - v3 API: https://live-mt-server.wati.io/api/ext/v3/...
    
    API Documentation: https://docs.wati.io/reference
    """
    
    def __init__(self, endpoint: str, token: str, api_version: str = "v1"):
        """
        Initialize Wati service
        
        Args:
            endpoint: Your Wati API endpoint (e.g., https://live-mt-server.wati.io)
            token: Your API Bearer token
            api_version: API version to use ("v1" or "v3")
        """
        # Normalize endpoint - ensure it doesn't have trailing slash
        self.endpoint = endpoint.rstrip('/')
        self.token = token
        self.api_version = api_version
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        # Set up API-version specific base URLs
        # v3 uses a different endpoint format
        if api_version == "v3":
            self.v3_base = f"{self.endpoint}/api/ext/v3"
        self.v1_base = f"{self.endpoint}/api/v1"
    
    async def test_connection(self) -> dict:
        """
        Test the Wati API connection
        Tries v1 first, then v3 if v1 fails
        """
        errors = []
        
        # Try v1 API first - getMessageTemplates
        v1_url = f"{self.v1_base}/getMessageTemplates"
        try:
            async with httpx.AsyncClient(verify=True, timeout=15.0) as client:
                response = await client.get(v1_url, headers=self.headers)
                logger.info(f"Wati v1 test response: {response.status_code}")
                if response.status_code == 200:
                    return {
                        "connected": True, 
                        "message": "Successfully connected to Wati.io (v1 API)",
                        "api_version": "v1"
                    }
                elif response.status_code == 401:
                    errors.append("v1: Authentication failed - check your API token")
                else:
                    errors.append(f"v1: Status {response.status_code}")
        except httpx.ConnectError as e:
            errors.append(f"v1: Connection failed - {str(e)}")
        except httpx.TimeoutException:
            errors.append("v1: Connection timed out")
        except Exception as e:
            errors.append(f"v1: {str(e)}")
        
        # Try v3 API - messageTemplates
        if self.api_version == "v3" or not errors[0].startswith("v1: Authentication"):
            v3_url = f"{self.endpoint}/api/ext/v3/messageTemplates"
            try:
                async with httpx.AsyncClient(verify=True, timeout=15.0) as client:
                    response = await client.get(v3_url, headers=self.headers)
                    logger.info(f"Wati v3 test response: {response.status_code}")
                    if response.status_code == 200:
                        return {
                            "connected": True, 
                            "message": "Successfully connected to Wati.io (v3 API)",
                            "api_version": "v3"
                        }
                    elif response.status_code == 401:
                        errors.append("v3: Authentication failed")
                    else:
                        errors.append(f"v3: Status {response.status_code}")
            except httpx.ConnectError as e:
                errors.append(f"v3: Connection failed - {str(e)}")
            except httpx.TimeoutException:
                errors.append("v3: Connection timed out")
            except Exception as e:
                errors.append(f"v3: {str(e)}")
        
        logger.error(f"Wati connection test failed: {errors}")
        return {
            "connected": False, 
            "message": f"Connection failed. Errors: {'; '.join(errors)}",
            "errors": errors
        }
    
    async def send_session_message(self, phone_number: str, message: str) -> dict:
        """
        Send a message within active WhatsApp session (24-hour window)
        Uses v1 API: POST /api/v1/sendSessionMessage/{phone}
        """
        phone = self._normalize_phone(phone_number)
        
        # v1 API endpoint
        url = f"{self.v1_base}/sendSessionMessage/{phone}"
        payload = {"messageText": message}
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=payload, headers=self.headers)
                logger.info(f"Wati session message response: {response.status_code}")
                
                if response.status_code == 200:
                    return {"success": True, "result": response.json()}
                else:
                    return {"success": False, "error": response.text, "status": response.status_code}
        except Exception as e:
            logger.error(f"Wati session message error: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def send_template_message_v1(
        self, 
        phone_number: str, 
        template_name: str,
        parameters: Optional[List[dict]] = None,
        broadcast_name: Optional[str] = None
    ) -> dict:
        """
        Send a template message using v1 API
        POST /api/v1/sendTemplateMessage?whatsappNumber={phone}
        
        Args:
            phone_number: Recipient phone with country code
            template_name: Name of the approved template
            parameters: List of {name: str, value: str} for template variables
            broadcast_name: Name for this broadcast (for tracking)
        """
        phone = self._normalize_phone(phone_number)
        
        url = f"{self.v1_base}/sendTemplateMessage?whatsappNumber={phone}"
        payload = {
            "template_name": template_name,
            "broadcast_name": broadcast_name or f"api_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        }
        
        if parameters:
            payload["parameters"] = parameters
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=payload, headers=self.headers)
                logger.info(f"Wati v1 template response: {response.status_code} - {response.text[:200]}")
                
                if response.status_code == 200:
                    return {"success": True, "api_version": "v1", "result": response.json()}
                else:
                    return {"success": False, "api_version": "v1", "error": response.text, "status": response.status_code}
        except Exception as e:
            logger.error(f"Wati v1 template error: {str(e)}")
            return {"success": False, "api_version": "v1", "error": str(e)}
    
    async def send_template_message_v3(
        self, 
        template_name: str,
        broadcast_name: str,
        recipients: List[dict],
        channel: Optional[str] = None
    ) -> dict:
        """
        Send template messages using v3 API (supports bulk sending)
        POST /api/ext/v3/messageTemplates/send
        
        Args:
            template_name: Name of the approved template
            broadcast_name: Name for this broadcast
            recipients: List of recipients with format:
                [{"whatsappNumber": "919876543210", "customParams": [{"name": "1", "value": "John"}]}]
            channel: Channel name/number (optional, uses default if null)
        """
        url = f"{self.endpoint}/api/ext/v3/messageTemplates/send"
        payload = {
            "template_name": template_name,
            "broadcast_name": broadcast_name,
            "recipients": recipients
        }
        
        if channel:
            payload["channel"] = channel
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(url, json=payload, headers=self.headers)
                logger.info(f"Wati v3 template response: {response.status_code}")
                
                if response.status_code == 200:
                    return {"success": True, "api_version": "v3", "result": response.json()}
                else:
                    return {"success": False, "api_version": "v3", "error": response.text, "status": response.status_code}
        except Exception as e:
            logger.error(f"Wati v3 template error: {str(e)}")
            return {"success": False, "api_version": "v3", "error": str(e)}
    
    async def send_template_message(
        self, 
        phone_number: str, 
        template_name: str,
        parameters: Optional[List[str]] = None,
        broadcast_name: Optional[str] = None
    ) -> dict:
        """
        Send a template message - tries v1 first, falls back to v3
        
        Args:
            phone_number: Recipient phone with country code
            template_name: Name of the approved template
            parameters: List of parameter values (will be converted to {name, value} format)
            broadcast_name: Name for this broadcast
        """
        phone = self._normalize_phone(phone_number)
        
        # Convert simple parameter list to format required by API
        param_list = []
        if parameters:
            for i, value in enumerate(parameters):
                param_list.append({"name": str(i + 1), "value": str(value)})
        
        # Try v1 API first
        result = await self.send_template_message_v1(
            phone, 
            template_name, 
            param_list,
            broadcast_name
        )
        
        if result.get("success"):
            return result
        
        # If v1 fails, try v3
        logger.info("v1 API failed, trying v3...")
        recipients = [{
            "whatsappNumber": phone,
            "customParams": param_list
        }]
        
        return await self.send_template_message_v3(
            template_name,
            broadcast_name or f"api_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            recipients
        )
    
    async def send_bulk_template(
        self,
        phone_numbers: List[str],
        template_name: str,
        parameters: Optional[List[str]] = None,
        broadcast_name: Optional[str] = None
    ) -> dict:
        """
        Send template to multiple recipients using v3 API
        
        Args:
            phone_numbers: List of phone numbers
            template_name: Name of the approved template
            parameters: Common parameters for all recipients
            broadcast_name: Name for this broadcast
        """
        # Build recipients list
        recipients = []
        for phone in phone_numbers:
            clean_phone = self._normalize_phone(phone)
            recipient = {"whatsappNumber": clean_phone}
            if parameters:
                recipient["customParams"] = [
                    {"name": str(i + 1), "value": str(v)} 
                    for i, v in enumerate(parameters)
                ]
            recipients.append(recipient)
        
        return await self.send_template_message_v3(
            template_name,
            broadcast_name or f"bulk_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            recipients
        )
    
    async def get_templates(self) -> dict:
        """
        Get all message templates
        Tries v1 first, then v3
        """
        # Try v1 API
        url = f"{self.v1_base}/getMessageTemplates"
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(url, headers=self.headers)
                if response.status_code == 200:
                    return {"success": True, "api_version": "v1", "templates": response.json()}
        except Exception as e:
            logger.error(f"Wati v1 get templates error: {str(e)}")
        
        # Try v3 API
        url = f"{self.endpoint}/api/ext/v3/messageTemplates"
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(url, headers=self.headers)
                if response.status_code == 200:
                    return {"success": True, "api_version": "v3", "templates": response.json()}
                else:
                    return {"success": False, "error": response.text}
        except Exception as e:
            logger.error(f"Wati v3 get templates error: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def get_contacts(self, page_size: int = 100, page_number: int = 1) -> dict:
        """Get contacts from Wati"""
        url = f"{self.v1_base}/getContacts?pageSize={page_size}&pageNumber={page_number}"
        
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(url, headers=self.headers)
                if response.status_code == 200:
                    return {"success": True, "contacts": response.json()}
                else:
                    return {"success": False, "error": response.text}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _normalize_phone(self, phone: str) -> str:
        """Normalize phone number to include country code"""
        # Remove all non-digits
        phone = ''.join(filter(str.isdigit, phone))
        # Add India country code if not present
        if not phone.startswith('91') and len(phone) == 10:
            phone = '91' + phone
        return phone


# Get Wati service instance
async def get_wati_service() -> Optional[WatiService]:
    """Get configured Wati service instance"""
    config = await db.system_config.find_one({"config_type": "whatsapp"})
    if not config:
        return None
    
    api_endpoint = config.get("api_endpoint")
    api_token = config.get("api_token")
    api_version = config.get("api_version", "v1")
    
    if not api_endpoint or not api_token:
        return None
    
    return WatiService(api_endpoint, api_token, api_version)
            # Check if we got templates or result is True
            return result.get("result", False) or len(result.get("messageTemplates", [])) > 0
        except Exception as e:
            logger.error(f"Wati connection test failed: {str(e)}")
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

@router.post("/test-connection")
async def test_wati_connection(
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("notifications.whatsapp_connect", "test WhatsApp connection"))
):
    """Test the current Wati.io connection"""
    service = await get_wati_service()
    
    if not service:
        return {
            "connected": False,
            "message": "Wati.io is not configured. Please configure the API endpoint and token first."
        }
    
    result = await service.test_connection()
    
    # Update status in config
    if result.get("connected"):
        await db.system_config.update_one(
            {"config_type": "whatsapp"},
            {"$set": {"status": "connected", "last_test": datetime.now(timezone.utc).isoformat()}}
        )
    else:
        await db.system_config.update_one(
            {"config_type": "whatsapp"},
            {"$set": {"status": "disconnected", "last_error": result.get("message")}}
        )
    
    return result


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
    connection_result = await service.test_connection()
    
    if not connection_result.get("connected"):
        raise HTTPException(
            status_code=400, 
            detail=f"Failed to connect to Wati.io: {connection_result.get('message', 'Unknown error')}"
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



# ============== AUTOMATION ==============

from services.whatsapp_automation import (
    get_automation_config,
    update_automation_config,
    send_payment_reminders,
    send_document_reminders,
    send_bulk_broadcast,
    notify_dp_ready_bookings,
    run_scheduled_automations
)


class AutomationConfigUpdate(BaseModel):
    payment_reminder_enabled: bool = False
    payment_reminder_days: int = 3
    document_reminder_enabled: bool = False
    dp_ready_notification_enabled: bool = True


class BulkBroadcastRequest(BaseModel):
    message: str
    recipient_type: str  # all_clients, all_rps, all_bps, custom
    recipient_ids: Optional[List[str]] = None
    broadcast_name: Optional[str] = None


@router.get("/automation/config")
async def get_automation_settings(
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("notifications.whatsapp_config", "view WhatsApp automation config"))
):
    """Get WhatsApp automation configuration"""
    config = await get_automation_config()
    return config


@router.put("/automation/config")
async def update_automation_settings(
    config: AutomationConfigUpdate,
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("notifications.whatsapp_config", "update WhatsApp automation config"))
):
    """Update WhatsApp automation configuration"""
    updated = await update_automation_config(
        config.dict(),
        current_user.get("id"),
        current_user.get("name")
    )
    return updated


@router.post("/automation/payment-reminders")
async def trigger_payment_reminders(
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("notifications.whatsapp_send", "send WhatsApp notifications"))
):
    """Manually trigger payment reminder automation"""
    result = await send_payment_reminders()
    return result


@router.post("/automation/document-reminders")
async def trigger_document_reminders(
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("notifications.whatsapp_send", "send WhatsApp notifications"))
):
    """Manually trigger document upload reminder automation"""
    result = await send_document_reminders()
    return result


@router.post("/automation/dp-ready-notifications")
async def trigger_dp_ready_notifications(
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("notifications.whatsapp_send", "send WhatsApp notifications"))
):
    """Manually trigger DP ready notifications"""
    result = await notify_dp_ready_bookings()
    return result


@router.post("/automation/bulk-broadcast")
async def send_broadcast(
    request: BulkBroadcastRequest,
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("notifications.whatsapp_send", "send WhatsApp notifications"))
):
    """Send bulk broadcast message"""
    result = await send_bulk_broadcast(
        message=request.message,
        recipient_type=request.recipient_type,
        recipient_ids=request.recipient_ids,
        broadcast_name=request.broadcast_name,
        user_id=current_user.get("id"),
        user_name=current_user.get("name")
    )
    return result


@router.post("/automation/run-all")
async def run_all_automations(
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("notifications.whatsapp_config", "run WhatsApp automations"))
):
    """Run all enabled automations manually"""
    result = await run_scheduled_automations()
    return result


@router.get("/automation/logs")
async def get_automation_logs(
    limit: int = Query(50, ge=1, le=200),
    skip: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("notifications.whatsapp_history", "view WhatsApp automation logs"))
):
    """Get automation run logs"""
    logs = await db.whatsapp_automation_logs.find(
        {}, {"_id": 0}
    ).sort("run_at", -1).skip(skip).limit(limit).to_list(limit)
    
    total = await db.whatsapp_automation_logs.count_documents({})
    
    return {
        "logs": logs,
        "total": total,
        "limit": limit,
        "skip": skip
    }


@router.get("/broadcasts")
async def get_broadcasts(
    limit: int = Query(50, ge=1, le=200),
    skip: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("notifications.whatsapp_history", "view WhatsApp broadcasts"))
):
    """Get broadcast history"""
    broadcasts = await db.whatsapp_broadcasts.find(
        {}, {"_id": 0}
    ).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    
    total = await db.whatsapp_broadcasts.count_documents({})
    
    return {
        "broadcasts": broadcasts,
        "total": total,
        "limit": limit,
        "skip": skip
    }


# ============== WATI WEBHOOK ENDPOINTS ==============

class WebhookPayload(BaseModel):
    """Wati.io Webhook payload model"""
    eventType: Optional[str] = None
    waId: Optional[str] = None  # WhatsApp ID (phone number)
    id: Optional[str] = None  # Message ID
    timestamp: Optional[str] = None
    text: Optional[str] = None
    status: Optional[str] = None  # sent, delivered, read, failed
    type: Optional[str] = None
    localMessageId: Optional[str] = None
    conversationId: Optional[str] = None
    # Allow any additional fields
    class Config:
        extra = "allow"


@router.post("/webhook")
async def wati_webhook(payload: dict):
    """
    Wati.io Webhook endpoint for receiving delivery status updates.
    Configure this URL in your Wati.io dashboard under Settings > Webhooks.
    
    Webhook URL: {your_domain}/api/whatsapp/webhook
    """
    try:
        event_type = payload.get("eventType", payload.get("type", "unknown"))
        wa_id = payload.get("waId", payload.get("from", ""))
        message_id = payload.get("id", payload.get("messageId", ""))
        status = payload.get("status", "")
        timestamp = payload.get("timestamp", datetime.now(timezone.utc).isoformat())
        
        # Store webhook event
        webhook_event = {
            "id": str(uuid.uuid4()),
            "event_type": event_type,
            "wa_id": wa_id,
            "message_id": message_id,
            "status": status,
            "payload": payload,
            "received_at": datetime.now(timezone.utc).isoformat(),
            "processed": False
        }
        
        await db.whatsapp_webhook_events.insert_one(webhook_event.copy())
        
        # Process based on event type
        if event_type in ["message_status", "status_update"] or status:
            # Update message log with delivery status
            await process_delivery_status(message_id, status, wa_id, timestamp)
        
        elif event_type in ["message_received", "incoming"]:
            # Store incoming message
            await process_incoming_message(payload)
        
        # Create notification for PE Desk about important events
        if status == "failed" or event_type == "message_failed":
            from services.notification_service import notify_roles
            await notify_roles(
                roles=[1, 2],  # PE Desk and PE Manager
                notif_type="whatsapp_failed",
                title="WhatsApp Message Failed",
                message=f"Message to {wa_id} failed to deliver",
                data={"wa_id": wa_id, "message_id": message_id, "payload": payload}
            )
        
        # Mark as processed
        await db.whatsapp_webhook_events.update_one(
            {"id": webhook_event["id"]},
            {"$set": {"processed": True, "processed_at": datetime.now(timezone.utc).isoformat()}}
        )
        
        return {"status": "ok", "event_id": webhook_event["id"]}
    
    except Exception as e:
        logger.error(f"Webhook processing error: {str(e)}")
        # Store the error but return 200 to prevent retries
        await db.whatsapp_webhook_events.insert_one({
            "id": str(uuid.uuid4()),
            "event_type": "error",
            "error": str(e),
            "payload": payload,
            "received_at": datetime.now(timezone.utc).isoformat(),
            "processed": False
        })
        return {"status": "error", "message": str(e)}


async def process_delivery_status(message_id: str, status: str, wa_id: str, timestamp: str):
    """Process delivery status update from webhook"""
    if not message_id:
        return
    
    # Update the message log entry
    update_data = {
        f"delivery_status.{status}": True,
        f"delivery_status.{status}_at": timestamp,
        "delivery_status.current": status,
        "delivery_status.updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.whatsapp_message_logs.update_one(
        {"$or": [{"message_id": message_id}, {"local_message_id": message_id}]},
        {"$set": update_data}
    )
    
    # Also update by phone number if message_id not found
    await db.whatsapp_message_logs.update_one(
        {"phone_number": {"$regex": wa_id.replace("+", "").replace("91", "")}},
        {"$set": update_data},
        upsert=False
    )


async def process_incoming_message(payload: dict):
    """Process incoming WhatsApp message"""
    incoming_message = {
        "id": str(uuid.uuid4()),
        "wa_id": payload.get("waId", payload.get("from", "")),
        "message_id": payload.get("id", ""),
        "text": payload.get("text", payload.get("body", "")),
        "type": payload.get("type", "text"),
        "timestamp": payload.get("timestamp", datetime.now(timezone.utc).isoformat()),
        "received_at": datetime.now(timezone.utc).isoformat(),
        "read": False
    }
    
    await db.whatsapp_incoming_messages.insert_one(incoming_message.copy())
    
    # Notify PE Desk
    from services.notification_service import notify_roles
    await notify_roles(
        roles=[1, 2],
        notif_type="whatsapp_incoming",
        title="New WhatsApp Message",
        message=f"New message from {incoming_message['wa_id']}: {incoming_message['text'][:50]}...",
        data=incoming_message
    )


@router.get("/webhook/events")
async def get_webhook_events(
    limit: int = Query(100, ge=1, le=500),
    skip: int = Query(0, ge=0),
    event_type: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("notifications.whatsapp_history", "view webhook events"))
):
    """Get webhook event history for debugging"""
    query = {}
    if event_type:
        query["event_type"] = event_type
    
    events = await db.whatsapp_webhook_events.find(
        query, {"_id": 0}
    ).sort("received_at", -1).skip(skip).limit(limit).to_list(limit)
    
    total = await db.whatsapp_webhook_events.count_documents(query)
    
    return {
        "events": events,
        "total": total,
        "limit": limit,
        "skip": skip
    }


@router.get("/incoming-messages")
async def get_incoming_messages(
    limit: int = Query(50, ge=1, le=200),
    skip: int = Query(0, ge=0),
    unread_only: bool = Query(False),
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("notifications.whatsapp_history", "view incoming messages"))
):
    """Get incoming WhatsApp messages"""
    query = {}
    if unread_only:
        query["read"] = False
    
    messages = await db.whatsapp_incoming_messages.find(
        query, {"_id": 0}
    ).sort("received_at", -1).skip(skip).limit(limit).to_list(limit)
    
    total = await db.whatsapp_incoming_messages.count_documents(query)
    unread_count = await db.whatsapp_incoming_messages.count_documents({"read": False})
    
    return {
        "messages": messages,
        "total": total,
        "unread_count": unread_count,
        "limit": limit,
        "skip": skip
    }


@router.put("/incoming-messages/{message_id}/read")
async def mark_incoming_read(
    message_id: str,
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("notifications.whatsapp_history", "mark messages as read"))
):
    """Mark incoming message as read"""
    result = await db.whatsapp_incoming_messages.update_one(
        {"id": message_id},
        {"$set": {"read": True, "read_at": datetime.now(timezone.utc).isoformat(), "read_by": current_user["id"]}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Message not found")
    
    return {"message": "Marked as read"}


@router.get("/delivery-stats")
async def get_delivery_stats(
    days: int = Query(7, ge=1, le=30),
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("notifications.whatsapp_history", "view delivery stats"))
):
    """Get WhatsApp message delivery statistics"""
    from datetime import timedelta
    
    start_date = datetime.now(timezone.utc) - timedelta(days=days)
    
    # Aggregate delivery stats from message logs
    pipeline = [
        {"$match": {"sent_at": {"$gte": start_date.isoformat()}}},
        {"$group": {
            "_id": None,
            "total_sent": {"$sum": 1},
            "delivered": {"$sum": {"$cond": [{"$eq": ["$delivery_status.delivered", True]}, 1, 0]}},
            "read": {"$sum": {"$cond": [{"$eq": ["$delivery_status.read", True]}, 1, 0]}},
            "failed": {"$sum": {"$cond": [{"$eq": ["$delivery_status.failed", True]}, 1, 0]}}
        }}
    ]
    
    stats = await db.whatsapp_message_logs.aggregate(pipeline).to_list(1)
    
    if stats:
        stat = stats[0]
        total = stat.get("total_sent", 0)
        return {
            "period_days": days,
            "total_sent": total,
            "delivered": stat.get("delivered", 0),
            "read": stat.get("read", 0),
            "failed": stat.get("failed", 0),
            "delivery_rate": round((stat.get("delivered", 0) / total * 100) if total > 0 else 0, 2),
            "read_rate": round((stat.get("read", 0) / total * 100) if total > 0 else 0, 2)
        }
    
    return {
        "period_days": days,
        "total_sent": 0,
        "delivered": 0,
        "read": 0,
        "failed": 0,
        "delivery_rate": 0,
        "read_rate": 0
    }
