"""
Bookings Router with High-Concurrency Support

This router handles all booking operations with proper locking and atomic updates
to prevent race conditions during simultaneous booking requests.
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from datetime import datetime, timezone
import uuid
import os

from database import db
from config import is_pe_level, is_pe_desk_only, ROLES
from models import BookingCreate, Booking, BookingWithDetails
from utils.auth import get_current_user, check_permission
from services.notification_service import notify_roles, create_notification
from services.audit_service import create_audit_log
from services.email_service import send_templated_email
from services.inventory_service import (
    update_inventory,
    check_and_reserve_inventory,
    release_inventory_reservation,
    check_stock_availability
)

router = APIRouter(tags=["Bookings"])

# Lock for booking number generation
import asyncio
_booking_number_lock = asyncio.Lock()


async def generate_booking_number() -> str:
    """Generate a unique booking number in format BK-YYYY-NNNNN using atomic counter."""
    year = datetime.now().year
    
    async with _booking_number_lock:
        # Use atomic findAndModify to get next sequence
        counter = await db.counters.find_one_and_update(
            {"_id": f"booking_{year}"},
            {"$inc": {"seq": 1}},
            upsert=True,
            return_document=True
        )
        
        seq_num = counter.get("seq", 1)
        return f"BK-{year}-{seq_num:05d}"


def get_client_emails(client: dict) -> list:
    """Get all email addresses for a client"""
    emails = []
    if client.get("email"):
        emails.append(client["email"])
    if client.get("secondary_email"):
        emails.append(client["secondary_email"])
    if client.get("tertiary_email"):
        emails.append(client["tertiary_email"])
    return emails


@router.get("/bookings/check-client-rp-conflict/{client_id}")
async def check_client_rp_conflict(client_id: str, current_user: dict = Depends(get_current_user)):
    """
    Check if a client is also registered as a Referral Partner.
    Returns conflict info if found, null otherwise.
    STRICT RULE: A Client cannot be an RP and vice versa.
    """
    client = await db.clients.find_one({"id": client_id}, {"_id": 0, "pan_number": 1, "name": 1, "otc_ucc": 1})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # Check if client's PAN matches any RP
    client_pan = client.get("pan_number", "").upper()
    matching_rp = await db.referral_partners.find_one(
        {"pan_number": client_pan},
        {"_id": 0, "rp_code": 1, "name": 1, "id": 1}
    )
    
    if matching_rp:
        return {
            "has_conflict": True,
            "client_name": client.get("name"),
            "client_ucc": client.get("otc_ucc"),
            "rp_code": matching_rp.get("rp_code"),
            "rp_name": matching_rp.get("name"),
            "rp_id": matching_rp.get("id"),
            "message": f"This client ({client.get('name')}) is also registered as RP {matching_rp.get('rp_code')}. RP revenue share will be automatically set to 0%."
        }
    
    return {"has_conflict": False}


@router.post("/bookings", response_model=Booking)
async def create_booking(booking_data: BookingCreate, current_user: dict = Depends(get_current_user)):
    """
    Create a new booking with high-concurrency safety.
    
    This endpoint uses atomic inventory operations to prevent race conditions
    when multiple users try to book the same stock simultaneously.
    """
    user_role = current_user.get("role", 5)
    
    # Permission check
    if user_role == 4:  # Employee
        check_permission(current_user, "create_bookings")
    else:
        check_permission(current_user, "manage_bookings")
    
    # Verify client exists and is active
    client = await db.clients.find_one({"id": booking_data.client_id}, {"_id": 0})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # Check client approval status
    if client.get("approval_status") != "approved":
        raise HTTPException(
            status_code=400, 
            detail=f"Client must be approved by PE Desk before creating bookings. Current status: {client.get('approval_status', 'pending')}"
        )
    
    # Check if client is active
    if not client.get("is_active", True):
        raise HTTPException(status_code=400, detail="Client is inactive and cannot be used for bookings")
    
    # Check if client is suspended
    if client.get("is_suspended"):
        raise HTTPException(
            status_code=400, 
            detail=f"Client is suspended and cannot be used for bookings. Reason: {client.get('suspension_reason', 'No reason provided')}"
        )
    
    # Employee can only book for their own clients
    if user_role == 4:
        if client.get("mapped_employee_id") != current_user["id"] and client.get("created_by") != current_user["id"]:
            raise HTTPException(status_code=403, detail="You can only create bookings for your own clients")
    
    # Verify stock exists
    stock = await db.stocks.find_one({"id": booking_data.stock_id}, {"_id": 0})
    if not stock:
        raise HTTPException(status_code=404, detail="Stock not found")
    
    # Check if stock is blocked
    if stock.get("exchange") == "Blocked IPO/RTA":
        raise HTTPException(
            status_code=400, 
            detail="This stock is blocked (IPO/RTA) and not available for booking"
        )
    
    # HIGH-CONCURRENCY: Atomic inventory check
    is_available, available_qty, weighted_avg = await check_stock_availability(
        booking_data.stock_id, 
        booking_data.quantity
    )
    
    if not is_available:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient inventory. Available: {available_qty}, Requested: {booking_data.quantity}"
        )
    
    # Validate selling price
    if booking_data.selling_price is None or booking_data.selling_price <= 0:
        raise HTTPException(
            status_code=400,
            detail="Selling price is required and must be greater than 0"
        )
    
    # Determine buying price
    if user_role == 4:  # Employee must use weighted average
        buying_price = weighted_avg
    else:
        buying_price = booking_data.buying_price if booking_data.buying_price else weighted_avg
    
    if buying_price is None or buying_price <= 0:
        raise HTTPException(
            status_code=400,
            detail="Landing price is required and must be greater than 0"
        )
    
    # Validate RP revenue share percentage cap at 30%
    if booking_data.rp_revenue_share_percent is not None:
        if booking_data.rp_revenue_share_percent > 30:
            raise HTTPException(
                status_code=400,
                detail="Referral Partner revenue share cannot exceed 30%"
            )
        if booking_data.rp_revenue_share_percent < 0:
            raise HTTPException(
                status_code=400,
                detail="Referral Partner revenue share cannot be negative"
            )
    
    # STRICT RULE: A Client cannot be an RP - Auto-zero RP share if client's PAN matches any RP
    rp_share_auto_zeroed = False
    if booking_data.referral_partner_id and booking_data.rp_revenue_share_percent:
        # Check if client's PAN matches any RP's PAN
        client_pan = client.get("pan_number", "").upper()
        matching_rp = await db.referral_partners.find_one(
            {"pan_number": client_pan},
            {"_id": 0, "rp_code": 1, "name": 1}
        )
        if matching_rp:
            # Client is also an RP - auto-zero the RP revenue share
            booking_data.rp_revenue_share_percent = 0
            booking_data.referral_partner_id = None  # Remove RP assignment
            rp_share_auto_zeroed = True
    
    # Get RP details if specified
    rp_code = None
    rp_name = None
    if booking_data.referral_partner_id:
        rp = await db.referral_partners.find_one({"id": booking_data.referral_partner_id}, {"_id": 0})
        if rp:
            # Additional check: Verify the selected RP is not the same person as the client
            rp_pan = rp.get("pan_number", "").upper()
            client_pan = client.get("pan_number", "").upper()
            if rp_pan == client_pan:
                # Same person - zero out RP share
                booking_data.rp_revenue_share_percent = 0
                booking_data.referral_partner_id = None
                rp_share_auto_zeroed = True
            else:
                rp_code = rp.get("rp_code")
                rp_name = rp.get("name")
        else:
            raise HTTPException(status_code=404, detail="Referral Partner not found")
    
    # Generate booking identifiers
    booking_id = str(uuid.uuid4())
    booking_number = await generate_booking_number()
    confirmation_token = str(uuid.uuid4())
    
    # Check if loss booking
    is_loss_booking = booking_data.selling_price < buying_price
    loss_approval_status = "pending" if is_loss_booking else "not_required"
    
    # Create booking document
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
        "approval_status": "pending",  # Requires PE approval
        "approved_by": None,
        "approved_at": None,
        "booking_type": booking_data.booking_type,
        "insider_form_uploaded": booking_data.insider_form_uploaded,
        "insider_form_path": None,
        # Referral Partner fields (may be zeroed if client=RP)
        "referral_partner_id": booking_data.referral_partner_id if not rp_share_auto_zeroed else None,
        "rp_code": rp_code if not rp_share_auto_zeroed else None,
        "rp_name": rp_name if not rp_share_auto_zeroed else None,
        "rp_revenue_share_percent": booking_data.rp_revenue_share_percent if not rp_share_auto_zeroed else 0,
        "rp_share_auto_zeroed": rp_share_auto_zeroed,  # Flag for audit trail
        # Employee Revenue Share - calculated based on RP allocation
        "base_employee_share_percent": 100.0,  # Full share before RP deduction
        "employee_revenue_share_percent": 100.0 if rp_share_auto_zeroed else 100.0 - (booking_data.rp_revenue_share_percent or 0),
        "employee_commission_amount": None,  # Calculated when stock transfer confirmed
        "employee_commission_status": "pending",
        # Client confirmation
        "client_confirmation_status": "pending",
        "client_confirmation_token": confirmation_token,
        "client_confirmed_at": None,
        "client_denial_reason": None,
        "is_loss_booking": is_loss_booking,
        "loss_approval_status": loss_approval_status,
        "loss_approved_by": None,
        "loss_approved_at": None,
        "notes": f"[AUTO: RP share zeroed - Client is also an RP] {booking_data.notes or ''}" if rp_share_auto_zeroed else booking_data.notes,
        "user_id": current_user["id"],
        "created_by": current_user["id"],
        "created_by_name": current_user["name"],
        "created_by_role": user_role,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    # Insert booking
    await db.bookings.insert_one(booking_doc)
    
    # Create audit log
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
            "selling_price": booking_data.selling_price,
            "rp_share": booking_data.rp_revenue_share_percent,
            "employee_share": 100.0 - (booking_data.rp_revenue_share_percent or 0)
        }
    )
    
    # Send email notification
    if client.get("email"):
        await send_templated_email(
            "booking_created",
            client["email"],
            {
                "client_name": client["name"],
                "booking_number": booking_number,
                "stock_symbol": stock["symbol"],
                "stock_name": stock["name"],
                "quantity": booking_data.quantity
            },
            cc_email=current_user.get("email")
        )
    
    # Real-time notification to PE Desk
    await notify_roles(
        [1],
        "booking_pending",
        "New Booking Pending Approval",
        f"Booking {booking_number} for '{client['name']}' - {stock['symbol']} x {booking_data.quantity} awaiting PE Desk approval",
        {"booking_id": booking_id, "booking_number": booking_number, "client_name": client["name"], "stock_symbol": stock["symbol"]}
    )
    
    return Booking(**{k: v for k, v in booking_doc.items() if k not in ["user_id", "created_by_name"]})


@router.put("/bookings/{booking_id}/approve")
async def approve_booking(
    booking_id: str,
    approve: bool = True,
    current_user: dict = Depends(get_current_user)
):
    """
    Approve or reject a booking with atomic inventory update.
    
    When approved, inventory is atomically updated to prevent race conditions.
    """
    user_role = current_user.get("role", 6)
    
    if not is_pe_level(user_role):
        raise HTTPException(status_code=403, detail="Only PE Desk or PE Manager can approve bookings")
    
    booking = await db.bookings.find_one({"id": booking_id}, {"_id": 0})
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    if booking.get("approval_status") != "pending":
        raise HTTPException(status_code=400, detail="Booking already processed")
    
    if approve:
        # HIGH-CONCURRENCY: Atomic inventory reservation
        success, message, inventory = await check_and_reserve_inventory(
            booking["stock_id"],
            booking["quantity"],
            booking_id
        )
        
        if not success:
            raise HTTPException(status_code=400, detail=message)
    
    # Update booking status
    update_data = {
        "approval_status": "approved" if approve else "rejected",
        "approved_by": current_user["id"],
        "approved_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.bookings.update_one({"id": booking_id}, {"$set": update_data})
    
    # Get related entities for notifications
    client = await db.clients.find_one({"id": booking["client_id"]}, {"_id": 0})
    stock = await db.stocks.find_one({"id": booking["stock_id"]}, {"_id": 0})
    creator = await db.users.find_one({"id": booking["created_by"]}, {"_id": 0})
    booking_number = booking.get("booking_number", booking_id[:8].upper())
    
    if approve:
        # Create audit log
        await create_audit_log(
            action="BOOKING_APPROVE",
            entity_type="booking",
            entity_id=booking_id,
            user_id=current_user["id"],
            user_name=current_user["name"],
            user_role=user_role,
            details={"stock_id": booking["stock_id"], "quantity": booking["quantity"]}
        )
        
        # Send confirmation email to client
        is_loss_pending = booking.get("is_loss_booking") and booking.get("loss_approval_status") == "pending"
        client_emails = get_client_emails(client) if client else []
        primary_email = client_emails[0] if client_emails else None
        additional_emails = client_emails[1:] if len(client_emails) > 1 else None
        
        if client and primary_email:
            confirmation_token = booking.get("client_confirmation_token")
            frontend_url = os.environ.get('FRONTEND_URL', 'https://privity-desk.preview.emergentagent.com')
            
            if is_loss_pending:
                await send_templated_email(
                    "booking_pending_loss_review",
                    primary_email,
                    {
                        "client_name": client["name"],
                        "booking_number": booking_number,
                        "stock_symbol": stock["symbol"] if stock else "N/A"
                    },
                    cc_email=creator.get("email") if creator else None,
                    additional_emails=additional_emails
                )
            else:
                await send_templated_email(
                    "booking_confirmation_request",
                    primary_email,
                    {
                        "client_name": client["name"],
                        "booking_number": booking_number,
                        "otc_ucc": client.get("otc_ucc", "N/A"),
                        "stock_symbol": stock["symbol"] if stock else "N/A",
                        "stock_name": stock["name"] if stock else "",
                        "quantity": booking["quantity"],
                        "buying_price": f"{booking.get('buying_price', 0):,.2f}",
                        "total_value": f"{(booking.get('buying_price', 0) * booking.get('quantity', 0)):,.2f}",
                        "approved_by": current_user["name"],
                        "accept_url": f"{frontend_url}/booking-confirm/{booking_id}/{confirmation_token}/accept",
                        "deny_url": f"{frontend_url}/booking-confirm/{booking_id}/{confirmation_token}/deny"
                    },
                    cc_email=creator.get("email") if creator else None,
                    additional_emails=additional_emails
                )
        
        # Notify booking creator
        if booking.get("created_by"):
            await create_notification(
                booking["created_by"],
                "booking_approved",
                "Booking Approved - Awaiting Client Confirmation",
                f"Your booking {booking_number} for '{stock['symbol'] if stock else 'N/A'}' has been approved.",
                {"booking_id": booking_id, "stock_symbol": stock['symbol'] if stock else None}
            )
    else:
        # Rejection - create audit log
        await create_audit_log(
            action="BOOKING_REJECT",
            entity_type="booking",
            entity_id=booking_id,
            user_id=current_user["id"],
            user_name=current_user["name"],
            user_role=user_role,
            details={"stock_id": booking["stock_id"], "quantity": booking["quantity"]}
        )
        
        # Notify booking creator
        if booking.get("created_by"):
            await create_notification(
                booking["created_by"],
                "booking_rejected",
                "Booking Rejected",
                f"Your booking for '{stock['symbol'] if stock else 'N/A'}' has been rejected",
                {"booking_id": booking_id, "stock_symbol": stock['symbol'] if stock else None}
            )
    
    return {"message": f"Booking {'approved' if approve else 'rejected'} successfully"}


@router.put("/bookings/{booking_id}/void")
async def void_booking(
    booking_id: str,
    reason: str = Query(..., description="Reason for voiding the booking"),
    current_user: dict = Depends(get_current_user)
):
    """
    Void a booking with atomic inventory release.
    
    This releases the blocked inventory back to available.
    If the booking had payments, creates a refund request.
    """
    user_role = current_user.get("role", 6)
    
    if not is_pe_level(user_role):
        raise HTTPException(status_code=403, detail="Only PE Desk or PE Manager can void bookings")
    
    booking = await db.bookings.find_one({"id": booking_id}, {"_id": 0})
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    if booking.get("is_voided"):
        raise HTTPException(status_code=400, detail="Booking is already voided")
    
    if booking.get("stock_transferred"):
        raise HTTPException(status_code=400, detail="Cannot void - stock has already been transferred")
    
    # Release inventory if booking was approved
    if booking.get("approval_status") == "approved":
        success, message = await release_inventory_reservation(
            booking["stock_id"],
            booking["quantity"],
            booking_id
        )
        if not success:
            # Log warning but don't fail - manual reconciliation may be needed
            import logging
            logging.warning(f"Failed to release inventory for voided booking {booking_id}: {message}")
    
    # Update booking
    update_data = {
        "is_voided": True,
        "void_reason": reason,
        "voided_by": current_user["id"],
        "voided_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.bookings.update_one({"id": booking_id}, {"$set": update_data})
    
    # Create refund request if there are payments
    payments = booking.get("payments", [])
    total_paid = sum(p.get("amount", 0) for p in payments)
    
    refund_request_id = None
    if total_paid > 0:
        client = await db.clients.find_one({"id": booking["client_id"]}, {"_id": 0})
        stock = await db.stocks.find_one({"id": booking["stock_id"]}, {"_id": 0})
        
        # Get client's primary bank account for refund
        bank_details = {}
        if client and client.get("bank_accounts") and len(client["bank_accounts"]) > 0:
            primary_bank = client["bank_accounts"][0]
            bank_details = {
                "bank_name": primary_bank.get("bank_name", ""),
                "account_number": primary_bank.get("account_number", ""),
                "ifsc_code": primary_bank.get("ifsc_code", ""),
                "account_holder_name": primary_bank.get("account_holder_name", ""),
                "branch": primary_bank.get("branch", "")
            }
        
        refund_request_id = str(uuid.uuid4())
        refund_request = {
            "id": refund_request_id,
            "booking_id": booking_id,
            "booking_number": booking.get("booking_number", ""),
            "client_id": booking["client_id"],
            "client_name": client["name"] if client else "Unknown",
            "client_email": client.get("email", "") if client else "",
            "stock_id": booking["stock_id"],
            "stock_symbol": stock["symbol"] if stock else "Unknown",
            "quantity": booking["quantity"],
            "refund_amount": total_paid,
            "bank_details": bank_details,
            "void_reason": reason,
            "voided_by": current_user["id"],
            "voided_by_name": current_user["name"],
            "status": "pending",
            "reference_number": None,
            "notes": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": None,
            "updated_by": None
        }
        
        await db.refund_requests.insert_one(refund_request)
        
        # Send refund notification email
        if client and client.get("email"):
            await send_templated_email(
                "refund_request_created",
                client["email"],
                {
                    "client_name": client["name"],
                    "booking_number": booking.get("booking_number", ""),
                    "stock_symbol": stock["symbol"] if stock else "Unknown",
                    "refund_amount": f"{total_paid:,.2f}",
                    "void_reason": reason
                }
            )
    
    # Create audit log
    await create_audit_log(
        action="BOOKING_VOID",
        entity_type="booking",
        entity_id=booking_id,
        user_id=current_user["id"],
        user_name=current_user["name"],
        user_role=user_role,
        details={
            "reason": reason,
            "refund_amount": total_paid if total_paid > 0 else None,
            "refund_request_id": refund_request_id
        }
    )
    
    return {
        "message": "Booking voided successfully",
        "refund_request_created": total_paid > 0,
        "refund_amount": total_paid if total_paid > 0 else None,
        "refund_request_id": refund_request_id
    }


@router.get("/bookings", response_model=List[BookingWithDetails])
async def get_bookings(
    status: Optional[str] = None,
    approval_status: Optional[str] = None,
    client_id: Optional[str] = None,
    stock_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get all bookings with optional filters."""
    query = {}
    user_role = current_user.get("role", 5)
    
    # Employee can only see their own bookings
    if user_role == 4:
        query["created_by"] = current_user["id"]
    
    # Apply filters
    if status:
        query["status"] = status
    if approval_status:
        query["approval_status"] = approval_status
    if client_id:
        query["client_id"] = client_id
    if stock_id:
        query["stock_id"] = stock_id
    
    bookings = await db.bookings.find(query, {"_id": 0}).sort("created_at", -1).to_list(10000)
    
    # Enrich with client and stock details
    result = []
    for booking in bookings:
        client = await db.clients.find_one({"id": booking["client_id"]}, {"_id": 0})
        stock = await db.stocks.find_one({"id": booking["stock_id"]}, {"_id": 0})
        
        # Calculate total amount
        quantity = booking.get("quantity", 0)
        selling_price = booking.get("selling_price", 0)
        buying_price = booking.get("buying_price", 0)
        total_amount = quantity * selling_price
        
        # Calculate payment info
        payments = booking.get("payments", [])
        total_paid = sum(p.get("amount", 0) for p in payments)
        
        booking_with_details = {
            **booking,
            "client_name": client["name"] if client else "Unknown",
            "client_email": client.get("email") if client else None,
            "stock_symbol": stock["symbol"] if stock else "Unknown",
            "stock_name": stock["name"] if stock else "Unknown",
            "total_amount": total_amount,
            "profit_loss": (selling_price - buying_price) * quantity,
            "total_paid": total_paid,
            "payment_status": "paid" if total_paid >= total_amount else ("partial" if total_paid > 0 else "pending")
        }
        result.append(BookingWithDetails(**booking_with_details))
    
    return result


