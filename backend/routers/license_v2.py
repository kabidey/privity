"""
License Router V2
Granular licensing system with separate PE/FI licenses

Access: Only the secret license admin (deynet) can access these endpoints
"""
from fastapi import APIRouter, HTTPException, Depends, Body
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime, timezone

from database import db
from utils.auth import get_current_user
from services.license_service_v2 import (
    generate_license_key_v2,
    create_license,
    activate_license_v2,
    get_active_license,
    get_all_licenses,
    revoke_license_v2,
    check_feature_license,
    check_module_license,
    check_usage_limit,
    get_license_status_v2,
    is_license_admin,
    get_licensable_definitions,
    LICENSE_ADMIN_ROLE,
    LICENSABLE_MODULES,
    LICENSABLE_FEATURES,
    USAGE_LIMITS
)

router = APIRouter(prefix="/licence", tags=["License Management V2"])


# ============== Pydantic Models ==============

class GenerateLicenseRequest(BaseModel):
    company_type: str = Field(..., description="'private_equity' or 'fixed_income'")
    company_name: str = Field(default="SMIFS", description="Company name")
    duration_days: int = Field(default=365, ge=1, le=3650, description="License validity in days")
    modules: List[str] = Field(default=[], description="List of module keys to enable")
    features: List[str] = Field(default=[], description="List of feature keys to enable")
    usage_limits: Dict[str, int] = Field(default={}, description="Usage limits (max_users, max_clients, etc.)")


class ActivateLicenseRequest(BaseModel):
    license_key: str = Field(..., description="License key to activate")


class CheckFeatureRequest(BaseModel):
    feature: str = Field(..., description="Feature key to check")
    company_type: Optional[str] = Field(None, description="Company type (optional)")


# ============== Helper Functions ==============

async def require_license_admin(current_user: dict = Depends(get_current_user)):
    """Dependency to ensure only license admin can access"""
    if not await is_license_admin(current_user):
        raise HTTPException(
            status_code=403,
            detail="Access denied. Only license administrators can access this resource."
        )
    return current_user


# ============== License Admin Endpoints ==============

@router.get("/definitions")
async def get_license_definitions(admin: dict = Depends(require_license_admin)):
    """
    Get all licensable modules, features, and usage limit definitions.
    Used to populate the license generation form.
    """
    return get_licensable_definitions()


@router.post("/generate")
async def generate_license(
    request: GenerateLicenseRequest,
    admin: dict = Depends(require_license_admin)
):
    """
    Generate a new license key with granular permissions.
    
    - company_type: 'private_equity' or 'fixed_income'
    - modules: List of module keys (e.g., ['private_equity'])
    - features: List of feature keys (e.g., ['clients', 'bookings', 'reports'])
    - usage_limits: Dict of limits (e.g., {'max_users': 50, 'max_clients': 1000})
    """
    if request.company_type not in ["private_equity", "fixed_income"]:
        raise HTTPException(status_code=400, detail="company_type must be 'private_equity' or 'fixed_income'")
    
    # Generate the key
    key_data = generate_license_key_v2(
        company_type=request.company_type,
        duration_days=request.duration_days,
        company_name=request.company_name
    )
    
    # Set default modules and features if not provided
    modules = request.modules if request.modules else [request.company_type]
    features = request.features if request.features else list(LICENSABLE_FEATURES.keys())
    
    # Set default usage limits
    usage_limits = {}
    for limit_key, limit_info in USAGE_LIMITS.items():
        usage_limits[limit_key] = request.usage_limits.get(limit_key, limit_info["default"])
    
    # Create the license in database
    result = await create_license(
        license_key=key_data["license_key"],
        company_type=request.company_type,
        modules=modules,
        features=features,
        usage_limits=usage_limits,
        duration_days=request.duration_days,
        company_name=request.company_name,
        created_by=admin.get("email", "license_admin")
    )
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    
    return {
        "success": True,
        "license": {
            "key": key_data["license_key"],
            "company_type": request.company_type,
            "company_name": request.company_name,
            "duration_days": request.duration_days,
            "expires_at": key_data["expires_at"],
            "modules": modules,
            "features": features,
            "usage_limits": usage_limits
        },
        "message": f"License key generated for {request.company_type}"
    }


@router.post("/activate")
async def activate_license(
    request: ActivateLicenseRequest,
    admin: dict = Depends(require_license_admin)
):
    """
    Activate a license key.
    Deactivates any existing active license for the same company type.
    """
    result = await activate_license_v2(
        license_key=request.license_key,
        activated_by=admin.get("email", "license_admin")
    )
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    
    return result


@router.post("/revoke")
async def revoke_license(
    license_key: str = Body(..., embed=True),
    admin: dict = Depends(require_license_admin)
):
    """Revoke a license key"""
    result = await revoke_license_v2(
        license_key=license_key,
        revoked_by=admin.get("email", "license_admin")
    )
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    
    return result


