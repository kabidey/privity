"""
Revenue Dashboard Router

Provides revenue dashboards for:
1. Referral Partners (RP) - visible to mapped employees and hierarchy
2. Employees - visible to the employee and their hierarchy
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from database import db
from utils.auth import get_current_user
from config import ROLES
from services.permission_service import require_permission

router = APIRouter(tags=["Revenue Dashboard"])


def is_pe_level(role: int) -> bool:
    """Check if user has PE Desk or PE Manager role"""
    return role in [1, 2]


async def get_subordinate_user_ids(user_id: str, user_role: int) -> List[str]:
    """Get all subordinate user IDs based on hierarchy.
    
    Hierarchy:
    - PE Desk/Manager (1,2): Can see all users
    - Zonal Manager (3): Can see Managers (4) and Employees (5) under them
    - Manager (4): Can see Employees (5) under them
    - Employee (5): Can only see themselves
    """
    if is_pe_level(user_role):
        # PE level can see all users
        all_users = await db.users.find({}, {"_id": 0, "id": 1}).to_list(10000)
        return [u["id"] for u in all_users]
    
    subordinates = [user_id]  # Always include self
    
    if user_role == 3:  # Zonal Manager
        # Get all managers under this zonal manager
        managers = await db.users.find(
            {"manager_id": user_id, "role": 4},
            {"_id": 0, "id": 1}
        ).to_list(1000)
        manager_ids = [m["id"] for m in managers]
        subordinates.extend(manager_ids)
        
        # Get all employees under these managers
        if manager_ids:
            employees = await db.users.find(
                {"manager_id": {"$in": manager_ids}, "role": 5},
                {"_id": 0, "id": 1}
            ).to_list(10000)
            subordinates.extend([e["id"] for e in employees])
    
    elif user_role == 4:  # Manager
        # Get all employees under this manager
        employees = await db.users.find(
            {"manager_id": user_id, "role": 5},
            {"_id": 0, "id": 1}
        ).to_list(10000)
        subordinates.extend([e["id"] for e in employees])
    
    # Role 5 (Employee) only sees themselves (already added)
    
    return list(set(subordinates))


# ================== RP Revenue Dashboard ==================

@router.get("/rp-revenue", dependencies=[Depends(require_permission("revenue.rp_view", "view RP revenue dashboard"))])
async def get_rp_revenue_dashboard(
    rp_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get RP revenue dashboard data.
    
    Access Rules:
    - Employee: Can only see RPs mapped to them
    - Manager: Can see RPs mapped to their employees
    - Zonal Manager: Can see RPs mapped to their managers' employees
    - PE Level: Can see all RPs
    """
    user_role = current_user.get("role", 6)
    user_id = current_user.get("id")
    
    # Get subordinate user IDs based on hierarchy
    authorized_user_ids = await get_subordinate_user_ids(user_id, user_role)
    
    # Build query for RPs
    rp_query = {}
    
    # Filter by mapped employee for non-PE users
    if not is_pe_level(user_role):
        rp_query["mapped_employee_id"] = {"$in": authorized_user_ids}
    
    if rp_id:
        rp_query["id"] = rp_id
    
    # Get RPs
    rps = await db.referral_partners.find(rp_query, {"_id": 0}).to_list(10000)
    
    if not rps:
        return {
            "total_rps": 0,
            "total_revenue": 0,
            "total_commission": 0,
            "rp_details": []
        }
    
    rp_ids = [rp["id"] for rp in rps]
    
    # Build booking query
    booking_query = {
        "referral_partner_id": {"$in": rp_ids},
        "is_voided": {"$ne": True}
    }
    
    if start_date:
        booking_query["created_at"] = {"$gte": start_date}
    if end_date:
        if "created_at" in booking_query:
            booking_query["created_at"]["$lte"] = end_date
        else:
            booking_query["created_at"] = {"$lte": end_date}
    
    # Get bookings for these RPs
    bookings = await db.bookings.find(booking_query, {"_id": 0}).to_list(100000)
    
    # Calculate revenue per RP
    rp_revenue_map = {}
    for booking in bookings:
        rp_id = booking.get("referral_partner_id")
        if rp_id not in rp_revenue_map:
            rp_revenue_map[rp_id] = {
                "total_bookings": 0,
                "total_quantity": 0,
                "total_revenue": 0,
                "total_commission": 0,
                "completed_bookings": 0,
                "pending_bookings": 0
            }
        
        qty = booking.get("quantity", 0)
        price = booking.get("selling_price", 0)
        revenue = qty * price
        commission = booking.get("rp_commission_amount", 0) or 0
        
        rp_revenue_map[rp_id]["total_bookings"] += 1
        rp_revenue_map[rp_id]["total_quantity"] += qty
        rp_revenue_map[rp_id]["total_revenue"] += revenue
        rp_revenue_map[rp_id]["total_commission"] += commission
        
        if booking.get("stock_transferred"):
            rp_revenue_map[rp_id]["completed_bookings"] += 1
        else:
            rp_revenue_map[rp_id]["pending_bookings"] += 1
    
    # Build detailed response
    rp_details = []
    total_revenue = 0
    total_commission = 0
    
    for rp in rps:
        rp_id = rp["id"]
        revenue_data = rp_revenue_map.get(rp_id, {
            "total_bookings": 0,
            "total_quantity": 0,
            "total_revenue": 0,
            "total_commission": 0,
            "completed_bookings": 0,
            "pending_bookings": 0
        })
        
        rp_detail = {
            "rp_id": rp_id,
            "rp_code": rp.get("rp_code"),
            "rp_name": rp.get("name"),
            "rp_email": rp.get("email"),
            "rp_phone": rp.get("phone"),
            "mapped_employee_id": rp.get("mapped_employee_id"),
            "mapped_employee_name": rp.get("mapped_employee_name"),
            "commission_percent": rp.get("commission_percent", 0),
            **revenue_data
        }
        
        rp_details.append(rp_detail)
        total_revenue += revenue_data["total_revenue"]
        total_commission += revenue_data["total_commission"]
    
    # Sort by total revenue descending
    rp_details.sort(key=lambda x: x["total_revenue"], reverse=True)
    
    return {
        "total_rps": len(rps),
        "total_revenue": total_revenue,
        "total_commission": total_commission,
        "total_bookings": sum(r["total_bookings"] for r in rp_details),
        "rp_details": rp_details
    }


