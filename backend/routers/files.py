"""
File Router - Serves files from GridFS and handles uploads
"""
from fastapi import APIRouter, HTTPException, UploadFile, File, Depends, Query
from fastapi.responses import StreamingResponse, Response
from typing import Optional, List
import io
from database import db
from utils.auth import get_current_user
from services.file_storage import (
    upload_file_to_gridfs,
    download_file_from_gridfs,
    delete_file_from_gridfs,
    get_file_metadata,
    list_files_by_category,
    get_file_url
)
from services.permission_service import (
    has_permission,
    check_permission as check_dynamic_permission,
    require_permission
)

router = APIRouter(prefix="/files", tags=["files"])


# Helper function for backward compatibility
def is_pe_level(role: int) -> bool:
    """Check if role is PE level (PE Desk or PE Manager)."""
    return role in [1, 2]


# ============== Static routes (must come before dynamic /{file_id} routes) ==============

@router.get("/storage-stats")
async def get_file_stats(
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("files.view_stats", "view file storage stats"))
):
    """
    Get file storage statistics (PE Desk/Manager only).
    """
    # Count files in GridFS
    total_files = await db.fs.files.count_documents({})
    
    # Get total size
    pipeline = [
        {"$group": {"_id": None, "total_size": {"$sum": "$length"}}}
    ]
    size_result = await db.fs.files.aggregate(pipeline).to_list(1)
    total_size = size_result[0]["total_size"] if size_result else 0
    
    # Count by category
    category_pipeline = [
        {"$group": {"_id": "$metadata.category", "count": {"$sum": 1}, "size": {"$sum": "$length"}}}
    ]
    categories = await db.fs.files.aggregate(category_pipeline).to_list(100)
    
    return {
        "total_files": total_files,
        "total_size_bytes": total_size,
        "total_size_mb": round(total_size / (1024 * 1024), 2),
        "by_category": [
            {
                "category": c["_id"] or "uncategorized",
                "count": c["count"],
                "size_mb": round(c["size"] / (1024 * 1024), 2)
            }
            for c in categories
        ]
    }


