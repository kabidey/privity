"""
Fixed Income - Primary Market (IPO/NFO) Router

Handles new issue subscriptions for:
- NCDs (Non-Convertible Debentures)
- Bonds
- Government Securities

Workflow:
1. Issue Creation (by PE Desk)
2. Subscription Window Opening
3. Client Bid Submission
4. Allocation Processing
5. Settlement
"""

import logging
import uuid
from typing import Optional, List
from datetime import date, datetime, timedelta
from decimal import Decimal
from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from pydantic import BaseModel, Field

from database import db
from utils.auth import get_current_user
from services.permission_service import require_permission
from services.email_service import send_email
from config import is_pe_level

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/fixed-income/primary-market", tags=["Fixed Income - Primary Market"])


# ==================== MODELS ====================

class IssueStatus:
    DRAFT = "draft"
    UPCOMING = "upcoming"
    OPEN = "open"
    CLOSED = "closed"
    ALLOTMENT_DONE = "allotment_done"
    LISTED = "listed"
    CANCELLED = "cancelled"


class BidStatus:
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PARTIALLY_ALLOTTED = "partially_allotted"
    FULLY_ALLOTTED = "fully_allotted"
    NOT_ALLOTTED = "not_allotted"
    REFUND_INITIATED = "refund_initiated"
    COMPLETED = "completed"


class IssueCreate(BaseModel):
    """Model for creating a new primary market issue"""
    isin: str = Field(..., description="ISIN of the instrument")
    issuer_name: str
    issue_name: str = Field(..., description="Display name for the issue")
    issue_type: str = Field(default="NCD", description="NCD, BOND, GSEC")
    
    # Issue details
    face_value: Decimal
    issue_price: Decimal
    coupon_rate: Decimal
    coupon_frequency: str = Field(default="annual")
    tenure_years: int
    maturity_date: date
    
    # Credit info
    credit_rating: str = Field(default="UNRATED")
    rating_agency: Optional[str] = None
    
    # Subscription details
    issue_open_date: date
    issue_close_date: date
    min_application_size: int = Field(default=1, description="Minimum units to apply")
    max_application_size: Optional[int] = None
    lot_size: int = Field(default=1)
    
    # Amount details
    base_issue_size: Decimal = Field(..., description="Base issue size in crores")
    shelf_limit: Optional[Decimal] = Field(None, description="Shelf limit if any")
    green_shoe_option: Optional[Decimal] = None
    
    # Category allocations (percentages)
    category_1_pct: Decimal = Field(default=Decimal("25"), description="QIB allocation %")
    category_2_pct: Decimal = Field(default=Decimal("25"), description="Non-Institutional %")
    category_3_pct: Decimal = Field(default=Decimal("25"), description="HNI %")
    category_4_pct: Decimal = Field(default=Decimal("25"), description="Retail %")
    
    # Documents
    prospectus_url: Optional[str] = None
    
    notes: Optional[str] = None


class BidCreate(BaseModel):
    """Model for submitting a bid"""
    issue_id: str
    client_id: str
    category: str = Field(default="retail", description="retail, hni, qib, non_institutional")
    quantity: int = Field(..., gt=0)
    price: Decimal = Field(..., description="Bid price (usually same as issue price for NCDs)")
    payment_mode: str = Field(default="upi", description="upi, netbanking, neft")
    upi_id: Optional[str] = None
    bank_account: Optional[str] = None


# ==================== ISSUE ENDPOINTS ====================

