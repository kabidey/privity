"""
Email service for sending notifications with audit logging
"""
import logging
import smtplib
import random
import string
import uuid
from datetime import datetime, timezone
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, Dict, Any, List

from config import (
    EMAIL_HOST, EMAIL_PORT, EMAIL_USERNAME, EMAIL_PASSWORD, EMAIL_FROM,
    OTP_EXPIRY_MINUTES, DEFAULT_EMAIL_TEMPLATES
)


async def log_email(
    to_email: str,
    subject: str,
    template_key: Optional[str],
    status: str,
    error_message: Optional[str] = None,
    cc_email: Optional[str] = None,
    variables: Optional[Dict[str, Any]] = None,
    related_entity_type: Optional[str] = None,
    related_entity_id: Optional[str] = None
):
    """Log email sending attempt to database for audit purposes"""
    from database import db
    
    log_entry = {
        "id": str(uuid.uuid4()),
        "to_email": to_email,
        "cc_email": cc_email,
        "subject": subject,
        "template_key": template_key,
        "status": status,  # "sent", "failed", "skipped"
        "error_message": error_message,
        "variables": variables or {},
        "related_entity_type": related_entity_type,  # "booking", "client", "rp", "user", etc.
        "related_entity_id": related_entity_id,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    try:
        await db.email_logs.insert_one(log_entry)
    except Exception as e:
        logging.error(f"Failed to log email: {e}")


async def get_smtp_config():
    """Get SMTP configuration from database or fall back to environment variables"""
    from database import db
    
    config = await db.email_config.find_one({"_id": "smtp_config"})
    
    if config and config.get("is_enabled") and config.get("smtp_password"):
        return {
            "host": config["smtp_host"],
            "port": config["smtp_port"],
            "username": config["smtp_username"],
            "password": config["smtp_password"],
            "from_email": config["smtp_from_email"],
            "from_name": config.get("smtp_from_name", "SMIFS Private Equity System"),
            "use_tls": config.get("use_tls", True),
            "use_ssl": config.get("use_ssl", False),
            "timeout": config.get("timeout", 30)
        }
    
    # Fall back to environment variables
    if EMAIL_USERNAME and EMAIL_PASSWORD:
        return {
            "host": EMAIL_HOST,
            "port": EMAIL_PORT,
            "username": EMAIL_USERNAME,
            "password": EMAIL_PASSWORD,
            "from_email": EMAIL_FROM,
            "from_name": "SMIFS Private Equity System",
            "use_tls": True,
            "use_ssl": False,
            "timeout": 30
        }
    
    return None


async def get_email_template(template_key: str) -> dict:
    """Get email template from database or fall back to default"""
    from database import db
    
    # Try to get from database first
    template = await db.email_templates.find_one({"key": template_key}, {"_id": 0})
    
    if not template:
        # Fall back to default template
        template = DEFAULT_EMAIL_TEMPLATES.get(template_key)
        if template:
            # Save default to database for future customization
            await db.email_templates.insert_one(template)
    
    return template


def render_template(template: dict, variables: Dict[str, Any]) -> tuple:
    """Render email template with variable substitution"""
    subject = template.get("subject", "")
    body = template.get("body", "")
    
    for key, value in variables.items():
        placeholder = "{{" + key + "}}"
        subject = subject.replace(placeholder, str(value) if value is not None else "")
        body = body.replace(placeholder, str(value) if value is not None else "")
    
    return subject, body


async def send_templated_email(
    template_key: str,
    to_email: str,
    variables: Dict[str, Any],
    cc_email: Optional[str] = None,
    additional_emails: Optional[list] = None,
    related_entity_type: Optional[str] = None,
    related_entity_id: Optional[str] = None
):
    """Send email using a template with variable substitution
    
    Args:
        template_key: The template identifier
        to_email: Primary recipient email
        variables: Template variable substitutions
        cc_email: Optional CC email
        additional_emails: List of additional emails to send to (e.g., secondary and tertiary)
        related_entity_type: Type of related entity (booking, client, rp, user)
        related_entity_id: ID of related entity
    """
    template = await get_email_template(template_key)
    
    if not template:
        logging.warning(f"Email template '{template_key}' not found")
        await log_email(
            to_email=to_email,
            subject=f"[Template: {template_key}]",
            template_key=template_key,
            status="skipped",
            error_message="Template not found",
            variables=variables,
            related_entity_type=related_entity_type,
            related_entity_id=related_entity_id
        )
        return False
    
    if not template.get("is_active", True):
        logging.info(f"Email template '{template_key}' is disabled")
        await log_email(
            to_email=to_email,
            subject=template.get("subject", f"[Template: {template_key}]"),
            template_key=template_key,
            status="skipped",
            error_message="Template disabled",
            variables=variables,
            related_entity_type=related_entity_type,
            related_entity_id=related_entity_id
        )
        return False
    
    subject, body = render_template(template, variables)
    
    # Collect all recipients
    all_recipients = [to_email] if to_email else []
    if additional_emails:
        for email in additional_emails:
            if email and email not in all_recipients:
                all_recipients.append(email)
    
    # Send to primary recipient with CC
    if to_email:
        await send_email(
            to_email, 
            subject, 
            body, 
            cc_email,
            template_key=template_key,
            variables=variables,
            related_entity_type=related_entity_type,
            related_entity_id=related_entity_id
        )
    
    # Send to additional emails (without CC to avoid duplicates)
    if additional_emails:
        for email in additional_emails:
            if email and email != to_email:
                await send_email(
                    email, 
                    subject, 
                    body, 
                    None,
                    template_key=template_key,
                    variables=variables,
                    related_entity_type=related_entity_type,
                    related_entity_id=related_entity_id
                )
    
    return True


async def send_email(
    to_email: str, 
    subject: str, 
    body: str, 
    cc_email: Optional[str] = None,
    template_key: Optional[str] = None,
    variables: Optional[Dict[str, Any]] = None,
    related_entity_type: Optional[str] = None,
    related_entity_id: Optional[str] = None
):
    """Send email via SMTP with optional CC - uses database config or env vars"""
    smtp_config = await get_smtp_config()
    
    if not smtp_config:
        logging.warning("Email not configured - neither database config nor environment variables set")
        await log_email(
            to_email=to_email,
            subject=subject,
            template_key=template_key,
            status="skipped",
            error_message="Email not configured",
            cc_email=cc_email,
            variables=variables,
            related_entity_type=related_entity_type,
            related_entity_id=related_entity_id
        )
        return
    
    try:
        msg = MIMEMultipart()
        from_display = f"{smtp_config['from_name']} <{smtp_config['from_email']}>"
        msg['From'] = from_display
        msg['To'] = to_email
        if cc_email:
            msg['Cc'] = cc_email
        msg['Subject'] = subject
        
        msg.attach(MIMEText(body, 'html'))
        
        recipients = [to_email]
        if cc_email:
            recipients.append(cc_email)
        
        # Connect using appropriate method
        if smtp_config['use_ssl']:
            server = smtplib.SMTP_SSL(
                smtp_config['host'], 
                smtp_config['port'], 
                timeout=smtp_config['timeout']
            )
        else:
            server = smtplib.SMTP(
                smtp_config['host'], 
                smtp_config['port'], 
                timeout=smtp_config['timeout']
            )
            if smtp_config['use_tls']:
                server.starttls()
        
        server.login(smtp_config['username'], smtp_config['password'])
        server.sendmail(smtp_config['from_email'], recipients, msg.as_string())
        server.quit()
        
        logging.info(f"Email sent successfully to {to_email}")
        
        # Log successful email
        await log_email(
            to_email=to_email,
            subject=subject,
            template_key=template_key,
            status="sent",
            cc_email=cc_email,
            variables=variables,
            related_entity_type=related_entity_type,
            related_entity_id=related_entity_id
        )
        
    except Exception as e:
        logging.error(f"Failed to send email: {e}")
        
        # Log failed email
        await log_email(
            to_email=to_email,
            subject=subject,
            template_key=template_key,
            status="failed",
            error_message=str(e),
            cc_email=cc_email,
            variables=variables,
            related_entity_type=related_entity_type,
            related_entity_id=related_entity_id
        )


def generate_otp(length: int = 6) -> str:
    """Generate numeric OTP"""
    return ''.join(random.choices(string.digits, k=length))


async def send_otp_email(to_email: str, otp: str, user_name: str = "User"):
    """Send OTP email for password reset"""
    subject = "Password Reset OTP - Private Equity System"
    body = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: #333;">Password Reset Request</h2>
        <p>Dear {user_name},</p>
        <p>You have requested to reset your password. Use the following OTP to proceed:</p>
        <div style="background: #f5f5f5; padding: 20px; text-align: center; margin: 20px 0;">
            <h1 style="color: #007bff; letter-spacing: 5px; margin: 0;">{otp}</h1>
        </div>
        <p><strong>This OTP is valid for {OTP_EXPIRY_MINUTES} minutes.</strong></p>
        <p>If you did not request this password reset, please ignore this email.</p>
        <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
        <p style="color: #666; font-size: 12px;">This is an automated message from Private Equity System.</p>
    </div>
    """
    await send_email(to_email, subject, body)


async def send_booking_notification_email(
    client_email: str,
    client_name: str,
    stock_symbol: str,
    stock_name: str,
    quantity: int,
    buying_price: float,
    booking_number: str,
    cc_email: Optional[str] = None
):
    """Send booking creation notification email"""
    subject = f"New Booking Order - {stock_symbol} | {booking_number}"
    body = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: #333;">Booking Order Notification</h2>
        <p>Dear {client_name},</p>
        <p>A new booking order has been created and is pending internal approval. You will receive another email to confirm your acceptance once approved.</p>
        
        <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
            <tr style="background-color: #f3f4f6;">
                <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Booking ID</strong></td>
                <td style="padding: 10px; border: 1px solid #e5e7eb;">{booking_number}</td>
            </tr>
            <tr>
                <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Stock</strong></td>
                <td style="padding: 10px; border: 1px solid #e5e7eb;">{stock_symbol} - {stock_name}</td>
            </tr>
            <tr style="background-color: #f3f4f6;">
                <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Quantity</strong></td>
                <td style="padding: 10px; border: 1px solid #e5e7eb;">{quantity}</td>
            </tr>
            <tr>
                <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Landing Price</strong></td>
                <td style="padding: 10px; border: 1px solid #e5e7eb;">₹{buying_price:,.2f}</td>
            </tr>
        </table>
        
        <p style="color: #6b7280; font-size: 14px;">This is an automated notification. You will receive a confirmation request email once the booking is approved internally.</p>
        
        <p>Best regards,<br><strong>SMIFS Private Equity System</strong></p>
    </div>
    """
    await send_email(client_email, subject, body, cc_email)


async def send_booking_approval_email(
    client_email: str,
    client_name: str,
    stock_symbol: str,
    stock_name: str,
    quantity: int,
    buying_price: float,
    booking_id: str,
    booking_number: str,
    confirmation_token: str,
    approved_by: str,
    frontend_url: str,
    client_otc_ucc: str = "N/A",
    cc_email: Optional[str] = None
):
    """Send booking approval email with confirmation buttons"""
    subject = f"Action Required: Confirm Booking - {stock_symbol} | {booking_number}"
    body = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: #10b981;">Booking Approved - Please Confirm ✓</h2>
        <p>Dear {client_name},</p>
        <p>Your booking order has been <strong style="color: #10b981;">APPROVED</strong> by PE Desk. Please confirm your acceptance to proceed.</p>
        
        <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
            <tr style="background-color: #f3f4f6;">
                <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Booking ID</strong></td>
                <td style="padding: 10px; border: 1px solid #e5e7eb;">{booking_number}</td>
            </tr>
            <tr>
                <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Client OTC UCC</strong></td>
                <td style="padding: 10px; border: 1px solid #e5e7eb;">{client_otc_ucc}</td>
            </tr>
            <tr style="background-color: #f3f4f6;">
                <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Stock</strong></td>
                <td style="padding: 10px; border: 1px solid #e5e7eb;">{stock_symbol} - {stock_name}</td>
            </tr>
            <tr>
                <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Quantity</strong></td>
                <td style="padding: 10px; border: 1px solid #e5e7eb;">{quantity}</td>
            </tr>
            <tr style="background-color: #f3f4f6;">
                <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Landing Price</strong></td>
                <td style="padding: 10px; border: 1px solid #e5e7eb;">₹{buying_price:,.2f}</td>
            </tr>
            <tr>
                <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Total Value</strong></td>
                <td style="padding: 10px; border: 1px solid #e5e7eb;">₹{(buying_price * quantity):,.2f}</td>
            </tr>
            <tr style="background-color: #f3f4f6;">
                <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Approved By</strong></td>
                <td style="padding: 10px; border: 1px solid #e5e7eb;">{approved_by} (PE Desk)</td>
            </tr>
        </table>
        
        <div style="margin: 30px 0; text-align: center;">
            <p style="margin-bottom: 20px; font-weight: bold;">Please confirm your booking:</p>
            <a href="{frontend_url}/booking-confirm/{booking_id}/{confirmation_token}/accept" 
               style="display: inline-block; background-color: #22c55e; color: white; padding: 12px 30px; text-decoration: none; border-radius: 6px; margin-right: 10px; font-weight: bold;">
                ✓ ACCEPT BOOKING
            </a>
            <a href="{frontend_url}/booking-confirm/{booking_id}/{confirmation_token}/deny" 
               style="display: inline-block; background-color: #ef4444; color: white; padding: 12px 30px; text-decoration: none; border-radius: 6px; font-weight: bold;">
                ✗ DENY BOOKING
            </a>
        </div>
        
        <p style="color: #6b7280; font-size: 14px;">Please review and confirm this booking. If you accept, payment can be initiated. If you deny, the booking will be cancelled.</p>
        
        <p>Best regards,<br><strong>SMIFS Private Equity System</strong></p>
    </div>
    """
    await send_email(client_email, subject, body, cc_email)


async def send_loss_booking_pending_email(
    client_email: str,
    client_name: str,
    stock_symbol: str,
    booking_number: str,
    cc_email: Optional[str] = None
):
    """Send email for loss booking pending loss approval"""
    subject = f"Booking Approved - Pending Loss Review | {booking_number}"
    body = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: #f59e0b;">Booking Approved - Pending Loss Review</h2>
        <p>Dear {client_name},</p>
        <p>Your booking order has been approved. However, since this is a loss transaction, it requires additional review. You will receive a confirmation request once fully approved.</p>
        
        <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
            <tr style="background-color: #f3f4f6;">
                <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Booking ID</strong></td>
                <td style="padding: 10px; border: 1px solid #e5e7eb;">{booking_number}</td>
            </tr>
            <tr>
                <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Stock</strong></td>
                <td style="padding: 10px; border: 1px solid #e5e7eb;">{stock_symbol}</td>
            </tr>
            <tr style="background-color: #f3f4f6;">
                <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Status</strong></td>
                <td style="padding: 10px; border: 1px solid #e5e7eb;"><span style="color: #f59e0b;">Pending Loss Review</span></td>
            </tr>
        </table>
        
        <p>Best regards,<br><strong>SMIFS Private Equity System</strong></p>
    </div>
    """
    await send_email(client_email, subject, body, cc_email)


async def send_loss_approval_email(
    client_email: str,
    client_name: str,
    stock_symbol: str,
    quantity: int,
    buying_price: float,
    selling_price: float,
    booking_id: str,
    booking_number: str,
    confirmation_token: str,
    frontend_url: str,
    cc_email: Optional[str] = None
):
    """Send email for fully approved loss booking with confirmation buttons"""
    subject = f"Action Required: Confirm Loss Booking - {stock_symbol} | {booking_number}"
    body = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: #10b981;">Booking Fully Approved - Please Confirm ✓</h2>
        <p>Dear {client_name},</p>
        <p>Your loss booking order has been <strong style="color: #10b981;">FULLY APPROVED</strong>. Please confirm your acceptance to proceed.</p>
        
        <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
            <tr style="background-color: #f3f4f6;">
                <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Booking ID</strong></td>
                <td style="padding: 10px; border: 1px solid #e5e7eb;">{booking_number}</td>
            </tr>
            <tr>
                <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Stock</strong></td>
                <td style="padding: 10px; border: 1px solid #e5e7eb;">{stock_symbol}</td>
            </tr>
            <tr style="background-color: #f3f4f6;">
                <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Quantity</strong></td>
                <td style="padding: 10px; border: 1px solid #e5e7eb;">{quantity}</td>
            </tr>
            <tr>
                <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Landing Price</strong></td>
                <td style="padding: 10px; border: 1px solid #e5e7eb;">₹{buying_price:,.2f}</td>
            </tr>
            <tr style="background-color: #fef3c7;">
                <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Selling Price</strong></td>
                <td style="padding: 10px; border: 1px solid #e5e7eb;">₹{selling_price:,.2f} <span style="color: #dc2626;">(Loss Transaction)</span></td>
            </tr>
        </table>
        
        <div style="margin: 30px 0; text-align: center;">
            <p style="margin-bottom: 20px; font-weight: bold;">Please confirm your booking:</p>
            <a href="{frontend_url}/booking-confirm/{booking_id}/{confirmation_token}/accept" 
               style="display: inline-block; background-color: #22c55e; color: white; padding: 12px 30px; text-decoration: none; border-radius: 6px; margin-right: 10px; font-weight: bold;">
                ✓ ACCEPT BOOKING
            </a>
            <a href="{frontend_url}/booking-confirm/{booking_id}/{confirmation_token}/deny" 
               style="display: inline-block; background-color: #ef4444; color: white; padding: 12px 30px; text-decoration: none; border-radius: 6px; font-weight: bold;">
                ✗ DENY BOOKING
            </a>
        </div>
        
        <p style="color: #6b7280; font-size: 14px;">This is a loss transaction booking. Please review carefully before confirming.</p>
        
        <p>Best regards,<br><strong>SMIFS Private Equity System</strong></p>
    </div>
    """
    await send_email(client_email, subject, body, cc_email)
