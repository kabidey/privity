"""
Role-Based Email Notification Service

Automatically sends attention emails to users based on their assigned roles
when relevant events are triggered in their menu sections.

Supported notification categories:
- Finance: Payment events, receivables, financial reports
- Partners Desk: Partner activities, commissions
- Business Partners: Client referrals, payouts
- Custom Roles: Based on assigned permissions
"""
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime, timezone
from database import db

logger = logging.getLogger(__name__)

# Map menu sections to roles that should be notified
ROLE_NOTIFICATION_MAP = {
    "finance": {
        "roles": [1, 2, 3],  # PE Desk, PE Manager, Finance
        "permission_check": "finance.*",
        "events": [
            "payment_received",
            "payment_pending",
            "payment_overdue",
            "receivable_created",
            "payout_requested",
            "financial_report"
        ]
    },
    "partners": {
        "roles": [1, 2, 5],  # PE Desk, PE Manager, Partners Desk
        "permission_check": "referral_partners.*",
        "events": [
            "new_partner_registered",
            "partner_commission_earned",
            "partner_payout_requested",
            "partner_performance_alert"
        ]
    },
    "business_partners": {
        "roles": [1, 2, 5],  # PE Desk, PE Manager, Partners Desk
        "permission_check": "business_partners.*",
        "events": [
            "new_bp_registered",
            "bp_client_referral",
            "bp_commission_earned",
            "bp_payout_processed"
        ]
    },
    "bookings": {
        "roles": [1, 2],  # PE Desk, PE Manager
        "permission_check": "bookings.*",
        "events": [
            "new_booking_created",
            "booking_approved",
            "booking_cancelled",
            "dp_transfer_complete"
        ]
    },
    "inventory": {
        "roles": [1, 2],  # PE Desk, PE Manager
        "permission_check": "inventory.*",
        "events": [
            "low_stock_alert",
            "stock_added",
            "price_updated"
        ]
    },
    "purchases": {
        "roles": [1, 2, 3],  # PE Desk, PE Manager, Finance
        "permission_check": "purchases.*",
        "events": [
            "new_purchase_created",
            "purchase_payment_due",
            "vendor_payment_processed"
        ]
    }
}

