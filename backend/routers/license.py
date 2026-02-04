"""
License Router
API endpoints for license management
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional

from utils.auth import get_current_user
from services.license_service import (
    check_license_status,
    activate_license,
    activate_license_with_duration,
    generate_license_key,
    get_license_history,
    revoke_license
)
from services.permission_service import require_permission

router = APIRouter(prefix="/license", tags=["License Management"])


class ActivateLicenseRequest(BaseModel):
    license_key: str
    duration_days: Optional[int] = None  # If provided, use custom duration


class GenerateLicenseRequest(BaseModel):
    duration_days: int = 365
    company_name: str = "SMIFS"


# ============== Public Endpoints (for license check) ==============

@router.get("/status")
async def get_license_status():
    """
    Check current license status.
    This endpoint is public so the app can check license before login.
    """
    status = await check_license_status()
    return status


# ============== Protected Endpoints ==============

@router.post("/activate")
async def activate_new_license(
    request: ActivateLicenseRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Activate a new license key.
    Only PE Desk can activate licenses.
    """
    # Check if user is PE Desk (role 1)
    if current_user.get("role") != 1:
        raise HTTPException(status_code=403, detail="Only PE Desk can activate licenses")
    
    if request.duration_days:
        result = await activate_license_with_duration(
            license_key=request.license_key,
            duration_days=request.duration_days,
            activated_by=current_user.get("email", "unknown")
        )
    else:
        result = await activate_license(
            license_key=request.license_key,
            activated_by=current_user.get("email", "unknown")
        )
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    
    return result


@router.post("/generate", dependencies=[Depends(require_permission("security.manage_license", "generate license keys"))])
async def generate_new_license_key(
    request: GenerateLicenseRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Generate a new license key (PE Desk only).
    This is for admin use to generate keys for distribution.
    """
    # Only PE Desk can generate
    if current_user.get("role") != 1:
        raise HTTPException(status_code=403, detail="Only PE Desk can generate license keys")
    
    license_data = generate_license_key(
        duration_days=request.duration_days,
        company_name=request.company_name
    )
    
    return {
        "success": True,
        "license": license_data,
        "message": f"License key generated for {request.duration_days} days"
    }


@router.get("/history", dependencies=[Depends(require_permission("security.view_audit", "view license history"))])
async def get_all_license_history(current_user: dict = Depends(get_current_user)):
    """Get history of all license activations"""
    if current_user.get("role") != 1:
        raise HTTPException(status_code=403, detail="Only PE Desk can view license history")
    
    history = await get_license_history()
    return {"licenses": history}


@router.post("/revoke", dependencies=[Depends(require_permission("security.manage_license", "revoke licenses"))])
async def revoke_active_license(
    license_key: str,
    current_user: dict = Depends(get_current_user)
):
    """Revoke/deactivate a license"""
    if current_user.get("role") != 1:
        raise HTTPException(status_code=403, detail="Only PE Desk can revoke licenses")
    
    result = await revoke_license(
        license_key=license_key,
        revoked_by=current_user.get("email", "unknown")
    )
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    
    return result
