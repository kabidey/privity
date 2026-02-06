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

@router.post("/send-pe-report")
async def send_consolidated_pe_report(
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("inventory.send_report", "send PE report"))
):
    """
    Send Consolidated PE Inventory Report to all users via Email.
    
    A single report containing ALL stocks in tabular format:
    - Stock Code
    - Stock Name  
    - Landing Price (LP)
    
    Includes company logo, timestamp, footer with company info and disclaimer.
    CC: pe@smifs.com
    """
    from services.email_service import send_email
    from datetime import datetime, timezone
    
    # Get ALL inventory items
    inventory_items = await db.inventory.find(
        {"available_quantity": {"$gt": 0}},
        {"_id": 0}
    ).sort("stock_symbol", 1).to_list(1000)
    
    if not inventory_items:
        raise HTTPException(status_code=400, detail="No inventory items found")
    
    # Get company master details
    company = await db.company_master.find_one({"_id": "company_settings"}, {"_id": 0})
    if not company:
        company = {
            "company_name": "SMIFS Private Equity",
            "address": "12, India Exchange Place, Kolkata - 700001",
            "phone": "+91-33-4012-1234",
            "email": "pe@smifs.com",
            "website": "www.smifs.com",
            "logo_url": ""
        }
    
    # Get all active users with email
    users = await db.users.find(
        {"is_active": {"$ne": False}, "email": {"$exists": True, "$ne": ""}},
        {"_id": 0, "id": 1, "name": 1, "email": 1}
    ).to_list(10000)
    
    if not users:
        raise HTTPException(status_code=400, detail="No users found to send report")
    
    # Generate timestamp
    report_time = datetime.now(timezone.utc)
    report_time_ist = report_time.strftime("%d %B %Y, %I:%M %p IST")
    
    # Build inventory table rows
    table_rows = ""
    for idx, item in enumerate(inventory_items):
        bg_color = "#ffffff" if idx % 2 == 0 else "#f9fafb"
        lp = item.get("landing_price", 0)
        lp_formatted = f"₹{lp:,.2f}" if lp else "N/A"
        
        table_rows += f"""
        <tr style="background-color: {bg_color};">
            <td style="padding: 14px 16px; border-bottom: 1px solid #e5e7eb; font-family: 'Courier New', monospace; font-weight: 600; color: #064E3B;">{item.get('stock_symbol', 'N/A')}</td>
            <td style="padding: 14px 16px; border-bottom: 1px solid #e5e7eb; color: #374151;">{item.get('stock_name', 'N/A')}</td>
            <td style="padding: 14px 16px; border-bottom: 1px solid #e5e7eb; text-align: right; font-weight: 600; color: #059669; font-size: 15px;">{lp_formatted}</td>
        </tr>
        """
    
    # Build the beautiful HTML email
    logo_html = ""
    if company.get("logo_url"):
        logo_html = f'<img src="{company["logo_url"]}" alt="{company["company_name"]}" style="max-height: 60px; max-width: 200px; object-fit: contain;">'
    else:
        logo_html = f'<div style="font-size: 24px; font-weight: bold; color: #064E3B;">{company.get("company_name", "SMIFS")}</div>'
    
    html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; font-family: 'Segoe UI', Arial, sans-serif; background-color: #f3f4f6;">
    <div style="max-width: 800px; margin: 0 auto; background-color: #ffffff;">
        
        <!-- Header with Logo -->
        <div style="background: linear-gradient(135deg, #064E3B 0%, #065f46 100%); padding: 30px 40px; text-align: center;">
            {logo_html}
            <h1 style="color: #ffffff; margin: 15px 0 5px 0; font-size: 26px; font-weight: 600;">PE Inventory Report</h1>
            <p style="color: rgba(255,255,255,0.85); margin: 0; font-size: 14px;">Private Equity Unlisted Shares</p>
        </div>
        
        <!-- Report Timestamp -->
        <div style="background-color: #ecfdf5; padding: 12px 40px; border-bottom: 2px solid #10b981;">
            <p style="margin: 0; color: #065f46; font-size: 13px;">
                <strong>Report Generated:</strong> {report_time_ist}
            </p>
        </div>
        
        <!-- Main Content -->
        <div style="padding: 30px 40px;">
            <p style="color: #374151; font-size: 15px; line-height: 1.6; margin-bottom: 25px;">
                Dear Investor,<br><br>
                Please find below the current inventory of available unlisted and pre-IPO shares for your consideration.
            </p>
            
            <!-- Inventory Table -->
            <div style="border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.05); border: 1px solid #e5e7eb;">
                <table style="width: 100%; border-collapse: collapse;">
                    <thead>
                        <tr style="background: linear-gradient(135deg, #064E3B 0%, #047857 100%);">
                            <th style="padding: 16px; text-align: left; color: #ffffff; font-weight: 600; font-size: 14px; text-transform: uppercase; letter-spacing: 0.5px;">Stock Code</th>
                            <th style="padding: 16px; text-align: left; color: #ffffff; font-weight: 600; font-size: 14px; text-transform: uppercase; letter-spacing: 0.5px;">Stock Name</th>
                            <th style="padding: 16px; text-align: right; color: #ffffff; font-weight: 600; font-size: 14px; text-transform: uppercase; letter-spacing: 0.5px;">Landing Price (LP)</th>
                        </tr>
                    </thead>
                    <tbody>
                        {table_rows}
                    </tbody>
                </table>
            </div>
            
            <p style="color: #6b7280; font-size: 13px; margin-top: 25px; line-height: 1.6;">
                Total Stocks Available: <strong>{len(inventory_items)}</strong>
            </p>
            
            <!-- CTA -->
            <div style="text-align: center; margin: 35px 0;">
                <p style="color: #374151; margin-bottom: 15px;">Interested in any of these opportunities?</p>
                <a href="{company.get('custom_domain', 'https://pesmifs.com')}/bookings" 
                   style="display: inline-block; background: linear-gradient(135deg, #064E3B, #059669); color: #ffffff; padding: 14px 35px; text-decoration: none; border-radius: 8px; font-weight: 600; font-size: 15px;">
                    Book Now
                </a>
            </div>
        </div>
        
        <!-- Disclaimer -->
        <div style="background-color: #fef3c7; padding: 20px 40px; border-top: 1px solid #fbbf24; border-bottom: 1px solid #fbbf24;">
            <p style="margin: 0; color: #92400e; font-size: 12px; line-height: 1.6;">
                <strong>⚠️ DISCLAIMER:</strong> This is an <strong>indicative report</strong> for informational purposes only. 
                Prices and availability are subject to change without prior notice. This does not constitute investment advice. 
                Please consult your financial advisor before making any investment decisions. Past performance does not guarantee future results.
                SMIFS Limited is a SEBI registered entity.
            </p>
        </div>
        
        <!-- Footer -->
        <div style="background-color: #1f2937; padding: 30px 40px; text-align: center;">
            <div style="margin-bottom: 20px;">
                <p style="color: #ffffff; font-size: 16px; font-weight: 600; margin: 0 0 5px 0;">{company.get('company_name', 'SMIFS Private Equity')}</p>
                <p style="color: #9ca3af; font-size: 13px; margin: 0; line-height: 1.6;">
                    {company.get('address', '')}
                </p>
            </div>
            
            <div style="border-top: 1px solid #374151; padding-top: 20px; margin-top: 20px;">
                <p style="color: #9ca3af; font-size: 13px; margin: 0;">
                    📞 {company.get('phone', '')} &nbsp;|&nbsp; 
                    ✉️ {company.get('email', 'pe@smifs.com')} &nbsp;|&nbsp;
                    🌐 {company.get('website', 'www.smifs.com')}
                </p>
            </div>
            
            <p style="color: #6b7280; font-size: 11px; margin: 20px 0 0 0;">
                © {datetime.now().year} {company.get('company_name', 'SMIFS')}. All rights reserved.<br>
                This email was sent to you as a registered user of SMIFS Private Equity platform.
            </p>
        </div>
    </div>
