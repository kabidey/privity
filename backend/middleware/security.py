"""
Security Middleware and Utilities
Provides comprehensive security features for the application
"""
import time
import hashlib
import re
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional
from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import logging

logger = logging.getLogger(__name__)

# ============== Rate Limiting ==============
class RateLimiter:
    """
    Token bucket rate limiter with sliding window
    """
    def __init__(self):
        self.requests: Dict[str, List[float]] = defaultdict(list)
        self.blocked_ips: Dict[str, float] = {}
        
    def is_rate_limited(self, identifier: str, max_requests: int = 100, window_seconds: int = 60) -> bool:
        """Check if identifier has exceeded rate limit"""
        now = time.time()
        window_start = now - window_seconds
        
        # Clean old requests
        self.requests[identifier] = [
            req_time for req_time in self.requests[identifier] 
            if req_time > window_start
        ]
        
        # Check rate limit
        if len(self.requests[identifier]) >= max_requests:
            return True
        
        # Record this request
        self.requests[identifier].append(now)
        return False
    
    def block_ip(self, ip: str, duration_seconds: int = 3600):
        """Block an IP address for a duration"""
        self.blocked_ips[ip] = time.time() + duration_seconds
        logger.warning(f"Blocked IP {ip} for {duration_seconds} seconds")
    
    def is_ip_blocked(self, ip: str) -> bool:
        """Check if IP is currently blocked"""
        if ip in self.blocked_ips:
            if time.time() < self.blocked_ips[ip]:
                return True
            else:
                del self.blocked_ips[ip]
        return False

# Global rate limiter instance
rate_limiter = RateLimiter()

# ============== Login Attempt Tracking ==============
class LoginAttemptTracker:
    """
    Track failed login attempts and lock accounts
    """
    def __init__(self):
        self.failed_attempts: Dict[str, List[float]] = defaultdict(list)
        self.locked_accounts: Dict[str, float] = {}
        self.max_attempts = 5
        self.lockout_duration = 900  # 15 minutes
        self.attempt_window = 300  # 5 minutes
        
    def record_failed_attempt(self, identifier: str, ip_address: str = None) -> int:
        """Record a failed login attempt, return remaining attempts"""
        now = time.time()
        window_start = now - self.attempt_window
        
        # Clean old attempts
        self.failed_attempts[identifier] = [
            attempt for attempt in self.failed_attempts[identifier]
            if attempt > window_start
        ]
        
        # Record this attempt
        self.failed_attempts[identifier].append(now)
        attempts = len(self.failed_attempts[identifier])
        
        # Lock account if max attempts exceeded
        if attempts >= self.max_attempts:
            self.locked_accounts[identifier] = now + self.lockout_duration
            logger.warning(f"Account locked due to too many failed attempts: {identifier}")
            
            # Send security alert email (async, fire and forget)
            import asyncio
            try:
                from services.captcha_service import SecurityAlertService
                asyncio.create_task(
                    SecurityAlertService.send_account_locked_alert(
                        email=identifier,
                        ip_address=ip_address or "unknown",
                        lockout_minutes=self.lockout_duration // 60
                    )
                )
            except Exception as e:
                logger.error(f"Failed to send account locked alert: {e}")
        
        return max(0, self.max_attempts - attempts)
    
    def get_failed_attempts_count(self, identifier: str) -> int:
        """Get current failed attempts count for an identifier"""
        now = time.time()
        window_start = now - self.attempt_window
        
        # Count attempts within window
        attempts = [
            attempt for attempt in self.failed_attempts.get(identifier, [])
            if attempt > window_start
        ]
        return len(attempts)
    
    def is_account_locked(self, identifier: str) -> tuple[bool, int]:
        """Check if account is locked, return (is_locked, remaining_seconds)"""
        if identifier in self.locked_accounts:
            remaining = self.locked_accounts[identifier] - time.time()
            if remaining > 0:
                return True, int(remaining)
            else:
                del self.locked_accounts[identifier]
                self.failed_attempts[identifier] = []
        return False, 0
    
    def clear_attempts(self, identifier: str):
        """Clear failed attempts after successful login"""
        if identifier in self.failed_attempts:
            del self.failed_attempts[identifier]
        if identifier in self.locked_accounts:
            del self.locked_accounts[identifier]

# Global login tracker instance
login_tracker = LoginAttemptTracker()

