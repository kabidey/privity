"""
Fixed Income Router - Order Management System (OMS)

Handles the complete order lifecycle:
1. Deal Sheet creation
2. Client approval workflow
3. Payment tracking
4. Settlement management

Implements strict RBAC:
- Agents can see all orders
- Clients can only see their own orders
"""

import logging
import uuid
from typing import Optional, List
from datetime import date, datetime, timedelta
from decimal import Decimal
from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks

from database import db
from utils.auth import get_current_user
from services.permission_service import require_permission, has_permission
from services.email_service import send_email
from config import is_pe_level, ROLES
from middleware.license_enforcement import license_enforcer

from .models import (
    FIOrder, FIOrderCreate, OrderStatus, OrderType,
    FIDealSheet, SettlementStatus, CouponFrequency, DayCountConvention
)
from .calculations import (
    calculate_accrued_interest, calculate_ytm,
    calculate_dirty_price, generate_cash_flow_schedule
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/fixed-income/orders", tags=["Fixed Income - Order Management"])


# ==================== ORDER NUMBER GENERATION ====================

async def generate_order_number() -> str:
    """Generate unique order number: FI/YY-YY/NNNN"""
    current_fy = datetime.now().year
    fy_start = current_fy if datetime.now().month >= 4 else current_fy - 1
    fy_end = fy_start + 1
    fy_str = f"{str(fy_start)[-2:]}-{str(fy_end)[-2:]}"
    
    # Get last order number for this FY
    last_order = await db.fi_orders.find_one(
        {"order_number": {"$regex": f"^FI/{fy_str}/"}},
        sort=[("order_number", -1)]
    )
    
    if last_order:
        try:
            last_num = int(last_order["order_number"].split("/")[-1])
            new_num = last_num + 1
        except (ValueError, IndexError):
            new_num = 1
    else:
        new_num = 1
    
    return f"FI/{fy_str}/{new_num:04d}"


# ==================== ORDER CRUD ====================

@router.post("", response_model=dict)
async def create_order(
    order: FIOrderCreate,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("fixed_income.order_create", "create fixed income order"))
):
    """
    Create a new fixed income order (Deal Sheet).
    
    This calculates all pricing, creates the deal sheet, and optionally
    sends it to the client for approval.
    
    Requires: fixed_income.order_create permission
    """
    # Validate client exists
    client = await db.fi_clients.find_one({"id": order.client_id}, {"_id": 0})
    if not client:
        # Try main clients collection
        client = await db.clients.find_one({"id": order.client_id}, {"_id": 0})
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")
    
    # Validate instrument exists
    instrument = await db.fi_instruments.find_one({"isin": order.isin}, {"_id": 0})
    if not instrument:
        raise HTTPException(status_code=404, detail=f"Instrument with ISIN {order.isin} not found")
    
    # Parse instrument dates
    issue_dt = date.fromisoformat(instrument["issue_date"]) if isinstance(instrument["issue_date"], str) else instrument["issue_date"]
    maturity_dt = date.fromisoformat(instrument["maturity_date"]) if isinstance(instrument["maturity_date"], str) else instrument["maturity_date"]
    
    face_value = Decimal(str(instrument.get("face_value", 100)))
    coupon_rate = Decimal(str(instrument.get("coupon_rate", 0)))
    freq = CouponFrequency(instrument.get("coupon_frequency", "annual"))
    conv = DayCountConvention(instrument.get("day_count_convention", "ACT/365"))
    
    clean_price = Decimal(str(order.clean_price))
    
    # Calculate accrued interest
    accrued = calculate_accrued_interest(
        face_value=face_value,
        coupon_rate=coupon_rate,
        settlement_date=order.settlement_date,
        issue_date=issue_dt,
        maturity_date=maturity_dt,
        frequency=freq,
        convention=conv
    )
    
    # Calculate dirty price
    dirty_price = clean_price + accrued
    
    # Calculate YTM
    ytm = calculate_ytm(
        clean_price=clean_price,
        face_value=face_value,
        coupon_rate=coupon_rate,
        settlement_date=order.settlement_date,
        maturity_date=maturity_dt,
        frequency=freq,
        convention=conv
    )
    
    # Calculate amounts
    principal_amount = clean_price * order.quantity
    accrued_interest_amount = accrued * order.quantity
    total_consideration = dirty_price * order.quantity
    
    # Calculate charges (example rates - should be configurable)
    brokerage_rate = Decimal("0.0010")  # 0.10%
    stamp_duty_rate = Decimal("0.00015")  # 0.015%
    gst_rate = Decimal("0.18")  # 18% on brokerage
    
    brokerage = (total_consideration * brokerage_rate).quantize(Decimal("0.01"))
    stamp_duty = (total_consideration * stamp_duty_rate).quantize(Decimal("0.01"))
    gst = (brokerage * gst_rate).quantize(Decimal("0.01"))
    
    # Net amount depends on order type
    if order.order_type == OrderType.SECONDARY_BUY:
        net_amount = total_consideration + brokerage + stamp_duty + gst
    else:  # SELL
        net_amount = total_consideration - brokerage - stamp_duty - gst
    
    # Generate order number
    order_number = await generate_order_number()
    
    # Create order document
    order_dict = {
        "id": str(uuid.uuid4()),
        "order_number": order_number,
        "client_id": order.client_id,
        "instrument_id": instrument.get("id"),
        "isin": order.isin,
        "order_type": order.order_type.value,
        "quantity": order.quantity,
        "clean_price": str(clean_price),
        "accrued_interest": str(accrued),
        "dirty_price": str(dirty_price),
        "ytm": str(ytm),
        "settlement_date": order.settlement_date.isoformat(),
        "principal_amount": str(principal_amount),
        "accrued_interest_amount": str(accrued_interest_amount),
        "total_consideration": str(total_consideration),
        "brokerage": str(brokerage),
        "stamp_duty": str(stamp_duty),
        "gst": str(gst),
        "other_charges": "0",
        "net_amount": str(net_amount),
        "status": OrderStatus.DRAFT.value,
        "notes": order.notes,
        "approved_by_client": False,
        "payment_received": False,
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
        "created_by": current_user.get("id"),
        "created_by_name": current_user.get("name")
    }
    
    # Store order
    await db.fi_orders.insert_one(order_dict)
    
    logger.info(f"Created FI order {order_number} for client {order.client_id}")
    
    return {
        "message": "Order created successfully",
        "order_id": order_dict["id"],
        "order_number": order_number,
        "net_amount": str(net_amount),
        "ytm": str(ytm)
    }