@router.get("/scan-missing")
async def scan_missing_files_legacy(
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("files.scan", "scan for missing files"))
):
    """
    Scan database for references to files that are not in GridFS (requires files.scan permission).
    Returns a list of entities with missing files that need re-upload.
    """
    
    missing_files = []
    
    # Scan clients for missing documents
    async for client in db.clients.find({"documents": {"$exists": True, "$ne": []}}, {"_id": 0}):
        for doc in client.get("documents", []):
            file_id = doc.get("file_id")
            if file_id:
                metadata = await get_file_metadata(file_id)
                if not metadata:
                    missing_files.append({
                        "entity_type": "client",
                        "entity_id": client.get("id"),
                        "entity_name": client.get("name"),
                        "doc_type": doc.get("doc_type"),
                        "file_id": file_id,
                        "original_filename": doc.get("filename")
                    })
            elif doc.get("file_path") and not doc.get("file_id"):
                # Old document without GridFS - needs migration
                missing_files.append({
                    "entity_type": "client",
                    "entity_id": client.get("id"),
                    "entity_name": client.get("name"),
                    "doc_type": doc.get("doc_type"),
                    "file_id": None,
                    "original_filename": doc.get("filename"),
                    "needs_migration": True
                })
    
    # Scan company master for missing documents
    company = await db.company_master.find_one({"_id": "company_settings"})
    if company:
        doc_fields = ["logo", "cml_cdsl", "cml_nsdl", "cancelled_cheque", "pan_card"]
        for field in doc_fields:
            file_id = company.get(f"{field}_file_id")
            if file_id:
                metadata = await get_file_metadata(file_id)
                if not metadata:
                    missing_files.append({
                        "entity_type": "company_master",
                        "entity_id": "company_settings",
                        "entity_name": "Company Master",
                        "doc_type": field,
                        "file_id": file_id
                    })
    
    # Scan referral partners for missing documents
    async for rp in db.referral_partners.find({}, {"_id": 0}):
        doc_fields = ["pan_card", "aadhar_card", "cancelled_cheque"]
        for field in doc_fields:
            file_id = rp.get(f"{field}_file_id")
            if file_id:
                metadata = await get_file_metadata(file_id)
                if not metadata:
                    missing_files.append({
                        "entity_type": "referral_partner",
                        "entity_id": rp.get("id"),
                        "entity_name": rp.get("name"),
                        "doc_type": field,
                        "file_id": file_id
                    })
    
    # Scan business partners for missing documents
    async for bp in db.business_partners.find({"documents": {"$exists": True, "$ne": []}}, {"_id": 0}):
        for doc in bp.get("documents", []):
            file_id = doc.get("file_id")
            if file_id:
                metadata = await get_file_metadata(file_id)
                if not metadata:
                    missing_files.append({
                        "entity_type": "business_partner",
                        "entity_id": bp.get("id"),
                        "entity_name": bp.get("name"),
                        "doc_type": doc.get("doc_type"),
                        "file_id": file_id
                    })
    
    # Scan research reports for missing files
    async for report in db.research_reports.find({"file_id": {"$exists": True}}, {"_id": 0}):
        file_id = report.get("file_id")
        if file_id:
            metadata = await get_file_metadata(file_id)
            if not metadata:
                missing_files.append({
                    "entity_type": "research_report",
                    "entity_id": report.get("id"),
                    "entity_name": report.get("title"),
                    "doc_type": "research_report",
                    "file_id": file_id,
                    "original_filename": report.get("file_name")
                })
    
    # Scan contract notes for missing PDFs
    async for cn in db.contract_notes.find({"file_id": {"$exists": True}}, {"_id": 0}):
        file_id = cn.get("file_id")
        if file_id:
            metadata = await get_file_metadata(file_id)
            if not metadata:
                missing_files.append({
                    "entity_type": "contract_note",
                    "entity_id": cn.get("id"),
                    "entity_name": cn.get("contract_note_number"),
                    "doc_type": "contract_note_pdf",
                    "file_id": file_id
                })
    
    return {
        "missing_files": missing_files,
        "total_missing": len(missing_files),
        "message": f"Found {len(missing_files)} missing files that need re-upload"
    }


# ============== Dynamic routes ==============