@router.post("/issues", response_model=dict)
async def create_issue(
    issue: IssueCreate,
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("fixed_income.create", "create primary issue"))
):
    """
    Create a new primary market issue (IPO/NFO).
    Only PE Desk can create issues.
    """
    # Validate dates
    if issue.issue_close_date <= issue.issue_open_date:
        raise HTTPException(status_code=400, detail="Close date must be after open date")
    
    # Check ISIN doesn't already have an active issue
    existing = await db.fi_primary_issues.find_one({
        "isin": issue.isin,
        "status": {"$nin": [IssueStatus.CANCELLED, IssueStatus.LISTED]}
    })
    if existing:
        raise HTTPException(status_code=400, detail=f"Active issue already exists for ISIN {issue.isin}")
    
    # Generate issue number
    count = await db.fi_primary_issues.count_documents({})
    issue_number = f"IPO/{datetime.now().strftime('%y%m')}/{count + 1:04d}"
    
    # Create issue document
    issue_dict = {
        "id": str(uuid.uuid4()),
        "issue_number": issue_number,
        **issue.dict(),
        "status": IssueStatus.DRAFT,
        "total_bids": 0,
        "total_bid_amount": "0",
        "subscription_times": "0",
        "allotment_date": None,
        "listing_date": None,
        "created_at": datetime.now(),
        "created_by": current_user.get("id"),
        "created_by_name": current_user.get("name")
    }
    
    # Convert dates and decimals to strings for MongoDB
    for key in ["issue_open_date", "issue_close_date", "maturity_date"]:
        if issue_dict.get(key):
            issue_dict[key] = issue_dict[key].isoformat() if isinstance(issue_dict[key], date) else issue_dict[key]
    
    for key in ["face_value", "issue_price", "coupon_rate", "base_issue_size", "shelf_limit", 
                "green_shoe_option", "category_1_pct", "category_2_pct", "category_3_pct", "category_4_pct"]:
        if issue_dict.get(key) is not None:
            issue_dict[key] = str(issue_dict[key])
    
    await db.fi_primary_issues.insert_one(issue_dict)
    
    logger.info(f"Created primary issue {issue_number} for {issue.issuer_name}")
    
    return {"message": "Issue created", "issue_id": issue_dict["id"], "issue_number": issue_number}


@router.get("/issues", response_model=dict)
async def list_issues(
    status: Optional[str] = None,
    issuer: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("fixed_income.view", "view primary issues"))
):
    """List all primary market issues"""
    query = {}
    
    if status:
        query["status"] = status
    if issuer:
        query["issuer_name"] = {"$regex": issuer, "$options": "i"}
    
    total = await db.fi_primary_issues.count_documents(query)
    
    cursor = db.fi_primary_issues.find(query, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit)
    issues = await cursor.to_list(length=limit)
    
    return {"issues": issues, "total": total, "skip": skip, "limit": limit}


@router.get("/issues/{issue_id}", response_model=dict)
async def get_issue(
    issue_id: str,
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("fixed_income.view", "view primary issue"))
):
    """Get detailed issue information"""
    issue = await db.fi_primary_issues.find_one(
        {"$or": [{"id": issue_id}, {"issue_number": issue_id}]},
        {"_id": 0}
    )
    
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    
    # Get bid statistics
    bids_pipeline = [
        {"$match": {"issue_id": issue.get("id")}},
        {"$group": {
            "_id": "$category",
            "total_quantity": {"$sum": "$quantity"},
            "total_amount": {"$sum": {"$toDouble": "$amount"}},
            "count": {"$sum": 1}
        }}
    ]
    
    bid_stats = await db.fi_primary_bids.aggregate(bids_pipeline).to_list(length=10)
    issue["bid_statistics"] = {stat["_id"]: stat for stat in bid_stats}
    
    return issue