@router.get("", response_model=dict)
async def list_orders(
    status: Optional[OrderStatus] = None,
    client_id: Optional[str] = None,
    order_type: Optional[OrderType] = None,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("fixed_income.order_view", "view fixed income orders"))
):
    """
    List orders with RBAC filtering.
    
    - PE Level users: See all orders
    - Agents (Employee, BP): See orders they created
    - Clients: See only their own orders (not implemented in this system)
    """
    user_role = current_user.get("role", 99)
    
    # Build query based on role
    query = {}
    
    # Non-PE users can only see their own created orders
    if not is_pe_level(user_role):
        query["created_by"] = current_user.get("id")
    
    # Apply filters
    if status:
        query["status"] = status.value
    
    if client_id:
        query["client_id"] = client_id
    
    if order_type:
        query["order_type"] = order_type.value
    
    if from_date:
        query["created_at"] = {"$gte": datetime.combine(from_date, datetime.min.time())}
    
    if to_date:
        if "created_at" in query:
            query["created_at"]["$lte"] = datetime.combine(to_date, datetime.max.time())
        else:
            query["created_at"] = {"$lte": datetime.combine(to_date, datetime.max.time())}
    
    # Get total count
    total = await db.fi_orders.count_documents(query)
    
    # Get orders
    cursor = db.fi_orders.find(query, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit)
    orders = await cursor.to_list(length=limit)
    
    # Enrich with client and instrument names
    for order in orders:
        # Get client name
        client = await db.clients.find_one({"id": order.get("client_id")}, {"_id": 0, "name": 1})
        order["client_name"] = client.get("name", "Unknown") if client else "Unknown"
        
        # Get instrument name
        instrument = await db.fi_instruments.find_one({"isin": order.get("isin")}, {"_id": 0, "issuer_name": 1})
        order["issuer_name"] = instrument.get("issuer_name", "Unknown") if instrument else "Unknown"
    
    return {
        "orders": orders,
        "total": total,
        "skip": skip,
        "limit": limit
    }


