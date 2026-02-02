"""
File Router - Serves files from GridFS and handles uploads
"""
from fastapi import APIRouter, HTTPException, UploadFile, File, Depends, Query
from fastapi.responses import StreamingResponse, Response
from typing import Optional
import io
from auth import get_current_user
from services.file_storage import (
    upload_file_to_gridfs,
    download_file_from_gridfs,
    delete_file_from_gridfs,
    get_file_metadata,
    list_files_by_category,
    get_file_url
)

router = APIRouter(prefix="/files", tags=["files"])

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
    current_user: dict = Depends(get_current_user)
):
    """
    Upload a file to GridFS
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
