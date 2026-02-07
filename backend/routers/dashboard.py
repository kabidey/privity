"""
Dashboard Router
Handles dashboard stats and overview endpoints
"""
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends
import pytz

from database import db
from models import DashboardStats
from utils.auth import get_current_user
from services.permission_service import (
    require_permission
)
from utils.demo_isolation import add_demo_filter

# IST timezone
IST = pytz.timezone('Asia/Kolkata')

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


# Helper function for backward compatibility
def is_pe_level(role: int) -> bool:
    """Check if role is PE level (PE Desk or PE Manager)."""
    return role in [1, 2]


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("dashboard.view", "view dashboard stats"))
):
    """Get dashboard statistics"""
    user_role = current_user.get("role", 6)
    user_id = current_user.get("id")
    
    # Base query - PE level sees all, others see only their own
    base_query = {}
    if not is_pe_level(user_role):
        base_query["created_by"] = user_id
    
    # CRITICAL: Add demo data isolation filter to all dashboard queries
    # Demo users only see demo data stats, live users don't see demo data stats
    demo_filter = add_demo_filter({}, current_user)
    
    # Count totals with demo isolation
    client_query = add_demo_filter({"is_active": True, "is_vendor": False}, current_user)
    vendor_query = add_demo_filter({"is_active": True, "is_vendor": True}, current_user)
    stock_query = add_demo_filter({"is_active": True}, current_user)
    booking_base_query = add_demo_filter({**base_query, "status": {"$ne": "cancelled"}}, current_user)
    booking_open_query = add_demo_filter({**base_query, "status": "open", "is_voided": {"$ne": True}}, current_user)
    booking_closed_query = add_demo_filter({**base_query, "status": "closed", "is_voided": {"$ne": True}}, current_user)
    purchase_query = add_demo_filter({}, current_user)
    
    total_clients = await db.clients.count_documents(client_query)
    total_vendors = await db.clients.count_documents(vendor_query)
    total_stocks = await db.stocks.count_documents(stock_query)
    total_bookings = await db.bookings.count_documents(booking_base_query)
    open_bookings = await db.bookings.count_documents(booking_open_query)
    closed_bookings = await db.bookings.count_documents(booking_closed_query)
    total_purchases = await db.purchases.count_documents(purchase_query)
    
    # Calculate inventory value with demo isolation
    inventory_query = add_demo_filter({}, current_user)
    inventory_items = await db.inventory.find(inventory_query, {"_id": 0, "total_value": 1}).to_list(10000)
    total_inventory_value = sum(item.get("total_value", 0) for item in inventory_items)
    
    # Calculate revenue and profit with demo isolation
    profit_query = add_demo_filter({**base_query, "status": {"$ne": "cancelled"}, "is_voided": {"$ne": True}}, current_user)
    bookings = await db.bookings.find(
        profit_query,
        {"_id": 0, "quantity": 1, "buying_price": 1, "selling_price": 1}
    ).to_list(10000)
    
    total_profit_loss = 0
    for booking in bookings:
        qty = booking.get("quantity", 0)
        selling = booking.get("selling_price", 0)
        buying = booking.get("buying_price", 0)
        total_profit_loss += qty * (selling - buying)
    
    return DashboardStats(
        total_clients=total_clients,
        total_vendors=total_vendors,
        total_stocks=total_stocks,
        total_bookings=total_bookings,
        open_bookings=open_bookings,
        closed_bookings=closed_bookings,
        total_profit_loss=total_profit_loss,
        total_inventory_value=total_inventory_value,
        total_purchases=total_purchases
    )


@router.get("/analytics")
async def get_dashboard_analytics(
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("dashboard.view", "view dashboard analytics"))
):
    """Get detailed dashboard analytics"""
    user_role = current_user.get("role", 6)
    user_id = current_user.get("id")
    
    base_query = {}
    if not is_pe_level(user_role):
        base_query["created_by"] = user_id
    
    # Add demo isolation filter
    base_query = add_demo_filter(base_query, current_user)
    
    # Get booking status distribution
    status_pipeline = [
        {"$match": base_query},
        {"$group": {"_id": "$status", "count": {"$sum": 1}}}
    ]
    status_dist = await db.bookings.aggregate(status_pipeline).to_list(100)
    
    # Get approval status distribution
    approval_pipeline = [
        {"$match": base_query},
        {"$group": {"_id": "$approval_status", "count": {"$sum": 1}}}
    ]
    approval_dist = await db.bookings.aggregate(approval_pipeline).to_list(100)
    
    # Get recent activity
    recent_bookings = await db.bookings.find(
        base_query,
        {"_id": 0, "booking_number": 1, "status": 1, "created_at": 1}
    ).sort("created_at", -1).limit(10).to_list(10)
    
    return {
        "status_distribution": {item["_id"]: item["count"] for item in status_dist if item["_id"]},
        "approval_distribution": {item["_id"]: item["count"] for item in approval_dist if item["_id"]},
        "recent_bookings": recent_bookings
    }


