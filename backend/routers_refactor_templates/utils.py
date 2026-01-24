"""
OCR and utility routes
"""
import uuid
from pathlib import Path
from datetime import datetime, timezone
from typing import List

import aiofiles
from fastapi import APIRouter, HTTPException, Depends, File, UploadFile, Form

from database import db
from config import UPLOAD_DIR, ROLES
from models import User
from utils.auth import get_current_user
from services.ocr_service import process_document_ocr

router = APIRouter(tags=["OCR & Utilities"])


@router.post("/ocr/preview")
async def ocr_preview(
    doc_type: str = Form(...),
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """Process OCR on a document without saving - for auto-fill preview"""
    temp_dir = UPLOAD_DIR / "temp"
    temp_dir.mkdir(exist_ok=True)
    
    file_ext = Path(file.filename).suffix
    temp_filename = f"temp_{uuid.uuid4()}{file_ext}"
    temp_path = temp_dir / temp_filename
    
    try:
        async with aiofiles.open(temp_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
        
        ocr_data = await process_document_ocr(str(temp_path), doc_type)
        return ocr_data
    finally:
        if temp_path.exists():
            temp_path.unlink()


@router.get("/employees", response_model=List[User])
async def get_employees(current_user: dict = Depends(get_current_user)):
    """Get list of employees for mapping"""
    users = await db.users.find({}, {"_id": 0, "password": 0}).to_list(1000)
    return [User(
        id=u["id"],
        email=u["email"],
        name=u["name"],
        role=u["role"],
        role_name=ROLES.get(u["role"], "Unknown"),
        created_at=u["created_at"]
    ) for u in users]