@router.patch("/issues/{issue_id}/status", response_model=dict)
async def update_issue_status(
    issue_id: str,
    new_status: str,
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("fixed_income.edit", "update issue status"))
):
    """Update issue status (open, close, etc.)"""
    valid_statuses = [IssueStatus.DRAFT, IssueStatus.UPCOMING, IssueStatus.OPEN, 
                      IssueStatus.CLOSED, IssueStatus.ALLOTMENT_DONE, IssueStatus.LISTED, IssueStatus.CANCELLED]
    
    if new_status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")
    
    result = await db.fi_primary_issues.update_one(
        {"id": issue_id},
        {"$set": {"status": new_status, "updated_at": datetime.now()}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Issue not found")
    
    logger.info(f"Issue {issue_id} status updated to {new_status}")
    
    return {"message": f"Status updated to {new_status}"}


# ==================== BID ENDPOINTS ====================

@router.post("/bids", response_model=dict)
async def submit_bid(
    bid: BidCreate,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("fixed_income.order_create", "submit bid"))
):
    """
    Submit a bid for a primary market issue.
    """
    # Get issue
    issue = await db.fi_primary_issues.find_one({"id": bid.issue_id}, {"_id": 0})
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    
    # Validate issue is open
    if issue.get("status") != IssueStatus.OPEN:
        raise HTTPException(status_code=400, detail="Issue is not open for subscription")
    
    # Check subscription window
    today = date.today()
    open_date = date.fromisoformat(issue["issue_open_date"]) if isinstance(issue["issue_open_date"], str) else issue["issue_open_date"]
    close_date = date.fromisoformat(issue["issue_close_date"]) if isinstance(issue["issue_close_date"], str) else issue["issue_close_date"]
    
    if today < open_date or today > close_date:
        raise HTTPException(status_code=400, detail="Subscription window is closed")
    
    # Validate quantity
    min_qty = issue.get("min_application_size", 1)
    max_qty = issue.get("max_application_size")
    lot_size = issue.get("lot_size", 1)
    
    if bid.quantity < min_qty:
        raise HTTPException(status_code=400, detail=f"Minimum application is {min_qty} units")
    if max_qty and bid.quantity > max_qty:
        raise HTTPException(status_code=400, detail=f"Maximum application is {max_qty} units")
    if bid.quantity % lot_size != 0:
        raise HTTPException(status_code=400, detail=f"Quantity must be in multiples of {lot_size}")
    
    # Get client
    client = await db.clients.find_one({"id": bid.client_id}, {"_id": 0})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # Calculate amount
    price = Decimal(str(bid.price))
    amount = price * bid.quantity
    
    # Generate bid number
    bid_count = await db.fi_primary_bids.count_documents({"issue_id": bid.issue_id})
    bid_number = f"{issue.get('issue_number')}/BID/{bid_count + 1:05d}"
    
    # Create bid
    bid_dict = {
        "id": str(uuid.uuid4()),
        "bid_number": bid_number,
        "issue_id": bid.issue_id,
        "issue_number": issue.get("issue_number"),
        "client_id": bid.client_id,
        "client_name": client.get("name"),
        "client_pan": client.get("pan_number"),
        "category": bid.category,
        "quantity": bid.quantity,
        "price": str(price),
        "amount": str(amount),
        "payment_mode": bid.payment_mode,
        "upi_id": bid.upi_id,
        "bank_account": bid.bank_account,
        "status": BidStatus.PENDING,
        "allotted_quantity": 0,
        "refund_amount": "0",
        "created_at": datetime.now(),
        "created_by": current_user.get("id"),
        "created_by_name": current_user.get("name")
    }
    
    await db.fi_primary_bids.insert_one(bid_dict)
    
    # Update issue totals
    await db.fi_primary_issues.update_one(
        {"id": bid.issue_id},
        {
            "$inc": {"total_bids": 1},
            "$set": {"updated_at": datetime.now()}
        }
    )
    
    # Send confirmation email
    if client.get("email"):
        background_tasks.add_task(
            send_email,
            to_email=client.get("email"),
            subject=f"Bid Confirmation - {issue.get('issue_name')}",
            body=f"""
            <p>Dear {client.get('name')},</p>
            <p>Your bid has been submitted successfully:</p>
            <ul>
                <li>Bid Number: {bid_number}</li>
                <li>Issue: {issue.get('issue_name')}</li>
                <li>Quantity: {bid.quantity}</li>
                <li>Amount: ₹{amount:,.2f}</li>
            </ul>
            <p>Status: Pending Payment Confirmation</p>
            """,
            template_key="fi_bid_confirmation",
            related_entity_type="fi_primary_bid",
            related_entity_id=bid_dict["id"]
        )
    
    logger.info(f"Bid {bid_number} submitted for issue {issue.get('issue_number')}")
    
    return {
        "message": "Bid submitted successfully",
        "bid_id": bid_dict["id"],
        "bid_number": bid_number,
        "amount": str(amount)
    }


@router.get("/bids", response_model=dict)
async def list_bids(
    issue_id: Optional[str] = None,
    client_id: Optional[str] = None,
    status: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("fixed_income.order_view", "view bids"))
):
    """List bids with filters"""
    query = {}
    
    # RBAC - non-PE users see only their submitted bids
    user_role = current_user.get("role", 99)
    if not is_pe_level(user_role):
        query["created_by"] = current_user.get("id")
    
    if issue_id:
        query["issue_id"] = issue_id
    if client_id:
        query["client_id"] = client_id
    if status:
        query["status"] = status
    
    total = await db.fi_primary_bids.count_documents(query)
    
    cursor = db.fi_primary_bids.find(query, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit)
    bids = await cursor.to_list(length=limit)
    
    return {"bids": bids, "total": total, "skip": skip, "limit": limit}


