"""
Bookings Router with High-Concurrency Support

This router handles all booking operations with proper locking and atomic updates
to prevent race conditions during simultaneous booking requests.
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import StreamingResponse
from typing import List, Optional
from datetime import datetime, timezone
import uuid
import os
import io

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

from database import db
from config import is_pe_level, is_pe_desk_only, ROLES
from models import BookingCreate, Booking, BookingWithDetails
from utils.auth import get_current_user, check_permission
from services.notification_service import notify_roles, create_notification
from services.audit_service import create_audit_log
from services.email_service import send_templated_email, send_payment_request_email
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
    is_business_partner = user_role == 8 or current_user.get("is_bp", False)
    bp_info = None
    
    # Permission check - Business Partners can create bookings
    if user_role == 4 or is_business_partner:  # Employee or Business Partner
        check_permission(current_user, "create_bookings")
    else:
        check_permission(current_user, "manage_bookings")
    
    # If Business Partner, get their BP profile for revenue share
    if is_business_partner:
        bp_id = current_user.get("user_id") or current_user.get("id")
        bp_info = await db.business_partners.find_one({"id": bp_id}, {"_id": 0})
        if not bp_info:
            raise HTTPException(status_code=404, detail="Business Partner profile not found")
        if not bp_info.get("is_active", True):
            raise HTTPException(status_code=403, detail="Your Business Partner account is inactive")
        # BPs cannot select RPs - clear any RP data
        booking_data.referral_partner_id = None
        booking_data.rp_revenue_share_percent = None
    
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
    
    # Determine if BP booking - BP revenue share takes precedence
    is_bp_booking = is_business_partner and bp_info is not None
    bp_revenue_share = bp_info.get("revenue_share_percent", 0) if bp_info else 0
    
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
        # Business Partner fields (takes precedence over RP)
        "business_partner_id": bp_info.get("id") if is_bp_booking else None,
        "bp_name": bp_info.get("name") if is_bp_booking else None,
        "bp_revenue_share_percent": bp_revenue_share if is_bp_booking else None,
        "is_bp_booking": is_bp_booking,
        # Referral Partner fields (may be zeroed if client=RP or if BP booking)
        "referral_partner_id": None if is_bp_booking else (booking_data.referral_partner_id if not rp_share_auto_zeroed else None),
        "rp_code": None if is_bp_booking else (rp_code if not rp_share_auto_zeroed else None),
        "rp_name": None if is_bp_booking else (rp_name if not rp_share_auto_zeroed else None),
        "rp_revenue_share_percent": 0 if is_bp_booking else (booking_data.rp_revenue_share_percent if not rp_share_auto_zeroed else 0),
        "rp_share_auto_zeroed": rp_share_auto_zeroed,  # Flag for audit trail
        # Employee Revenue Share - calculated based on RP/BP allocation
        "base_employee_share_percent": 100.0,  # Full share before deduction
        "employee_revenue_share_percent": 100.0 - bp_revenue_share if is_bp_booking else (100.0 if rp_share_auto_zeroed else 100.0 - (booking_data.rp_revenue_share_percent or 0)),
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
        "notes": f"[BP Booking: {bp_info.get('name')} @ {bp_revenue_share}%] {booking_data.notes or ''}" if is_bp_booking else (f"[AUTO: RP share zeroed - Client is also an RP] {booking_data.notes or ''}" if rp_share_auto_zeroed else booking_data.notes),
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
            frontend_url = os.environ.get('FRONTEND_URL', 'https://privity-booking-2.preview.emergentagent.com')
            
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
            
            # Send payment request email with bank details and company documents
            company_master = await db.company_master.find_one({"_id": "company_settings"}, {"_id": 0})
            if company_master:
                await send_payment_request_email(
                    booking_id=booking_id,
                    client=client,
                    stock=stock,
                    booking=booking,
                    company_master=company_master,
                    approved_by=current_user["name"],
                    cc_email=creator.get("email") if creator else None
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


# ============== DP Transfer Endpoints (Client Stock Transfers) ==============
# NOTE: These routes MUST be defined before /bookings/{booking_id} to avoid path conflicts

@router.get("/bookings/dp-ready")
async def get_dp_ready_bookings(current_user: dict = Depends(get_current_user)):
    """Get all bookings with DP ready status (fully paid, ready to transfer)"""
    user_role = current_user.get("role", 6)
    
    if not is_pe_level(user_role):
        raise HTTPException(status_code=403, detail="Only PE level can view DP ready bookings")
    
    # Get bookings with dp_status = "ready"
    bookings_list = await db.bookings.find(
        {"dp_status": "ready", "approval_status": "approved"},
        {"_id": 0}
    ).sort("dp_ready_at", -1).to_list(1000)
    
    # Enrich with client and stock details
    for booking in bookings_list:
        client = await db.clients.find_one(
            {"id": booking.get("client_id")},
            {"_id": 0, "name": 1, "email": 1, "otc_ucc": 1, "pan_number": 1, "dp_id": 1, "depository": 1}
        )
        if client:
            booking["client_name"] = client.get("name")
            booking["client_email"] = client.get("email")
            booking["client_otc_ucc"] = client.get("otc_ucc")
            booking["client_pan"] = client.get("pan_number")
            booking["client_dp_id"] = client.get("dp_id")
            booking["client_depository"] = client.get("depository")
        
        stock = await db.stocks.find_one(
            {"id": booking.get("stock_id")},
            {"_id": 0, "name": 1, "symbol": 1}
        )
        if stock:
            booking["stock_name"] = stock.get("name")
            booking["stock_symbol"] = stock.get("symbol")
        
        # Calculate total amount
        booking["total_amount"] = (booking.get("selling_price") or 0) * booking.get("quantity", 0)
    
    return bookings_list


@router.get("/bookings/dp-transferred")
async def get_dp_transferred_bookings(current_user: dict = Depends(get_current_user)):
    """Get all bookings where stock has been transferred"""
    user_role = current_user.get("role", 6)
    
    if not is_pe_level(user_role):
        raise HTTPException(status_code=403, detail="Only PE level can view transferred bookings")
    
    # Get bookings with dp_status = "transferred"
    bookings_list = await db.bookings.find(
        {"dp_status": "transferred"},
        {"_id": 0}
    ).sort("dp_transferred_at", -1).to_list(1000)
    
    # Enrich with client and stock details
    for booking in bookings_list:
        client = await db.clients.find_one(
            {"id": booking.get("client_id")},
            {"_id": 0, "name": 1, "email": 1, "otc_ucc": 1, "pan_number": 1, "dp_id": 1, "depository": 1}
        )
        if client:
            booking["client_name"] = client.get("name")
            booking["client_email"] = client.get("email")
            booking["client_otc_ucc"] = client.get("otc_ucc")
            booking["client_pan"] = client.get("pan_number")
            booking["client_dp_id"] = client.get("dp_id")
            booking["client_depository"] = client.get("depository")
        
        stock = await db.stocks.find_one(
            {"id": booking.get("stock_id")},
            {"_id": 0, "name": 1, "symbol": 1}
        )
        if stock:
            booking["stock_name"] = stock.get("name")
            booking["stock_symbol"] = stock.get("symbol")
        
        booking["total_amount"] = (booking.get("selling_price") or 0) * booking.get("quantity", 0)
    
    return bookings_list


@router.get("/bookings/dp-export")
async def export_dp_transfer_excel(
    status: str = "all",  # "ready", "transferred", or "all"
    current_user: dict = Depends(get_current_user)
):
    """Export DP transfer data to Excel"""
    user_role = current_user.get("role", 6)
    
    if not is_pe_level(user_role):
        raise HTTPException(status_code=403, detail="Only PE level can export DP data")
    
    # Build query based on status
    query = {"approval_status": "approved"}
    if status == "ready":
        query["dp_status"] = "ready"
    elif status == "transferred":
        query["dp_status"] = "transferred"
    else:
        query["dp_status"] = {"$in": ["ready", "transferred"]}
    
    # Get bookings
    bookings_data = await db.bookings.find(query, {"_id": 0}).to_list(10000)
    
    # Create workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "DP Transfer"
    
    # Styles
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="3B82F6", end_color="3B82F6", fill_type="solid")
    header_alignment = Alignment(horizontal="center", vertical="center")
    thin_border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )
    
    # Headers
    headers = [
        "Booking #", "Client Name", "Client DP ID", "Client PAN",
        "Stock Symbol", "Stock Name", "ISIN", "Quantity",
        "Amount", "Status", "DP Type", "Transfer Date"
    ]
    
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment
        cell.border = thin_border
    
    # Data rows
    row = 2
    for booking in bookings_data:
        # Get client details
        client = await db.clients.find_one(
            {"id": booking.get("client_id")},
            {"_id": 0, "name": 1, "dp_id": 1, "pan": 1, "otc_ucc": 1}
        )
        
        # Get stock details
        stock = await db.stocks.find_one(
            {"id": booking.get("stock_id")},
            {"_id": 0, "name": 1, "symbol": 1, "isin": 1}
        )
        
        # Calculate total amount
        total_amount = (booking.get("selling_price") or 0) * booking.get("quantity", 0)
        
        # Get DP ID - use otc_ucc or dp_id
        dp_id = ""
        if client:
            dp_id = client.get("otc_ucc") or client.get("dp_id") or ""
        
        data = [
            booking.get("booking_number", ""),
            client.get("name", "") if client else "",
            dp_id,
            client.get("pan", "") if client else "",
            stock.get("symbol", "") if stock else "",
            stock.get("name", "") if stock else "",
            stock.get("isin", "") if stock else "",
            booking.get("quantity", 0),
            total_amount,
            "READY" if booking.get("dp_status") == "ready" else "TRANSFERRED",
            booking.get("dp_type", ""),
            booking.get("dp_transferred_at", "")[:10] if booking.get("dp_transferred_at") else ""
        ]
        
        for col, value in enumerate(data, 1):
            cell = ws.cell(row=row, column=col, value=value)
            cell.border = thin_border
            if col in [8, 9]:  # Quantity and Amount columns
                cell.alignment = Alignment(horizontal="right")
        
        row += 1
    
    # Adjust column widths
    column_widths = [15, 25, 20, 15, 15, 30, 20, 12, 15, 15, 10, 15]
    for i, width in enumerate(column_widths, 1):
        ws.column_dimensions[chr(64 + i)].width = width
    
    # Save to buffer
    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    
    filename = f"dp_transfer_{status}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


# IMPORTANT: Static routes MUST be defined BEFORE dynamic routes like /bookings/{booking_id}
# to prevent FastAPI from matching 'pending-approval' as a booking_id parameter

@router.get("/bookings/pending-approval", response_model=List[BookingWithDetails])
async def get_pending_bookings(current_user: dict = Depends(get_current_user)):
    """Get bookings pending approval (PE Level only)."""
    user_role = current_user.get("role", 6)
    
    if not is_pe_level(user_role):
        raise HTTPException(status_code=403, detail="Only PE Desk or PE Manager can view pending bookings")
    
    bookings = await db.bookings.find(
        {"approval_status": "pending"},
        {"_id": 0, "user_id": 0}
    ).to_list(1000)
    
    if not bookings:
        return []
    
    # Enrich with client and stock details
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
    """Get loss bookings pending approval (PE Level only)."""
    if not is_pe_level(current_user.get("role", 6)):
        raise HTTPException(status_code=403, detail="Only PE Desk or PE Manager can view pending loss bookings")
    
    bookings = await db.bookings.find(
        {"is_loss_booking": True, "loss_approval_status": "pending"},
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


@router.put("/bookings/{booking_id}", response_model=Booking)
async def update_booking(booking_id: str, booking_data: BookingCreate, current_user: dict = Depends(get_current_user)):
    """Update a booking."""
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
        entity_name=f"{stock['symbol'] if stock else 'Unknown'} - {client['name'] if client else 'Unknown'}"
    )
    
    updated_booking = await db.bookings.find_one({"id": booking_id}, {"_id": 0, "user_id": 0})
    return updated_booking


@router.delete("/bookings/{booking_id}")
async def delete_booking(booking_id: str, current_user: dict = Depends(get_current_user)):
    """Delete a booking (PE Desk only)."""
    user_role = current_user.get("role", 6)
    
    if not is_pe_desk_only(user_role):
        raise HTTPException(status_code=403, detail="Only PE Desk can delete bookings")
    
    booking = await db.bookings.find_one({"id": booking_id}, {"_id": 0})
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    if booking.get("stock_transferred"):
        raise HTTPException(status_code=400, detail="Cannot delete a booking where stock has already been transferred")
    
    stock_id = booking["stock_id"]
    
    result = await db.bookings.delete_one({"id": booking_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    await update_inventory(stock_id)
    
    await create_audit_log(
        action="BOOKING_DELETE",
        entity_type="booking",
        entity_id=booking_id,
        user_id=current_user["id"],
        user_name=current_user["name"],
        user_role=user_role,
        entity_name=booking.get("booking_number", booking_id[:8])
    )
    
    return {"message": "Booking deleted successfully"}


@router.post("/bookings/{booking_id}/payments")
async def add_payment_tranche(
    booking_id: str,
    amount: float = Query(...),
    payment_mode: str = Query("bank_transfer"),
    reference_number: str = Query(None),
    notes: str = Query(None),
    current_user: dict = Depends(get_current_user)
):
    """Add a payment tranche to a booking."""
    user_role = current_user.get("role", 6)
    
    booking = await db.bookings.find_one({"id": booking_id}, {"_id": 0})
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    payments = booking.get("payments", [])
    total_amount = (booking.get("selling_price") or 0) * booking.get("quantity", 0)
    current_paid = sum(p.get("amount", 0) for p in payments)
    remaining = total_amount - current_paid
    
    if amount > remaining + 0.01:
        raise HTTPException(
            status_code=400,
            detail=f"Payment amount ({amount}) exceeds remaining balance ({remaining:.2f})"
        )
    
    tranche_number = len(payments) + 1
    payment = {
        "tranche_number": tranche_number,
        "amount": amount,
        "payment_mode": payment_mode,
        "reference_number": reference_number,
        "notes": notes,
        "recorded_by": current_user["id"],
        "recorded_by_name": current_user["name"],
        "recorded_at": datetime.now(timezone.utc).isoformat()
    }
    
    new_total_paid = current_paid + amount
    is_complete = abs(new_total_paid - total_amount) < 0.01
    
    update_data = {
        "$push": {"payments": payment},
        "$set": {
            "total_paid": new_total_paid,
            "payment_complete": is_complete
        }
    }
    
    # If payment is complete, mark as DP Ready for transfer
    if is_complete:
        update_data["$set"]["dp_status"] = "ready"
        update_data["$set"]["dp_ready_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.bookings.update_one({"id": booking_id}, update_data)
    
    return {
        "message": f"Payment of ₹{amount:,.2f} recorded successfully",
        "tranche_number": tranche_number,
        "total_paid": new_total_paid,
        "remaining": remaining - amount,
        "payment_complete": is_complete
    }


@router.get("/bookings/{booking_id}/payments")
async def get_booking_payments(
    booking_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get all payment tranches for a booking."""
    booking = await db.bookings.find_one({"id": booking_id}, {"_id": 0})
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    total_amount = (booking.get("selling_price") or 0) * booking.get("quantity", 0)
    payments = booking.get("payments", [])
    total_paid = sum(p.get("amount", 0) for p in payments)
    
    return {
        "booking_id": booking_id,
        "booking_number": booking.get("booking_number"),
        "total_amount": total_amount,
        "total_paid": total_paid,
        "remaining": total_amount - total_paid,
        "payment_complete": booking.get("payment_complete", False),
        "payments": payments
    }