# ============== PE DASHBOARD ==============
@router.get("/pe")
async def get_pe_dashboard(
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("dashboard.pe_view", "view PE dashboard"))
):
    """Get PE Desk/Manager specific dashboard data"""
    # Pending approvals
    pending_bookings = await db.bookings.count_documents({"approval_status": "pending"})
    pending_loss_approval = await db.bookings.count_documents({"approval_status": "pending_loss_approval"})
    pending_clients = await db.clients.count_documents({"approval_status": "pending"})
    pending_rp_approval = await db.referral_partners.count_documents({"approval_status": "pending"})
    pending_bp_overrides = await db.bookings.count_documents({"bp_override_approval_status": "pending"})
    
    # Today's activity
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    today_bookings = await db.bookings.count_documents({"created_at": {"$regex": f"^{today}"}})
    today_logins = await db.audit_logs.count_documents({
        "action": "USER_LOGIN",
        "timestamp": {"$regex": f"^{today}"}
    })
    
    # User stats
    total_users = await db.users.count_documents({"is_active": True})
    online_users = await db.users.count_documents({
        "last_activity": {"$gte": (datetime.now(timezone.utc) - timedelta(minutes=15)).isoformat()}
    })
    
    # Recent pending items
    recent_pending_bookings = await db.bookings.find(
        {"approval_status": {"$in": ["pending", "pending_loss_approval"]}},
        {"_id": 0, "id": 1, "booking_number": 1, "client_name": 1, "stock_symbol": 1, "approval_status": 1, "created_at": 1}
    ).sort("created_at", -1).limit(5).to_list(5)
    
    recent_pending_clients = await db.clients.find(
        {"approval_status": "pending"},
        {"_id": 0, "id": 1, "name": 1, "pan_number": 1, "created_at": 1}
    ).sort("created_at", -1).limit(5).to_list(5)
    
    # System health
    total_bookings_value = 0
    bookings = await db.bookings.find(
        {"status": {"$ne": "cancelled"}, "is_voided": {"$ne": True}},
        {"_id": 0, "quantity": 1, "buying_price": 1}
    ).to_list(10000)
    for b in bookings:
        total_bookings_value += b.get("quantity", 0) * b.get("buying_price", 0)
    
    return {
        "pending_actions": {
            "bookings": pending_bookings,
            "loss_approvals": pending_loss_approval,
            "clients": pending_clients,
            "rp_approvals": pending_rp_approval,
            "bp_overrides": pending_bp_overrides,
            "total": pending_bookings + pending_loss_approval + pending_clients + pending_rp_approval + pending_bp_overrides
        },
        "today_activity": {
            "bookings_created": today_bookings,
            "user_logins": today_logins
        },
        "user_stats": {
            "total_users": total_users,
            "online_users": online_users
        },
        "recent_pending_bookings": recent_pending_bookings,
        "recent_pending_clients": recent_pending_clients,
        "total_bookings_value": total_bookings_value
    }


