"""
Business Partner Router
Handles Business Partner management, OTP login, and revenue sharing
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, UploadFile, File
from pydantic import BaseModel, EmailStr
from typing import List, Optional, Dict
from datetime import datetime, timezone, timedelta
import uuid
import secrets
import string
import os
import shutil

from database import db
from routers.auth import get_current_user, create_audit_log
from config import is_pe_level, ROLES
from services.email_service import send_templated_email, generate_otp

router = APIRouter(prefix="/business-partners", tags=["Business Partners"])

# OTP settings
BP_OTP_EXPIRY_MINUTES = 10
BP_OTP_MAX_ATTEMPTS = 5

# Upload settings
BP_UPLOAD_DIR = "/app/uploads/bp_documents"
ALLOWED_DOC_TYPES = ["pan_card", "aadhaar_card", "cancelled_cheque"]
ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

# Ensure upload directory exists
os.makedirs(BP_UPLOAD_DIR, exist_ok=True)


# ============== Models ==============

class BusinessPartnerCreate(BaseModel):
    name: str
    email: EmailStr
    phone: Optional[str] = None
    mobile: Optional[str] = None
    pan_number: Optional[str] = None
    address: Optional[str] = None
    revenue_share_percent: float  # % of revenue shared with SMIFS
    linked_employee_id: str  # Employee this BP is linked to
    notes: Optional[str] = None


class BusinessPartnerUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    mobile: Optional[str] = None
    pan_number: Optional[str] = None
    address: Optional[str] = None
    revenue_share_percent: Optional[float] = None
    linked_employee_id: Optional[str] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None


class BPDocument(BaseModel):
    doc_type: str  # pan_card, aadhaar_card, cancelled_cheque
    file_name: str
    file_url: str
    uploaded_at: str


class BusinessPartnerResponse(BaseModel):
    id: str
    name: str
    email: str
    phone: Optional[str] = None
    mobile: Optional[str] = None
    pan_number: Optional[str] = None
    address: Optional[str] = None
    revenue_share_percent: float
    linked_employee_id: str
    linked_employee_name: Optional[str] = None
    notes: Optional[str] = None
    is_active: bool = True
    documents: Optional[List[Dict]] = []
    documents_verified: bool = False
    created_at: str
    created_by: str
    created_by_name: Optional[str] = None


class BPLoginRequest(BaseModel):
    email: EmailStr


class BPOTPVerify(BaseModel):
    email: EmailStr
    otp: str


# ============== Helper Functions ==============

def generate_bp_otp() -> str:
    """Generate a 6-digit OTP"""
    return ''.join(secrets.choice(string.digits) for _ in range(6))


def check_bp_documents_complete(documents: List[Dict]) -> bool:
    """Check if all required documents are uploaded"""
    uploaded_types = {doc.get("doc_type") for doc in documents}
    return all(doc_type in uploaded_types for doc_type in ALLOWED_DOC_TYPES)


async def send_bp_otp_email(email: str, otp: str, bp_name: str):
    """Send OTP email to Business Partner"""
    html_content = f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="background: linear-gradient(135deg, #10B981 0%, #059669 100%); color: white; padding: 30px; border-radius: 16px 16px 0 0; text-align: center;">
            <h1 style="margin: 0; font-size: 24px;">🔐 Login OTP</h1>
        </div>
        <div style="background: #f9fafb; padding: 30px; border-radius: 0 0 16px 16px;">
            <p style="color: #374151; font-size: 16px;">Dear <strong>{bp_name}</strong>,</p>
            
            <p style="color: #374151; font-size: 16px;">Your One-Time Password (OTP) for Privity login is:</p>
            
            <div style="background: white; border-radius: 12px; padding: 30px; margin: 20px 0; text-align: center; border: 2px dashed #10B981;">
                <p style="font-size: 36px; font-weight: bold; letter-spacing: 8px; color: #10B981; margin: 0;">{otp}</p>
            </div>
            
            <p style="color: #6b7280; font-size: 14px;">This OTP is valid for <strong>{BP_OTP_EXPIRY_MINUTES} minutes</strong>.</p>
            <p style="color: #6b7280; font-size: 14px;">If you didn't request this OTP, please ignore this email.</p>
            
            <p style="color: #6b7280; font-size: 14px; margin-top: 30px;">Best regards,<br/><strong>SMIFS Capital Markets Ltd</strong></p>
        </div>
    </div>
    """
    
    await send_templated_email(
        to_email=email,
        subject="Your Privity Login OTP",
        html_content=html_content,
        template_key="bp_login_otp"
    )


