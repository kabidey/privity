"""
WhatsApp Bulk Notification Automation Service
Handles scheduled and triggered bulk WhatsApp notifications
"""
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict
import uuid
import logging
import asyncio

from database import db
from services.wati_service import WatiService

logger = logging.getLogger(__name__)


# Automation trigger types
AUTOMATION_TRIGGERS = {
    "booking_status_change": "When booking status changes (created, approved, DP ready, completed)",
    "payment_reminder": "Payment reminders for pending payments",
    "document_upload_reminder": "Reminder to upload pending documents",
    "scheduled_broadcast": "Scheduled bulk broadcast messages",
    "dp_ready_notification": "When order is ready for DP transfer"
}


async def get_wati_service() -> Optional[WatiService]:
    """Get configured Wati service if available"""
    config = await db.system_config.find_one({"config_type": "whatsapp"}, {"_id": 0})
    if not config or not config.get("enabled") or config.get("status") != "connected":
        return None
    
    return WatiService(
        endpoint=config.get("api_endpoint", ""),
        token=config.get("api_token", "")
    )


async def log_automation_run(
    automation_type: str,
    trigger_event: str,
    recipients_count: int,
    success_count: int,
    failed_count: int,
    details: dict = None
):
    """Log automation run for audit"""
    log_entry = {
        "id": str(uuid.uuid4()),
        "automation_type": automation_type,
        "trigger_event": trigger_event,
        "recipients_count": recipients_count,
        "success_count": success_count,
        "failed_count": failed_count,
        "details": details or {},
        "run_at": datetime.now(timezone.utc).isoformat()
    }
    await db.whatsapp_automation_logs.insert_one(log_entry)
    return log_entry


# ============== PAYMENT REMINDER AUTOMATION ==============

async def get_pending_payment_bookings(days_overdue: int = 3) -> List[dict]:
    """Get bookings with pending payments older than X days"""
    cutoff_date = (datetime.now(timezone.utc) - timedelta(days=days_overdue)).isoformat()
    
    bookings = await db.bookings.find({
        "approval_status": "approved",
        "payment_status": {"$in": ["pending", "partial"]},
        "is_voided": {"$ne": True},
        "approved_at": {"$lt": cutoff_date}
    }, {"_id": 0}).to_list(1000)
    
    return bookings


async def send_payment_reminders():
    """Send payment reminders to clients with pending payments"""
    wati = await get_wati_service()
    if not wati:
        logger.info("WhatsApp not configured, skipping payment reminders")
        return {"status": "skipped", "reason": "WhatsApp not configured"}
    
    bookings = await get_pending_payment_bookings()
    
    success_count = 0
    failed_count = 0
    
    for booking in bookings:
        client = await db.clients.find_one({"id": booking["client_id"]}, {"_id": 0})
        if not client or not client.get("phone"):
            continue
        
        stock = await db.stocks.find_one({"id": booking["stock_id"]}, {"_id": 0})
        
        # Calculate pending amount
        payments = booking.get("payments", [])
        total_paid = sum(p.get("amount", 0) for p in payments)
        total_amount = booking.get("quantity", 0) * booking.get("selling_price", 0)
        pending_amount = total_amount - total_paid
        
        message = f"""Dear {client.get('name', 'Customer')},

Payment Reminder for your booking:

Booking: #{booking.get('booking_number', 'N/A')}
Stock: {stock.get('symbol', 'N/A') if stock else 'N/A'}
Pending Amount: ₹{pending_amount:,.2f}

Please complete the payment to proceed with share transfer.

- SMIFS Private Equity"""
        
        try:
            await wati.send_session_message(client["phone"], message)
            success_count += 1
            
            # Log the message
            await db.whatsapp_messages.insert_one({
                "id": str(uuid.uuid4()),
                "phone_number": client["phone"],
                "message": message,
                "template_id": "payment_reminder",
                "recipient_type": "client",
                "recipient_id": client["id"],
                "booking_id": booking["id"],
                "status": "sent",
                "sent_at": datetime.now(timezone.utc).isoformat(),
                "sent_by": "automation",
                "sent_by_name": "Payment Reminder Automation"
            })
        except Exception as e:
            logger.error(f"Failed to send payment reminder: {e}")
            failed_count += 1
    
    await log_automation_run(
        "payment_reminder",
        "scheduled",
        len(bookings),
        success_count,
        failed_count
    )
    
    return {
        "status": "completed",
        "total": len(bookings),
        "success": success_count,
        "failed": failed_count
    }