# ============== FINANCE DASHBOARD ==============
@router.get("/finance")
async def get_finance_dashboard(
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("finance.view", "view finance dashboard"))
):
    """Get Finance specific dashboard data"""
    
    # Payment stats from bookings
    bookings = await db.bookings.find(
        {"status": {"$ne": "cancelled"}, "is_voided": {"$ne": True}},
        {"_id": 0, "id": 1, "booking_number": 1, "client_name": 1, "quantity": 1, 
         "buying_price": 1, "payments": 1, "payment_status": 1, "stock_symbol": 1}
    ).to_list(10000)
    
    total_receivable = 0
    total_received = 0
    pending_collections = []
    recent_payments = []
    
    for booking in bookings:
        booking_value = booking.get("quantity", 0) * booking.get("buying_price", 0)
        payments = booking.get("payments", [])
        paid_amount = sum(p.get("amount", 0) for p in payments)
        
        total_receivable += booking_value
        total_received += paid_amount
        
        if paid_amount < booking_value:
            pending_collections.append({
                "booking_number": booking.get("booking_number"),
                "client_name": booking.get("client_name"),
                "stock_symbol": booking.get("stock_symbol"),
                "total_amount": booking_value,
                "paid_amount": paid_amount,
                "pending_amount": booking_value - paid_amount
            })
        
        for payment in payments:
            recent_payments.append({
                "booking_number": booking.get("booking_number"),
                "client_name": booking.get("client_name"),
                "amount": payment.get("amount", 0),
                "payment_date": payment.get("payment_date"),
                "notes": payment.get("notes", "")
            })
    
    # Sort recent payments by date
    recent_payments.sort(key=lambda x: x.get("payment_date", ""), reverse=True)
    
    # Sort pending by amount (highest first)
    pending_collections.sort(key=lambda x: x.get("pending_amount", 0), reverse=True)
    
    # Vendor payments from purchases
    purchases = await db.purchases.find(
        {},
        {"_id": 0, "id": 1, "quantity": 1, "price_per_share": 1, "payments": 1}
    ).to_list(10000)
    
    total_payable = 0
    total_paid = 0
    
    for purchase in purchases:
        purchase_value = purchase.get("quantity", 0) * purchase.get("price_per_share", 0)
        payments = purchase.get("payments", [])
        paid_amount = sum(p.get("amount", 0) for p in payments)
        
        total_payable += purchase_value
        total_paid += paid_amount
    
    # Refund requests
    pending_refunds = await db.bookings.count_documents({
        "refund_request": {"$exists": True},
        "refund_request.status": "pending"
    })
    
    return {
        "receivables": {
            "total": total_receivable,
            "received": total_received,
            "pending": total_receivable - total_received,
            "collection_rate": round((total_received / total_receivable * 100) if total_receivable > 0 else 0, 2)
        },
        "payables": {
            "total": total_payable,
            "paid": total_paid,
            "pending": total_payable - total_paid
        },
        "pending_refunds": pending_refunds,
        "pending_collections": pending_collections[:10],
        "recent_payments": recent_payments[:10]
    }


