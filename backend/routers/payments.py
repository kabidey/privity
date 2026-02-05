"""
Payments Router - Handles payment proof uploads and payment-related operations
"""
from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from typing import Optional
from datetime import datetime, timezone
import uuid
import os
from pathlib import Path

from database import db
from utils.auth import get_current_user
from services.file_storage import upload_file_to_gridfs, get_file_url
from services.permission_service import require_permission

router = APIRouter(prefix="/payments", tags=["Payments"])

# Allowed file types for payment proofs
ALLOWED_EXTENSIONS = {'.pdf', '.jpg', '.jpeg', '.png', '.gif', '.webp'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


@router.post("/upload-proof")
async def upload_payment_proof(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("bookings.record_payment", "upload payment proof"))
):
    """
    Upload a payment proof document.
    Returns the URL that can be used when recording a payment.
    """
    # Validate file extension
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # Read file content
    content = await file.read()
    
    # Validate file size
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)}MB"
        )
    
    # Generate unique filename
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    unique_id = str(uuid.uuid4())[:8]
    safe_filename = f"payment_proof_{timestamp}_{unique_id}{file_ext}"
    
    try:
        # Upload to GridFS
        file_id = await upload_file_to_gridfs(
            file_content=content,
            filename=safe_filename,
            content_type=file.content_type or "application/octet-stream",
            metadata={
                "category": "payment_proofs",
                "uploaded_by": current_user["id"],
                "uploaded_by_name": current_user["name"],
                "original_filename": file.filename,
                "uploaded_at": datetime.now(timezone.utc).isoformat()
            }
        )
        
        # Get the URL for the uploaded file
        file_url = get_file_url(file_id)
        
        return {
            "success": True,
            "url": file_url,
            "file_id": file_id,
            "filename": safe_filename,
            "message": "Payment proof uploaded successfully"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload payment proof: {str(e)}"
        )


@router.post("/vendor/upload-proof")
async def upload_vendor_payment_proof(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("purchases.record_payment", "upload vendor payment proof"))
):
    """
    Upload a vendor payment proof document.
    Returns the URL that can be used when recording a vendor payment.
    """
    # Validate file extension
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # Read file content
    content = await file.read()
    
    # Validate file size
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)}MB"
        )
    
    # Generate unique filename
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    unique_id = str(uuid.uuid4())[:8]
    safe_filename = f"vendor_payment_proof_{timestamp}_{unique_id}{file_ext}"
    
    try:
        # Upload to GridFS
        file_id = await upload_file_to_gridfs(
            file_content=content,
            filename=safe_filename,
            content_type=file.content_type or "application/octet-stream",
            metadata={
                "category": "vendor_payment_proofs",
                "uploaded_by": current_user["id"],
                "uploaded_by_name": current_user["name"],
                "original_filename": file.filename,
                "uploaded_at": datetime.now(timezone.utc).isoformat()
            }
        )
        
        # Get the URL for the uploaded file
        file_url = get_file_url(file_id)
        
        return {
            "success": True,
            "url": file_url,
            "file_id": file_id,
            "filename": safe_filename,
            "message": "Vendor payment proof uploaded successfully"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload vendor payment proof: {str(e)}"
        )
