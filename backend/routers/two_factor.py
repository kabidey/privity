"""
Two-Factor Authentication (2FA) Routes

Implements TOTP-based 2FA with:
- Enable/disable 2FA
- QR code generation for authenticator apps
- TOTP verification during login
- Backup code management
"""
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, timezone
import logging

from database import db
from config import ROLES, is_pe_level
from utils.auth import get_current_user, verify_password
from services.totp_service import TwoFactorManager, TOTPService, BackupCodeService
from services.audit_service import create_audit_log

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth/2fa", tags=["Two-Factor Authentication"])


# ============== Pydantic Models ==============

class EnableTwoFactorRequest(BaseModel):
    """Request to initiate 2FA setup - requires password confirmation"""
    password: str = Field(..., min_length=1, description="Current password for verification")


class EnableTwoFactorResponse(BaseModel):
    """Response containing QR code and backup codes for 2FA setup"""
    qr_code_url: str
    secret_key: str  # Shown only during setup for manual entry
    backup_codes: List[str]
    message: str


class VerifyTwoFactorSetupRequest(BaseModel):
    """Request to verify TOTP code and complete 2FA setup"""
    totp_code: str = Field(..., min_length=6, max_length=6, description="6-digit TOTP code from authenticator app")


class VerifyTwoFactorLoginRequest(BaseModel):
    """Request to verify TOTP code during login"""
    totp_code: str = Field(..., min_length=6, max_length=6, description="6-digit TOTP code")


class UseBackupCodeRequest(BaseModel):
    """Request to use a backup code instead of TOTP"""
    backup_code: str = Field(..., description="8-character backup code (format: XXXX-XXXX)")


class DisableTwoFactorRequest(BaseModel):
    """Request to disable 2FA - requires password confirmation"""
    password: str = Field(..., min_length=1, description="Current password for verification")


class TwoFactorStatusResponse(BaseModel):
    """Response model for 2FA status"""
    enabled: bool
    setup_pending: bool = False
    backup_codes_remaining: int = 0
    enabled_at: Optional[str] = None


# ============== Endpoints ==============

@router.get("/status", response_model=TwoFactorStatusResponse)
async def get_2fa_status(current_user: dict = Depends(get_current_user)):
    """Get current 2FA status for the authenticated user"""
    two_factor = current_user.get("two_factor", {})
    
    return TwoFactorStatusResponse(
        enabled=two_factor.get("enabled", False),
        setup_pending=two_factor.get("setup_pending", False),
        backup_codes_remaining=len(two_factor.get("backup_codes_hashed", [])),
        enabled_at=two_factor.get("enabled_at")
    )


