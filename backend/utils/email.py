"""
Email utilities
"""
import smtplib
import logging
import random
import string
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config import EMAIL_HOST, EMAIL_PORT, EMAIL_USERNAME, EMAIL_PASSWORD, EMAIL_FROM

async def send_email(to_email: str, subject: str, html_content: str, cc_emails: list = None):
    """Send email using SMTP"""
    if not EMAIL_USERNAME or not EMAIL_PASSWORD:
        logging.warning("Email credentials not configured, skipping email send")
        return False
    
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = EMAIL_FROM
        msg['To'] = to_email
        if cc_emails:
            msg['Cc'] = ', '.join(cc_emails)
        
        html_part = MIMEText(html_content, 'html')
        msg.attach(html_part)
        
        recipients = [to_email] + (cc_emails or [])
        
        with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as server:
            server.starttls()
            server.login(EMAIL_USERNAME, EMAIL_PASSWORD)
            server.sendmail(EMAIL_FROM, recipients, msg.as_string())
        
        logging.info(f"Email sent to {to_email}")
        return True
    except Exception as e:
        logging.error(f"Failed to send email: {e}")
        return False

def generate_otp(length: int = 6) -> str:
    """Generate numeric OTP"""
    return ''.join(random.choices(string.digits, k=length))

async def send_otp_email(to_email: str, otp: str, user_name: str = "User"):
    """Send OTP email for password reset"""
    subject = "Password Reset OTP - Private Equity System"
    html_content = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: #333;">Password Reset Request</h2>
        <p>Dear {user_name},</p>
        <p>You have requested to reset your password. Use the following OTP to proceed:</p>
        <div style="background: #f5f5f5; padding: 20px; text-align: center; margin: 20px 0;">
            <h1 style="color: #007bff; letter-spacing: 5px; margin: 0;">{otp}</h1>
        </div>
        <p><strong>This OTP is valid for 10 minutes.</strong></p>
        <p>If you did not request this password reset, please ignore this email or contact support.</p>
        <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
        <p style="color: #666; font-size: 12px;">This is an automated message from Private Equity System.</p>
    </div>
    """
    return await send_email(to_email, subject, html_content)
