"""
Referral Partners Router

Handles all referral partner (RP) management operations.
- Employees can CREATE RPs (pending approval)
- PE Desk and PE Manager can CREATE RPs (auto-approved)
- PE Desk and PE Manager can APPROVE/REJECT/EDIT RPs
"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from typing import List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel
import uuid
import os
import aiofiles
from pathlib import Path

from database import db
from config import UPLOAD_DIR
from models import ReferralPartnerCreate, ReferralPartner
from utils.auth import get_current_user
from services.audit_service import create_audit_log
from services.email_service import send_templated_email
from services.file_storage import upload_file_to_gridfs, get_file_url
from services.permission_service import (
    require_permission
)
from utils.demo_isolation import add_demo_filter

router = APIRouter(tags=["Referral Partners"])


# Helper function for backward compatibility
def is_pe_level(role: int) -> bool:
    """Check if role is PE level (PE Desk or PE Manager)."""
    return role in [1, 2]


async def generate_rp_code() -> str:
    """Generate a unique RP code in format RP-XXXX"""
    # Use atomic counter for unique codes
    counter = await db.counters.find_one_and_update(
        {"_id": "referral_partner"},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=True
    )
    seq_num = counter.get("seq", 1)
    return f"RP-{seq_num:04d}"


@router.post("/referral-partners", response_model=ReferralPartner)
async def create_referral_partner(
    rp_data: ReferralPartnerCreate,
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("referral_partners.create", "create referral partners"))
):
    """
    Create a new Referral Partner.
    Any authenticated user (including Employees) can create RPs.
    All fields are mandatory including documents (uploaded separately).
    """
    user_role = current_user.get("role", 6)
    
    # Validate 10-digit phone number (without +91)
    phone_digits = ''.join(filter(str.isdigit, rp_data.phone))
    if len(phone_digits) != 10:
        raise HTTPException(
            status_code=400,
            detail="Phone number must be exactly 10 digits (without +91)"
        )
    
    # Validate PAN format (basic validation)
    if len(rp_data.pan_number) != 10:
        raise HTTPException(
            status_code=400,
            detail="PAN number must be exactly 10 characters"
        )
    
    # Validate Aadhar format
    aadhar_digits = ''.join(filter(str.isdigit, rp_data.aadhar_number))
    if len(aadhar_digits) != 12:
        raise HTTPException(
            status_code=400,
            detail="Aadhar number must be exactly 12 digits"
        )
    
    # Check for duplicate PAN
    existing = await db.referral_partners.find_one(
        {"pan_number": rp_data.pan_number.upper()},
        {"_id": 0}
    )
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Referral Partner with PAN {rp_data.pan_number} already exists"
        )
    
    # Check for duplicate Aadhar
    existing_aadhar = await db.referral_partners.find_one(
        {"aadhar_number": aadhar_digits},
        {"_id": 0}
    )
    if existing_aadhar:
        raise HTTPException(
            status_code=400,
            detail=f"Referral Partner with Aadhar {rp_data.aadhar_number} already exists"
        )
    
    # Check for duplicate email
    existing_email = await db.referral_partners.find_one(
        {"email": rp_data.email.lower()},
        {"_id": 0}
    )
    if existing_email:
        raise HTTPException(
            status_code=400,
            detail=f"Referral Partner with email {rp_data.email} already exists"
        )
    
    # STRICT RULE: RP cannot be a Client - Check by PAN
    existing_client_pan = await db.clients.find_one(
        {"pan_number": rp_data.pan_number.upper()},
        {"_id": 0, "name": 1, "pan_number": 1, "otc_ucc": 1}
    )
    if existing_client_pan:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot create RP: This PAN ({rp_data.pan_number.upper()}) belongs to an existing Client ({existing_client_pan.get('name', 'Unknown')} - {existing_client_pan.get('otc_ucc', '')}). A Client cannot be an RP."
        )
    
    # STRICT RULE: RP cannot be a Client - Check by Email
    existing_client_email = await db.clients.find_one(
        {"$or": [
            {"email": rp_data.email.lower()},
            {"email_secondary": rp_data.email.lower()},
            {"email_tertiary": rp_data.email.lower()}
        ]},
        {"_id": 0, "name": 1, "email": 1, "otc_ucc": 1}
    )
    if existing_client_email:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot create RP: This email ({rp_data.email}) belongs to an existing Client ({existing_client_email.get('name', 'Unknown')} - {existing_client_email.get('otc_ucc', '')}). A Client cannot be an RP."
        )
    
    # STRICT RULE: RP cannot be an Employee - Check by PAN
    existing_employee_pan = await db.users.find_one(
        {"pan_number": rp_data.pan_number.upper()},
        {"_id": 0, "name": 1, "email": 1}
    )
    if existing_employee_pan:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot create RP: This PAN ({rp_data.pan_number.upper()}) belongs to an existing Employee ({existing_employee_pan.get('name', 'Unknown')}). An Employee cannot be an RP."
        )
    
    # STRICT RULE: RP cannot be an Employee - Check by Email
    existing_employee_email = await db.users.find_one(
        {"email": rp_data.email.lower()},
        {"_id": 0, "name": 1, "email": 1}
    )
    if existing_employee_email:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot create RP: This email ({rp_data.email}) belongs to an existing Employee ({existing_employee_email.get('name', 'Unknown')}). An Employee cannot be an RP."
        )
    
    rp_id = str(uuid.uuid4())
    rp_code = await generate_rp_code()
    
    # PE Level users can auto-approve RPs they create
    is_pe_level_user = is_pe_level(user_role)
    
    rp_doc = {
        "id": rp_id,
        "rp_code": rp_code,
        "name": rp_data.name.strip(),
        "email": rp_data.email.lower().strip(),
        "phone": phone_digits,  # Store only digits
        "pan_number": rp_data.pan_number.upper(),
        "aadhar_number": aadhar_digits,  # Store only digits
        "address": rp_data.address.strip(),
        # Bank Details
        "bank_name": rp_data.bank_name.strip(),
        "bank_account_number": rp_data.bank_account_number.strip(),
        "bank_ifsc_code": rp_data.bank_ifsc_code.upper().strip(),
        "bank_branch": rp_data.bank_branch.strip() if rp_data.bank_branch else None,
        # Documents
        "pan_card_url": None,
        "aadhar_card_url": None,
        "cancelled_cheque_url": None,
        # Approval status - PE Level auto-approves, others need approval
        "approval_status": "approved" if is_pe_level_user else "pending",
        "approved_by": current_user["id"] if is_pe_level_user else None,
        "approved_by_name": current_user["name"] if is_pe_level_user else None,
        "approved_at": datetime.now(timezone.utc).isoformat() if is_pe_level_user else None,
        "rejection_reason": None,
        "is_active": True,
        "created_by": current_user["id"],
        "created_by_name": current_user["name"],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": None,
        "updated_by": None
    }
    
    await db.referral_partners.insert_one(rp_doc)
    
    # Create audit log
    await create_audit_log(
        action="RP_CREATE",
        entity_type="referral_partner",
        entity_id=rp_id,
        user_id=current_user["id"],
        user_name=current_user["name"],
        user_role=user_role,
        entity_name=f"{rp_data.name} ({rp_code})",
        details={"pan_number": rp_data.pan_number, "rp_code": rp_code}
    )
    
    # Send role-based notification for new partner
    try:
        from services.role_notification_service import notify_new_partner
        await notify_new_partner(
            partner_name=rp_data.name,
            partner_email=rp_data.email,
            partner_phone=phone_digits,
            exclude_user_id=current_user["id"]
        )
    except Exception as e:
        import logging
        logging.error(f"Failed to send new partner notification: {e}")
    
    return ReferralPartner(**{k: v for k, v in rp_doc.items() if k != "_id"})


@router.get("/referral-partners", response_model=List[ReferralPartner])
async def get_referral_partners(
    search: Optional[str] = None,
    active_only: bool = True,
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("referral_partners.view", "view referral partners"))
):
    """Get all referral partners."""
    query = {}
    
    if active_only:
        query["is_active"] = True
    
    if search:
        search_regex = {"$regex": search, "$options": "i"}
        query["$or"] = [
            {"name": search_regex},
            {"rp_code": search_regex},
            {"pan_number": search_regex},
            {"phone": search_regex}
        ]
    
    # CRITICAL: Add demo data isolation filter
    query = add_demo_filter(query, current_user)
    
    rps = await db.referral_partners.find(query, {"_id": 0}).sort("created_at", -1).to_list(10000)
    return [ReferralPartner(**rp) for rp in rps]


@router.get("/referral-partners/{rp_id}", response_model=ReferralPartner)
async def get_referral_partner(
    rp_id: str,
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("referral_partners.view", "view referral partner"))
):
    """Get a specific referral partner by ID."""
    rp = await db.referral_partners.find_one({"id": rp_id}, {"_id": 0})
    if not rp:
        raise HTTPException(status_code=404, detail="Referral Partner not found")
    return ReferralPartner(**rp)


@router.put("/referral-partners/{rp_id}", response_model=ReferralPartner)
async def update_referral_partner(
    rp_id: str,
    rp_data: ReferralPartnerCreate,
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("referral_partners.edit", "edit referral partners"))
):
    """
    Update a referral partner.
    Only PE Desk and PE Manager can edit RPs.
    """
    user_role = current_user.get("role", 6)
    
    existing = await db.referral_partners.find_one({"id": rp_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Referral Partner not found")
    
    # Validate 10-digit phone number (without +91)
    phone_digits = ''.join(filter(str.isdigit, rp_data.phone))
    if len(phone_digits) != 10:
        raise HTTPException(
            status_code=400,
            detail="Phone number must be exactly 10 digits (without +91)"
        )
    
    # Validate Aadhar format
    aadhar_digits = ''.join(filter(str.isdigit, rp_data.aadhar_number))
    if len(aadhar_digits) != 12:
        raise HTTPException(
            status_code=400,
            detail="Aadhar number must be exactly 12 digits"
        )
    
    # Check for duplicate PAN (if changed)
    if rp_data.pan_number.upper() != existing.get("pan_number"):
        dup_pan = await db.referral_partners.find_one(
            {"pan_number": rp_data.pan_number.upper(), "id": {"$ne": rp_id}},
            {"_id": 0}
        )
        if dup_pan:
            raise HTTPException(
                status_code=400,
                detail=f"Another RP with PAN {rp_data.pan_number} already exists"
            )
    
    # Check for duplicate email (if changed)
    if rp_data.email.lower() != existing.get("email", "").lower():
        dup_email = await db.referral_partners.find_one(
            {"email": rp_data.email.lower(), "id": {"$ne": rp_id}},
            {"_id": 0}
        )
        if dup_email:
            raise HTTPException(
                status_code=400,
                detail=f"Another RP with email {rp_data.email} already exists"
            )
    
    update_data = {
        "name": rp_data.name.strip(),
        "email": rp_data.email.lower().strip(),
        "phone": phone_digits,
        "pan_number": rp_data.pan_number.upper(),
        "aadhar_number": aadhar_digits,
        "address": rp_data.address.strip(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "updated_by": current_user["id"]
    }
    
    await db.referral_partners.update_one({"id": rp_id}, {"$set": update_data})
    
    # Create audit log
    await create_audit_log(
        action="RP_UPDATE",
        entity_type="referral_partner",
        entity_id=rp_id,
        user_id=current_user["id"],
        user_name=current_user["name"],
        user_role=user_role,
        entity_name=f"{rp_data.name} ({existing.get('rp_code')})",
        details={"changes": "Updated RP details"}
    )
    
    updated = await db.referral_partners.find_one({"id": rp_id}, {"_id": 0})
    return ReferralPartner(**updated)


@router.post("/referral-partners/{rp_id}/documents")
async def upload_rp_documents(
    rp_id: str,
    document_type: str = Form(..., description="pan_card, aadhar_card, or cancelled_cheque"),
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("referral_partners.edit", "upload referral partner documents"))
):
    """
    Upload documents for a referral partner. Stored in GridFS for persistence.
    Document types: pan_card, aadhar_card, cancelled_cheque
    """
    if document_type not in ["pan_card", "aadhar_card", "cancelled_cheque"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid document type. Use: pan_card, aadhar_card, or cancelled_cheque"
        )
    
    rp = await db.referral_partners.find_one({"id": rp_id}, {"_id": 0})
    if not rp:
        raise HTTPException(status_code=404, detail="Referral Partner not found")
    
    # Read file content
    content = await file.read()
    
    # Generate filename
    file_ext = os.path.splitext(file.filename)[1]
    filename = f"{document_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{file_ext}"
    
    # Upload to GridFS for persistent storage
    file_id = await upload_file_to_gridfs(
        content,
        filename,
        file.content_type or "application/octet-stream",
        {
            "category": "rp_documents",
            "entity_id": rp_id,
            "doc_type": document_type,
            "rp_name": rp.get("name"),
            "uploaded_by": current_user.get("id"),
            "uploaded_by_name": current_user.get("name")
        }
    )
    
    # Also save locally for backward compatibility
    upload_path = Path(UPLOAD_DIR) / "referral_partners" / rp_id
    upload_path.mkdir(parents=True, exist_ok=True)
    file_path = upload_path / filename
    
    try:
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(content)
    except Exception as e:
        print(f"Warning: Local file save failed: {e}")
    
    # Update database with GridFS URL
    url_field = f"{document_type}_url"
    file_id_field = f"{document_type}_file_id"
    gridfs_url = get_file_url(file_id)
    
    await db.referral_partners.update_one(
        {"id": rp_id},
        {"$set": {
            url_field: gridfs_url,
            file_id_field: file_id,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "updated_by": current_user["id"]
        }}
    )
    
    return {
        "message": f"{document_type.replace('_', ' ').title()} uploaded successfully",
        "url": gridfs_url,
        "file_id": file_id
    }


@router.put("/referral-partners/{rp_id}/toggle-active")
async def toggle_rp_active(
    rp_id: str,
    is_active: bool,
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("referral_partners.edit", "toggle referral partner status"))
):
    """
    Activate or deactivate a referral partner.
    Only PE Desk and PE Manager can change status.
    """
    rp = await db.referral_partners.find_one({"id": rp_id}, {"_id": 0})
    if not rp:
        raise HTTPException(status_code=404, detail="Referral Partner not found")
    
    await db.referral_partners.update_one(
        {"id": rp_id},
        {"$set": {
            "is_active": is_active,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "updated_by": current_user["id"]
        }}
    )
    
    return {"message": f"Referral Partner {'activated' if is_active else 'deactivated'} successfully"}


@router.get("/referral-partners/{rp_id}/bookings")
async def get_rp_bookings(
    rp_id: str,
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("referral_partners.view_payouts", "view referral partner bookings"))
):
    """Get all bookings associated with a referral partner."""
    rp = await db.referral_partners.find_one({"id": rp_id}, {"_id": 0})
    if not rp:
        raise HTTPException(status_code=404, detail="Referral Partner not found")
    
    bookings = await db.bookings.find(
        {"referral_partner_id": rp_id},
        {"_id": 0}
    ).sort("created_at", -1).to_list(1000)
    
    # Calculate revenue share
    total_bookings = len(bookings)
    total_revenue = 0
    total_share = 0
    
    for booking in bookings:
        if booking.get("approval_status") == "approved" and not booking.get("is_voided"):
            qty = booking.get("quantity", 0)
            selling_price = booking.get("selling_price", 0)
            buying_price = booking.get("buying_price", 0)
            profit = (selling_price - buying_price) * qty
            
            if profit > 0:
                share_percent = booking.get("rp_revenue_share_percent", 0) or 0
                share_amount = profit * (share_percent / 100)
                total_revenue += profit
                total_share += share_amount
    
    return {
        "referral_partner": rp,
        "total_bookings": total_bookings,
        "total_revenue": round(total_revenue, 2),
        "total_share": round(total_share, 2),
        "bookings": bookings
    }


@router.get("/referral-partners-pending", response_model=List[ReferralPartner])
async def get_pending_referral_partners(
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("referral_partners.approve", "view pending referral partners"))
):
    """
    Get all pending referral partners awaiting approval.
    Only PE Desk and PE Manager can view pending RPs.
    """
    rps = await db.referral_partners.find(
        {"approval_status": "pending"},
        {"_id": 0}
    ).sort("created_at", -1).to_list(10000)
    
    return [ReferralPartner(**rp) for rp in rps]


@router.get("/referral-partners-approved", response_model=List[ReferralPartner])
async def get_approved_referral_partners(
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("referral_partners.view", "view approved referral partners"))
):
    """
    Get all approved and active referral partners for booking form (requires referral_partners.view).
    Returns only RPs that can be used in bookings.
    """
    rps = await db.referral_partners.find(
        {"approval_status": "approved", "is_active": True},
        {"_id": 0}
    ).sort("name", 1).to_list(10000)
    
    return [ReferralPartner(**rp) for rp in rps]


class RPApprovalRequest(BaseModel):
    approve: bool
    rejection_reason: Optional[str] = None


@router.put("/referral-partners/{rp_id}/approve")
async def approve_referral_partner(
    rp_id: str,
    approval_data: RPApprovalRequest,
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("referral_partners.approve", "approve referral partners"))
):
    """
    Approve or reject a referral partner.
    Only PE Desk and PE Manager can approve/reject RPs.
    Sends email notification to the RP upon approval/rejection.
    """
    rp = await db.referral_partners.find_one({"id": rp_id}, {"_id": 0})
    if not rp:
        raise HTTPException(status_code=404, detail="Referral Partner not found")
    
    if rp.get("approval_status") == "approved":
        raise HTTPException(status_code=400, detail="Referral Partner is already approved")
    
    if approval_data.approve:
        # Approve the RP
        approval_timestamp = datetime.now(timezone.utc)
        update_data = {
            "approval_status": "approved",
            "approved_by": current_user["id"],
            "approved_by_name": current_user["name"],
            "approved_at": approval_timestamp.isoformat(),
            "rejection_reason": None,
            "updated_at": approval_timestamp.isoformat(),
            "updated_by": current_user["id"]
        }
        
        await db.referral_partners.update_one({"id": rp_id}, {"$set": update_data})
        
        # Send approval email notification to RP
        if rp.get("email"):
            await send_templated_email(
                "rp_approval_notification",
                rp["email"],
                {
                    "rp_name": rp["name"],
                    "rp_code": rp["rp_code"],
                    "pan_number": rp.get("pan_number", "N/A"),
                    "approved_by": current_user["name"],
                    "approval_date": approval_timestamp.strftime("%d %B %Y, %I:%M %p")
                }
            )
        
        # Create audit log
        await create_audit_log(
            action="RP_APPROVE",
            entity_type="referral_partner",
            entity_id=rp_id,
            user_id=current_user["id"],
            user_name=current_user["name"],
            user_role=current_user.get("role", 6),
            entity_name=f"{rp['name']} ({rp['rp_code']})",
            details={"action": "approved", "email_sent": bool(rp.get("email"))}
        )
        
        return {"message": f"Referral Partner {rp['rp_code']} approved successfully"}
    else:
        # Reject the RP
        if not approval_data.rejection_reason:
            raise HTTPException(status_code=400, detail="Rejection reason is required")
        
        update_data = {
            "approval_status": "rejected",
            "rejection_reason": approval_data.rejection_reason,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "updated_by": current_user["id"]
        }
        
        await db.referral_partners.update_one({"id": rp_id}, {"$set": update_data})
        
        # Send rejection email notification to RP
        if rp.get("email"):
            await send_templated_email(
                "rp_rejection_notification",
                rp["email"],
                {
                    "rp_name": rp["name"],
                    "rp_code": rp["rp_code"],
                    "pan_number": rp.get("pan_number", "N/A"),
                    "rejection_reason": approval_data.rejection_reason
                }
            )
        
        # Create audit log
        await create_audit_log(
            action="RP_REJECT",
            entity_type="referral_partner",
            entity_id=rp_id,
            user_id=current_user["id"],
            user_name=current_user["name"],
            user_role=current_user.get("role", 6),
            entity_name=f"{rp['name']} ({rp['rp_code']})",
            details={"action": "rejected", "reason": approval_data.rejection_reason, "email_sent": bool(rp.get("email"))}
        )
        
        return {"message": f"Referral Partner {rp['rp_code']} rejected"}
