"""
Dashboard Router
Handles dashboard stats and overview endpoints
"""
from typing import Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends

from database import db
from config import is_pe_level
from models import DashboardStats
from utils.auth import get_current_user

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(current_user: dict = Depends(get_current_user)):
    """Get dashboard statistics"""
    user_role = current_user.get("role", 6)
    user_id = current_user.get("id")
    
    # Base query - PE level sees all, others see only their own
    base_query = {}
    if not is_pe_level(user_role):
        base_query["created_by"] = user_id
    
    # Count totals
    total_clients = await db.clients.count_documents({"is_active": True, "is_vendor": False})
    total_vendors = await db.clients.count_documents({"is_active": True, "is_vendor": True})
    total_stocks = await db.stocks.count_documents({"is_active": True})
    total_bookings = await db.bookings.count_documents({**base_query, "status": {"$ne": "cancelled"}})
    open_bookings = await db.bookings.count_documents({**base_query, "status": "open", "is_voided": {"$ne": True}})
    closed_bookings = await db.bookings.count_documents({**base_query, "status": "closed", "is_voided": {"$ne": True}})
    total_purchases = await db.purchases.count_documents({})
    
    # Calculate inventory value
    inventory_items = await db.inventory.find({}, {"_id": 0, "total_value": 1}).to_list(10000)
    total_inventory_value = sum(item.get("total_value", 0) for item in inventory_items)
    
    # Calculate revenue and profit
    bookings = await db.bookings.find(
        {**base_query, "status": {"$ne": "cancelled"}, "is_voided": {"$ne": True}},
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
async def get_dashboard_analytics(current_user: dict = Depends(get_current_user)):
    """Get detailed dashboard analytics"""
    user_role = current_user.get("role", 6)
    user_id = current_user.get("id")
    
    base_query = {}
    if not is_pe_level(user_role):
        base_query["created_by"] = user_id
    
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
