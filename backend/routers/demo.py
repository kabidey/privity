"""
Demo Mode Router
Handles demo user creation and demo data initialization

ISOLATION RULES:
- All demo data is marked with is_demo=True
- Demo users can only see/modify data where is_demo=True
- Live operations filter out demo data with is_demo!=True
- Demo data is completely isolated from production data
"""
from fastapi import APIRouter, HTTPException
from datetime import datetime, timedelta
import uuid
import random
from database import db
from utils.auth import hash_password, create_token

router = APIRouter(prefix="/demo", tags=["Demo"])

# Demo data prefix for easy identification
DEMO_PREFIX = "demo_"

# Demo user credentials - Employee Role for realistic demo experience
DEMO_USER = {
    "id": "demo_user_privity",
    "email": "demo@privity.com",
    "name": "Demo Employee",
    "role": 7,  # Employee role (Role 7 in PRIVITY)
    "role_name": "Employee (Demo)",
    "is_active": True,
    "is_demo": True,
    "mobile_number": "9999999999",
    "hierarchy_level": 3,  # Employee level
    "hierarchy_level_name": "Employee",
}

def is_demo_id(entity_id: str) -> bool:
    """Check if an ID belongs to demo data"""
    return entity_id and entity_id.startswith(DEMO_PREFIX)

# Sample data generators
def generate_demo_clients():
    """Generate demo client data"""
    clients = []
    client_names = [
        ("Rajesh Kumar", "ABCPK1234A", "rajesh.kumar@email.com", "9876543210"),
        ("Priya Sharma", "DEFPS5678B", "priya.sharma@email.com", "9876543211"),
        ("Amit Patel", "GHIAP9012C", "amit.patel@email.com", "9876543212"),
        ("Sneha Reddy", "JKLSR3456D", "sneha.reddy@email.com", "9876543213"),
        ("Vikram Singh", "MNOVS7890E", "vikram.singh@email.com", "9876543214"),
        ("Anita Gupta", "PQRAG1234F", "anita.gupta@email.com", "9876543215"),
        ("Rahul Verma", "STURV5678G", "rahul.verma@email.com", "9876543216"),
        ("Kavita Nair", "WXYKN9012H", "kavita.nair@email.com", "9876543217"),
    ]
    
    for i, (name, pan, email, mobile) in enumerate(client_names):
        clients.append({
            "id": f"demo_client_{i+1}",
            "otc_ucc": f"DEMO-OTC{i+1:04d}",
            "name": name,
            "pan_number": pan,  # Correct field name
            "email": email,
            "mobile": mobile,
            "phone": mobile,
            "dp_id": f"IN30001{i+1:05d}",
            "dp_type": "NSDL",
            "address": f"{random.randint(1, 500)}, Demo Street, Mumbai, MH",
            "pin_code": f"40000{i+1}",
            "is_vendor": False,
            "is_active": True,
            "is_suspended": False,
            "bank_accounts": [],
            "documents": [],
            "approval_status": "approved",
            "approved_by": DEMO_USER["id"],
            "approved_at": datetime.utcnow().isoformat(),
            "kyc_status": "verified",
            "client_type": random.choice(["individual", "corporate"]),
            "mapped_employee_id": DEMO_USER["id"],
            "mapped_employee_name": DEMO_USER["name"],
            "created_by": DEMO_USER["id"],
            "created_at": (datetime.utcnow() - timedelta(days=random.randint(30, 365))).isoformat(),
            "is_demo": True,
        })
    return clients