@router.get("/{order_id}", response_model=dict)
async def get_order(
    order_id: str,
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("fixed_income.order_view", "view fixed income order"))
):
    """
    Get detailed order information.
    """
    order = await db.fi_orders.find_one(
        {"$or": [{"id": order_id}, {"order_number": order_id}]},
        {"_id": 0}
    )
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # RBAC check - non-PE users can only see their own orders
    user_role = current_user.get("role", 99)
    if not is_pe_level(user_role) and order.get("created_by") != current_user.get("id"):
        raise HTTPException(status_code=403, detail="Access denied to this order")
    
    # Enrich with client and instrument details
    client = await db.clients.find_one({"id": order.get("client_id")}, {"_id": 0})
    order["client"] = client
    
    instrument = await db.fi_instruments.find_one({"isin": order.get("isin")}, {"_id": 0})
    order["instrument"] = instrument
    
    return order


# ==================== DEAL SHEET & APPROVAL WORKFLOW ====================

@router.post("/{order_id}/send-deal-sheet", response_model=dict)
async def send_deal_sheet(
    order_id: str,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("fixed_income.order_send", "send deal sheet"))
):
    """
    Send deal sheet to client for approval via email.
    
    This updates the order status to PENDING_APPROVAL and sends
    an email with the deal details and approval link.
    """
    # Get order
    order = await db.fi_orders.find_one({"id": order_id}, {"_id": 0})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    if order.get("status") != OrderStatus.DRAFT.value:
        raise HTTPException(
            status_code=400, 
            detail=f"Can only send deal sheet for DRAFT orders. Current status: {order.get('status')}"
        )
    
    # Get client
    client = await db.clients.find_one({"id": order.get("client_id")}, {"_id": 0})
    if not client or not client.get("email"):
        raise HTTPException(status_code=400, detail="Client email not found")
    
    # Get instrument
    instrument = await db.fi_instruments.find_one({"isin": order.get("isin")}, {"_id": 0})
    if not instrument:
        raise HTTPException(status_code=404, detail="Instrument not found")
    
    # Get company bank details for payment instructions
    company = await db.company_master.find_one({"_id": "company_settings"})
    bank_details = {
        "bank_name": company.get("company_bank_name", "N/A") if company else "N/A",
        "bank_account": company.get("company_bank_account", "N/A") if company else "N/A",
        "bank_ifsc": company.get("company_bank_ifsc", "N/A") if company else "N/A"
    }
    
    # Generate payment reference
    payment_reference = f"FI-{order.get('order_number', '').replace('/', '-')}"
    
    # Generate cash flow preview
    cash_flows = generate_cash_flow_schedule(
        face_value=Decimal(str(instrument.get("face_value", 100))),
        coupon_rate=Decimal(str(instrument.get("coupon_rate", 0))),
        settlement_date=date.fromisoformat(order["settlement_date"]) if isinstance(order["settlement_date"], str) else order["settlement_date"],
        issue_date=date.fromisoformat(instrument["issue_date"]) if isinstance(instrument["issue_date"], str) else instrument["issue_date"],
        maturity_date=date.fromisoformat(instrument["maturity_date"]) if isinstance(instrument["maturity_date"], str) else instrument["maturity_date"],
        frequency=CouponFrequency(instrument.get("coupon_frequency", "annual")),
        quantity=order.get("quantity", 1)
    )
    
    # Take first 4 cash flows for preview
    cash_flow_preview = [
        {"date": cf.date.isoformat(), "amount": str(cf.amount), "type": cf.type}
        for cf in cash_flows[:4]
    ]
    
    # Create deal sheet document
    deal_sheet = {
        "id": str(uuid.uuid4()),
        "order_id": order_id,
        "client_id": order.get("client_id"),
        "client_name": client.get("name"),
        "client_pan": client.get("pan_number"),
        "instrument_id": instrument.get("id"),
        "isin": order.get("isin"),
        "issuer_name": instrument.get("issuer_name"),
        "instrument_type": instrument.get("instrument_type"),
        "coupon_rate": instrument.get("coupon_rate"),
        "maturity_date": instrument.get("maturity_date"),
        "credit_rating": instrument.get("credit_rating"),
        "order_type": order.get("order_type"),
        "quantity": order.get("quantity"),
        "clean_price": order.get("clean_price"),
        "accrued_interest": order.get("accrued_interest"),
        "dirty_price": order.get("dirty_price"),
        "ytm": order.get("ytm"),
        "principal_amount": order.get("principal_amount"),
        "accrued_interest_amount": order.get("accrued_interest_amount"),
        "total_consideration": order.get("total_consideration"),
        "brokerage": order.get("brokerage"),
        "stamp_duty": order.get("stamp_duty"),
        "gst": order.get("gst"),
        "net_amount": order.get("net_amount"),
        "settlement_date": order.get("settlement_date"),
        "cash_flow_preview": cash_flow_preview,
        "status": "pending",
        "sent_at": datetime.now(),
        "expires_at": datetime.now() + timedelta(days=3),
        "bank_name": bank_details["bank_name"],
        "bank_account": bank_details["bank_account"],
        "bank_ifsc": bank_details["bank_ifsc"],
        "payment_reference": payment_reference
    }
    
    # Store deal sheet
    await db.fi_deal_sheets.insert_one(deal_sheet)
    
    # Update order status
    await db.fi_orders.update_one(
        {"id": order_id},
        {
            "$set": {
                "status": OrderStatus.PENDING_APPROVAL.value,
                "deal_sheet_id": deal_sheet["id"],
                "updated_at": datetime.now()
            }
        }
    )
    
    # Send email to client
    subject = f"Deal Sheet - {order.get('order_number')} | {instrument.get('issuer_name')}"
    
    body = f"""
    <div style="font-family: Arial, sans-serif; max-width: 700px; margin: 0 auto;">
        <h2 style="color: #064E3B;">Fixed Income Deal Sheet</h2>
        <p>Dear {client.get('name', 'Client')},</p>
        <p>Please find below the deal sheet for your review and approval:</p>
        
        <h3 style="color: #064E3B; margin-top: 20px;">Order Details</h3>
        <table style="width: 100%; border-collapse: collapse;">
            <tr style="background-color: #f3f4f6;">
                <td style="padding: 8px; border: 1px solid #e5e7eb;">Order Number</td>
                <td style="padding: 8px; border: 1px solid #e5e7eb;"><strong>{order.get('order_number')}</strong></td>
            </tr>
            <tr>
                <td style="padding: 8px; border: 1px solid #e5e7eb;">Security</td>
                <td style="padding: 8px; border: 1px solid #e5e7eb;">{instrument.get('issuer_name')} ({order.get('isin')})</td>
            </tr>
            <tr style="background-color: #f3f4f6;">
                <td style="padding: 8px; border: 1px solid #e5e7eb;">Type</td>
                <td style="padding: 8px; border: 1px solid #e5e7eb;">{order.get('order_type').replace('_', ' ').title()}</td>
            </tr>
            <tr>
                <td style="padding: 8px; border: 1px solid #e5e7eb;">Quantity</td>
                <td style="padding: 8px; border: 1px solid #e5e7eb;">{order.get('quantity'):,}</td>
            </tr>
            <tr style="background-color: #f3f4f6;">
                <td style="padding: 8px; border: 1px solid #e5e7eb;">Clean Price</td>
                <td style="padding: 8px; border: 1px solid #e5e7eb;">₹ {order.get('clean_price')}</td>
            </tr>
            <tr>
                <td style="padding: 8px; border: 1px solid #e5e7eb;">Accrued Interest</td>
                <td style="padding: 8px; border: 1px solid #e5e7eb;">₹ {order.get('accrued_interest')}</td>
            </tr>
            <tr style="background-color: #f3f4f6;">
                <td style="padding: 8px; border: 1px solid #e5e7eb;">Dirty Price</td>
                <td style="padding: 8px; border: 1px solid #e5e7eb;">₹ {order.get('dirty_price')}</td>
            </tr>
            <tr>
                <td style="padding: 8px; border: 1px solid #e5e7eb;">YTM</td>
                <td style="padding: 8px; border: 1px solid #e5e7eb;"><strong>{order.get('ytm')}%</strong></td>
            </tr>
        </table>
        
        <h3 style="color: #064E3B; margin-top: 20px;">Amount Breakup</h3>
        <table style="width: 100%; border-collapse: collapse;">
            <tr>
                <td style="padding: 8px; border: 1px solid #e5e7eb;">Principal Amount</td>
                <td style="padding: 8px; border: 1px solid #e5e7eb; text-align: right;">₹ {order.get('principal_amount')}</td>
            </tr>
            <tr>
                <td style="padding: 8px; border: 1px solid #e5e7eb;">Accrued Interest</td>
                <td style="padding: 8px; border: 1px solid #e5e7eb; text-align: right;">₹ {order.get('accrued_interest_amount')}</td>
            </tr>
            <tr>
                <td style="padding: 8px; border: 1px solid #e5e7eb;">Brokerage</td>
                <td style="padding: 8px; border: 1px solid #e5e7eb; text-align: right;">₹ {order.get('brokerage')}</td>
            </tr>
            <tr>
                <td style="padding: 8px; border: 1px solid #e5e7eb;">Stamp Duty</td>
                <td style="padding: 8px; border: 1px solid #e5e7eb; text-align: right;">₹ {order.get('stamp_duty')}</td>
            </tr>
            <tr>
                <td style="padding: 8px; border: 1px solid #e5e7eb;">GST</td>
                <td style="padding: 8px; border: 1px solid #e5e7eb; text-align: right;">₹ {order.get('gst')}</td>
            </tr>
            <tr style="background-color: #064E3B; color: white;">
                <td style="padding: 10px; border: 1px solid #064E3B;"><strong>Net Amount Payable</strong></td>
                <td style="padding: 10px; border: 1px solid #064E3B; text-align: right;"><strong>₹ {order.get('net_amount')}</strong></td>
            </tr>
        </table>
        
        <h3 style="color: #064E3B; margin-top: 20px;">Payment Details</h3>
        <table style="width: 100%; border-collapse: collapse; background-color: #fef3c7;">
            <tr>
                <td style="padding: 8px; border: 1px solid #fbbf24;">Bank Name</td>
                <td style="padding: 8px; border: 1px solid #fbbf24;">{bank_details['bank_name']}</td>
            </tr>
            <tr>
                <td style="padding: 8px; border: 1px solid #fbbf24;">Account Number</td>
                <td style="padding: 8px; border: 1px solid #fbbf24;">{bank_details['bank_account']}</td>
            </tr>
            <tr>
                <td style="padding: 8px; border: 1px solid #fbbf24;">IFSC Code</td>
                <td style="padding: 8px; border: 1px solid #fbbf24;">{bank_details['bank_ifsc']}</td>
            </tr>
            <tr>
                <td style="padding: 8px; border: 1px solid #fbbf24;">Payment Reference</td>
                <td style="padding: 8px; border: 1px solid #fbbf24;"><strong>{payment_reference}</strong></td>
            </tr>
        </table>
        
        <p style="margin-top: 20px; color: #666;">
            Settlement Date: <strong>{order.get('settlement_date')}</strong><br/>
            This deal sheet expires on: <strong>{deal_sheet['expires_at'].strftime('%d-%b-%Y %H:%M')}</strong>
        </p>
        
        <p style="color: #666; font-size: 12px; margin-top: 30px;">
            To approve this deal, please reply to this email with "APPROVED" or contact your relationship manager.<br/>
            Any discrepancy should be reported immediately.
        </p>
    </div>
    """
    
    # Queue email
    background_tasks.add_task(
        send_email,
        to_email=client.get("email"),
        subject=subject,
        body=body,
        template_key="fi_deal_sheet",
        related_entity_type="fi_order",
        related_entity_id=order_id
    )
    
    logger.info(f"Deal sheet sent for order {order.get('order_number')} to {client.get('email')}")
    
    return {
        "message": "Deal sheet sent successfully",
        "deal_sheet_id": deal_sheet["id"],
        "expires_at": deal_sheet["expires_at"].isoformat()
    }