# ============== Input Sanitization ==============
class InputSanitizer:
    """
    Sanitize and validate user inputs
    """
    # Patterns for potential attacks
    SQL_INJECTION_PATTERNS = [
        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|UNION|ALTER|CREATE|TRUNCATE)\b)",
        r"(--|;|/\*|\*/)",
        r"(\bOR\b\s+\d+\s*=\s*\d+)",
        r"(\bAND\b\s+\d+\s*=\s*\d+)",
    ]
    
    XSS_PATTERNS = [
        r"<script[^>]*>",
        r"javascript:",
        r"on\w+\s*=",
        r"<iframe[^>]*>",
        r"<object[^>]*>",
        r"<embed[^>]*>",
    ]
    
    NOSQL_INJECTION_PATTERNS = [
        r"\$where",
        r"\$gt",
        r"\$lt",
        r"\$ne",
        r"\$regex",
        r"\$or",
        r"\$and",
    ]
    
    @classmethod
    def detect_sql_injection(cls, value: str) -> bool:
        """Detect potential SQL injection"""
        if not isinstance(value, str):
            return False
        for pattern in cls.SQL_INJECTION_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                return True
        return False
    
    @classmethod
    def detect_xss(cls, value: str) -> bool:
        """Detect potential XSS attack"""
        if not isinstance(value, str):
            return False
        for pattern in cls.XSS_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                return True
        return False
    
    @classmethod
    def detect_nosql_injection(cls, value: str) -> bool:
        """Detect potential NoSQL injection"""
        if not isinstance(value, str):
            return False
        for pattern in cls.NOSQL_INJECTION_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                return True
        return False
    
    @classmethod
    def sanitize_string(cls, value: str, max_length: int = 10000) -> str:
        """Sanitize a string value"""
        if not isinstance(value, str):
            return value
        # Truncate to max length
        value = value[:max_length]
        # Remove null bytes
        value = value.replace('\x00', '')
        return value

