"""
Stock management routes including corporate actions
"""
import uuid
import io
from datetime import datetime, timezone
from typing import List, Optional

import pandas as pd
from fastapi import APIRouter, HTTPException, Depends, File, UploadFile

from database import db
from models import StockCreate, Stock, CorporateActionCreate, CorporateAction
from utils.auth import get_current_user
from services.audit_service import create_audit_log

router = APIRouter(prefix="/stocks", tags=["Stocks"])


@router.post("", response_model=Stock)
async def create_stock(stock_data: StockCreate, current_user: dict = Depends(get_current_user)):
    """Create a new stock (PE Desk only)"""
    user_role = current_user.get("role", 5)
    
    if user_role != 1:
        raise HTTPException(status_code=403, detail="Only PE Desk can add stocks")
    
    stock_id = str(uuid.uuid4())
    stock_doc = {
        "id": stock_id,
        **stock_data.model_dump(),
        "user_id": current_user["id"],
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.stocks.insert_one(stock_doc)
    
    await create_audit_log(
        action="STOCK_CREATE",
        entity_type="stock",
        entity_id=stock_id,
        user_id=current_user["id"],
        user_name=current_user["name"],
        user_role=user_role,
        entity_name=stock_data.symbol,
        details={"symbol": stock_data.symbol, "name": stock_data.name, "isin": stock_data.isin_number}
    )
    
    return Stock(**{k: v for k, v in stock_doc.items() if k != "user_id"})


@router.get("", response_model=List[Stock])
async def get_stocks(search: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    """Get list of stocks with optional search"""
    query = {}
    
    if search:
        query["$or"] = [
            {"symbol": {"$regex": search, "$options": "i"}},
            {"name": {"$regex": search, "$options": "i"}}
        ]
    
    stocks = await db.stocks.find(query, {"_id": 0, "user_id": 0}).to_list(1000)
    return stocks


@router.get("/{stock_id}", response_model=Stock)
async def get_stock(stock_id: str, current_user: dict = Depends(get_current_user)):
    """Get a single stock by ID"""
    stock = await db.stocks.find_one({"id": stock_id}, {"_id": 0, "user_id": 0})
    if not stock:
        raise HTTPException(status_code=404, detail="Stock not found")
    return stock


@router.put("/{stock_id}", response_model=Stock)
async def update_stock(stock_id: str, stock_data: StockCreate, current_user: dict = Depends(get_current_user)):
    """Update a stock (PE Desk only)"""
    user_role = current_user.get("role", 5)
    
    if user_role != 1:
        raise HTTPException(status_code=403, detail="Only PE Desk can update stocks")
    
    result = await db.stocks.update_one(
        {"id": stock_id},
        {"$set": stock_data.model_dump()}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Stock not found")
    
    updated_stock = await db.stocks.find_one({"id": stock_id}, {"_id": 0, "user_id": 0})
    return updated_stock


@router.delete("/{stock_id}")
async def delete_stock(stock_id: str, current_user: dict = Depends(get_current_user)):
    """Delete a stock (PE Desk only)"""
    user_role = current_user.get("role", 5)
    
    if user_role != 1:
        raise HTTPException(status_code=403, detail="Only PE Desk can delete stocks")
    
    result = await db.stocks.delete_one({"id": stock_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Stock not found")
    return {"message": "Stock deleted successfully"}


@router.post("/bulk-upload")
async def bulk_upload_stocks(file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    """Bulk upload stocks from CSV (PE Desk only)"""
    user_role = current_user.get("role", 5)
    
    if user_role != 1:
        raise HTTPException(status_code=403, detail="Only PE Desk can bulk upload stocks")
    
    try:
        content = await file.read()
        df = pd.read_csv(io.BytesIO(content))
        
        required_columns = ["symbol", "name"]
        if not all(col in df.columns for col in required_columns):
            raise HTTPException(status_code=400, detail=f"CSV must contain columns: {', '.join(required_columns)}")
        
        stocks_created = 0
        for _, row in df.iterrows():
            stock_id = str(uuid.uuid4())
            stock_doc = {
                "id": stock_id,
                "symbol": str(row["symbol"]).upper(),
                "name": str(row["name"]),
                "exchange": str(row.get("exchange", "")) if pd.notna(row.get("exchange")) else None,
                "user_id": current_user["id"],
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            
            await db.stocks.insert_one(stock_doc)
            stocks_created += 1
        
        return {"message": f"Successfully uploaded {stocks_created} stocks"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error processing CSV: {str(e)}")


# Corporate Actions Router
corporate_router = APIRouter(prefix="/corporate-actions", tags=["Corporate Actions"])


@corporate_router.post("", response_model=CorporateAction)
async def create_corporate_action(
    action_data: CorporateActionCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create a corporate action (Stock Split or Bonus) - PE Desk only"""
    user_role = current_user.get("role", 5)
    
    if user_role != 1:
        raise HTTPException(status_code=403, detail="Only PE Desk can create corporate actions")
    
    stock = await db.stocks.find_one({"id": action_data.stock_id}, {"_id": 0})
    if not stock:
        raise HTTPException(status_code=404, detail="Stock not found")
    
    if action_data.action_type not in ["stock_split", "bonus"]:
        raise HTTPException(status_code=400, detail="Action type must be 'stock_split' or 'bonus'")
    
    if action_data.action_type == "stock_split" and not action_data.new_face_value:
        raise HTTPException(status_code=400, detail="New face value is required for stock split")
    
    action_id = str(uuid.uuid4())
    action_doc = {
        "id": action_id,
        "stock_id": action_data.stock_id,
        "action_type": action_data.action_type,
        "ratio_from": action_data.ratio_from,
        "ratio_to": action_data.ratio_to,
        "new_face_value": action_data.new_face_value,
        "record_date": action_data.record_date,
        "status": "pending",
        "applied_at": None,
        "notes": action_data.notes,
        "created_by": current_user["id"],
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.corporate_actions.insert_one(action_doc)
    
    await create_audit_log(
        action="CORPORATE_ACTION_CREATE",
        entity_type="corporate_action",
        entity_id=action_id,
        user_id=current_user["id"],
        user_name=current_user["name"],
        user_role=user_role,
        entity_name=f"{stock['symbol']} - {action_data.action_type}",
        details={
            "stock_symbol": stock["symbol"],
            "action_type": action_data.action_type,
            "ratio": f"{action_data.ratio_from}:{action_data.ratio_to}",
            "record_date": action_data.record_date
        }
    )
    
    return CorporateAction(
        **action_doc,
        stock_symbol=stock["symbol"],
        stock_name=stock["name"]
    )


@corporate_router.get("", response_model=List[CorporateAction])
async def get_corporate_actions(
    stock_id: Optional[str] = None,
    status: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get corporate actions - PE Desk only"""
    user_role = current_user.get("role", 5)
    
    if user_role != 1:
        raise HTTPException(status_code=403, detail="Only PE Desk can view corporate actions")
    
    query = {}
    if stock_id:
        query["stock_id"] = stock_id
    if status:
        query["status"] = status
    
    actions = await db.corporate_actions.find(query, {"_id": 0}).sort("created_at", -1).to_list(1000)
    
    stock_ids = list(set(a["stock_id"] for a in actions))
    stocks = await db.stocks.find({"id": {"$in": stock_ids}}, {"_id": 0}).to_list(1000)
    stock_map = {s["id"]: s for s in stocks}
    
    enriched = []
    for a in actions:
        stock = stock_map.get(a["stock_id"], {})
        enriched.append(CorporateAction(
            **a,
            stock_symbol=stock.get("symbol", "Unknown"),
            stock_name=stock.get("name", "Unknown")
        ))
    
    return enriched


@corporate_router.put("/{action_id}/apply")
async def apply_corporate_action(
    action_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Apply a corporate action on record date - adjusts buy prices in inventory"""
    user_role = current_user.get("role", 5)
    
    if user_role != 1:
        raise HTTPException(status_code=403, detail="Only PE Desk can apply corporate actions")
    
    action = await db.corporate_actions.find_one({"id": action_id}, {"_id": 0})
    if not action:
        raise HTTPException(status_code=404, detail="Corporate action not found")
    
    if action["status"] == "applied":
        raise HTTPException(status_code=400, detail="Corporate action already applied")
    
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if action["record_date"] != today:
        raise HTTPException(
            status_code=400, 
            detail=f"Corporate action can only be applied on record date ({action['record_date']}). Today is {today}"
        )
    
    stock_id = action["stock_id"]
    ratio_from = action["ratio_from"]
    ratio_to = action["ratio_to"]
    action_type = action["action_type"]
    
    if action_type == "stock_split":
        adjustment_factor = ratio_from / ratio_to
    else:
        adjustment_factor = ratio_from / (ratio_from + ratio_to)
    
    inventory = await db.inventory.find_one({"stock_id": stock_id}, {"_id": 0})
    if inventory:
        new_avg_price = inventory["weighted_avg_price"] * adjustment_factor
        
        if action_type == "stock_split":
            new_quantity = int(inventory["available_quantity"] * (ratio_to / ratio_from))
        else:
            bonus_shares = int(inventory["available_quantity"] * (ratio_to / ratio_from))
            new_quantity = inventory["available_quantity"] + bonus_shares
        
        await db.inventory.update_one(
            {"stock_id": stock_id},
            {"$set": {
                "weighted_avg_price": new_avg_price,
                "available_quantity": new_quantity
            }}
        )
    
    await db.purchases.update_many(
        {"stock_id": stock_id},
        {"$mul": {"price_per_unit": adjustment_factor}}
    )
    
    await db.bookings.update_many(
        {"stock_id": stock_id},
        {"$mul": {"buying_price": adjustment_factor}}
    )
    
    if action_type == "stock_split" and action.get("new_face_value"):
        await db.stocks.update_one(
            {"id": stock_id},
            {"$set": {"face_value": action["new_face_value"]}}
        )
    
    await db.corporate_actions.update_one(
        {"id": action_id},
        {"$set": {
            "status": "applied",
            "applied_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    stock = await db.stocks.find_one({"id": stock_id}, {"_id": 0})
    await create_audit_log(
        action="CORPORATE_ACTION_APPLY",
        entity_type="corporate_action",
        entity_id=action_id,
        user_id=current_user["id"],
        user_name=current_user["name"],
        user_role=user_role,
        entity_name=f"{stock['symbol'] if stock else 'Unknown'} - {action_type}",
        details={
            "adjustment_factor": adjustment_factor,
            "action_type": action_type,
            "ratio": f"{ratio_from}:{ratio_to}"
        }
    )
    
    return {
        "message": f"Corporate action applied successfully. Prices adjusted by factor {adjustment_factor:.4f}",
        "adjustment_factor": adjustment_factor
    }


@corporate_router.delete("/{action_id}")
async def delete_corporate_action(action_id: str, current_user: dict = Depends(get_current_user)):
    """Delete a pending corporate action - PE Desk only"""
    user_role = current_user.get("role", 5)
    
    if user_role != 1:
        raise HTTPException(status_code=403, detail="Only PE Desk can delete corporate actions")
    
    action = await db.corporate_actions.find_one({"id": action_id}, {"_id": 0})
    if not action:
        raise HTTPException(status_code=404, detail="Corporate action not found")
    
    if action["status"] == "applied":
        raise HTTPException(status_code=400, detail="Cannot delete applied corporate action")
    
    await db.corporate_actions.delete_one({"id": action_id})
    return {"message": "Corporate action deleted successfully"}
