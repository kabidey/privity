"""
Referral Partners Router

Handles all referral partner (RP) management operations.
- Employees can CREATE RPs
- PE Desk and PE Manager can EDIT RPs
"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from typing import List, Optional
from datetime import datetime, timezone
import uuid
import os
import aiofiles
from pathlib import Path

from database import db
from config import is_pe_level, UPLOAD_DIR
from models import ReferralPartnerCreate, ReferralPartner
from utils.auth import get_current_user
from services.audit_service import create_audit_log

router = APIRouter(tags=["Referral Partners"])


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
    current_user: dict = Depends(get_current_user)
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
    
    rp_id = str(uuid.uuid4())
    rp_code = await generate_rp_code()
    
    rp_doc = {
        "id": rp_id,
        "rp_code": rp_code,
        "name": rp_data.name.strip(),
        "email": rp_data.email.lower().strip(),
        "phone": phone_digits,  # Store only digits
        "pan_number": rp_data.pan_number.upper(),
        "aadhar_number": aadhar_digits,  # Store only digits
        "address": rp_data.address.strip(),
        "pan_card_url": None,
        "aadhar_card_url": None,
        "cancelled_cheque_url": None,
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
    
    return ReferralPartner(**{k: v for k, v in rp_doc.items() if k != "_id"})


@router.get("/referral-partners", response_model=List[ReferralPartner])
async def get_referral_partners(
    search: Optional[str] = None,
    active_only: bool = True,
    current_user: dict = Depends(get_current_user)
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
    
    rps = await db.referral_partners.find(query, {"_id": 0}).sort("created_at", -1).to_list(10000)
    return [ReferralPartner(**rp) for rp in rps]


@router.get("/referral-partners/{rp_id}", response_model=ReferralPartner)
async def get_referral_partner(rp_id: str, current_user: dict = Depends(get_current_user)):
    """Get a specific referral partner by ID."""
    rp = await db.referral_partners.find_one({"id": rp_id}, {"_id": 0})
    if not rp:
        raise HTTPException(status_code=404, detail="Referral Partner not found")
    return ReferralPartner(**rp)


@router.put("/referral-partners/{rp_id}", response_model=ReferralPartner)
async def update_referral_partner(
    rp_id: str,
    rp_data: ReferralPartnerCreate,
    current_user: dict = Depends(get_current_user)
):
    """
    Update a referral partner.
    Only PE Desk and PE Manager can edit RPs.
    """
    user_role = current_user.get("role", 6)
    
    # Only PE Level can edit
    if not is_pe_level(user_role):
        raise HTTPException(
            status_code=403,
            detail="Only PE Desk or PE Manager can edit Referral Partners"
        )
    
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
    current_user: dict = Depends(get_current_user)
):
    """
    Upload documents for a referral partner.
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
    
    # Create upload directory
    upload_path = Path(UPLOAD_DIR) / "referral_partners" / rp_id
    upload_path.mkdir(parents=True, exist_ok=True)
    
    # Generate filename
    file_ext = os.path.splitext(file.filename)[1]
    filename = f"{document_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{file_ext}"
    file_path = upload_path / filename
    
    # Save file
    async with aiofiles.open(file_path, "wb") as f:
        content = await file.read()
        await f.write(content)
    
    # Update database
    url_field = f"{document_type}_url"
    relative_path = f"/uploads/referral_partners/{rp_id}/{filename}"
    
    await db.referral_partners.update_one(
        {"id": rp_id},
        {"$set": {
            url_field: relative_path,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "updated_by": current_user["id"]
        }}
    )
    
    return {
        "message": f"{document_type.replace('_', ' ').title()} uploaded successfully",
        "url": relative_path
    }


@router.put("/referral-partners/{rp_id}/toggle-active")
async def toggle_rp_active(
    rp_id: str,
    is_active: bool,
    current_user: dict = Depends(get_current_user)
):
    """
    Activate or deactivate a referral partner.
    Only PE Desk and PE Manager can change status.
    """
    user_role = current_user.get("role", 6)
    
    if not is_pe_level(user_role):
        raise HTTPException(
            status_code=403,
            detail="Only PE Desk or PE Manager can change RP status"
        )
    
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
    current_user: dict = Depends(get_current_user)
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