# Email templates for different event types
EVENT_EMAIL_TEMPLATES = {
    "payment_received": {
        "subject": "💰 Payment Received - {{booking_number}}",
        "body": """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: #064E3B; padding: 20px; text-align: center;">
                <h2 style="color: white; margin: 0;">Payment Received</h2>
            </div>
            <div style="padding: 20px; background: #f9fafb;">
                <p>A payment has been received and requires your attention:</p>
                <table style="width: 100%; border-collapse: collapse; margin: 15px 0;">
                    <tr style="background: #e5e7eb;">
                        <td style="padding: 10px; font-weight: bold;">Booking #</td>
                        <td style="padding: 10px;">{{booking_number}}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; font-weight: bold;">Client</td>
                        <td style="padding: 10px;">{{client_name}}</td>
                    </tr>
                    <tr style="background: #e5e7eb;">
                        <td style="padding: 10px; font-weight: bold;">Amount</td>
                        <td style="padding: 10px; color: #059669; font-weight: bold;">₹{{amount}}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; font-weight: bold;">Payment Mode</td>
                        <td style="padding: 10px;">{{payment_mode}}</td>
                    </tr>
                    <tr style="background: #e5e7eb;">
                        <td style="padding: 10px; font-weight: bold;">Recorded By</td>
                        <td style="padding: 10px;">{{recorded_by}}</td>
                    </tr>
                </table>
                <p style="color: #6b7280; font-size: 12px;">This is an automated notification from Privity.</p>
            </div>
        </div>
        """
    },
    "payment_pending": {
        "subject": "⏳ Payment Pending Approval - {{booking_number}}",
        "body": """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: #f59e0b; padding: 20px; text-align: center;">
                <h2 style="color: white; margin: 0;">Payment Pending Approval</h2>
            </div>
            <div style="padding: 20px; background: #f9fafb;">
                <p>A payment is pending approval and requires your action:</p>
                <table style="width: 100%; border-collapse: collapse; margin: 15px 0;">
                    <tr style="background: #e5e7eb;">
                        <td style="padding: 10px; font-weight: bold;">Booking #</td>
                        <td style="padding: 10px;">{{booking_number}}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; font-weight: bold;">Client</td>
                        <td style="padding: 10px;">{{client_name}}</td>
                    </tr>
                    <tr style="background: #e5e7eb;">
                        <td style="padding: 10px; font-weight: bold;">Amount</td>
                        <td style="padding: 10px; color: #f59e0b; font-weight: bold;">₹{{amount}}</td>
                    </tr>
                </table>
                <div style="text-align: center; margin: 20px 0;">
                    <a href="{{action_url}}" style="background: #064E3B; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px;">Review Payment</a>
                </div>
            </div>
        </div>
        """
    },
    "new_booking_created": {
        "subject": "📋 New Booking Created - {{booking_number}}",
        "body": """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: #064E3B; padding: 20px; text-align: center;">
                <h2 style="color: white; margin: 0;">New Booking Created</h2>
            </div>
            <div style="padding: 20px; background: #f9fafb;">
                <p>A new booking has been created:</p>
                <table style="width: 100%; border-collapse: collapse; margin: 15px 0;">
                    <tr style="background: #e5e7eb;">
                        <td style="padding: 10px; font-weight: bold;">Booking #</td>
                        <td style="padding: 10px;">{{booking_number}}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; font-weight: bold;">Client</td>
                        <td style="padding: 10px;">{{client_name}}</td>
                    </tr>
                    <tr style="background: #e5e7eb;">
                        <td style="padding: 10px; font-weight: bold;">Stock</td>
                        <td style="padding: 10px;">{{stock_symbol}} - {{stock_name}}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; font-weight: bold;">Quantity</td>
                        <td style="padding: 10px;">{{quantity}} shares</td>
                    </tr>
                    <tr style="background: #e5e7eb;">
                        <td style="padding: 10px; font-weight: bold;">Total Amount</td>
                        <td style="padding: 10px; color: #059669; font-weight: bold;">₹{{total_amount}}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; font-weight: bold;">Created By</td>
                        <td style="padding: 10px;">{{created_by}}</td>
                    </tr>
                </table>
            </div>
        </div>
        """
    },
    "new_partner_registered": {
        "subject": "🤝 New Referral Partner Registered - {{partner_name}}",
        "body": """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: #7c3aed; padding: 20px; text-align: center;">
                <h2 style="color: white; margin: 0;">New Referral Partner</h2>
            </div>
            <div style="padding: 20px; background: #f9fafb;">
                <p>A new referral partner has registered:</p>
                <table style="width: 100%; border-collapse: collapse; margin: 15px 0;">
                    <tr style="background: #e5e7eb;">
                        <td style="padding: 10px; font-weight: bold;">Name</td>
                        <td style="padding: 10px;">{{partner_name}}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; font-weight: bold;">Email</td>
                        <td style="padding: 10px;">{{partner_email}}</td>
                    </tr>
                    <tr style="background: #e5e7eb;">
                        <td style="padding: 10px; font-weight: bold;">Phone</td>
                        <td style="padding: 10px;">{{partner_phone}}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; font-weight: bold;">Registered On</td>
                        <td style="padding: 10px;">{{registered_date}}</td>
                    </tr>
                </table>
            </div>
        </div>
        """
    },
    "new_bp_registered": {
        "subject": "🏢 New Business Partner Registered - {{bp_name}}",
        "body": """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: #0891b2; padding: 20px; text-align: center;">
                <h2 style="color: white; margin: 0;">New Business Partner</h2>
            </div>
            <div style="padding: 20px; background: #f9fafb;">
                <p>A new business partner has been registered:</p>
                <table style="width: 100%; border-collapse: collapse; margin: 15px 0;">
                    <tr style="background: #e5e7eb;">
                        <td style="padding: 10px; font-weight: bold;">Company</td>
                        <td style="padding: 10px;">{{bp_name}}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; font-weight: bold;">Contact Person</td>
                        <td style="padding: 10px;">{{contact_person}}</td>
                    </tr>
                    <tr style="background: #e5e7eb;">
                        <td style="padding: 10px; font-weight: bold;">Email</td>
                        <td style="padding: 10px;">{{bp_email}}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; font-weight: bold;">Registered By</td>
                        <td style="padding: 10px;">{{registered_by}}</td>
                    </tr>
                </table>
            </div>
        </div>
        """
    },
    "bp_client_referral": {
        "subject": "👥 New Client Referral from {{bp_name}}",
        "body": """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: #059669; padding: 20px; text-align: center;">
                <h2 style="color: white; margin: 0;">New Client Referral</h2>
            </div>
            <div style="padding: 20px; background: #f9fafb;">
                <p>A business partner has referred a new client:</p>
                <table style="width: 100%; border-collapse: collapse; margin: 15px 0;">
                    <tr style="background: #e5e7eb;">
                        <td style="padding: 10px; font-weight: bold;">Business Partner</td>
                        <td style="padding: 10px;">{{bp_name}}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; font-weight: bold;">Client Name</td>
                        <td style="padding: 10px;">{{client_name}}</td>
                    </tr>
                    <tr style="background: #e5e7eb;">
                        <td style="padding: 10px; font-weight: bold;">Client Email</td>
                        <td style="padding: 10px;">{{client_email}}</td>
                    </tr>
                </table>
            </div>
        </div>
        """
    },
    "partner_commission_earned": {
        "subject": "💵 Commission Earned - {{partner_name}}",
        "body": """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: #059669; padding: 20px; text-align: center;">
                <h2 style="color: white; margin: 0;">Commission Earned</h2>
            </div>
            <div style="padding: 20px; background: #f9fafb;">
                <p>A partner has earned commission on a transaction:</p>
                <table style="width: 100%; border-collapse: collapse; margin: 15px 0;">
                    <tr style="background: #e5e7eb;">
                        <td style="padding: 10px; font-weight: bold;">Partner</td>
                        <td style="padding: 10px;">{{partner_name}}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; font-weight: bold;">Booking #</td>
                        <td style="padding: 10px;">{{booking_number}}</td>
                    </tr>
                    <tr style="background: #e5e7eb;">
                        <td style="padding: 10px; font-weight: bold;">Commission Amount</td>
                        <td style="padding: 10px; color: #059669; font-weight: bold;">₹{{commission_amount}}</td>
                    </tr>
                </table>
            </div>
        </div>
        """
    },
    "low_stock_alert": {
        "subject": "⚠️ Low Stock Alert - {{stock_symbol}}",
        "body": """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: #dc2626; padding: 20px; text-align: center;">
                <h2 style="color: white; margin: 0;">Low Stock Alert</h2>
            </div>
            <div style="padding: 20px; background: #f9fafb;">
                <p>A stock has reached low inventory levels:</p>
                <table style="width: 100%; border-collapse: collapse; margin: 15px 0;">
                    <tr style="background: #e5e7eb;">
                        <td style="padding: 10px; font-weight: bold;">Stock</td>
                        <td style="padding: 10px;">{{stock_symbol}} - {{stock_name}}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; font-weight: bold;">Available Qty</td>
                        <td style="padding: 10px; color: #dc2626; font-weight: bold;">{{available_quantity}}</td>
                    </tr>
                    <tr style="background: #e5e7eb;">
                        <td style="padding: 10px; font-weight: bold;">Threshold</td>
                        <td style="padding: 10px;">{{threshold}}</td>
                    </tr>
                </table>
                <p style="color: #dc2626;">Please consider restocking this item.</p>
            </div>
        </div>
        """
    },
    "dp_transfer_complete": {
        "subject": "✅ DP Transfer Complete - {{booking_number}}",
        "body": """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: #059669; padding: 20px; text-align: center;">
                <h2 style="color: white; margin: 0;">DP Transfer Complete</h2>
            </div>
            <div style="padding: 20px; background: #f9fafb;">
                <p>A DP transfer has been completed:</p>
                <table style="width: 100%; border-collapse: collapse; margin: 15px 0;">
                    <tr style="background: #e5e7eb;">
                        <td style="padding: 10px; font-weight: bold;">Booking #</td>
                        <td style="padding: 10px;">{{booking_number}}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; font-weight: bold;">Client</td>
                        <td style="padding: 10px;">{{client_name}}</td>
                    </tr>
                    <tr style="background: #e5e7eb;">
                        <td style="padding: 10px; font-weight: bold;">Stock</td>
                        <td style="padding: 10px;">{{stock_symbol}}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; font-weight: bold;">Quantity</td>
                        <td style="padding: 10px;">{{quantity}} shares</td>
                    </tr>
                    <tr style="background: #e5e7eb;">
                        <td style="padding: 10px; font-weight: bold;">DP Type</td>
                        <td style="padding: 10px;">{{dp_type}}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; font-weight: bold;">Transferred By</td>
                        <td style="padding: 10px;">{{transferred_by}}</td>
                    </tr>
                </table>
            </div>
        </div>
        """
    },
    "payout_requested": {
        "subject": "💸 Payout Requested - {{partner_name}}",
        "body": """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: #f59e0b; padding: 20px; text-align: center;">
                <h2 style="color: white; margin: 0;">Payout Request</h2>
            </div>
            <div style="padding: 20px; background: #f9fafb;">
                <p>A partner has requested a payout:</p>
                <table style="width: 100%; border-collapse: collapse; margin: 15px 0;">
                    <tr style="background: #e5e7eb;">
                        <td style="padding: 10px; font-weight: bold;">Partner</td>
                        <td style="padding: 10px;">{{partner_name}}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; font-weight: bold;">Amount</td>
                        <td style="padding: 10px; color: #f59e0b; font-weight: bold;">₹{{amount}}</td>
                    </tr>
                    <tr style="background: #e5e7eb;">
                        <td style="padding: 10px; font-weight: bold;">Request Date</td>
                        <td style="padding: 10px;">{{request_date}}</td>
                    </tr>
                </table>
                <div style="text-align: center; margin: 20px 0;">
                    <a href="{{action_url}}" style="background: #064E3B; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px;">Process Payout</a>
                </div>
            </div>
        </div>
        """
    }
}


