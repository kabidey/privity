"""
Analytics & Reports Router
Handles all analytics, reporting, and export endpoints
"""
from typing import List, Optional, Dict
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import StreamingResponse
import io

from database import db
from config import ROLES
from utils.auth import get_current_user
from services.permission_service import (
    has_permission,
    check_permission as check_dynamic_permission,
    require_permission
)

router = APIRouter(prefix="/analytics", tags=["Analytics"])


# Helper function for backward compatibility
def is_pe_level(role: int) -> bool:
    """Check if role is PE level (PE Desk or PE Manager)."""
    return role in [1, 2]


@router.get("/summary")
async def get_analytics_summary(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("analytics.view", "view analytics"))
):
    """Get analytics summary"""
    query = {"status": {"$ne": "cancelled"}}
    
    if start_date:
        query["created_at"] = {"$gte": start_date}
    if end_date:
        if "created_at" in query:
            query["created_at"]["$lte"] = end_date
        else:
            query["created_at"] = {"$lte": end_date}
    
    bookings = await db.bookings.find(query, {"_id": 0}).to_list(10000)
    
    total_revenue = 0
    total_cost = 0
    total_bookings = len(bookings)
    
    for booking in bookings:
        qty = booking.get("quantity", 0)
        selling = booking.get("selling_price", 0)
        buying = booking.get("buying_price", 0)
        total_revenue += qty * selling
        total_cost += qty * buying
    
    return {
        "total_bookings": total_bookings,
        "total_revenue": total_revenue,
        "total_cost": total_cost,
        "profit": total_revenue - total_cost,
        "profit_margin": ((total_revenue - total_cost) / total_revenue * 100) if total_revenue > 0 else 0
    }


@router.get("/stock-performance")
async def get_stock_performance(
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("analytics.performance", "view stock performance"))
):
    """Get stock performance analytics"""
    stocks = await db.stocks.find({"is_active": True}, {"_id": 0}).to_list(1000)
    stock_map = {s["id"]: s for s in stocks}
    
    bookings = await db.bookings.find(
        {"status": {"$ne": "cancelled"}},
        {"_id": 0, "stock_id": 1, "quantity": 1, "buying_price": 1, "selling_price": 1}
    ).to_list(10000)
    
    stock_stats = {}
    for booking in bookings:
        stock_id = booking.get("stock_id")
        if not stock_id:
            continue
        
        if stock_id not in stock_stats:
            stock_info = stock_map.get(stock_id, {})
            stock_stats[stock_id] = {
                "stock_id": stock_id,
                "symbol": stock_info.get("symbol", "Unknown"),
                "name": stock_info.get("name", "Unknown"),
                "total_quantity": 0,
                "total_revenue": 0,
                "total_cost": 0,
                "booking_count": 0
            }
        
        qty = booking.get("quantity", 0)
        stock_stats[stock_id]["total_quantity"] += qty
        stock_stats[stock_id]["total_revenue"] += booking.get("selling_price", 0) * qty
        stock_stats[stock_id]["total_cost"] += booking.get("buying_price", 0) * qty
        stock_stats[stock_id]["booking_count"] += 1
    
    # Calculate profit for each stock
    for stats in stock_stats.values():
        stats["profit"] = stats["total_revenue"] - stats["total_cost"]
        stats["profit_margin"] = (stats["profit"] / stats["total_revenue"] * 100) if stats["total_revenue"] > 0 else 0
    
    return list(stock_stats.values())


@router.get("/employee-performance")
async def get_employee_performance(
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("analytics.performance", "view employee performance"))
):
    """Get employee performance analytics"""
    
    employees = await db.users.find(
        {"role": {"$in": [3, 4]}},  # PE Managers and Employees
        {"_id": 0, "id": 1, "name": 1, "email": 1, "role": 1}
    ).to_list(1000)
    
    employee_map = {e["id"]: e for e in employees}
    
    bookings = await db.bookings.find(
        {"status": {"$ne": "cancelled"}},
        {"_id": 0, "created_by": 1, "quantity": 1, "buying_price": 1, "selling_price": 1}
    ).to_list(10000)
    
    emp_stats = {}
    for booking in bookings:
        emp_id = booking.get("created_by")
        if not emp_id or emp_id not in employee_map:
            continue
        
        if emp_id not in emp_stats:
            emp_info = employee_map[emp_id]
            emp_stats[emp_id] = {
                "employee_id": emp_id,
                "name": emp_info.get("name", "Unknown"),
                "email": emp_info.get("email", ""),
                "role": ROLES.get(emp_info.get("role", 4), "Employee"),
                "total_bookings": 0,
                "total_revenue": 0,
                "total_profit": 0
            }
        
        qty = booking.get("quantity", 0)
        revenue = booking.get("selling_price", 0) * qty
        cost = booking.get("buying_price", 0) * qty
        
        emp_stats[emp_id]["total_bookings"] += 1
        emp_stats[emp_id]["total_revenue"] += revenue
        emp_stats[emp_id]["total_profit"] += revenue - cost
    
    return list(emp_stats.values())


@router.get("/sector-distribution")
async def get_sector_distribution(
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("analytics.view", "view sector distribution"))
):
    """Get sector-wise distribution of bookings"""
    stocks = await db.stocks.find({}, {"_id": 0, "id": 1, "sector": 1}).to_list(1000)
    stock_sectors = {s["id"]: s.get("sector", "Other") for s in stocks}
    
    bookings = await db.bookings.find(
        {"status": {"$ne": "cancelled"}},
        {"_id": 0, "stock_id": 1, "quantity": 1, "selling_price": 1}
    ).to_list(10000)
    
    sector_stats = {}
    for booking in bookings:
        stock_id = booking.get("stock_id")
        sector = stock_sectors.get(stock_id, "Other") or "Other"
        
        if sector not in sector_stats:
            sector_stats[sector] = {"sector": sector, "count": 0, "revenue": 0}
        
        qty = booking.get("quantity", 0)
        sector_stats[sector]["count"] += 1
        sector_stats[sector]["revenue"] += booking.get("selling_price", 0) * qty
    
    return list(sector_stats.values())


@router.get("/daily-trend")
async def get_daily_trend(
    days: int = Query(30, ge=1, le=365),
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("analytics.view", "view daily trend"))
):
    """Get daily booking trend for the last N days"""
    start_date = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    
    bookings = await db.bookings.find(
        {"created_at": {"$gte": start_date}, "status": {"$ne": "cancelled"}},
        {"_id": 0, "created_at": 1, "quantity": 1, "selling_price": 1, "buying_price": 1}
    ).to_list(10000)
    
    daily_stats = {}
    for booking in bookings:
        date = booking.get("created_at", "")[:10]  # Get YYYY-MM-DD
        if not date:
            continue
        
        if date not in daily_stats:
            daily_stats[date] = {"date": date, "bookings": 0, "revenue": 0, "profit": 0}
        
        qty = booking.get("quantity", 0)
        revenue = booking.get("selling_price", 0) * qty
        cost = booking.get("buying_price", 0) * qty
        
        daily_stats[date]["bookings"] += 1
        daily_stats[date]["revenue"] += revenue
        daily_stats[date]["profit"] += revenue - cost
    
    # Sort by date
    result = sorted(daily_stats.values(), key=lambda x: x["date"])
    return result