@router.post("/{order_id}/approve", response_model=dict)
async def approve_order(
    order_id: str,
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("fixed_income.order_approve", "approve fixed income order"))
):
    """
    Mark order as approved by client.
    
    This is typically done by an agent after receiving client confirmation.
    """
    # Get order
    order = await db.fi_orders.find_one({"id": order_id}, {"_id": 0})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    if order.get("status") != OrderStatus.PENDING_APPROVAL.value:
        raise HTTPException(
            status_code=400,
            detail=f"Order must be in PENDING_APPROVAL status. Current: {order.get('status')}"
        )
    
    # Update order
    await db.fi_orders.update_one(
        {"id": order_id},
        {
            "$set": {
                "status": OrderStatus.CLIENT_APPROVED.value,
                "approved_by_client": True,
                "client_approval_date": datetime.now(),
                "updated_at": datetime.now()
            }
        }
    )
    
    # Update deal sheet
    await db.fi_deal_sheets.update_one(
        {"order_id": order_id},
        {"$set": {"status": "approved", "approved_at": datetime.now()}}
    )
    
    logger.info(f"Order {order.get('order_number')} approved by {current_user.get('name')}")
    
    return {"message": "Order approved successfully", "status": OrderStatus.CLIENT_APPROVED.value}


@router.post("/{order_id}/reject", response_model=dict)
async def reject_order(
    order_id: str,
    reason: str,
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("fixed_income.order_approve", "reject fixed income order"))
):
    """
    Reject an order on behalf of client.
    """
    order = await db.fi_orders.find_one({"id": order_id}, {"_id": 0})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    await db.fi_orders.update_one(
        {"id": order_id},
        {
            "$set": {
                "status": OrderStatus.CLIENT_REJECTED.value,
                "approved_by_client": False,
                "client_rejection_reason": reason,
                "updated_at": datetime.now()
            }
        }
    )
    
    await db.fi_deal_sheets.update_one(
        {"order_id": order_id},
        {"$set": {"status": "rejected", "rejected_at": datetime.now(), "rejection_reason": reason}}
    )
    
    logger.info(f"Order {order.get('order_number')} rejected: {reason}")
    
    return {"message": "Order rejected", "status": OrderStatus.CLIENT_REJECTED.value}


