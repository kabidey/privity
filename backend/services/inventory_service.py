"""
Inventory service for stock calculations
"""
import logging
from database import db


async def update_inventory(stock_id: str):
    """Recalculate weighted average and available quantity for a stock"""
    # Get all purchases for this stock
    purchases = await db.purchases.find({"stock_id": stock_id}, {"_id": 0}).to_list(10000)
    
    # Calculate total purchased quantity and weighted average
    total_qty = 0
    total_value = 0
    for purchase in purchases:
        total_qty += purchase["quantity"]
        total_value += purchase["quantity"] * purchase["price_per_unit"]
    
    # Get total booked quantity (only approved bookings reduce inventory)
    booked_result = await db.bookings.aggregate([
        {"$match": {"stock_id": stock_id, "approval_status": "approved"}},
        {"$group": {"_id": None, "total_booked": {"$sum": "$quantity"}}}
    ]).to_list(1)
    
    total_booked = booked_result[0]["total_booked"] if booked_result else 0
    
    # Calculate available quantity and weighted average price
    available_qty = total_qty - total_booked
    weighted_avg = total_value / total_qty if total_qty > 0 else 0
    
    # Get stock info
    stock = await db.stocks.find_one({"id": stock_id}, {"_id": 0})
    
    # Update or create inventory record
    inventory_doc = {
        "stock_id": stock_id,
        "stock_symbol": stock["symbol"] if stock else "",
        "stock_name": stock["name"] if stock else "",
        "available_quantity": available_qty,
        "weighted_avg_price": round(weighted_avg, 2),
        "total_value": round(available_qty * weighted_avg, 2),
        "last_updated": ""
    }
    
    await db.inventory.update_one(
        {"stock_id": stock_id},
        {"$set": inventory_doc},
        upsert=True
    )
    
    logging.info(f"Inventory updated for stock {stock_id}: {available_qty} @ {weighted_avg:.2f}")
    
    return inventory_doc


async def get_stock_weighted_avg_price(stock_id: str) -> float:
    """Get the weighted average price for a stock from inventory"""
    inventory = await db.inventory.find_one({"stock_id": stock_id}, {"_id": 0})
    if inventory:
        return inventory.get("weighted_avg_price", 0)
    return 0


async def check_stock_availability(stock_id: str, required_qty: int) -> tuple:
    """Check if stock has sufficient quantity available
    Returns: (is_available, available_qty, weighted_avg_price)
    """
    inventory = await db.inventory.find_one({"stock_id": stock_id}, {"_id": 0})
    if not inventory:
        return False, 0, 0
    
    available_qty = inventory.get("available_quantity", 0)
    weighted_avg = inventory.get("weighted_avg_price", 0)
    
    return available_qty >= required_qty, available_qty, weighted_avg
