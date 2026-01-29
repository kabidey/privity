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
    """Test SMTP connection (PE Desk only)"""
    if current_user.get("role", 5) != 1:
        raise HTTPException(status_code=403, detail="Only PE Desk can test SMTP connection")
    
    config = await db.smtp_settings.find_one({}, {"_id": 0})
    
    if not config:
        raise HTTPException(status_code=400, detail="SMTP not configured. Please configure SMTP settings first.")
    
    test_result = None
    test_message = ""
    
    try:
        use_ssl = config.get("smtp_use_ssl", False)
        use_tls = config.get("smtp_use_tls", True)
        
        if use_ssl:
            server = smtplib.SMTP_SSL(config["smtp_host"], config["smtp_port"], timeout=config.get("timeout", 30))
        else:
            server = smtplib.SMTP(config["smtp_host"], config["smtp_port"], timeout=config.get("timeout", 30))
            if use_tls:
                server.starttls()
        
        server.login(config["smtp_username"], config.get("smtp_password", ""))
        server.quit()
        
        test_result = "success"
        test_message = "SMTP connection successful!"
        
    except smtplib.SMTPAuthenticationError:
        test_result = "auth_failed"
        test_message = "Authentication failed. Check username and password."
    except smtplib.SMTPConnectError:
        test_result = "connection_failed"
        test_message = "Could not connect to SMTP server. Check host and port."
    except Exception as e:
        test_result = f"error: {str(e)}"
        test_message = f"Connection failed: {str(e)}"
    
    # Update last test result in database
    await db.smtp_settings.update_one(
        {},
        {"$set": {
            "last_test": datetime.now(timezone.utc).isoformat(),
            "last_test_result": test_result,
            "last_test_email": test_data.test_email if test_data else None
        }}
    )
    
    return {"success": test_result == "success", "message": test_message}


@router.get("/presets")
async def get_smtp_presets(current_user: dict = Depends(get_current_user)):
    """Get common SMTP provider presets (PE Level only)"""
    if current_user.get("role", 5) not in [1, 2]:
        raise HTTPException(status_code=403, detail="Only PE Level users can access SMTP presets")
    
    return [
        {"key": key, **value}
        for key, value in SMTP_PRESETS.items()
    ]
