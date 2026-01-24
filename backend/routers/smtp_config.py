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

router = APIRouter(prefix="/smtp-config", tags=["SMTP Configuration"])


# ============== Pydantic Models ==============
class SMTPConfig(BaseModel):
    smtp_host: str
    smtp_port: int
    smtp_username: str
    smtp_password: Optional[str] = None
    smtp_from_email: str
    smtp_from_name: Optional[str] = "SMIFS Private Equity System"
    smtp_use_tls: bool = True
    smtp_use_ssl: bool = False


class SMTPTestRequest(BaseModel):
    test_email: Optional[str] = None


# ============== SMTP Presets ==============
SMTP_PRESETS = {
    "microsoft365": {
        "name": "Microsoft 365 / Outlook",
        "smtp_host": "smtp.office365.com",
        "smtp_port": 587,
        "smtp_use_tls": True,
        "smtp_use_ssl": False
    },
    "google": {
        "name": "Google Workspace / Gmail",
        "smtp_host": "smtp.gmail.com",
        "smtp_port": 587,
        "smtp_use_tls": True,
        "smtp_use_ssl": False
    },
    "sendgrid": {
        "name": "SendGrid",
        "smtp_host": "smtp.sendgrid.net",
        "smtp_port": 587,
        "smtp_use_tls": True,
        "smtp_use_ssl": False
    },
    "amazon_ses": {
        "name": "Amazon SES",
        "smtp_host": "email-smtp.us-east-1.amazonaws.com",
        "smtp_port": 587,
        "smtp_use_tls": True,
        "smtp_use_ssl": False
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
            "smtp_use_tls": True,
            "smtp_use_ssl": False,
            "is_configured": False
        }
    
    # Don't return password
    config.pop("smtp_password", None)
    config["is_configured"] = True
    return config


@router.put("")
async def update_smtp_config(
    config: SMTPConfig,
    current_user: dict = Depends(get_current_user)
):
    """Update SMTP configuration (PE Desk only)"""
    if current_user.get("role", 5) != 1:
        raise HTTPException(status_code=403, detail="Only PE Desk can update SMTP configuration")
    
    update_data = {
        "smtp_host": config.smtp_host,
        "smtp_port": config.smtp_port,
        "smtp_username": config.smtp_username,
        "smtp_from_email": config.smtp_from_email,
        "smtp_from_name": config.smtp_from_name or "SMIFS Private Equity System",
        "smtp_use_tls": config.smtp_use_tls,
        "smtp_use_ssl": config.smtp_use_ssl,
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
    
    return {"message": "SMTP configuration updated successfully"}


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
    
    try:
        if config.get("smtp_use_ssl"):
            server = smtplib.SMTP_SSL(config["smtp_host"], config["smtp_port"], timeout=10)
        else:
            server = smtplib.SMTP(config["smtp_host"], config["smtp_port"], timeout=10)
            if config.get("smtp_use_tls"):
                server.starttls()
        
        server.login(config["smtp_username"], config.get("smtp_password", ""))
        server.quit()
        
        return {"success": True, "message": "SMTP connection successful!"}
    except smtplib.SMTPAuthenticationError:
        return {"success": False, "message": "Authentication failed. Check username and password."}
    except smtplib.SMTPConnectError:
        return {"success": False, "message": "Could not connect to SMTP server. Check host and port."}
    except Exception as e:
        return {"success": False, "message": f"Connection failed: {str(e)}"}


@router.get("/presets")
async def get_smtp_presets(current_user: dict = Depends(get_current_user)):
    """Get common SMTP provider presets (PE Desk only)"""
    if current_user.get("role", 5) != 1:
        raise HTTPException(status_code=403, detail="Only PE Desk can access SMTP presets")
    
    return [
        {"key": key, **value}
        for key, value in SMTP_PRESETS.items()
    ]
