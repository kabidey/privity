"""
Database connection and utilities
"""
from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGO_URL, DB_NAME

# MongoDB connection
client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

async def get_database():
    """Get database instance"""
    return db

async def close_database():
    """Close database connection"""
    client.close()

async def create_indexes():
    """Create database indexes for better query performance"""
    try:
        # Users collection indexes
        await db.users.create_index("email", unique=True)
        await db.users.create_index("pan_number", sparse=True)
        await db.users.create_index("role")
        
        # Clients collection indexes
        await db.clients.create_index("pan_number")
        await db.clients.create_index("email")
        await db.clients.create_index("otc_ucc", unique=True, sparse=True)
        await db.clients.create_index("approval_status")
        await db.clients.create_index("is_vendor")
        await db.clients.create_index([("name", 1), ("is_active", 1)])
        
        # Bookings collection indexes
        await db.bookings.create_index("booking_number", unique=True)
        await db.bookings.create_index("client_id")
        await db.bookings.create_index("stock_id")
        await db.bookings.create_index("status")
        await db.bookings.create_index("approval_status")
        await db.bookings.create_index("created_by")
        await db.bookings.create_index([("created_at", -1)])
        await db.bookings.create_index("referral_partner_id", sparse=True)
        
        # Referral Partners collection indexes
        await db.referral_partners.create_index("rp_code", unique=True)
        await db.referral_partners.create_index("pan_number", unique=True)
        await db.referral_partners.create_index("email", sparse=True)
        await db.referral_partners.create_index("approval_status")
        
        # Stocks collection indexes
        await db.stocks.create_index("symbol", unique=True)
        await db.stocks.create_index("isin_number", sparse=True)
        
        # Audit logs collection indexes
        await db.audit_logs.create_index([("created_at", -1)])
        await db.audit_logs.create_index("user_id")
        await db.audit_logs.create_index("entity_type")
        await db.audit_logs.create_index("action")
        
        # Notifications collection indexes
        await db.notifications.create_index("user_id")
        await db.notifications.create_index([("created_at", -1)])
        await db.notifications.create_index("read")
        
        # Finance/Payments collection indexes
        await db.rp_payments.create_index("booking_id")
        await db.rp_payments.create_index("rp_id")
        await db.rp_payments.create_index("status")
        
        await db.employee_commissions.create_index("booking_id")
        await db.employee_commissions.create_index("employee_id")
        await db.employee_commissions.create_index("status")
        
        # Email logs collection indexes
        await db.email_logs.create_index([("created_at", -1)])
        await db.email_logs.create_index("status")
        await db.email_logs.create_index("template_key", sparse=True)
        await db.email_logs.create_index("to_email")
        await db.email_logs.create_index([("related_entity_type", 1), ("related_entity_id", 1)], sparse=True)
        
        print("Database indexes created successfully")
    except Exception as e:
        print(f"Error creating indexes: {e}")

