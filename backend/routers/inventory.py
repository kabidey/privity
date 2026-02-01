"""
Inventory Router
Handles inventory management endpoints
"""
from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends

from database import db
from config import is_pe_level
from models import Inventory as InventoryModel
from utils.auth import get_current_user

router = APIRouter(prefix="/inventory", tags=["Inventory"])


async def calculate_weighted_avg_for_stock(stock_id: str) -> dict:
    """
    Calculate weighted average price from all received purchases for a stock.
    This ensures accurate pricing based on actual purchase history.
    """
    # Get all purchases for this stock that have been received (dp_status = 'received')
    purchases = await db.purchases.find(
        {"stock_id": stock_id, "dp_status": "received"},
        {"_id": 0, "quantity": 1, "total_amount": 1, "price_per_share": 1}
    ).to_list(10000)
    
    if not purchases:
        return {"weighted_avg_price": 0, "total_value": 0, "total_purchased_qty": 0}
    
    total_quantity = 0
    total_value = 0
    
    for p in purchases:
        qty = p.get("quantity", 0)
        amount = p.get("total_amount", 0)
        total_quantity += qty
        total_value += amount
    
    weighted_avg = total_value / total_quantity if total_quantity > 0 else 0
    
    return {
        "weighted_avg_price": round(weighted_avg, 2),
        "total_value": round(total_value, 2),
        "total_purchased_qty": total_quantity
    }


@router.get("", response_model=List[InventoryModel])
async def get_inventory(current_user: dict = Depends(get_current_user)):
    """Get all inventory items with dynamically calculated weighted average pricing"""
    inventory = await db.inventory.find({}, {"_id": 0}).to_list(10000)
    
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
        item["weighted_avg_price"] = calc["weighted_avg_price"]
        item["total_value"] = calc["total_value"]
        
        result.append(item)
    
    return result


@router.get("/{stock_id}", response_model=InventoryModel)
async def get_inventory_item(stock_id: str, current_user: dict = Depends(get_current_user)):
    """Get inventory for a specific stock"""
    inventory = await db.inventory.find_one({"stock_id": stock_id}, {"_id": 0})
    if not inventory:
        raise HTTPException(status_code=404, detail="Inventory not found")
    
    # Enrich with stock details
    stock = await db.stocks.find_one({"id": stock_id}, {"_id": 0})
    if stock:
        inventory["stock_symbol"] = stock.get("symbol", "Unknown")
        inventory["stock_name"] = stock.get("name", "Unknown")
    
    return inventory


@router.delete("/{stock_id}")
async def delete_inventory(stock_id: str, current_user: dict = Depends(get_current_user)):
    """Delete inventory for a stock (PE Desk only)"""
    user_role = current_user.get("role", 6)
    
    if user_role != 1:  # Only PE Desk
        raise HTTPException(status_code=403, detail="Only PE Desk can delete inventory")
    
    result = await db.inventory.delete_one({"stock_id": stock_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Inventory not found")
    
    return {"message": "Inventory deleted successfully"}