# ============== Business Partner Management (PE Level Only) ==============

@router.post("", response_model=BusinessPartnerResponse)
async def create_business_partner(
    bp_data: BusinessPartnerCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create a new Business Partner (PE Level only)"""
    if not is_pe_level(current_user.get("role", 5)):
        raise HTTPException(status_code=403, detail="Only PE Desk or PE Manager can create Business Partners")
    
    # Check if email already exists
    existing = await db.business_partners.find_one({"email": bp_data.email.lower()})
    if existing:
        raise HTTPException(status_code=400, detail="A Business Partner with this email already exists")
    
    # Verify linked employee exists
    employee = await db.users.find_one({"id": bp_data.linked_employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=400, detail="Linked employee not found")
    
    # Validate revenue share percentage
    if bp_data.revenue_share_percent < 0 or bp_data.revenue_share_percent > 100:
        raise HTTPException(status_code=400, detail="Revenue share must be between 0 and 100")
    
    bp_id = str(uuid.uuid4())
    bp_doc = {
        "id": bp_id,
        "name": bp_data.name,
        "email": bp_data.email.lower(),
        "phone": bp_data.phone,
        "mobile": bp_data.mobile,
        "pan_number": bp_data.pan_number.upper() if bp_data.pan_number else None,
        "address": bp_data.address,
        "revenue_share_percent": bp_data.revenue_share_percent,
        "linked_employee_id": bp_data.linked_employee_id,
        "linked_employee_name": employee.get("name"),
        "notes": bp_data.notes,
        "is_active": True,
        "documents": [],  # Will be uploaded separately
        "documents_verified": False,
        "role": 8,  # Business Partner role
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": current_user["id"],
        "created_by_name": current_user["name"]
    }
    
    await db.business_partners.insert_one(bp_doc)
    
    # Create audit log
    await create_audit_log(
        action="BUSINESS_PARTNER_CREATED",
        entity_type="business_partner",
        entity_id=bp_id,
        user_id=current_user["id"],
        user_name=current_user["name"],
        user_role=current_user.get("role", 5),
        details={
            "bp_name": bp_data.name,
            "bp_email": bp_data.email,
            "revenue_share_percent": bp_data.revenue_share_percent,
            "linked_employee": employee.get("name")
        }
    )
    
    return BusinessPartnerResponse(**bp_doc)


@router.get("", response_model=List[BusinessPartnerResponse])
async def get_business_partners(
    current_user: dict = Depends(get_current_user),
    linked_employee_id: Optional[str] = None
):
    """Get all Business Partners (PE Level only)"""
    if not is_pe_level(current_user.get("role", 5)):
        raise HTTPException(status_code=403, detail="Only PE Desk or PE Manager can view Business Partners")
    
    query = {}
    if linked_employee_id:
        query["linked_employee_id"] = linked_employee_id
    
    bps = await db.business_partners.find(query, {"_id": 0}).sort("created_at", -1).to_list(10000)
    return [BusinessPartnerResponse(**bp) for bp in bps]


@router.get("/{bp_id}", response_model=BusinessPartnerResponse)
async def get_business_partner(
    bp_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get a specific Business Partner"""
    # BP can view their own profile, PE Level can view any
    bp = await db.business_partners.find_one({"id": bp_id}, {"_id": 0})
    if not bp:
        raise HTTPException(status_code=404, detail="Business Partner not found")
    
    if current_user.get("role") == 8:
        # BP can only view their own profile
        if bp["email"].lower() != current_user.get("email", "").lower():
            raise HTTPException(status_code=403, detail="You can only view your own profile")
    elif not is_pe_level(current_user.get("role", 5)):
        raise HTTPException(status_code=403, detail="Access denied")
    
    return BusinessPartnerResponse(**bp)


@router.put("/{bp_id}", response_model=BusinessPartnerResponse)
async def update_business_partner(
    bp_id: str,
    bp_data: BusinessPartnerUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update a Business Partner (PE Level only)"""
    if not is_pe_level(current_user.get("role", 5)):
        raise HTTPException(status_code=403, detail="Only PE Desk or PE Manager can update Business Partners")
    
    bp = await db.business_partners.find_one({"id": bp_id}, {"_id": 0})
    if not bp:
        raise HTTPException(status_code=404, detail="Business Partner not found")
    
    update_data = {}
    
    if bp_data.name is not None:
        update_data["name"] = bp_data.name
    if bp_data.phone is not None:
        update_data["phone"] = bp_data.phone
    if bp_data.mobile is not None:
        update_data["mobile"] = bp_data.mobile
    if bp_data.pan_number is not None:
        update_data["pan_number"] = bp_data.pan_number.upper()
    if bp_data.address is not None:
        update_data["address"] = bp_data.address
    if bp_data.notes is not None:
        update_data["notes"] = bp_data.notes
    if bp_data.is_active is not None:
        update_data["is_active"] = bp_data.is_active
    
    if bp_data.revenue_share_percent is not None:
        if bp_data.revenue_share_percent < 0 or bp_data.revenue_share_percent > 100:
            raise HTTPException(status_code=400, detail="Revenue share must be between 0 and 100")
        update_data["revenue_share_percent"] = bp_data.revenue_share_percent
    
    if bp_data.linked_employee_id is not None:
        employee = await db.users.find_one({"id": bp_data.linked_employee_id}, {"_id": 0})
        if not employee:
            raise HTTPException(status_code=400, detail="Linked employee not found")
        update_data["linked_employee_id"] = bp_data.linked_employee_id
        update_data["linked_employee_name"] = employee.get("name")
    
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    update_data["updated_by"] = current_user["id"]
    
    await db.business_partners.update_one({"id": bp_id}, {"$set": update_data})
    
    # Get updated document
    updated_bp = await db.business_partners.find_one({"id": bp_id}, {"_id": 0})
    
    # Create audit log
    await create_audit_log(
        action="BUSINESS_PARTNER_UPDATED",
        entity_type="business_partner",
        entity_id=bp_id,
        user_id=current_user["id"],
        user_name=current_user["name"],
        user_role=current_user.get("role", 5),
        details={"updated_fields": list(update_data.keys())}
    )
    
    return BusinessPartnerResponse(**updated_bp)


@router.delete("/{bp_id}")
async def delete_business_partner(
    bp_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a Business Partner (PE Desk only)"""
    if current_user.get("role", 5) != 1:
        raise HTTPException(status_code=403, detail="Only PE Desk can delete Business Partners")
    
    bp = await db.business_partners.find_one({"id": bp_id}, {"_id": 0})
    if not bp:
        raise HTTPException(status_code=404, detail="Business Partner not found")
    
    await db.business_partners.delete_one({"id": bp_id})
    
    # Create audit log
    await create_audit_log(
        action="BUSINESS_PARTNER_DELETED",
        entity_type="business_partner",
        entity_id=bp_id,
        user_id=current_user["id"],
        user_name=current_user["name"],
        user_role=current_user.get("role", 5),
        details={"bp_name": bp["name"], "bp_email": bp["email"]}
    )
    
    return {"message": "Business Partner deleted successfully"}


# ============== Document Upload Endpoints ==============

@router.post("/{bp_id}/documents/{doc_type}")
async def upload_bp_document(
    bp_id: str,
    doc_type: str,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """Upload a document for Business Partner (PE Level or self)"""
    # Check authorization - PE Level can upload for any BP, BP can upload for self
    user_role = current_user.get("role", 5)
    is_self = user_role == 8 and current_user.get("id") == bp_id
    
    if not is_pe_level(user_role) and not is_self:
        raise HTTPException(status_code=403, detail="Not authorized to upload documents")
    
    if doc_type not in ALLOWED_DOC_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid document type. Allowed: {', '.join(ALLOWED_DOC_TYPES)}")
    
    # Check file extension
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}")
    
    # Check file size
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File size exceeds 5MB limit")
    
    # Get BP
    bp = await db.business_partners.find_one({"id": bp_id}, {"_id": 0})
    if not bp:
        raise HTTPException(status_code=404, detail="Business Partner not found")
    
    # Create unique filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    new_filename = f"{bp_id}_{doc_type}_{timestamp}{file_ext}"
    file_path = os.path.join(BP_UPLOAD_DIR, new_filename)
    
    # Delete old file if exists
    existing_docs = bp.get("documents", [])
    for doc in existing_docs:
        if doc.get("doc_type") == doc_type:
            old_path = f"/app{doc.get('file_url', '')}"
            if os.path.exists(old_path):
                os.remove(old_path)
    
    # Save new file
    with open(file_path, "wb") as f:
        f.write(content)
    
    # Update documents array
    file_url = f"/uploads/bp_documents/{new_filename}"
    new_doc = {
        "doc_type": doc_type,
        "file_name": file.filename,
        "file_url": file_url,
        "uploaded_at": datetime.now(timezone.utc).isoformat()
    }
    
    # Remove old entry for this doc_type and add new one
    updated_docs = [d for d in existing_docs if d.get("doc_type") != doc_type]
    updated_docs.append(new_doc)
    
    # Check if all documents are now uploaded
    documents_verified = check_bp_documents_complete(updated_docs)
    
    await db.business_partners.update_one(
        {"id": bp_id},
        {"$set": {
            "documents": updated_docs,
            "documents_verified": documents_verified
        }}
    )
    
    return {
        "message": f"{doc_type.replace('_', ' ').title()} uploaded successfully",
        "document": new_doc,
        "documents_verified": documents_verified,
        "all_documents": updated_docs
    }


@router.delete("/{bp_id}/documents/{doc_type}")
async def delete_bp_document(
    bp_id: str,
    doc_type: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a document for Business Partner (PE Level only)"""
    if not is_pe_level(current_user.get("role", 5)):
        raise HTTPException(status_code=403, detail="Only PE Level can delete documents")
    
    bp = await db.business_partners.find_one({"id": bp_id}, {"_id": 0})
    if not bp:
        raise HTTPException(status_code=404, detail="Business Partner not found")
    
    existing_docs = bp.get("documents", [])
    doc_to_delete = None
    
    for doc in existing_docs:
        if doc.get("doc_type") == doc_type:
            doc_to_delete = doc
            break
    
    if not doc_to_delete:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Delete file
    file_path = f"/app{doc_to_delete.get('file_url', '')}"
    if os.path.exists(file_path):
        os.remove(file_path)
    
    # Update documents array
    updated_docs = [d for d in existing_docs if d.get("doc_type") != doc_type]
    documents_verified = check_bp_documents_complete(updated_docs)
    
    await db.business_partners.update_one(
        {"id": bp_id},
        {"$set": {
            "documents": updated_docs,
            "documents_verified": documents_verified
        }}
    )
    
    return {"message": "Document deleted successfully", "documents_verified": documents_verified}


@router.get("/{bp_id}/documents")
async def get_bp_documents(
    bp_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get all documents for a Business Partner"""
    user_role = current_user.get("role", 5)
    is_self = user_role == 8 and current_user.get("id") == bp_id
    
    if not is_pe_level(user_role) and not is_self:
        raise HTTPException(status_code=403, detail="Not authorized to view documents")
    
    bp = await db.business_partners.find_one({"id": bp_id}, {"_id": 0})
    if not bp:
        raise HTTPException(status_code=404, detail="Business Partner not found")
    
    return {
        "documents": bp.get("documents", []),
        "documents_verified": bp.get("documents_verified", False),
        "required_documents": ALLOWED_DOC_TYPES
    }


# ============== Business Partner OTP Login ==============

@router.post("/auth/request-otp")
async def request_bp_login_otp(data: BPLoginRequest, background_tasks: BackgroundTasks):
    """Request OTP for Business Partner login"""
    # Find Business Partner by email
    bp = await db.business_partners.find_one({"email": data.email.lower()}, {"_id": 0})
    
    if not bp:
        # Return clear error message for unregistered users
        raise HTTPException(
            status_code=404, 
            detail="You are not registered with SMSL, please write to partnersdesk@smifs.com for more query"
        )
    
    if not bp.get("is_active", True):
        raise HTTPException(status_code=403, detail="Your account has been deactivated. Please contact support.")
    
    # Check rate limiting
    recent_otps = await db.bp_otps.count_documents({
        "email": data.email.lower(),
        "created_at": {"$gte": datetime.now(timezone.utc) - timedelta(minutes=BP_OTP_EXPIRY_MINUTES)}
    })
    
    if recent_otps >= BP_OTP_MAX_ATTEMPTS:
        raise HTTPException(status_code=429, detail="Too many OTP requests. Please try again later.")
    
    # Generate OTP
    otp = generate_bp_otp()
    
    # Store OTP
    await db.bp_otps.insert_one({
        "id": str(uuid.uuid4()),
        "email": data.email.lower(),
        "bp_id": bp["id"],
        "otp": otp,
        "attempts": 0,
        "used": False,
        "created_at": datetime.now(timezone.utc),
        "expires_at": datetime.now(timezone.utc) + timedelta(minutes=BP_OTP_EXPIRY_MINUTES)
    })
    
    # Send email in background
    background_tasks.add_task(send_bp_otp_email, data.email.lower(), otp, bp["name"])
    
    return {"message": f"OTP sent to {data.email}. Valid for {BP_OTP_EXPIRY_MINUTES} minutes."}


@router.post("/auth/verify-otp")
async def verify_bp_otp(data: BPOTPVerify):
    """Verify OTP and login Business Partner"""
    from routers.auth import create_token
    
    # Find valid OTP
    otp_record = await db.bp_otps.find_one({
        "email": data.email.lower(),
        "otp": data.otp,
        "used": False,
        "expires_at": {"$gte": datetime.now(timezone.utc)}
    })
    
    if not otp_record:
        # Increment attempts for any matching unused OTP
        await db.bp_otps.update_many(
            {"email": data.email.lower(), "used": False},
            {"$inc": {"attempts": 1}}
        )
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")
    
    # Check attempts
    if otp_record.get("attempts", 0) >= BP_OTP_MAX_ATTEMPTS:
        raise HTTPException(status_code=400, detail="Too many failed attempts. Please request a new OTP.")
    
    # Mark OTP as used
    await db.bp_otps.update_one(
        {"id": otp_record["id"]},
        {"$set": {"used": True}}
    )
    
    # Get Business Partner
    bp = await db.business_partners.find_one({"id": otp_record["bp_id"]}, {"_id": 0})
    if not bp:
        raise HTTPException(status_code=404, detail="Business Partner not found")
    
    if not bp.get("is_active", True):
        raise HTTPException(status_code=403, detail="Your account has been deactivated")
    
    # Create JWT token
    token = create_token(bp["id"], bp["email"])
    
    # Update last login
    await db.business_partners.update_one(
        {"id": bp["id"]},
        {"$set": {"last_login": datetime.now(timezone.utc).isoformat()}}
    )
    
    # Create audit log
    await create_audit_log(
        action="BUSINESS_PARTNER_LOGIN",
        entity_type="business_partner",
        entity_id=bp["id"],
        user_id=bp["id"],
        user_name=bp["name"],
        user_role=8,
        details={"login_method": "OTP"}
    )
    
    return {
        "token": token,
        "user": {
            "id": bp["id"],
            "name": bp["name"],
            "email": bp["email"],
            "role": 8,
            "role_name": "Business Partner",
            "is_bp": True,
            "revenue_share_percent": bp.get("revenue_share_percent"),
            "linked_employee_name": bp.get("linked_employee_name")
        }
    }


# ============== Business Partner Dashboard Data ==============

@router.get("/dashboard/stats")
async def get_bp_dashboard_stats(current_user: dict = Depends(get_current_user)):
    """Get dashboard stats for Business Partner"""
    if current_user.get("role") != 8:
        raise HTTPException(status_code=403, detail="Access denied")
    
    bp_id = current_user.get("user_id") or current_user.get("id")
    
    # Get BP details
    bp = await db.business_partners.find_one({"id": bp_id}, {"_id": 0})
    if not bp:
        raise HTTPException(status_code=404, detail="Business Partner not found")
    
    # Get linked employee's bookings AND bookings directly made by this BP
    linked_employee_id = bp.get("linked_employee_id")
    
    # Query bookings: created by linked employee OR created by BP OR where BP is tagged
    bookings = await db.bookings.find({
        "$or": [
            {"created_by": linked_employee_id},
            {"business_partner_id": bp_id},
            {"created_by": bp_id}
        ]
    }, {"_id": 0}).to_list(10000)
    
    # Remove duplicates (by booking id)
    seen_ids = set()
    unique_bookings = []
    for b in bookings:
        if b.get("id") not in seen_ids:
            seen_ids.add(b.get("id"))
            unique_bookings.append(b)
    bookings = unique_bookings
    
    # Calculate statistics
    total_bookings = len(bookings)
    completed_bookings = len([b for b in bookings if b.get("status") == "completed"])
    
    # For BP bookings, use the bp_revenue_share_percent from the booking itself
    # For linked employee bookings, use BP's default share
    total_revenue = 0
    bp_share_total = 0
    
    for b in bookings:
        if b.get("status") == "completed":
            profit = (b.get("selling_price", 0) - b.get("buying_price", 0)) * b.get("quantity", 0)
            total_revenue += profit
            
            # Check if this is a direct BP booking
            if b.get("is_bp_booking") and b.get("business_partner_id") == bp_id:
                bp_share_total += profit * (b.get("bp_revenue_share_percent", 0) / 100)
            else:
                # Use default BP share for linked employee bookings
                bp_share_total += profit * (bp.get("revenue_share_percent", 0) / 100)
    
    smifs_share = total_revenue - bp_share_total
    
    return {
        "bp_name": bp["name"],
        "linked_employee_name": bp.get("linked_employee_name"),
        "revenue_share_percent": bp.get("revenue_share_percent", 0),
        "total_bookings": total_bookings,
        "completed_bookings": completed_bookings,
        "total_revenue": round(total_revenue, 2),
        "bp_share": round(bp_share_total, 2),
        "smifs_share": round(smifs_share, 2),
        "documents_verified": bp.get("documents_verified", False)
    }


@router.get("/dashboard/bookings")
async def get_bp_bookings(
    current_user: dict = Depends(get_current_user),
    status: Optional[str] = None,
    limit: int = 50
):
    """Get bookings for Business Partner's linked employee and direct BP bookings"""
    if current_user.get("role") != 8:
        raise HTTPException(status_code=403, detail="Access denied")
    
    bp_id = current_user.get("user_id") or current_user.get("id")
    
    bp = await db.business_partners.find_one({"id": bp_id}, {"_id": 0})
    if not bp:
        raise HTTPException(status_code=404, detail="Business Partner not found")
    
    linked_employee_id = bp.get("linked_employee_id")
    
    # Query: created by linked employee OR created by BP OR where BP is tagged
    query = {
        "$or": [
            {"created_by": linked_employee_id},
            {"business_partner_id": bp_id},
            {"created_by": bp_id}
        ]
    }
    if status:
        query["status"] = status
    
    bookings = await db.bookings.find(query, {"_id": 0}).sort("created_at", -1).limit(limit * 2).to_list(limit * 2)
    
    # Remove duplicates and limit
    seen_ids = set()
    unique_bookings = []
    for b in bookings:
        if b.get("id") not in seen_ids:
            seen_ids.add(b.get("id"))
            unique_bookings.append(b)
            if len(unique_bookings) >= limit:
                break
    
    # Calculate BP share for each booking
    result = []
    for b in unique_bookings:
        profit = (b.get("selling_price", 0) - b.get("buying_price", 0)) * b.get("quantity", 0)
        
        # Determine BP share based on booking type
        if b.get("is_bp_booking") and b.get("business_partner_id") == bp_id:
            bp_share = profit * (b.get("bp_revenue_share_percent", 0) / 100) if b.get("status") == "completed" else 0
        else:
            bp_share = profit * (bp.get("revenue_share_percent", 0) / 100) if b.get("status") == "completed" else 0
        
        # Get client and stock names if not present
        client_name = b.get("client_name")
        stock_symbol = b.get("stock_symbol")
        
        if not client_name:
            client = await db.clients.find_one({"id": b.get("client_id")}, {"_id": 0, "name": 1})
            client_name = client.get("name") if client else "Unknown"
        
        if not stock_symbol:
            stock = await db.stocks.find_one({"id": b.get("stock_id")}, {"_id": 0, "symbol": 1})
            stock_symbol = stock.get("symbol") if stock else "Unknown"
        
        result.append({
            **b,
            "client_name": client_name,
            "stock_symbol": stock_symbol,
            "profit": round(profit, 2),
            "bp_share": round(bp_share, 2),
            "is_direct_bp_booking": b.get("is_bp_booking", False) and b.get("business_partner_id") == bp_id
        })
    
    return result