# ==================== PAYMENT TRACKING ====================

@router.post("/{order_id}/record-payment", response_model=dict)
async def record_payment(
    order_id: str,
    payment_amount: float,
    payment_reference: str,
    payment_date: Optional[date] = None,
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("fixed_income.payment_record", "record payment"))
):
    """
    Record payment received from client.
    """
    order = await db.fi_orders.find_one({"id": order_id}, {"_id": 0})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    if order.get("status") not in [OrderStatus.CLIENT_APPROVED.value, OrderStatus.PAYMENT_PENDING.value]:
        raise HTTPException(
            status_code=400,
            detail=f"Payment can only be recorded for approved orders. Current: {order.get('status')}"
        )
    
    payment_dt = datetime.combine(payment_date, datetime.min.time()) if payment_date else datetime.now()
    
    await db.fi_orders.update_one(
        {"id": order_id},
        {
            "$set": {
                "status": OrderStatus.PAYMENT_RECEIVED.value,
                "payment_received": True,
                "payment_received_date": payment_dt,
                "payment_reference": payment_reference,
                "payment_amount": str(Decimal(str(payment_amount))),
                "updated_at": datetime.now()
            }
        }
    )
    
    logger.info(f"Payment of ₹{payment_amount} recorded for order {order.get('order_number')}")
    
    return {"message": "Payment recorded", "status": OrderStatus.PAYMENT_RECEIVED.value}


