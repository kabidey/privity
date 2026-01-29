"""
Booking management routes including payments and DP transfer
"""
import os
import uuid
import io
from datetime import datetime, timezone
from typing import List, Optional

import pandas as pd
from fastapi import APIRouter, HTTPException, Depends, File, UploadFile, Response

from database import db
from config import ROLES, ROLE_PERMISSIONS
from models import (
    BookingCreate, Booking, BookingWithDetails, 
    PaymentTrancheCreate, ClientConfirmationRequest
)
from utils.auth import get_current_user, check_permission
from services.email_service import send_email
from services.notification_service import create_notification, notify_roles
from services.audit_service import create_audit_log

router = APIRouter(tags=["Bookings"])


async def generate_booking_number() -> str:
    """Generate unique human-readable booking number (e.g., BK-2026-00001)"""
    year = datetime.now(timezone.utc).strftime("%Y")
    
    last_booking = await db.bookings.find_one(
        {"booking_number": {"$regex": f"^BK-{year}-"}},
        {"_id": 0, "booking_number": 1},
        sort=[("booking_number", -1)]
    )
    
    if last_booking and last_booking.get("booking_number"):
        try:
            last_seq = int(last_booking["booking_number"].split("-")[-1])
            new_seq = last_seq + 1
        except (ValueError, IndexError):
            new_seq = 1
    else:
        new_seq = 1
    
    return f"BK-{year}-{new_seq:05d}"


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


