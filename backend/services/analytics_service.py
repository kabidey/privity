"""
Analytics service for advanced dashboard
"""
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any
from database import db

async def get_analytics_summary(days: int = 30) -> Dict[str, Any]:
    """Get comprehensive analytics summary for PE Desk"""
    start_date = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    
    # Get all closed bookings
    bookings = await db.bookings.find(
        {"status": "closed", "approval_status": "approved"},
        {"_id": 0}
    ).to_list(10000)
    
    # Get recent bookings for trend
    recent_bookings = [b for b in bookings if b.get("created_at", "") >= start_date]
    
    # Calculate totals
    total_revenue = sum(b.get("selling_price", 0) * b.get("quantity", 0) for b in bookings)
    total_cost = sum(b.get("buying_price", 0) * b.get("quantity", 0) for b in bookings)
    total_profit = total_revenue - total_cost
    
    # Get clients count
    clients_count = await db.clients.count_documents({"is_vendor": False, "is_active": True})
    
    avg_booking_value = total_revenue / len(bookings) if bookings else 0
    profit_margin = (total_profit / total_revenue * 100) if total_revenue > 0 else 0
    
    # Get stock performance
    stock_performance = await get_stock_performance(bookings)
    
    # Get employee performance
    employee_performance = await get_employee_performance(bookings)
    
    # Get daily trend
    daily_trend = await get_daily_trend(days)
    
    # Get client growth
    client_growth = await get_client_growth(days)
    
    # Get sector distribution
    sector_distribution = await get_sector_distribution(bookings)
    
    return {
        "total_revenue": round(total_revenue, 2),
        "total_profit": round(total_profit, 2),
        "total_bookings": len(bookings),
        "total_clients": clients_count,
        "avg_booking_value": round(avg_booking_value, 2),
        "profit_margin": round(profit_margin, 2),
        "top_stocks": stock_performance[:10],
        "top_employees": employee_performance[:10],
        "daily_trend": daily_trend,
        "client_growth": client_growth,
        "sector_distribution": sector_distribution
    }

async def get_stock_performance(bookings: List[Dict]) -> List[Dict]:
    """Get performance by stock"""
    stock_stats = {}
    
    for booking in bookings:
        stock_id = booking.get("stock_id")
        if not stock_id:
            continue
            
        if stock_id not in stock_stats:
            stock_stats[stock_id] = {
                "stock_id": stock_id,
                "total_quantity": 0,
                "total_revenue": 0,
                "total_cost": 0
            }
        
        qty = booking.get("quantity", 0)
        stock_stats[stock_id]["total_quantity"] += qty
        stock_stats[stock_id]["total_revenue"] += booking.get("selling_price", 0) * qty
        stock_stats[stock_id]["total_cost"] += booking.get("buying_price", 0) * qty
    
    # Get stock details
    stock_ids = list(stock_stats.keys())
    stocks = await db.stocks.find({"id": {"$in": stock_ids}}, {"_id": 0}).to_list(1000)
    stock_map = {s["id"]: s for s in stocks}
    
    result = []
    for stock_id, stats in stock_stats.items():
        stock = stock_map.get(stock_id, {})
        profit = stats["total_revenue"] - stats["total_cost"]
        margin = (profit / stats["total_revenue"] * 100) if stats["total_revenue"] > 0 else 0
        
        result.append({
            "stock_id": stock_id,
            "stock_symbol": stock.get("symbol", "Unknown"),
            "stock_name": stock.get("name", "Unknown"),
            "total_quantity_sold": stats["total_quantity"],
            "total_revenue": round(stats["total_revenue"], 2),
            "total_cost": round(stats["total_cost"], 2),
            "profit_loss": round(profit, 2),
            "profit_margin": round(margin, 2)
        })
    
    # Sort by profit
    result.sort(key=lambda x: x["profit_loss"], reverse=True)
    return result

