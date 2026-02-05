"""
Email service for sending notifications with audit logging
"""
import logging
import smtplib
import random
import string
import uuid
import os
from datetime import datetime, timezone
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.application import MIMEApplication
from email import encoders
from typing import Optional, Dict, Any, List

from config import (
    EMAIL_HOST, EMAIL_PORT, EMAIL_USERNAME, EMAIL_PASSWORD, EMAIL_FROM,
    OTP_EXPIRY_MINUTES, DEFAULT_EMAIL_TEMPLATES
)


async def get_base_url() -> str:
    """
    Get the base URL for file links in emails.
    Priority:
    1. Custom domain from company_master settings
    2. FRONTEND_URL environment variable
    3. Default fallback
    """
    from database import db
    
    # First check if there's a custom domain in company_master
    try:
        company = await db.company_master.find_one(
            {"_id": "company_settings"}, 
            {"custom_domain": 1}
        )
        if company and company.get("custom_domain"):
            custom_domain = company["custom_domain"].rstrip('/')
            # Ensure it has https://
            if not custom_domain.startswith('http'):
                custom_domain = f"https://{custom_domain}"
            logging.info(f"Using custom domain from company master: {custom_domain}")
            return custom_domain
    except Exception as e:
        logging.warning(f"Error fetching custom domain from company master: {e}")
    
    # Fall back to FRONTEND_URL environment variable
    frontend_url = os.environ.get('FRONTEND_URL', '')
    if frontend_url:
        return frontend_url.rstrip('/')
    
    # Last resort default (should never happen in production)
    return 'https://privity.smifs.com'


async def get_company_info():
    """Get company master info for email branding"""
    from database import db
    try:
        company = await db.company_master.find_one({"_id": "company_settings"}, {"_id": 0})
        if company:
            return {
                "name": company.get("company_name", "SMIFS Private Equity"),
                "address": company.get("company_address", ""),
                "cin": company.get("company_cin", ""),
                "gst": company.get("company_gst", ""),
                "pan": company.get("company_pan", ""),
                "logo_url": company.get("logo_url", ""),
                "bank_name": company.get("company_bank_name", ""),
                "bank_account": company.get("company_bank_account", ""),
                "bank_ifsc": company.get("company_bank_ifsc", ""),
            }
    except Exception as e:
        logging.error(f"Error getting company info: {e}")
    
    return {
        "name": "SMIFS Private Equity",
        "address": "",
        "cin": "",
        "gst": "",
        "pan": "",
        "logo_url": "",
        "bank_name": "",
        "bank_account": "",
        "bank_ifsc": "",
    }


async def get_mapped_employee_email(client_id: str) -> Optional[str]:
    """Get the mapped employee's email for a client (for CC in communications)"""
    from database import db
    try:
        client = await db.clients.find_one({"id": client_id}, {"_id": 0, "mapped_employee_id": 1, "mapped_employee_email": 1})
        if client:
            # First check if mapped_employee_email is directly stored
            if client.get("mapped_employee_email"):
                return client["mapped_employee_email"]
            # Otherwise, fetch from users collection
            if client.get("mapped_employee_id"):
                user = await db.users.find_one({"id": client["mapped_employee_id"]}, {"_id": 0, "email": 1})
                return user.get("email") if user else None
    except Exception as e:
        logging.error(f"Error getting mapped employee email: {e}")
    return None


def wrap_email_with_branding(body: str, company_info: dict) -> str:
    """Wrap email body with company logo header and footer"""
    
    logo_html = ""
    if company_info.get("logo_url"):
        logo_html = f'''
        <div style="text-align: center; padding: 20px 0; border-bottom: 2px solid #064E3B;">
            <img src="{company_info['logo_url']}" alt="{company_info['name']}" style="max-height: 60px; max-width: 200px;" />
        </div>
        '''
    else:
        logo_html = f'''
        <div style="text-align: center; padding: 20px 0; border-bottom: 2px solid #064E3B;">
            <h1 style="color: #064E3B; margin: 0; font-size: 24px;">{company_info['name']}</h1>
        </div>
        '''
    
    # Build footer with company information
    footer_lines = []
    if company_info.get("name"):
        footer_lines.append(f"<strong>{company_info['name']}</strong>")
    if company_info.get("address"):
        footer_lines.append(company_info['address'])
    
    info_parts = []
    if company_info.get("cin"):
        info_parts.append(f"CIN: {company_info['cin']}")
    if company_info.get("gst"):
        info_parts.append(f"GST: {company_info['gst']}")
    if company_info.get("pan"):
        info_parts.append(f"PAN: {company_info['pan']}")
    
    if info_parts:
        footer_lines.append(" | ".join(info_parts))
    
    footer_content = "<br>".join(footer_lines) if footer_lines else "SMIFS Private Equity System"
    
    footer_html = f'''
    <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #e5e7eb; text-align: center; color: #6b7280; font-size: 12px;">
        {footer_content}
        <br><br>
        <span style="color: #9ca3af;">This is an automated email from the Private Equity System. Please do not reply directly to this email.</span>
    </div>
    '''
    
    wrapped_body = f'''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="margin: 0; padding: 0; background-color: #f9fafb; font-family: Arial, sans-serif;">
        <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
            {logo_html}
            <div style="padding: 30px;">
                {body}
            </div>
            {footer_html}
        </div>
    </body>
    </html>
    '''
    
    return wrapped_body


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
    
    # Try smtp_settings collection first (new format from SMTP config UI)
    config = await db.smtp_settings.find_one({}, {"_id": 0})
    
    if config and config.get("is_enabled") and config.get("smtp_password"):
        return {
            "host": config["smtp_host"],
            "port": config["smtp_port"],
            "username": config["smtp_username"],
            "password": config["smtp_password"],
            "from_email": config["smtp_from_email"],
            "from_name": config.get("smtp_from_name", "SMIFS Private Equity System"),
            "use_tls": config.get("smtp_use_tls", config.get("use_tls", True)),
            "use_ssl": config.get("smtp_use_ssl", config.get("use_ssl", False)),
            "timeout": config.get("timeout", 30)
        }
    
    # Try legacy email_config collection
    legacy_config = await db.email_config.find_one({"_id": "smtp_config"})
    
    if legacy_config and legacy_config.get("is_enabled") and legacy_config.get("smtp_password"):
        return {
            "host": legacy_config["smtp_host"],
            "port": legacy_config["smtp_port"],
            "username": legacy_config["smtp_username"],
            "password": legacy_config["smtp_password"],
            "from_email": legacy_config["smtp_from_email"],
            "from_name": legacy_config.get("smtp_from_name", "SMIFS Private Equity System"),
            "use_tls": legacy_config.get("use_tls", True),
            "use_ssl": legacy_config.get("use_ssl", False),
            "timeout": legacy_config.get("timeout", 30)
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
    related_entity_id: Optional[str] = None,
    attachments: Optional[List[Dict[str, Any]]] = None
):
    """
    Send email via SMTP with optional CC and attachments
    
    Args:
        to_email: Recipient email
        subject: Email subject
        body: HTML body
        cc_email: Optional CC email
        template_key: Template identifier for logging
        variables: Template variables for logging
        related_entity_type: Entity type for logging
        related_entity_id: Entity ID for logging
        attachments: List of attachments, each with:
            - 'filename': Name of the file
            - 'content': Bytes content of the file
            - 'content_type': MIME type (default: application/pdf)
    """
    from database import db
    
    # Check kill switch status - block all emails if system is frozen
    try:
        kill_switch = await db.system_settings.find_one({"setting": "kill_switch"}, {"_id": 0})
        if kill_switch and kill_switch.get("is_active"):
            logging.warning(f"Email blocked - Kill switch is active. Would have sent to: {to_email}")
            await log_email(
                to_email=to_email,
                subject=subject,
                template_key=template_key,
                status="skipped",
                error_message="Kill switch active - System frozen",
                cc_email=cc_email,
                variables=variables,
                related_entity_type=related_entity_type,
                related_entity_id=related_entity_id
            )
            return
    except Exception as e:
        logging.error(f"Error checking kill switch: {e}")
    
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
        # Get company info for branding
        company_info = await get_company_info()
        
        # Wrap body with company logo and footer
        branded_body = wrap_email_with_branding(body, company_info)
        
        msg = MIMEMultipart()
        from_display = f"{smtp_config['from_name']} <{smtp_config['from_email']}>"
        msg['From'] = from_display
        msg['To'] = to_email
        if cc_email:
            msg['Cc'] = cc_email
        msg['Subject'] = subject
        
        # Attach HTML body with branding
        msg.attach(MIMEText(branded_body, 'html'))
        
        # Attach files if provided
        if attachments:
            for attachment in attachments:
                filename = attachment.get('filename', 'attachment.pdf')
                content = attachment.get('content')
                content_type = attachment.get('content_type', 'application/pdf')
                
                if content:
                    # Create attachment part
                    part = MIMEApplication(content, Name=filename)
                    part['Content-Disposition'] = f'attachment; filename="{filename}"'
                    msg.attach(part)
        
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
        
        logging.info(f"Email sent successfully to {to_email}" + (f" with {len(attachments)} attachment(s)" if attachments else ""))
        
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