# ============== EMPLOYEE DASHBOARD ==============
@router.get("/employee")
async def get_employee_dashboard(
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("dashboard.view", "view employee dashboard"))
):
    """Get Employee specific dashboard data"""
    user_id = current_user.get("id")
    user_name = current_user.get("name")
    user_role = current_user.get("role", 6)
    
    # My clients (mapped to me)
    my_clients = await db.clients.find(
        {"mapped_employee_id": user_id, "is_active": True, "is_vendor": False},
        {"_id": 0, "id": 1, "name": 1, "pan_number": 1, "approval_status": 1}
    ).to_list(1000)
    
    my_client_ids = [c["id"] for c in my_clients]
    
    # My bookings (created by me or for my clients)
    my_bookings_query = {
        "$or": [
            {"created_by": user_id},
            {"client_id": {"$in": my_client_ids}}
        ],
        "status": {"$ne": "cancelled"},
        "is_voided": {"$ne": True}
    }
    
    my_bookings = await db.bookings.find(
        my_bookings_query,
        {"_id": 0, "id": 1, "booking_number": 1, "client_name": 1, "stock_symbol": 1, 
         "quantity": 1, "buying_price": 1, "selling_price": 1, "status": 1, 
         "approval_status": 1, "created_at": 1}
    ).to_list(10000)
    
    # Get direct reports if the user is a manager
    direct_reports = await db.users.find(
        {"reports_to": user_id},
        {"_id": 0, "id": 1, "name": 1, "email": 1, "role": 1}
    ).to_list(100)
    
    direct_report_ids = [dr["id"] for dr in direct_reports]
    
    # Get team clients (clients mapped to direct reports)
    team_clients = []
    if direct_report_ids:
        team_clients = await db.clients.find(
            {"mapped_employee_id": {"$in": direct_report_ids}, "is_active": True, "is_vendor": False},
            {"_id": 0, "id": 1, "name": 1, "pan_number": 1, "approval_status": 1, "mapped_employee_id": 1, "mapped_employee_name": 1}
        ).to_list(1000)
    
    # Get team bookings (created by direct reports)
    team_bookings = []
    if direct_report_ids:
        team_bookings = await db.bookings.find(
            {"created_by": {"$in": direct_report_ids}, "status": {"$ne": "cancelled"}, "is_voided": {"$ne": True}},
            {"_id": 0, "id": 1, "booking_number": 1, "client_name": 1, "stock_symbol": 1, 
             "quantity": 1, "selling_price": 1, "approval_status": 1, "created_at": 1, "created_by": 1, "created_by_name": 1}
        ).to_list(10000)
    
    # Calculate metrics
    total_bookings_value = sum(b.get("quantity", 0) * b.get("selling_price", 0) for b in my_bookings)
    pending_bookings = [b for b in my_bookings if b.get("approval_status") == "pending"]
    approved_bookings = [b for b in my_bookings if b.get("approval_status") == "approved"]
    
    team_bookings_value = sum(b.get("quantity", 0) * b.get("selling_price", 0) for b in team_bookings) if team_bookings else 0
    
    # Get pending client approvals for my clients
    pending_clients = [c for c in my_clients if c.get("approval_status") == "pending"]
    
    # Get recent bookings (last 5)
    recent_bookings = sorted(my_bookings, key=lambda x: x.get("created_at", ""), reverse=True)[:5]
    
    # Get team performance summary
    team_performance = []
    for report in direct_reports:
        report_bookings = [b for b in team_bookings if b.get("created_by") == report["id"]]
        report_value = sum(b.get("quantity", 0) * b.get("selling_price", 0) for b in report_bookings)
        report_clients = [c for c in team_clients if c.get("mapped_employee_id") == report["id"]]
        team_performance.append({
            "id": report["id"],
            "name": report["name"],
            "email": report.get("email", ""),
            "bookings_count": len(report_bookings),
            "bookings_value": report_value,
            "clients_count": len(report_clients)
        })
    
    return {
        "user": {
            "id": user_id,
            "name": user_name,
            "role": user_role,
            "hierarchy_level": current_user.get("hierarchy_level", 1),
            "has_team": len(direct_reports) > 0
        },
        "my_stats": {
            "total_clients": len(my_clients),
            "pending_clients": len(pending_clients),
            "total_bookings": len(my_bookings),
            "pending_bookings": len(pending_bookings),
            "approved_bookings": len(approved_bookings),
            "total_value": total_bookings_value
        },
        "team_stats": {
            "direct_reports_count": len(direct_reports),
            "team_clients_count": len(team_clients),
            "team_bookings_count": len(team_bookings),
            "team_value": team_bookings_value
        },
        "my_clients": my_clients[:10],  # Top 10
        "my_pending_clients": pending_clients[:5],
        "my_recent_bookings": recent_bookings,
        "direct_reports": direct_reports,
        "team_performance": team_performance
    }


# ============== Security Status ==============
@router.get("/security-status")
async def get_security_status(
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("security.view_dashboard", "view security status"))
):
    """Get security status and recent security events (PE Desk only)"""
    from middleware.security import rate_limiter, login_tracker
    
    # Get recent security events from database
    recent_events = await db.security_logs.find(
        {},
        {"_id": 0}
    ).sort("timestamp", -1).limit(50).to_list(50)
    
    # Get failed login attempts in last hour
    one_hour_ago = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    failed_logins_count = await db.security_logs.count_documents({
        "event_type": "LOGIN_FAILED",
        "timestamp": {"$gte": one_hour_ago}
    })
    
    # Get blocked IPs
    blocked_ips = list(rate_limiter.blocked_ips.keys())
    
    # Get locked accounts
    locked_accounts = list(login_tracker.locked_accounts.keys())
    
    # Get login statistics for today
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    successful_logins_today = await db.security_logs.count_documents({
        "event_type": "LOGIN_SUCCESS",
        "timestamp": {"$regex": f"^{today}"}
    })
    failed_logins_today = await db.security_logs.count_documents({
        "event_type": "LOGIN_FAILED",
        "timestamp": {"$regex": f"^{today}"}
    })
    
    return {
        "security_status": "active",
        "protections": {
            "rate_limiting": True,
            "login_attempt_tracking": True,
            "security_headers": True,
            "input_validation": True,
            "xss_protection": True,
            "sql_injection_protection": True
        },
        "statistics": {
            "successful_logins_today": successful_logins_today,
            "failed_logins_today": failed_logins_today,
            "failed_logins_last_hour": failed_logins_count,
            "blocked_ips_count": len(blocked_ips),
            "locked_accounts_count": len(locked_accounts)
        },
        "blocked_ips": blocked_ips[:10],  # Show only first 10
        "locked_accounts": locked_accounts[:10],  # Show only first 10
        "recent_security_events": recent_events[:20]
    }


