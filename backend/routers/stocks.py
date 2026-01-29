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
from services.email_service import send_templated_email

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
        "isin_number": stock_data.isin_number,
        "bse_code": stock_data.bse_code,
        "nse_code": stock_data.nse_code
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
    current_user: dict = Depends(get_current_user)
):
    """Create a corporate action (PE Desk only)"""
    user_role = current_user.get("role", 5)
    if user_role != 1:
        raise HTTPException(status_code=403, detail="Only PE Desk can create corporate actions")
    
    stock = await db.stocks.find_one({"id": action_data.stock_id}, {"_id": 0})
    if not stock:
        raise HTTPException(status_code=404, detail="Stock not found")
    
    action_id = str(uuid.uuid4())
    action_doc = {
        "id": action_id,
        "stock_id": action_data.stock_id,
        "stock_symbol": stock["symbol"],
        "action_type": action_data.action_type,
        "ratio_from": action_data.ratio_from,
        "ratio_to": action_data.ratio_to,
        "record_date": action_data.record_date,
        "description": action_data.description,
        "is_applied": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": current_user["id"]
    }
    
    await db.corporate_actions.insert_one(action_doc)
    return CorporateAction(**action_doc)


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