@router.get("/rp-revenue/{rp_id}/bookings", dependencies=[Depends(require_permission("revenue.rp_view", "view RP bookings"))])
async def get_rp_bookings(
    rp_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get detailed bookings for a specific RP."""
    user_role = current_user.get("role", 6)
    user_id = current_user.get("id")
    
    # Check if user has access to this RP
    rp = await db.referral_partners.find_one({"id": rp_id}, {"_id": 0})
    if not rp:
        raise HTTPException(status_code=404, detail="Referral Partner not found")
    
    # Verify access
    if not is_pe_level(user_role):
        authorized_user_ids = await get_subordinate_user_ids(user_id, user_role)
        if rp.get("mapped_employee_id") not in authorized_user_ids:
            raise HTTPException(status_code=403, detail="You don't have access to this RP's data")
    
    # Build booking query
    booking_query = {
        "referral_partner_id": rp_id,
        "is_voided": {"$ne": True}
    }
    
    if start_date:
        booking_query["created_at"] = {"$gte": start_date}
    if end_date:
        if "created_at" in booking_query:
            booking_query["created_at"]["$lte"] = end_date
        else:
            booking_query["created_at"] = {"$lte": end_date}
    
    bookings = await db.bookings.find(booking_query, {"_id": 0}).to_list(10000)
    
    # Enrich with client and stock details
    client_ids = list(set(b.get("client_id") for b in bookings if b.get("client_id")))
    stock_ids = list(set(b.get("stock_id") for b in bookings if b.get("stock_id")))
    
    clients = await db.clients.find({"id": {"$in": client_ids}}, {"_id": 0, "id": 1, "name": 1}).to_list(1000)
    stocks = await db.stocks.find({"id": {"$in": stock_ids}}, {"_id": 0, "id": 1, "symbol": 1, "name": 1}).to_list(1000)
    
    client_map = {c["id"]: c for c in clients}
    stock_map = {s["id"]: s for s in stocks}
    
    enriched_bookings = []
    for b in bookings:
        client = client_map.get(b.get("client_id"), {})
        stock = stock_map.get(b.get("stock_id"), {})
        
        enriched_bookings.append({
            "booking_number": b.get("booking_number"),
            "booking_id": b.get("id"),
            "client_name": client.get("name", "Unknown"),
            "stock_symbol": stock.get("symbol", "Unknown"),
            "stock_name": stock.get("name", "Unknown"),
            "quantity": b.get("quantity", 0),
            "selling_price": b.get("selling_price", 0),
            "total_value": b.get("quantity", 0) * b.get("selling_price", 0),
            "rp_commission_percent": b.get("rp_revenue_share_percent", 0),
            "rp_commission_amount": b.get("rp_commission_amount", 0),
            "status": "Completed" if b.get("stock_transferred") else ("Approved" if b.get("approval_status") == "approved" else "Pending"),
            "created_at": b.get("created_at"),
            "transfer_date": b.get("transfer_date")
        })
    
    return {
        "rp_id": rp_id,
        "rp_name": rp.get("name"),
        "rp_code": rp.get("rp_code"),
        "bookings": enriched_bookings,
        "total_bookings": len(enriched_bookings)
    }


# ================== Employee Revenue Dashboard ==================

@router.get("/employee-revenue", dependencies=[Depends(require_permission("revenue.employee_view", "view employee revenue dashboard"))])
async def get_employee_revenue_dashboard(
    employee_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get Employee revenue dashboard data.
    
    Access Rules:
    - Employee: Can only see their own revenue
    - Manager: Can see their employees' revenue
    - Zonal Manager: Can see their managers' and employees' revenue
    - PE Level: Can see all employees' revenue
    """
    user_role = current_user.get("role", 6)
    user_id = current_user.get("id")
    
    # Get subordinate user IDs based on hierarchy
    authorized_user_ids = await get_subordinate_user_ids(user_id, user_role)
    
    # If specific employee requested, verify access
    if employee_id:
        if employee_id not in authorized_user_ids:
            raise HTTPException(status_code=403, detail="You don't have access to this employee's data")
        authorized_user_ids = [employee_id]
    
    # Get users
    users = await db.users.find(
        {"id": {"$in": authorized_user_ids}},
        {"_id": 0, "password": 0}
    ).to_list(10000)
    
    if not users:
        return {
            "total_employees": 0,
            "total_revenue": 0,
            "total_commission": 0,
            "employee_details": []
        }
    
    user_ids = [u["id"] for u in users]
    
    # Build booking query - bookings where employee is the mapped employee
    booking_query = {
        "is_voided": {"$ne": True}
    }
    
    if start_date:
        booking_query["created_at"] = {"$gte": start_date}
    if end_date:
        if "created_at" in booking_query:
            booking_query["created_at"]["$lte"] = end_date
        else:
            booking_query["created_at"] = {"$lte": end_date}
    
    # Get all bookings
    all_bookings = await db.bookings.find(booking_query, {"_id": 0}).to_list(100000)
    
    # Get client-employee mappings
    clients = await db.clients.find(
        {"mapped_employee_id": {"$in": user_ids}},
        {"_id": 0, "id": 1, "mapped_employee_id": 1}
    ).to_list(100000)
    
    client_to_employee = {c["id"]: c.get("mapped_employee_id") for c in clients}
    
    # Calculate revenue per employee
    # Note: We use two methods to attribute bookings to employees:
    # 1. Client's mapped_employee_id (preferred - the employee responsible for the client)
    # 2. Booking's created_by (fallback - who actually created the booking)
    employee_revenue_map = {}
    for booking in all_bookings:
        client_id = booking.get("client_id")
        # First try client mapping, then fall back to booking creator
        employee_id = client_to_employee.get(client_id) or booking.get("created_by")
        
        if not employee_id or employee_id not in user_ids:
            continue
        
        if employee_id not in employee_revenue_map:
            employee_revenue_map[employee_id] = {
                "total_bookings": 0,
                "total_quantity": 0,
                "total_revenue": 0,
                "total_commission": 0,
                "completed_bookings": 0,
                "pending_bookings": 0,
                "total_clients": set()
            }
        
        qty = booking.get("quantity", 0)
        price = booking.get("selling_price", 0)
        revenue = qty * price
        commission = booking.get("employee_commission_amount", 0) or 0
        
        employee_revenue_map[employee_id]["total_bookings"] += 1
        employee_revenue_map[employee_id]["total_quantity"] += qty
        employee_revenue_map[employee_id]["total_revenue"] += revenue
        employee_revenue_map[employee_id]["total_commission"] += commission
        employee_revenue_map[employee_id]["total_clients"].add(client_id)
        
        if booking.get("stock_transferred"):
            employee_revenue_map[employee_id]["completed_bookings"] += 1
        else:
            employee_revenue_map[employee_id]["pending_bookings"] += 1
    
    # Build detailed response
    employee_details = []
    total_revenue = 0
    total_commission = 0
    
    for user in users:
        emp_id = user["id"]
        revenue_data = employee_revenue_map.get(emp_id, {
            "total_bookings": 0,
            "total_quantity": 0,
            "total_revenue": 0,
            "total_commission": 0,
            "completed_bookings": 0,
            "pending_bookings": 0,
            "total_clients": set()
        })
        
        employee_detail = {
            "employee_id": emp_id,
            "employee_name": user.get("name"),
            "employee_email": user.get("email"),
            "role": user.get("role"),
            "role_name": ROLES.get(user.get("role", 6), "Unknown"),
            "total_bookings": revenue_data["total_bookings"],
            "total_quantity": revenue_data["total_quantity"],
            "total_revenue": revenue_data["total_revenue"],
            "total_commission": revenue_data["total_commission"],
            "completed_bookings": revenue_data["completed_bookings"],
            "pending_bookings": revenue_data["pending_bookings"],
            "total_clients": len(revenue_data["total_clients"])
        }
        
        employee_details.append(employee_detail)
        total_revenue += revenue_data["total_revenue"]
        total_commission += revenue_data["total_commission"]
    
    # Sort by total revenue descending
    employee_details.sort(key=lambda x: x["total_revenue"], reverse=True)
    
    return {
        "total_employees": len(users),
        "total_revenue": total_revenue,
        "total_commission": total_commission,
        "total_bookings": sum(e["total_bookings"] for e in employee_details),
        "employee_details": employee_details
    }


@router.get("/employee-revenue/{employee_id}/bookings", dependencies=[Depends(require_permission("revenue.employee_view", "view employee bookings"))])
async def get_employee_bookings(
    employee_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get detailed bookings for a specific employee."""
    user_role = current_user.get("role", 6)
    user_id = current_user.get("id")
    
    # Verify access
    authorized_user_ids = await get_subordinate_user_ids(user_id, user_role)
    if employee_id not in authorized_user_ids:
        raise HTTPException(status_code=403, detail="You don't have access to this employee's data")
    
    # Get employee
    employee = await db.users.find_one({"id": employee_id}, {"_id": 0, "password": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Get clients mapped to this employee
    clients = await db.clients.find(
        {"mapped_employee_id": employee_id},
        {"_id": 0, "id": 1, "name": 1}
    ).to_list(10000)
    
    client_ids = [c["id"] for c in clients]
    client_map = {c["id"]: c for c in clients}
    
    # Build booking query - find bookings either:
    # 1. Where the client is mapped to this employee, OR
    # 2. Where this employee created the booking
    booking_query = {
        "$or": [
            {"client_id": {"$in": client_ids}} if client_ids else {"_id": None},  # Skip if no clients
            {"created_by": employee_id}
        ],
        "is_voided": {"$ne": True}
    }
    
    if start_date:
        booking_query["created_at"] = {"$gte": start_date}
    if end_date:
        if "created_at" in booking_query:
            booking_query["created_at"]["$lte"] = end_date
        else:
            booking_query["created_at"] = {"$lte": end_date}
    
    bookings = await db.bookings.find(booking_query, {"_id": 0}).to_list(10000)
    
    # Get all client IDs from bookings for name lookup
    all_client_ids = list(set(b.get("client_id") for b in bookings if b.get("client_id")))
    all_clients = await db.clients.find(
        {"id": {"$in": all_client_ids}},
        {"_id": 0, "id": 1, "name": 1}
    ).to_list(10000)
    client_map = {c["id"]: c for c in all_clients}
    
    # Get stock details
    stock_ids = list(set(b.get("stock_id") for b in bookings if b.get("stock_id")))
    stocks = await db.stocks.find({"id": {"$in": stock_ids}}, {"_id": 0, "id": 1, "symbol": 1, "name": 1}).to_list(1000)
    stock_map = {s["id"]: s for s in stocks}
    
    enriched_bookings = []
    for b in bookings:
        client = client_map.get(b.get("client_id"), {})
        stock = stock_map.get(b.get("stock_id"), {})
        
        enriched_bookings.append({
            "booking_number": b.get("booking_number"),
            "booking_id": b.get("id"),
            "client_name": client.get("name", "Unknown"),
            "stock_symbol": stock.get("symbol", "Unknown"),
            "stock_name": stock.get("name", "Unknown"),
            "quantity": b.get("quantity", 0),
            "selling_price": b.get("selling_price", 0),
            "total_value": b.get("quantity", 0) * b.get("selling_price", 0),
            "employee_commission_percent": b.get("employee_revenue_share_percent", 0),
            "employee_commission_amount": b.get("employee_commission_amount", 0),
            "rp_name": b.get("referral_partner_name"),
            "status": "Completed" if b.get("stock_transferred") else ("Approved" if b.get("approval_status") == "approved" else "Pending"),
            "created_at": b.get("created_at"),
            "transfer_date": b.get("transfer_date")
        })
    
    return {
        "employee_id": employee_id,
        "employee_name": employee.get("name"),
        "role_name": ROLES.get(employee.get("role", 6), "Unknown"),
        "bookings": enriched_bookings,
        "total_bookings": len(enriched_bookings)
    }


# ================== Manager Hierarchy ==================

@router.get("/my-team", dependencies=[Depends(require_permission("revenue.team_view", "view team members"))])
async def get_my_team(current_user: dict = Depends(get_current_user)):
    """Get team members under current user based on hierarchy."""
    user_role = current_user.get("role", 6)
    user_id = current_user.get("id")
    
    subordinate_ids = await get_subordinate_user_ids(user_id, user_role)
    # Remove self
    subordinate_ids = [sid for sid in subordinate_ids if sid != user_id]
    
    if not subordinate_ids:
        return {"team_members": [], "total": 0}
    
    team = await db.users.find(
        {"id": {"$in": subordinate_ids}},
        {"_id": 0, "password": 0}
    ).to_list(1000)
    
    team_members = []
    for member in team:
        team_members.append({
            "id": member["id"],
            "name": member.get("name"),
            "email": member.get("email"),
            "role": member.get("role"),
            "role_name": ROLES.get(member.get("role", 6), "Unknown"),
            "manager_id": member.get("manager_id")
        })
    
    return {
        "team_members": team_members,
        "total": len(team_members)
    }
