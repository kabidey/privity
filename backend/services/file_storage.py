"""
File Storage Service using MongoDB GridFS
Provides persistent file storage that survives redeployments
"""
import os
import io
import base64
from datetime import datetime, timezone
from typing import Optional, Tuple, List
from motor.motor_asyncio import AsyncIOMotorGridFSBucket
from bson import ObjectId
from database import db, client

# GridFS bucket for file storage
fs_bucket = None

def get_gridfs_bucket():
    """Get or create GridFS bucket"""
    global fs_bucket
    if fs_bucket is None:
        fs_bucket = AsyncIOMotorGridFSBucket(db)
    return fs_bucket

async def upload_file_to_gridfs(
    file_content: bytes,
    filename: str,
    content_type: str,
    metadata: dict = None
) -> str:
    """
    Upload a file to GridFS
    
    Args:
        file_content: The file bytes
        filename: Original filename
        content_type: MIME type of the file
        metadata: Additional metadata (category, entity_id, etc.)
    
    Returns:
        The GridFS file_id as a string
    """
    bucket = get_gridfs_bucket()
    
    # Prepare metadata
    file_metadata = {
        "content_type": content_type,
        "original_filename": filename,
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
        **(metadata or {})
    }
    
    # Upload to GridFS
    file_id = await bucket.upload_from_stream(
        filename,
        io.BytesIO(file_content),
        metadata=file_metadata
    )
    
    return str(file_id)

async def download_file_from_gridfs(file_id: str) -> Tuple[bytes, dict]:
    """
    Download a file from GridFS
    
    Args:
        file_id: The GridFS file_id string
    
    Returns:
        Tuple of (file_bytes, metadata)
    """
    bucket = get_gridfs_bucket()
    
    try:
        # Get the file
        grid_out = await bucket.open_download_stream(ObjectId(file_id))
        content = await grid_out.read()
        metadata = grid_out.metadata or {}
        metadata["filename"] = grid_out.filename
        metadata["length"] = grid_out.length
        
        return content, metadata
    except Exception as e:
        raise FileNotFoundError(f"File not found: {file_id}") from e

async def delete_file_from_gridfs(file_id: str) -> bool:
    """
    Delete a file from GridFS
    
    Args:
        file_id: The GridFS file_id string
    
    Returns:
        True if deleted successfully
    """
    bucket = get_gridfs_bucket()
    
    try:
        await bucket.delete(ObjectId(file_id))
        return True
    except Exception as e:
        print(f"Error deleting file {file_id}: {e}")
        return False

async def get_file_metadata(file_id: str) -> Optional[dict]:
    """
    Get file metadata without downloading the content
    
    Args:
        file_id: The GridFS file_id string
    
    Returns:
        File metadata or None if not found
    """
    try:
        file_doc = await db.fs.files.find_one({"_id": ObjectId(file_id)})
        if file_doc:
            return {
                "file_id": str(file_doc["_id"]),
                "filename": file_doc.get("filename"),
                "length": file_doc.get("length"),
                "upload_date": file_doc.get("uploadDate"),
                **(file_doc.get("metadata") or {})
            }
        return None
    except Exception:
        return None

async def list_files_by_category(category: str, entity_id: str = None) -> List[dict]:
    """
    List all files in a category
    
    Args:
        category: File category (e.g., 'client_documents', 'company_logo')
        entity_id: Optional entity ID to filter by
    
    Returns:
        List of file metadata
    """
    query = {"metadata.category": category}
    if entity_id:
        query["metadata.entity_id"] = entity_id
    
    files = []
    async for doc in db.fs.files.find(query):
        files.append({
            "file_id": str(doc["_id"]),
            "filename": doc.get("filename"),
            "length": doc.get("length"),
            "upload_date": doc.get("uploadDate"),
            **(doc.get("metadata") or {})
        })
    
    return files

async def migrate_local_file_to_gridfs(
    local_path: str,
    category: str,
    entity_id: str = None
) -> Optional[str]:
    """
    Migrate a local file to GridFS
    
    Args:
        local_path: Path to the local file
        category: File category for metadata
        entity_id: Related entity ID
    
    Returns:
        GridFS file_id or None if migration failed
    """
    if not os.path.exists(local_path):
        return None
    
    try:
        filename = os.path.basename(local_path)
        
        # Determine content type
        ext = os.path.splitext(filename)[1].lower()
        content_types = {
            '.pdf': 'application/pdf',
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif',
            '.doc': 'application/msword',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.xls': 'application/vnd.ms-excel',
            '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        }
        content_type = content_types.get(ext, 'application/octet-stream')
        
        with open(local_path, 'rb') as f:
            file_content = f.read()
        
        metadata = {
            "category": category,
            "migrated_from": local_path,
            "migrated_at": datetime.now(timezone.utc).isoformat()
        }
        if entity_id:
            metadata["entity_id"] = entity_id
        
        file_id = await upload_file_to_gridfs(
            file_content,
            filename,
            content_type,
            metadata
        )
        
        return file_id
    except Exception as e:
        print(f"Migration failed for {local_path}: {e}")
        return None

# Helper function to generate file URL for API endpoint
def get_file_url(file_id: str) -> str:
    """Generate API URL for downloading a file"""
    return f"/api/files/{file_id}"
