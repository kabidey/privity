"""
SMTP Configuration Router
Handles SMTP server settings for email sending
"""
from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from pydantic import BaseModel
from datetime import datetime, timezone
import smtplib

from database import db
from routers.auth import get_current_user

router = APIRouter(prefix="/email-config", tags=["Email Configuration"])


# ============== Pydantic Models ==============
class SMTPConfig(BaseModel):
    smtp_host: str
    smtp_port: int
    smtp_username: str
    smtp_password: Optional[str] = None
    smtp_from_email: str
    smtp_from_name: Optional[str] = "SMIFS Private Equity System"
    use_tls: Optional[bool] = True
    use_ssl: Optional[bool] = False
    smtp_use_tls: Optional[bool] = None  # Accept both field names
    smtp_use_ssl: Optional[bool] = None
    is_enabled: Optional[bool] = True
    timeout: Optional[int] = 30


class SMTPTestRequest(BaseModel):
    test_email: Optional[str] = None


# ============== SMTP Presets ==============
SMTP_PRESETS = {
    "microsoft365": {
        "name": "Microsoft 365 / Outlook",
        "smtp_host": "smtp.office365.com",
        "smtp_port": 587,
        "use_tls": True,
        "use_ssl": False,
        "notes": "Use App Password if MFA is enabled"
    },
    "google": {
        "name": "Google Workspace / Gmail",
        "smtp_host": "smtp.gmail.com",
        "smtp_port": 587,
        "use_tls": True,
        "use_ssl": False,
        "notes": "Enable 'Less secure apps' or use App Password"
    },
    "sendgrid": {
        "name": "SendGrid",
        "smtp_host": "smtp.sendgrid.net",
        "smtp_port": 587,
        "use_tls": True,
        "use_ssl": False,
        "notes": "Use API key as password, 'apikey' as username"
    },
    "amazon_ses": {
        "name": "Amazon SES",
        "smtp_host": "email-smtp.us-east-1.amazonaws.com",
        "smtp_port": 587,
        "use_tls": True,
        "use_ssl": False,
        "notes": "Use SMTP credentials from AWS Console"
    },
    "zoho": {
        "name": "Zoho Mail",
        "smtp_host": "smtp.zoho.com",
        "smtp_port": 587,
        "use_tls": True,
        "use_ssl": False,
        "notes": "Use App Password for enhanced security"
    },
    "mailgun": {
        "name": "Mailgun",
        "smtp_host": "smtp.mailgun.org",
        "smtp_port": 587,
        "use_tls": True,
        "use_ssl": False,
        "notes": "Use domain credentials from Mailgun dashboard"
    }
}


# ============== SMTP Config Endpoints ==============
@router.get("")
async def get_smtp_config(current_user: dict = Depends(get_current_user)):
    """Get current SMTP configuration (PE Desk only)"""
    if current_user.get("role", 5) != 1:
        raise HTTPException(status_code=403, detail="Only PE Desk can access SMTP configuration")
    
    config = await db.smtp_settings.find_one({}, {"_id": 0})
    
    if not config:
        return {
            "smtp_host": "",
            "smtp_port": 587,
            "smtp_username": "",
            "smtp_from_email": "",
            "smtp_from_name": "SMIFS Private Equity System",
            "use_tls": True,
            "use_ssl": False,
            "is_enabled": False,
            "timeout": 30,
            "is_configured": False,
            "connection_status": "not_configured"
        }
    
    # Don't return password
    config.pop("smtp_password", None)
    config["is_configured"] = True
    
    # Normalize field names for frontend
    if "smtp_use_tls" in config:
        config["use_tls"] = config.pop("smtp_use_tls")
    if "smtp_use_ssl" in config:
        config["use_ssl"] = config.pop("smtp_use_ssl")
    
    # Set connection status based on last test
    if config.get("last_test_result") == "success":
        config["connection_status"] = "connected"
    elif config.get("last_test_result"):
        config["connection_status"] = "connection_failed"
    else:
        config["connection_status"] = "configured"
    
    return config


@router.put("")
async def update_smtp_config(
    config: SMTPConfig,
    current_user: dict = Depends(get_current_user)
):
    """Update SMTP configuration (PE Desk only)"""
    if current_user.get("role", 5) != 1:
        raise HTTPException(status_code=403, detail="Only PE Desk can update SMTP configuration")
    
    # Handle both field name formats
    use_tls = config.smtp_use_tls if config.smtp_use_tls is not None else config.use_tls
    use_ssl = config.smtp_use_ssl if config.smtp_use_ssl is not None else config.use_ssl
    
    update_data = {
        "smtp_host": config.smtp_host,
        "smtp_port": config.smtp_port,
        "smtp_username": config.smtp_username,
        "smtp_from_email": config.smtp_from_email,
        "smtp_from_name": config.smtp_from_name or "SMIFS Private Equity System",
        "smtp_use_tls": use_tls,
        "smtp_use_ssl": use_ssl,
        "is_enabled": config.is_enabled if config.is_enabled is not None else True,
        "timeout": config.timeout or 30,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "updated_by": current_user["id"]
    }
    
    # Only update password if provided
    if config.smtp_password:
        update_data["smtp_password"] = config.smtp_password
    
    existing = await db.smtp_settings.find_one({})
    
    if existing:
        await db.smtp_settings.update_one({}, {"$set": update_data})
    else:
        update_data["created_at"] = datetime.now(timezone.utc).isoformat()
        await db.smtp_settings.insert_one(update_data)
    
    return {"message": "SMTP configuration updated successfully", "is_configured": True}


