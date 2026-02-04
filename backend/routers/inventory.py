"""
Inventory Router
Handles inventory management endpoints
"""
from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends
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
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("inventory.view", "view inventory"))
):
    """
    Get all inventory items with dynamically calculated weighted average pricing.
    
    - PE Desk/Manager: See both WAP (Weighted Avg Price) and LP (Landing Price)
    - Other users: Only see LP (Landing Price) - WAP is hidden
    """
    user_role = current_user.get("role", 6)
    is_pe = is_pe_level(user_role)
    
    # Build query with demo isolation filter
    query = {}
    query = add_demo_filter(query, current_user)
    
    inventory = await db.inventory.find(query, {"_id": 0}).to_list(10000)
    
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