@router.patch("/bids/{bid_id}/confirm-payment", response_model=dict)
async def confirm_bid_payment(
    bid_id: str,
    payment_reference: str,
    payment_amount: float,
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("fixed_income.payment_record", "confirm bid payment"))
):
    """Confirm payment received for a bid"""
    result = await db.fi_primary_bids.update_one(
        {"id": bid_id},
        {
            "$set": {
                "status": BidStatus.CONFIRMED,
                "payment_confirmed": True,
                "payment_reference": payment_reference,
                "payment_amount": str(Decimal(str(payment_amount))),
                "payment_confirmed_at": datetime.now(),
                "payment_confirmed_by": current_user.get("id")
            }
        }
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Bid not found")
    
    return {"message": "Payment confirmed"}


# ==================== ALLOTMENT ====================

@router.post("/issues/{issue_id}/process-allotment", response_model=dict)
async def process_allotment(
    issue_id: str,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("fixed_income.settlement", "process allotment"))
):
    """
    Process allotment for an issue.
    This is a simplified pro-rata allotment.
    """
    issue = await db.fi_primary_issues.find_one({"id": issue_id}, {"_id": 0})
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    
    if issue.get("status") != IssueStatus.CLOSED:
        raise HTTPException(status_code=400, detail="Issue must be closed before allotment")
    
    # Get confirmed bids
    bids = await db.fi_primary_bids.find(
        {"issue_id": issue_id, "status": BidStatus.CONFIRMED},
        {"_id": 0}
    ).to_list(length=10000)
    
    if not bids:
        raise HTTPException(status_code=400, detail="No confirmed bids to process")
    
    # Calculate total demand
    total_demand = sum(b.get("quantity", 0) for b in bids)
    
    # Get total supply (base issue + green shoe if oversubscribed)
    base_issue = Decimal(str(issue.get("base_issue_size", 0))) * 10000000  # Convert crores to units
    issue_price = Decimal(str(issue.get("issue_price", 0)))
    total_units = int(base_issue / issue_price) if issue_price > 0 else 0
    
    # Calculate allotment ratio
    if total_demand > total_units:
        allotment_ratio = Decimal(total_units) / Decimal(total_demand)
    else:
        allotment_ratio = Decimal("1")
    
    # Process each bid
    allotted_count = 0
    for bid in bids:
        applied_qty = bid.get("quantity", 0)
        allotted_qty = int(Decimal(applied_qty) * allotment_ratio)
        
        # Ensure minimum allotment of lot size if any
        lot_size = issue.get("lot_size", 1)
        allotted_qty = (allotted_qty // lot_size) * lot_size
        
        # Calculate refund
        applied_amount = Decimal(str(bid.get("amount", 0)))
        allotted_amount = Decimal(allotted_qty) * issue_price
        refund_amount = applied_amount - allotted_amount
        
        # Update bid status
        if allotted_qty == applied_qty:
            new_status = BidStatus.FULLY_ALLOTTED
        elif allotted_qty > 0:
            new_status = BidStatus.PARTIALLY_ALLOTTED
        else:
            new_status = BidStatus.NOT_ALLOTTED
        
        await db.fi_primary_bids.update_one(
            {"id": bid["id"]},
            {
                "$set": {
                    "status": new_status,
                    "allotted_quantity": allotted_qty,
                    "allotted_amount": str(allotted_amount),
                    "refund_amount": str(refund_amount),
                    "allotment_processed_at": datetime.now()
                }
            }
        )
        
        if allotted_qty > 0:
            allotted_count += 1
    
    # Update issue status
    await db.fi_primary_issues.update_one(
        {"id": issue_id},
        {
            "$set": {
                "status": IssueStatus.ALLOTMENT_DONE,
                "allotment_date": datetime.now(),
                "allotment_ratio": str(allotment_ratio),
                "total_allotted": allotted_count
            }
        }
    )
    
    logger.info(f"Allotment processed for {issue_id}: {allotted_count}/{len(bids)} bids allotted")
    
    return {
        "message": "Allotment processed",
        "total_bids": len(bids),
        "allotted_bids": allotted_count,
        "allotment_ratio": str(allotment_ratio)
    }


# ==================== ACTIVE ISSUES FOR CLIENTS ====================

@router.get("/active-issues", response_model=dict)
async def get_active_issues(
    current_user: dict = Depends(get_current_user)
):
    """Get currently open issues for subscription (public endpoint)"""
    today = date.today().isoformat()
    
    issues = await db.fi_primary_issues.find(
        {
            "status": IssueStatus.OPEN,
            "issue_open_date": {"$lte": today},
            "issue_close_date": {"$gte": today}
        },
        {"_id": 0}
    ).sort("issue_close_date", 1).to_list(length=50)
    
    return {"issues": issues, "count": len(issues)}
