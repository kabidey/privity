"""
Inventory Service with High-Concurrency Support

This service handles all inventory operations with proper locking and atomic updates
to prevent race conditions during simultaneous booking requests.
"""
import asyncio
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Tuple
from database import db, client
import logging

logger = logging.getLogger(__name__)

# In-memory locks for inventory operations (per stock)
_inventory_locks: Dict[str, asyncio.Lock] = {}


def get_inventory_lock(stock_id: str) -> asyncio.Lock:
    """Get or create a lock for a specific stock's inventory."""
    if stock_id not in _inventory_locks:
        _inventory_locks[stock_id] = asyncio.Lock()
    return _inventory_locks[stock_id]


async def update_inventory(stock_id: str) -> Dict[str, Any]:
    """
    Recalculate inventory for a stock (backward compatible function).
    
    This function recalculates:
    - available_quantity: Stock available for new bookings
    - blocked_quantity: Stock reserved for approved bookings
    - weighted_avg_price: Average purchase price
    
    Returns the updated inventory data.
    """
    lock = get_inventory_lock(stock_id)
    
    async with lock:
        return await _recalculate_inventory_internal(stock_id)


async def _recalculate_inventory_internal(stock_id: str) -> Dict[str, Any]:
    """Internal recalculation without lock (caller must hold lock)."""
    # Get all purchases for this stock
    purchases = await db.purchases.find({"stock_id": stock_id}, {"_id": 0}).to_list(10000)
    
    # Get all bookings for this stock
    bookings = await db.bookings.find({"stock_id": stock_id}, {"_id": 0}).to_list(10000)
    
    # Calculate total purchased
    total_purchased_qty = sum(p["quantity"] for p in purchases)
    total_purchased_value = sum(p["quantity"] * p["price_per_unit"] for p in purchases)
    
    # Calculate blocked quantity (approved bookings not yet transferred)
    blocked_qty = sum(
        b["quantity"] for b in bookings 
        if b.get("approval_status") == "approved" 
        and not b.get("is_voided", False)
        and not b.get("stock_transferred", False)
    )
    
    # Calculate transferred quantity (completed sales)
    transferred_qty = sum(
        b["quantity"] for b in bookings 
        if b.get("stock_transferred") == True
        and not b.get("is_voided", False)
    )
    
    # Available = purchased - transferred - blocked
    available_qty = total_purchased_qty - transferred_qty - blocked_qty
    
    # Calculate weighted average from total purchases
    weighted_avg = total_purchased_value / total_purchased_qty if total_purchased_qty > 0 else 0
    
    # Get stock details
    stock = await db.stocks.find_one({"id": stock_id}, {"_id": 0})
    
    # Update or insert inventory
    inventory_data = {
        "stock_id": stock_id,
        "stock_symbol": stock["symbol"] if stock else "Unknown",
        "stock_name": stock["name"] if stock else "Unknown",
        "available_quantity": max(0, available_qty),
        "blocked_quantity": blocked_qty,
        "weighted_avg_price": round(weighted_avg, 2),
        "total_value": round(max(0, available_qty) * weighted_avg, 2),
        "last_updated": datetime.now(timezone.utc).isoformat()
    }
    
    await db.inventory.update_one(
        {"stock_id": stock_id},
        {"$set": inventory_data},
        upsert=True
    )
    
    logger.info(f"Inventory updated for stock {stock_id}: available={available_qty}, blocked={blocked_qty}")
    return inventory_data