# ============== Security Headers Middleware ==============
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Add security headers to all responses
    """
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Security Headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        # Content Security Policy (relaxed for API)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' data:; "
            "connect-src 'self' wss: https:;"
        )
        
        # Remove server identification
        if "server" in response.headers:
            del response.headers["server"]
        
        return response

# ============== Rate Limiting Middleware ==============
class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Apply rate limiting to all requests
    """
    # Rate limits per endpoint type
    RATE_LIMITS = {
        "/api/auth/login": (10, 60),      # 10 requests per minute
        "/api/auth/register": (5, 60),     # 5 requests per minute
        "/api/auth/forgot-password": (3, 60),  # 3 requests per minute
        "/api/auth/reset-password": (5, 60),   # 5 requests per minute
        "default": (200, 60),              # 200 requests per minute for other endpoints
    }
    
    async def dispatch(self, request: Request, call_next):
        # Get client IP
        client_ip = self._get_client_ip(request)
        
        # Check if IP is blocked
        if rate_limiter.is_ip_blocked(client_ip):
            logger.warning(f"Blocked request from banned IP: {client_ip}")
            return JSONResponse(
                status_code=403,
                content={"detail": "Your IP has been temporarily blocked due to suspicious activity"}
            )
        
        # Get rate limit for this endpoint
        path = request.url.path
        max_requests, window = self.RATE_LIMITS.get(path, self.RATE_LIMITS["default"])
        
        # Create identifier (IP + endpoint for more granular control)
        identifier = f"{client_ip}:{path}"
        
        # Check rate limit
        if rate_limiter.is_rate_limited(identifier, max_requests, window):
            logger.warning(f"Rate limit exceeded for {client_ip} on {path}")
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Please try again later."},
                headers={"Retry-After": str(window)}
            )
        
        return await call_next(request)
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract real client IP from request"""
        # Check X-Forwarded-For header (for proxies/load balancers)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Take the first IP in the chain
            return forwarded_for.split(",")[0].strip()
        
        # Check X-Real-IP header
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fall back to direct client IP
        if request.client:
            return request.client.host
        
        return "unknown"

# ============== Request Validation Middleware ==============
class RequestValidationMiddleware(BaseHTTPMiddleware):
    """
    Validate and sanitize incoming requests
    """
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10MB max request size
    
    # Paths that allow larger uploads
    LARGE_UPLOAD_PATHS = [
        "/api/company-master/upload",
        "/api/clients/upload",
        "/api/bulk-upload",
        "/api/database/restore",
    ]
    
    async def dispatch(self, request: Request, call_next):
        # Check content length
        content_length = request.headers.get("content-length")
        if content_length:
            length = int(content_length)
            max_size = self.MAX_CONTENT_LENGTH
            
            # Allow larger uploads for specific paths
            if any(request.url.path.startswith(p) for p in self.LARGE_UPLOAD_PATHS):
                max_size = 100 * 1024 * 1024  # 100MB for file uploads
            
            if length > max_size:
                return JSONResponse(
                    status_code=413,
                    content={"detail": f"Request too large. Maximum size is {max_size // (1024*1024)}MB"}
                )
        
        # Check for suspicious patterns in query params
        for key, value in request.query_params.items():
            if InputSanitizer.detect_sql_injection(value):
                logger.warning(f"Potential SQL injection detected in query: {key}={value[:100]}")
                return JSONResponse(
                    status_code=400,
                    content={"detail": "Invalid request parameters"}
                )
            if InputSanitizer.detect_xss(value):
                logger.warning(f"Potential XSS detected in query: {key}={value[:100]}")
                return JSONResponse(
                    status_code=400,
                    content={"detail": "Invalid request parameters"}
                )
        
        return await call_next(request)

# ============== Audit Logger ==============
class SecurityAuditLogger:
    """
    Log security-related events
    """
    @staticmethod
    async def log_security_event(
        event_type: str,
        ip_address: str,
        user_id: Optional[str] = None,
        details: Optional[dict] = None
    ):
        """Log a security event to the database"""
        from database import db
        
        event = {
            "event_type": event_type,
            "ip_address": ip_address,
            "user_id": user_id,
            "details": details or {},
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        try:
            await db.security_logs.insert_one(event)
        except Exception as e:
            logger.error(f"Failed to log security event: {e}")
        
        # Log to file as well
        logger.info(f"SECURITY: {event_type} from {ip_address} - {details}")

# ============== Password Strength Validator ==============
class PasswordValidator:
    """
    Validate password strength
    """
    MIN_LENGTH = 8
    
    @classmethod
    def validate(cls, password: str) -> tuple[bool, str]:
        """Validate password strength, return (is_valid, message)"""
        if len(password) < cls.MIN_LENGTH:
            return False, f"Password must be at least {cls.MIN_LENGTH} characters"
        
        if not re.search(r"[A-Z]", password):
            return False, "Password must contain at least one uppercase letter"
        
        if not re.search(r"[a-z]", password):
            return False, "Password must contain at least one lowercase letter"
        
        if not re.search(r"\d", password):
            return False, "Password must contain at least one digit"
        
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
            return False, "Password must contain at least one special character"
        
        # Check for common weak passwords
        weak_passwords = [
            "password", "12345678", "qwerty", "admin", "letmein",
            "welcome", "monkey", "dragon", "master", "login"
        ]
        if password.lower() in weak_passwords:
            return False, "This password is too common. Please choose a stronger password."
        
        return True, "Password is strong"

# ============== Session Manager ==============
class SessionManager:
    """
    Manage user sessions with additional security
    """
    def __init__(self):
        self.active_sessions: Dict[str, dict] = {}
    
    def create_session(self, user_id: str, ip_address: str, user_agent: str) -> str:
        """Create a new session and return session ID"""
        session_id = hashlib.sha256(
            f"{user_id}{time.time()}{ip_address}".encode()
        ).hexdigest()
        
        self.active_sessions[session_id] = {
            "user_id": user_id,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_activity": datetime.now(timezone.utc).isoformat()
        }
        
        return session_id
    
    def validate_session(self, session_id: str, ip_address: str) -> bool:
        """Validate a session"""
        if session_id not in self.active_sessions:
            return False
        
        session = self.active_sessions[session_id]
        
        # Optional: Check if IP matches (can be disabled for mobile users)
        # if session["ip_address"] != ip_address:
        #     return False
        
        # Update last activity
        session["last_activity"] = datetime.now(timezone.utc).isoformat()
        
        return True
    
    def invalidate_session(self, session_id: str):
        """Invalidate a session (logout)"""
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
    
    def invalidate_user_sessions(self, user_id: str):
        """Invalidate all sessions for a user"""
        to_remove = [
            sid for sid, session in self.active_sessions.items()
            if session["user_id"] == user_id
        ]
        for sid in to_remove:
            del self.active_sessions[sid]

# Global session manager
session_manager = SessionManager()

# ============== Export all ==============
__all__ = [
    'RateLimiter',
    'rate_limiter',
    'LoginAttemptTracker', 
    'login_tracker',
    'InputSanitizer',
    'SecurityHeadersMiddleware',
    'RateLimitMiddleware',
    'RequestValidationMiddleware',
    'SecurityAuditLogger',
    'PasswordValidator',
    'SessionManager',
    'session_manager'
]
