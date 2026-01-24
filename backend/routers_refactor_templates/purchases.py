"""
Purchase and Inventory management routes
"""
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Depends

from database import db
from models import PurchaseCreate, Purchase, Inventory
from utils.auth import get_current_user, check_permission
from services.email_service import send_email

router = APIRouter(tags=["Purchases & Inventory"])


async def update_inventory(stock_id: str):
    """Recalculate weighted average and available quantity for a stock"""
    purchases = await db.purchases.find({"stock_id": stock_id}, {"_id": 0}).to_list(10000)
    bookings = await db.bookings.find({"stock_id": stock_id}, {"_id": 0}).to_list(10000)
    
    total_purchased_qty = sum(p["quantity"] for p in purchases)
    total_purchased_value = sum(p["quantity"] * p["price_per_unit"] for p in purchases)
    
    total_sold_qty = sum(b["quantity"] for b in bookings)
    
    weighted_avg = total_purchased_value / total_purchased_qty if total_purchased_qty > 0 else 0
    available_qty = total_purchased_qty - total_sold_qty
    
    stock = await db.stocks.find_one({"id": stock_id}, {"_id": 0})
    
    inventory_data = {
        "stock_id": stock_id,
        "stock_symbol": stock["symbol"] if stock else "Unknown",
        "stock_name": stock["name"] if stock else "Unknown",
        "available_quantity": available_qty,
        "weighted_avg_price": weighted_avg,
        "total_value": available_qty * weighted_avg
    }
    
    await db.inventory.update_one(
        {"stock_id": stock_id},
        {"$set": inventory_data},
        upsert=True
    )
    
    return inventory_data


@router.post("/purchases", response_model=Purchase)
async def create_purchase(purchase_data: PurchaseCreate, current_user: dict = Depends(get_current_user)):
    """Create a new purchase from vendor (PE Desk only)"""
    user_role = current_user.get("role", 5)
    
    if user_role != 1:
        raise HTTPException(status_code=403, detail="Only PE Desk can create vendor purchases")
    
    check_permission(current_user, "manage_purchases")
    
    vendor = await db.clients.find_one({"id": purchase_data.vendor_id, "is_vendor": True}, {"_id": 0})
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    
    stock = await db.stocks.find_one({"id": purchase_data.stock_id}, {"_id": 0})
    if not stock:
        raise HTTPException(status_code=404, detail="Stock not found")
    
    purchase_id = str(uuid.uuid4())
    total_amount = purchase_data.quantity * purchase_data.price_per_unit
    
    purchase_doc = {
        "id": purchase_id,
        **purchase_data.model_dump(),
        "total_amount": total_amount,
        "user_id": current_user["id"],
        "created_by": current_user["id"],
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.purchases.insert_one(purchase_doc)
    
    await update_inventory(purchase_data.stock_id)
    
    if vendor.get("email"):
        await send_email(
            vendor["email"],
            "Purchase Order Confirmation",
            f"<p>Dear {vendor['name']},</p><p>A purchase order has been created for {purchase_data.quantity} units of {stock['symbol']}.</p>"
        )
    
    return Purchase(
        id=purchase_id,
        vendor_id=purchase_data.vendor_id,
        vendor_name=vendor["name"],
        stock_id=purchase_data.stock_id,
        stock_symbol=stock["symbol"],
        quantity=purchase_data.quantity,
        price_per_unit=purchase_data.price_per_unit,
        total_amount=total_amount,
        purchase_date=purchase_data.purchase_date,
        notes=purchase_data.notes,
        created_at=purchase_doc["created_at"],
        created_by=current_user["id"]
    )


@router.get("/purchases", response_model=List[Purchase])
async def get_purchases(
    vendor_id: Optional[str] = None,
    stock_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get list of purchases (PE Desk only)"""
    user_role = current_user.get("role", 5)
    
    if user_role != 1:
        raise HTTPException(status_code=403, detail="Only PE Desk can access vendor purchase history")
    
    check_permission(current_user, "manage_purchases")
    
    query = {}
    if vendor_id:
        query["vendor_id"] = vendor_id
    if stock_id:
        query["stock_id"] = stock_id
    
    purchases = await db.purchases.find(query, {"_id": 0, "user_id": 0}).to_list(1000)
    
    if purchases:
        vendor_ids = list(set(p["vendor_id"] for p in purchases))
        stock_ids = list(set(p["stock_id"] for p in purchases))
        
        vendors = await db.clients.find({"id": {"$in": vendor_ids}}, {"_id": 0}).to_list(1000)
        stocks = await db.stocks.find({"id": {"$in": stock_ids}}, {"_id": 0}).to_list(1000)
        
        vendor_map = {v["id"]: v for v in vendors}
        stock_map = {s["id"]: s for s in stocks}
        
        enriched_purchases = []
        for p in purchases:
            vendor = vendor_map.get(p["vendor_id"])
            stock = stock_map.get(p["stock_id"])
            enriched_purchases.append(Purchase(
                **p,
                vendor_name=vendor["name"] if vendor else "Unknown",
                stock_symbol=stock["symbol"] if stock else "Unknown"
            ))
        
        return enriched_purchases
    
    return []


@router.get("/inventory", response_model=List[Inventory])
async def get_inventory(current_user: dict = Depends(get_current_user)):
    """Get all inventory records"""
    inventory = await db.inventory.find({}, {"_id": 0}).to_list(1000)
    return inventory


@router.get("/inventory/{stock_id}", response_model=Inventory)
async def get_stock_inventory(stock_id: str, current_user: dict = Depends(get_current_user)):
    """Get inventory for a specific stock"""
    inventory = await db.inventory.find_one({"stock_id": stock_id}, {"_id": 0})
    if not inventory:
        raise HTTPException(status_code=404, detail="Inventory not found for this stock")
    return inventory