@router.delete("/bookings/{booking_id}/payments/{tranche_number}")
async def delete_payment_tranche(
    booking_id: str,
    tranche_number: int,
    current_user: dict = Depends(get_current_user)
):
    """Delete a payment tranche (PE Desk only)."""
    if not is_pe_desk_only(current_user.get("role", 6)):
        raise HTTPException(status_code=403, detail="Only PE Desk can delete payments")
    
    booking = await db.bookings.find_one({"id": booking_id}, {"_id": 0})
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    payments = booking.get("payments", [])
    payment_to_delete = None
    
    for p in payments:
        if p.get("tranche_number") == tranche_number:
            payment_to_delete = p
            break
    
    if not payment_to_delete:
        raise HTTPException(status_code=404, detail="Payment tranche not found")
    
    new_payments = [p for p in payments if p.get("tranche_number") != tranche_number]
    new_total_paid = sum(p.get("amount", 0) for p in new_payments)
    total_amount = (booking.get("selling_price") or 0) * booking.get("quantity", 0)
    
    await db.bookings.update_one(
        {"id": booking_id},
        {"$set": {
            "payments": new_payments,
            "total_paid": new_total_paid,
            "payment_complete": abs(new_total_paid - total_amount) < 0.01
        }}
    )
    
    return {"message": f"Payment tranche {tranche_number} deleted successfully"}