async def get_users_by_role(role_ids: List[int]) -> List[Dict]:
    """Get all active users with specified roles."""
    users = await db.users.find(
        {
            "role": {"$in": role_ids},
            "is_active": {"$ne": False},
            "email": {"$exists": True, "$ne": ""}
        },
        {"_id": 0, "id": 1, "name": 1, "email": 1, "role": 1}
    ).to_list(1000)
    return users


async def get_users_with_permission(permission: str) -> List[Dict]:
    """Get all active users who have a specific permission (including custom roles)."""
    from services.permission_service import check_permission
    
    # Get all active users
    all_users = await db.users.find(
        {
            "is_active": {"$ne": False},
            "email": {"$exists": True, "$ne": ""}
        },
        {"_id": 0, "id": 1, "name": 1, "email": 1, "role": 1}
    ).to_list(1000)
    
    # Filter users who have the permission
    users_with_permission = []
    for user in all_users:
        role_id = user.get("role", 7)
        has_permission = await check_permission(role_id, permission)
        if has_permission:
            users_with_permission.append(user)
    
    return users_with_permission


def render_template(template: str, variables: Dict[str, Any]) -> str:
    """Replace template variables with actual values."""
    result = template
    for key, value in variables.items():
        placeholder = "{{" + key + "}}"
        result = result.replace(placeholder, str(value) if value is not None else "N/A")
    return result


