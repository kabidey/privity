"""
Inventory Router
Handles inventory management endpoints
"""
from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
import logging

from database import db
from models import Inventory as InventoryModel
from utils.auth import get_current_user
from services.permission_service import (
    has_permission,
    check_permission as check_dynamic_permission,
    require_permission
)
from utils.demo_isolation import is_demo_user, add_demo_filter, mark_as_demo, require_demo_access

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/inventory", tags=["Inventory"])


# Helper function for backward compatibility
def is_pe_level(role: int) -> bool:
    """Check if role is PE level (PE Desk or PE Manager)."""
    return role in [1, 2]


class UpdateLandingPriceRequest(BaseModel):
    landing_price: float


async def calculate_weighted_avg_for_stock(stock_id: str) -> dict:
    """
    Calculate weighted average price from ALL purchases for a stock.
    This ensures accurate pricing based on actual purchase history.
    """
    # Get ALL purchases for this stock (to calculate true weighted average)
    purchases = await db.purchases.find(
        {"stock_id": stock_id},
        {"_id": 0, "quantity": 1, "total_amount": 1}
    ).to_list(10000)
    
    if not purchases:
        # Fallback: Use stored inventory values if no purchases
        inventory = await db.inventory.find_one({"stock_id": stock_id}, {"_id": 0})
        if inventory:
            return {
                "weighted_avg_price": inventory.get("weighted_avg_price", 0),
                "total_value": inventory.get("total_value", 0)
            }
        return {"weighted_avg_price": 0, "total_value": 0}
    
    # Calculate weighted average from all purchases
    total_quantity = sum(p.get("quantity", 0) for p in purchases)
    total_purchase_value = sum(p.get("total_amount", 0) for p in purchases)
    
    weighted_avg = total_purchase_value / total_quantity if total_quantity > 0 else 0
    
    # Get current inventory quantity for total_value calculation
    inventory = await db.inventory.find_one({"stock_id": stock_id}, {"_id": 0, "available_quantity": 1})
    current_qty = inventory.get("available_quantity", 0) if inventory else 0
    
    # Total value = current inventory quantity * weighted average price
    total_value = current_qty * weighted_avg
    
    return {
        "weighted_avg_price": round(weighted_avg, 2),
        "total_value": round(total_value, 2)
    }


@router.get("")
async def get_inventory(
    search: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(1000, ge=1, le=10000),
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("inventory.view", "view inventory"))
):
    """
    Get all inventory items with dynamically calculated weighted average pricing.
    
    Args:
        search: Search query to filter by stock symbol, name, or ISIN
        skip: Number of records to skip (for pagination)
        limit: Maximum number of records to return
    
    - PE Desk/Manager: See both WAP (Weighted Avg Price) and LP (Landing Price)
    - Other users: Only see LP (Landing Price) - WAP is hidden
    """
    user_role = current_user.get("role", 6)
    is_pe = is_pe_level(user_role)
    
    # Build query with demo isolation filter
    query = {}
    query = add_demo_filter(query, current_user)
    
    # If search is provided, first find matching stock IDs
    stock_filter = {}
    if search:
        search_regex = {"$regex": search, "$options": "i"}
        stock_filter = {"$or": [
            {"symbol": search_regex},
            {"name": search_regex},
            {"isin": search_regex}
        ]}
    
    # Get matching stock IDs
    if stock_filter:
        matching_stocks = await db.stocks.find(stock_filter, {"_id": 0, "id": 1}).to_list(10000)
        matching_stock_ids = [s["id"] for s in matching_stocks]
        if matching_stock_ids:
            query["stock_id"] = {"$in": matching_stock_ids}
        else:
            # No matching stocks, return empty
            return []
    
    inventory = await db.inventory.find(query, {"_id": 0}).skip(skip).limit(limit).to_list(limit)
    
    # Enrich with stock details
    stock_ids = list(set(item.get("stock_id") for item in inventory if item.get("stock_id")))
    stocks = await db.stocks.find({"id": {"$in": stock_ids}}, {"_id": 0}).to_list(1000)
    stock_map = {s["id"]: s for s in stocks}
    
    result = []
    for item in inventory:
        stock_id = item.get("stock_id")
        stock = stock_map.get(stock_id, {})
        
        # Skip orphaned inventory records (stock doesn't exist)
        if not stock:
            continue
        
        item["stock_symbol"] = stock.get("symbol", "Unknown")
        item["stock_name"] = stock.get("name", "Unknown")
        
        # ALWAYS calculate weighted average dynamically from purchases
        calc = await calculate_weighted_avg_for_stock(stock_id)
        
        # Get landing price (or default to WAP if not set)
        landing_price = item.get("landing_price")
        if landing_price is None or landing_price <= 0:
            landing_price = calc["weighted_avg_price"]
        
        item["landing_price"] = round(landing_price, 2) if landing_price else 0.0
        
        # Calculate total value based on landing price for non-PE users
        if is_pe:
            # PE Desk/Manager see both WAP and LP
            item["weighted_avg_price"] = calc["weighted_avg_price"]
            item["total_value"] = calc["total_value"]  # WAP-based value
            item["lp_total_value"] = round(item["available_quantity"] * landing_price, 2)  # LP-based value
        else:
            # Other users only see LP (WAP is hidden)
            item["weighted_avg_price"] = landing_price  # Show LP as the "price"
            item["total_value"] = round(item["available_quantity"] * landing_price, 2)
            # Remove actual WAP from response
            item.pop("weighted_avg_price_actual", None)
        
        result.append(item)
    
    return result