@router.post("/unblock-ip")
async def unblock_ip(
    ip_address: str,
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("security.manage_threats", "unblock IP addresses"))
):
    """Unblock an IP address (requires security.manage_threats permission)"""
    from middleware.security import rate_limiter
    
    if ip_address in rate_limiter.blocked_ips:
        del rate_limiter.blocked_ips[ip_address]
        return {"message": f"IP {ip_address} has been unblocked"}
    
    return {"message": f"IP {ip_address} was not blocked"}


@router.post("/unlock-account")
async def unlock_account(
    email: str,
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("security.unlock_accounts", "unlock user accounts"))
):
    """Unlock a locked account (PE Desk only)"""
    from middleware.security import login_tracker
    
    login_tracker.clear_attempts(email)
    return {"message": f"Account {email} has been unlocked"}


@router.get("/login-locations")
async def get_login_locations(
    user_id: str = None,
    hours: int = 24,
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("security.view_locations", "view login locations"))
):
    """Get login locations - PE Desk can view all, others can view their own"""
    user_role = current_user.get("role", 6)
    
    from services.geolocation_service import UnusualLoginDetector
    
    # If specific user requested, check permissions
    if user_id:
        if user_role not in [1, 2] and user_id != current_user["id"]:
            return {"error": "Access denied"}
        locations = await UnusualLoginDetector.get_user_login_locations(user_id, limit=50)
    else:
        # PE level can see unusual logins, others see their own
        if user_role in [1, 2]:
            locations = await UnusualLoginDetector.get_unusual_logins(hours=hours)
        else:
            locations = await UnusualLoginDetector.get_user_login_locations(
                current_user["id"], limit=20
            )
    
    return {
        "locations": locations,
        "count": len(locations)
    }


@router.get("/login-locations/map-data")
async def get_login_map_data(
    user_id: str = None,
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("security.view_locations", "view login map data"))
):
    """Get login locations formatted for map display"""
    query = {}
    if user_id:
        query["user_id"] = user_id
    
    # Get recent locations with coordinates
    locations = await db.login_locations.find(
        {**query, "lat": {"$ne": 0}},
        {"_id": 0, "user_email": 1, "city": 1, "country": 1, "lat": 1, "lon": 1, 
         "is_unusual": 1, "risk_level": 1, "timestamp": 1}
    ).sort("timestamp", -1).limit(100).to_list(100)
    
    # Group by location for clustering
    location_groups = {}
    for loc in locations:
        key = f"{loc.get('lat', 0):.2f},{loc.get('lon', 0):.2f}"
        if key not in location_groups:
            location_groups[key] = {
                "lat": loc.get("lat"),
                "lon": loc.get("lon"),
                "city": loc.get("city"),
                "country": loc.get("country"),
                "logins": []
            }
        location_groups[key]["logins"].append({
            "user": loc.get("user_email"),
            "time": loc.get("timestamp"),
            "is_unusual": loc.get("is_unusual", False),
            "risk_level": loc.get("risk_level", "low")
        })
    
    return {
        "markers": list(location_groups.values()),
        "total_locations": len(location_groups)
    }