@router.get("/{file_id}")
async def download_file(file_id: str):
    """
    Download a file from GridFS
    Public endpoint - files can be accessed by anyone with the file_id
    """
    try:
        content, metadata = await download_file_from_gridfs(file_id)
        
        content_type = metadata.get("content_type", "application/octet-stream")
        filename = metadata.get("original_filename") or metadata.get("filename", "download")
        
        return Response(
            content=content,
            media_type=content_type,
            headers={
                "Content-Disposition": f'inline; filename="{filename}"',
                "Cache-Control": "public, max-age=31536000"  # Cache for 1 year
            }
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{file_id}/download")
async def force_download_file(file_id: str):
    """
    Download a file from GridFS with attachment disposition (force download)
    """
    try:
        content, metadata = await download_file_from_gridfs(file_id)
        
        content_type = metadata.get("content_type", "application/octet-stream")
        filename = metadata.get("original_filename") or metadata.get("filename", "download")
        
        return Response(
            content=content,
            media_type=content_type,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
            }
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{file_id}/info")
async def get_file_info(
    file_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get file metadata without downloading content
    """
    metadata = await get_file_metadata(file_id)
    if not metadata:
        raise HTTPException(status_code=404, detail="File not found")
    return metadata

@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    category: str = Query(..., description="File category (e.g., client_documents, company_logo)"),
    entity_id: Optional[str] = Query(None, description="Related entity ID"),
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("files.upload", "upload files"))
):
    """
    Upload a file to GridFS (requires files.upload permission)
    """
    try:
        content = await file.read()
        
        metadata = {
            "category": category,
            "uploaded_by": current_user.get("id"),
            "uploaded_by_name": current_user.get("name")
        }
        if entity_id:
            metadata["entity_id"] = entity_id
        
        file_id = await upload_file_to_gridfs(
            content,
            file.filename,
            file.content_type or "application/octet-stream",
            metadata
        )
        
        return {
            "success": True,
            "file_id": file_id,
            "file_url": get_file_url(file_id),
            "filename": file.filename
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{file_id}")
async def delete_file(
    file_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Delete a file from GridFS (requires authentication)
    """
    # Check if user has permission (PE Desk or file owner)
    metadata = await get_file_metadata(file_id)
    if not metadata:
        raise HTTPException(status_code=404, detail="File not found")
    
    # Only PE Desk (role 1-2) or the uploader can delete
    if current_user.get("role") > 2 and metadata.get("uploaded_by") != current_user.get("id"):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    success = await delete_file_from_gridfs(file_id)
    if success:
        return {"success": True, "message": "File deleted"}
    else:
        raise HTTPException(status_code=500, detail="Failed to delete file")

@router.get("/list/{category}")
async def list_files(
    category: str,
    entity_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """
    List all files in a category
    """
    files = await list_files_by_category(category, entity_id)
    return {"files": files, "count": len(files)}


# ============== Missing Files Scanner & Re-upload (PE Desk/Manager Only) ==============

@router.get("/scan/missing")
async def scan_missing_files(
    current_user: dict = Depends(get_current_user)
):
    """
    Scan database for references to files that are not in GridFS (PE Desk/Manager only).
    Returns a list of entities with missing files that need re-upload.
    """
    user_role = current_user.get("role", 6)
    if not is_pe_level(user_role):
        raise HTTPException(status_code=403, detail="Only PE Desk or PE Manager can scan for missing files")
    
    missing_files = []
    
    # Scan clients for missing documents
    async for client in db.clients.find({"documents": {"$exists": True, "$ne": []}}, {"_id": 0}):
        for doc in client.get("documents", []):
            file_id = doc.get("file_id")
            if file_id:
                metadata = await get_file_metadata(file_id)
                if not metadata:
                    missing_files.append({
                        "entity_type": "client",
                        "entity_id": client.get("id"),
                        "entity_name": client.get("name"),
                        "doc_type": doc.get("doc_type"),
                        "file_id": file_id,
                        "original_filename": doc.get("filename")
                    })
            elif doc.get("file_path") and not doc.get("file_id"):
                # Old document without GridFS - needs migration
                missing_files.append({
                    "entity_type": "client",
                    "entity_id": client.get("id"),
                    "entity_name": client.get("name"),
                    "doc_type": doc.get("doc_type"),
                    "file_id": None,
                    "original_filename": doc.get("filename"),
                    "needs_migration": True
                })
    
    # Scan company master for missing documents
    company = await db.company_master.find_one({"_id": "company_settings"})
    if company:
        doc_fields = ["logo", "cml_cdsl", "cml_nsdl", "cancelled_cheque", "pan_card"]
        for field in doc_fields:
            file_id = company.get(f"{field}_file_id")
            if file_id:
                metadata = await get_file_metadata(file_id)
                if not metadata:
                    missing_files.append({
                        "entity_type": "company_master",
                        "entity_id": "company_settings",
                        "entity_name": "Company Master",
                        "doc_type": field,
                        "file_id": file_id
                    })
    
    # Scan referral partners for missing documents
    async for rp in db.referral_partners.find({}, {"_id": 0}):
        doc_fields = ["pan_card", "aadhar_card", "cancelled_cheque"]
        for field in doc_fields:
            file_id = rp.get(f"{field}_file_id")
            if file_id:
                metadata = await get_file_metadata(file_id)
                if not metadata:
                    missing_files.append({
                        "entity_type": "referral_partner",
                        "entity_id": rp.get("id"),
                        "entity_name": rp.get("name"),
                        "doc_type": field,
                        "file_id": file_id
                    })
    
    # Scan business partners for missing documents
    async for bp in db.business_partners.find({"documents": {"$exists": True, "$ne": []}}, {"_id": 0}):
        for doc in bp.get("documents", []):
            file_id = doc.get("file_id")
            if file_id:
                metadata = await get_file_metadata(file_id)
                if not metadata:
                    missing_files.append({
                        "entity_type": "business_partner",
                        "entity_id": bp.get("id"),
                        "entity_name": bp.get("name"),
                        "doc_type": doc.get("doc_type"),
                        "file_id": file_id
                    })
    
    # Scan research reports for missing files
    async for report in db.research_reports.find({"file_id": {"$exists": True}}, {"_id": 0}):
        file_id = report.get("file_id")
        if file_id:
            metadata = await get_file_metadata(file_id)
            if not metadata:
                missing_files.append({
                    "entity_type": "research_report",
                    "entity_id": report.get("id"),
                    "entity_name": report.get("title"),
                    "doc_type": "research_report",
                    "file_id": file_id,
                    "original_filename": report.get("file_name")
                })
    
    # Scan contract notes for missing PDFs
    async for cn in db.contract_notes.find({"file_id": {"$exists": True}}, {"_id": 0}):
        file_id = cn.get("file_id")
        if file_id:
            metadata = await get_file_metadata(file_id)
            if not metadata:
                missing_files.append({
                    "entity_type": "contract_note",
                    "entity_id": cn.get("id"),
                    "entity_name": cn.get("contract_note_number"),
                    "doc_type": "contract_note_pdf",
                    "file_id": file_id
                })
    
    return {
        "missing_files": missing_files,
        "total_missing": len(missing_files),
        "message": f"Found {len(missing_files)} missing files that need re-upload"
    }


@router.post("/reupload/{entity_type}/{entity_id}")
async def reupload_file(
    entity_type: str,
    entity_id: str,
    doc_type: str = Query(..., description="Document type to re-upload"),
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Re-upload a missing file for an entity (PE Desk/Manager only).
    This is used to restore files that were lost during redeployment.
    """
    user_role = current_user.get("role", 6)
    if not is_pe_level(user_role):
        raise HTTPException(status_code=403, detail="Only PE Desk or PE Manager can re-upload files")
    
    content = await file.read()
    
    # Upload to GridFS
    file_id = await upload_file_to_gridfs(
        content,
        file.filename,
        file.content_type or "application/octet-stream",
        {
            "category": f"{entity_type}_documents",
            "entity_id": entity_id,
            "doc_type": doc_type,
            "uploaded_by": current_user.get("id"),
            "uploaded_by_name": current_user.get("name"),
            "is_reupload": True
        }
    )
    
    file_url = get_file_url(file_id)
    
    # Update the appropriate collection
    if entity_type == "client":
        # Update client document
        await db.clients.update_one(
            {"id": entity_id, "documents.doc_type": doc_type},
            {"$set": {
                "documents.$.file_id": file_id,
                "documents.$.file_url": file_url,
                "documents.$.reuploaded_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()
            }}
        )
    
    elif entity_type == "company_master":
        # Update company master document
        await db.company_master.update_one(
            {"_id": "company_settings"},
            {"$set": {
                f"{doc_type}_file_id": file_id,
                f"{doc_type}_url": file_url
            }}
        )
    
    elif entity_type == "referral_partner":
        # Update referral partner document
        await db.referral_partners.update_one(
            {"id": entity_id},
            {"$set": {
                f"{doc_type}_file_id": file_id,
                f"{doc_type}_url": file_url
            }}
        )
    
    elif entity_type == "business_partner":
        # Update business partner document
        await db.business_partners.update_one(
            {"id": entity_id, "documents.doc_type": doc_type},
            {"$set": {
                "documents.$.file_id": file_id,
                "documents.$.file_url": file_url
            }}
        )
    
    elif entity_type == "research_report":
        # Update research report
        await db.research_reports.update_one(
            {"id": entity_id},
            {"$set": {
                "file_id": file_id,
                "file_url": file_url
            }}
        )
    
    elif entity_type == "contract_note":
        # Update contract note
        await db.contract_notes.update_one(
            {"id": entity_id},
            {"$set": {
                "file_id": file_id,
                "pdf_url": file_url
            }}
        )
    
    else:
        raise HTTPException(status_code=400, detail=f"Unknown entity type: {entity_type}")
    
    return {
        "success": True,
        "message": f"File re-uploaded successfully for {entity_type}/{entity_id}",
        "file_id": file_id,
        "file_url": file_url
    }

