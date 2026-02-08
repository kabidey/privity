"""
PRIVITY - Private Equity System
Main FastAPI Application Server

This is the main entry point for the application.
All business logic endpoints are organized in modular routers under /routers/
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from starlette.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
import logging
from pathlib import Path
import asyncio
from datetime import datetime, timezone
import uuid
import json

# Load environment variables
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Import configuration

# Import database
from database import db, client, create_indexes

# Import authentication utilities
from utils.auth import hash_password

# Import WebSocket manager and notification services
from services.notification_service import ws_manager

# Create the main app
app = FastAPI(
    title="PRIVITY - Private Equity System",
    version="7.2.2.1",
    description="Share Booking Management System with Role-based Access Control"
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ====================
# Cache Control Middleware for Auth Routes
# ====================
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

class NoCacheAuthMiddleware(BaseHTTPMiddleware):
    """Middleware to prevent caching of auth-related responses"""
    
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        
        # Add no-cache headers for auth routes
        path = request.url.path.lower()
        if '/auth/' in path or '/register' in path or '/login' in path:
            response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
        
        return response

app.add_middleware(NoCacheAuthMiddleware)


# ====================
# Health Check Endpoint (No Auth Required)
# ====================

@app.get("/api/health")
async def health_check():
    """
    Comprehensive health check endpoint for diagnosing production issues.
    No authentication required - accessible for monitoring.
    """
    import platform
    import sys
    
    health = {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "7.2.2.1",
        "checks": {}
    }
    
    # 1. Database connectivity check
    try:
        # Simple ping to check MongoDB connection
        await db.command("ping")
        collections = await db.list_collection_names()
        health["checks"]["database"] = {
            "status": "ok",
            "collections_count": len(collections),
            "message": "MongoDB connected"
        }
    except Exception as e:
        health["status"] = "degraded"
        health["checks"]["database"] = {
            "status": "error",
            "message": str(e)
        }
    
    # 2. Check critical collections exist
    try:
        critical_collections = ["users", "clients", "bookings", "stocks"]
        existing = await db.list_collection_names()
        missing = [c for c in critical_collections if c not in existing]
        health["checks"]["collections"] = {
            "status": "ok" if not missing else "warning",
            "critical_collections": critical_collections,
            "missing": missing
        }
    except Exception as e:
        health["checks"]["collections"] = {"status": "error", "message": str(e)}
    
    # 3. Check admin user exists
    try:
        admin = await db.users.find_one({"email": "pe@smifs.com"}, {"_id": 0, "email": 1, "name": 1})
        health["checks"]["admin_user"] = {
            "status": "ok" if admin else "error",
            "exists": bool(admin),
            "email": admin.get("email") if admin else None
        }
    except Exception as e:
        health["checks"]["admin_user"] = {"status": "error", "message": str(e)}
    
    # 4. Environment check
    env_vars = ["MONGO_URL", "DB_NAME", "JWT_SECRET"]
    env_status = {}
    for var in env_vars:
        value = os.environ.get(var)
        env_status[var] = "set" if value else "missing"
    
    health["checks"]["environment"] = {
        "status": "ok" if all(v == "set" for v in env_status.values()) else "error",
        "variables": env_status
    }
    
    # 5. System info
    health["system"] = {
        "python_version": sys.version.split()[0],
        "platform": platform.system(),
        "hostname": platform.node()
    }
    
    # 6. WhatsApp/Wati check
    try:
        wati_config = await db.system_config.find_one({"config_type": "whatsapp"}, {"_id": 0, "api_token": 0})
        health["checks"]["whatsapp"] = {
            "status": "ok",
            "configured": bool(wati_config),
            "using_defaults": not bool(wati_config),
            "message": "Hardcoded defaults active" if not wati_config else "Database config active"
        }
    except Exception as e:
        health["checks"]["whatsapp"] = {"status": "error", "message": str(e)}
    
    return health


@app.get("/api/health/simple")
async def simple_health():
    """Simple health check - just returns OK if server is running"""
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}


@app.get("/api/health/db")
async def db_health():
    """Database-only health check"""
    try:
        await db.command("ping")
        count = await db.users.count_documents({})
        return {
            "status": "ok",
            "database": "connected",
            "users_count": count,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        return {
            "status": "error",
            "database": "disconnected",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


# ====================
# Helper Functions
# ====================

def generate_otc_ucc() -> str:
    """Generate unique OTC UCC code"""
    date_part = datetime.now(timezone.utc).strftime("%Y%m%d")
    unique_part = str(uuid.uuid4())[:8].upper()
    return f"OTC{date_part}{unique_part}"


_booking_number_lock = asyncio.Lock()

async def generate_booking_number() -> str:
    """Generate unique human-readable booking number using atomic counter."""
    year = datetime.now(timezone.utc).strftime("%Y")
    
    async with _booking_number_lock:
        counter = await db.counters.find_one_and_update(
            {"_id": f"booking_{year}"},
            {"$inc": {"seq": 1}},
            upsert=True,
            return_document=True
        )
        seq_num = counter.get("seq", 1)
        return f"BK-{year}-{seq_num:05d}"


def get_client_emails(client: dict) -> list:
    """Get all email addresses for a client (primary, secondary, tertiary)"""
    emails = []
    if client.get("email"):
        emails.append(client["email"])
    if client.get("email_secondary"):
        emails.append(client["email_secondary"])
    if client.get("email_tertiary"):
        emails.append(client["email_tertiary"])
    return emails


async def update_inventory(stock_id: str):
    """Recalculate weighted average and available quantity for a stock.
    
    Inventory Logic:
    - available_quantity: Stock available for new bookings (purchased - transferred - blocked)
    - blocked_quantity: Stock reserved for approved bookings pending transfer
    - weighted_avg_price: Calculated from total purchased value / total purchased quantity
    """
    purchases = await db.purchases.find({"stock_id": stock_id}, {"_id": 0}).to_list(10000)
    bookings = await db.bookings.find({"stock_id": stock_id}, {"_id": 0}).to_list(10000)
    
    total_purchased_qty = sum(p["quantity"] for p in purchases)
    total_purchased_value = sum(p["quantity"] * p["price_per_unit"] for p in purchases)
    
    blocked_qty = sum(
        b["quantity"] for b in bookings 
        if b.get("approval_status") == "approved" 
        and not b.get("is_voided", False)
        and not b.get("stock_transferred", False)
    )
    
    transferred_qty = sum(
        b["quantity"] for b in bookings 
        if b.get("stock_transferred") == True
        and not b.get("is_voided", False)
    )
    
    available_qty = total_purchased_qty - transferred_qty - blocked_qty
    weighted_avg = total_purchased_value / total_purchased_qty if total_purchased_qty > 0 else 0
    
    stock = await db.stocks.find_one({"id": stock_id}, {"_id": 0})
    
    inventory_data = {
        "stock_id": stock_id,
        "stock_symbol": stock["symbol"] if stock else "Unknown",
        "stock_name": stock["name"] if stock else "Unknown",
        "available_quantity": max(0, available_qty),
        "blocked_quantity": blocked_qty,
        "weighted_avg_price": weighted_avg,
        "total_value": max(0, available_qty) * weighted_avg
    }
    
    await db.inventory.update_one(
        {"stock_id": stock_id},
        {"$set": inventory_data},
        upsert=True
    )
    
    return inventory_data


# ====================
# Startup / Shutdown Events
# ====================

@app.on_event("startup")
async def startup_tasks():
    """Startup tasks: create indexes, seed admin user, start scheduler"""
    await create_indexes()
    await seed_admin_user()
    await seed_license_admin_user()
    
    # Initialize and start the scheduler
    from services.scheduler_service import init_scheduler
    init_scheduler()
    logging.info("Scheduler initialized for day-end reports at 6 PM IST")


async def seed_license_admin_user():
    """Create secret license admin user - hidden from all frontend views"""
    try:
        from services.license_service_v2 import create_license_admin_user
        await create_license_admin_user()
        logging.info("License admin user initialized")
    except Exception as e:
        logging.error(f"Error seeding license admin: {e}")


async def seed_admin_user():
    """Create default PE Desk super admin - ALWAYS ensures admin exists"""
    try:
        pedesk_user = await db.users.find_one({"email": "pe@smifs.com"})
        
        if pedesk_user is not None:
            await db.users.update_one(
                {"email": "pe@smifs.com"},
                {"$set": {
                    "password": hash_password("Kutta@123"),
                    "role": 1,
                    "name": "PE Desk Super Admin"
                }}
            )
            logging.info("PE Desk super admin password reset: pe@smifs.com")
        else:
            # Create new admin user
            admin_id = str(uuid.uuid4())
            admin_doc = {
                "id": admin_id,
                "email": "pe@smifs.com",
                "password": hash_password("Kutta@123"),
                "name": "PE Desk Super Admin",
                "role": 1,
                "is_active": True,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            await db.users.insert_one(admin_doc)
            logging.info("PE Desk super admin created: pe@smifs.com")
                
    except Exception as e:
        logging.error(f"Error seeding admin user: {e}")


@app.on_event("shutdown")
async def shutdown_db_client():
    """Close database connection and scheduler on shutdown"""
    # Shutdown scheduler
    from services.scheduler_service import shutdown_scheduler
    shutdown_scheduler()
    
    # Close database connection
    client.close()


# ====================
# WebSocket Endpoint
# ====================

@app.websocket("/api/ws/notifications")
async def websocket_notifications(websocket: WebSocket, token: str = None):
    """WebSocket endpoint for real-time notifications
    
    Note: Must accept() the WebSocket connection before any close() or send() operations.
    This is required for proper WebSocket handshake in production Kubernetes environments.
    """
    from utils.auth import decode_token
    
    # First, accept the WebSocket connection (required before any other operation)
    await websocket.accept()
    
    if not token:
        await websocket.close(code=4001, reason="No token provided")
        return
    
    try:
        payload = decode_token(token)
        user_id = payload.get("user_id")
        if not user_id:
            await websocket.close(code=4002, reason="Invalid token")
            return
    except Exception as e:
        logger.warning(f"WebSocket token error: {str(e)}")
        await websocket.close(code=4003, reason=f"Token error: {str(e)}")
        return
    
    # Register connection with user_id
    await ws_manager.connect(websocket, user_id)
    
    try:
        while True:
            data = await websocket.receive_text()
            # Handle ping/pong for keepalive
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, user_id)
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {str(e)}")
        ws_manager.disconnect(websocket, user_id)


# Group Chat WebSocket Endpoint
@app.websocket("/api/ws/group-chat")
async def websocket_group_chat(websocket: WebSocket, token: str = None):
    """WebSocket endpoint for real-time group chat
    
    All authenticated users can connect and participate in the common chat.
    """
    from utils.auth import decode_token
    from routers.group_chat import get_chat_manager
    
    # First, accept the WebSocket connection
    await websocket.accept()
    
    if not token:
        await websocket.close(code=4001, reason="No token provided")
        return
    
    try:
        payload = decode_token(token)
        user_id = payload.get("user_id")
        if not user_id:
            await websocket.close(code=4002, reason="Invalid token")
            return
    except Exception as e:
        logger.warning(f"Group chat WebSocket token error: {str(e)}")
        await websocket.close(code=4003, reason=f"Token error: {str(e)}")
        return
    
    # Get user info from database
    user = await db.users.find_one({"id": user_id}, {"_id": 0, "id": 1, "name": 1, "role": 1})
    if not user:
        await websocket.close(code=4004, reason="User not found")
        return
    
    role_names = {
        1: "PE Desk",
        2: "PE Manager",
        3: "Finance",
        4: "Viewer",
        5: "Partners Desk",
        6: "Business Partner",
        7: "Employee"
    }
    
    user_info = {
        "name": user["name"],
        "role": user.get("role", 5),
        "role_name": role_names.get(user.get("role", 5), "User")
    }
    
    # Get chat manager and connect
    chat_mgr = get_chat_manager()
    await chat_mgr.connect(websocket, user_id, user_info)
    
    try:
        while True:
            data = await websocket.receive_text()
            # Handle ping/pong for keepalive
            if data == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
    except WebSocketDisconnect:
        user_name = chat_mgr.disconnect(user_id)
        if user_name:
            await chat_mgr.broadcast_system_message(f"{user_name} left the chat")
            await chat_mgr.broadcast_online_users()
    except Exception as e:
        logger.error(f"Group chat WebSocket error for user {user_id}: {str(e)}")
        user_name = chat_mgr.disconnect(user_id)
        if user_name:
            await chat_mgr.broadcast_online_users()


# ====================
# Include All Routers
# ====================

# Core Authentication & Users
from routers.auth import router as auth_router
from routers.users import router as users_router

# Client & Partner Management
from routers.clients import router as clients_router
from routers.referral_partners import router as referral_partners_router
from routers.business_partners import router as business_partners_router

# Stock & Inventory Management
from routers.stocks import router as stocks_router
from routers.inventory import router as inventory_router
from routers.purchases import router as purchases_router

# Bookings
from routers.bookings import router as bookings_router

# Finance & Payments
from routers.finance import router as finance_router

# Reports & Analytics
from routers.reports import router as reports_router
from routers.analytics import router as analytics_router
from routers.dashboard import router as dashboard_router

# Audit & Logs
from routers.audit_logs import router as audit_logs_router
from routers.email_logs import router as email_logs_router

# System Configuration
from routers.email_templates import router as email_templates_router
from routers.smtp_config import router as smtp_config_router
from routers.company_master import router as company_master_router
from routers.database_backup import router as database_backup_router

# Documents & Contracts
from routers.contract_notes import router as contract_notes_router

# Fixed Income Module
from fixed_income.router_instruments import router as fi_instruments_router
from fixed_income.router_orders import router as fi_orders_router
from fixed_income.router_reports import router as fi_reports_router
from fixed_income.router_dashboard import router as fi_dashboard_router
from fixed_income.market_data_service import router as fi_market_data_router
from fixed_income.router_primary_market import router as fi_primary_market_router
from fixed_income.router_analytics import router as fi_analytics_router

# Bulk Operations
from routers.bulk_upload import router as bulk_upload_router

# Notifications
from routers.notifications import router as notifications_router

# Revenue Dashboards
from routers.revenue_dashboard import router as revenue_dashboard_router

# AI Assistant
from routers.sohini import router as sohini_router

# Kill Switch
from routers.kill_switch import router as kill_switch_router

# Research
from routers.research import router as research_router

# Group Chat
from routers.group_chat import router as group_chat_router

# File Storage (GridFS)
from routers.files import router as files_router

# Two-Factor Authentication
from routers.two_factor import router as two_factor_router
from routers.roles import router as roles_router
from routers.license import router as license_router
from routers.license_v2 import router as license_v2_router

# Security Threats
from routers.security import router as security_router

# Business Intelligence
from routers.bi_reports import router as bi_reports_router

# WhatsApp Notifications
from routers.whatsapp import router as whatsapp_router

# Demo Mode
from routers.demo import router as demo_router

# Payments
from routers.payments import router as payments_router

# Register all routers with /api prefix
app.include_router(auth_router, prefix="/api")
app.include_router(users_router, prefix="/api")
app.include_router(clients_router, prefix="/api")
app.include_router(referral_partners_router, prefix="/api")
app.include_router(business_partners_router, prefix="/api")
app.include_router(stocks_router, prefix="/api")
app.include_router(inventory_router, prefix="/api")
app.include_router(purchases_router, prefix="/api")
app.include_router(bookings_router, prefix="/api")
app.include_router(finance_router, prefix="/api")
app.include_router(reports_router, prefix="/api")
app.include_router(analytics_router, prefix="/api")
app.include_router(dashboard_router, prefix="/api")
app.include_router(revenue_dashboard_router, prefix="/api")
app.include_router(audit_logs_router, prefix="/api")
app.include_router(email_logs_router, prefix="/api")
app.include_router(email_templates_router, prefix="/api")
app.include_router(smtp_config_router, prefix="/api")
app.include_router(company_master_router, prefix="/api")
app.include_router(database_backup_router, prefix="/api")
app.include_router(contract_notes_router, prefix="/api")
app.include_router(bulk_upload_router, prefix="/api")
app.include_router(notifications_router, prefix="/api")
app.include_router(sohini_router, prefix="/api")
app.include_router(kill_switch_router, prefix="/api")
app.include_router(research_router, prefix="/api")
app.include_router(group_chat_router, prefix="/api")
app.include_router(files_router, prefix="/api")
app.include_router(two_factor_router, prefix="/api")
app.include_router(roles_router, prefix="/api")
app.include_router(license_router, prefix="/api")
app.include_router(license_v2_router, prefix="/api")
app.include_router(security_router)
app.include_router(bi_reports_router, prefix="/api")
app.include_router(whatsapp_router, prefix="/api")
app.include_router(demo_router, prefix="/api")
app.include_router(payments_router, prefix="/api")

# Fixed Income Module
app.include_router(fi_instruments_router, prefix="/api")
app.include_router(fi_orders_router, prefix="/api")
app.include_router(fi_reports_router, prefix="/api")
app.include_router(fi_dashboard_router, prefix="/api")
app.include_router(fi_market_data_router, prefix="/api")
app.include_router(fi_primary_market_router, prefix="/api")


# ====================
# Static Files Mount
# ====================

from fastapi.staticfiles import StaticFiles

UPLOADS_PATH = Path("/app/uploads")
UPLOADS_PATH.mkdir(exist_ok=True)
app.mount("/api/uploads", StaticFiles(directory=str(UPLOADS_PATH)), name="uploads")


# ====================
# CORS Middleware
# ====================

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# ====================
# Security Middleware
# ====================

from middleware.security import (
    SecurityHeadersMiddleware,
    RateLimitMiddleware,
    RequestValidationMiddleware
)

# Add security headers to all responses
app.add_middleware(SecurityHeadersMiddleware)

# Rate limiting to prevent brute force and DDoS
app.add_middleware(RateLimitMiddleware)

# Request validation and sanitization
app.add_middleware(RequestValidationMiddleware)

# ====================
# Bot Protection Middleware
# ====================

from middleware.bot_protection import (
    BotProtectionMiddleware,
    ROBOTS_TXT_CONTENT
)

# Block bots, crawlers, and various attacks
app.add_middleware(BotProtectionMiddleware)

# ====================
# Kill Switch Middleware
# ====================

from middleware.kill_switch import KillSwitchMiddleware
app.add_middleware(KillSwitchMiddleware)


# ====================
# Robots.txt Endpoint (Block all crawlers)
# ====================

@app.get("/robots.txt")
async def robots_txt():
    """Return robots.txt that blocks all crawlers"""
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse(ROBOTS_TXT_CONTENT, media_type="text/plain")


# ====================
# Health Check
# ====================

@app.get("/health")
async def health_check_root():
    """Root health check endpoint for Kubernetes liveness/readiness probes"""
    return {"status": "healthy", "version": "7.2.2.1"}

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "version": "7.2.2.1"}