async def send_role_notification(
    event_type: str,
    category: str,
    variables: Dict[str, Any],
    exclude_user_id: Optional[str] = None,
    additional_recipients: Optional[List[str]] = None
) -> Dict:
    """
    Send notification emails to users based on their roles for a specific event.
    
    Args:
        event_type: The type of event (e.g., 'payment_received', 'new_booking_created')
        category: The menu category (e.g., 'finance', 'partners', 'bookings')
        variables: Template variables for the email
        exclude_user_id: User ID to exclude (usually the one who triggered the event)
        additional_recipients: Additional email addresses to notify
    
    Returns:
        Dict with results of notification sending
    """
    from services.email_service import send_email
    
    results = {
        "event_type": event_type,
        "category": category,
        "notifications_sent": 0,
        "notifications_failed": 0,
        "recipients": [],
        "errors": []
    }
    
    # Get template for this event
    template = EVENT_EMAIL_TEMPLATES.get(event_type)
    if not template:
        logger.warning(f"No email template found for event: {event_type}")
        return results
    
    # Get category config
    category_config = ROLE_NOTIFICATION_MAP.get(category)
    if not category_config:
        logger.warning(f"No notification config found for category: {category}")
        return results
    
    # Get users to notify - by role and by permission
    role_ids = category_config.get("roles", [])
    permission_check = category_config.get("permission_check")
    
    # Get users by role
    users_by_role = await get_users_by_role(role_ids)
    
    # Get users by permission (for custom roles)
    users_by_permission = []
    if permission_check:
        users_by_permission = await get_users_with_permission(permission_check)
    
    # Combine and deduplicate
    all_users = {u["id"]: u for u in users_by_role}
    for u in users_by_permission:
        if u["id"] not in all_users:
            all_users[u["id"]] = u
    
    recipients = list(all_users.values())
    
    # Exclude the triggering user
    if exclude_user_id:
        recipients = [r for r in recipients if r["id"] != exclude_user_id]
    
    # Render email content
    subject = render_template(template["subject"], variables)
    body = render_template(template["body"], variables)
    
    # Send to role-based recipients
    for recipient in recipients:
        try:
            await send_email(
                to_email=recipient["email"],
                subject=subject,
                body=body
            )
            results["notifications_sent"] += 1
            results["recipients"].append(recipient["email"])
        except Exception as e:
            results["notifications_failed"] += 1
            results["errors"].append({"email": recipient["email"], "error": str(e)})
            logger.error(f"Failed to send notification to {recipient['email']}: {e}")
    
    # Send to additional recipients
    if additional_recipients:
        for email in additional_recipients:
            if email not in results["recipients"]:
                try:
                    await send_email(
                        to_email=email,
                        subject=subject,
                        body=body
                    )
                    results["notifications_sent"] += 1
                    results["recipients"].append(email)
                except Exception as e:
                    results["notifications_failed"] += 1
                    results["errors"].append({"email": email, "error": str(e)})
    
    # Log the notification
    await db.notification_logs.insert_one({
        "event_type": event_type,
        "category": category,
        "variables": {k: str(v)[:100] for k, v in variables.items()},  # Truncate for storage
        "recipients_count": results["notifications_sent"],
        "failed_count": results["notifications_failed"],
        "triggered_at": datetime.now(timezone.utc).isoformat(),
        "exclude_user_id": exclude_user_id
    })
    
    logger.info(f"Role notification [{event_type}]: {results['notifications_sent']} sent, {results['notifications_failed']} failed")
    
    return results