# ============== DOCUMENT UPLOAD REMINDER AUTOMATION ==============

async def get_clients_missing_documents() -> List[dict]:
    """Get approved clients missing mandatory documents"""
    required_docs = ["pan_card", "cml_copy", "cancelled_cheque"]
    
    clients = await db.clients.find({
        "approval_status": "pending",
        "is_vendor": False,
        "is_active": True
    }, {"_id": 0}).to_list(1000)
    
    clients_missing_docs = []
    for client in clients:
        documents = client.get("documents", [])
        doc_types = [d.get("doc_type") for d in documents]
        missing = [doc for doc in required_docs if doc not in doc_types]
        
        if missing:
            client["missing_documents"] = missing
            clients_missing_docs.append(client)
    
    return clients_missing_docs


async def send_document_reminders():
    """Send document upload reminders to clients"""
    wati = await get_wati_service()
    if not wati:
        logger.info("WhatsApp not configured, skipping document reminders")
        return {"status": "skipped", "reason": "WhatsApp not configured"}
    
    clients = await get_clients_missing_documents()
    
    success_count = 0
    failed_count = 0
    
    doc_names = {
        "pan_card": "PAN Card",
        "cml_copy": "CML Copy",
        "cancelled_cheque": "Cancelled Cheque"
    }
    
    for client in clients:
        if not client.get("phone"):
            continue
        
        missing_docs = client.get("missing_documents", [])
        missing_names = [doc_names.get(d, d) for d in missing_docs]
        
        message = f"""Dear {client.get('name', 'Customer')},

Document Upload Reminder:

Your account is pending approval. Please upload the following documents:

{chr(10).join(f'• {name}' for name in missing_names)}

Upload these documents to complete your account setup.

- SMIFS Private Equity"""
        
        try:
            await wati.send_session_message(client["phone"], message)
            success_count += 1
            
            await db.whatsapp_messages.insert_one({
                "id": str(uuid.uuid4()),
                "phone_number": client["phone"],
                "message": message,
                "template_id": "document_reminder",
                "recipient_type": "client",
                "recipient_id": client["id"],
                "status": "sent",
                "sent_at": datetime.now(timezone.utc).isoformat(),
                "sent_by": "automation",
                "sent_by_name": "Document Reminder Automation"
            })
        except Exception as e:
            logger.error(f"Failed to send document reminder: {e}")
            failed_count += 1
    
    await log_automation_run(
        "document_reminder",
        "scheduled",
        len(clients),
        success_count,
        failed_count
    )
    
    return {
        "status": "completed",
        "total": len(clients),
        "success": success_count,
        "failed": failed_count
    }


# ============== BULK BROADCAST ==============