async def send_payment_request_email(
    booking_id: str,
    client: dict,
    stock: dict,
    booking: dict,
    company_master: dict,
    approved_by: str,
    cc_email: Optional[str] = None
):
    """
    Send payment request email to client when booking is approved.
    Includes bank details from company master and attaches company documents.
    
    Args:
        booking_id: Booking ID
        client: Client document
        stock: Stock document
        booking: Booking document
        company_master: Company master document with bank details and document URLs
        approved_by: Name of the user who approved
        cc_email: Optional CC email (usually the booking creator)
    """
    import aiohttp
    import aiofiles
    
    client_name = client.get("name", "Valued Client")
    client_email = client.get("email")
    
    if not client_email:
        logging.warning(f"Cannot send payment request - no email for client {client.get('id')}")
        return
    
    # Calculate payment details - use selling_price for client payment
    quantity = booking.get("quantity", 0)
    selling_price = booking.get("selling_price") or booking.get("buying_price", 0)
    total_amount = quantity * selling_price
    booking_number = booking.get("booking_number", booking_id[:8].upper())
    
    # Get bank details from company master
    company_name = company_master.get("company_name", "SMIFS Capital Markets Ltd")
    bank_name = company_master.get("company_bank_name", "")
    bank_account = company_master.get("company_bank_account", "")
    bank_ifsc = company_master.get("company_bank_ifsc", "")
    bank_branch = company_master.get("company_bank_branch", "")
    company_pan = company_master.get("company_pan", "")
    
    # Get document URLs
    nsdl_cml_url = company_master.get("cml_nsdl_url")
    cdsl_cml_url = company_master.get("cml_cdsl_url")
    pan_card_url = company_master.get("pan_card_url")
    cancelled_cheque_url = company_master.get("cancelled_cheque_url")
    
    # Build attachments list
    attachments = []
    
    async def load_document(url: str, filename: str) -> Optional[dict]:
        """Load document from URL, local path, or GridFS"""
        if not url:
            return None
        try:
            # Check if it's a GridFS file URL (stored in MongoDB)
            if url.startswith("/api/files/"):
                from services.file_storage import get_file_from_gridfs
                file_id = url.split("/api/files/")[-1]
                file_data = await get_file_from_gridfs(file_id)
                if file_data:
                    return {
                        'filename': filename,
                        'content': file_data['content'],
                        'content_type': file_data.get('content_type', 'application/octet-stream')
                    }
            # Check if it's a local file path
            elif url.startswith("/uploads/"):
                local_path = f"/app{url}"
                if os.path.exists(local_path):
                    async with aiofiles.open(local_path, 'rb') as f:
                        content = await f.read()
                    # Determine content type based on file extension
                    ext = url.split('.')[-1].lower() if '.' in url else ''
                    if ext in ['pdf']:
                        content_type = 'application/pdf'
                    elif ext in ['png']:
                        content_type = 'image/png'
                    elif ext in ['jpg', 'jpeg']:
                        content_type = 'image/jpeg'
                    else:
                        content_type = 'application/octet-stream'
                    return {
                        'filename': filename,
                        'content': content,
                        'content_type': content_type
                    }
            # Handle external URLs
            elif url.startswith("http"):
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as response:
                        if response.status == 200:
                            content = await response.read()
                            return {
                                'filename': filename,
                                'content': content,
                                'content_type': 'application/pdf'
                            }
        except Exception as e:
            logging.error(f"Failed to load document {url}: {e}")
        return None
    
    # Load company documents as attachments
    if nsdl_cml_url:
        ext = nsdl_cml_url.split('.')[-1].lower() if '.' in nsdl_cml_url else 'pdf'
        doc = await load_document(nsdl_cml_url, f"NSDL_CML.{ext}")
        if doc:
            attachments.append(doc)
    
    if cdsl_cml_url:
        ext = cdsl_cml_url.split('.')[-1].lower() if '.' in cdsl_cml_url else 'pdf'
        doc = await load_document(cdsl_cml_url, f"CDSL_CML.{ext}")
        if doc:
            attachments.append(doc)
    
    if pan_card_url:
        ext = pan_card_url.split('.')[-1].lower() if '.' in pan_card_url else 'pdf'
        doc = await load_document(pan_card_url, f"Company_PAN_Card.{ext}")
        if doc:
            attachments.append(doc)
    
    if cancelled_cheque_url:
        ext = cancelled_cheque_url.split('.')[-1].lower() if '.' in cancelled_cheque_url else 'pdf'
        doc = await load_document(cancelled_cheque_url, f"Cancelled_Cheque.{ext}")
        if doc:
            attachments.append(doc)
    
    # Also attach client documents (CML, PAN, Cancelled Cheque)
    client_documents = client.get("documents", [])
    for doc_info in client_documents:
        doc_type = doc_info.get("doc_type")
        doc_url = doc_info.get("url") or doc_info.get("file_url")
        if doc_url and doc_type in ["cml_copy", "pan_card", "cancelled_cheque"]:
            ext = doc_url.split('.')[-1].lower() if '.' in doc_url else 'pdf'
            doc_name = f"Client_{doc_type.upper().replace('_', ' ')}.{ext}"
            doc = await load_document(doc_url, doc_name)
            if doc:
                attachments.append(doc)
                logging.info(f"Attached client document: {doc_name}")
    
    # Log attachment details
    if attachments:
        logging.info(f"Payment request email will have {len(attachments)} attachment(s): {[a['filename'] for a in attachments]}")
    else:
        logging.warning("No company master documents found to attach to payment request email")
    
    # Get base URL for document links (from system config or environment)
    frontend_url = await get_base_url()
    
    # Build document links section
    doc_links = []
    if nsdl_cml_url:
        full_url = f"{frontend_url}{nsdl_cml_url}" if nsdl_cml_url.startswith('/') else nsdl_cml_url
        doc_links.append(f'<a href="{full_url}" style="color: #2563eb; text-decoration: none; margin-right: 15px;">📄 NSDL CML</a>')
    if cdsl_cml_url:
        full_url = f"{frontend_url}{cdsl_cml_url}" if cdsl_cml_url.startswith('/') else cdsl_cml_url
        doc_links.append(f'<a href="{full_url}" style="color: #2563eb; text-decoration: none; margin-right: 15px;">📄 CDSL CML</a>')
    if pan_card_url:
        full_url = f"{frontend_url}{pan_card_url}" if pan_card_url.startswith('/') else pan_card_url
        doc_links.append(f'<a href="{full_url}" style="color: #2563eb; text-decoration: none; margin-right: 15px;">📄 PAN Card</a>')
    if cancelled_cheque_url:
        full_url = f"{frontend_url}{cancelled_cheque_url}" if cancelled_cheque_url.startswith('/') else cancelled_cheque_url
        doc_links.append(f'<a href="{full_url}" style="color: #2563eb; text-decoration: none; margin-right: 15px;">📄 Cancelled Cheque</a>')
    
    documents_html = ""
    if doc_links:
        documents_html = f"""
            <!-- Company Documents -->
            <div style="background: #f0f9ff; border-radius: 12px; padding: 20px; margin: 25px 0; border: 1px solid #bae6fd;">
                <h3 style="color: #0369a1; margin: 0 0 15px 0; font-size: 16px; border-bottom: 2px solid #0ea5e9; padding-bottom: 10px;">
                    📎 Company Documents (Click to Download)
                </h3>
                <div style="display: flex; flex-wrap: wrap; gap: 10px;">
                    {''.join(doc_links)}
                </div>
                <p style="color: #6b7280; font-size: 12px; margin-top: 15px; margin-bottom: 0;">
                    <em>Documents are also attached to this email for your convenience.</em>
                </p>
            </div>
        """
    
    # Build email subject
    subject = f"Payment Request - Booking {booking_number} | {stock.get('symbol', 'N/A')}"
    
    # Build email body
    body = f"""
    <div style="font-family: Arial, sans-serif; max-width: 700px; margin: 0 auto; background: #ffffff;">
        <!-- Header -->
        <div style="background: linear-gradient(135deg, #10b981, #059669); padding: 25px; text-align: center;">
            <h1 style="color: white; margin: 0; font-size: 24px;">Payment Request</h1>
            <p style="color: #d1fae5; margin: 10px 0 0 0; font-size: 14px;">Booking Reference: {booking_number}</p>
        </div>
        
        <!-- Content -->
        <div style="padding: 30px;">
            <p style="font-size: 16px; color: #374151;">Dear <strong>{client_name}</strong>,</p>
            
            <p style="color: #4b5563; line-height: 1.6;">
                Your booking has been approved by our PE Desk. Please find below the payment details for completing your investment.
            </p>
            
            <!-- Booking Summary -->
            <div style="background: #f9fafb; border-radius: 12px; padding: 20px; margin: 25px 0; border: 1px solid #e5e7eb;">
                <h3 style="color: #111827; margin: 0 0 15px 0; font-size: 16px; border-bottom: 2px solid #10b981; padding-bottom: 10px;">
                    📋 Booking Summary
                </h3>
                <table style="width: 100%; border-collapse: collapse;">
                    <tr>
                        <td style="padding: 10px 0; color: #6b7280; width: 40%;">Stock:</td>
                        <td style="padding: 10px 0; color: #111827; font-weight: 600;">{stock.get('symbol', 'N/A')} - {stock.get('name', '')}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px 0; color: #6b7280;">Quantity:</td>
                        <td style="padding: 10px 0; color: #111827; font-weight: 600;">{quantity:,} shares</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px 0; color: #6b7280;">Sell Price per Share:</td>
                        <td style="padding: 10px 0; color: #111827; font-weight: 600;">₹ {selling_price:,.2f}</td>
                    </tr>
                    <tr style="background: #ecfdf5;">
                        <td style="padding: 15px 10px; color: #065f46; font-weight: bold; font-size: 18px;">Total Amount Payable:</td>
                        <td style="padding: 15px 10px; color: #065f46; font-weight: bold; font-size: 22px;">₹ {total_amount:,.2f}</td>
                    </tr>
                </table>
            </div>
            
            <!-- Bank Details -->
            <div style="background: #eff6ff; border-radius: 12px; padding: 20px; margin: 25px 0; border: 1px solid #bfdbfe;">
                <h3 style="color: #1e40af; margin: 0 0 15px 0; font-size: 16px; border-bottom: 2px solid #3b82f6; padding-bottom: 10px;">
                    🏦 Bank Account Details for Payment
                </h3>
                <table style="width: 100%; border-collapse: collapse;">
                    <tr>
                        <td style="padding: 10px 0; color: #6b7280; width: 40%;">Beneficiary Name:</td>
                        <td style="padding: 10px 0; color: #111827; font-weight: 600;">{company_name}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px 0; color: #6b7280;">Bank Name:</td>
                        <td style="padding: 10px 0; color: #111827; font-weight: 600;">{bank_name or 'Please contact PE Desk'}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px 0; color: #6b7280;">Account Number:</td>
                        <td style="padding: 10px 0; color: #111827; font-weight: 600; font-family: monospace; font-size: 16px;">{bank_account or 'Please contact PE Desk'}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px 0; color: #6b7280;">IFSC Code:</td>
                        <td style="padding: 10px 0; color: #111827; font-weight: 600; font-family: monospace;">{bank_ifsc or 'Please contact PE Desk'}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px 0; color: #6b7280;">Branch:</td>
                        <td style="padding: 10px 0; color: #111827;">{bank_branch or '-'}</td>
                    </tr>
                </table>
            </div>
            
            {documents_html}
            
            <!-- Important Notes -->
            <div style="background: #fef3c7; border-radius: 12px; padding: 20px; margin: 25px 0; border: 1px solid #fcd34d;">
                <h3 style="color: #92400e; margin: 0 0 10px 0; font-size: 14px;">⚠️ Important Notes:</h3>
                <ul style="color: #78350f; margin: 0; padding-left: 20px; line-height: 1.8;">
                    <li>Please mention your <strong>Booking Reference ({booking_number})</strong> in the payment remarks</li>
                    <li>After making the payment, please share the payment confirmation with your relationship manager</li>
                    <li>Stock transfer will be initiated within 2-3 business days after payment confirmation</li>
                </ul>
            </div>
            
            <!-- Approved By -->
            <p style="color: #6b7280; font-size: 14px; margin-top: 30px;">
                <em>Approved by: {approved_by}</em><br>
                <em>Date: {datetime.now(timezone.utc).strftime('%d %B %Y, %I:%M %p')} UTC</em>
            </p>
            
            <p style="color: #4b5563; margin-top: 25px;">
                For any queries, please contact your relationship manager or reach out to our PE Desk.
            </p>
            
            <p style="color: #374151; margin-top: 20px;">
                Best regards,<br>
                <strong>{company_name}</strong><br>
                <span style="color: #6b7280; font-size: 14px;">Private Equity Division</span>
            </p>
        </div>
        
        <!-- Footer -->
        <div style="background: #f3f4f6; padding: 20px; text-align: center; border-top: 1px solid #e5e7eb;">
            <p style="color: #9ca3af; font-size: 12px; margin: 0;">
                This is an automated message from the Private Equity System.<br>
                Company PAN: {company_pan or 'N/A'}
            </p>
        </div>
    </div>
    """
    
    # Get additional client emails
    additional_emails = []
    if client.get("secondary_email"):
        additional_emails.append(client["secondary_email"])
    if client.get("tertiary_email"):
        additional_emails.append(client["tertiary_email"])
    
    # Send primary email with attachments
    await send_email(
        client_email,
        subject,
        body,
        cc_email=cc_email,
        template_key="payment_request",
        variables={
            "booking_number": booking_number,
            "client_name": client_name,
            "stock_symbol": stock.get("symbol"),
            "total_amount": total_amount
        },
        related_entity_type="booking",
        related_entity_id=booking_id,
        attachments=attachments if attachments else None
    )
    
    # Send to additional client emails (without attachments to save bandwidth)
    for email in additional_emails:
        if email and email != client_email:
            await send_email(
                email,
                subject,
                body,
                template_key="payment_request",
                variables={
                    "booking_number": booking_number,
                    "client_name": client_name,
                    "stock_symbol": stock.get("symbol"),
                    "total_amount": total_amount
                },
                related_entity_type="booking",
                related_entity_id=booking_id
            )
    
    logging.info(f"Payment request email sent for booking {booking_number} to {client_email}")
    
    # Send WhatsApp notification if configured
    await send_payment_whatsapp_notification(
        client=client,
        booking=booking,
        stock=stock,
        company_master=company_master
    )