@router.post("/test")
async def test_smtp_connection(
    test_data: SMTPTestRequest = None,
    current_user: dict = Depends(get_current_user)
):
    """Test SMTP connection and send a test email (PE Desk only)"""
    if current_user.get("role", 5) != 1:
        raise HTTPException(status_code=403, detail="Only PE Desk can test SMTP connection")
    
    config = await db.smtp_settings.find_one({}, {"_id": 0})
    
    if not config:
        raise HTTPException(status_code=400, detail="SMTP not configured. Please configure SMTP settings first.")
    
    test_result = None
    test_message = ""
    test_email = test_data.test_email if test_data and test_data.test_email else config.get("smtp_from_email")
    
    try:
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        
        use_ssl = config.get("smtp_use_ssl", False)
        use_tls = config.get("smtp_use_tls", True)
        
        # Create SMTP connection
        if use_ssl:
            server = smtplib.SMTP_SSL(config["smtp_host"], config["smtp_port"], timeout=config.get("timeout", 30))
        else:
            server = smtplib.SMTP(config["smtp_host"], config["smtp_port"], timeout=config.get("timeout", 30))
            if use_tls:
                server.starttls()
        
        # Login
        server.login(config["smtp_username"], config.get("smtp_password", ""))
        
        # Create and send test email
        msg = MIMEMultipart('alternative')
        msg['Subject'] = 'SMTP Test - Privity System'
        msg['From'] = f"{config.get('smtp_from_name', 'Privity System')} <{config['smtp_from_email']}>"
        msg['To'] = test_email
        
        # Plain text version
        text_content = f"""
Hello,

This is a test email from the Privity Private Equity System.

If you received this email, your SMTP configuration is working correctly.

SMTP Server: {config['smtp_host']}:{config['smtp_port']}
From: {config['smtp_from_email']}
TLS: {'Enabled' if use_tls else 'Disabled'}
SSL: {'Enabled' if use_ssl else 'Disabled'}

Sent at: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}

Best regards,
Privity System
        """
        
        # HTML version
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; padding: 20px;">
            <div style="max-width: 600px; margin: 0 auto; border: 1px solid #e5e7eb; border-radius: 8px; overflow: hidden;">
                <div style="background: linear-gradient(135deg, #10b981, #059669); padding: 20px; text-align: center;">
                    <h1 style="color: white; margin: 0;">✓ SMTP Test Successful</h1>
                </div>
                <div style="padding: 20px;">
                    <p>Hello,</p>
                    <p>This is a test email from the <strong>Privity Private Equity System</strong>.</p>
                    <p>If you received this email, your SMTP configuration is working correctly.</p>
                    
                    <div style="background: #f3f4f6; padding: 15px; border-radius: 8px; margin: 20px 0;">
                        <h3 style="margin-top: 0; color: #374151;">Configuration Details</h3>
                        <table style="width: 100%; border-collapse: collapse;">
                            <tr><td style="padding: 5px 0; color: #6b7280;">SMTP Server:</td><td style="padding: 5px 0;">{config['smtp_host']}:{config['smtp_port']}</td></tr>
                            <tr><td style="padding: 5px 0; color: #6b7280;">From Address:</td><td style="padding: 5px 0;">{config['smtp_from_email']}</td></tr>
                            <tr><td style="padding: 5px 0; color: #6b7280;">TLS:</td><td style="padding: 5px 0;">{'✓ Enabled' if use_tls else '✗ Disabled'}</td></tr>
                            <tr><td style="padding: 5px 0; color: #6b7280;">SSL:</td><td style="padding: 5px 0;">{'✓ Enabled' if use_ssl else '✗ Disabled'}</td></tr>
                        </table>
                    </div>
                    
                    <p style="color: #6b7280; font-size: 12px;">
                        Sent at: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}
                    </p>
                </div>
                <div style="background: #f9fafb; padding: 15px; text-align: center; border-top: 1px solid #e5e7eb;">
                    <p style="margin: 0; color: #9ca3af; font-size: 12px;">Privity Private Equity System</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        part1 = MIMEText(text_content, 'plain')
        part2 = MIMEText(html_content, 'html')
        msg.attach(part1)
        msg.attach(part2)
        
        # Send the email
        server.sendmail(config['smtp_from_email'], test_email, msg.as_string())
        server.quit()
        
        test_result = "success"
        test_message = f"Test email sent successfully to {test_email}!"
        
    except smtplib.SMTPAuthenticationError as e:
        test_result = "auth_failed"
        test_message = f"Authentication failed. Check username and password. Error: {str(e)}"
    except smtplib.SMTPConnectError as e:
        test_result = "connection_failed"
        test_message = f"Could not connect to SMTP server. Check host and port. Error: {str(e)}"
    except smtplib.SMTPRecipientsRefused as e:
        test_result = "recipient_refused"
        test_message = f"Recipient email was refused by the server. Error: {str(e)}"
    except Exception as e:
        test_result = f"error"
        test_message = f"Failed to send test email: {str(e)}"
    
    # Update last test result in database
    await db.smtp_settings.update_one(
        {},
        {"$set": {
            "last_test": datetime.now(timezone.utc).isoformat(),
            "last_test_result": test_result,
            "last_test_email": test_email
        }}
    )
    
    return {"success": test_result == "success", "message": test_message, "test_email": test_email}


@router.get("/presets")
async def get_smtp_presets(current_user: dict = Depends(get_current_user)):
    """Get common SMTP provider presets (PE Level only)"""
    if current_user.get("role", 5) not in [1, 2]:
        raise HTTPException(status_code=403, detail="Only PE Level users can access SMTP presets")
    
    return [
        {"key": key, **value}
        for key, value in SMTP_PRESETS.items()
    ]
