"""
Activity Alert Service
Sends alerts to clients, RPs, and BPs for their activities via WhatsApp
"""
from datetime import datetime, timezone
from typing import Optional
import uuid

from database import db


async def get_whatsapp_config():
    """Get WhatsApp configuration"""
    config = await db.system_config.find_one({"config_type": "whatsapp"}, {"_id": 0})
    return config


async def log_whatsapp_message(phone_number: str, message: str, template_id: str, recipient_type: str, 
                               recipient_id: str, sent_by: str = "system"):
    """Log a WhatsApp message to the database"""
    message_log = {
        "id": str(uuid.uuid4()),
        "phone_number": phone_number,
        "message": message,
        "template_id": template_id,
        "recipient_type": recipient_type,  # client, rp, bp, user
        "recipient_id": recipient_id,
        "status": "sent",  # In production would track actual delivery
        "sent_at": datetime.now(timezone.utc).isoformat(),
        "sent_by": sent_by,
        "sent_by_name": "System Alert"
    }
    await db.whatsapp_messages.insert_one(message_log)
    return message_log


async def send_activity_alert(
    recipient_type: str,  # client, rp, bp
    recipient_id: str,
    activity_type: str,  # booking_created, booking_approved, booking_rejected, payment_received, dp_transfer, client_approved
    activity_details: dict
):
    """
    Send activity alert to client/RP/BP via WhatsApp
    """
    # Check if WhatsApp is enabled
    config = await get_whatsapp_config()
    if not config or config.get("status") != "connected" or not config.get("enabled"):
        return {"status": "skipped", "reason": "WhatsApp not connected or disabled"}
    
    # Get recipient details
    recipient = None
    phone_number = None
    recipient_name = None
    
    if recipient_type == "client":
        recipient = await db.clients.find_one({"id": recipient_id}, {"_id": 0, "name": 1, "phone": 1})
        if recipient:
            phone_number = recipient.get("phone")
            recipient_name = recipient.get("name")
    elif recipient_type == "rp":
        recipient = await db.referral_partners.find_one({"id": recipient_id}, {"_id": 0, "name": 1, "phone": 1})
        if recipient:
            phone_number = recipient.get("phone")
            recipient_name = recipient.get("name")
    elif recipient_type == "bp":
        recipient = await db.business_partners.find_one({"id": recipient_id}, {"_id": 0, "name": 1, "phone": 1})
        if recipient:
            phone_number = recipient.get("phone")
            recipient_name = recipient.get("name")
    
    if not phone_number:
        return {"status": "skipped", "reason": f"No phone number for {recipient_type}"}
    
    # Build message based on activity type
    message = build_activity_message(activity_type, recipient_name, activity_details)
    
    if not message:
        return {"status": "skipped", "reason": "Unknown activity type"}
    
    # Log the message
    await log_whatsapp_message(
        phone_number=phone_number,
        message=message,
        template_id=f"activity_{activity_type}",
        recipient_type=recipient_type,
        recipient_id=recipient_id
    )
    
    return {"status": "sent", "phone_number": phone_number[-4:].rjust(len(phone_number), '*')}