@router.post("/enable", response_model=EnableTwoFactorResponse)
async def enable_2fa(
    request: EnableTwoFactorRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Initiate 2FA setup for the authenticated user.
    Returns QR code, secret key for manual entry, and backup codes.
    User must verify with a TOTP code to complete setup.
    """
    # Check if 2FA is already enabled
    if current_user.get("two_factor", {}).get("enabled"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Two-factor authentication is already enabled"
        )
    
    # Verify password
    if not verify_password(request.password, current_user.get("password", "")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid password"
        )
    
    # Generate 2FA setup data
    setup_data = TwoFactorManager.setup_2fa(current_user["email"])
    
    # Store pending setup in database (not enabled yet)
    await db.users.update_one(
        {"id": current_user["id"]},
        {
            "$set": {
                "two_factor.setup_pending": True,
                "two_factor.pending_secret": setup_data["secret"],
                "two_factor.pending_backup_codes_hashed": setup_data["backup_codes_hashed"],
                "two_factor.setup_initiated_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    logger.info(f"2FA setup initiated for user {current_user['id']}")
    
    return EnableTwoFactorResponse(
        qr_code_url=setup_data["qr_code_url"],
        secret_key=setup_data["secret"],
        backup_codes=setup_data["backup_codes"],
        message="Scan the QR code with your authenticator app and enter the 6-digit code to complete setup"
    )


@router.post("/verify-setup")
async def verify_2fa_setup(
    request: VerifyTwoFactorSetupRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Verify TOTP code to complete 2FA setup.
    This endpoint confirms that the user has successfully configured their authenticator app.
    """
    two_factor = current_user.get("two_factor", {})
    
    # Check if there's a pending setup
    if not two_factor.get("setup_pending"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No pending 2FA setup found. Please initiate setup first."
        )
    
    pending_secret = two_factor.get("pending_secret")
    if not pending_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Setup data not found. Please initiate setup again."
        )
    
    # Verify the TOTP code
    if not TOTPService.verify_token(pending_secret, request.totp_code):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid TOTP code. Please try again with the code from your authenticator app."
        )
    
    # Activate 2FA
    await db.users.update_one(
        {"id": current_user["id"]},
        {
            "$set": {
                "two_factor.enabled": True,
                "two_factor.secret": pending_secret,
                "two_factor.backup_codes_hashed": two_factor.get("pending_backup_codes_hashed", []),
                "two_factor.enabled_at": datetime.now(timezone.utc).isoformat(),
                "two_factor.setup_pending": False
            },
            "$unset": {
                "two_factor.pending_secret": "",
                "two_factor.pending_backup_codes_hashed": "",
                "two_factor.setup_initiated_at": ""
            }
        }
    )
    
    # Create audit log
    await create_audit_log(
        action="2FA_ENABLED",
        entity_type="user",
        entity_id=current_user["id"],
        user_id=current_user["id"],
        user_name=current_user["name"],
        user_role=current_user.get("role", 7),
        entity_name=current_user["name"],
        details={"method": "totp"}
    )
    
    logger.info(f"2FA successfully enabled for user {current_user['id']}")
    
    return {
        "message": "Two-factor authentication has been successfully enabled",
        "status": "enabled"
    }