async def send_bulk_broadcast(
    message: str,
    recipient_type: str,  # all_clients, all_rps, all_bps, custom
    recipient_ids: List[str] = None,
    broadcast_name: str = None,
    user_id: str = None,
    user_name: str = None
) -> dict:
    """Send bulk broadcast message"""
    wati = await get_wati_service()
    if not wati:
        return {"status": "failed", "reason": "WhatsApp not configured"}
    
    recipients = []
    
    if recipient_type == "all_clients":
        recipients = await db.clients.find(
            {"is_vendor": False, "is_active": True, "phone": {"$exists": True, "$ne": None}},
            {"_id": 0, "id": 1, "name": 1, "phone": 1}
        ).to_list(10000)
    elif recipient_type == "all_rps":
        recipients = await db.referral_partners.find(
            {"is_active": True, "phone": {"$exists": True, "$ne": None}},
            {"_id": 0, "id": 1, "name": 1, "phone": 1}
        ).to_list(10000)
    elif recipient_type == "all_bps":
        recipients = await db.business_partners.find(
            {"is_active": True, "phone": {"$exists": True, "$ne": None}},
            {"_id": 0, "id": 1, "name": 1, "phone": 1}
        ).to_list(10000)
    elif recipient_type == "all_users":
        # Internal users (employees) with mobile numbers
        users = await db.users.find(
            {"is_active": True, "mobile_number": {"$exists": True, "$ne": None}},
            {"_id": 0, "id": 1, "name": 1, "mobile_number": 1}
        ).to_list(10000)
        # Map mobile_number to phone for consistency
        recipients = [{"id": u["id"], "name": u["name"], "phone": u["mobile_number"]} for u in users]
    elif recipient_type == "custom" and recipient_ids:
        # Get from all collections including users
        clients = await db.clients.find(
            {"id": {"$in": recipient_ids}},
            {"_id": 0, "id": 1, "name": 1, "phone": 1}
        ).to_list(10000)
        rps = await db.referral_partners.find(
            {"id": {"$in": recipient_ids}},
            {"_id": 0, "id": 1, "name": 1, "phone": 1}
        ).to_list(10000)
        bps = await db.business_partners.find(
            {"id": {"$in": recipient_ids}},
            {"_id": 0, "id": 1, "name": 1, "phone": 1}
        ).to_list(10000)
        # Also check users collection for mobile_number
        users = await db.users.find(
            {"id": {"$in": recipient_ids}, "mobile_number": {"$exists": True, "$ne": None}},
            {"_id": 0, "id": 1, "name": 1, "mobile_number": 1}
        ).to_list(10000)
        user_recipients = [{"id": u["id"], "name": u["name"], "phone": u["mobile_number"]} for u in users]
        recipients = clients + rps + bps + user_recipients
    
    if not recipients:
        return {"status": "failed", "reason": "No recipients found"}
    
    # Create broadcast record
    broadcast_id = str(uuid.uuid4())
    broadcast_record = {
        "id": broadcast_id,
        "name": broadcast_name or f"Broadcast_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "message": message,
        "recipient_type": recipient_type,
        "recipient_count": len(recipients),
        "status": "in_progress",
        "created_by": user_id,
        "created_by_name": user_name,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.whatsapp_broadcasts.insert_one(broadcast_record)
    
    success_count = 0
    failed_count = 0
    
    for recipient in recipients:
        if not recipient.get("phone"):
            failed_count += 1
            continue
        
        try:
            await wati.send_session_message(recipient["phone"], message)
            success_count += 1
            
            await db.whatsapp_messages.insert_one({
                "id": str(uuid.uuid4()),
                "phone_number": recipient["phone"],
                "message": message,
                "template_id": "broadcast",
                "broadcast_id": broadcast_id,
                "recipient_type": recipient_type,
                "recipient_id": recipient["id"],
                "status": "sent",
                "sent_at": datetime.now(timezone.utc).isoformat(),
                "sent_by": user_id or "automation",
                "sent_by_name": user_name or "Broadcast"
            })
            
            # Small delay to avoid rate limiting
            await asyncio.sleep(0.1)
        except Exception as e:
            logger.error(f"Failed to send broadcast to {recipient['phone']}: {e}")
            failed_count += 1
    
    # Update broadcast status
    await db.whatsapp_broadcasts.update_one(
        {"id": broadcast_id},
        {"$set": {
            "status": "completed",
            "success_count": success_count,
            "failed_count": failed_count,
            "completed_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    await log_automation_run(
        "bulk_broadcast",
        broadcast_name or "manual",
        len(recipients),
        success_count,
        failed_count,
        {"broadcast_id": broadcast_id}
    )
    
    return {
        "status": "completed",
        "broadcast_id": broadcast_id,
        "total": len(recipients),
        "success": success_count,
        "failed": failed_count
    }


# ============== DP READY NOTIFICATION ==============

async def notify_dp_ready_bookings():
    """Notify clients when their bookings are ready for DP transfer"""
    wati = await get_wati_service()
    if not wati:
        return {"status": "skipped", "reason": "WhatsApp not configured"}
    
    # Get bookings that just became DP ready (in last 24 hours) and haven't been notified
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    
    bookings = await db.bookings.find({
        "dp_status": "ready",
        "dp_whatsapp_notified": {"$ne": True},
        "dp_ready_at": {"$gte": cutoff}
    }, {"_id": 0}).to_list(1000)
    
    success_count = 0
    failed_count = 0
    
    for booking in bookings:
        client = await db.clients.find_one({"id": booking["client_id"]}, {"_id": 0})
        if not client or not client.get("phone"):
            continue
        
        stock = await db.stocks.find_one({"id": booking["stock_id"]}, {"_id": 0})
        
        message = f"""Dear {client.get('name', 'Customer')},

Great news! Your shares are ready for transfer.

Booking: #{booking.get('booking_number', 'N/A')}
Stock: {stock.get('symbol', 'N/A') if stock else 'N/A'}
Quantity: {booking.get('quantity', 0)} shares
DP ID: {client.get('dp_id', 'N/A')}

The shares will be transferred to your DP account shortly.

- SMIFS Private Equity"""
        
        try:
            await wati.send_session_message(client["phone"], message)
            success_count += 1
            
            # Mark as notified
            await db.bookings.update_one(
                {"id": booking["id"]},
                {"$set": {"dp_whatsapp_notified": True, "dp_whatsapp_notified_at": datetime.now(timezone.utc).isoformat()}}
            )
            
            await db.whatsapp_messages.insert_one({
                "id": str(uuid.uuid4()),
                "phone_number": client["phone"],
                "message": message,
                "template_id": "dp_ready",
                "recipient_type": "client",
                "recipient_id": client["id"],
                "booking_id": booking["id"],
                "status": "sent",
                "sent_at": datetime.now(timezone.utc).isoformat(),
                "sent_by": "automation",
                "sent_by_name": "DP Ready Automation"
            })
        except Exception as e:
            logger.error(f"Failed to send DP ready notification: {e}")
            failed_count += 1
    
    await log_automation_run(
        "dp_ready_notification",
        "scheduled",
        len(bookings),
        success_count,
        failed_count
    )
    
    return {
        "status": "completed",
        "total": len(bookings),
        "success": success_count,
        "failed": failed_count
    }


# ============== AUTOMATION CONFIGURATION ==============

async def get_automation_config() -> dict:
    """Get WhatsApp automation configuration"""
    config = await db.system_config.find_one({"config_type": "whatsapp_automation"}, {"_id": 0})
    return config or {
        "payment_reminder_enabled": False,
        "payment_reminder_days": 3,
        "document_reminder_enabled": False,
        "dp_ready_notification_enabled": True
    }


async def update_automation_config(config: dict, user_id: str, user_name: str) -> dict:
    """Update WhatsApp automation configuration"""
    config["config_type"] = "whatsapp_automation"
    config["updated_at"] = datetime.now(timezone.utc).isoformat()
    config["updated_by"] = user_id
    config["updated_by_name"] = user_name
    
    await db.system_config.update_one(
        {"config_type": "whatsapp_automation"},
        {"$set": config},
        upsert=True
    )
    
    return config


# ============== RUN ALL SCHEDULED AUTOMATIONS ==============

async def run_scheduled_automations():
    """Run all enabled scheduled automations"""
    config = await get_automation_config()
    results = {}
    
    if config.get("payment_reminder_enabled"):
        results["payment_reminders"] = await send_payment_reminders()
    
    if config.get("document_reminder_enabled"):
        results["document_reminders"] = await send_document_reminders()
    
    if config.get("dp_ready_notification_enabled", True):
        results["dp_ready_notifications"] = await notify_dp_ready_bookings()
    
    logger.info(f"WhatsApp automation run completed: {results}")
    return results
