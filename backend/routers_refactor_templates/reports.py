"""
Reports and Dashboard routes including PnL, analytics, and audit logs
"""
import io
from datetime import datetime, timezone, timedelta
from typing import Optional

import pandas as pd
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse, Response
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER

from database import db
from config import ROLES, ROLE_PERMISSIONS
from models import DashboardStats
from utils.auth import get_current_user, check_permission

router = APIRouter(tags=["Reports & Analytics"])


@router.get("/dashboard/stats", response_model=DashboardStats)
async def get_dashboard_stats(current_user: dict = Depends(get_current_user)):
    """Get dashboard statistics"""
    query_filter = {}
    if current_user.get("role", 5) >= 3:
        if "view_all" not in ROLE_PERMISSIONS.get(current_user.get("role", 5), []):
            query_filter = {"created_by": current_user["id"]}
    
    total_clients = await db.clients.count_documents({})
    total_vendors = await db.clients.count_documents({"is_vendor": True})
    total_stocks = await db.stocks.count_documents({})
    total_bookings = await db.bookings.count_documents(query_filter)
    open_bookings = await db.bookings.count_documents({**query_filter, "status": "open"})
    closed_bookings = await db.bookings.count_documents({**query_filter, "status": "closed"})
    total_purchases = await db.purchases.count_documents({})
    
    bookings = await db.bookings.find({**query_filter, "status": "closed"}, {"_id": 0}).to_list(1000)
    total_profit_loss = sum(
        (b["selling_price"] - b["buying_price"]) * b["quantity"]
        for b in bookings if b.get("selling_price")
    )
    
    inventory_items = await db.inventory.find({}, {"_id": 0}).to_list(1000)
    total_inventory_value = sum(item.get("total_value", 0) for item in inventory_items)
    
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


@router.get("/dashboard/analytics")
async def get_dashboard_analytics(current_user: dict = Depends(get_current_user)):
    """Get analytics data for charts"""
    query_filter = {}
    if current_user.get("role", 5) >= 3:
        if "view_all" not in ROLE_PERMISSIONS.get(current_user.get("role", 5), []):
            query_filter = {"created_by": current_user["id"]}
    
    bookings = await db.bookings.find({**query_filter, "status": "closed"}, {"_id": 0}).to_list(10000)
    
    monthly_pnl = {}
    for booking in bookings:
        if booking.get("selling_price"):
            booking_date = datetime.fromisoformat(booking["booking_date"]).strftime("%Y-%m")
            pnl = (booking["selling_price"] - booking["buying_price"]) * booking["quantity"]
            monthly_pnl[booking_date] = monthly_pnl.get(booking_date, 0) + pnl
    
    stock_performance = {}
    for booking in bookings:
        if booking.get("selling_price"):
            stock_id = booking["stock_id"]
            pnl = (booking["selling_price"] - booking["buying_price"]) * booking["quantity"]
            if stock_id not in stock_performance:
                stock_performance[stock_id] = {"pnl": 0, "quantity": 0}
            stock_performance[stock_id]["pnl"] += pnl
            stock_performance[stock_id]["quantity"] += booking["quantity"]
    
    stock_ids = list(stock_performance.keys())
    stocks = await db.stocks.find({"id": {"$in": stock_ids}}, {"_id": 0}).to_list(1000)
    stock_map = {s["id"]: s for s in stocks}
    
    top_stocks = [
        {
            "stock_symbol": stock_map.get(stock_id, {}).get("symbol", "Unknown"),
            "pnl": data["pnl"],
            "quantity": data["quantity"]
        }
        for stock_id, data in sorted(stock_performance.items(), key=lambda x: x[1]["pnl"], reverse=True)[:10]
    ]
    
    return {
        "monthly_pnl": [{"month": k, "pnl": v} for k, v in sorted(monthly_pnl.items())],
        "top_stocks": top_stocks
    }