async def send_payment_whatsapp_notification(
    client: dict,
    booking: dict,
    stock: dict,
    company_master: dict
):
    """
    Send payment request notification via WhatsApp using Wati.io API
    """
    from database import db
    
    try:
        # Check if WhatsApp is configured
        wa_config = await db.system_config.find_one({"config_type": "whatsapp"}, {"_id": 0})
        if not wa_config or not wa_config.get("enabled"):
            logging.info("WhatsApp not enabled - skipping payment notification")
            return
        
        # Get client mobile number
        client_mobile = client.get("mobile") or client.get("phone")
        if not client_mobile:
            logging.warning(f"No mobile number for client {client.get('name')} - skipping WhatsApp")
            return
        
        # Format details
        booking_number = booking.get("booking_number", "N/A")
        client_name = client.get("name", "Client")
        stock_symbol = stock.get("symbol", "N/A") if stock else "N/A"
        quantity = booking.get("quantity", 0)
        selling_price = booking.get("selling_price", 0)
        total_amount = quantity * selling_price
        
        # Bank details from company master
        bank_name = company_master.get("company_bank_name", "N/A")
        account_number = company_master.get("company_bank_account", "N/A")
        ifsc_code = company_master.get("company_bank_ifsc", "N/A")
        
        # Create WhatsApp message
        message = f"""📢 *Payment Request - Booking #{booking_number}*

Dear {client_name},

Your booking for *{quantity} shares* of *{stock_symbol}* has been approved!

💰 *Payment Details:*
• Total Amount: ₹{total_amount:,.2f}
• Price per Share: ₹{selling_price:,.2f}

🏦 *Bank Details:*
• Bank: {bank_name}
• A/C No: {account_number}
• IFSC: {ifsc_code}

Please complete the payment and share the proof via email for faster processing.

Thank you for choosing SMIFS Private Equity! 🙏"""
        
        # Send via Wati API
        from routers.whatsapp import get_wati_service
        service = await get_wati_service()
        if service:
            await service.send_session_message(client_mobile, message)
            logging.info(f"WhatsApp payment notification sent to {client_mobile} for booking {booking_number}")
        else:
            logging.warning("Wati service not available - WhatsApp notification not sent")
            
    except Exception as e:
        logging.error(f"Failed to send WhatsApp payment notification: {e}")


