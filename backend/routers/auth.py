"""
Authentication routes
Handles user registration, login, SSO, password management
"""
import uuid
import bcrypt
import secrets
import string
import logging
import asyncio
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)
from fastapi import APIRouter, HTTPException, Depends, Request, Body

from database import db
from config import (
    ROLES, ALLOWED_EMAIL_DOMAINS, OTP_EXPIRY_MINUTES, OTP_MAX_ATTEMPTS
)
from models import (
    UserCreate, UserLogin, User, TokenResponse, ChangePassword,
    PasswordResetRequest, PasswordResetVerify
)
from utils.auth import (
    hash_password, verify_password, create_token, get_current_user
)
from services.email_service import generate_otp, send_otp_email, send_email
from services.audit_service import create_audit_log

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register")
async def register(user_data: UserCreate, request: Request = None):
    """
    Register a new employee. Password is auto-generated and sent via email.
    PAN is required for all users except superadmin (pe@smifs.com).
    """
    # Check email domain restriction
    email_domain = user_data.email.split('@')[-1].lower()
    if email_domain not in ALLOWED_EMAIL_DOMAINS:
        raise HTTPException(
            status_code=400, 
            detail="Registration is restricted to employees with @smifs.com email addresses"
        )
    
    existing_user = await db.users.find_one({"email": user_data.email}, {"_id": 0})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Superadmin check - pe@smifs.com doesn't need PAN
    is_superadmin = user_data.email.lower() == "pe@smifs.com"
    
    pan_number = None
    if not is_superadmin:
        # PAN is required for non-superadmin users
        if not user_data.pan_number:
            raise HTTPException(status_code=400, detail="PAN number is required for employee registration")
        
        pan_number = user_data.pan_number.upper().strip()
        if len(pan_number) != 10:
            raise HTTPException(status_code=400, detail="PAN number must be exactly 10 characters")
        
        # Check for duplicate PAN among users
        existing_pan_user = await db.users.find_one({"pan_number": pan_number}, {"_id": 0, "name": 1, "email": 1})
        if existing_pan_user:
            raise HTTPException(
                status_code=400, 
                detail="PAN number already registered with another employee account"
            )
        
        # STRICT RULE: Employee cannot be an RP - Check by PAN
        existing_rp = await db.referral_partners.find_one(
            {"pan_number": pan_number},
            {"_id": 0, "name": 1, "rp_code": 1}
        )
        if existing_rp:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot register: This PAN ({pan_number}) belongs to an existing Referral Partner ({existing_rp.get('name', 'Unknown')} - {existing_rp.get('rp_code', '')}). An RP cannot be an Employee."
            )
        
        # STRICT RULE: Employee cannot be a Client - Check by PAN
        existing_client = await db.clients.find_one(
            {"pan_number": pan_number},
            {"_id": 0, "name": 1, "otc_ucc": 1}
        )
        if existing_client:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot register: This PAN ({pan_number}) belongs to an existing Client ({existing_client.get('name', 'Unknown')} - {existing_client.get('otc_ucc', '')}). A Client cannot be an Employee."
            )
    
    # Generate random password (12 chars with letters, digits, and special chars)
    alphabet = string.ascii_letters + string.digits + "!@#$%"
    random_password = ''.join(secrets.choice(alphabet) for _ in range(12))
    
    user_id = str(uuid.uuid4())
    hashed_pw = hash_password(random_password)
    
    # Set role: Superadmin (1) for pe@smifs.com, Employee (5) for others
    user_role = 1 if is_superadmin else 5
    
    user_doc = {
        "id": user_id,
        "email": user_data.email.lower(),
        "password": hashed_pw,
        "name": user_data.name,
        "pan_number": pan_number,
        "role": user_role,
        "must_change_password": True,  # Force password change on first login
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.users.insert_one(user_doc)
    
    # Send welcome email with password
    try:
        subject = "Welcome to SMIFS Private Equity - Your Account Credentials"
        body = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #064E3B;">Welcome to SMIFS Private Equity</h2>
            <p>Dear {user_data.name},</p>
            <p>Your employee account has been created successfully.</p>
            
            <div style="background-color: #f3f4f6; border-radius: 8px; padding: 20px; margin: 20px 0;">
                <h3 style="margin-top: 0; color: #064E3B;">Your Login Credentials</h3>
                <table style="width: 100%;">
                    <tr>
                        <td style="padding: 8px 0;"><strong>Email:</strong></td>
                        <td style="padding: 8px 0;">{user_data.email}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0;"><strong>Temporary Password:</strong></td>
                        <td style="padding: 8px 0; font-family: monospace; font-size: 16px; color: #dc2626; background-color: #fef2f2; padding: 8px; border-radius: 4px;">{random_password}</td>
                    </tr>
                </table>
            </div>
            
            <div style="background-color: #fef3c7; border-left: 4px solid #f59e0b; padding: 12px; margin: 20px 0;">
                <p style="margin: 0; color: #92400e;"><strong>Important:</strong> Please change your password immediately after your first login for security purposes.</p>
            </div>
            
            <p>Best regards,<br><strong>SMIFS Private Equity System</strong></p>
        </div>
        """
        await send_email(user_data.email, subject, body)
    except Exception as e:
        # Log error but don't fail registration
        print(f"Failed to send welcome email: {e}")
    
    # Create audit log
    await create_audit_log(
        action="USER_REGISTER",
        entity_type="user",
        entity_id=user_id,
        user_id=user_id,
        user_name=user_data.name,
        user_role=user_role,
        entity_name=user_data.name,
        details={"email": user_data.email, "role": user_role, "pan_number": pan_number, "is_superadmin": is_superadmin}
    )
    
    return {
        "message": f"Account created successfully. Login credentials have been sent to {user_data.email}",
        "email": user_data.email
    }


from middleware.security import login_tracker, SecurityAuditLogger
from services.captcha_service import captcha_service, SecurityAlertService

@router.post("/login", response_model=TokenResponse)
async def login(
    login_data: UserLogin, 
    request: Request = None,
    captcha_token: str = None,
    captcha_answer: str = None
):
    """Login user and return JWT token"""
    email = login_data.email.lower().strip()
    
    # Get client IP for security tracking
    client_ip = "unknown"
    user_agent = "unknown"
    if request:
        client_ip = request.headers.get("X-Forwarded-For", "").split(",")[0].strip() or \
                    request.headers.get("X-Real-IP", "") or \
                    (request.client.host if request.client else "unknown")
        user_agent = request.headers.get("User-Agent", "unknown")
    
    # Check if account is locked due to too many failed attempts
    is_locked, remaining_seconds = login_tracker.is_account_locked(email)
    if is_locked:
        await SecurityAuditLogger.log_security_event(
            "LOGIN_BLOCKED_LOCKED_ACCOUNT",
            client_ip,
            details={"email": email, "remaining_seconds": remaining_seconds}
        )
        raise HTTPException(
            status_code=423, 
            detail=f"Account temporarily locked due to too many failed attempts. Try again in {remaining_seconds // 60} minutes."
        )
    
    # Check if CAPTCHA is required (after 3 failed attempts)
    failed_attempts = login_tracker.get_failed_attempts_count(email)
    if failed_attempts >= 3:
        # CAPTCHA is required
        if not captcha_token or not captcha_answer:
            # Generate new CAPTCHA challenge
            challenge = captcha_service.generate_challenge(email)
            raise HTTPException(
                status_code=428,  # Precondition Required
                detail={
                    "message": "CAPTCHA verification required",
                    "captcha_required": True,
                    **challenge
                }
            )
        
        # Verify CAPTCHA
        is_valid, captcha_message = captcha_service.verify_challenge(captcha_token, captcha_answer, email)
        if not is_valid:
            raise HTTPException(
                status_code=400,
                detail=captcha_message
            )
    
    user = await db.users.find_one({"email": email}, {"_id": 0})
    
    if not user or not verify_password(login_data.password, user["password"]):
        # Record failed attempt with IP
        remaining_attempts = login_tracker.record_failed_attempt(email, client_ip)
        
        await SecurityAuditLogger.log_security_event(
            "LOGIN_FAILED",
            client_ip,
            details={"email": email, "remaining_attempts": remaining_attempts}
        )
        
        # Check if CAPTCHA will be required next time
        new_failed_count = login_tracker.get_failed_attempts_count(email)
        response_detail = f"Invalid email or password. {remaining_attempts} attempts remaining."
        
        if new_failed_count >= 3 and remaining_attempts > 0:
            # Generate CAPTCHA for next attempt
            challenge = captcha_service.generate_challenge(email)
            raise HTTPException(
                status_code=401,
                detail={
                    "message": response_detail,
                    "captcha_required": True,
                    **challenge
                }
            )
        elif remaining_attempts > 0:
            raise HTTPException(status_code=401, detail=response_detail)
        else:
            raise HTTPException(
                status_code=401, 
                detail="Invalid email or password. Account has been temporarily locked."
            )
    
    # Clear failed attempts on successful login
    login_tracker.clear_attempts(email)
    
    # Log successful login
    await SecurityAuditLogger.log_security_event(
        "LOGIN_SUCCESS",
        client_ip,
        user_id=user["id"],
        details={"email": email}
    )
    
    # Check login location for unusual activity (async)
    try:
        from services.geolocation_service import UnusualLoginDetector
        location_check = await UnusualLoginDetector.check_login_location(
            user_id=user["id"],
            user_email=email,
            ip_address=client_ip,
            user_agent=user_agent
        )
        
        # If unusual login detected, send enhanced alert
        if location_check.get("is_unusual"):
            asyncio.create_task(
                SecurityAlertService.send_unusual_login_alert(
                    user_email=email,
                    user_name=user["name"],
                    ip_address=client_ip,
                    user_agent=user_agent,
                    location_data=location_check
                )
            )
    except Exception as e:
        logger.error(f"Failed to check login location: {e}")
    
    # Send login notification email to user (async)
    try:
        asyncio.create_task(
            SecurityAlertService.send_new_login_alert(
                user_email=email,
                user_name=user["name"],
                ip_address=client_ip,
                user_agent=user_agent
            )
        )
    except Exception as e:
        logger.error(f"Failed to send login notification: {e}")
    
    # Create audit log for login
    await create_audit_log(
        action="USER_LOGIN",
        entity_type="user",
        entity_id=user["id"],
        user_id=user["id"],
        user_name=user["name"],
        user_role=user.get("role", 5),
        entity_name=user["name"]
    )
    
    token = create_token(user["id"], user["email"])
    user_response = User(
        id=user["id"],
        email=user["email"],
        name=user["name"],
        pan_number=user.get("pan_number"),
        role=user.get("role", 5),
        role_name=ROLES.get(user.get("role", 5), "Viewer"),
        created_at=user["created_at"],
        agreement_accepted=user.get("agreement_accepted", False),
        agreement_accepted_at=user.get("agreement_accepted_at")
    )
    
    return TokenResponse(token=token, user=user_response)


@router.get("/me", response_model=User)
async def get_me(current_user: dict = Depends(get_current_user)):
    """Get current user info"""
    return User(
        id=current_user["id"],
        email=current_user["email"],
        name=current_user["name"],
        pan_number=current_user.get("pan_number"),
        role=current_user.get("role", 5),
        role_name=ROLES.get(current_user.get("role", 5), "Viewer"),
        created_at=current_user["created_at"]
    )


@router.post("/change-password")
async def change_password(data: ChangePassword, current_user: dict = Depends(get_current_user)):
    """
    Change password for logged-in user.
    Requires current password verification.
    """
    # Verify current password
    if not verify_password(data.current_password, current_user["password"]):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    
    # Validate new password length
    if len(data.new_password) < 8:
        raise HTTPException(status_code=400, detail="New password must be at least 8 characters")
    
    # Hash new password
    hashed_new_pw = hash_password(data.new_password)
    
    # Update password and clear must_change_password flag
    await db.users.update_one(
        {"id": current_user["id"]},
        {
            "$set": {
                "password": hashed_new_pw,
                "must_change_password": False,
                "password_changed_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    # Create audit log
    await create_audit_log(
        action="PASSWORD_CHANGE",
        entity_type="user",
        entity_id=current_user["id"],
        user_id=current_user["id"],
        user_name=current_user["name"],
        user_role=current_user.get("role", 5),
        entity_name=current_user["name"],
        details={"method": "change_password"}
    )
    
    return {"message": "Password changed successfully"}


# ============== SSO Authentication Endpoints ==============

@router.get("/sso/config")
async def get_sso_config():
    """Get SSO configuration for frontend"""
    from services.azure_sso_service import AzureSSOService
    sso_service = AzureSSOService(db)
    return sso_service.get_sso_config()


@router.post("/sso/login")
async def sso_login(token: str = Body(..., embed=True)):
    """
    Authenticate user via Microsoft SSO token.
    Creates new user as Employee if not exists.
    """
    from services.azure_sso_service import AzureSSOService
    
    sso_service = AzureSSOService(db)
    
    if not sso_service.is_sso_enabled():
        raise HTTPException(
            status_code=400,
            detail="SSO is not configured. Please contact administrator."
        )
    
    # Validate token and get/create user
    user = await sso_service.authenticate_sso_token(token)
    
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid SSO token or authentication failed"
        )
    
    # Create local JWT token for the session
    local_token = create_token(user["id"], user["email"])
    
    # Create audit log
    await create_audit_log(
        action="SSO_LOGIN",
        entity_type="user",
        entity_id=user["id"],
        user_id=user["id"],
        user_name=user["name"],
        user_role=user.get("role", 4),
        entity_name=user["name"],
        details={"email": user["email"], "auth_method": "azure_sso"}
    )
    
    user_response = User(
        id=user["id"],
        email=user["email"],
        name=user["name"],
        pan_number=user.get("pan_number"),
        role=user.get("role", 4),
        role_name=ROLES.get(user.get("role", 4), "Employee"),
        created_at=user["created_at"]
    )
    
    return TokenResponse(token=local_token, user=user_response)


@router.post("/forgot-password")
async def forgot_password(data: PasswordResetRequest):
    """Request password reset OTP"""
    user = await db.users.find_one({"email": data.email.lower()})
    if not user:
        # Don't reveal if email exists
        return {"message": "If the email exists, an OTP has been sent"}
    
    # Check rate limiting
    recent_otps = await db.password_resets.count_documents({
        "email": data.email.lower(),
        "created_at": {"$gte": datetime.now(timezone.utc) - timedelta(minutes=OTP_EXPIRY_MINUTES)}
    })
    
    if recent_otps >= OTP_MAX_ATTEMPTS:
        raise HTTPException(status_code=429, detail="Too many OTP requests. Please try again later.")
    
    # Generate OTP
    otp = generate_otp()
    
    # Store OTP
    await db.password_resets.insert_one({
        "id": str(uuid.uuid4()),
        "email": data.email.lower(),
        "otp": otp,
        "attempts": 0,
        "used": False,
        "created_at": datetime.now(timezone.utc),
        "expires_at": datetime.now(timezone.utc) + timedelta(minutes=OTP_EXPIRY_MINUTES)
    })
    
    # Send email
    await send_otp_email(data.email, otp, user["name"])
    
    return {"message": "If the email exists, an OTP has been sent"}


@router.post("/reset-password")
async def reset_password(data: PasswordResetVerify, request: Request):
    """Reset password with OTP verification"""
    # Find valid OTP
    otp_record = await db.password_resets.find_one({
        "email": data.email.lower(),
        "otp": data.otp,
        "used": False,
        "expires_at": {"$gte": datetime.now(timezone.utc)}
    })
    
    if not otp_record:
        # Increment attempts for any matching unused OTP
        await db.password_resets.update_many(
            {"email": data.email.lower(), "used": False},
            {"$inc": {"attempts": 1}}
        )
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")
    
    # Check attempts
    if otp_record.get("attempts", 0) >= OTP_MAX_ATTEMPTS:
        raise HTTPException(status_code=400, detail="Too many failed attempts. Please request a new OTP.")
    
    # Mark OTP as used
    await db.password_resets.update_one(
        {"id": otp_record["id"]},
        {"$set": {"used": True}}
    )
    
    # Update password
    user = await db.users.find_one({"email": data.email.lower()})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    hashed = bcrypt.hashpw(data.new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    await db.users.update_one(
        {"email": data.email.lower()},
        {"$set": {"password": hashed}}
    )
    
    # Create audit log
    await create_audit_log(
        action="USER_PASSWORD_RESET",
        entity_type="user",
        entity_id=user["id"],
        user_id=user["id"],
        user_name=user["name"],
        user_role=user["role"],
        ip_address=request.client.host if request.client else None
    )
    
    return {"message": "Password reset successfully"}



# ============== Proxy Login (PE Desk Only) ==============

class ProxyLoginRequest(BaseModel):
    target_user_id: str

from pydantic import BaseModel

@router.post("/proxy-login")
async def proxy_login(
    data: ProxyLoginRequest,
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """
    PE Desk can log in as any other user to view/manage their account.
    Creates a special token that includes proxy information.
    """
    # Only PE Desk (role 1) can use proxy login
    if current_user.get("role", 6) != 1:
        raise HTTPException(status_code=403, detail="Only PE Desk can use proxy login")
    
    # Get target user
    target_user = await db.users.find_one({"id": data.target_user_id}, {"_id": 0, "password": 0})
    if not target_user:
        raise HTTPException(status_code=404, detail="Target user not found")
    
    # Cannot proxy as yourself
    if target_user["id"] == current_user["id"]:
        raise HTTPException(status_code=400, detail="Cannot proxy as yourself")
    
    # Create audit log
    await create_audit_log(
        action="PROXY_LOGIN",
        entity_type="user",
        entity_id=target_user["id"],
        user_id=current_user["id"],
        user_name=current_user["name"],
        user_role=current_user.get("role", 1),
        entity_name=target_user["name"],
        details={
            "proxy_as": target_user["email"],
            "proxy_as_name": target_user["name"],
            "proxy_as_role": target_user.get("role")
        },
        ip_address=request.client.host if request.client else None
    )
    
    # Create token with proxy information embedded
    from utils.auth import create_proxy_token
    token = create_proxy_token(
        target_user_id=target_user["id"],
        target_user_email=target_user["email"],
        proxy_user_id=current_user["id"],
        proxy_user_email=current_user["email"],
        proxy_user_name=current_user["name"]
    )
    
    # Return proxy session info
    return {
        "token": token,
        "user": {
            "id": target_user["id"],
            "email": target_user["email"],
            "name": target_user["name"],
            "role": target_user.get("role", 5),
            "role_name": ROLES.get(target_user.get("role", 5), "Viewer"),
            "pan_number": target_user.get("pan_number"),
            "created_at": target_user.get("created_at"),
            "agreement_accepted": target_user.get("agreement_accepted", False)
        },
        "proxy_session": {
            "is_proxy": True,
            "original_user": {
                "id": current_user["id"],
                "email": current_user["email"],
                "name": current_user["name"],
                "role": current_user.get("role", 1),
                "role_name": ROLES.get(current_user.get("role", 1), "PE Desk")
            }
        }
    }


@router.post("/proxy-logout")
async def proxy_logout(
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """
    End proxy session and return to original PE Desk account.
    """
    # Check if this is a proxy session
    proxy_info = current_user.get("proxy_info")
    if not proxy_info:
        raise HTTPException(status_code=400, detail="Not in a proxy session")
    
    # Get the original PE Desk user
    original_user = await db.users.find_one(
        {"id": proxy_info.get("proxy_user_id")}, 
        {"_id": 0, "password": 0}
    )
    if not original_user:
        raise HTTPException(status_code=404, detail="Original user not found")
    
    # Create audit log
    await create_audit_log(
        action="PROXY_LOGOUT",
        entity_type="user",
        entity_id=current_user["id"],
        user_id=proxy_info.get("proxy_user_id"),
        user_name=proxy_info.get("proxy_user_name"),
        user_role=1,
        entity_name=current_user["name"],
        details={
            "ended_proxy_as": current_user["email"],
            "ended_proxy_as_name": current_user["name"]
        },
        ip_address=request.client.host if request.client else None
    )
    
    # Create fresh token for original user
    from utils.auth import create_token
    token = create_token(original_user["id"], original_user["email"])
    
    return {
        "token": token,
        "user": {
            "id": original_user["id"],
            "email": original_user["email"],
            "name": original_user["name"],
            "role": original_user.get("role", 1),
            "role_name": ROLES.get(original_user.get("role", 1), "PE Desk"),
            "pan_number": original_user.get("pan_number"),
            "created_at": original_user.get("created_at"),
            "agreement_accepted": original_user.get("agreement_accepted", False)
        },
        "message": "Proxy session ended"
    }


@router.get("/proxy-status")
async def get_proxy_status(current_user: dict = Depends(get_current_user)):
    """
    Check if current session is a proxy session.
    """
    proxy_info = current_user.get("proxy_info")
    
    if proxy_info:
        return {
            "is_proxy": True,
            "viewing_as": {
                "id": current_user["id"],
                "email": current_user["email"],
                "name": current_user["name"],
                "role": current_user.get("role"),
                "role_name": ROLES.get(current_user.get("role", 5), "Viewer")
            },
            "original_user": {
                "id": proxy_info.get("proxy_user_id"),
                "email": proxy_info.get("proxy_user_email"),
                "name": proxy_info.get("proxy_user_name"),
                "role": 1,
                "role_name": "PE Desk"
            }
        }
    
    return {
        "is_proxy": False,
        "current_user": {
            "id": current_user["id"],
            "email": current_user["email"],
            "name": current_user["name"],
            "role": current_user.get("role"),
            "role_name": ROLES.get(current_user.get("role", 5), "Viewer")
        }
    }
