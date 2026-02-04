"""
License Service
Manages application licensing with time-based expiration
"""
import os
import hashlib
import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict
import logging

from database import db

logger = logging.getLogger(__name__)

# License configuration
LICENSE_COLLECTION = "app_license"
LICENSE_SECRET = os.environ.get("LICENSE_SECRET", "SMIFS-PRIVITY-2024-SECRET")


def generate_license_key(duration_days: int = 365, company_name: str = "SMIFS") -> Dict:
    """
    Generate a new license key with expiration
    
    Args:
        duration_days: Number of days the license is valid
        company_name: Company name to embed in license
    
    Returns:
        Dict with license_key, expires_at, and other metadata
    """
    # Generate unique components
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    random_part = secrets.token_hex(8).upper()
    
    # Create license key format: PRIV-XXXX-XXXX-XXXX-XXXX
    key_base = f"{company_name}-{timestamp}-{random_part}"
    key_hash = hashlib.sha256(f"{key_base}{LICENSE_SECRET}".encode()).hexdigest()[:16].upper()
    
    # Format as readable license key
    license_key = f"PRIV-{key_hash[:4]}-{key_hash[4:8]}-{key_hash[8:12]}-{key_hash[12:16]}"
    
    expires_at = datetime.now(timezone.utc) + timedelta(days=duration_days)
    
    return {
        "license_key": license_key,
        "duration_days": duration_days,
        "expires_at": expires_at.isoformat(),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "company_name": company_name
    }


def validate_license_format(license_key: str) -> bool:
    """Check if license key has valid format"""
    if not license_key:
        return False
    
    # Format: PRIV-XXXX-XXXX-XXXX-XXXX
    parts = license_key.upper().split("-")
    if len(parts) != 5:
        return False
    if parts[0] != "PRIV":
        return False
    for part in parts[1:]:
        if len(part) != 4 or not all(c.isalnum() for c in part):
            return False
    return True


async def get_current_license() -> Optional[Dict]:
    """Get the current active license from database"""
    license_doc = await db[LICENSE_COLLECTION].find_one(
        {"is_active": True},
        {"_id": 0}
    )
    return license_doc