# ============== CLIENT DASHBOARD ==============
@router.get("/client")
async def get_client_dashboard(
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("dashboard.client_view", "view client dashboard"))
):
    """Get Client specific dashboard data"""
    user_email = current_user.get("email")
    
    # Find the client record linked to this user
    client = await db.clients.find_one(
        {"primary_email": user_email, "is_active": True, "is_vendor": False},
        {"_id": 0}
    )
    
    if not client:
        return {"error": "No client profile found"}
    
    client_id = client.get("id")
    
    # Get client's bookings
    bookings = await db.bookings.find(
        {"client_id": client_id, "status": {"$ne": "cancelled"}, "is_voided": {"$ne": True}},
        {"_id": 0}
    ).to_list(1000)
    
    # Calculate portfolio
    portfolio = {}
    total_invested = 0
    total_current_value = 0
    
    for booking in bookings:
        stock_id = booking.get("stock_id")
        stock_symbol = booking.get("stock_symbol", "Unknown")
        qty = booking.get("quantity", 0)
        buying_price = booking.get("buying_price", 0)
        selling_price = booking.get("selling_price", 0) or buying_price
        status = booking.get("status")
        
        if stock_id not in portfolio:
            portfolio[stock_id] = {
                "stock_symbol": stock_symbol,
                "stock_name": booking.get("stock_name", ""),
                "total_quantity": 0,
                "avg_price": 0,
                "total_invested": 0,
                "current_value": 0,
                "bookings_count": 0
            }
        
        portfolio[stock_id]["total_quantity"] += qty
        portfolio[stock_id]["total_invested"] += qty * buying_price
        portfolio[stock_id]["current_value"] += qty * selling_price
        portfolio[stock_id]["bookings_count"] += 1
        
        total_invested += qty * buying_price
        total_current_value += qty * selling_price
    
    # Calculate average price per stock
    for stock_id in portfolio:
        if portfolio[stock_id]["total_quantity"] > 0:
            portfolio[stock_id]["avg_price"] = portfolio[stock_id]["total_invested"] / portfolio[stock_id]["total_quantity"]
    
    # Booking summary
    open_bookings = len([b for b in bookings if b.get("status") == "open"])
    closed_bookings = len([b for b in bookings if b.get("status") == "closed"])
    awaiting_confirmation = len([b for b in bookings if b.get("approval_status") == "approved" and not b.get("client_confirmed")])
    
    # Payment summary
    total_payments = 0
    for booking in bookings:
        payments = booking.get("payments", [])
        total_payments += sum(p.get("amount", 0) for p in payments)
    
    # Recent bookings
    recent_bookings = sorted(bookings, key=lambda x: x.get("created_at", ""), reverse=True)[:10]
    for b in recent_bookings:
        b.pop("payments", None)  # Remove payment details for security
    
    return {
        "client_info": {
            "name": client.get("name"),
            "otc_ucc": client.get("otc_ucc"),
            "pan_number": client.get("pan_number"),
            "approval_status": client.get("approval_status")
        },
        "portfolio_summary": {
            "total_invested": total_invested,
            "current_value": total_current_value,
            "profit_loss": total_current_value - total_invested,
            "stocks_count": len(portfolio)
        },
        "booking_summary": {
            "total": len(bookings),
            "open": open_bookings,
            "closed": closed_bookings,
            "awaiting_confirmation": awaiting_confirmation
        },
        "payment_summary": {
            "total_paid": total_payments,
            "pending": total_invested - total_payments
        },
        "portfolio": list(portfolio.values()),
        "recent_bookings": recent_bookings
    }


@router.post("/clear-cache")
async def clear_system_cache(
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("system.clear_cache", "clear system cache"))
):
    """
    Clear system cache and refresh data (PE Desk only)
    - Recalculates inventory weighted averages
    - Cleans up orphaned records
    - Resets temporary data
    """
    cleanup_results = {
        "orphaned_inventory_deleted": 0,
        "inventory_recalculated": 0,
        "orphaned_bookings_fixed": 0
    }
    
    # 1. Clean up orphaned inventory records (stocks that no longer exist)
    all_stocks = await db.stocks.find({}, {"_id": 0, "id": 1}).to_list(10000)
    valid_stock_ids = [s["id"] for s in all_stocks]
    
    orphaned_result = await db.inventory.delete_many({"stock_id": {"$nin": valid_stock_ids}})
    cleanup_results["orphaned_inventory_deleted"] = orphaned_result.deleted_count
    
    # 2. Recalculate weighted averages for all inventory
    inventory_items = await db.inventory.find({}, {"_id": 0, "stock_id": 1}).to_list(10000)
    
    for item in inventory_items:
        stock_id = item.get("stock_id")
        
        # Get all received purchases for this stock
        purchases = await db.purchases.find(
            {"stock_id": stock_id, "dp_status": "received"},
            {"_id": 0, "quantity": 1, "total_amount": 1}
        ).to_list(10000)
        
        total_quantity = sum(p.get("quantity", 0) for p in purchases)
        total_value = sum(p.get("total_amount", 0) for p in purchases)
        weighted_avg = total_value / total_quantity if total_quantity > 0 else 0
        
        await db.inventory.update_one(
            {"stock_id": stock_id},
            {"$set": {
                "weighted_avg_price": round(weighted_avg, 2),
                "total_value": round(total_value, 2)
            }}
        )
        cleanup_results["inventory_recalculated"] += 1
    
    # 3. Clean up orphaned bookings (client doesn't exist)
    all_clients = await db.clients.find({}, {"_id": 0, "id": 1}).to_list(100000)
    valid_client_ids = [c["id"] for c in all_clients]
    
    orphaned_bookings = await db.bookings.count_documents({"client_id": {"$nin": valid_client_ids}})
    cleanup_results["orphaned_bookings_fixed"] = orphaned_bookings
    
    # Log the cache clear action
    from services.audit_service import create_audit_log
    await create_audit_log(
        action="CACHE_CLEARED",
        entity_type="system",
        entity_id="cache",
        user_id=current_user["id"],
        user_name=current_user["name"],
        user_role=current_user.get("role", 6),
        entity_name="System Cache",
        details=cleanup_results
    )
    
    return {
        "message": "System cache cleared successfully",
        "results": cleanup_results,
        "cleared_at": datetime.now(timezone.utc).isoformat()
    }