# ==================== SETTLEMENT ====================

@router.post("/{order_id}/initiate-settlement", response_model=dict)
async def initiate_settlement(
    order_id: str,
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("fixed_income.settlement", "initiate settlement"))
):
    """
    Initiate settlement process after payment is received.
    """
    order = await db.fi_orders.find_one({"id": order_id}, {"_id": 0})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    if order.get("status") != OrderStatus.PAYMENT_RECEIVED.value:
        raise HTTPException(
            status_code=400,
            detail="Settlement can only be initiated after payment is received"
        )
    
    await db.fi_orders.update_one(
        {"id": order_id},
        {
            "$set": {
                "status": OrderStatus.SETTLEMENT_INITIATED.value,
                "settlement_initiated_at": datetime.now(),
                "settlement_initiated_by": current_user.get("id"),
                "updated_at": datetime.now()
            }
        }
    )
    
    logger.info(f"Settlement initiated for order {order.get('order_number')}")
    
    return {"message": "Settlement initiated", "status": OrderStatus.SETTLEMENT_INITIATED.value}


@router.post("/{order_id}/complete-settlement", response_model=dict)
async def complete_settlement(
    order_id: str,
    counterparty_payment: float,
    settlement_reference: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("fixed_income.settlement", "complete settlement"))
):
    """
    Complete settlement and close the deal.
    
    Records counterparty payment and creates transaction record.
    """
    order = await db.fi_orders.find_one({"id": order_id}, {"_id": 0})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    if order.get("status") != OrderStatus.SETTLEMENT_INITIATED.value:
        raise HTTPException(
            status_code=400,
            detail="Settlement must be initiated first"
        )
    
    # Create transaction record
    transaction_number = f"FIT-{order.get('order_number', '').replace('FI/', '')}"
    
    transaction = {
        "id": str(uuid.uuid4()),
        "transaction_number": transaction_number,
        "order_id": order_id,
        "client_id": order.get("client_id"),
        "instrument_id": order.get("instrument_id"),
        "isin": order.get("isin"),
        "transaction_type": order.get("order_type"),
        "transaction_date": datetime.now().date().isoformat(),
        "settlement_date": order.get("settlement_date"),
        "quantity": order.get("quantity"),
        "clean_price": order.get("clean_price"),
        "accrued_interest": order.get("accrued_interest"),
        "dirty_price": order.get("dirty_price"),
        "ytm": order.get("ytm"),
        "principal_amount": order.get("principal_amount"),
        "accrued_interest_amount": order.get("accrued_interest_amount"),
        "total_consideration": order.get("total_consideration"),
        "charges": str(
            Decimal(order.get("brokerage", "0")) + 
            Decimal(order.get("stamp_duty", "0")) + 
            Decimal(order.get("gst", "0"))
        ),
        "net_amount": order.get("net_amount"),
        "settlement_status": SettlementStatus.DEAL_CLOSED.value,
        "client_payment_received": order.get("payment_amount", "0"),
        "counterparty_payment_made": str(Decimal(str(counterparty_payment))),
        "settlement_reference": settlement_reference,
        "created_at": datetime.now(),
        "created_by": current_user.get("id")
    }
    
    await db.fi_transactions.insert_one(transaction)
    
    # Update order
    await db.fi_orders.update_one(
        {"id": order_id},
        {
            "$set": {
                "status": OrderStatus.SETTLED.value,
                "settlement_completed_at": datetime.now(),
                "settlement_completed_by": current_user.get("id"),
                "counterparty_payment": str(Decimal(str(counterparty_payment))),
                "settlement_reference": settlement_reference,
                "transaction_id": transaction["id"],
                "updated_at": datetime.now()
            }
        }
    )
    
    # Update client holdings
    await _update_client_holdings(order, transaction)
    
    logger.info(f"Settlement completed for order {order.get('order_number')}")
    
    return {
        "message": "Settlement completed successfully",
        "transaction_number": transaction_number,
        "status": OrderStatus.SETTLED.value
    }