async def activate_license(license_key: str, activated_by: str) -> Dict:
    """
    Activate a new license key
    
    Args:
        license_key: The license key to activate
        activated_by: User ID/email who activated
    
    Returns:
        Activation result with status and message
    """
    if not validate_license_format(license_key):
        return {
            "success": False,
            "message": "Invalid license key format. Expected: PRIV-XXXX-XXXX-XXXX-XXXX"
        }
    
    # Deactivate any existing license
    await db[LICENSE_COLLECTION].update_many(
        {"is_active": True},
        {"$set": {"is_active": False, "deactivated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    # Check if this key was previously used
    existing = await db[LICENSE_COLLECTION].find_one({"license_key": license_key.upper()})
    if existing:
        return {
            "success": False,
            "message": "This license key has already been used. Please use a new key."
        }
    
    # Calculate expiration (extract from key or use default 365 days)
    # For now, we'll use the duration stored during generation or default
    expires_at = datetime.now(timezone.utc) + timedelta(days=365)
    
    # Store new license
    license_doc = {
        "license_key": license_key.upper(),
        "is_active": True,
        "activated_at": datetime.now(timezone.utc).isoformat(),
        "activated_by": activated_by,
        "expires_at": expires_at.isoformat(),
        "duration_days": 365,
        "status": "active"
    }
    
    await db[LICENSE_COLLECTION].insert_one(license_doc)
    
    logger.info(f"License activated by {activated_by}: {license_key[:10]}...")
    
    return {
        "success": True,
        "message": "License activated successfully",
        "expires_at": expires_at.isoformat(),
        "days_remaining": 365
    }


async def activate_license_with_duration(license_key: str, duration_days: int, activated_by: str) -> Dict:
    """
    Activate a license with specific duration
    
    Args:
        license_key: The license key
        duration_days: Number of days valid
        activated_by: User who activated
    """
    if not validate_license_format(license_key):
        return {
            "success": False,
            "message": "Invalid license key format. Expected: PRIV-XXXX-XXXX-XXXX-XXXX"
        }
    
    if duration_days < 1 or duration_days > 3650:  # Max 10 years
        return {
            "success": False,
            "message": "Duration must be between 1 and 3650 days"
        }
    
    # Deactivate existing
    await db[LICENSE_COLLECTION].update_many(
        {"is_active": True},
        {"$set": {"is_active": False, "deactivated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    # Check if key was used before
    existing = await db[LICENSE_COLLECTION].find_one({"license_key": license_key.upper()})
    if existing:
        return {
            "success": False,
            "message": "This license key has already been used"
        }
    
    expires_at = datetime.now(timezone.utc) + timedelta(days=duration_days)
    
    license_doc = {
        "license_key": license_key.upper(),
        "is_active": True,
        "activated_at": datetime.now(timezone.utc).isoformat(),
        "activated_by": activated_by,
        "expires_at": expires_at.isoformat(),
        "duration_days": duration_days,
        "status": "active"
    }
    
    await db[LICENSE_COLLECTION].insert_one(license_doc)
    
    logger.info(f"License activated with {duration_days} days by {activated_by}")
    
    return {
        "success": True,
        "message": f"License activated for {duration_days} days",
        "expires_at": expires_at.isoformat(),
        "days_remaining": duration_days
    }


async def check_license_status() -> Dict:
    """
    Check current license status
    
    Returns:
        Dict with is_valid, days_remaining, expires_at, etc.
    """
    license_doc = await get_current_license()
    
    if not license_doc:
        return {
            "is_valid": False,
            "status": "no_license",
            "message": "No active license found. Please activate a license to use the application.",
            "days_remaining": 0
        }
    
    expires_at = datetime.fromisoformat(license_doc["expires_at"].replace("Z", "+00:00"))
    now = datetime.now(timezone.utc)
    
    if expires_at <= now:
        # License expired
        await db[LICENSE_COLLECTION].update_one(
            {"license_key": license_doc["license_key"]},
            {"$set": {"status": "expired"}}
        )
        return {
            "is_valid": False,
            "status": "expired",
            "message": "License has expired. Please renew with a new license key.",
            "expires_at": license_doc["expires_at"],
            "expired_on": license_doc["expires_at"],
            "days_remaining": 0
        }
    
    days_remaining = (expires_at - now).days
    
    # Warning if expiring soon (within 30 days)
    if days_remaining <= 30:
        status = "expiring_soon"
        message = f"License expiring in {days_remaining} days. Please renew soon."
    else:
        status = "active"
        message = "License is active"
    
    return {
        "is_valid": True,
        "status": status,
        "message": message,
        "license_key": license_doc["license_key"][:10] + "...",
        "activated_at": license_doc.get("activated_at"),
        "expires_at": license_doc["expires_at"],
        "days_remaining": days_remaining,
        "duration_days": license_doc.get("duration_days", 365)
    }


async def get_license_history() -> list:
    """Get history of all licenses"""
    licenses = await db[LICENSE_COLLECTION].find(
        {},
        {"_id": 0}
    ).sort("activated_at", -1).to_list(50)
    
    # Mask license keys for security
    for lic in licenses:
        if lic.get("license_key"):
            lic["license_key"] = lic["license_key"][:10] + "..." + lic["license_key"][-4:]
    
    return licenses


async def revoke_license(license_key: str, revoked_by: str) -> Dict:
    """Revoke/deactivate a specific license"""
    result = await db[LICENSE_COLLECTION].update_one(
        {"license_key": {"$regex": f"^{license_key[:10]}", "$options": "i"}},
        {
            "$set": {
                "is_active": False,
                "status": "revoked",
                "revoked_at": datetime.now(timezone.utc).isoformat(),
                "revoked_by": revoked_by
            }
        }
    )
    
    if result.modified_count > 0:
        return {"success": True, "message": "License revoked successfully"}
    return {"success": False, "message": "License not found"}
