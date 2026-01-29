"""
Kill Switch Middleware
Blocks all API requests when kill switch is active (except allowed endpoints)
"""
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import jwt
import os

from database import db

# Endpoints that are always allowed even when kill switch is active
ALLOWED_ENDPOINTS = [
    "/api/kill-switch/status",
    "/api/kill-switch/activate",
    "/api/kill-switch/deactivate",
    "/api/auth/login",
    "/api/auth/me",
    "/api/users/heartbeat",
    "/api/users/pe-status",
    "/api/health",
    "/api/ws/notifications",
]

# Endpoints that start with these prefixes are allowed
ALLOWED_PREFIXES = [
    "/api/uploads/",  # Static files
]


class KillSwitchMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Skip for non-API routes
        if not request.url.path.startswith("/api"):
            return await call_next(request)
        
        # Always allow certain endpoints
        if request.url.path in ALLOWED_ENDPOINTS:
            return await call_next(request)
        
        # Allow endpoints with certain prefixes
        for prefix in ALLOWED_PREFIXES:
            if request.url.path.startswith(prefix):
                return await call_next(request)
        
        # Check kill switch status
        try:
            status = await db.system_settings.find_one({"setting": "kill_switch"}, {"_id": 0})
            
            if status and status.get("is_active"):
                # Check if user is PE Desk (role 1) - they can still access the system
                auth_header = request.headers.get("Authorization")
                if auth_header and auth_header.startswith("Bearer "):
                    token = auth_header.split(" ")[1]
                    try:
                        payload = jwt.decode(
                            token, 
                            os.environ.get("JWT_SECRET", "your-secret-key"),
                            algorithms=["HS256"]
                        )
                        user_id = payload.get("user_id")
                        if user_id:
                            user = await db.users.find_one({"id": user_id}, {"_id": 0, "role": 1})
                            if user and user.get("role") == 1:
                                # PE Desk can access everything
                                return await call_next(request)
                    except:
                        pass
                
                # System is frozen for this user
                return JSONResponse(
                    status_code=503,
                    content={
                        "detail": "System is temporarily frozen",
                        "kill_switch_active": True,
                        "activated_by": status.get("activated_by_name"),
                        "reason": status.get("reason")
                    }
                )
        except Exception as e:
            # If we can't check, allow the request (fail open for safety)
            pass
        
        return await call_next(request)
