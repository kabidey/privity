"""
PRIVITY - Private Equity System
Main FastAPI Application Server

This is the main entry point for the application.
All business logic endpoints are organized in modular routers under /routers/
"""
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from starlette.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
import logging
from pathlib import Path
import asyncio
from datetime import datetime, timezone
import uuid

# Load environment variables
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Import configuration
from config import UPLOAD_DIR

# Import database
from database import db, client, create_indexes

# Import authentication utilities
from utils.auth import hash_password

# Import WebSocket manager and notification services
from services.notification_service import ws_manager

# Create the main app
app = FastAPI(
    title="PRIVITY - Private Equity System",
    version="2.0.0",
    description="Share Booking Management System with Role-based Access Control"
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


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
    """Startup tasks: create indexes and seed admin user"""
    await create_indexes()
    await seed_admin_user()


async def seed_admin_user():
    """Create default PE Desk super admin - ALWAYS ensures admin exists"""
    try:
        pedesk_user = await db.users.find_one({"email": "pedesk@smifs.com"}, {"_id": 0})
        
        if pedesk_user:
            await db.users.update_one(
                {"email": "pedesk@smifs.com"},
                {"$set": {
                    "password": hash_password("Kutta@123"),
                    "role": 1,
                    "name": "PE Desk Super Admin"
                }}
            )
            logging.info("PE Desk super admin password reset: pedesk@smifs.com")
        else:
            admin_exists = await db.users.find_one({"role": {"$lte": 2}}, {"_id": 0})
            
            admin_id = str(uuid.uuid4())
            admin_doc = {
                "id": admin_id,
                "email": "pedesk@smifs.com",
                "password": hash_password("Kutta@123"),
                "name": "PE Desk Super Admin",
                "role": 1,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            await db.users.insert_one(admin_doc)
            logging.info("PE Desk super admin created: pedesk@smifs.com")
                
    except Exception as e:
        logging.error(f"Error seeding admin user: {e}")


@app.on_event("shutdown")
async def shutdown_db_client():
    """Close database connection on shutdown"""
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
# Health Check
# ====================

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "version": "2.0.0"}