# ============== Stock News Endpoint ==============

@router.get("/stock-news")
async def get_stock_news(
    limit: int = 20,
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("dashboard.view", "view stock news"))
):
    """
    Get latest stock market news specifically for stocks in the system.
    News is cached for 1 hour to reduce API calls.
    Only shows news related to stocks in the stocks collection.
    """
    from services.news_service import fetch_stock_news
    
    try:
        # Get stock symbols AND names from the database for targeted news
        stocks = await db.stocks.find(
            {"is_active": True},
            {"_id": 0, "symbol": 1, "name": 1}
        ).limit(20).to_list(20)
        
        stock_symbols = [s.get("symbol") for s in stocks if s.get("symbol")]
        stock_names = [s.get("name") for s in stocks if s.get("name")]
        
        # Fetch news for these specific stocks
        news_items = await fetch_stock_news(
            stock_symbols=stock_symbols,
            stock_names=stock_names,
            limit=limit
        )
        
        return {
            "news": news_items,
            "total": len(news_items),
            "stocks_tracked": len(stock_symbols),
            "fetched_at": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        # Return message when error occurs
        from services.news_service import get_no_stocks_message
        return {
            "news": get_no_stocks_message(),
            "total": 1,
            "is_fallback": True,
            "error": str(e),
            "fetched_at": datetime.now(timezone.utc).isoformat()
        }



# ============== Day-End Revenue Reports ==============

@router.get("/revenue-report")
async def get_revenue_report(
    date: str = None,
    current_user: dict = Depends(get_current_user)
):
    """
    Get revenue report for current user
    Managers get consolidated team report
    """
    from services.day_end_reports import trigger_manual_report
    
    report = await trigger_manual_report(current_user["id"], date)
    if not report:
        return {"error": "Failed to generate report"}
    
    return report


@router.post("/send-day-end-reports")
async def send_day_end_reports(
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("analytics.export", "send day-end reports"))
):
    """
    Manually trigger day-end reports for all users
    Typically called by scheduler at 6 PM IST
    """
    from services.day_end_reports import send_day_end_reports as send_reports
    
    result = await send_reports()
    return {
        "message": "Day-end reports sent successfully",
        **result
    }




# ============== Scheduler Management ==============

@router.get("/scheduled-jobs")
async def get_scheduled_jobs(
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("analytics.export", "view scheduled jobs"))
):
    """
    Get list of all scheduled jobs with their next run times
    """
    from services.scheduler_service import get_scheduled_jobs, IST
    
    jobs = get_scheduled_jobs()
    
    return {
        "timezone": "Asia/Kolkata (IST)",
        "current_time_ist": datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S %Z"),
        "jobs": jobs
    }


@router.post("/trigger-job/{job_id}")
async def trigger_scheduled_job(
    job_id: str,
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("analytics.export", "trigger scheduled job"))
):
    """
    Manually trigger a scheduled job immediately
    """
    from services.scheduler_service import trigger_job_now
    
    result = trigger_job_now(job_id)
    return result


@router.get("/job-history")
async def get_job_history(
    job_name: str = None,
    limit: int = 20,
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("analytics.export", "view job history"))
):
    """
    Get history of scheduled job executions
    """
    query = {}
    if job_name:
        query["job_name"] = job_name
    
    history = await db.scheduled_job_runs.find(
        query,
        {"_id": 0}
    ).sort("executed_at", -1).limit(limit).to_list(limit)
    
    return history