# Convenience functions for common events
async def notify_payment_received(
    booking_number: str,
    client_name: str,
    amount: float,
    payment_mode: str,
    recorded_by: str,
    exclude_user_id: Optional[str] = None
) -> Dict:
    """Notify Finance and PE roles about a received payment."""
    return await send_role_notification(
        event_type="payment_received",
        category="finance",
        variables={
            "booking_number": booking_number,
            "client_name": client_name,
            "amount": f"{amount:,.2f}",
            "payment_mode": payment_mode,
            "recorded_by": recorded_by
        },
        exclude_user_id=exclude_user_id
    )


async def notify_new_booking(
    booking_number: str,
    client_name: str,
    stock_symbol: str,
    stock_name: str,
    quantity: int,
    total_amount: float,
    created_by: str,
    exclude_user_id: Optional[str] = None
) -> Dict:
    """Notify PE roles about a new booking."""
    return await send_role_notification(
        event_type="new_booking_created",
        category="bookings",
        variables={
            "booking_number": booking_number,
            "client_name": client_name,
            "stock_symbol": stock_symbol,
            "stock_name": stock_name,
            "quantity": quantity,
            "total_amount": f"{total_amount:,.2f}",
            "created_by": created_by
        },
        exclude_user_id=exclude_user_id
    )