@router.get("/export")
async def export_inventory(
    format: str = Query("xlsx", enum=["xlsx", "csv"]),
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("inventory.view", "export inventory"))
):
    """Export inventory to Excel or CSV"""
    import io
    from fastapi.responses import StreamingResponse
    
    # Get inventory with stock details
    inventory_data = await db.inventory.find({}, {"_id": 0}).to_list(10000)
    
    # Get stocks for lookup
    stocks = {s["id"]: s for s in await db.stocks.find({}, {"_id": 0, "id": 1, "name": 1, "symbol": 1, "face_value": 1}).to_list(10000)}
    
    if format == "csv":
        import csv
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Headers
        headers = [
            "Stock Symbol", "Stock Name", "Available Qty", "Reserved Qty",
            "Total Qty", "Weighted Avg Price", "Total Value", "Face Value",
            "Last Updated"
        ]
        writer.writerow(headers)
        
        # Data rows
        for inv in inventory_data:
            stock = stocks.get(inv.get("stock_id"), {})
            available = inv.get("available_quantity", 0)
            reserved = inv.get("reserved_quantity", 0)
            total = available + reserved
            avg_price = inv.get("weighted_average_price", 0)
            total_value = total * avg_price
            
            row = [
                stock.get("symbol", ""),
                stock.get("name", ""),
                available,
                reserved,
                total,
                round(avg_price, 2),
                round(total_value, 2),
                stock.get("face_value", ""),
                inv.get("updated_at", "")
            ]
            writer.writerow(row)
        
        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=inventory_export.csv"}
        )
    
    else:  # xlsx
        from openpyxl import Workbook
        from openpyxl.styles import Font, Alignment, PatternFill
        
        wb = Workbook()
        ws = wb.active
        ws.title = "Inventory"
        
        # Headers
        headers = [
            "Stock Symbol", "Stock Name", "Available Qty", "Reserved Qty",
            "Total Qty", "Weighted Avg Price", "Total Value", "Face Value",
            "Last Updated"
        ]
        
        # Style headers
        header_fill = PatternFill(start_color="10B981", end_color="10B981", fill_type="solid")
        header_font = Font(bold=True, color="FFFFFF")
        
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center")
        
        # Data rows
        for row_num, inv in enumerate(inventory_data, 2):
            stock = stocks.get(inv.get("stock_id"), {})
            available = inv.get("available_quantity", 0)
            reserved = inv.get("reserved_quantity", 0)
            total = available + reserved
            avg_price = inv.get("weighted_average_price", 0)
            total_value = total * avg_price
            
            data = [
                stock.get("symbol", ""),
                stock.get("name", ""),
                available,
                reserved,
                total,
                round(avg_price, 2),
                round(total_value, 2),
                stock.get("face_value", ""),
                inv.get("updated_at", "")
            ]
            
            for col, value in enumerate(data, 1):
                ws.cell(row=row_num, column=col, value=value)
        
        # Adjust column widths
        for col in ws.columns:
            max_length = 0
            column = col[0].column_letter
            for cell in col:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)
            ws.column_dimensions[column].width = adjusted_width
        
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=inventory_export.xlsx"}
        )


