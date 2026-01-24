"""
Email service with template support
"""
import smtplib
import logging
import random
import string
import re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Optional
from datetime import datetime, timezone
import uuid

from config import EMAIL_HOST, EMAIL_PORT, EMAIL_USERNAME, EMAIL_PASSWORD, EMAIL_FROM, DEFAULT_EMAIL_TEMPLATES
from database import db

async def get_email_template(template_key: str) -> Optional[Dict]:
    """Get email template from database or default"""
    # Try database first
    template = await db.email_templates.find_one({"key": template_key, "is_active": True}, {"_id": 0})
    if template:
        return template
    
    # Fall back to default
    default = DEFAULT_EMAIL_TEMPLATES.get(template_key)
    if default:
        return {
            "id": template_key,
            "key": template_key,
            **default,
            "is_active": True
        }
    return None

def render_template(template_body: str, variables: Dict[str, str]) -> str:
    """Render template with variables"""
    result = template_body
    for key, value in variables.items():
        result = result.replace(f"{{{{{key}}}}}", str(value) if value else "")
    return result

async def send_templated_email(
    template_key: str,
    to_email: str,
    variables: Dict[str, str],
    cc_email: Optional[str] = None
) -> bool:
    """Send email using template"""
    template = await get_email_template(template_key)
    if not template:
        logging.warning(f"Email template '{template_key}' not found")
        return False
    
    subject = render_template(template["subject"], variables)
    body = render_template(template["body"], variables)
    
    return await send_email(to_email, subject, body, cc_email)

async def send_email(to_email: str, subject: str, body: str, cc_email: Optional[str] = None) -> bool:
    """Send email via SMTP"""
    if not EMAIL_USERNAME or not EMAIL_PASSWORD:
        logging.warning("Email credentials not configured, skipping email send")
        return False
    
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_FROM
        msg['To'] = to_email
        if cc_email:
            msg['Cc'] = cc_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'html'))
        
        recipients = [to_email]
        if cc_email:
            recipients.append(cc_email)
        
        with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as server:
            server.starttls()
            server.login(EMAIL_USERNAME, EMAIL_PASSWORD)
            server.sendmail(EMAIL_FROM, recipients, msg.as_string())
        
        logging.info(f"Email sent to {to_email}")
        return True
    except Exception as e:
        logging.error(f"Failed to send email: {str(e)}")
        return False

def generate_otp(length: int = 6) -> str:
    """Generate numeric OTP"""
    return ''.join(random.choices(string.digits, k=length))

async def send_otp_email(to_email: str, otp: str, user_name: str = "User") -> bool:
    """Send OTP email for password reset"""
    return await send_templated_email(
        "password_reset_otp",
        to_email,
        {"user_name": user_name, "otp": otp}
    )

async def init_email_templates():
    """Initialize default email templates in database"""
    for key, template_data in DEFAULT_EMAIL_TEMPLATES.items():
        existing = await db.email_templates.find_one({"key": key})
        if not existing:
            await db.email_templates.insert_one({
                "id": str(uuid.uuid4()),
                "key": key,
                **template_data,
                "is_active": True,
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "updated_by": None
            })
            logging.info(f"Created default email template: {key}")