@router.put("/bookings/{booking_id}/confirm-transfer")
async def confirm_stock_transfer(
    booking_id: str,
    dp_receipt_number: str = Query(None),
    notes: str = Query(None),
    current_user: dict = Depends(get_current_user)
):
    """Confirm DP stock transfer (PE Level only)."""
    if not is_pe_level(current_user.get("role", 6)):
        raise HTTPException(status_code=403, detail="Only PE Desk or PE Manager can confirm transfers")
    
    booking = await db.bookings.find_one({"id": booking_id}, {"_id": 0})
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    if booking.get("approval_status") != "approved":
        raise HTTPException(status_code=400, detail="Booking must be approved before transfer")
    
    if booking.get("stock_transferred"):
        raise HTTPException(status_code=400, detail="Stock already transferred")
    
    update_data = {
        "stock_transferred": True,
        "dp_receipt_number": dp_receipt_number,
        "transfer_notes": notes,
        "transfer_date": datetime.now(timezone.utc).isoformat(),
        "transferred_by": current_user["id"],
        "transferred_by_name": current_user["name"],
        "status": "completed"
    }
    
    await db.bookings.update_one({"id": booking_id}, {"$set": update_data})
    
    # Update inventory
    await update_inventory(booking["stock_id"])
    
    # Audit log
    await create_audit_log(
        action="BOOKING_TRANSFER",
        entity_type="booking",
        entity_id=booking_id,
        user_id=current_user["id"],
        user_name=current_user["name"],
        user_role=current_user.get("role", 1),
        entity_name=booking.get("booking_number", booking_id[:8])
    )
    
    return {
        "message": "Stock transfer confirmed successfully",
        "booking_id": booking_id,
        "dp_receipt_number": dp_receipt_number
    }