async def check_and_reserve_inventory(
    stock_id: str, 
    quantity: int,
    booking_id: str
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Atomically check inventory availability and create a reservation.
    
    This uses in-memory locking with MongoDB atomic operations to prevent
    race conditions when multiple bookings try to reserve the same stock.
    
    Args:
        stock_id: The stock to reserve
        quantity: Amount to reserve
        booking_id: The booking ID making the reservation
    
    Returns:
        Tuple of (success, message, inventory_data)
    """
    lock = get_inventory_lock(stock_id)
    
    async with lock:
        # First recalculate to ensure consistency
        await _recalculate_inventory_internal(stock_id)
        
        # Get current inventory
        inventory = await db.inventory.find_one({"stock_id": stock_id}, {"_id": 0})
        
        if not inventory:
            return False, "Inventory record not found for this stock", None
        
        available = inventory.get("available_quantity", 0)
        
        if available < quantity:
            return False, f"Insufficient inventory. Available: {available}, Requested: {quantity}", inventory
        
        # Atomic update: decrement available and increment blocked
        result = await db.inventory.find_one_and_update(
            {
                "stock_id": stock_id,
                "available_quantity": {"$gte": quantity}  # Optimistic lock condition
            },
            {
                "$inc": {
                    "available_quantity": -quantity,
                    "blocked_quantity": quantity
                },
                "$set": {
                    "last_updated": datetime.now(timezone.utc).isoformat()
                }
            },
            return_document=True
        )
        
        if result is None:
            # Race condition detected - another booking took the inventory
            current = await db.inventory.find_one({"stock_id": stock_id}, {"_id": 0})
            return False, f"Inventory changed during reservation. Current available: {current.get('available_quantity', 0) if current else 0}", current
        
        # Remove _id from result before returning
        result.pop("_id", None)
        
        logger.info(f"Reserved {quantity} units of stock {stock_id} for booking {booking_id}")
        return True, "Inventory reserved successfully", result


async def release_inventory_reservation(
    stock_id: str,
    quantity: int,
    booking_id: str
) -> Tuple[bool, str]:
    """
    Release a previously made inventory reservation.
    
    Used when:
    - Booking is voided
    - Booking is rejected
    - Booking fails validation
    
    Args:
        stock_id: The stock to release
        quantity: Amount to release
        booking_id: The booking ID releasing the reservation
    
    Returns:
        Tuple of (success, message)
    """
    lock = get_inventory_lock(stock_id)
    
    async with lock:
        result = await db.inventory.find_one_and_update(
            {"stock_id": stock_id},
            {
                "$inc": {
                    "available_quantity": quantity,
                    "blocked_quantity": -quantity
                },
                "$set": {
                    "last_updated": datetime.now(timezone.utc).isoformat()
                }
            },
            return_document=True
        )
        
        if result is None:
            logger.warning(f"Failed to release reservation for stock {stock_id}, booking {booking_id}")
            return False, "Failed to release inventory reservation"
        
        logger.info(f"Released {quantity} units of stock {stock_id} from booking {booking_id}")
        return True, "Inventory released successfully"


async def transfer_inventory(
    stock_id: str,
    quantity: int,
    booking_id: str
) -> Tuple[bool, str]:
    """
    Mark inventory as transferred (completed sale).
    
    Moves stock from blocked to transferred status.
    
    Args:
        stock_id: The stock being transferred
        quantity: Amount being transferred
        booking_id: The booking ID for the transfer
    
    Returns:
        Tuple of (success, message)
    """
    lock = get_inventory_lock(stock_id)
    
    async with lock:
        # Decrement blocked quantity (available stays same since it was already blocked)
        result = await db.inventory.find_one_and_update(
            {
                "stock_id": stock_id,
                "blocked_quantity": {"$gte": quantity}
            },
            {
                "$inc": {
                    "blocked_quantity": -quantity
                },
                "$set": {
                    "last_updated": datetime.now(timezone.utc).isoformat()
                }
            },
            return_document=True
        )
        
        if result is None:
            logger.warning(f"Failed to transfer inventory for stock {stock_id}, booking {booking_id}")
            return False, "Failed to mark inventory as transferred"
        
        logger.info(f"Transferred {quantity} units of stock {stock_id} for booking {booking_id}")
        return True, "Inventory transferred successfully"


async def get_stock_weighted_avg_price(stock_id: str) -> float:
    """Get the weighted average price for a stock from inventory"""
    inventory = await db.inventory.find_one({"stock_id": stock_id}, {"_id": 0})
    if inventory:
        return inventory.get("weighted_avg_price", 0)
    return 0


async def check_stock_availability(stock_id: str, required_qty: int) -> Tuple[bool, int, float]:
    """
    Check if stock has sufficient quantity available.
    
    Returns: (is_available, available_qty, weighted_avg_price)
    """
    lock = get_inventory_lock(stock_id)
    
    async with lock:
        inventory = await db.inventory.find_one({"stock_id": stock_id}, {"_id": 0})
        if not inventory:
            return False, 0, 0
        
        available_qty = inventory.get("available_quantity", 0)
        weighted_avg = inventory.get("weighted_avg_price", 0)
        
        return available_qty >= required_qty, available_qty, weighted_avg


async def get_inventory_with_lock(stock_id: str) -> Optional[Dict[str, Any]]:
    """
    Get inventory data with a lock to prevent concurrent reads during critical operations.
    """
    lock = get_inventory_lock(stock_id)
    
    async with lock:
        inventory = await db.inventory.find_one({"stock_id": stock_id}, {"_id": 0})
        return inventory


async def batch_check_inventory(stock_ids: list) -> Dict[str, Dict[str, Any]]:
    """
    Check inventory for multiple stocks at once.
    
    Useful for bulk operations or dashboard views.
    
    Args:
        stock_ids: List of stock IDs to check
    
    Returns:
        Dictionary mapping stock_id to inventory data
    """
    inventories = await db.inventory.find(
        {"stock_id": {"$in": stock_ids}},
        {"_id": 0}
    ).to_list(len(stock_ids))
    
    return {inv["stock_id"]: inv for inv in inventories}