@router.get("/{stock_id}", response_model=InventoryModel)
async def get_inventory_item(
    stock_id: str,
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("inventory.view", "view inventory details"))
):
    """Get inventory for a specific stock"""
    user_role = current_user.get("role", 6)
    is_pe = is_pe_level(user_role)
    
    inventory = await db.inventory.find_one({"stock_id": stock_id}, {"_id": 0})
    if not inventory:
        raise HTTPException(status_code=404, detail="Inventory not found")
    
    # Enrich with stock details
    stock = await db.stocks.find_one({"id": stock_id}, {"_id": 0})
    if stock:
        inventory["stock_symbol"] = stock.get("symbol", "Unknown")
        inventory["stock_name"] = stock.get("name", "Unknown")
    
    # Calculate WAP
    calc = await calculate_weighted_avg_for_stock(stock_id)
    
    # Get landing price (or default to WAP)
    landing_price = inventory.get("landing_price")
    if landing_price is None or landing_price <= 0:
        landing_price = calc["weighted_avg_price"]
    
    inventory["landing_price"] = round(landing_price, 2)
    
    if is_pe:
        inventory["weighted_avg_price"] = calc["weighted_avg_price"]
        inventory["total_value"] = calc["total_value"]
    else:
        # Non-PE users see LP as the price
        inventory["weighted_avg_price"] = landing_price
        inventory["total_value"] = round(inventory.get("available_quantity", 0) * landing_price, 2)
    
    return inventory


@router.get("/{stock_id}/landing-price")
async def get_landing_price(
    stock_id: str,
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("inventory.view", "view landing price"))
):
    """Get the landing price for a stock (used by booking to get buying price)"""
    inventory = await db.inventory.find_one({"stock_id": stock_id}, {"_id": 0})
    if not inventory:
        raise HTTPException(status_code=404, detail="Inventory not found")
    
    # Calculate WAP
    calc = await calculate_weighted_avg_for_stock(stock_id)
    
    # Get landing price (or default to WAP)
    landing_price = inventory.get("landing_price")
    if landing_price is None or landing_price <= 0:
        landing_price = calc["weighted_avg_price"]
    
    return {
        "stock_id": stock_id,
        "landing_price": round(landing_price, 2),
        "available_quantity": inventory.get("available_quantity", 0)
    }


