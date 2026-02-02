"""
Company Master Router
Handles company master settings - PE Desk only access
"""
import os
import uuid
import shutil
from typing import Optional
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from pydantic import BaseModel

from database import db
from utils.auth import get_current_user
from services.audit_service import create_audit_log
from services.file_storage import upload_file_to_gridfs, get_file_url

router = APIRouter(prefix="/company-master", tags=["Company Master"])

UPLOAD_DIR = "/app/uploads/company"
os.makedirs(UPLOAD_DIR, exist_ok=True)


class CompanyMasterCreate(BaseModel):
    company_name: Optional[str] = None
    company_address: Optional[str] = None
    company_cin: Optional[str] = None
    company_gst: Optional[str] = None
    company_pan: Optional[str] = None
    cdsl_dp_id: Optional[str] = None
    nsdl_dp_id: Optional[str] = None
    company_tan: Optional[str] = None
    company_bank_name: Optional[str] = None
    company_bank_account: Optional[str] = None
    company_bank_ifsc: Optional[str] = None
    company_bank_branch: Optional[str] = None
    user_agreement_text: Optional[str] = None


class CompanyMasterResponse(BaseModel):
    id: str
    company_name: Optional[str] = None
    company_address: Optional[str] = None
    company_cin: Optional[str] = None
    company_gst: Optional[str] = None
    company_pan: Optional[str] = None
    cdsl_dp_id: Optional[str] = None
    nsdl_dp_id: Optional[str] = None
    company_tan: Optional[str] = None
    company_bank_name: Optional[str] = None
    company_bank_account: Optional[str] = None
    company_bank_ifsc: Optional[str] = None
    company_bank_branch: Optional[str] = None
    # Logo
    logo_url: Optional[str] = None
    # Document URLs
    cml_cdsl_url: Optional[str] = None
    cml_nsdl_url: Optional[str] = None
    cancelled_cheque_url: Optional[str] = None
    pan_card_url: Optional[str] = None
    # User Agreement
    user_agreement_text: Optional[str] = None
    # Metadata
    updated_at: Optional[str] = None
    updated_by: Optional[str] = None


def check_pe_desk(current_user: dict):
    """Verify user is PE Desk (role 1)"""
    if current_user.get("role") != 1:
        raise HTTPException(
            status_code=403, 
            detail="Only PE Desk can access Company Master settings"
        )


@router.get("", response_model=CompanyMasterResponse)
async def get_company_master(current_user: dict = Depends(get_current_user)):
    """Get company master settings (PE Desk only)"""
    check_pe_desk(current_user)
    
    # Get or create company master record
    master = await db.company_master.find_one({"_id": "company_settings"})
    
    if not master:
        # Create default record with default user agreement
        default_agreement = """TERMS OF USE AND USER AGREEMENT

By accessing and using the PRIVITY Share Booking System, you agree to the following terms and conditions:

1. CONFIDENTIALITY
You agree to maintain the confidentiality of all information accessed through this system. Client data, transaction details, and business information must not be shared with unauthorized parties.

2. AUTHORIZED USE
This system is intended solely for authorized business purposes. You agree not to use the system for any illegal or unauthorized activities.

3. DATA ACCURACY
You are responsible for ensuring the accuracy of all data you enter into the system. Any errors should be reported and corrected immediately.

4. SECURITY
You agree to keep your login credentials secure and not share them with anyone. Report any suspected security breaches immediately.

5. COMPLIANCE
You agree to comply with all applicable laws, regulations, and company policies while using this system.

6. MONITORING
You acknowledge that your activities on this system may be monitored and logged for security and audit purposes.

7. TERMINATION
The company reserves the right to terminate your access to the system at any time for violation of these terms.

By clicking "I Agree", you confirm that you have read, understood, and agree to be bound by these terms and conditions."""
        
        master = {
            "_id": "company_settings",
            "id": "company_settings",
            "company_name": "",
            "company_address": "",
            "company_cin": "",
            "company_gst": "",
            "company_pan": "",
            "cdsl_dp_id": "",
            "nsdl_dp_id": "",
            "company_tan": "",
            "company_bank_name": "",
            "company_bank_account": "",
            "company_bank_ifsc": "",
            "company_bank_branch": "",
            "logo_url": None,
            "cml_cdsl_url": None,
            "cml_nsdl_url": None,
            "cancelled_cheque_url": None,
            "pan_card_url": None,
            "user_agreement_text": default_agreement,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "updated_by": current_user["name"]
        }
        await db.company_master.insert_one(master)
    
    return CompanyMasterResponse(
        id=master.get("id", "company_settings"),
        company_name=master.get("company_name"),
        company_address=master.get("company_address"),
        company_cin=master.get("company_cin"),
        company_gst=master.get("company_gst"),
        company_pan=master.get("company_pan"),
        cdsl_dp_id=master.get("cdsl_dp_id"),
        nsdl_dp_id=master.get("nsdl_dp_id"),
        company_tan=master.get("company_tan"),
        company_bank_name=master.get("company_bank_name"),
        company_bank_account=master.get("company_bank_account"),
        company_bank_ifsc=master.get("company_bank_ifsc"),
        company_bank_branch=master.get("company_bank_branch"),
        logo_url=master.get("logo_url"),
        cml_cdsl_url=master.get("cml_cdsl_url"),
        cml_nsdl_url=master.get("cml_nsdl_url"),
        cancelled_cheque_url=master.get("cancelled_cheque_url"),
        pan_card_url=master.get("pan_card_url"),
        user_agreement_text=master.get("user_agreement_text"),
        updated_at=master.get("updated_at"),
        updated_by=master.get("updated_by")
    )