def build_activity_message(activity_type: str, recipient_name: str, details: dict) -> Optional[str]:
    """Build message based on activity type"""
    templates = {
        "booking_created": f"""Dear {recipient_name},

A new booking has been created:

Booking: #{details.get('booking_number', 'N/A')}
Stock: {details.get('stock_symbol', 'N/A')}
Quantity: {details.get('quantity', 0)} shares
Amount: ₹{details.get('amount', 0):,.2f}

Thank you for your business.
- SMIFS Private Equity""",

        "booking_approved": f"""Dear {recipient_name},

Your booking has been approved!

Booking: #{details.get('booking_number', 'N/A')}
Stock: {details.get('stock_symbol', 'N/A')}
Status: Approved ✅

Please complete the payment to proceed.
- SMIFS Private Equity""",

        "booking_rejected": f"""Dear {recipient_name},

Your booking has been rejected.

Booking: #{details.get('booking_number', 'N/A')}
Stock: {details.get('stock_symbol', 'N/A')}
Reason: {details.get('rejection_reason', 'Not specified')}

Please contact support for more information.
- SMIFS Private Equity""",

        "payment_received": f"""Dear {recipient_name},

Payment received successfully!

Booking: #{details.get('booking_number', 'N/A')}
Amount: ₹{details.get('amount', 0):,.2f}
Payment Mode: {details.get('payment_mode', 'N/A')}

Thank you for your payment.
- SMIFS Private Equity""",

        "dp_transfer": f"""Dear {recipient_name},

Shares transferred to your DP account!

Booking: #{details.get('booking_number', 'N/A')}
Stock: {details.get('stock_symbol', 'N/A')}
Quantity: {details.get('quantity', 0)} shares
DP ID: {details.get('dp_id', 'N/A')}

Transfer complete. Thank you for your business.
- SMIFS Private Equity""",

        "client_approved": f"""Dear {recipient_name},

Your account has been approved!

Status: Approved ✅
You can now proceed with bookings.

Welcome to SMIFS Private Equity!""",

        "client_rejected": f"""Dear {recipient_name},

Your account application requires attention.

Status: Requires Review
Reason: {details.get('rejection_reason', 'Additional verification needed')}

Please contact support for assistance.
- SMIFS Private Equity""",

        # RP-specific alerts
        "rp_commission_earned": f"""Dear {recipient_name},

You've earned a commission!

Booking: #{details.get('booking_number', 'N/A')}
Client: {details.get('client_name', 'N/A')}
Commission: ₹{details.get('commission_amount', 0):,.2f} ({details.get('commission_percent', 0)}%)

Thank you for your referral!
- SMIFS Private Equity""",

        # BP-specific alerts
        "bp_revenue_earned": f"""Dear {recipient_name},

Revenue share credited!

Booking: #{details.get('booking_number', 'N/A')}
Client: {details.get('client_name', 'N/A')}
Revenue: ₹{details.get('revenue_amount', 0):,.2f} ({details.get('revenue_percent', 0)}%)

Thank you for your partnership!
- SMIFS Private Equity"""
    }
    
    return templates.get(activity_type)


# Integration functions to be called from booking/payment routers

async def notify_booking_created(booking: dict, client: dict, rp: dict = None, bp: dict = None):
    """Notify client, RP, BP when a booking is created"""
    details = {
        "booking_number": booking.get("booking_number"),
        "stock_symbol": booking.get("stock_symbol"),
        "quantity": booking.get("quantity"),
        "amount": booking.get("quantity", 0) * booking.get("buying_price", 0)
    }
    
    # Notify client
    if client and client.get("id"):
        await send_activity_alert("client", client["id"], "booking_created", details)
    
    # Notify RP if exists
    if rp and rp.get("id"):
        commission_details = {
            **details,
            "client_name": client.get("name") if client else "N/A",
            "commission_amount": booking.get("rp_revenue", 0),
            "commission_percent": booking.get("rp_revenue_share_percent", 0)
        }
        await send_activity_alert("rp", rp["id"], "rp_commission_earned", commission_details)
    
    # Notify BP if exists
    if bp and bp.get("id"):
        revenue_details = {
            **details,
            "client_name": client.get("name") if client else "N/A",
            "revenue_amount": booking.get("bp_revenue", 0),
            "revenue_percent": booking.get("bp_revenue_share_percent", 0)
        }
        await send_activity_alert("bp", bp["id"], "bp_revenue_earned", revenue_details)


async def notify_booking_approved(booking: dict, client_id: str):
    """Notify client when booking is approved"""
    details = {
        "booking_number": booking.get("booking_number"),
        "stock_symbol": booking.get("stock_symbol")
    }
    await send_activity_alert("client", client_id, "booking_approved", details)


async def notify_booking_rejected(booking: dict, client_id: str, rejection_reason: str):
    """Notify client when booking is rejected"""
    details = {
        "booking_number": booking.get("booking_number"),
        "stock_symbol": booking.get("stock_symbol"),
        "rejection_reason": rejection_reason
    }
    await send_activity_alert("client", client_id, "booking_rejected", details)


async def notify_payment_received(booking: dict, client_id: str, amount: float, payment_mode: str):
    """Notify client when payment is received"""
    details = {
        "booking_number": booking.get("booking_number"),
        "amount": amount,
        "payment_mode": payment_mode
    }
    await send_activity_alert("client", client_id, "payment_received", details)


async def notify_dp_transfer(booking: dict, client_id: str, dp_id: str):
    """Notify client when DP transfer is complete"""
    details = {
        "booking_number": booking.get("booking_number"),
        "stock_symbol": booking.get("stock_symbol"),
        "quantity": booking.get("quantity"),
        "dp_id": dp_id
    }
    await send_activity_alert("client", client_id, "dp_transfer", details)


async def notify_client_approved(client_id: str, client_name: str):
    """Notify client when their account is approved"""
    await send_activity_alert("client", client_id, "client_approved", {"name": client_name})


async def notify_client_rejected(client_id: str, client_name: str, reason: str):
    """Notify client when their account is rejected"""
    await send_activity_alert("client", client_id, "client_rejected", {
        "name": client_name,
        "rejection_reason": reason
    })