@router.put("/{stock_id}/landing-price")
async def update_landing_price(
    stock_id: str,
    data: UpdateLandingPriceRequest,
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("inventory.edit_landing_price", "update landing price"))
):
    """
    Update landing price for a stock (requires inventory.edit_landing_price permission).
    Landing Price (LP) is the price shown to non-PE users and used for booking revenue calculation.
    """
    user_role = current_user.get("role", 6)
    
    if data.landing_price <= 0:
        raise HTTPException(status_code=400, detail="Landing price must be greater than 0")
    
    # Check inventory exists
    inventory = await db.inventory.find_one({"stock_id": stock_id})
    if not inventory:
        raise HTTPException(status_code=404, detail="Inventory not found")
    
    # Get stock info for audit
    stock = await db.stocks.find_one({"id": stock_id}, {"_id": 0, "symbol": 1, "name": 1})
    
    old_lp = inventory.get("landing_price", 0)
    new_lp = round(data.landing_price, 2)
    
    # Store LP history entry
    lp_history_entry = {
        "stock_id": stock_id,
        "stock_symbol": stock.get("symbol") if stock else None,
        "old_price": old_lp,
        "new_price": new_lp,
        "change": round(new_lp - old_lp, 2) if old_lp else 0,
        "change_percent": round(((new_lp - old_lp) / old_lp) * 100, 2) if old_lp and old_lp > 0 else 0,
        "updated_by": current_user["id"],
        "updated_by_name": current_user["name"],
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    await db.lp_history.insert_one(lp_history_entry)
    
    # Update landing price with previous LP reference
    result = await db.inventory.update_one(
        {"stock_id": stock_id},
        {"$set": {
            "landing_price": new_lp,
            "previous_landing_price": old_lp,
            "landing_price_updated_at": datetime.now(timezone.utc).isoformat(),
            "landing_price_updated_by": current_user["id"],
            "landing_price_updated_by_name": current_user["name"]
        }}
    )
    
    # Create audit log
    from services.audit_service import create_audit_log
    await create_audit_log(
        action="LANDING_PRICE_UPDATE",
        entity_type="inventory",
        entity_id=stock_id,
        user_id=current_user["id"],
        user_name=current_user["name"],
        user_role=user_role,
        entity_name=stock.get("symbol", stock_id) if stock else stock_id,
        details={
            "stock_symbol": stock.get("symbol") if stock else None,
            "stock_name": stock.get("name") if stock else None,
            "new_landing_price": new_lp,
            "old_landing_price": old_lp
        }
    )
    
    return {
        "message": "Landing price updated successfully",
        "stock_id": stock_id,
        "landing_price": new_lp,
        "previous_landing_price": old_lp,
        "change": round(new_lp - old_lp, 2) if old_lp else 0
    }


@router.get("/{stock_id}/lp-history")
async def get_lp_history(
    stock_id: str,
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("inventory.view_lp_history", "view LP history"))
):
    """Get landing price history for a stock"""
    # Get LP history from dedicated collection
    history = await db.lp_history.find(
        {"stock_id": stock_id},
        {"_id": 0}
    ).sort("updated_at", -1).to_list(100)
    
    # Also get current inventory data
    inventory = await db.inventory.find_one({"stock_id": stock_id}, {"_id": 0})
    
    return {
        "stock_id": stock_id,
        "stock_symbol": inventory.get("stock_symbol") if inventory else None,
        "current_lp": inventory.get("landing_price") if inventory else None,
        "previous_lp": inventory.get("previous_landing_price") if inventory else None,
        "history": history
    }