@router.post("/bookings", response_model=Booking)
async def create_booking(booking_data: BookingCreate, current_user: dict = Depends(get_current_user)):
    """Create a new booking"""
    user_role = current_user.get("role", 5)
    
    if user_role == 4:
        check_permission(current_user, "create_bookings")
    else:
        check_permission(current_user, "manage_bookings")
    
    client = await db.clients.find_one({"id": booking_data.client_id}, {"_id": 0})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    if client.get("approval_status") != "approved":
        raise HTTPException(
            status_code=400, 
            detail="Client must be approved by PE Desk before creating bookings. Current status: " + client.get("approval_status", "pending")
        )
    
    if not client.get("is_active", True):
        raise HTTPException(status_code=400, detail="Client is inactive and cannot be used for bookings")
    
    if user_role == 4:
        if client.get("mapped_employee_id") != current_user["id"] and client.get("created_by") != current_user["id"]:
            raise HTTPException(status_code=403, detail="You can only create bookings for your own clients")
    
    stock = await db.stocks.find_one({"id": booking_data.stock_id}, {"_id": 0})
    if not stock:
        raise HTTPException(status_code=404, detail="Stock not found")
    
    inventory = await db.inventory.find_one({"stock_id": booking_data.stock_id}, {"_id": 0})
    
    if not inventory or inventory["available_quantity"] < booking_data.quantity:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient inventory. Available: {inventory['available_quantity'] if inventory else 0}"
        )
    
    if user_role == 4:
        buying_price = inventory["weighted_avg_price"]
    else:
        buying_price = booking_data.buying_price if booking_data.buying_price else inventory["weighted_avg_price"]
    
    booking_id = str(uuid.uuid4())
    booking_number = await generate_booking_number()
    
    is_loss_booking = False
    loss_approval_status = "not_required"
    if booking_data.selling_price is not None and booking_data.selling_price < buying_price:
        is_loss_booking = True
        loss_approval_status = "pending"
    
    confirmation_token = str(uuid.uuid4())
    
    booking_doc = {
        "id": booking_id,
        "booking_number": booking_number,
        "client_id": booking_data.client_id,
        "stock_id": booking_data.stock_id,
        "quantity": booking_data.quantity,
        "buying_price": buying_price,
        "selling_price": booking_data.selling_price,
        "booking_date": booking_data.booking_date,
        "status": booking_data.status,
        "approval_status": "pending",
        "approved_by": None,
        "approved_at": None,
        "client_confirmation_status": "pending",
        "client_confirmation_token": confirmation_token,
        "client_confirmed_at": None,
        "client_denial_reason": None,
        "is_loss_booking": is_loss_booking,
        "loss_approval_status": loss_approval_status,
        "loss_approved_by": None,
        "loss_approved_at": None,
        "notes": booking_data.notes,
        "user_id": current_user["id"],
        "created_by": current_user["id"],
        "created_by_name": current_user["name"],
        "created_by_role": user_role,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.bookings.insert_one(booking_doc)
    
    await create_audit_log(
        action="BOOKING_CREATE",
        entity_type="booking",
        entity_id=booking_id,
        user_id=current_user["id"],
        user_name=current_user["name"],
        user_role=user_role,
        entity_name=f"{stock['symbol']} - {client['name']} ({booking_number})",
        details={
            "client_id": booking_data.client_id,
            "client_name": client["name"],
            "stock_id": booking_data.stock_id,
            "stock_symbol": stock["symbol"],
            "quantity": booking_data.quantity,
            "buying_price": buying_price,
            "selling_price": booking_data.selling_price
        }
    )
    
    if client.get("email"):
        email_body = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #064E3B;">Booking Order Created</h2>
            <p>Dear {client['name']},</p>
            <p>A new booking order has been created and is pending internal approval. You will receive another email to confirm your acceptance once approved.</p>
            
            <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
                <tr style="background-color: #f3f4f6;">
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Order ID</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">{booking_number}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Stock</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">{stock['symbol']} - {stock['name']}</td>
                </tr>
                <tr style="background-color: #f3f4f6;">
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Quantity</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">{booking_data.quantity}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Status</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><span style="color: #f59e0b;">Pending Internal Approval</span></td>
                </tr>
            </table>
            
            <p style="color: #6b7280; font-size: 14px;">This is an automated notification. You will receive a confirmation request email once the booking is approved internally.</p>
            
            <p>Best regards,<br><strong>SMIFS Private Equity System</strong></p>
        </div>
        """
        
        await send_email(
            client["email"],
            f"Booking Created - Pending Approval | {booking_number}",
            email_body,
            cc_email=current_user.get("email")
        )
    
    await notify_roles(
        [1],
        "booking_pending",
        "New Booking Pending Approval",
        f"Booking {booking_number} for '{client['name']}' - {stock['symbol']} x {booking_data.quantity} awaiting PE Desk approval",
        {"booking_id": booking_id, "booking_number": booking_number, "client_name": client["name"], "stock_symbol": stock["symbol"]}
    )
    
    return Booking(**{k: v for k, v in booking_doc.items() if k not in ["user_id", "created_by_name"]})


@router.get("/bookings", response_model=List[BookingWithDetails])
async def get_bookings(
    client_id: Optional[str] = None,
    stock_id: Optional[str] = None,
    status: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get list of bookings with optional filters"""
    query = {}
    
    if current_user.get("role", 5) >= 3:
        if "view_all" not in ROLE_PERMISSIONS.get(current_user.get("role", 5), []):
            query["created_by"] = current_user["id"]
    
    if client_id:
        query["client_id"] = client_id
    if stock_id:
        query["stock_id"] = stock_id
    if status:
        query["status"] = status
    
    bookings = await db.bookings.find(query, {"_id": 0, "user_id": 0}).to_list(1000)
    
    if not bookings:
        return []
    
    client_ids = list(set(b["client_id"] for b in bookings))
    stock_ids = list(set(b["stock_id"] for b in bookings))
    user_ids = list(set(b["created_by"] for b in bookings))
    
    clients = await db.clients.find({"id": {"$in": client_ids}}, {"_id": 0}).to_list(1000)
    stocks = await db.stocks.find({"id": {"$in": stock_ids}}, {"_id": 0}).to_list(1000)
    users = await db.users.find({"id": {"$in": user_ids}}, {"_id": 0}).to_list(1000)
    
    client_map = {c["id"]: c for c in clients}
    stock_map = {s["id"]: s for s in stocks}
    user_map = {u["id"]: u for u in users}
    
    enriched_bookings = []
    for booking in bookings:
        client = client_map.get(booking["client_id"])
        stock = stock_map.get(booking["stock_id"])
        user = user_map.get(booking["created_by"])
        
        profit_loss = None
        if booking.get("selling_price") and booking["status"] == "closed":
            profit_loss = (booking["selling_price"] - booking["buying_price"]) * booking["quantity"]
        
        booking_data = {k: v for k, v in booking.items() if k not in ["client_name", "stock_symbol", "stock_name", "created_by_name", "profit_loss"]}
        
        enriched_bookings.append(BookingWithDetails(
            **booking_data,
            client_name=client["name"] if client else "Unknown",
            stock_symbol=stock["symbol"] if stock else "Unknown",
            stock_name=stock["name"] if stock else "Unknown",
            created_by_name=user["name"] if user else "Unknown",
            profit_loss=profit_loss
        ))
    
    return enriched_bookings


@router.get("/bookings/pending-approval", response_model=List[BookingWithDetails])
async def get_pending_bookings(current_user: dict = Depends(get_current_user)):
    """Get bookings pending approval (PE Desk only)"""
    if current_user.get("role", 5) != 1:
        raise HTTPException(status_code=403, detail="Only PE Desk can view pending bookings")
    
    bookings = await db.bookings.find(
        {"approval_status": "pending"},
        {"_id": 0, "user_id": 0}
    ).to_list(1000)
    
    if not bookings:
        return []
    
    client_ids = list(set(b["client_id"] for b in bookings))
    stock_ids = list(set(b["stock_id"] for b in bookings))
    
    clients = await db.clients.find({"id": {"$in": client_ids}}, {"_id": 0}).to_list(1000)
    stocks = await db.stocks.find({"id": {"$in": stock_ids}}, {"_id": 0}).to_list(1000)
    
    client_map = {c["id"]: c for c in clients}
    stock_map = {s["id"]: s for s in stocks}
    
    enriched = []
    for b in bookings:
        client = client_map.get(b["client_id"], {})
        stock = stock_map.get(b["stock_id"], {})
        enriched.append(BookingWithDetails(
            **b,
            client_name=client.get("name", "Unknown"),
            stock_symbol=stock.get("symbol", "Unknown"),
            stock_name=stock.get("name", "Unknown")
        ))
    
    return enriched


@router.get("/bookings/pending-loss-approval", response_model=List[BookingWithDetails])
async def get_pending_loss_bookings(current_user: dict = Depends(get_current_user)):
    """Get loss bookings pending approval (PE Desk only)"""
    if current_user.get("role", 5) != 1:
        raise HTTPException(status_code=403, detail="Only PE Desk can view pending loss bookings")
    
    bookings = await db.bookings.find(
        {"is_loss_booking": True, "loss_approval_status": "pending"},
        {"_id": 0, "user_id": 0}
    ).to_list(1000)
    
    if not bookings:
        return []
    
    client_ids = list(set(b["client_id"] for b in bookings))
    stock_ids = list(set(b["stock_id"] for b in bookings))
    user_ids = list(set(b["created_by"] for b in bookings))
    
    clients = await db.clients.find({"id": {"$in": client_ids}}, {"_id": 0}).to_list(1000)
    stocks = await db.stocks.find({"id": {"$in": stock_ids}}, {"_id": 0}).to_list(1000)
    users = await db.users.find({"id": {"$in": user_ids}}, {"_id": 0}).to_list(1000)
    
    client_map = {c["id"]: c for c in clients}
    stock_map = {s["id"]: s for s in stocks}
    user_map = {u["id"]: u for u in users}
    
    enriched = []
    for b in bookings:
        client = client_map.get(b["client_id"], {})
        stock = stock_map.get(b["stock_id"], {})
        user = user_map.get(b["created_by"], {})
        
        profit_loss = None
        if b.get("selling_price"):
            profit_loss = (b["selling_price"] - b["buying_price"]) * b["quantity"]
        
        booking_data = {k: v for k, v in b.items() if k not in ["client_name", "stock_symbol", "stock_name", "created_by_name", "profit_loss"]}
        
        enriched.append(BookingWithDetails(
            **booking_data,
            client_name=client.get("name", "Unknown"),
            client_pan=client.get("pan_number"),
            client_dp_id=client.get("dp_id"),
            stock_symbol=stock.get("symbol", "Unknown"),
            stock_name=stock.get("name", "Unknown"),
            created_by_name=user.get("name", "Unknown"),
            profit_loss=profit_loss
        ))
    
    return enriched


@router.get("/bookings/{booking_id}", response_model=BookingWithDetails)
async def get_booking(booking_id: str, current_user: dict = Depends(get_current_user)):
    """Get a single booking by ID"""
    booking = await db.bookings.find_one({"id": booking_id}, {"_id": 0, "user_id": 0})
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    client = await db.clients.find_one({"id": booking["client_id"]}, {"_id": 0})
    stock = await db.stocks.find_one({"id": booking["stock_id"]}, {"_id": 0})
    user = await db.users.find_one({"id": booking["created_by"]}, {"_id": 0})
    
    profit_loss = None
    if booking.get("selling_price") and booking["status"] == "closed":
        profit_loss = (booking["selling_price"] - booking["buying_price"]) * booking["quantity"]
    
    booking_data = {k: v for k, v in booking.items() if k not in ["client_name", "stock_symbol", "stock_name", "created_by_name", "profit_loss"]}
    
    return BookingWithDetails(
        **booking_data,
        client_name=client["name"] if client else "Unknown",
        stock_symbol=stock["symbol"] if stock else "Unknown",
        stock_name=stock["name"] if stock else "Unknown",
        created_by_name=user["name"] if user else "Unknown",
        profit_loss=profit_loss
    )


@router.put("/bookings/{booking_id}", response_model=Booking)
async def update_booking(booking_id: str, booking_data: BookingCreate, current_user: dict = Depends(get_current_user)):
    """Update a booking"""
    user_role = current_user.get("role", 5)
    check_permission(current_user, "manage_bookings")
    
    old_booking = await db.bookings.find_one({"id": booking_id}, {"_id": 0})
    if not old_booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    client = await db.clients.find_one({"id": booking_data.client_id}, {"_id": 0})
    stock = await db.stocks.find_one({"id": booking_data.stock_id}, {"_id": 0})
    
    result = await db.bookings.update_one(
        {"id": booking_id},
        {"$set": booking_data.model_dump()}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    await update_inventory(booking_data.stock_id)
    
    await create_audit_log(
        action="BOOKING_UPDATE",
        entity_type="booking",
        entity_id=booking_id,
        user_id=current_user["id"],
        user_name=current_user["name"],
        user_role=user_role,
        entity_name=f"{stock['symbol'] if stock else 'Unknown'} - {client['name'] if client else 'Unknown'}",
        details={
            "booking_number": old_booking.get("booking_number", booking_id[:8].upper()),
            "changes": {
                "quantity": {"old": old_booking.get("quantity"), "new": booking_data.quantity},
                "selling_price": {"old": old_booking.get("selling_price"), "new": booking_data.selling_price},
                "status": {"old": old_booking.get("status"), "new": booking_data.status}
            }
        }
    )
    
    booking_number = old_booking.get("booking_number", booking_id[:8].upper())
    
    if old_booking.get("created_by") and old_booking["created_by"] != current_user["id"]:
        await create_notification(
            old_booking["created_by"],
            "booking_updated",
            "Booking Updated",
            f"Booking {booking_number} for {stock['symbol'] if stock else 'Unknown'} has been updated by {current_user['name']}",
            {"booking_id": booking_id, "stock_symbol": stock["symbol"] if stock else None, "updated_by": current_user["name"]}
        )
    
    if user_role != 1:
        await notify_roles(
            [1],
            "booking_updated",
            "Booking Modified",
            f"Booking {booking_number} modified by {current_user['name']}",
            {"booking_id": booking_id, "stock_symbol": stock["symbol"] if stock else None}
        )
    
    if old_booking["status"] != booking_data.status:
        if client and client.get("email"):
            await send_email(
                client["email"],
                "Booking Status Updated",
                f"<p>Dear {client['name']},</p><p>Your booking {booking_number} status has been updated to: <strong>{booking_data.status.upper()}</strong></p>"
            )
    
    updated_booking = await db.bookings.find_one({"id": booking_id}, {"_id": 0, "user_id": 0})
    return updated_booking


@router.delete("/bookings/{booking_id}")
async def delete_booking(booking_id: str, current_user: dict = Depends(get_current_user)):
    """Delete a booking (PE Desk only)"""
    user_role = current_user.get("role", 5)
    
    if user_role != 1:
        raise HTTPException(status_code=403, detail="Only PE Desk can delete bookings")
    
    booking = await db.bookings.find_one({"id": booking_id}, {"_id": 0})
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    client = await db.clients.find_one({"id": booking["client_id"]}, {"_id": 0})
    stock = await db.stocks.find_one({"id": booking["stock_id"]}, {"_id": 0})
    
    result = await db.bookings.delete_one({"id": booking_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    await create_audit_log(
        action="BOOKING_DELETE",
        entity_type="booking",
        entity_id=booking_id,
        user_id=current_user["id"],
        user_name=current_user["name"],
        user_role=user_role,
        entity_name=f"{stock['symbol'] if stock else 'Unknown'} - {client['name'] if client else 'Unknown'}",
        details={
            "booking_number": booking.get("booking_number", booking_id[:8].upper()),
            "client_name": client["name"] if client else "Unknown",
            "stock_symbol": stock["symbol"] if stock else "Unknown",
            "quantity": booking.get("quantity"),
            "deleted_by": current_user["name"]
        }
    )
    
    if booking.get("created_by") and booking["created_by"] != current_user["id"]:
        await create_notification(
            booking["created_by"],
            "booking_deleted",
            "Booking Deleted",
            f"Your booking {booking.get('booking_number', booking_id[:8].upper())} for {stock['symbol'] if stock else 'Unknown'} has been deleted by PE Desk",
            {"booking_id": booking_id, "stock_symbol": stock["symbol"] if stock else None, "deleted_by": current_user["name"]}
        )
    
    return {"message": "Booking deleted successfully"}


@router.put("/bookings/{booking_id}/approve")
async def approve_booking(
    booking_id: str,
    approve: bool = True,
    current_user: dict = Depends(get_current_user)
):
    """Approve or reject a booking (PE Desk only)"""
    user_role = current_user.get("role", 5)
    
    if user_role != 1:
        raise HTTPException(status_code=403, detail="Only PE Desk can approve bookings for inventory adjustment")
    
    booking = await db.bookings.find_one({"id": booking_id}, {"_id": 0})
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    if booking.get("approval_status") != "pending":
        raise HTTPException(status_code=400, detail="Booking already processed")
    
    update_data = {
        "approval_status": "approved" if approve else "rejected",
        "approved_by": current_user["id"],
        "approved_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.bookings.update_one({"id": booking_id}, {"$set": update_data})
    
    if approve:
        await update_inventory(booking["stock_id"])
        
        await create_audit_log(
            action="BOOKING_APPROVE",
            entity_type="booking",
            entity_id=booking_id,
            user_id=current_user["id"],
            user_name=current_user["name"],
            user_role=user_role,
            details={"stock_id": booking["stock_id"], "quantity": booking["quantity"]}
        )
        
        client = await db.clients.find_one({"id": booking["client_id"]}, {"_id": 0})
        stock = await db.stocks.find_one({"id": booking["stock_id"]}, {"_id": 0})
        creator = await db.users.find_one({"id": booking["created_by"]}, {"_id": 0})
        booking_number = booking.get("booking_number", booking_id[:8].upper())
        confirmation_token = booking.get("client_confirmation_token")
        
        is_loss_pending = booking.get("is_loss_booking") and booking.get("loss_approval_status") == "pending"
        
        if client and client.get("email"):
            if is_loss_pending:
                email_body = f"""
                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                    <h2 style="color: #f59e0b;">Booking Approved - Pending Loss Review</h2>
                    <p>Dear {client['name']},</p>
                    <p>Your booking order has been approved. However, since this is a loss transaction, it requires additional review. You will receive a confirmation request once fully approved.</p>
                    
                    <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
                        <tr style="background-color: #f3f4f6;">
                            <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Booking ID</strong></td>
                            <td style="padding: 10px; border: 1px solid #e5e7eb;">{booking_number}</td>
                        </tr>
                        <tr>
                            <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Stock</strong></td>
                            <td style="padding: 10px; border: 1px solid #e5e7eb;">{stock['symbol'] if stock else 'N/A'}</td>
                        </tr>
                        <tr style="background-color: #f3f4f6;">
                            <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Status</strong></td>
                            <td style="padding: 10px; border: 1px solid #e5e7eb;"><span style="color: #f59e0b;">Pending Loss Review</span></td>
                        </tr>
                    </table>
                    
                    <p>Best regards,<br><strong>SMIFS Private Equity System</strong></p>
                </div>
                """
                await send_email(
                    client["email"],
                    f"Booking Approved - Pending Loss Review | {booking_number}",
                    email_body,
                    cc_email=creator.get("email") if creator else None
                )
            else:
                frontend_url = os.environ.get('FRONTEND_URL', 'https://privity-desk.preview.emergentagent.com')
                email_body = f"""
                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                    <h2 style="color: #10b981;">Booking Approved - Please Confirm ✓</h2>
                    <p>Dear {client['name']},</p>
                    <p>Your booking order has been <strong style="color: #10b981;">APPROVED</strong> by PE Desk. Please confirm your acceptance to proceed.</p>
                    
                    <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
                        <tr style="background-color: #f3f4f6;">
                            <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Booking ID</strong></td>
                            <td style="padding: 10px; border: 1px solid #e5e7eb;">{booking_number}</td>
                        </tr>
                        <tr>
                            <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Client OTC UCC</strong></td>
                            <td style="padding: 10px; border: 1px solid #e5e7eb;">{client.get('otc_ucc', 'N/A')}</td>
                        </tr>
                        <tr style="background-color: #f3f4f6;">
                            <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Stock</strong></td>
                            <td style="padding: 10px; border: 1px solid #e5e7eb;">{stock['symbol'] if stock else 'N/A'} - {stock['name'] if stock else ''}</td>
                        </tr>
                        <tr>
                            <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Quantity</strong></td>
                            <td style="padding: 10px; border: 1px solid #e5e7eb;">{booking['quantity']}</td>
                        </tr>
                        <tr style="background-color: #f3f4f6;">
                            <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Landing Price</strong></td>
                            <td style="padding: 10px; border: 1px solid #e5e7eb;">₹{booking.get('buying_price', 0):,.2f}</td>
                        </tr>
                        <tr>
                            <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Total Value</strong></td>
                            <td style="padding: 10px; border: 1px solid #e5e7eb;">₹{(booking.get('buying_price', 0) * booking.get('quantity', 0)):,.2f}</td>
                        </tr>
                        <tr style="background-color: #f3f4f6;">
                            <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Approved By</strong></td>
                            <td style="padding: 10px; border: 1px solid #e5e7eb;">{current_user['name']} (PE Desk)</td>
                        </tr>
                    </table>
                    
                    <div style="margin: 30px 0; text-align: center;">
                        <p style="margin-bottom: 20px; font-weight: bold;">Please confirm your booking:</p>
                        <a href="{frontend_url}/booking-confirm/{booking_id}/{confirmation_token}/accept" 
                           style="display: inline-block; background-color: #22c55e; color: white; padding: 12px 30px; text-decoration: none; border-radius: 6px; margin-right: 10px; font-weight: bold;">
                            ✓ ACCEPT BOOKING
                        </a>
                        <a href="{frontend_url}/booking-confirm/{booking_id}/{confirmation_token}/deny" 
                           style="display: inline-block; background-color: #ef4444; color: white; padding: 12px 30px; text-decoration: none; border-radius: 6px; font-weight: bold;">
                            ✗ DENY BOOKING
                        </a>
                    </div>
                    
                    <p style="color: #6b7280; font-size: 14px;">Please review and confirm this booking. If you accept, payment can be initiated. If you deny, the booking will be cancelled.</p>
                    
                    <p>Best regards,<br><strong>SMIFS Private Equity System</strong></p>
                </div>
                """
                await send_email(
                    client["email"],
                    f"Action Required: Confirm Booking - {stock['symbol'] if stock else 'N/A'} | {booking_number}",
                    email_body,
                    cc_email=creator.get("email") if creator else None
                )
        
        if booking.get("created_by"):
            await create_notification(
                booking["created_by"],
                "booking_approved",
                "Booking Approved - Awaiting Client Confirmation",
                f"Your booking {booking_number} for '{stock['symbol'] if stock else 'N/A'}' has been approved. Client confirmation email sent.",
                {"booking_id": booking_id, "stock_symbol": stock['symbol'] if stock else None}
            )
    else:
        await create_audit_log(
            action="BOOKING_REJECT",
            entity_type="booking",
            entity_id=booking_id,
            user_id=current_user["id"],
            user_name=current_user["name"],
            user_role=user_role,
            details={"stock_id": booking["stock_id"], "quantity": booking["quantity"]}
        )
        
        stock = await db.stocks.find_one({"id": booking["stock_id"]}, {"_id": 0})
        if booking.get("created_by"):
            await create_notification(
                booking["created_by"],
                "booking_rejected",
                "Booking Rejected",
                f"Your booking for '{stock['symbol'] if stock else 'N/A'}' has been rejected",
                {"booking_id": booking_id, "stock_symbol": stock['symbol'] if stock else None}
            )
    
    return {"message": f"Booking {'approved' if approve else 'rejected'} successfully"}


# ============== Client Confirmation Endpoints (Public - no auth) ==============

@router.get("/booking-confirm/{booking_id}/{token}/{action}")
async def client_confirm_booking_get(booking_id: str, token: str, action: str):
    """Client confirms or denies booking via email link (GET for direct link click)"""
    return await process_client_confirmation(booking_id, token, action, None)


@router.post("/booking-confirm/{booking_id}/{token}/{action}")
async def client_confirm_booking_post(
    booking_id: str, 
    token: str, 
    action: str, 
    request: ClientConfirmationRequest = None
):
    """Client confirms or denies booking via email link (POST with optional reason)"""
    reason = request.reason if request else None
    return await process_client_confirmation(booking_id, token, action, reason)


async def process_client_confirmation(booking_id: str, token: str, action: str, reason: Optional[str]):
    """Process client confirmation/denial of booking"""
    if action not in ["accept", "deny"]:
        raise HTTPException(status_code=400, detail="Invalid action. Use 'accept' or 'deny'")
    
    booking = await db.bookings.find_one({"id": booking_id}, {"_id": 0})
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    # Validate token
    if booking.get("client_confirmation_token") != token:
        raise HTTPException(status_code=403, detail="Invalid confirmation token")
    
    # Check if booking is approved by PE Desk first
    if booking.get("approval_status") != "approved":
        return {
            "message": "This booking is still pending PE Desk approval. You cannot confirm it yet.",
            "status": "pending_approval",
            "booking_number": booking.get("booking_number", booking_id[:8].upper())
        }
    
    # Check if loss booking is approved (if applicable)
    if booking.get("is_loss_booking") and booking.get("loss_approval_status") == "pending":
        return {
            "message": "This is a loss booking that requires additional approval. You cannot confirm it yet.",
            "status": "pending_loss_approval",
            "booking_number": booking.get("booking_number", booking_id[:8].upper())
        }
    
    # Check if already confirmed
    if booking.get("client_confirmation_status") != "pending":
        return {
            "message": f"Booking has already been {booking.get('client_confirmation_status')}",
            "status": booking.get("client_confirmation_status")
        }
    
    # Get client and stock info
    client = await db.clients.find_one({"id": booking["client_id"]}, {"_id": 0})
    stock = await db.stocks.find_one({"id": booking["stock_id"]}, {"_id": 0})
    booking_number = booking.get("booking_number", booking_id[:8].upper())
    
    if action == "accept":
        update_data = {
            "client_confirmation_status": "accepted",
            "client_confirmed_at": datetime.now(timezone.utc).isoformat()
        }
        message = "Booking accepted successfully! Your order is now pending PE Desk approval."
        
        # Notify PE Desk about client acceptance
        await notify_roles(
            [1],
            "client_accepted",
            "Client Accepted Booking",
            f"Client {client['name'] if client else 'Unknown'} has accepted booking {booking_number} for {stock['symbol'] if stock else 'Unknown'}",
            {"booking_id": booking_id, "booking_number": booking_number}
        )
        
        # Notify booking creator
        if booking.get("created_by"):
            await create_notification(
                booking["created_by"],
                "client_accepted",
                "Client Accepted Booking",
                f"Client {client['name'] if client else 'Unknown'} has accepted booking {booking_number}",
                {"booking_id": booking_id, "booking_number": booking_number}
            )
        
    else:  # deny
        update_data = {
            "client_confirmation_status": "denied",
            "client_confirmed_at": datetime.now(timezone.utc).isoformat(),
            "client_denial_reason": reason or "No reason provided"
        }
        message = "Booking denied. The booking creator and PE Desk have been notified."
        
        # Notify PE Desk about denial
        await notify_roles(
            [1],
            "client_denied",
            "Client Denied Booking",
            f"Client {client['name'] if client else 'Unknown'} has DENIED booking {booking_number}. Reason: {reason or 'Not specified'}",
            {"booking_id": booking_id, "booking_number": booking_number, "reason": reason}
        )
        
        # Notify booking creator
        if booking.get("created_by"):
            await create_notification(
                booking["created_by"],
                "client_denied",
                "Client Denied Booking",
                f"Client {client['name'] if client else 'Unknown'} has denied booking {booking_number}. Reason: {reason or 'Not specified'}",
                {"booking_id": booking_id, "booking_number": booking_number, "reason": reason}
            )
    
    await db.bookings.update_one({"id": booking_id}, {"$set": update_data})
    
    # Create audit log
    await create_audit_log(
        action=f"CLIENT_{'ACCEPT' if action == 'accept' else 'DENY'}",
        entity_type="booking",
        entity_id=booking_id,
        user_id=client["id"] if client else "unknown",
        user_name=client["name"] if client else "Unknown Client",
        user_role=0,  # Client
        entity_name=f"{stock['symbol'] if stock else 'Unknown'} - {booking_number}",
        details={
            "action": action,
            "reason": reason if action == "deny" else None,
            "client_email": client.get("email") if client else None
        }
    )
    
    return {
        "message": message,
        "status": "accepted" if action == "accept" else "denied",
        "booking_number": booking_number
    }


# ============== Bulk Upload ==============

@router.post("/bookings/bulk-upload")
async def bulk_upload_bookings(file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    """Bulk upload bookings from CSV"""
    check_permission(current_user, "manage_bookings")
    
    try:
        content = await file.read()
        df = pd.read_csv(io.BytesIO(content))
        
        required_columns = ["client_id", "stock_id", "quantity", "booking_date"]
        if not all(col in df.columns for col in required_columns):
            raise HTTPException(status_code=400, detail=f"CSV must contain columns: {', '.join(required_columns)}")
        
        bookings_created = 0
        for _, row in df.iterrows():
            inventory = await db.inventory.find_one({"stock_id": str(row["stock_id"])}, {"_id": 0})
            buying_price = float(row.get("buying_price", inventory["weighted_avg_price"] if inventory else 0))
            
            booking_id = str(uuid.uuid4())
            booking_doc = {
                "id": booking_id,
                "client_id": str(row["client_id"]),
                "stock_id": str(row["stock_id"]),
                "quantity": int(row["quantity"]),
                "buying_price": buying_price,
                "selling_price": float(row["selling_price"]) if pd.notna(row.get("selling_price")) else None,
                "booking_date": str(row["booking_date"]),
                "status": str(row.get("status", "open")),
                "notes": str(row.get("notes", "")) if pd.notna(row.get("notes")) else None,
                "user_id": current_user["id"],
                "created_by": current_user["id"],
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            
            await db.bookings.insert_one(booking_doc)
            await update_inventory(str(row["stock_id"]))
            bookings_created += 1
        
        return {"message": f"Successfully uploaded {bookings_created} bookings"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error processing CSV: {str(e)}")

                "Booking Rejected",
                f"Your booking for '{stock['symbol'] if stock else 'N/A'}' has been rejected",
                {"booking_id": booking_id, "stock_symbol": stock['symbol'] if stock else None}
            )
    
    return {"message": f"Booking {'approved' if approve else 'rejected'} successfully"}


@router.put("/bookings/{booking_id}/approve-loss")
async def approve_loss_booking(
    booking_id: str,
    approve: bool = True,
    current_user: dict = Depends(get_current_user)
):
    """Approve or reject a loss booking (PE Desk only)"""
    user_role = current_user.get("role", 5)
    
    if user_role != 1:
        raise HTTPException(status_code=403, detail="Only PE Desk can approve loss bookings")
    
    booking = await db.bookings.find_one({"id": booking_id}, {"_id": 0})
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    if not booking.get("is_loss_booking", False):
        raise HTTPException(status_code=400, detail="This is not a loss booking")
    
    if booking.get("loss_approval_status") != "pending":
        raise HTTPException(status_code=400, detail="Loss booking already processed")
    
    update_data = {
        "loss_approval_status": "approved" if approve else "rejected",
        "loss_approved_by": current_user["id"],
        "loss_approved_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.bookings.update_one({"id": booking_id}, {"$set": update_data})
    
    action = "LOSS_BOOKING_APPROVE" if approve else "LOSS_BOOKING_REJECT"
    stock = await db.stocks.find_one({"id": booking["stock_id"]}, {"_id": 0})
    
    await create_audit_log(
        action=action,
        entity_type="booking",
        entity_id=booking_id,
        user_id=current_user["id"],
        user_name=current_user["name"],
        user_role=user_role,
        details={
            "stock_id": booking["stock_id"],
            "stock_symbol": stock['symbol'] if stock else "Unknown",
            "buying_price": booking["buying_price"],
            "selling_price": booking["selling_price"],
            "loss_amount": (booking["buying_price"] - booking["selling_price"]) * booking["quantity"]
        }
    )
    
    client = await db.clients.find_one({"id": booking["client_id"]}, {"_id": 0})
    creator = await db.users.find_one({"id": booking["created_by"]}, {"_id": 0})
    booking_number = booking.get("booking_number", booking_id[:8].upper())
    confirmation_token = booking.get("client_confirmation_token")
    
    if approve and booking.get("approval_status") == "approved":
        if client and client.get("email"):
            frontend_url = os.environ.get('FRONTEND_URL', 'https://privity-desk.preview.emergentagent.com')
            email_body = f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <h2 style="color: #10b981;">Booking Fully Approved - Please Confirm ✓</h2>
                <p>Dear {client['name']},</p>
                <p>Your loss booking order has been <strong style="color: #10b981;">FULLY APPROVED</strong>. Please confirm your acceptance to proceed.</p>
                
                <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
                    <tr style="background-color: #f3f4f6;">
                        <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Booking ID</strong></td>
                        <td style="padding: 10px; border: 1px solid #e5e7eb;">{booking_number}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Stock</strong></td>
                        <td style="padding: 10px; border: 1px solid #e5e7eb;">{stock['symbol'] if stock else 'N/A'}</td>
                    </tr>
                    <tr style="background-color: #f3f4f6;">
                        <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Quantity</strong></td>
                        <td style="padding: 10px; border: 1px solid #e5e7eb;">{booking['quantity']}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Landing Price</strong></td>
                        <td style="padding: 10px; border: 1px solid #e5e7eb;">₹{booking.get('buying_price', 0):,.2f}</td>
                    </tr>
                    <tr style="background-color: #fef3c7;">
                        <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Selling Price</strong></td>
                        <td style="padding: 10px; border: 1px solid #e5e7eb;">₹{booking.get('selling_price', 0):,.2f} <span style="color: #dc2626;">(Loss Transaction)</span></td>
                    </tr>
                </table>
                
                <div style="margin: 30px 0; text-align: center;">
                    <p style="margin-bottom: 20px; font-weight: bold;">Please confirm your booking:</p>
                    <a href="{frontend_url}/booking-confirm/{booking_id}/{confirmation_token}/accept" 
                       style="display: inline-block; background-color: #22c55e; color: white; padding: 12px 30px; text-decoration: none; border-radius: 6px; margin-right: 10px; font-weight: bold;">
                        ✓ ACCEPT BOOKING
                    </a>
                    <a href="{frontend_url}/booking-confirm/{booking_id}/{confirmation_token}/deny" 
                       style="display: inline-block; background-color: #ef4444; color: white; padding: 12px 30px; text-decoration: none; border-radius: 6px; font-weight: bold;">
                        ✗ DENY BOOKING
                    </a>
                </div>
                
                <p style="color: #6b7280; font-size: 14px;">This is a loss transaction booking. Please review carefully before confirming.</p>
                
                <p>Best regards,<br><strong>SMIFS Private Equity System</strong></p>
            </div>
            """
            await send_email(
                client["email"],
                f"Action Required: Confirm Loss Booking - {stock['symbol'] if stock else 'N/A'} | {booking_number}",
                email_body,
                cc_email=creator.get("email") if creator else None
            )
    
    if booking.get("created_by"):
        message = f"Loss booking {booking_number} for '{stock['symbol'] if stock else 'N/A'}' has been {'approved - client confirmation email sent' if approve else 'rejected'}"
        await create_notification(
            booking["created_by"],
            "loss_booking_approved" if approve else "loss_booking_rejected",
            "Loss Booking " + ("Approved" if approve else "Rejected"),
            message,
            {"booking_id": booking_id, "stock_symbol": stock['symbol'] if stock else None}
        )
    
    return {"message": f"Loss booking {'approved' if approve else 'rejected'} successfully"}


# ============== Payment Tracking Endpoints ==============

@router.post("/bookings/{booking_id}/payments")
async def add_payment_tranche(
    booking_id: str,
    payment: PaymentTrancheCreate,
    current_user: dict = Depends(get_current_user)
):
    """Add payment tranche to approved booking (PE Desk & Zonal Manager only)"""
    user_role = current_user.get("role", 5)
    if user_role not in [1, 2]:
        raise HTTPException(status_code=403, detail="Only PE Desk and Zonal Manager can record payments")
    
    booking = await db.bookings.find_one({"id": booking_id}, {"_id": 0})
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    if booking.get("approval_status") != "approved":
        raise HTTPException(status_code=400, detail="Can only add payments to approved bookings")
    
    payments = booking.get("payments", [])
    
    if len(payments) >= 4:
        raise HTTPException(status_code=400, detail="Maximum 4 payment tranches allowed")
    
    total_amount = (booking.get("selling_price") or 0) * booking.get("quantity", 0)
    current_paid = sum(p.get("amount", 0) for p in payments)
    remaining = total_amount - current_paid
    
    if payment.amount > remaining + 0.01:
        raise HTTPException(
            status_code=400, 
            detail=f"Payment amount ({payment.amount}) exceeds remaining balance ({remaining:.2f})"
        )
    
    new_tranche = {
        "tranche_number": len(payments) + 1,
        "amount": payment.amount,
        "payment_date": payment.payment_date,
        "recorded_by": current_user["id"],
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "notes": payment.notes
    }
    
    payments.append(new_tranche)
    new_total_paid = current_paid + payment.amount
    
    is_complete = abs(new_total_paid - total_amount) < 0.01
    payment_status = "completed" if is_complete else ("partial" if new_total_paid > 0 else "pending")
    
    update_data = {
        "payments": payments,
        "total_paid": new_total_paid,
        "payment_status": payment_status,
        "dp_transfer_ready": is_complete
    }
    
    if new_tranche["tranche_number"] == 1:
        if booking.get("client_confirmation_status") != "accepted":
            update_data["client_confirmation_status"] = "accepted"
            update_data["client_confirmed_at"] = datetime.now(timezone.utc).isoformat()
    
    if is_complete:
        update_data["payment_completed_at"] = payment.payment_date
    
    await db.bookings.update_one({"id": booking_id}, {"$set": update_data})
    
    await create_audit_log(
        action="PAYMENT_RECORDED",
        entity_type="booking",
        entity_id=booking_id,
        user_id=current_user["id"],
        user_name=current_user["name"],
        user_role=user_role,
        details={
            "tranche_number": new_tranche["tranche_number"],
            "amount": payment.amount,
            "total_paid": new_total_paid,
            "payment_status": payment_status,
            "auto_client_accepted": new_tranche["tranche_number"] == 1 and booking.get("client_confirmation_status") != "accepted"
        }
    )
    
    client = await db.clients.find_one({"id": booking["client_id"]}, {"_id": 0})
    stock = await db.stocks.find_one({"id": booking["stock_id"]}, {"_id": 0})
    booking_number = booking.get("booking_number", booking_id[:8].upper())
    
    if new_tranche["tranche_number"] == 1 and booking.get("client_confirmation_status") != "accepted":
        await notify_roles(
            [1],
            "client_auto_accepted",
            "Client Auto-Accepted via Payment",
            f"Booking {booking_number} automatically marked as client accepted (first payment recorded)",
            {"booking_id": booking_id, "booking_number": booking_number}
        )
    
    if booking.get("created_by"):
        await create_notification(
            booking["created_by"],
            "payment_received",
            "Payment Received",
            f"Payment of ₹{payment.amount:,.2f} recorded for {booking_number}. Total paid: ₹{new_total_paid:,.2f}",
            {"booking_id": booking_id, "booking_number": booking_number, "amount": payment.amount}
        )
    
    if is_complete:
        await notify_roles(
            [1, 2],
            "payment_complete",
            "Payment Complete - Ready for DP Transfer",
            f"Booking {booking_number} ({stock['symbol'] if stock else 'Unknown'}) is fully paid and ready for DP transfer to {client['name'] if client else 'Unknown'}",
            {"booking_id": booking_id, "booking_number": booking_number, "client_name": client["name"] if client else None}
        )
        
        if client and client.get("email"):
            await send_email(
                client["email"],
                f"Payment Complete - Booking {booking_number}",
                f"""
                <p>Dear {client['name']},</p>
                <p>We are pleased to confirm that full payment has been received for your booking:</p>
                <ul>
                    <li><strong>Booking ID:</strong> {booking_number}</li>
                    <li><strong>Stock:</strong> {stock['symbol'] if stock else 'Unknown'}</li>
                    <li><strong>Quantity:</strong> {booking.get('quantity')}</li>
                    <li><strong>Total Amount:</strong> ₹{total_amount:,.2f}</li>
                </ul>
                <p>Your booking is now ready for DP transfer.</p>
                """
            )
    
    return {
        "message": f"Payment tranche {new_tranche['tranche_number']} recorded",
        "total_paid": new_total_paid,
        "remaining": total_amount - new_total_paid,
        "payment_status": payment_status,
        "dp_transfer_ready": is_complete
    }


@router.get("/bookings/{booking_id}/payments")
async def get_booking_payments(
    booking_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get payment details for a booking"""
    check_permission(current_user, "manage_bookings")
    
    booking = await db.bookings.find_one({"id": booking_id}, {"_id": 0})
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    total_amount = (booking.get("selling_price") or 0) * booking.get("quantity", 0)
    total_paid = booking.get("total_paid", 0)
    
    return {
        "booking_id": booking_id,
        "total_amount": total_amount,
        "total_paid": total_paid,
        "remaining": total_amount - total_paid,
        "payment_status": booking.get("payment_status", "pending"),
        "payments": booking.get("payments", []),
        "dp_transfer_ready": booking.get("dp_transfer_ready", False),
        "payment_completed_at": booking.get("payment_completed_at")
    }


@router.delete("/bookings/{booking_id}/payments/{tranche_number}")
async def delete_payment_tranche(
    booking_id: str,
    tranche_number: int,
    current_user: dict = Depends(get_current_user)
):
    """Delete a payment tranche (PE Desk only)"""
    if current_user.get("role") != 1:
        raise HTTPException(status_code=403, detail="Only PE Desk can delete payment tranches")
    
    booking = await db.bookings.find_one({"id": booking_id}, {"_id": 0})
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    payments = booking.get("payments", [])
    payments = [p for p in payments if p.get("tranche_number") != tranche_number]
    
    total_paid = sum(p.get("amount", 0) for p in payments)
    total_amount = (booking.get("selling_price") or 0) * booking.get("quantity", 0)
    is_complete = abs(total_paid - total_amount) < 0.01
    payment_status = "completed" if is_complete else ("partial" if total_paid > 0 else "pending")
    
    for i, p in enumerate(payments):
        p["tranche_number"] = i + 1
    
    await db.bookings.update_one(
        {"id": booking_id},
        {"$set": {
            "payments": payments,
            "total_paid": total_paid,
            "payment_status": payment_status,
            "dp_transfer_ready": is_complete,
            "payment_completed_at": None if not is_complete else booking.get("payment_completed_at")
        }}
    )
    
    return {"message": "Payment tranche deleted"}