@router.get("/reports/pnl")
async def get_pnl_report(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    client_id: Optional[str] = None,
    stock_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get P&L report with filters"""
    check_permission(current_user, "view_reports")
    
    query = {}
    if start_date:
        query["booking_date"] = {"$gte": start_date}
    if end_date:
        if "booking_date" in query:
            query["booking_date"]["$lte"] = end_date
        else:
            query["booking_date"] = {"$lte": end_date}
    if client_id:
        query["client_id"] = client_id
    if stock_id:
        query["stock_id"] = stock_id
    
    bookings = await db.bookings.find(query, {"_id": 0, "user_id": 0}).to_list(1000)
    
    if not bookings:
        return []
    
    client_ids = list(set(b["client_id"] for b in bookings))
    stock_ids = list(set(b["stock_id"] for b in bookings))
    
    clients = await db.clients.find({"id": {"$in": client_ids}}, {"_id": 0}).to_list(1000)
    stocks = await db.stocks.find({"id": {"$in": stock_ids}}, {"_id": 0}).to_list(1000)
    
    client_map = {c["id"]: c for c in clients}
    stock_map = {s["id"]: s for s in stocks}
    
    report = []
    for booking in bookings:
        client = client_map.get(booking["client_id"])
        stock = stock_map.get(booking["stock_id"])
        
        profit_loss = None
        if booking.get("selling_price") and booking["status"] == "closed":
            profit_loss = (booking["selling_price"] - booking["buying_price"]) * booking["quantity"]
        
        report.append({
            "booking_id": booking["id"],
            "client_name": client["name"] if client else "Unknown",
            "stock_symbol": stock["symbol"] if stock else "Unknown",
            "stock_name": stock["name"] if stock else "Unknown",
            "quantity": booking["quantity"],
            "buying_price": booking["buying_price"],
            "selling_price": booking.get("selling_price"),
            "booking_date": booking["booking_date"],
            "status": booking["status"],
            "profit_loss": profit_loss
        })
    
    return report


@router.get("/reports/export/excel")
async def export_excel(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Export P&L report as Excel"""
    check_permission(current_user, "view_reports")
    
    query = {"status": "closed"}
    if start_date:
        query["booking_date"] = {"$gte": start_date}
    if end_date:
        if "booking_date" in query:
            query["booking_date"]["$lte"] = end_date
        else:
            query["booking_date"] = {"$lte": end_date}
    
    bookings = await db.bookings.find(query, {"_id": 0}).to_list(10000)
    
    if not bookings:
        raise HTTPException(status_code=404, detail="No data to export")
    
    client_ids = list(set(b["client_id"] for b in bookings))
    stock_ids = list(set(b["stock_id"] for b in bookings))
    
    clients = await db.clients.find({"id": {"$in": client_ids}}, {"_id": 0}).to_list(1000)
    stocks = await db.stocks.find({"id": {"$in": stock_ids}}, {"_id": 0}).to_list(1000)
    
    client_map = {c["id"]: c for c in clients}
    stock_map = {s["id"]: s for s in stocks}
    
    data = []
    for b in bookings:
        client = client_map.get(b["client_id"], {})
        stock = stock_map.get(b["stock_id"], {})
        profit_loss = (b.get("selling_price", 0) - b["buying_price"]) * b["quantity"]
        
        data.append({
            "Client": client.get("name", "Unknown"),
            "Stock": stock.get("symbol", "Unknown"),
            "Quantity": b["quantity"],
            "Buy Price": b["buying_price"],
            "Sell Price": b.get("selling_price", 0),
            "P&L": profit_loss,
            "Date": b["booking_date"]
        })
    
    df = pd.DataFrame(data)
    buffer = io.BytesIO()
    df.to_excel(buffer, index=False, engine='openpyxl')
    buffer.seek(0)
    
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=pnl_report_{datetime.now().strftime('%Y%m%d')}.xlsx"}
    )