@router.delete("/{stock_id}")
async def delete_inventory(
    stock_id: str,
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("inventory.delete", "delete inventory"))
):
    """Delete inventory for a stock (requires inventory.delete permission)"""
    user_role = current_user.get("role", 6)
    
    result = await db.inventory.delete_one({"stock_id": stock_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Inventory not found")
    
    return {"message": "Inventory deleted successfully"}


# ========== PE REPORT ENDPOINT ==========

class PEReportRequest(BaseModel):
    stock_id: str
    method: str = "both"  # 'email', 'whatsapp', 'both'


@router.post("/send-pe-report")
async def send_pe_report(
    request: PEReportRequest,
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("inventory.send_report", "send PE report"))
):
    """
    Send PE Stock Report to all users via Email and/or WhatsApp.
    
    Includes:
    - Stock Symbol
    - Stock Name
    - Landing Price (LP)
    - Company details from Company Master
    
    CC: pe@smifs.com
    """
    from services.email_service import send_email
    from routers.whatsapp import get_wati_service
    
    # Get stock/inventory details
    inventory = await db.inventory.find_one({"stock_id": request.stock_id}, {"_id": 0})
    if not inventory:
        raise HTTPException(status_code=404, detail="Stock not found in inventory")
    
    # Get stock details
    stock = await db.stocks.find_one({"id": request.stock_id}, {"_id": 0})
    
    # Get company master details
    company = await db.company_master.find_one({"_id": "company_settings"}, {"_id": 0})
    if not company:
        company = {
            "company_name": "SMIFS Private Equity",
            "address": "",
            "phone": "",
            "email": "pe@smifs.com"
        }
    
    # Get all active users
    users = await db.users.find(
        {"is_active": {"$ne": False}},
        {"_id": 0, "id": 1, "name": 1, "email": 1, "mobile": 1}
    ).to_list(10000)
    
    results = {
        "total_users": len(users),
        "emails_sent": 0,
        "whatsapp_sent": 0,
        "errors": []
    }
    
    # Prepare stock data
    stock_data = {
        "stock_symbol": inventory.get("stock_symbol") or stock.get("symbol", ""),
        "stock_name": inventory.get("stock_name") or stock.get("name", ""),
        "landing_price": inventory.get("landing_price", 0),
        "sector": stock.get("sector", "Unlisted"),
        "lot_size": stock.get("lot_size", 1),
        "min_investment": stock.get("min_investment", inventory.get("landing_price", 0) * stock.get("lot_size", 1)),
        "available_quantity": inventory.get("available_quantity", 0),
        "company_name": company.get("company_name", "SMIFS Private Equity"),
        "company_address": company.get("address", ""),
        "company_phone": company.get("phone", ""),
        "company_email": company.get("email", "pe@smifs.com"),
        "custom_domain": company.get("custom_domain", "")
    }
    
    # Format currency for display
    def format_currency(value):
        try:
            return f"{float(value):,.2f}"
        except:
            return "0.00"
    
    # Send reports
    for user in users:
        user_name = user.get("name", "Valued Client")
        user_email = user.get("email")
        user_mobile = user.get("mobile")
        
        # Send Email
        if request.method in ["email", "both"] and user_email:
            try:
                booking_url = f"{stock_data['custom_domain'] or 'https://pesmifs.com'}/bookings?stock={request.stock_id}"
                
                email_data = {
                    "recipient_name": user_name,
                    "stock_symbol": stock_data["stock_symbol"],
                    "stock_name": stock_data["stock_name"],
                    "landing_price": format_currency(stock_data["landing_price"]),
                    "sector": stock_data["sector"],
                    "lot_size": str(stock_data["lot_size"]),
                    "min_investment": format_currency(stock_data["min_investment"]),
                    "available_quantity": f"{stock_data['available_quantity']:,}",
                    "booking_url": booking_url,
                    "company_name": stock_data["company_name"],
                    "company_address": stock_data["company_address"],
                    "company_phone": stock_data["company_phone"],
                    "company_email": stock_data["company_email"]
                }
                
                # Send email with CC to pe@smifs.com
                await send_email(
                    to_email=user_email,
                    template_key="pe_stock_report",
                    data=email_data,
                    cc_email="pe@smifs.com"
                )
                results["emails_sent"] += 1
            except Exception as e:
                logger.error(f"Failed to send email to {user_email}: {str(e)}")
                results["errors"].append({"user": user_email, "type": "email", "error": str(e)})
        
        # Send WhatsApp
        if request.method in ["whatsapp", "both"] and user_mobile:
            try:
                service = await get_wati_service()
                if service:
                    # Format phone number
                    phone = ''.join(filter(str.isdigit, user_mobile))
                    if not phone.startswith('91') and len(phone) == 10:
                        phone = '91' + phone
                    
                    # Create message
                    message = f"""📈 *PE Stock Report*

Hello {user_name},

*{stock_data['stock_name']}* ({stock_data['stock_symbol']})

💰 *Landing Price:* ₹{format_currency(stock_data['landing_price'])}

📋 *Details:*
• Sector: {stock_data['sector']}
• Lot Size: {stock_data['lot_size']} shares
• Available: {stock_data['available_quantity']:,} shares

Contact us to book now!

{stock_data['company_name']}
📞 {stock_data['company_phone']}
✉️ {stock_data['company_email']}"""
                    
                    # Try session message first
                    result = await service.send_session_message(phone, message)
                    if result.get("result"):
                        results["whatsapp_sent"] += 1
                    else:
                        # If session fails, try template (requires pre-approved template in Wati)
                        results["errors"].append({
                            "user": phone, 
                            "type": "whatsapp", 
                            "error": "Session expired - needs template"
                        })
            except Exception as e:
                logger.error(f"Failed to send WhatsApp to {user_mobile}: {str(e)}")
                results["errors"].append({"user": user_mobile, "type": "whatsapp", "error": str(e)})
    
    # Create audit log
    from services.audit_service import create_audit_log
    await create_audit_log(
        action="PE_REPORT_SENT",
        entity_type="inventory",
        entity_id=request.stock_id,
        user_id=current_user["id"],
        user_name=current_user["name"],
        user_role=current_user.get("role", 6),
        entity_name=stock_data["stock_symbol"],
        details={
            "method": request.method,
            "total_users": results["total_users"],
            "emails_sent": results["emails_sent"],
            "whatsapp_sent": results["whatsapp_sent"],
            "errors_count": len(results["errors"])
        }
    )
    
    logger.info(f"PE Report sent for {stock_data['stock_symbol']}: {results['emails_sent']} emails, {results['whatsapp_sent']} WhatsApp by {current_user['name']}")
    
    return {
        "message": f"PE Report sent: {results['emails_sent']} emails, {results['whatsapp_sent']} WhatsApp messages",
        "stock": {
            "symbol": stock_data["stock_symbol"],
            "name": stock_data["stock_name"],
            "landing_price": stock_data["landing_price"]
        },
        "results": results
    }


@router.post("/recalculate")
async def recalculate_all_inventory(current_user: dict = Depends(get_current_user)):
    """
    Recalculate inventory for ALL stocks (PE Desk only).
    
    This is a manual fail-safe to ensure inventory data is accurate.
    It recalculates available_quantity, blocked_quantity, and weighted_avg_price
    for every stock based on actual purchases and bookings.
    """
    from services.permission_service import check_permission
    
    # Check permission dynamically
    await check_permission(current_user, "inventory.recalculate", "recalculate inventory")
    
    from services.inventory_service import update_inventory
    
    # Get all unique stock IDs from purchases, inventory, AND bookings
    purchase_stock_ids = await db.purchases.distinct("stock_id")
    inventory_stock_ids = await db.inventory.distinct("stock_id")
    booking_stock_ids = await db.bookings.distinct("stock_id")
    all_stock_ids = list(set(purchase_stock_ids + inventory_stock_ids + booking_stock_ids))
    
    results = {
        "total_stocks": len(all_stock_ids),
        "recalculated": 0,
        "errors": []
    }
    
    for stock_id in all_stock_ids:
        try:
            await update_inventory(stock_id)
            results["recalculated"] += 1
        except Exception as e:
            logger.error(f"Error recalculating inventory for stock {stock_id}: {str(e)}")
            results["errors"].append({"stock_id": stock_id, "error": str(e)})
    
    # Create audit log
    from services.audit_service import create_audit_log
    await create_audit_log(
        action="INVENTORY_RECALCULATE_ALL",
        entity_type="inventory",
        entity_id="all",
        user_id=current_user["id"],
        user_name=current_user["name"],
        user_role=current_user.get("role", 6),
        entity_name="All Stocks",
        details={
            "total_stocks": results["total_stocks"],
            "recalculated": results["recalculated"],
            "errors_count": len(results["errors"])
        }
    )
    
    logger.info(f"Inventory recalculated for {results['recalculated']}/{results['total_stocks']} stocks by {current_user['name']}")
    
    return {
        "message": f"Inventory recalculated for {results['recalculated']} of {results['total_stocks']} stocks",
        "details": results
    }