@router.get("/all")
async def get_all_license_list(admin: dict = Depends(require_license_admin)):
    """Get all licenses (active and inactive)"""
    licenses = await get_all_licenses()
    
    # Mask full license keys for security display
    for lic in licenses:
        if lic.get("license_key"):
            key = lic["license_key"]
            lic["license_key_masked"] = key[:15] + "..." + key[-4:] if len(key) > 19 else key
    
    return {"licenses": licenses}


@router.get("/status")
async def get_license_status(
    company_type: Optional[str] = None,
    admin: dict = Depends(require_license_admin)
):
    """
    Get license status for dashboard display.
    If company_type is provided, returns status for that company only.
    Otherwise returns status for both PE and FI.
    """
    status = await get_license_status_v2(company_type)
    return {"status": status}


@router.get("/active/{company_type}")
async def get_active_license_details(
    company_type: str,
    admin: dict = Depends(require_license_admin)
):
    """Get detailed active license for a company type"""
    if company_type not in ["private_equity", "fixed_income"]:
        raise HTTPException(status_code=400, detail="Invalid company type")
    
    license_doc = await get_active_license(company_type)
    
    if not license_doc:
        return {"active_license": None, "message": f"No active license for {company_type}"}
    
    return {"active_license": license_doc}


# ============== Public Endpoints (for app license checking) ==============

@router.get("/check/status")
async def check_app_license_status(current_user: dict = Depends(get_current_user)):
    """
    Check license status for the current user.
    Returns which modules and features are available.
    """
    # License admin always has full access
    if await is_license_admin(current_user):
        return {
            "is_licensed": True,
            "private_equity": {
                "is_licensed": True,
                "modules": ["*"],
                "features": ["*"]
            },
            "fixed_income": {
                "is_licensed": True,
                "modules": ["*"],
                "features": ["*"]
            }
        }
    
    status = await get_license_status_v2()
    
    return {
        "is_licensed": status["private_equity"]["is_active"] or status["fixed_income"]["is_active"],
        "private_equity": {
            "is_licensed": status["private_equity"]["is_active"],
            "status": status["private_equity"]["status"],
            "modules": status["private_equity"]["modules"],
            "features": status["private_equity"]["features"],
            "days_remaining": status["private_equity"]["days_remaining"],
            "usage_limits": status["private_equity"]["usage_limits"]
        },
        "fixed_income": {
            "is_licensed": status["fixed_income"]["is_active"],
            "status": status["fixed_income"]["status"],
            "modules": status["fixed_income"]["modules"],
            "features": status["fixed_income"]["features"],
            "days_remaining": status["fixed_income"]["days_remaining"],
            "usage_limits": status["fixed_income"]["usage_limits"]
        }
    }


@router.post("/check/feature")
async def check_feature_available(
    request: CheckFeatureRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Check if a specific feature is available based on license.
    Returns is_licensed, message, and contact_admin flag.
    """
    # License admin always has access
    if await is_license_admin(current_user):
        return {"is_licensed": True, "message": "Full access", "contact_admin": False}
    
    result = await check_feature_license(request.feature, request.company_type)
    return result


@router.get("/check/module/{module}")
async def check_module_available(
    module: str,
    current_user: dict = Depends(get_current_user)
):
    """Check if a module is licensed"""
    # License admin always has access
    if await is_license_admin(current_user):
        return {"is_licensed": True, "message": "Full access", "contact_admin": False}
    
    result = await check_module_license(module)
    return result


@router.get("/check/usage/{limit_type}/{company_type}")
async def check_usage_available(
    limit_type: str,
    company_type: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Check if a usage limit allows more items.
    Returns current count, limit, and remaining.
    """
    # License admin has unlimited access
    if await is_license_admin(current_user):
        return {"allowed": True, "limit": -1, "current": 0, "remaining": -1, "message": "Unlimited"}
    
    # Get current count based on limit type
    current_count = 0
    
    if limit_type == "max_users":
        current_count = await db.users.count_documents({"is_active": True, "is_hidden": {"$ne": True}})
    elif limit_type == "max_clients":
        current_count = await db.clients.count_documents({"status": {"$ne": "deleted"}})
    elif limit_type == "max_bookings_per_month":
        from datetime import datetime, timedelta
        month_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        current_count = await db.bookings.count_documents({"created_at": {"$gte": month_start.isoformat()}})
    elif limit_type == "max_fi_orders_per_month":
        from datetime import datetime, timedelta
        month_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        current_count = await db.fi_orders.count_documents({"created_at": {"$gte": month_start.isoformat()}})
    
    result = await check_usage_limit(limit_type, company_type, current_count)
    return result


# ============== Verify License Admin Login ==============

@router.get("/verify-admin")
async def verify_license_admin_access(current_user: dict = Depends(get_current_user)):
    """
    Verify if current user is a license admin.
    Used by frontend to determine if /licence page should be accessible.
    """
    is_admin = await is_license_admin(current_user)
    return {
        "is_license_admin": is_admin,
        "message": "Full license management access" if is_admin else "Not a license administrator"
    }