@router.put("/bookings/{booking_id}/approve-loss")
async def approve_loss_booking(
    booking_id: str,
    approve: bool = True,
    current_user: dict = Depends(get_current_user)
):
    """Approve or reject a loss booking (PE Level only)."""
    if not is_pe_level(current_user.get("role", 6)):
        raise HTTPException(status_code=403, detail="Only PE Desk or PE Manager can approve loss bookings")
    
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
    
    if not approve:
        update_data["status"] = "rejected"
        update_data["rejection_reason"] = "Loss booking rejected by PE"
    
    await db.bookings.update_one({"id": booking_id}, {"$set": update_data})
    
    return {"message": f"Loss booking {'approved' if approve else 'rejected'} successfully"}


@router.put("/bookings/{booking_id}/dp-transfer")
async def mark_dp_transferred(
    booking_id: str,
    dp_type: str,  # "NSDL" or "CDSL"
    current_user: dict = Depends(get_current_user)
):
    """Mark a booking as DP transferred and send notification to client"""
    from services.email_service import send_stock_transferred_email
    
    user_role = current_user.get("role", 6)
    
    if not is_pe_level(user_role):
        raise HTTPException(status_code=403, detail="Only PE level can mark DP as transferred")
    
    if dp_type not in ["NSDL", "CDSL"]:
        raise HTTPException(status_code=400, detail="dp_type must be 'NSDL' or 'CDSL'")
    
    booking = await db.bookings.find_one({"id": booking_id}, {"_id": 0})
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    if booking.get("dp_status") != "ready":
        raise HTTPException(status_code=400, detail="Booking is not in DP ready status")
    
    transfer_time = datetime.now(timezone.utc)
    
    # Update booking with transferred status
    await db.bookings.update_one(
        {"id": booking_id},
        {"$set": {
            "dp_status": "transferred",
            "dp_type": dp_type,
            "dp_transferred_at": transfer_time.isoformat(),
            "dp_transferred_by": current_user["id"],
            "dp_transferred_by_name": current_user["name"]
        }}
    )
    
    # Update inventory - deduct from available stock
    inventory = await db.inventory.find_one({"stock_id": booking.get("stock_id")}, {"_id": 0})
    if inventory:
        await db.inventory.update_one(
            {"stock_id": booking.get("stock_id")},
            {"$inc": {"available_quantity": -booking.get("quantity", 0)}}
        )
    
    # Get client and stock details for email
    client = await db.clients.find_one({"id": booking.get("client_id")}, {"_id": 0})
    stock = await db.stocks.find_one({"id": booking.get("stock_id")}, {"_id": 0})
    company_master = await db.company_master.find_one({"_id": "company_settings"}, {"_id": 0})
    
    # Send email to client
    if client and stock and company_master:
        await send_stock_transferred_email(
            booking_id=booking_id,
            client=client,
            booking=booking,
            stock=stock,
            dp_type=dp_type,
            transfer_date=transfer_time.isoformat(),
            company_master=company_master,
            cc_email=current_user.get("email")
        )
    
    await create_audit_log(
        action="DP_TRANSFERRED",
        entity_type="booking",
        entity_id=booking_id,
        user_id=current_user["id"],
        user_name=current_user["name"],
        user_role=user_role,
        details={
            "dp_type": dp_type,
            "quantity": booking.get("quantity"),
            "stock_id": booking.get("stock_id"),
            "client_id": booking.get("client_id")
        },
        entity_name=booking.get("booking_number", booking_id)
    )
    
    return {
        "message": f"Stock transferred via {dp_type}. Client notified about T+2 settlement.",
        "dp_type": dp_type,
        "quantity": booking.get("quantity"),
        "transferred_at": transfer_time.isoformat()
    }