async def _update_client_holdings(order: dict, transaction: dict):
    """Update client holdings after successful settlement"""
    client_id = order.get("client_id")
    isin = order.get("isin")
    quantity = order.get("quantity", 0)
    
    # Get existing holding
    holding = await db.fi_holdings.find_one({"client_id": client_id, "isin": isin})
    
    if order.get("order_type") == OrderType.SECONDARY_BUY.value:
        # Add to holdings
        if holding:
            new_qty = holding.get("quantity", 0) + quantity
            total_cost = (
                Decimal(str(holding.get("average_cost", 0))) * holding.get("quantity", 0) +
                Decimal(str(order.get("dirty_price", 0))) * quantity
            )
            new_avg_cost = total_cost / new_qty if new_qty > 0 else Decimal("0")
            
            await db.fi_holdings.update_one(
                {"client_id": client_id, "isin": isin},
                {
                    "$set": {
                        "quantity": new_qty,
                        "average_cost": str(new_avg_cost),
                        "last_updated": datetime.now()
                    }
                }
            )
        else:
            # Create new holding
            instrument = await db.fi_instruments.find_one({"isin": isin}, {"_id": 0})
            
            new_holding = {
                "id": str(uuid.uuid4()),
                "client_id": client_id,
                "instrument_id": order.get("instrument_id"),
                "isin": isin,
                "quantity": quantity,
                "average_cost": order.get("dirty_price"),
                "face_value": str(instrument.get("face_value", 100)) if instrument else "100",
                "current_value": order.get("total_consideration"),
                "unrealized_pnl": "0",
                "last_updated": datetime.now()
            }
            await db.fi_holdings.insert_one(new_holding)
    
    else:  # SELL
        if holding:
            new_qty = holding.get("quantity", 0) - quantity
            if new_qty <= 0:
                await db.fi_holdings.delete_one({"client_id": client_id, "isin": isin})
            else:
                await db.fi_holdings.update_one(
                    {"client_id": client_id, "isin": isin},
                    {
                        "$set": {
                            "quantity": new_qty,
                            "last_updated": datetime.now()
                        }
                    }
                )