@router.put("", response_model=CompanyMasterResponse)
async def update_company_master(
    data: CompanyMasterCreate,
    current_user: dict = Depends(get_current_user)
):
    """Update company master settings (PE Desk only)"""
    check_pe_desk(current_user)
    
    update_data = {
        "company_name": data.company_name,
        "company_address": data.company_address,
        "company_cin": data.company_cin,
        "company_gst": data.company_gst,
        "company_pan": data.company_pan.upper() if data.company_pan else None,
        "cdsl_dp_id": data.cdsl_dp_id,
        "nsdl_dp_id": data.nsdl_dp_id,
        "company_tan": data.company_tan.upper() if data.company_tan else None,
        "company_bank_name": data.company_bank_name,
        "company_bank_account": data.company_bank_account,
        "company_bank_ifsc": data.company_bank_ifsc.upper() if data.company_bank_ifsc else None,
        "company_bank_branch": data.company_bank_branch,
        "user_agreement_text": data.user_agreement_text,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "updated_by": current_user["name"]
    }
    
    # Upsert the record
    await db.company_master.update_one(
        {"_id": "company_settings"},
        {"$set": update_data},
        upsert=True
    )
    
    # Create audit log
    await create_audit_log(
        action="COMPANY_MASTER_UPDATE",
        entity_type="company_master",
        entity_id="company_settings",
        user_id=current_user["id"],
        user_name=current_user["name"],
        user_role=current_user.get("role", 1),
        entity_name="Company Master Settings",
        details={"updated_fields": list(update_data.keys())}
    )
    
    # Fetch updated record
    return await get_company_master(current_user)


