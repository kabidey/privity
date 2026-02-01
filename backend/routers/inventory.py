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


@router.get("", response_model=List[InventoryModel])
async def get_inventory(current_user: dict = Depends(get_current_user)):
    """Get all inventory items with weighted average pricing"""
    inventory = await db.inventory.find({}, {"_id": 0}).to_list(10000)
    
    # Enrich with stock details
    stock_ids = list(set(item.get("stock_id") for item in inventory if item.get("stock_id")))
    stocks = await db.stocks.find({"id": {"$in": stock_ids}}, {"_id": 0}).to_list(1000)
    stock_map = {s["id"]: s for s in stocks}
    
    for item in inventory:
        stock = stock_map.get(item.get("stock_id"), {})
        item["stock_symbol"] = stock.get("symbol", "Unknown")
        item["stock_name"] = stock.get("name", "Unknown")
        
        # Ensure weighted_avg_price and total_value exist (for backwards compatibility)
        if "weighted_avg_price" not in item:
            item["weighted_avg_price"] = 0
        if "total_value" not in item:
            item["total_value"] = 0
    
    return inventory


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
