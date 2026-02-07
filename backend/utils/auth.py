"""
Authentication utilities
"""
import bcrypt
import jwt
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from config import JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRATION_HOURS, ROLE_PERMISSIONS
from database import db

security = HTTPBearer()


def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against its hash"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))


def create_token(user_id: str, email: str) -> str:
    """Create JWT token"""
    expiration = datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS)
    payload = {
        'user_id': user_id,
        'email': email,
        'exp': expiration
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def create_proxy_token(
    target_user_id: str, 
    target_user_email: str,
    proxy_user_id: str,
    proxy_user_email: str,
    proxy_user_name: str
) -> str:
    """Create JWT token for proxy login session"""
    expiration = datetime.now(timezone.utc) + timedelta(hours=8)  # Shorter expiration for proxy
    payload = {
        'user_id': target_user_id,
        'email': target_user_email,
        'is_proxy': True,
        'proxy_info': {
            'proxy_user_id': proxy_user_id,
            'proxy_user_email': proxy_user_email,
            'proxy_user_name': proxy_user_name
        },
        'exp': expiration
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """Decode and verify JWT token, return payload"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise Exception("Token has expired")
    except jwt.InvalidTokenError as e:
        raise Exception(f"Invalid token: {str(e)}")


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current user from JWT token (includes proxy session support)"""
    try:
        token = credentials.credentials
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get('user_id')
        
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        user = await db.users.find_one({"id": user_id}, {"_id": 0})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        
        # Check if this is a proxy session
        if payload.get('is_proxy'):
            user['proxy_info'] = payload.get('proxy_info')
            user['is_proxy_session'] = True
        
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


def check_permission(user: dict, required_permission: str):
    """Check if user has required permission"""
    user_role = user.get("role", 5)
    permissions = ROLE_PERMISSIONS.get(user_role, [])
    
    if "all" in permissions:
        return True
    
    if required_permission in permissions:
        return True
    
    raise HTTPException(status_code=403, detail="Insufficient permissions")


def require_role(min_role: int):
    """Decorator to require minimum role level"""
    async def role_checker(current_user: dict = Depends(get_current_user)):
        if current_user.get("role", 5) > min_role:
            raise HTTPException(status_code=403, detail="Insufficient role permissions")
        return current_user
    return role_checker