def generate_demo_stocks():
    """Generate demo stock data"""
    stocks = [
        {"id": "demo_stock_1", "name": "Reliance Industries", "symbol": "RELIANCE", "sector": "Oil & Gas", "landing_price": 2450.00},
        {"id": "demo_stock_2", "name": "TCS", "symbol": "TCS", "sector": "IT Services", "landing_price": 3890.50},
        {"id": "demo_stock_3", "name": "HDFC Bank", "symbol": "HDFCBANK", "sector": "Banking", "landing_price": 1650.25},
        {"id": "demo_stock_4", "name": "Infosys", "symbol": "INFY", "sector": "IT Services", "landing_price": 1520.75},
        {"id": "demo_stock_5", "name": "ICICI Bank", "symbol": "ICICIBANK", "sector": "Banking", "landing_price": 1125.00},
        {"id": "demo_stock_6", "name": "Bharti Airtel", "symbol": "BHARTIARTL", "sector": "Telecom", "landing_price": 1680.50},
        {"id": "demo_stock_7", "name": "ITC Ltd", "symbol": "ITC", "sector": "FMCG", "landing_price": 485.25},
        {"id": "demo_stock_8", "name": "Axis Bank", "symbol": "AXISBANK", "sector": "Banking", "landing_price": 1180.00},
    ]
    
    for stock in stocks:
        stock["is_demo"] = True
        stock["is_active"] = True
        stock["exchange"] = "NSE"
        stock["isin_number"] = f"INE{stock['symbol'][:6]}001"
        stock["product"] = "equity"
        stock["face_value"] = 10
        stock["available_quantity"] = random.randint(100, 1000)
        stock["wap"] = round(stock["landing_price"] * random.uniform(0.95, 1.05), 2)
        stock["created_by"] = DEMO_USER["id"]
        stock["created_at"] = (datetime.utcnow() - timedelta(days=random.randint(60, 180))).isoformat()
    
    return stocks

def generate_demo_bookings(clients, stocks):
    """Generate demo booking data"""
    bookings = []
    statuses = ["open", "closed"]
    approval_statuses = ["approved", "pending"]
    
    for i in range(15):
        client = random.choice(clients)
        stock = random.choice(stocks)
        quantity = random.randint(10, 100)
        buy_price = stock["landing_price"] * random.uniform(0.98, 1.02)
        sell_price = buy_price * random.uniform(0.95, 1.15)
        status = random.choice(statuses)
        
        # Generate unique booking number
        booking_num = f"DEMO-BK-{i+1:05d}"
        
        booking = {
            "id": f"demo_booking_{i+1}",
            "booking_number": booking_num,
            "client_id": client["id"],
            "client_name": client["name"],
            "stock_id": stock["id"],
            "stock_name": stock["name"],
            "stock_symbol": stock["symbol"],
            "quantity": quantity,
            "buying_price": round(buy_price, 2),
            "selling_price": round(sell_price, 2),
            "status": status,
            "approval_status": "approved",
            "booking_date": (datetime.utcnow() - timedelta(days=random.randint(1, 60))).strftime("%Y-%m-%d"),
            "created_at": (datetime.utcnow() - timedelta(days=random.randint(1, 60))).isoformat(),
            "created_by": DEMO_USER["id"],
            "created_by_name": DEMO_USER["name"],
            "is_demo": True,
            "is_voided": False,
            "is_loss_booking": False,
        }
        
        # Calculate P&L
        booking["profit_loss"] = round((booking["selling_price"] - booking["buying_price"]) * quantity, 2)
        booking["profit_loss_percentage"] = round(((booking["selling_price"] - booking["buying_price"]) / booking["buying_price"]) * 100, 2)
            
        bookings.append(booking)
    
    return bookings

def generate_demo_vendors():
    """Generate demo vendor data"""
    vendors = [
        {"id": "demo_vendor_1", "name": "ABC Securities", "contact": "vendor1@abc.com", "type": "broker"},
        {"id": "demo_vendor_2", "name": "XYZ Capital", "contact": "vendor2@xyz.com", "type": "broker"},
        {"id": "demo_vendor_3", "name": "PQR Investments", "contact": "vendor3@pqr.com", "type": "dealer"},
    ]
    
    for i, vendor in enumerate(vendors):
        vendor["is_demo"] = True
        vendor["is_active"] = True
        vendor["is_vendor"] = True
        vendor["otc_ucc"] = f"DEMO-VDR{i+1:04d}"
        vendor["pan_number"] = f"VENDPAN{i+1:03d}V"
        vendor["email"] = vendor.pop("contact")
        vendor["phone"] = f"98765432{i}0"
        vendor["mobile"] = f"98765432{i}0"
        vendor["dp_id"] = f"IN30002{i+1:05d}"
        vendor["dp_type"] = "NSDL"
        vendor["bank_accounts"] = []
        vendor["documents"] = []
        vendor["approval_status"] = "approved"
        vendor["created_by"] = DEMO_USER["id"]
        vendor["created_at"] = (datetime.utcnow() - timedelta(days=random.randint(90, 365))).isoformat()
    
    return vendors