@router.get("/bookings/{booking_id}", response_model=BookingWithDetails)
async def get_booking(booking_id: str, current_user: dict = Depends(get_current_user)):
    """Get a specific booking by ID."""
    booking = await db.bookings.find_one({"id": booking_id}, {"_id": 0})
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    # Employee can only view their own bookings
    user_role = current_user.get("role", 5)
    if user_role == 4 and booking.get("created_by") != current_user["id"]:
        raise HTTPException(status_code=403, detail="You can only view your own bookings")
    
    client = await db.clients.find_one({"id": booking["client_id"]}, {"_id": 0})
    stock = await db.stocks.find_one({"id": booking["stock_id"]}, {"_id": 0})
    
    quantity = booking.get("quantity", 0)
    selling_price = booking.get("selling_price", 0)
    buying_price = booking.get("buying_price", 0)
    total_amount = quantity * selling_price
    
    payments = booking.get("payments", [])
    total_paid = sum(p.get("amount", 0) for p in payments)
    
    return BookingWithDetails(**{
        **booking,
        "client_name": client["name"] if client else "Unknown",
        "client_email": client.get("email") if client else None,
        "stock_symbol": stock["symbol"] if stock else "Unknown",
        "stock_name": stock["name"] if stock else "Unknown",
        "total_amount": total_amount,
        "profit_loss": (selling_price - buying_price) * quantity,
        "total_paid": total_paid,
        "payment_status": "paid" if total_paid >= total_amount else ("partial" if total_paid > 0 else "pending")
    })