async def notify_new_partner(
    partner_name: str,
    partner_email: str,
    partner_phone: str,
    exclude_user_id: Optional[str] = None
) -> Dict:
    """Notify Partners Desk about a new referral partner."""
    return await send_role_notification(
        event_type="new_partner_registered",
        category="partners",
        variables={
            "partner_name": partner_name,
            "partner_email": partner_email,
            "partner_phone": partner_phone or "N/A",
            "registered_date": datetime.now(timezone.utc).strftime("%d %b %Y, %I:%M %p")
        },
        exclude_user_id=exclude_user_id
    )


async def notify_new_business_partner(
    bp_name: str,
    contact_person: str,
    bp_email: str,
    registered_by: str,
    exclude_user_id: Optional[str] = None
) -> Dict:
    """Notify about a new business partner registration."""
    return await send_role_notification(
        event_type="new_bp_registered",
        category="business_partners",
        variables={
            "bp_name": bp_name,
            "contact_person": contact_person,
            "bp_email": bp_email,
            "registered_by": registered_by
        },
        exclude_user_id=exclude_user_id
    )


async def notify_bp_client_referral(
    bp_name: str,
    client_name: str,
    client_email: str,
    exclude_user_id: Optional[str] = None
) -> Dict:
    """Notify about a client referred by a business partner."""
    return await send_role_notification(
        event_type="bp_client_referral",
        category="business_partners",
        variables={
            "bp_name": bp_name,
            "client_name": client_name,
            "client_email": client_email
        },
        exclude_user_id=exclude_user_id
    )


async def notify_dp_transfer(
    booking_number: str,
    client_name: str,
    stock_symbol: str,
    quantity: int,
    dp_type: str,
    transferred_by: str,
    exclude_user_id: Optional[str] = None
) -> Dict:
    """Notify about a completed DP transfer."""
    return await send_role_notification(
        event_type="dp_transfer_complete",
        category="bookings",
        variables={
            "booking_number": booking_number,
            "client_name": client_name,
            "stock_symbol": stock_symbol,
            "quantity": quantity,
            "dp_type": dp_type,
            "transferred_by": transferred_by
        },
        exclude_user_id=exclude_user_id
    )


async def notify_low_stock(
    stock_symbol: str,
    stock_name: str,
    available_quantity: int,
    threshold: int = 100
) -> Dict:
    """Notify about low stock levels."""
    return await send_role_notification(
        event_type="low_stock_alert",
        category="inventory",
        variables={
            "stock_symbol": stock_symbol,
            "stock_name": stock_name,
            "available_quantity": available_quantity,
            "threshold": threshold
        }
    )


async def notify_partner_commission(
    partner_name: str,
    booking_number: str,
    commission_amount: float,
    exclude_user_id: Optional[str] = None
) -> Dict:
    """Notify about partner commission earned."""
    return await send_role_notification(
        event_type="partner_commission_earned",
        category="partners",
        variables={
            "partner_name": partner_name,
            "booking_number": booking_number,
            "commission_amount": f"{commission_amount:,.2f}"
        },
        exclude_user_id=exclude_user_id
    )