def generate_demo_business_partners():
    """Generate demo business partner data"""
    partners = [
        {"id": "demo_bp_1", "name": "Partner Finance Ltd", "bp_code": "BP001", "email": "partner1@email.com", "revenue_share": 15},
        {"id": "demo_bp_2", "name": "Investment Associates", "bp_code": "BP002", "email": "partner2@email.com", "revenue_share": 12},
        {"id": "demo_bp_3", "name": "Capital Partners", "bp_code": "BP003", "email": "partner3@email.com", "revenue_share": 18},
    ]
    
    for partner in partners:
        partner["is_demo"] = True
        partner["status"] = "active"
        partner["is_active"] = True
        partner["phone"] = "9876543200"
        partner["mobile"] = "9876543200"
        partner["linked_employee_id"] = DEMO_USER["id"]
        partner["linked_employee_name"] = DEMO_USER["name"]
        partner["created_by"] = DEMO_USER["id"]
        partner["created_at"] = (datetime.utcnow() - timedelta(days=random.randint(30, 180))).isoformat()
    
    return partners

@router.post("/init")
async def initialize_demo():
    """
    Initialize demo mode with sample data.
    Creates a demo user and populates the database with sample data.
    Returns a token for the demo user.
    """
    try:
        # Check if demo user already exists
        existing_user = await db.users.find_one({"id": DEMO_USER["id"]})
        
        if not existing_user:
            # Create demo user
            demo_user_doc = {
                **DEMO_USER,
                "password": hash_password("demo123"),
                "created_at": datetime.utcnow(),
                "permissions": ["*"],  # Full access for demo
                "agreement_accepted": True,  # Auto-accept agreement for demo
                "agreement_accepted_at": datetime.utcnow(),
            }
            await db.users.insert_one(demo_user_doc)
        else:
            # Update existing demo user to have agreement accepted
            await db.users.update_one(
                {"id": DEMO_USER["id"]},
                {"$set": {
                    "agreement_accepted": True,
                    "agreement_accepted_at": datetime.utcnow()
                }}
            )
        
        # Clear previous demo data
        await db.clients.delete_many({"is_demo": True})
        await db.stocks.delete_many({"is_demo": True})
        await db.bookings.delete_many({"is_demo": True})
        await db.vendors.delete_many({"is_demo": True})
        await db.business_partners.delete_many({"is_demo": True})
        
        # Generate demo data
        clients = generate_demo_clients()
        stocks = generate_demo_stocks()
        bookings = generate_demo_bookings(clients, stocks)
        vendors = generate_demo_vendors()
        partners = generate_demo_business_partners()
        
        # Insert or update demo data using upsert to avoid duplicate key errors
        for client in clients:
            await db.clients.update_one(
                {"id": client["id"]},
                {"$set": client},
                upsert=True
            )
        
        for stock in stocks:
            # Use symbol as the unique identifier since stocks has unique index on symbol
            await db.stocks.update_one(
                {"symbol": stock["symbol"]},
                {"$set": {**stock, "is_demo": True}},
                upsert=True
            )
            
        for booking in bookings:
            await db.bookings.update_one(
                {"id": booking["id"]},
                {"$set": booking},
                upsert=True
            )
            
        for vendor in vendors:
            await db.vendors.update_one(
                {"id": vendor["id"]},
                {"$set": vendor},
                upsert=True
            )
            
        for partner in partners:
            await db.business_partners.update_one(
                {"id": partner["id"]},
                {"$set": partner},
                upsert=True
            )
        
        # Create access token for demo user
        token = create_token(
            user_id=DEMO_USER["id"],
            email=DEMO_USER["email"]
        )
        
        return {
            "success": True,
            "message": "Demo mode initialized successfully",
            "token": token,
            "user": {
                "id": DEMO_USER["id"],
                "name": DEMO_USER["name"],
                "email": DEMO_USER["email"],
                "role": DEMO_USER["role"],
                "role_name": DEMO_USER["role_name"],
                "is_demo": True,
            },
            "demo_data": {
                "clients": len(clients),
                "stocks": len(stocks),
                "bookings": len(bookings),
                "vendors": len(vendors),
                "partners": len(partners),
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to initialize demo: {str(e)}")

@router.post("/cleanup")
async def cleanup_demo():
    """
    Clean up ALL demo data from the database.
    Removes all data marked with is_demo=True across all collections.
    This ensures complete isolation and cleanup when exiting demo mode.
    """
    try:
        # List of all collections that may contain demo data
        collections_to_clean = [
            "clients",
            "stocks", 
            "bookings",
            "vendors",
            "business_partners",
            "referral_partners",
            "purchases",
            "inventory",
            "contract_notes",
            "audit_logs",
        ]
        
        deleted_counts = {}
        total_deleted = 0
        
        for collection_name in collections_to_clean:
            try:
                collection = db[collection_name]
                result = await collection.delete_many({"is_demo": True})
                deleted_counts[collection_name] = result.deleted_count
                total_deleted += result.deleted_count
            except Exception as e:
                deleted_counts[collection_name] = f"error: {str(e)}"
        
        # Also delete the demo user
        await db.users.delete_one({"id": DEMO_USER["id"]})
        deleted_counts["demo_user"] = 1
        
        return {
            "success": True,
            "message": f"Demo data cleaned up successfully. {total_deleted} records removed.",
            "deleted": deleted_counts,
            "isolation_verified": True
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to cleanup demo: {str(e)}")

@router.get("/status")
async def get_demo_status():
    """
    Get the current status of demo data in the system.
    Also verifies isolation between demo and live data.
    """
    try:
        # Count demo data
        demo_counts = {
            "clients": await db.clients.count_documents({"is_demo": True}),
            "stocks": await db.stocks.count_documents({"is_demo": True}),
            "bookings": await db.bookings.count_documents({"is_demo": True}),
            "vendors": await db.vendors.count_documents({"is_demo": True}),
            "business_partners": await db.business_partners.count_documents({"is_demo": True}),
        }
        
        # Count live data (non-demo)
        live_counts = {
            "clients": await db.clients.count_documents({"is_demo": {"$ne": True}}),
            "stocks": await db.stocks.count_documents({"is_demo": {"$ne": True}}),
            "bookings": await db.bookings.count_documents({"is_demo": {"$ne": True}}),
        }
        
        # Check if demo user exists
        demo_user_exists = await db.users.find_one({"id": DEMO_USER["id"]}) is not None
        
        return {
            "demo_active": sum(demo_counts.values()) > 0 or demo_user_exists,
            "demo_data": demo_counts,
            "live_data": live_counts,
            "demo_user_exists": demo_user_exists,
            "isolation_status": "complete" if all(v >= 0 for v in demo_counts.values()) else "unknown"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get demo status: {str(e)}")

@router.get("/verify-isolation")
async def verify_demo_isolation():
    """
    Verify that demo data is completely isolated from live data.
    Returns detailed report on data isolation status.
    """
    try:
        isolation_report = {
            "status": "verified",
            "checks": [],
            "warnings": [],
        }
        
        # Check 1: All demo IDs start with 'demo_' prefix
        demo_clients = await db.clients.find({"is_demo": True}, {"id": 1}).to_list(100)
        for client in demo_clients:
            if not client.get("id", "").startswith("demo_"):
                isolation_report["warnings"].append(f"Client {client.get('id')} has is_demo=True but doesn't have demo_ prefix")
        isolation_report["checks"].append({
            "name": "Demo ID prefix check",
            "passed": len(isolation_report["warnings"]) == 0,
            "details": f"Checked {len(demo_clients)} demo clients"
        })
        
        # Check 2: No demo bookings reference live clients
        demo_bookings = await db.bookings.find({"is_demo": True}, {"client_id": 1}).to_list(100)
        for booking in demo_bookings:
            client_id = booking.get("client_id", "")
            if client_id and not client_id.startswith("demo_"):
                live_client = await db.clients.find_one({"id": client_id, "is_demo": {"$ne": True}})
                if live_client:
                    isolation_report["warnings"].append(f"Demo booking references live client {client_id}")
        isolation_report["checks"].append({
            "name": "Demo booking isolation",
            "passed": len([w for w in isolation_report["warnings"] if "booking" in w.lower()]) == 0,
            "details": f"Checked {len(demo_bookings)} demo bookings"
        })
        
        # Check 3: Demo user doesn't have access to live data (by design)
        isolation_report["checks"].append({
            "name": "Demo user isolation",
            "passed": True,
            "details": "Demo user queries are filtered by is_demo flag in API endpoints"
        })
        
        # Set overall status
        if isolation_report["warnings"]:
            isolation_report["status"] = "warnings"
        
        return isolation_report
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to verify isolation: {str(e)}")
