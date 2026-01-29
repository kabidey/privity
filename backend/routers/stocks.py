"""
Stocks Router
Handles stock management, corporate actions, and inventory
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from typing import List, Optional
from datetime import datetime, timezone
import uuid
import io

from database import db
from routers.auth import get_current_user
from models import Stock, StockCreate, CorporateAction, CorporateActionCreate, Inventory
from services.email_service import send_email

router = APIRouter(tags=["Stocks"])


# ============== Helper Functions ==============
async def update_inventory(stock_id: str):
    """Recalculate weighted average and available quantity for a stock."""
    purchases = await db.purchases.find({"stock_id": stock_id}, {"_id": 0}).to_list(10000)
    bookings = await db.bookings.find({"stock_id": stock_id}, {"_id": 0}).to_list(10000)
    
    total_purchased_qty = sum(p["quantity"] for p in purchases)
    total_purchased_value = sum(p["quantity"] * p["price_per_unit"] for p in purchases)
    
    blocked_qty = sum(
        b["quantity"] for b in bookings 
        if b.get("approval_status") == "approved" 
        and b.get("client_confirmed") == True
        and not b.get("is_voided", False)
        and not b.get("stock_transferred", False)
    )
    
    transferred_qty = sum(
        b["quantity"] for b in bookings 
        if b.get("stock_transferred") == True
        and not b.get("is_voided", False)
    )
    
    available_qty = total_purchased_qty - transferred_qty - blocked_qty
    weighted_avg = total_purchased_value / total_purchased_qty if total_purchased_qty > 0 else 0
    
    stock = await db.stocks.find_one({"id": stock_id}, {"_id": 0})
    
    inventory_data = {
        "stock_id": stock_id,
        "stock_symbol": stock["symbol"] if stock else "Unknown",
        "stock_name": stock["name"] if stock else "Unknown",
        "available_quantity": max(0, available_qty),
        "blocked_quantity": blocked_qty,
        "weighted_avg_price": weighted_avg,
        "total_value": max(0, available_qty) * weighted_avg
    }
    
    await db.inventory.update_one(
        {"stock_id": stock_id},
        {"$set": inventory_data},
        upsert=True
    )
    
    return inventory_data


# ============== Stock Endpoints ==============
@router.post("/stocks", response_model=Stock)
async def create_stock(stock_data: StockCreate, current_user: dict = Depends(get_current_user)):
    """Create a new stock (PE Desk only)"""
    user_role = current_user.get("role", 5)
    if user_role != 1:
        raise HTTPException(status_code=403, detail="Only PE Desk can create stocks")
    
    existing = await db.stocks.find_one({"symbol": stock_data.symbol.upper()}, {"_id": 0})
    if existing:
        raise HTTPException(status_code=400, detail="Stock with this symbol already exists")
    
    stock_id = str(uuid.uuid4())
    stock_doc = {
        "id": stock_id,
        "symbol": stock_data.symbol.upper(),
        "name": stock_data.name,
        "isin_number": stock_data.isin_number,
        "exchange": stock_data.exchange,
        "sector": stock_data.sector,
        "product": stock_data.product,
        "face_value": stock_data.face_value,
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": current_user["id"]
    }
    
    await db.stocks.insert_one(stock_doc)
    await update_inventory(stock_id)
    
    return Stock(**stock_doc)


@router.get("/stocks", response_model=List[Stock])
async def get_stocks(
    current_user: dict = Depends(get_current_user),
    active_only: bool = True
):
    """Get all stocks"""
    query = {"is_active": True} if active_only else {}
    stocks = await db.stocks.find(query, {"_id": 0}).to_list(10000)
    return [Stock(**s) for s in stocks]


@router.get("/stocks/{stock_id}", response_model=Stock)
async def get_stock(stock_id: str, current_user: dict = Depends(get_current_user)):
    """Get a single stock by ID"""
    stock = await db.stocks.find_one({"id": stock_id}, {"_id": 0})
    if not stock:
        raise HTTPException(status_code=404, detail="Stock not found")
    return Stock(**stock)


@router.put("/stocks/{stock_id}", response_model=Stock)
async def update_stock(stock_id: str, stock_data: StockCreate, current_user: dict = Depends(get_current_user)):
    """Update a stock (PE Desk only)"""
    user_role = current_user.get("role", 5)
    if user_role != 1:
        raise HTTPException(status_code=403, detail="Only PE Desk can update stocks")
    
    existing = await db.stocks.find_one({"id": stock_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Stock not found")
    
    update_data = {
        "symbol": stock_data.symbol.upper(),
        "name": stock_data.name,
        "exchange": stock_data.exchange,
        "isin_number": stock_data.isin_number,
        "sector": stock_data.sector,
        "product": stock_data.product,
        "face_value": stock_data.face_value
    }
    
    await db.stocks.update_one({"id": stock_id}, {"$set": update_data})
    updated = await db.stocks.find_one({"id": stock_id}, {"_id": 0})
    return Stock(**updated)


@router.delete("/stocks/{stock_id}")
async def delete_stock(stock_id: str, current_user: dict = Depends(get_current_user)):
    """Delete a stock (PE Desk only)"""
    user_role = current_user.get("role", 5)
    if user_role != 1:
        raise HTTPException(status_code=403, detail="Only PE Desk can delete stocks")
    
    result = await db.stocks.delete_one({"id": stock_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Stock not found")
    
    return {"message": "Stock deleted successfully"}


@router.post("/stocks/bulk-upload")
async def bulk_upload_stocks(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """Bulk upload stocks from Excel file (PE Desk only)"""
    user_role = current_user.get("role", 5)
    if user_role != 1:
        raise HTTPException(status_code=403, detail="Only PE Desk can bulk upload stocks")
    
    try:
        import openpyxl
        content = await file.read()
        wb = openpyxl.load_workbook(io.BytesIO(content))
        ws = wb.active
        
        created = 0
        errors = []
        
        for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
            if not row[0]:
                continue
            
            symbol = str(row[0]).upper().strip()
            existing = await db.stocks.find_one({"symbol": symbol})
            if existing:
                errors.append(f"Row {row_idx}: Stock {symbol} already exists")
                continue
            
            stock_doc = {
                "id": str(uuid.uuid4()),
                "symbol": symbol,
                "name": str(row[1] or symbol).strip(),
                "isin_number": str(row[2] or "").strip() if len(row) > 2 else "",
                "bse_code": str(row[3] or "").strip() if len(row) > 3 else "",
                "nse_code": str(row[4] or "").strip() if len(row) > 4 else "",
                "is_active": True,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "created_by": current_user["id"]
            }
            
            await db.stocks.insert_one(stock_doc)
            await update_inventory(stock_doc["id"])
            created += 1
        
        return {"created": created, "errors": errors}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error processing file: {str(e)}")


# ============== Inventory Endpoints ==============
@router.get("/inventory", response_model=List[Inventory])
async def get_inventory(current_user: dict = Depends(get_current_user)):
    """Get current inventory"""
    inventory = await db.inventory.find({}, {"_id": 0}).to_list(10000)
    return [Inventory(**i) for i in inventory]


@router.get("/inventory/{stock_id}", response_model=Inventory)
async def get_stock_inventory(stock_id: str, current_user: dict = Depends(get_current_user)):
    """Get inventory for a specific stock"""
    inventory = await db.inventory.find_one({"stock_id": stock_id}, {"_id": 0})
    if not inventory:
        raise HTTPException(status_code=404, detail="Inventory not found")
    return Inventory(**inventory)


# ============== Corporate Actions Endpoints ==============
@router.post("/corporate-actions", response_model=CorporateAction)
async def create_corporate_action(
    action_data: CorporateActionCreate,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    """Create a corporate action (PE Desk only)"""
    user_role = current_user.get("role", 5)
    if user_role != 1:
        raise HTTPException(status_code=403, detail="Only PE Desk can create corporate actions")
    
    stock = await db.stocks.find_one({"id": action_data.stock_id}, {"_id": 0})
    if not stock:
        raise HTTPException(status_code=404, detail="Stock not found")
    
    # Validate based on action type
    if action_data.action_type in ["stock_split", "bonus", "rights_issue"]:
        if not action_data.ratio_from or not action_data.ratio_to:
            raise HTTPException(status_code=400, detail="Ratio is required for this action type")
    elif action_data.action_type == "dividend":
        if not action_data.dividend_amount:
            raise HTTPException(status_code=400, detail="Dividend amount is required for dividend action")
    
    action_id = str(uuid.uuid4())
    action_doc = {
        "id": action_id,
        "stock_id": action_data.stock_id,
        "stock_symbol": stock["symbol"],
        "stock_name": stock.get("name", stock["symbol"]),
        "action_type": action_data.action_type,
        "ratio_from": action_data.ratio_from,
        "ratio_to": action_data.ratio_to,
        "dividend_amount": action_data.dividend_amount,
        "dividend_type": action_data.dividend_type,
        "new_face_value": action_data.new_face_value,
        "record_date": action_data.record_date,
        "ex_date": action_data.ex_date,
        "payment_date": action_data.payment_date,
        "notes": action_data.notes,
        "status": "pending",
        "notified_clients": 0,
        "is_applied": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": current_user["id"]
    }
    
    await db.corporate_actions.insert_one(action_doc)
    
    # Log the action
    await db.audit_logs.insert_one({
        "id": str(uuid.uuid4()),
        "action": "CORPORATE_ACTION_CREATED",
        "entity_type": "corporate_action",
        "entity_id": action_id,
        "user_id": current_user["id"],
        "user_name": current_user["name"],
        "details": {
            "stock_symbol": stock["symbol"],
            "action_type": action_data.action_type,
            "record_date": action_data.record_date
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    return CorporateAction(**action_doc)


async def notify_clients_for_corporate_action(action_id: str):
    """Send email notifications to clients who hold the stock"""
    action = await db.corporate_actions.find_one({"id": action_id}, {"_id": 0})
    if not action:
        return 0
    
    stock_id = action["stock_id"]
    stock_symbol = action["stock_symbol"]
    stock_name = action.get("stock_name", stock_symbol)
    
    # Find all clients who have this stock in completed bookings
    bookings = await db.bookings.find({
        "stock_id": stock_id,
        "status": {"$in": ["completed", "open", "approved"]}
    }, {"_id": 0}).to_list(10000)
    
    # Get unique client IDs
    client_ids = list(set(b["client_id"] for b in bookings))
    
    if not client_ids:
        return 0
    
    # Get client details
    clients = await db.clients.find({
        "id": {"$in": client_ids},
        "is_vendor": False
    }, {"_id": 0}).to_list(10000)
    
    notified_count = 0
    action_type_display = action["action_type"].replace("_", " ").title()
    
    for client in clients:
        email = client.get("email")
        if not email:
            continue
        
        # Get client's holdings for this stock
        client_bookings = [b for b in bookings if b["client_id"] == client["id"]]
        total_quantity = sum(b.get("quantity", 0) for b in client_bookings)
        
        # Prepare email content based on action type
        if action["action_type"] == "dividend":
            dividend_amount = action.get("dividend_amount", 0)
            estimated_dividend = total_quantity * dividend_amount
            subject = f"Dividend Announcement - {stock_symbol}"
            
            html_content = f"""
            <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
                <div style="background: linear-gradient(135deg, #10B981 0%, #059669 100%); color: white; padding: 30px; border-radius: 16px 16px 0 0; text-align: center;">
                    <h1 style="margin: 0; font-size: 24px;">💰 Dividend Announcement</h1>
                </div>
                <div style="background: #f9fafb; padding: 30px; border-radius: 0 0 16px 16px;">
                    <p style="color: #374151; font-size: 16px;">Dear <strong>{client.get('name', 'Valued Client')}</strong>,</p>
                    
                    <p style="color: #374151; font-size: 16px;">We are pleased to inform you about the following dividend announcement:</p>
                    
                    <div style="background: white; border-radius: 12px; padding: 20px; margin: 20px 0; border: 1px solid #e5e7eb;">
                        <table style="width: 100%; border-collapse: collapse;">
                            <tr><td style="padding: 10px 0; color: #6b7280;">Stock</td><td style="padding: 10px 0; font-weight: 600; text-align: right;">{stock_name} ({stock_symbol})</td></tr>
                            <tr><td style="padding: 10px 0; color: #6b7280;">Dividend Type</td><td style="padding: 10px 0; font-weight: 600; text-align: right;">{action.get('dividend_type', 'Regular').title()}</td></tr>
                            <tr><td style="padding: 10px 0; color: #6b7280;">Dividend per Share</td><td style="padding: 10px 0; font-weight: 600; text-align: right;">₹{dividend_amount:.2f}</td></tr>
                            <tr><td style="padding: 10px 0; color: #6b7280;">Record Date</td><td style="padding: 10px 0; font-weight: 600; text-align: right;">{action.get('record_date', 'TBA')}</td></tr>
                            <tr><td style="padding: 10px 0; color: #6b7280;">Ex-Dividend Date</td><td style="padding: 10px 0; font-weight: 600; text-align: right;">{action.get('ex_date', 'TBA')}</td></tr>
                            <tr><td style="padding: 10px 0; color: #6b7280;">Payment Date</td><td style="padding: 10px 0; font-weight: 600; text-align: right;">{action.get('payment_date', 'TBA')}</td></tr>
                        </table>
                    </div>
                    
                    <div style="background: #ecfdf5; border-radius: 12px; padding: 20px; margin: 20px 0; border-left: 4px solid #10B981;">
                        <p style="margin: 0; color: #065f46; font-size: 14px;"><strong>Your Holdings:</strong></p>
                        <p style="margin: 8px 0 0 0; color: #065f46; font-size: 18px; font-weight: 600;">{total_quantity:,} shares</p>
                        <p style="margin: 8px 0 0 0; color: #065f46; font-size: 14px;">Estimated Dividend: <strong>₹{estimated_dividend:,.2f}</strong></p>
                    </div>
                    
                    {f'<p style="color: #6b7280; font-size: 14px;"><em>Note: {action.get("notes", "")}</em></p>' if action.get("notes") else ''}
                    
                    <p style="color: #374151; font-size: 14px; margin-top: 20px;">Please ensure your bank account details are updated to receive the dividend.</p>
                    
                    <p style="color: #6b7280; font-size: 14px; margin-top: 30px;">Best regards,<br/><strong>SMIFS Capital Markets Ltd</strong></p>
                </div>
            </div>
            """
        else:
            # For stock split, bonus, rights issue, buyback
            subject = f"{action_type_display} Announcement - {stock_symbol}"
            
            ratio_text = ""
            if action.get("ratio_from") and action.get("ratio_to"):
                ratio_text = f"{action['ratio_to']}:{action['ratio_from']}"
            
            html_content = f"""
            <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
                <div style="background: linear-gradient(135deg, #3B82F6 0%, #1D4ED8 100%); color: white; padding: 30px; border-radius: 16px 16px 0 0; text-align: center;">
                    <h1 style="margin: 0; font-size: 24px;">📢 {action_type_display}</h1>
                </div>
                <div style="background: #f9fafb; padding: 30px; border-radius: 0 0 16px 16px;">
                    <p style="color: #374151; font-size: 16px;">Dear <strong>{client.get('name', 'Valued Client')}</strong>,</p>
                    
                    <p style="color: #374151; font-size: 16px;">We would like to inform you about the following corporate action:</p>
                    
                    <div style="background: white; border-radius: 12px; padding: 20px; margin: 20px 0; border: 1px solid #e5e7eb;">
                        <table style="width: 100%; border-collapse: collapse;">
                            <tr><td style="padding: 10px 0; color: #6b7280;">Stock</td><td style="padding: 10px 0; font-weight: 600; text-align: right;">{stock_name} ({stock_symbol})</td></tr>
                            <tr><td style="padding: 10px 0; color: #6b7280;">Action Type</td><td style="padding: 10px 0; font-weight: 600; text-align: right;">{action_type_display}</td></tr>
                            {f'<tr><td style="padding: 10px 0; color: #6b7280;">Ratio</td><td style="padding: 10px 0; font-weight: 600; text-align: right;">{ratio_text}</td></tr>' if ratio_text else ''}
                            <tr><td style="padding: 10px 0; color: #6b7280;">Record Date</td><td style="padding: 10px 0; font-weight: 600; text-align: right;">{action.get('record_date', 'TBA')}</td></tr>
                            {f'<tr><td style="padding: 10px 0; color: #6b7280;">New Face Value</td><td style="padding: 10px 0; font-weight: 600; text-align: right;">₹{action.get("new_face_value")}</td></tr>' if action.get('new_face_value') else ''}
                        </table>
                    </div>
                    
                    <div style="background: #eff6ff; border-radius: 12px; padding: 20px; margin: 20px 0; border-left: 4px solid #3B82F6;">
                        <p style="margin: 0; color: #1e40af; font-size: 14px;"><strong>Your Current Holdings:</strong></p>
                        <p style="margin: 8px 0 0 0; color: #1e40af; font-size: 18px; font-weight: 600;">{total_quantity:,} shares</p>
                    </div>
                    
                    {f'<p style="color: #6b7280; font-size: 14px;"><em>Note: {action.get("notes", "")}</em></p>' if action.get("notes") else ''}
                    
                    <p style="color: #374151; font-size: 14px; margin-top: 20px;">The corporate action will be processed as per the record date. Your portfolio will be updated accordingly.</p>
                    
                    <p style="color: #6b7280; font-size: 14px; margin-top: 30px;">Best regards,<br/><strong>SMIFS Capital Markets Ltd</strong></p>
                </div>
            </div>
            """
        
        # Send email
        try:
            await send_email(
                to_email=email,
                subject=subject,
                body=html_content,
                template_key="corporate_action_notification",
                related_entity_type="corporate_action",
                related_entity_id=action_id
            )
            notified_count += 1
        except Exception as e:
            print(f"Failed to send corporate action email to {email}: {e}")
    
    # Update the action with notification count
    await db.corporate_actions.update_one(
        {"id": action_id},
        {"$set": {"notified_clients": notified_count, "status": "notified"}}
    )
    
    return notified_count


@router.post("/corporate-actions/{action_id}/notify")
async def send_corporate_action_notifications(
    action_id: str,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    """Send email notifications to all clients holding the stock (PE Desk only)"""
    user_role = current_user.get("role", 5)
    if user_role != 1:
        raise HTTPException(status_code=403, detail="Only PE Desk can send notifications")
    
    action = await db.corporate_actions.find_one({"id": action_id}, {"_id": 0})
    if not action:
        raise HTTPException(status_code=404, detail="Corporate action not found")
    
    # Run notification in background
    background_tasks.add_task(notify_clients_for_corporate_action, action_id)
    
    # Log the action
    await db.audit_logs.insert_one({
        "id": str(uuid.uuid4()),
        "action": "CORPORATE_ACTION_NOTIFICATION_SENT",
        "entity_type": "corporate_action",
        "entity_id": action_id,
        "user_id": current_user["id"],
        "user_name": current_user["name"],
        "details": {
            "stock_symbol": action["stock_symbol"],
            "action_type": action["action_type"]
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    return {"message": "Notifications are being sent to clients", "action_id": action_id}


@router.get("/corporate-actions", response_model=List[CorporateAction])
async def get_corporate_actions(
    current_user: dict = Depends(get_current_user),
    stock_id: Optional[str] = None
):
    """Get corporate actions"""
    query = {"stock_id": stock_id} if stock_id else {}
    actions = await db.corporate_actions.find(query, {"_id": 0}).to_list(10000)
    return [CorporateAction(**a) for a in actions]


@router.delete("/corporate-actions/{action_id}")
async def delete_corporate_action(action_id: str, current_user: dict = Depends(get_current_user)):
    """Delete a corporate action (PE Desk only, only if not applied)"""
    user_role = current_user.get("role", 5)
    if user_role != 1:
        raise HTTPException(status_code=403, detail="Only PE Desk can delete corporate actions")
    
    action = await db.corporate_actions.find_one({"id": action_id}, {"_id": 0})
    if not action:
        raise HTTPException(status_code=404, detail="Corporate action not found")
    
    if action.get("is_applied"):
        raise HTTPException(status_code=400, detail="Cannot delete applied corporate action")
    
    await db.corporate_actions.delete_one({"id": action_id})
    return {"message": "Corporate action deleted"}
