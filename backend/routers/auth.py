"""
Authentication routes
Handles user registration, login, SSO, password management
"""
import uuid
import bcrypt
import secrets
import string
from datetime import datetime, timezone, timedelta
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
    PAN is required for all users except superadmin (pedesk@smifs.com).
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
    
    # Superadmin check - pedesk@smifs.com doesn't need PAN
    is_superadmin = user_data.email.lower() == "pedesk@smifs.com"
    
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
    
    # Set role: Superadmin (1) for pedesk@smifs.com, Employee (4) for others
    user_role = 1 if is_superadmin else 4
    
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


@router.post("/login", response_model=TokenResponse)
async def login(login_data: UserLogin):
    """Login user and return JWT token"""
    user = await db.users.find_one({"email": login_data.email}, {"_id": 0})
    if not user or not verify_password(login_data.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
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
        created_at=user["created_at"]
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