async def send_stock_transfer_request_email(
    purchase_id: str,
    vendor: dict,
    purchase: dict,
    stock: dict,
    total_paid: float,
    payment_date: str,
    company_master: dict,
    cc_email: Optional[str] = None
):
    """
    Send stock transfer request email to vendor when full payment is completed.
    Includes payment details and attaches all company documents.
    
    Args:
        purchase_id: Purchase ID
        vendor: Vendor document (from clients collection with is_vendor=True)
        purchase: Purchase document
        stock: Stock document
        total_paid: Total amount paid to vendor
        payment_date: Date of final payment
        company_master: Company master document with documents
        cc_email: Optional CC email
    """
    import aiohttp
    import aiofiles
    
    vendor_name = vendor.get("name", "Valued Vendor")
    vendor_email = vendor.get("email")
    
    if not vendor_email:
        logging.warning(f"Cannot send stock transfer request - no email for vendor {vendor.get('id')}")
        return
    
    purchase_number = purchase.get("purchase_number", purchase_id[:8].upper())
    quantity = purchase.get("quantity", 0)
    stock_symbol = stock.get("symbol", "N/A") if stock else purchase.get("stock_symbol", "N/A")
    stock_name = stock.get("name", "") if stock else ""
    
    # Get company details
    company_name = company_master.get("company_name", "SMIFS Capital Markets Ltd")
    cdsl_dp_id = company_master.get("cdsl_dp_id", "")
    nsdl_dp_id = company_master.get("nsdl_dp_id", "")
    
    # Get document URLs
    nsdl_cml_url = company_master.get("cml_nsdl_url")
    cdsl_cml_url = company_master.get("cml_cdsl_url")
    pan_card_url = company_master.get("pan_card_url")
    cancelled_cheque_url = company_master.get("cancelled_cheque_url")
    logo_url = company_master.get("logo_url")
    
    # Build attachments list
    attachments = []
    
    async def load_document(url: str, filename: str) -> Optional[dict]:
        """Load document from URL or local path"""
        if not url:
            return None
        try:
            if url.startswith("/uploads/"):
                local_path = f"/app{url}"
                if os.path.exists(local_path):
                    async with aiofiles.open(local_path, 'rb') as f:
                        content = await f.read()
                    ext = url.split('.')[-1].lower() if '.' in url else 'pdf'
                    content_type = 'application/pdf' if ext == 'pdf' else f'image/{ext}'
                    return {
                        'filename': filename,
                        'content': content,
                        'content_type': content_type
                    }
            elif url.startswith("http"):
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as response:
                        if response.status == 200:
                            content = await response.read()
                            return {
                                'filename': filename,
                                'content': content,
                                'content_type': 'application/pdf'
                            }
        except Exception as e:
            logging.error(f"Failed to load document {url}: {e}")
        return None
    
    # Load all company documents as attachments
    if nsdl_cml_url:
        doc = await load_document(nsdl_cml_url, "NSDL_CML.pdf")
        if doc:
            attachments.append(doc)
    
    if cdsl_cml_url:
        doc = await load_document(cdsl_cml_url, "CDSL_CML.pdf")
        if doc:
            attachments.append(doc)
    
    if pan_card_url:
        ext = pan_card_url.split('.')[-1].lower() if '.' in pan_card_url else 'pdf'
        doc = await load_document(pan_card_url, f"Company_PAN_Card.{ext}")
        if doc:
            attachments.append(doc)
    
    if cancelled_cheque_url:
        ext = cancelled_cheque_url.split('.')[-1].lower() if '.' in cancelled_cheque_url else 'pdf'
        doc = await load_document(cancelled_cheque_url, f"Cancelled_Cheque.{ext}")
        if doc:
            attachments.append(doc)
    
    # Format payment date
    try:
        payment_dt = datetime.fromisoformat(payment_date.replace('Z', '+00:00'))
        formatted_date = payment_dt.strftime('%d %B %Y')
        formatted_time = payment_dt.strftime('%I:%M %p UTC')
    except:
        formatted_date = payment_date
        formatted_time = ""
    
    # Build email subject
    subject = f"Stock Transfer Request - {stock_symbol} | {purchase_number}"
    
    # Build email body
    body = f"""
    <div style="font-family: Arial, sans-serif; max-width: 700px; margin: 0 auto; background: #ffffff;">
        <!-- Header -->
        <div style="background: linear-gradient(135deg, #3b82f6, #1d4ed8); padding: 25px; text-align: center;">
            <h1 style="color: white; margin: 0; font-size: 24px;">Stock Transfer Request</h1>
            <p style="color: #bfdbfe; margin: 10px 0 0 0; font-size: 14px;">Purchase Reference: {purchase_number}</p>
        </div>
        
        <!-- Content -->
        <div style="padding: 30px;">
            <p style="font-size: 16px; color: #374151;">Dear <strong>{vendor_name}</strong>,</p>
            
            <p style="color: #4b5563; line-height: 1.6;">
                We are pleased to inform you that the <strong>full payment</strong> for your stock purchase order has been completed. 
                We kindly request you to <strong>initiate the stock transfer immediately</strong>.
            </p>
            
            <!-- Payment Confirmation -->
            <div style="background: #ecfdf5; border-radius: 12px; padding: 20px; margin: 25px 0; border: 2px solid #10b981;">
                <h3 style="color: #065f46; margin: 0 0 15px 0; font-size: 16px;">
                    ✓ Payment Confirmation
                </h3>
                <table style="width: 100%; border-collapse: collapse;">
                    <tr>
                        <td style="padding: 10px 0; color: #6b7280; width: 40%;">Total Amount Paid:</td>
                        <td style="padding: 10px 0; color: #065f46; font-weight: bold; font-size: 20px;">₹ {total_paid:,.2f}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px 0; color: #6b7280;">Payment Date:</td>
                        <td style="padding: 10px 0; color: #111827; font-weight: 600;">{formatted_date}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px 0; color: #6b7280;">Payment Time:</td>
                        <td style="padding: 10px 0; color: #111827;">{formatted_time}</td>
                    </tr>
                </table>
            </div>
            
            <!-- Stock Details -->
            <div style="background: #f9fafb; border-radius: 12px; padding: 20px; margin: 25px 0; border: 1px solid #e5e7eb;">
                <h3 style="color: #111827; margin: 0 0 15px 0; font-size: 16px; border-bottom: 2px solid #3b82f6; padding-bottom: 10px;">
                    📋 Stock Transfer Details
                </h3>
                <table style="width: 100%; border-collapse: collapse;">
                    <tr>
                        <td style="padding: 10px 0; color: #6b7280; width: 40%;">Stock:</td>
                        <td style="padding: 10px 0; color: #111827; font-weight: 600;">{stock_symbol} - {stock_name}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px 0; color: #6b7280;">Quantity to Transfer:</td>
                        <td style="padding: 10px 0; color: #111827; font-weight: 600; font-size: 18px;">{quantity:,} shares</td>
                    </tr>
                </table>
            </div>
            
            <!-- DP Details -->
            <div style="background: #eff6ff; border-radius: 12px; padding: 20px; margin: 25px 0; border: 1px solid #bfdbfe;">
                <h3 style="color: #1e40af; margin: 0 0 15px 0; font-size: 16px; border-bottom: 2px solid #3b82f6; padding-bottom: 10px;">
                    🏦 Transfer To (Our DP Details)
                </h3>
                <table style="width: 100%; border-collapse: collapse;">
                    <tr>
                        <td style="padding: 10px 0; color: #6b7280; width: 40%;">Beneficiary:</td>
                        <td style="padding: 10px 0; color: #111827; font-weight: 600;">{company_name}</td>
                    </tr>
                    {f'''<tr>
                        <td style="padding: 10px 0; color: #6b7280;">CDSL DP ID:</td>
                        <td style="padding: 10px 0; color: #111827; font-weight: 600; font-family: monospace;">{cdsl_dp_id}</td>
                    </tr>''' if cdsl_dp_id else ''}
                    {f'''<tr>
                        <td style="padding: 10px 0; color: #6b7280;">NSDL DP ID:</td>
                        <td style="padding: 10px 0; color: #111827; font-weight: 600; font-family: monospace;">{nsdl_dp_id}</td>
                    </tr>''' if nsdl_dp_id else ''}
                </table>
            </div>
            
            <!-- Urgent Notice -->
            <div style="background: #fef2f2; border-radius: 12px; padding: 20px; margin: 25px 0; border: 2px solid #ef4444;">
                <h3 style="color: #991b1b; margin: 0 0 10px 0; font-size: 16px;">⚠️ Immediate Action Required</h3>
                <p style="color: #7f1d1d; margin: 0; line-height: 1.6;">
                    As the full payment has been completed, we kindly request you to <strong>initiate the stock transfer immediately</strong>. 
                    Please use the DP details provided above and ensure the transfer is completed at the earliest.
                </p>
            </div>
            
            <!-- Attachments Note -->
            <div style="background: #fefce8; border-radius: 12px; padding: 15px; margin: 25px 0; border: 1px solid #fcd34d;">
                <p style="color: #854d0e; margin: 0; font-size: 14px;">
                    <strong>📎 Attached Documents:</strong> NSDL CML, CDSL CML, Company PAN Card, and Cancelled Cheque for your reference.
                </p>
            </div>
            
            <p style="color: #4b5563; margin-top: 25px;">
                For any queries or assistance with the transfer, please contact our PE Desk.
            </p>
            
            <p style="color: #374151; margin-top: 20px;">
                Best regards,<br>
                <strong>{company_name}</strong><br>
                <span style="color: #6b7280; font-size: 14px;">Private Equity Division</span>
            </p>
        </div>
        
        <!-- Footer -->
        <div style="background: #f3f4f6; padding: 20px; text-align: center; border-top: 1px solid #e5e7eb;">
            <p style="color: #9ca3af; font-size: 12px; margin: 0;">
                This is an automated message from the Private Equity System.
            </p>
        </div>
    </div>
    """
    
    # Get additional vendor emails
    additional_emails = []
    if vendor.get("secondary_email"):
        additional_emails.append(vendor["secondary_email"])
    if vendor.get("tertiary_email"):
        additional_emails.append(vendor["tertiary_email"])
    
    # Send primary email with attachments
    await send_email(
        vendor_email,
        subject,
        body,
        cc_email=cc_email,
        template_key="stock_transfer_request",
        variables={
            "purchase_number": purchase_number,
            "vendor_name": vendor_name,
            "stock_symbol": stock_symbol,
            "total_paid": total_paid,
            "quantity": quantity
        },
        related_entity_type="purchase",
        related_entity_id=purchase_id,
        attachments=attachments if attachments else None
    )
    
    # Send to additional vendor emails (without attachments)
    for email in additional_emails:
        if email and email != vendor_email:
            await send_email(
                email,
                subject,
                body,
                template_key="stock_transfer_request",
                variables={
                    "purchase_number": purchase_number,
                    "vendor_name": vendor_name,
                    "stock_symbol": stock_symbol,
                    "total_paid": total_paid,
                    "quantity": quantity
                },
                related_entity_type="purchase",
                related_entity_id=purchase_id
            )
    
    logging.info(f"Stock transfer request email sent for purchase {purchase_number} to {vendor_email}")