@router.post("/verify")
async def verify_2fa_code(
    request: VerifyTwoFactorLoginRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Verify TOTP code during login or for sensitive operations.
    """
    two_factor = current_user.get("two_factor", {})
    
    if not two_factor.get("enabled"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Two-factor authentication is not enabled for this account"
        )
    
    secret = two_factor.get("secret")
    if not secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="2FA configuration error. Please contact support."
        )
    
    # Verify the TOTP code
    if not TOTPService.verify_token(secret, request.totp_code):
        # Log failed attempt
        await create_audit_log(
            action="2FA_VERIFY_FAILED",
            entity_type="user",
            entity_id=current_user["id"],
            user_id=current_user["id"],
            user_name=current_user["name"],
            user_role=current_user.get("role", 7),
            entity_name=current_user["name"]
        )
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired TOTP code"
        )
    
    # Update last verified timestamp
    await db.users.update_one(
        {"id": current_user["id"]},
        {
            "$set": {
                "two_factor.last_verified_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    logger.info(f"2FA code verified for user {current_user['id']}")
    
    return {
        "message": "Two-factor authentication verified successfully",
        "verified": True
    }


@router.post("/use-backup-code")
async def use_backup_code(
    request: UseBackupCodeRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Use a backup code for authentication when TOTP is unavailable.
    Backup codes are one-time use only.
    """
    two_factor = current_user.get("two_factor", {})
    
    if not two_factor.get("enabled"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Two-factor authentication is not enabled for this account"
        )
    
    stored_codes = two_factor.get("backup_codes_hashed", [])
    if not stored_codes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No backup codes available. Please generate new codes."
        )
    
    # Verify backup code
    is_valid, used_index = TwoFactorManager.verify_backup_code(
        request.backup_code,
        stored_codes
    )
    
    if not is_valid:
        # Log failed attempt
        await create_audit_log(
            action="2FA_BACKUP_CODE_FAILED",
            entity_type="user",
            entity_id=current_user["id"],
            user_id=current_user["id"],
            user_name=current_user["name"],
            user_role=current_user.get("role", 7),
            entity_name=current_user["name"]
        )
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid backup code"
        )
    
    # Remove used backup code (one-time use)
    remaining_codes = stored_codes[:used_index] + stored_codes[used_index + 1:]
    
    await db.users.update_one(
        {"id": current_user["id"]},
        {
            "$set": {
                "two_factor.backup_codes_hashed": remaining_codes,
                "two_factor.last_backup_code_used_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    # Log successful use
    await create_audit_log(
        action="2FA_BACKUP_CODE_USED",
        entity_type="user",
        entity_id=current_user["id"],
        user_id=current_user["id"],
        user_name=current_user["name"],
        user_role=current_user.get("role", 7),
        entity_name=current_user["name"],
        details={"remaining_codes": len(remaining_codes)}
    )
    
    logger.info(f"Backup code used by user {current_user['id']}, {len(remaining_codes)} codes remaining")
    
    return {
        "message": "Backup code accepted",
        "verified": True,
        "remaining_backup_codes": len(remaining_codes)
    }


@router.post("/regenerate-backup-codes")
async def regenerate_backup_codes(
    request: EnableTwoFactorRequest,  # Requires password confirmation
    current_user: dict = Depends(get_current_user)
):
    """
    Generate new backup codes. This invalidates all previous backup codes.
    Requires password confirmation.
    """
    two_factor = current_user.get("two_factor", {})
    
    if not two_factor.get("enabled"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Two-factor authentication is not enabled"
        )
    
    # Verify password
    if not verify_password(request.password, current_user.get("password", "")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid password"
        )
    
    # Generate new backup codes
    backup_codes = BackupCodeService.generate_backup_codes()
    backup_codes_hashed = [BackupCodeService.hash_backup_code(code) for code in backup_codes]
    
    # Update database
    await db.users.update_one(
        {"id": current_user["id"]},
        {
            "$set": {
                "two_factor.backup_codes_hashed": backup_codes_hashed,
                "two_factor.backup_codes_regenerated_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    # Log regeneration
    await create_audit_log(
        action="2FA_BACKUP_CODES_REGENERATED",
        entity_type="user",
        entity_id=current_user["id"],
        user_id=current_user["id"],
        user_name=current_user["name"],
        user_role=current_user.get("role", 7),
        entity_name=current_user["name"]
    )
    
    logger.info(f"Backup codes regenerated for user {current_user['id']}")
    
    return {
        "message": "New backup codes generated. Save them securely - previous codes are now invalid.",
        "backup_codes": backup_codes
    }


@router.post("/disable")
async def disable_2fa(
    request: DisableTwoFactorRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Disable 2FA for the authenticated user.
    Requires password confirmation.
    """
    two_factor = current_user.get("two_factor", {})
    
    if not two_factor.get("enabled"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Two-factor authentication is not enabled"
        )
    
    # Verify password
    if not verify_password(request.password, current_user.get("password", "")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid password"
        )
    
    # Disable 2FA
    await db.users.update_one(
        {"id": current_user["id"]},
        {
            "$set": {
                "two_factor.enabled": False,
                "two_factor.disabled_at": datetime.now(timezone.utc).isoformat()
            },
            "$unset": {
                "two_factor.secret": "",
                "two_factor.backup_codes_hashed": ""
            }
        }
    )
    
    # Log disabling
    await create_audit_log(
        action="2FA_DISABLED",
        entity_type="user",
        entity_id=current_user["id"],
        user_id=current_user["id"],
        user_name=current_user["name"],
        user_role=current_user.get("role", 7),
        entity_name=current_user["name"]
    )
    
    logger.info(f"2FA disabled for user {current_user['id']}")
    
    return {
        "message": "Two-factor authentication has been disabled",
        "status": "disabled"
    }


@router.get("/check-required")
async def check_2fa_required(current_user: dict = Depends(get_current_user)):
    """
    Check if 2FA verification is required for the current session.
    Used after initial login to determine if 2FA prompt should be shown.
    """
    two_factor = current_user.get("two_factor", {})
    
    return {
        "two_factor_enabled": two_factor.get("enabled", False),
        "two_factor_required": two_factor.get("enabled", False)
    }
