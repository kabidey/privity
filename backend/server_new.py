"""
Privity Share Booking System - Main Application Entry Point
This server.py imports all routes from modular router files.
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from starlette.middleware.cors import CORSMiddleware
import os
import logging
import jwt

# Import configuration
from config import JWT_SECRET, JWT_ALGORITHM

# Import database client
from database import client

# Import WebSocket manager
from services.notification_service import ws_manager

# Import utility functions for seed
from utils.auth import hash_password

# Import all routers
from routers import (
    auth_router,
    users_router,
    notifications_router,
    clients_router,
    stocks_router,
    corporate_router,
    purchases_router,
    bookings_router,
    reports_router,
    email_templates_router,
    utils_router,
)

# Create the main app
app = FastAPI(title="Privity Share Booking System", version="2.0.0")

# Include all routers with /api prefix
app.include_router(auth_router, prefix="/api")
app.include_router(users_router, prefix="/api")
app.include_router(notifications_router, prefix="/api")
app.include_router(clients_router, prefix="/api")
app.include_router(stocks_router, prefix="/api")
app.include_router(corporate_router, prefix="/api")
app.include_router(purchases_router, prefix="/api")
app.include_router(bookings_router, prefix="/api")
app.include_router(reports_router, prefix="/api")
app.include_router(email_templates_router, prefix="/api")
app.include_router(utils_router, prefix="/api")

# WebSocket endpoint for real-time notifications
@app.websocket("/api/ws/notifications")
async def websocket_notifications(websocket: WebSocket, token: str = Query(...)):
    """WebSocket endpoint for real-time notifications"""
    try:
        # Verify token
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload["user_id"]
        
        await ws_manager.connect(websocket, user_id)
        
        try:
            while True:
                data = await websocket.receive_text()
                if data == "ping":
                    await websocket.send_text("pong")
        except WebSocketDisconnect:
            ws_manager.disconnect(websocket, user_id)
    except jwt.ExpiredSignatureError:
        await websocket.close(code=4001, reason="Token expired")
    except jwt.InvalidTokenError:
        await websocket.close(code=4002, reason="Invalid token")
    except Exception as e:
        logging.error(f"WebSocket error: {e}")
        await websocket.close(code=1011)


# Startup event to seed admin user
@app.on_event("startup")
async def seed_admin_user():
    """Create default admin user if no admin exists"""
    from database import db
    from datetime import datetime, timezone
    import uuid
    
    try:
        # Check if any admin user exists (role 1 or 2)
        admin_exists = await db.users.find_one({"role": {"$lte": 2}}, {"_id": 0})
        if not admin_exists:
            admin_id = str(uuid.uuid4())
            admin_doc = {
                "id": admin_id,
                "email": "admin@privity.com",
                "password": hash_password("Admin@123"),
                "name": "Admin User",
                "role": 1,  # PE Desk - full access
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            await db.users.insert_one(admin_doc)
            logging.info("Default admin user created: admin@privity.com")
        else:
            logging.info("Admin user already exists, skipping seed")
    except Exception as e:
        logging.error(f"Error seeding admin user: {e}")


# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