@router.post("/upload/{document_type}")
async def upload_company_document(
    document_type: str,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Upload company document (PE Desk only) - Stored in GridFS for persistence
    
    document_type: cml_cdsl, cml_nsdl, cancelled_cheque, pan_card
    """
    check_pe_desk(current_user)
    
    valid_types = ["cml_cdsl", "cml_nsdl", "cancelled_cheque", "pan_card"]
    if document_type not in valid_types:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid document type. Must be one of: {', '.join(valid_types)}"
        )
    
    # Validate file type
    allowed_extensions = [".pdf", ".jpg", ".jpeg", ".png"]
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(allowed_extensions)}"
        )
    
    # Read file content
    content = await file.read()
    
    # Generate unique filename
    filename = f"{document_type}_{uuid.uuid4().hex[:8]}{file_ext}"
    
    # Upload to GridFS for persistent storage
    file_id = await upload_file_to_gridfs(
        content,
        filename,
        file.content_type or "application/octet-stream",
        {
            "category": "company_documents",
            "doc_type": document_type,
            "uploaded_by": current_user.get("id"),
            "uploaded_by_name": current_user.get("name")
        }
    )
    
    # Generate URL using GridFS
    file_url = get_file_url(file_id)
    
    # Also save locally for backward compatibility
    file_path = os.path.join(UPLOAD_DIR, filename)
    try:
        with open(file_path, "wb") as buffer:
            buffer.write(content)
    except Exception as e:
        print(f"Warning: Local file save failed: {e}")
    
    # Update database with GridFS file_id and URL
    url_field = f"{document_type}_url"
    file_id_field = f"{document_type}_file_id"
    await db.company_master.update_one(
        {"_id": "company_settings"},
        {
            "$set": {
                url_field: file_url,
                file_id_field: file_id,
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "updated_by": current_user["name"]
            }
        },
        upsert=True
    )
    
    # Create audit log
    await create_audit_log(
        action="COMPANY_DOCUMENT_UPLOAD",
        entity_type="company_master",
        entity_id="company_settings",
        user_id=current_user["id"],
        user_name=current_user["name"],
        user_role=current_user.get("role", 1),
        entity_name="Company Master Settings",
        details={"document_type": document_type, "filename": filename}
    )
    
    return {
        "message": f"{document_type.replace('_', ' ').title()} uploaded successfully",
        "url": file_url,
        "filename": filename
    }


@router.post("/upload-logo")
async def upload_company_logo(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Upload company logo (PE Desk only)
    Supports PNG, JPG, JPEG, SVG, WEBP formats
    """
    check_pe_desk(current_user)
    
    # Validate file type - images only
    allowed_extensions = [".png", ".jpg", ".jpeg", ".svg", ".webp"]
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(allowed_extensions)}"
        )
    
    # Validate file size (max 5MB for logo)
    file_content = await file.read()
    if len(file_content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Logo file size must be less than 5MB")
    
    # Get current logo to delete old file
    master = await db.company_master.find_one({"_id": "company_settings"})
    if master and master.get("logo_url"):
        old_logo_path = f"/app{master.get('logo_url')}"
        if os.path.exists(old_logo_path):
            try:
                os.remove(old_logo_path)
            except Exception:
                pass
    
    # Generate unique filename
    filename = f"company_logo_{uuid.uuid4().hex[:8]}{file_ext}"
    file_path = os.path.join(UPLOAD_DIR, filename)
    
    # Save file
    try:
        with open(file_path, "wb") as buffer:
            buffer.write(file_content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save logo: {str(e)}")
    
    # Generate URL
    file_url = f"/uploads/company/{filename}"
    
    # Update database
    await db.company_master.update_one(
        {"_id": "company_settings"},
        {
            "$set": {
                "logo_url": file_url,
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "updated_by": current_user["name"]
            }
        },
        upsert=True
    )
    
    # Create audit log
    await create_audit_log(
        action="COMPANY_LOGO_UPLOAD",
        entity_type="company_master",
        entity_id="company_settings",
        user_id=current_user["id"],
        user_name=current_user["name"],
        user_role=current_user.get("role", 1),
        entity_name="Company Master Settings",
        details={"filename": filename}
    )
    
    return {
        "message": "Company logo uploaded successfully",
        "url": file_url,
        "filename": filename
    }


@router.delete("/logo")
async def delete_company_logo(
    current_user: dict = Depends(get_current_user)
):
    """Delete company logo (PE Desk only)"""
    check_pe_desk(current_user)
    
    # Get current logo
    master = await db.company_master.find_one({"_id": "company_settings"})
    if not master:
        raise HTTPException(status_code=404, detail="Company master not found")
    
    current_logo = master.get("logo_url")
    
    if current_logo:
        # Try to delete the file
        file_path = f"/app{current_logo}"
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass
    
    # Clear the URL in database
    await db.company_master.update_one(
        {"_id": "company_settings"},
        {
            "$set": {
                "logo_url": None,
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "updated_by": current_user["name"]
            }
        }
    )
    
    # Create audit log
    await create_audit_log(
        action="COMPANY_LOGO_DELETE",
        entity_type="company_master",
        entity_id="company_settings",
        user_id=current_user["id"],
        user_name=current_user["name"],
        user_role=current_user.get("role", 1),
        entity_name="Company Master Settings",
        details={}
    )
    
    return {"message": "Company logo deleted successfully"}


@router.delete("/document/{document_type}")
async def delete_company_document(
    document_type: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete company document (PE Desk only)"""
    check_pe_desk(current_user)
    
    valid_types = ["cml_cdsl", "cml_nsdl", "cancelled_cheque", "pan_card"]
    if document_type not in valid_types:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid document type. Must be one of: {', '.join(valid_types)}"
        )
    
    # Get current document URL
    master = await db.company_master.find_one({"_id": "company_settings"})
    if not master:
        raise HTTPException(status_code=404, detail="Company master not found")
    
    url_field = f"{document_type}_url"
    current_url = master.get(url_field)
    
    if current_url:
        # Try to delete the file
        file_path = f"/app{current_url}"
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass  # File may not exist, continue anyway
    
    # Clear the URL in database
    await db.company_master.update_one(
        {"_id": "company_settings"},
        {
            "$set": {
                url_field: None,
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "updated_by": current_user["name"]
            }
        }
    )
    
    # Create audit log
    await create_audit_log(
        action="COMPANY_DOCUMENT_DELETE",
        entity_type="company_master",
        entity_id="company_settings",
        user_id=current_user["id"],
        user_name=current_user["name"],
        user_role=current_user.get("role", 1),
        entity_name="Company Master Settings",
        details={"document_type": document_type}
    )
    
    return {"message": f"{document_type.replace('_', ' ').title()} deleted successfully"}



# ============== Public Endpoint for User Agreement ==============
@router.get("/user-agreement")
async def get_user_agreement():
    """
    Get user agreement text (public - no auth required)
    Used to show agreement to users on first login
    """
    master = await db.company_master.find_one({"_id": "company_settings"})
    
    default_agreement = """TERMS OF USE AND USER AGREEMENT

By accessing and using the PRIVITY Share Booking System, you agree to the following terms and conditions:

1. CONFIDENTIALITY
You agree to maintain the confidentiality of all information accessed through this system.

2. AUTHORIZED USE
This system is intended solely for authorized business purposes.

3. COMPLIANCE
You agree to comply with all applicable laws, regulations, and company policies.

By clicking "I Agree", you confirm that you have read, understood, and agree to these terms."""
    
    if not master:
        return {"user_agreement_text": default_agreement}
    
    return {"user_agreement_text": master.get("user_agreement_text") or default_agreement}


@router.post("/accept-agreement")
async def accept_user_agreement(current_user: dict = Depends(get_current_user)):
    """
    Accept user agreement - marks user as having accepted the agreement
    """
    await db.users.update_one(
        {"id": current_user["id"]},
        {
            "$set": {
                "agreement_accepted": True,
                "agreement_accepted_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    # Create audit log
    await create_audit_log(
        action="USER_AGREEMENT_ACCEPTED",
        entity_type="user",
        entity_id=current_user["id"],
        user_id=current_user["id"],
        user_name=current_user["name"],
        user_role=current_user.get("role", 5),
        entity_name=current_user["name"],
        details={"action": "User accepted terms and conditions"}
    )
    
    return {"message": "Agreement accepted successfully", "agreement_accepted": True}


@router.post("/decline-agreement")
async def decline_user_agreement(current_user: dict = Depends(get_current_user)):
    """
    Decline user agreement - marks user as having declined and logs out
    """
    await db.users.update_one(
        {"id": current_user["id"]},
        {
            "$set": {
                "agreement_accepted": False,
                "agreement_declined_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    # Create audit log
    await create_audit_log(
        action="USER_AGREEMENT_DECLINED",
        entity_type="user",
        entity_id=current_user["id"],
        user_id=current_user["id"],
        user_name=current_user["name"],
        user_role=current_user.get("role", 5),
        entity_name=current_user["name"],
        details={"action": "User declined terms and conditions"}
    )
    
    return {"message": "Agreement declined. You will be logged out.", "agreement_accepted": False}