async def send_dp_ready_email(
    client: dict,
    booking: dict,
    stock: dict,
    company_master: dict,
    cc_email: Optional[str] = None
):
    """
    Send DP Ready notification email to client when full payment is received.
    Informs them that their shares are ready for transfer.
    
    Args:
        client: Client document
        booking: Booking document
        stock: Stock document
        company_master: Company master document
        cc_email: Optional CC email
    """
    client_name = client.get("name", "Valued Client")
    client_email = client.get("email")
    
    if not client_email:
        logging.warning(f"Cannot send DP Ready email - no email for client {client.get('id')}")
        return
    
    booking_number = booking.get("booking_number", "N/A")
    stock_symbol = stock.get("symbol", "N/A") if stock else "N/A"
    stock_name = stock.get("name", "N/A") if stock else "N/A"
    quantity = booking.get("quantity", 0)
    
    # Get company info for email template
    company_info = await get_company_info()
    
    # Get base URL for links
    base_url = await get_base_url()
    
    subject = f"✅ Payment Received - Shares Ready for Transfer | Booking #{booking_number}"
    
    body = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="background: linear-gradient(135deg, #10b981, #059669); padding: 30px; border-radius: 10px 10px 0 0; text-align: center;">
            <h1 style="color: white; margin: 0; font-size: 24px;">Payment Confirmed!</h1>
            <p style="color: #d1fae5; margin: 10px 0 0 0;">Your shares are ready for transfer</p>
        </div>
        
        <div style="background: white; padding: 30px; border: 1px solid #e5e7eb; border-top: none;">
            <p style="color: #374151;">Dear <strong>{client_name}</strong>,</p>
            
            <p style="color: #374151; line-height: 1.6;">
                We are pleased to confirm that we have received your complete payment for booking 
                <strong>#{booking_number}</strong>. Your shares are now ready for transfer to your demat account.
            </p>
            
            <div style="background: #f3f4f6; padding: 20px; border-radius: 8px; margin: 20px 0;">
                <h3 style="color: #059669; margin: 0 0 15px 0;">📋 Transfer Details</h3>
                <table style="width: 100%; border-collapse: collapse;">
                    <tr>
                        <td style="padding: 8px 0; color: #6b7280;">Stock:</td>
                        <td style="padding: 8px 0; color: #111827; font-weight: 500;">{stock_symbol} - {stock_name}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; color: #6b7280;">Quantity:</td>
                        <td style="padding: 8px 0; color: #111827; font-weight: 500;">{quantity:,} shares</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; color: #6b7280;">Status:</td>
                        <td style="padding: 8px 0; color: #059669; font-weight: 600;">✅ Ready for Transfer</td>
                    </tr>
                </table>
            </div>
            
            <div style="background: #fffbeb; border-left: 4px solid #f59e0b; padding: 15px; margin: 20px 0;">
                <p style="color: #92400e; margin: 0; font-size: 14px;">
                    <strong>What's Next?</strong><br>
                    Our team will initiate the DP transfer shortly. The shares will reflect in your demat account 
                    within T+2 working days after transfer. You will receive a confirmation email once the transfer is complete.
                </p>
            </div>
            
            <p style="color: #374151; line-height: 1.6;">
                Thank you for your trust in SMIFS Private Equity. If you have any questions, 
                please don't hesitate to contact us.
            </p>
        </div>
        
        <div style="background: #f9fafb; padding: 20px; border-radius: 0 0 10px 10px; border: 1px solid #e5e7eb; border-top: none; text-align: center;">
            <p style="color: #6b7280; margin: 0; font-size: 12px;">
                {company_info.get('name', 'SMIFS Private Equity')}<br>
                {company_info.get('address', '')}
            </p>
        </div>
    </div>
    """
    
    # Wrap with company logo header
    body = wrap_email_with_logo(body, company_info)
    
    # Send email
    await send_email(
        to_email=client_email,
        subject=subject,
        body=body,
        cc_emails=[cc_email] if cc_email else None
    )
    
    # Send WhatsApp notification
    try:
        await send_dp_ready_whatsapp(client, booking, stock)
    except Exception as e:
        logging.error(f"Failed to send DP Ready WhatsApp: {e}")
    
    logging.info(f"DP Ready email sent for booking {booking_number} to {client_email}")


async def send_dp_ready_whatsapp(client: dict, booking: dict, stock: dict):
    """Send DP Ready notification via WhatsApp"""
    from database import db
    
    try:
        wa_config = await db.system_config.find_one({"config_type": "whatsapp"}, {"_id": 0})
        if not wa_config or not wa_config.get("enabled"):
            return
        
        client_mobile = client.get("mobile") or client.get("phone")
        if not client_mobile:
            return
        
        booking_number = booking.get("booking_number", "N/A")
        stock_symbol = stock.get("symbol", "N/A") if stock else "N/A"
        quantity = booking.get("quantity", 0)
        
        message = f"""✅ *Payment Confirmed - Booking #{booking_number}*