</body>
</html>
"""
    
    # Send to all users
    results = {
        "total_users": len(users),
        "emails_sent": 0,
        "errors": []
    }
    
    subject = f"📊 PE Inventory Report - {report_time.strftime('%d %b %Y')}"
    
    for user in users:
        user_email = user.get("email")
        if user_email:
            try:
                await send_email(
                    to_email=user_email,
                    subject=subject,
                    body=html_content,
                    cc_email="pe@smifs.com"
                )
                results["emails_sent"] += 1
            except Exception as e:
                logger.error(f"Failed to send PE Report to {user_email}: {str(e)}")
                results["errors"].append({"email": user_email, "error": str(e)})
    
    # Create audit log
    from services.audit_service import create_audit_log
    await create_audit_log(
        action="PE_INVENTORY_REPORT_SENT",
        entity_type="inventory",
        entity_id="consolidated_report",
        user_id=current_user["id"],
        user_name=current_user["name"],
        user_role=current_user.get("role", 6),
        entity_name="PE Inventory Report",
        details={
            "total_stocks": len(inventory_items),
            "total_users": results["total_users"],
            "emails_sent": results["emails_sent"],
            "errors_count": len(results["errors"]),
            "report_time": report_time_ist
        }
    )
    
    logger.info(f"PE Inventory Report sent to {results['emails_sent']} users by {current_user['name']}")
    
    return {
        "message": f"PE Report sent successfully to {results['emails_sent']} users",
        "report_time": report_time_ist,
        "stocks_included": len(inventory_items),
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