async def get_employee_performance(bookings: List[Dict]) -> List[Dict]:
    """Get performance by employee"""
    emp_stats = {}
    
    for booking in bookings:
        user_id = booking.get("created_by")
        if not user_id:
            continue
            
        if user_id not in emp_stats:
            emp_stats[user_id] = {
                "user_id": user_id,
                "total_bookings": 0,
                "total_value": 0,
                "total_profit": 0,
                "client_ids": set()
            }
        
        qty = booking.get("quantity", 0)
        revenue = booking.get("selling_price", 0) * qty
        cost = booking.get("buying_price", 0) * qty
        
        emp_stats[user_id]["total_bookings"] += 1
        emp_stats[user_id]["total_value"] += revenue
        emp_stats[user_id]["total_profit"] += revenue - cost
        emp_stats[user_id]["client_ids"].add(booking.get("client_id"))
    
    # Get user details
    user_ids = list(emp_stats.keys())
    users = await db.users.find({"id": {"$in": user_ids}}, {"_id": 0, "hashed_password": 0}).to_list(1000)
    user_map = {u["id"]: u for u in users}
    
    result = []
    for user_id, stats in emp_stats.items():
        user = user_map.get(user_id, {})
        result.append({
            "user_id": user_id,
            "user_name": user.get("name", "Unknown"),
            "total_bookings": stats["total_bookings"],
            "total_value": round(stats["total_value"], 2),
            "total_profit": round(stats["total_profit"], 2),
            "clients_count": len(stats["client_ids"])
        })
    
    # Sort by profit
    result.sort(key=lambda x: x["total_profit"], reverse=True)
    return result

async def get_daily_trend(days: int = 30) -> List[Dict]:
    """Get daily booking trend"""
    result = []
    
    for i in range(days, -1, -1):
        date = (datetime.now(timezone.utc) - timedelta(days=i)).strftime("%Y-%m-%d")
        date_start = f"{date}T00:00:00"
        date_end = f"{date}T23:59:59"
        
        # Get bookings for this day
        bookings = await db.bookings.find({
            "created_at": {"$gte": date_start, "$lte": date_end},
            "approval_status": "approved"
        }, {"_id": 0}).to_list(1000)
        
        # Get new clients for this day
        new_clients = await db.clients.count_documents({
            "created_at": {"$gte": date_start, "$lte": date_end},
            "is_vendor": False
        })
        
        bookings_value = sum(b.get("selling_price", 0) * b.get("quantity", 0) for b in bookings)
        profit_loss = sum(
            (b.get("selling_price", 0) - b.get("buying_price", 0)) * b.get("quantity", 0)
            for b in bookings if b.get("status") == "closed"
        )
        
        result.append({
            "date": date,
            "bookings_count": len(bookings),
            "bookings_value": round(bookings_value, 2),
            "profit_loss": round(profit_loss, 2),
            "new_clients": new_clients
        })
    
    return result

async def get_client_growth(days: int = 30) -> List[Dict]:
    """Get client growth over time"""
    result = []
    
    # Group by week
    for i in range(0, days, 7):
        week_end = datetime.now(timezone.utc) - timedelta(days=i)
        week_start = week_end - timedelta(days=7)
        
        # Count clients created in this period
        count = await db.clients.count_documents({
            "created_at": {
                "$gte": week_start.isoformat(),
                "$lte": week_end.isoformat()
            },
            "is_vendor": False
        })
        
        # Total clients up to this point
        total = await db.clients.count_documents({
            "created_at": {"$lte": week_end.isoformat()},
            "is_vendor": False
        })
        
        result.append({
            "week": week_end.strftime("%Y-%m-%d"),
            "new_clients": count,
            "total_clients": total
        })
    
    result.reverse()
    return result

async def get_sector_distribution(bookings: List[Dict]) -> List[Dict]:
    """Get booking distribution by sector"""
    # Get all stocks with sectors
    stock_ids = list(set(b.get("stock_id") for b in bookings if b.get("stock_id")))
    stocks = await db.stocks.find({"id": {"$in": stock_ids}}, {"_id": 0}).to_list(1000)
    stock_map = {s["id"]: s for s in stocks}
    
    sector_stats = {}
    
    for booking in bookings:
        stock = stock_map.get(booking.get("stock_id"), {})
        sector = stock.get("sector") or "Unknown"
        
        if sector not in sector_stats:
            sector_stats[sector] = {
                "sector": sector,
                "bookings_count": 0,
                "total_value": 0
            }
        
        qty = booking.get("quantity", 0)
        sector_stats[sector]["bookings_count"] += 1
        sector_stats[sector]["total_value"] += booking.get("selling_price", 0) * qty
    
    result = list(sector_stats.values())
    result.sort(key=lambda x: x["total_value"], reverse=True)
    
    return result
