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
    # Document URLs
    cml_cdsl_url: Optional[str] = None
    cml_nsdl_url: Optional[str] = None
    cancelled_cheque_url: Optional[str] = None
    pan_card_url: Optional[str] = None
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
        # Create default record
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
            "cml_cdsl_url": None,
            "cml_nsdl_url": None,
            "cancelled_cheque_url": None,
            "pan_card_url": None,
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
        cml_cdsl_url=master.get("cml_cdsl_url"),
        cml_nsdl_url=master.get("cml_nsdl_url"),
        cancelled_cheque_url=master.get("cancelled_cheque_url"),
        pan_card_url=master.get("pan_card_url"),
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
    Upload company document (PE Desk only)
    
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
    
    # Generate unique filename
    filename = f"{document_type}_{uuid.uuid4().hex[:8]}{file_ext}"
    file_path = os.path.join(UPLOAD_DIR, filename)
    
    # Save file
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
    
    # Generate URL
    file_url = f"/uploads/company/{filename}"
    
    # Update database
    url_field = f"{document_type}_url"
    await db.company_master.update_one(
        {"_id": "company_settings"},
        {
            "$set": {
                url_field: file_url,
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