@router.get("/reports/export/pdf")
async def export_pdf(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Export P&L report as PDF"""
    check_permission(current_user, "view_reports")
    
    query = {"status": "closed"}
    if start_date:
        query["booking_date"] = {"$gte": start_date}
    if end_date:
        if "booking_date" in query:
            query["booking_date"]["$lte"] = end_date
        else:
            query["booking_date"] = {"$lte": end_date}
    
    bookings = await db.bookings.find(query, {"_id": 0}).to_list(10000)
    
    if not bookings:
        raise HTTPException(status_code=404, detail="No data to export")
    
    client_ids = list(set(b["client_id"] for b in bookings))
    stock_ids = list(set(b["stock_id"] for b in bookings))
    
    clients = await db.clients.find({"id": {"$in": client_ids}}, {"_id": 0}).to_list(1000)
    stocks = await db.stocks.find({"id": {"$in": stock_ids}}, {"_id": 0}).to_list(1000)
    
    client_map = {c["id"]: c for c in clients}
    stock_map = {s["id"]: s for s in stocks}
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('Title', parent=styles['Heading1'], alignment=TA_CENTER)
    
    elements.append(Paragraph("P&L Report", title_style))
    elements.append(Spacer(1, 20))
    
    table_data = [["Client", "Stock", "Qty", "Buy", "Sell", "P&L", "Date"]]
    total_pnl = 0
    
    for b in bookings:
        client = client_map.get(b["client_id"], {})
        stock = stock_map.get(b["stock_id"], {})
        profit_loss = (b.get("selling_price", 0) - b["buying_price"]) * b["quantity"]
        total_pnl += profit_loss
        
        table_data.append([
            client.get("name", "Unknown")[:15],
            stock.get("symbol", "Unknown")[:10],
            str(b["quantity"]),
            f"₹{b['buying_price']:.2f}",
            f"₹{b.get('selling_price', 0):.2f}",
            f"₹{profit_loss:.2f}",
            b["booking_date"]
        ])
    
    table_data.append(["", "", "", "", "Total:", f"₹{total_pnl:.2f}", ""])
    
    table = Table(table_data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
    ]))
    
    elements.append(table)
    doc.build(elements)
    buffer.seek(0)
    
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=pnl_report_{datetime.now().strftime('%Y%m%d')}.pdf"}
    )


# ============== Audit Logs ==============

@router.get("/audit-logs")
async def get_audit_logs(
    entity_type: Optional[str] = None,
    action: Optional[str] = None,
    user_id: Optional[str] = None,
    limit: int = 100,
    current_user: dict = Depends(get_current_user)
):
    """Get audit logs (admin only)"""
    if current_user.get("role", 5) > 2:
        raise HTTPException(status_code=403, detail="Only admins can view audit logs")
    
    query = {}
    if entity_type:
        query["entity_type"] = entity_type
    if action:
        query["action"] = action
    if user_id:
        query["user_id"] = user_id
    
    logs = await db.audit_logs.find(query, {"_id": 0}).sort("timestamp", -1).to_list(limit)
    return logs


@router.get("/audit-logs/stats")
async def get_audit_stats(current_user: dict = Depends(get_current_user)):
    """Get audit log statistics"""
    if current_user.get("role", 5) > 2:
        raise HTTPException(status_code=403, detail="Only admins can view audit stats")
    
    total_logs = await db.audit_logs.count_documents({})
    
    pipeline = [
        {"$group": {"_id": "$action", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    action_counts = await db.audit_logs.aggregate(pipeline).to_list(100)
    
    return {
        "total_logs": total_logs,
        "by_action": {item["_id"]: item["count"] for item in action_counts}
    }


# ============== Advanced Analytics (PE Desk Only) ==============

@router.get("/analytics/summary")
async def get_analytics_summary(
    days: int = 30,
    current_user: dict = Depends(get_current_user)
):
    """Get analytics summary (PE Desk only)"""
    if current_user.get("role") != 1:
        raise HTTPException(status_code=403, detail="Only PE Desk can access advanced analytics")
    
    start_date = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    
    bookings = await db.bookings.find(
        {"status": "closed", "approval_status": "approved", "booking_date": {"$gte": start_date}},
        {"_id": 0}
    ).to_list(10000)
    
    total_revenue = sum(b.get("selling_price", 0) * b.get("quantity", 0) for b in bookings)
    total_cost = sum(b.get("buying_price", 0) * b.get("quantity", 0) for b in bookings)
    total_profit = total_revenue - total_cost
    
    total_clients = await db.clients.count_documents({"is_vendor": False})
    
    return {
        "total_revenue": round(total_revenue, 2),
        "total_profit": round(total_profit, 2),
        "total_bookings": len(bookings),
        "total_clients": total_clients,
        "avg_booking_value": round(total_revenue / len(bookings), 2) if bookings else 0,
        "profit_margin": round((total_profit / total_revenue) * 100, 2) if total_revenue else 0,
        "period_days": days
    }


@router.get("/analytics/stock-performance")
async def get_stock_performance(
    days: int = 30,
    limit: int = 10,
    current_user: dict = Depends(get_current_user)
):
    """Get stock performance analytics (PE Desk only)"""
    if current_user.get("role") != 1:
        raise HTTPException(status_code=403, detail="Only PE Desk can access advanced analytics")
    
    bookings = await db.bookings.find(
        {"status": "closed", "approval_status": "approved"},
        {"_id": 0}
    ).to_list(10000)
    
    stock_stats = {}
    for booking in bookings:
        stock_id = booking.get("stock_id")
        if not stock_id:
            continue
        
        if stock_id not in stock_stats:
            stock_stats[stock_id] = {
                "total_quantity": 0,
                "total_revenue": 0,
                "total_cost": 0,
                "bookings_count": 0
            }
        
        qty = booking.get("quantity", 0)
        revenue = booking.get("selling_price", 0) * qty
        cost = booking.get("buying_price", 0) * qty
        
        stock_stats[stock_id]["total_quantity"] += qty
        stock_stats[stock_id]["total_revenue"] += revenue
        stock_stats[stock_id]["total_cost"] += cost
        stock_stats[stock_id]["bookings_count"] += 1
    
    stock_ids = list(stock_stats.keys())
    stocks = await db.stocks.find({"id": {"$in": stock_ids}}, {"_id": 0}).to_list(1000)
    stock_map = {s["id"]: s for s in stocks}
    
    result = []
    for stock_id, stats in stock_stats.items():
        stock = stock_map.get(stock_id, {})
        result.append({
            "stock_id": stock_id,
            "stock_symbol": stock.get("symbol", "Unknown"),
            "stock_name": stock.get("name", "Unknown"),
            "sector": stock.get("sector", "Unknown"),
            "total_quantity": stats["total_quantity"],
            "total_revenue": round(stats["total_revenue"], 2),
            "profit_loss": round(stats["total_revenue"] - stats["total_cost"], 2),
            "bookings_count": stats["bookings_count"]
        })
    
    result.sort(key=lambda x: x["profit_loss"], reverse=True)
    return result[:limit]


@router.get("/analytics/employee-performance")
async def get_employee_performance(
    days: int = 30,
    limit: int = 10,
    current_user: dict = Depends(get_current_user)
):
    """Get employee performance analytics (PE Desk only)"""
    if current_user.get("role") != 1:
        raise HTTPException(status_code=403, detail="Only PE Desk can access advanced analytics")
    
    bookings = await db.bookings.find(
        {"status": "closed", "approval_status": "approved"},
        {"_id": 0}
    ).to_list(10000)
    
    emp_stats = {}
    for booking in bookings:
        user_id = booking.get("created_by")
        if not user_id:
            continue
        
        if user_id not in emp_stats:
            emp_stats[user_id] = {
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
    
    user_ids = list(emp_stats.keys())
    users = await db.users.find({"id": {"$in": user_ids}}, {"_id": 0, "hashed_password": 0}).to_list(1000)
    user_map = {u["id"]: u for u in users}
    
    result = []
    for user_id, stats in emp_stats.items():
        user = user_map.get(user_id, {})
        result.append({
            "user_id": user_id,
            "user_name": user.get("name", "Unknown"),
            "role": user.get("role", 5),
            "role_name": ROLES.get(user.get("role", 5), "Unknown"),
            "total_bookings": stats["total_bookings"],
            "total_value": round(stats["total_value"], 2),
            "total_profit": round(stats["total_profit"], 2),
            "clients_count": len(stats["client_ids"])
        })
    
    result.sort(key=lambda x: x["total_profit"], reverse=True)
    return result[:limit]


@router.get("/analytics/daily-trend")
async def get_daily_trend(
    days: int = 30,
    current_user: dict = Depends(get_current_user)
):
    """Get daily booking trend (PE Desk only)"""
    if current_user.get("role") != 1:
        raise HTTPException(status_code=403, detail="Only PE Desk can access advanced analytics")
    
    result = []
    
    for i in range(days, -1, -1):
        date = (datetime.now(timezone.utc) - timedelta(days=i)).strftime("%Y-%m-%d")
        date_start = f"{date}T00:00:00"
        date_end = f"{date}T23:59:59"
        
        bookings = await db.bookings.find({
            "created_at": {"$gte": date_start, "$lte": date_end},
            "approval_status": "approved"
        }, {"_id": 0}).to_list(1000)
        
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


@router.get("/analytics/sector-distribution")
async def get_sector_distribution(current_user: dict = Depends(get_current_user)):
    """Get booking distribution by sector (PE Desk only)"""
    if current_user.get("role") != 1:
        raise HTTPException(status_code=403, detail="Only PE Desk can access advanced analytics")
    
    bookings = await db.bookings.find(
        {"status": "closed", "approval_status": "approved"},
        {"_id": 0}
    ).to_list(10000)
    
    stock_ids = list(set(b.get("stock_id") for b in bookings if b.get("stock_id")))
    stocks = await db.stocks.find({"id": {"$in": stock_ids}}, {"_id": 0}).to_list(1000)
    stock_map = {s["id"]: s for s in stocks}
    
    sector_stats = {}
    for booking in bookings:
        stock = stock_map.get(booking.get("stock_id"), {})
        sector = stock.get("sector") or "Unknown"
        
        if sector not in sector_stats:
            sector_stats[sector] = {"bookings_count": 0, "total_value": 0, "total_profit": 0}
        
        qty = booking.get("quantity", 0)
        revenue = booking.get("selling_price", 0) * qty
        cost = booking.get("buying_price", 0) * qty
        
        sector_stats[sector]["bookings_count"] += 1
        sector_stats[sector]["total_value"] += revenue
        sector_stats[sector]["total_profit"] += revenue - cost
    
    result = [
        {
            "sector": sector,
            **stats,
            "total_value": round(stats["total_value"], 2),
            "total_profit": round(stats["total_profit"], 2)
        }
        for sector, stats in sector_stats.items()
    ]
    
    result.sort(key=lambda x: x["total_value"], reverse=True)
    return result


# ============== DP Transfer Report ==============

@router.get("/dp-transfer-report")
async def get_dp_transfer_report(current_user: dict = Depends(get_current_user)):
    """Get bookings ready for DP transfer (PE Desk & Zonal Manager only)"""
    if current_user.get("role", 5) not in [1, 2]:
        raise HTTPException(status_code=403, detail="Only PE Desk and Zonal Manager can access DP transfer report")
    
    bookings = await db.bookings.find(
        {"dp_transfer_ready": True, "approval_status": "approved"},
        {"_id": 0}
    ).to_list(10000)
    
    if not bookings:
        return []
    
    client_ids = list(set(b.get("client_id") for b in bookings))
    stock_ids = list(set(b.get("stock_id") for b in bookings))
    
    clients = await db.clients.find({"id": {"$in": client_ids}}, {"_id": 0}).to_list(1000)
    stocks = await db.stocks.find({"id": {"$in": stock_ids}}, {"_id": 0}).to_list(1000)
    
    client_map = {c["id"]: c for c in clients}
    stock_map = {s["id"]: s for s in stocks}
    
    result = []
    for booking in bookings:
        client = client_map.get(booking.get("client_id"), {})
        stock = stock_map.get(booking.get("stock_id"), {})
        
        total_amount = (booking.get("selling_price") or 0) * booking.get("quantity", 0)
        
        result.append({
            "booking_id": booking["id"],
            "client_name": client.get("name", "Unknown"),
            "pan_number": client.get("pan_number", "N/A"),
            "dp_id": client.get("dp_id", "N/A"),
            "stock_symbol": stock.get("symbol", "Unknown"),
            "stock_name": stock.get("name", "Unknown"),
            "isin_number": stock.get("isin_number", "N/A"),
            "quantity": booking.get("quantity", 0),
            "total_amount": total_amount,
            "total_paid": booking.get("total_paid", 0),
            "payment_completed_at": booking.get("payment_completed_at", ""),
            "booking_date": booking.get("booking_date", ""),
            "payments": booking.get("payments", [])
        })
    
    result.sort(key=lambda x: x.get("payment_completed_at", ""), reverse=True)
    return result


@router.get("/dp-transfer-report/export")
async def export_dp_transfer_report(
    format: str = "csv",
    current_user: dict = Depends(get_current_user)
):
    """Export DP transfer report as CSV or Excel"""
    if current_user.get("role", 5) not in [1, 2]:
        raise HTTPException(status_code=403, detail="Only PE Desk and Zonal Manager can export DP transfer report")
    
    bookings = await db.bookings.find(
        {"dp_transfer_ready": True, "approval_status": "approved"},
        {"_id": 0}
    ).to_list(10000)
    
    if not bookings:
        raise HTTPException(status_code=404, detail="No records to export")
    
    client_ids = list(set(b.get("client_id") for b in bookings))
    stock_ids = list(set(b.get("stock_id") for b in bookings))
    
    clients = await db.clients.find({"id": {"$in": client_ids}}, {"_id": 0}).to_list(1000)
    stocks = await db.stocks.find({"id": {"$in": stock_ids}}, {"_id": 0}).to_list(1000)
    
    client_map = {c["id"]: c for c in clients}
    stock_map = {s["id"]: s for s in stocks}
    
    rows = []
    for booking in bookings:
        client = client_map.get(booking.get("client_id"), {})
        stock = stock_map.get(booking.get("stock_id"), {})
        
        rows.append({
            "Client Name": client.get("name", "Unknown"),
            "PAN Number": client.get("pan_number", "N/A"),
            "DP ID": client.get("dp_id", "N/A"),
            "Stock Symbol": stock.get("symbol", "Unknown"),
            "Stock Name": stock.get("name", "Unknown"),
            "ISIN": stock.get("isin_number", "N/A"),
            "Quantity": booking.get("quantity", 0),
            "Total Amount": (booking.get("selling_price") or 0) * booking.get("quantity", 0),
            "Total Paid": booking.get("total_paid", 0),
            "Payment Completed Date": booking.get("payment_completed_at", ""),
            "Booking Date": booking.get("booking_date", "")
        })
    
    df = pd.DataFrame(rows)
    
    if format == "excel":
        buffer = io.BytesIO()
        df.to_excel(buffer, index=False, engine='openpyxl')
        buffer.seek(0)
        return StreamingResponse(
            buffer,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=dp_transfer_report.xlsx"}
        )
    else:
        buffer = io.StringIO()
        df.to_csv(buffer, index=False)
        buffer.seek(0)
        return StreamingResponse(
            io.BytesIO(buffer.getvalue().encode()),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=dp_transfer_report.csv"}
        )
