"""
Authentication routes
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from datetime import datetime, timezone, timedelta
import uuid
import logging

from database import db
from config import ROLES, ALLOWED_EMAIL_DOMAINS, AUDIT_ACTIONS, OTP_EXPIRY_MINUTES, OTP_MAX_ATTEMPTS
from models import UserCreate, UserLogin, User, TokenResponse, PasswordResetRequest, PasswordResetVerify
from utils.auth import hash_password, verify_password, create_token, get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])

async def create_audit_log(action, entity_type, entity_id, user_id, user_name, user_role, entity_name=None, details=None, ip_address=None):
    """Create audit log entry"""
    try:
        audit_doc = {
            "id": str(uuid.uuid4()),
            "action": action,
            "action_description": AUDIT_ACTIONS.get(action, action),
            "entity_type": entity_type,
            "entity_id": entity_id,
            "entity_name": entity_name,
            "user_id": user_id,
            "user_name": user_name,
            "user_role": user_role,
            "details": details,
            "ip_address": ip_address,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        await db.audit_logs.insert_one(audit_doc)
    except Exception as e:
        logging.error(f"Failed to create audit log: {e}")

@router.post("/register", response_model=TokenResponse)
async def register(user_data: UserCreate, request: Request):
    """Register a new user"""
    # Check email domain
    email_domain = user_data.email.split('@')[-1].lower()
    if email_domain not in ALLOWED_EMAIL_DOMAINS:
        raise HTTPException(status_code=400, detail=f"Registration restricted to {', '.join(ALLOWED_EMAIL_DOMAINS)} domain")
    
    # Check if email already exists
    existing = await db.users.find_one({"email": user_data.email.lower()})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user_id = str(uuid.uuid4())
    role = 4  # Default to Employee for domain users
    
    user_doc = {
        "id": user_id,
        "email": user_data.email.lower(),
        "name": user_data.name,
        "hashed_password": hash_password(user_data.password),
        "role": role,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.users.insert_one(user_doc)
    
    # Create audit log
    await create_audit_log(
        "USER_REGISTER", "user", user_id, user_id, user_data.name, role,
        ip_address=request.client.host if request.client else None
    )
    
    token = create_token(user_id, user_data.email, role)
    user = User(
        id=user_id,
        email=user_data.email,
        name=user_data.name,
        role=role,
        role_name=ROLES.get(role, "Unknown"),
        created_at=user_doc["created_at"]
    )
    
    return TokenResponse(token=token, user=user)

@router.post("/login", response_model=TokenResponse)
async def login(user_data: UserLogin, request: Request):
    """Login user"""
    user = await db.users.find_one({"email": user_data.email.lower()})
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if not verify_password(user_data.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Create audit log
    await create_audit_log(
        "USER_LOGIN", "user", user["id"], user["id"], user["name"], user["role"],
        ip_address=request.client.host if request.client else None
    )
    
    token = create_token(user["id"], user["email"], user["role"])
    user_response = User(
        id=user["id"],
        email=user["email"],
        name=user["name"],
        role=user["role"],
        role_name=ROLES.get(user["role"], "Unknown"),
        created_at=user["created_at"]
    )
    
    return TokenResponse(token=token, user=user_response)

@router.get("/me", response_model=User)
async def get_me(current_user: dict = Depends(get_current_user)):
    """Get current user profile"""
    return User(**current_user)

@router.post("/forgot-password")
async def forgot_password(data: PasswordResetRequest):
    """Request password reset OTP"""
    from utils.email import generate_otp, send_otp_email
    
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
    
    await db.users.update_one(
        {"email": data.email.lower()},
        {"$set": {"hashed_password": hash_password(data.new_password)}}
    )
    
    # Create audit log
    await create_audit_log(
        "USER_PASSWORD_RESET", "user", user["id"], user["id"], user["name"], user["role"],
        ip_address=request.client.host if request.client else None
    )
    
    return {"message": "Password reset successfully"}