Dear {client.get('name', 'Client')},

Your payment has been received successfully!

📋 *Transfer Details:*
• Stock: {stock_symbol}
• Quantity: {quantity:,} shares
• Status: Ready for Transfer

Our team will initiate the DP transfer shortly. You will receive a confirmation once complete.

Thank you for choosing SMIFS Private Equity! 🙏"""
        
        from routers.whatsapp import get_wati_service
        service = await get_wati_service()
        if service:
            await service.send_session_message(client_mobile, message)
            logging.info(f"DP Ready WhatsApp sent to {client_mobile}")
    except Exception as e:
        logging.error(f"DP Ready WhatsApp failed: {e}")


async def send_stock_transferred_email(
    booking_id: str,
    client: dict,
    booking: dict,
    stock: dict,
    dp_type: str,
    transfer_date: str,
    company_master: dict,
    cc_email: Optional[str] = None
):
    """
    Send stock transfer notification email to client.
    Informs them that stock has been transferred and will show in T+2 days.
    
    Args:
        booking_id: Booking ID
        client: Client document
        booking: Booking document
        stock: Stock document
        dp_type: "NSDL" or "CDSL"
        transfer_date: Date of transfer
        company_master: Company master document
        cc_email: Optional CC email
    """
    client_name = client.get("name", "Valued Client")
    client_email = client.get("email")
    
    if not client_email:
        logging.warning(f"Cannot send transfer notification - no email for client {client.get('id')}")
        return
    
    booking_number = booking.get("booking_number", booking_id[:8].upper())
    quantity = booking.get("quantity", 0)
    stock_symbol = stock.get("symbol", "N/A")
    stock_name = stock.get("name", "")
    client_otc_ucc = client.get("otc_ucc", "")
    
    # Get company details
    company_name = company_master.get("company_name", "SMIFS Capital Markets Ltd")
    
    # Format transfer date
    try:
        transfer_dt = datetime.fromisoformat(transfer_date.replace('Z', '+00:00'))
        formatted_date = transfer_dt.strftime('%d %B %Y')
        formatted_time = transfer_dt.strftime('%I:%M %p UTC')
        # Calculate T+2 date (excluding weekends)
        t2_date = transfer_dt
        days_added = 0
        while days_added < 2:
            t2_date += timedelta(days=1)
            if t2_date.weekday() < 5:  # Monday = 0, Friday = 4
                days_added += 1
        formatted_t2_date = t2_date.strftime('%d %B %Y')
    except:
        formatted_date = transfer_date
        formatted_time = ""
        formatted_t2_date = "within 2 business days"
    
    # Build email subject
    subject = f"Stock Transfer Completed - {stock_symbol} | Booking {booking_number}"
    
    # Build email body
    body = f"""
    <div style="font-family: Arial, sans-serif; max-width: 700px; margin: 0 auto; background: #ffffff;">
        <!-- Header -->
        <div style="background: linear-gradient(135deg, #10b981, #059669); padding: 25px; text-align: center;">
            <h1 style="color: white; margin: 0; font-size: 24px;">Stock Transfer Completed</h1>
            <p style="color: #d1fae5; margin: 10px 0 0 0; font-size: 14px;">Booking Reference: {booking_number}</p>
        </div>
        
        <!-- Content -->
        <div style="padding: 30px;">
            <p style="font-size: 16px; color: #374151;">Dear <strong>{client_name}</strong>,</p>
            
            <p style="color: #4b5563; line-height: 1.6;">
                We are pleased to inform you that your stock transfer has been <strong>successfully completed</strong>. 
                The shares have been transferred to your demat account.
            </p>
            
            <!-- Success Banner -->
            <div style="background: #ecfdf5; border-radius: 12px; padding: 20px; margin: 25px 0; border: 2px solid #10b981; text-align: center;">
                <div style="font-size: 48px; margin-bottom: 10px;">✓</div>
                <h2 style="color: #065f46; margin: 0 0 10px 0;">Transfer Successful</h2>
                <p style="color: #047857; margin: 0; font-size: 14px;">
                    Your shares will reflect in your demat account by <strong>{formatted_t2_date}</strong> (T+2 settlement)
                </p>
            </div>
            
            <!-- Transfer Details -->
            <div style="background: #f9fafb; border-radius: 12px; padding: 20px; margin: 25px 0; border: 1px solid #e5e7eb;">
                <h3 style="color: #111827; margin: 0 0 15px 0; font-size: 16px; border-bottom: 2px solid #10b981; padding-bottom: 10px;">
                    📋 Transfer Details
                </h3>
                <table style="width: 100%; border-collapse: collapse;">
                    <tr>
                        <td style="padding: 10px 0; color: #6b7280; width: 40%;">Stock:</td>
                        <td style="padding: 10px 0; color: #111827; font-weight: 600;">{stock_symbol} - {stock_name}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px 0; color: #6b7280;">Quantity Transferred:</td>
                        <td style="padding: 10px 0; color: #111827; font-weight: 600; font-size: 18px;">{quantity:,} shares</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px 0; color: #6b7280;">Transfer Mode:</td>
                        <td style="padding: 10px 0;">
                            <span style="background: {'#dbeafe' if dp_type == 'NSDL' else '#ede9fe'}; color: {'#1e40af' if dp_type == 'NSDL' else '#6d28d9'}; padding: 4px 12px; border-radius: 20px; font-weight: 600; font-size: 14px;">
                                {dp_type}
                            </span>
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 10px 0; color: #6b7280;">Transfer Date:</td>
                        <td style="padding: 10px 0; color: #111827;">{formatted_date} at {formatted_time}</td>
                    </tr>
                    {f'''<tr>
                        <td style="padding: 10px 0; color: #6b7280;">Your Demat Account:</td>
                        <td style="padding: 10px 0; color: #111827; font-family: monospace;">{client_otc_ucc}</td>
                    </tr>''' if client_otc_ucc else ''}
                </table>
            </div>
            
            <!-- Settlement Info -->
            <div style="background: #eff6ff; border-radius: 12px; padding: 20px; margin: 25px 0; border: 1px solid #bfdbfe;">
                <h3 style="color: #1e40af; margin: 0 0 10px 0; font-size: 14px;">📅 Settlement Information</h3>
                <p style="color: #1e3a8a; margin: 0; line-height: 1.6;">
                    As per standard market settlement (T+2), your shares will be credited to your demat account by 
                    <strong>{formatted_t2_date}</strong>. Please check your demat account after this date.
                </p>
            </div>
            
            <!-- Contact Info -->
            <div style="background: #fefce8; border-radius: 12px; padding: 15px; margin: 25px 0; border: 1px solid #fcd34d;">
                <p style="color: #854d0e; margin: 0; font-size: 14px;">
                    <strong>Need Help?</strong> If you don't see the shares in your account after {formatted_t2_date}, 
                    please contact our PE Desk with your booking reference: <strong>{booking_number}</strong>
                </p>
            </div>
            
            <p style="color: #4b5563; margin-top: 25px;">
                Thank you for choosing {company_name} for your investment needs.
            </p>
            
            <p style="color: #374151; margin-top: 20px;">
                Best regards,<br>
                <strong>{company_name}</strong><br>
                <span style="color: #6b7280; font-size: 14px;">Private Equity Division</span>
            </p>
        </div>
        
        <!-- Footer -->
        <div style="background: #f3f4f6; padding: 20px; text-align: center; border-top: 1px solid #e5e7eb;">
            <p style="color: #9ca3af; font-size: 12px; margin: 0;">
                This is an automated message from the Private Equity System.
            </p>
        </div>
    </div>
    """
    
    # Get additional client emails
    additional_emails = []
    if client.get("secondary_email"):
        additional_emails.append(client["secondary_email"])
    if client.get("tertiary_email"):
        additional_emails.append(client["tertiary_email"])
    
    # Send primary email
    await send_email(
        client_email,
        subject,
        body,
        cc_email=cc_email,
        template_key="stock_transferred",
        variables={
            "booking_number": booking_number,
            "client_name": client_name,
            "stock_symbol": stock_symbol,
            "quantity": quantity,
            "dp_type": dp_type,
            "t2_date": formatted_t2_date
        },
        related_entity_type="booking",
        related_entity_id=booking_id
    )
    
    # Send to additional client emails
    for email in additional_emails:
        if email and email != client_email:
            await send_email(
                email,
                subject,
                body,
                template_key="stock_transferred",
                variables={
                    "booking_number": booking_number,
                    "client_name": client_name,
                    "stock_symbol": stock_symbol,
                    "quantity": quantity,
                    "dp_type": dp_type
                },
                related_entity_type="booking",
                related_entity_id=booking_id
            )
    
    logging.info(f"Stock transfer notification sent for booking {booking_number} to {client_email}")
