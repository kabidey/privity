"""
Database Backup and Restore Router
Handles database backup creation, listing, and restoration (PE Desk only)
Includes support for backing up uploaded files
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse, StreamingResponse
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime, timezone
import uuid
import json
import os
import io
import zipfile
import shutil
import base64

from database import db
from routers.auth import get_current_user
from config import is_pe_level, is_pe_desk_only

router = APIRouter(prefix="/database", tags=["Database Management"])

# Upload directory path
UPLOADS_DIR = "/app/uploads"

# Collections to backup - comprehensive list
BACKUP_COLLECTIONS = [
    "users",
    "clients", 
    "stocks",
    "purchases",
    "purchase_payments",
    "bookings",
    "inventory",
    "corporate_actions",
    "notifications",
    "audit_logs",
    "email_templates",
    "email_logs",
    "smtp_settings",
    "referral_partners",
    "rp_payments",
    "business_partners",
    "bp_otps",
    "company_master",
    "contract_notes",
    "vendor_contract_notes",
    "employee_commissions",
    "counters",
    "password_resets",
    "refund_requests",
    "sohini_chats",
    "group_chat_messages",
    "research_reports",
    "system_settings",
]

# File directories to include in backup
FILE_DIRECTORIES = [
    "contract_notes",
    "vendor_contract_notes",
    "company",
    "bp_documents",
    "insider_forms",
    "referral_partners",
    "research",
]


class BackupMetadata(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    created_at: str
    created_by: str
    created_by_name: str
    collections: List[str]
    record_counts: dict
    size_bytes: int
    includes_files: bool = False
    files_count: int = 0
    files_size_bytes: int = 0


class RestoreRequest(BaseModel):
    backup_id: str
    collections: Optional[List[str]] = None  # If None, restore all


# ============== Backup Endpoints ==============
@router.get("/backups")
async def list_backups(current_user: dict = Depends(get_current_user)):
    """List all database backups (PE Level)"""
    if not is_pe_level(current_user.get("role", 6)):
        raise HTTPException(status_code=403, detail="Only PE Desk or PE Manager can access database backups")
    
    backups = await db.database_backups.find(
        {},
        {"_id": 0, "data": 0}  # Exclude actual data from listing
    ).sort("created_at", -1).to_list(100)
    
    return backups


@router.post("/backups")
async def create_backup(
    name: str,
    description: Optional[str] = None,
    include_all: bool = False,
    current_user: dict = Depends(get_current_user)
):
    """Create a new database backup (PE Level)
    
    Args:
        name: Name for the backup
        description: Optional description
        include_all: If True, backup all collections dynamically (recommended)
    """
    if not is_pe_level(current_user.get("role", 6)):
        raise HTTPException(status_code=403, detail="Only PE Desk or PE Manager can create database backups")
    
    backup_id = str(uuid.uuid4())
    backup_data = {}
    record_counts = {}
    total_size = 0
    
    # Determine which collections to backup
    if include_all:
        all_collections = await db.list_collection_names()
        # Exclude database_backups from backup
        collections_to_backup = [c for c in all_collections if c != "database_backups"]
    else:
        collections_to_backup = BACKUP_COLLECTIONS
    
    # Backup each collection
    for collection_name in collections_to_backup:
        try:
            collection = db[collection_name]
            documents = await collection.find({}, {"_id": 0}).to_list(100000)
            backup_data[collection_name] = documents
            record_counts[collection_name] = len(documents)
            total_size += len(json.dumps(documents, default=str))
        except Exception as e:
            backup_data[collection_name] = []
            record_counts[collection_name] = 0
    
    # Store backup
    backup_doc = {
        "id": backup_id,
        "name": name,
        "description": description,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": current_user["id"],
        "created_by_name": current_user["name"],
        "collections": collections_to_backup,
        "record_counts": record_counts,
        "size_bytes": total_size,
        "include_all": include_all,
        "data": backup_data
    }
    
    await db.database_backups.insert_one(backup_doc)
    
    # Log the backup action
    await db.audit_logs.insert_one({
        "id": str(uuid.uuid4()),
        "action": "DATABASE_BACKUP",
        "entity_type": "database",
        "entity_id": backup_id,
        "user_id": current_user["id"],
        "user_name": current_user["name"],
        "user_role": current_user.get("role", 5),
        "details": {
            "backup_name": name,
            "collections_count": len(collections_to_backup),
            "total_records": sum(record_counts.values()),
            "size_bytes": total_size
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    # Keep only last 10 backups to save space
    all_backups = await db.database_backups.find({}, {"id": 1}).sort("created_at", -1).to_list(100)
    if len(all_backups) > 10:
        old_backup_ids = [b["id"] for b in all_backups[10:]]
        await db.database_backups.delete_many({"id": {"$in": old_backup_ids}})
    
    return {
        "message": "Backup created successfully",
        "backup": {
            "id": backup_id,
            "name": name,
            "collections_count": len(collections_to_backup),
            "record_counts": record_counts,
            "total_records": sum(record_counts.values()),
            "size_bytes": total_size
        }
    }


@router.post("/backups/full")
async def create_full_backup(
    current_user: dict = Depends(get_current_user)
):
    """Create a FULL database backup including ALL collections and files info (PE Desk only)
    
    This backup includes:
    - ALL database collections (dynamically detected)
    - Metadata about all uploaded files
    - Ready for complete system restore
    """
    if not is_pe_desk_only(current_user.get("role", 6)):
        raise HTTPException(status_code=403, detail="Only PE Desk can create full backups")
    
    backup_id = str(uuid.uuid4())
    backup_data = {}
    record_counts = {}
    total_size = 0
    
    # Get ALL collections dynamically
    all_collections = await db.list_collection_names()
    collections_to_backup = [c for c in all_collections if c != "database_backups"]
    
    # Backup each collection
    for collection_name in collections_to_backup:
        try:
            collection = db[collection_name]
            documents = await collection.find({}, {"_id": 0}).to_list(100000)
            backup_data[collection_name] = documents
            record_counts[collection_name] = len(documents)
            total_size += len(json.dumps(documents, default=str))
        except Exception as e:
            backup_data[collection_name] = []
            record_counts[collection_name] = 0
    
    # Get file stats for metadata
    files_count, files_size = get_files_stats(UPLOADS_DIR)
    
    # Get files by category
    files_by_category = {}
    if os.path.exists(UPLOADS_DIR):
        for item in os.listdir(UPLOADS_DIR):
            item_path = os.path.join(UPLOADS_DIR, item)
            if os.path.isdir(item_path):
                cat_count, cat_size = get_files_stats(item_path)
                if cat_count > 0:
                    files_by_category[item] = {
                        "count": cat_count,
                        "size_bytes": cat_size
                    }
    
    # Store backup
    now = datetime.now(timezone.utc)
    backup_name = f"Full_Backup_{now.strftime('%Y%m%d_%H%M%S')}"
    
    backup_doc = {
        "id": backup_id,
        "name": backup_name,
        "description": f"Full system backup - {len(collections_to_backup)} collections, {sum(record_counts.values())} records",
        "created_at": now.isoformat(),
        "created_by": current_user["id"],
        "created_by_name": current_user["name"],
        "collections": collections_to_backup,
        "record_counts": record_counts,
        "size_bytes": total_size,
        "include_all": True,
        "is_full_backup": True,
        "files_metadata": {
            "total_count": files_count,
            "total_size_bytes": files_size,
            "by_category": files_by_category
        },
        "data": backup_data
    }
    
    await db.database_backups.insert_one(backup_doc)
    
    # Log the backup action
    await db.audit_logs.insert_one({
        "id": str(uuid.uuid4()),
        "action": "FULL_DATABASE_BACKUP",
        "entity_type": "database",
        "entity_id": backup_id,
        "user_id": current_user["id"],
        "user_name": current_user["name"],
        "user_role": current_user.get("role", 5),
        "details": {
            "backup_name": backup_name,
            "collections_count": len(collections_to_backup),
            "total_records": sum(record_counts.values()),
            "size_bytes": total_size,
            "files_count": files_count,
            "files_size_bytes": files_size
        },
        "timestamp": now.isoformat()
    })
    
    # Keep only last 10 backups
    all_backups = await db.database_backups.find({}, {"id": 1}).sort("created_at", -1).to_list(100)
    if len(all_backups) > 10:
        old_backup_ids = [b["id"] for b in all_backups[10:]]
        await db.database_backups.delete_many({"id": {"$in": old_backup_ids}})
    
    return {
        "message": "Full backup created successfully",
        "backup": {
            "id": backup_id,
            "name": backup_name,
            "collections_count": len(collections_to_backup),
            "collections": collections_to_backup,
            "record_counts": record_counts,
            "total_records": sum(record_counts.values()),
            "size_bytes": total_size,
            "files_count": files_count,
            "files_size_mb": round(files_size / (1024 * 1024), 2)
        },
        "tip": f"Download this backup with files using: GET /api/database/backups/{backup_id}/download?include_files=true"
    }


@router.get("/backups/{backup_id}")
async def get_backup_details(backup_id: str, current_user: dict = Depends(get_current_user)):
    """Get backup details (PE Level)"""
    if not is_pe_level(current_user.get("role", 6)):
        raise HTTPException(status_code=403, detail="Only PE Desk or PE Manager can access database backups")
    
    backup = await db.database_backups.find_one(
        {"id": backup_id},
        {"_id": 0, "data": 0}
    )
    
    if not backup:
        raise HTTPException(status_code=404, detail="Backup not found")
    
    return backup


@router.delete("/backups/{backup_id}")
async def delete_backup(backup_id: str, current_user: dict = Depends(get_current_user)):
    """Delete a backup (PE Desk only - deletion restricted)"""
    if not is_pe_desk_only(current_user.get("role", 6)):
        raise HTTPException(status_code=403, detail="Only PE Desk can delete backups")
    
    result = await db.database_backups.delete_one({"id": backup_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Backup not found")
    
    return {"message": "Backup deleted successfully"}


@router.post("/restore")
async def restore_database(
    restore_data: RestoreRequest,
    current_user: dict = Depends(get_current_user)
):
    """Restore database from a backup (PE Desk only - restore restricted)
    
    WARNING: This will replace existing data in the selected collections!
    """
    if not is_pe_desk_only(current_user.get("role", 6)):
        raise HTTPException(status_code=403, detail="Only PE Desk can restore database")
    
    # Get backup
    backup = await db.database_backups.find_one({"id": restore_data.backup_id}, {"_id": 0})
    
    if not backup:
        raise HTTPException(status_code=404, detail="Backup not found")
    
    backup_data = backup.get("data", {})
    collections_to_restore = restore_data.collections or BACKUP_COLLECTIONS
    
    restored_counts = {}
    errors = []
    
    for collection_name in collections_to_restore:
        if collection_name not in backup_data:
            errors.append(f"Collection {collection_name} not found in backup")
            continue
        
        if collection_name == "users":
            # Special handling for users - preserve super admin
            documents = backup_data[collection_name]
            # Remove existing users except super admin
            await db.users.delete_many({"email": {"$ne": "pedesk@smifs.com"}})
            # Insert backup users except if they conflict with super admin
            users_to_insert = [d for d in documents if d.get("email") != "pedesk@smifs.com"]
            if users_to_insert:
                await db.users.insert_many(users_to_insert)
            restored_counts[collection_name] = len(users_to_insert)
        else:
            try:
                documents = backup_data[collection_name]
                collection = db[collection_name]
                
                # Clear existing data
                await collection.delete_many({})
                
                # Insert backup data
                if documents:
                    await collection.insert_many(documents)
                
                restored_counts[collection_name] = len(documents)
            except Exception as e:
                errors.append(f"Error restoring {collection_name}: {str(e)}")
    
    # Log the restore action
    await db.audit_logs.insert_one({
        "id": str(uuid.uuid4()),
        "action": "DATABASE_RESTORE",
        "entity_type": "database",
        "entity_id": restore_data.backup_id,
        "user_id": current_user["id"],
        "user_name": current_user["name"],
        "user_role": current_user.get("role", 5),
        "details": {
            "backup_name": backup.get("name"),
            "collections_restored": list(restored_counts.keys()),
            "record_counts": restored_counts,
            "errors": errors
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    return {
        "message": "Database restored successfully" if not errors else "Database restored with some errors",
        "restored_counts": restored_counts,
        "errors": errors
    }


@router.get("/stats")
async def get_database_stats(current_user: dict = Depends(get_current_user)):
    """Get database statistics (PE Level)"""
    if not is_pe_level(current_user.get("role", 6)):
        raise HTTPException(status_code=403, detail="Only PE Desk or PE Manager can access database stats")
    
    stats = {}
    
    # Get all collections dynamically
    all_collections = await db.list_collection_names()
    
    # Exclude system and backup collections from stats
    excluded = ["database_backups"]
    
    for collection_name in sorted(all_collections):
        if collection_name not in excluded:
            try:
                collection = db[collection_name]
                count = await collection.count_documents({})
                stats[collection_name] = count
            except Exception:
                stats[collection_name] = 0
    
    # Get uploaded files stats
    files_count, files_size = get_files_stats(UPLOADS_DIR)
    
    # Get files by category (including client document folders)
    files_by_category = {}
    if os.path.exists(UPLOADS_DIR):
        for item in os.listdir(UPLOADS_DIR):
            item_path = os.path.join(UPLOADS_DIR, item)
            if os.path.isdir(item_path):
                cat_count, cat_size = get_files_stats(item_path)
                if cat_count > 0:
                    files_by_category[item] = {
                        "count": cat_count,
                        "size_bytes": cat_size,
                        "size_mb": round(cat_size / (1024 * 1024), 2)
                    }
    
    # Check for missing collections in backup list
    missing_from_backup = [c for c in all_collections if c not in BACKUP_COLLECTIONS and c != "database_backups"]
    
    return {
        "collections": stats,
        "total_records": sum(stats.values()),
        "total_collections": len(stats),
        "backup_count": await db.database_backups.count_documents({}),
        "backed_up_collections": BACKUP_COLLECTIONS,
        "missing_from_backup_list": missing_from_backup,
        "uploaded_files": {
            "total_count": files_count,
            "total_size_bytes": files_size,
            "total_size_mb": round(files_size / (1024 * 1024), 2),
            "by_category": files_by_category,
            "backed_up_directories": FILE_DIRECTORIES
        }
    }


# ============== Clear Database Endpoint ==============
@router.delete("/clear")
async def clear_database(current_user: dict = Depends(get_current_user)):
    """Clear all database collections except users and database_backups (PE Desk only)
    
    WARNING: This permanently deletes all data except user accounts and backups!
    """
    if not is_pe_desk_only(current_user.get("role", 6)):
        raise HTTPException(status_code=403, detail="Only PE Desk can clear the database")
    
    cleared_counts = {}
    errors = []
    
    # Get all collections dynamically from the database
    all_collections = await db.list_collection_names()
    
    # Collections to preserve (users for authentication, database_backups for recovery)
    protected_collections = ["users", "database_backups"]
    
    # Clear all collections except protected ones
    collections_to_clear = [c for c in all_collections if c not in protected_collections]
    
    for collection_name in collections_to_clear:
        try:
            collection = db[collection_name]
            count_before = await collection.count_documents({})
            if count_before > 0:
                await collection.delete_many({})
                cleared_counts[collection_name] = count_before
        except Exception as e:
            errors.append(f"Error clearing {collection_name}: {str(e)}")
    
    # Log the clear action
    await db.audit_logs.insert_one({
        "id": str(uuid.uuid4()),
        "action": "DATABASE_CLEAR",
        "entity_type": "database",
        "entity_id": "all",
        "user_id": current_user["id"],
        "user_name": current_user["name"],
        "user_role": current_user.get("role", 5),
        "details": {
            "collections_cleared": list(cleared_counts.keys()),
            "record_counts_deleted": cleared_counts,
            "protected_collections": protected_collections,
            "errors": errors
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    return {
        "message": "Database cleared successfully" if not errors else "Database cleared with some errors",
        "cleared_counts": cleared_counts,
        "total_deleted": sum(cleared_counts.values()),
        "collections_cleared": len(cleared_counts),
        "protected_collections": protected_collections,
        "errors": errors
    }


# ============== Download Backup as ZIP ==============
def get_all_files_in_directory(directory: str) -> List[tuple]:
    """Get all files in a directory recursively with their relative paths"""
    files = []
    if os.path.exists(directory):
        for root, dirs, filenames in os.walk(directory):
            for filename in filenames:
                full_path = os.path.join(root, filename)
                rel_path = os.path.relpath(full_path, directory)
                files.append((full_path, rel_path))
    return files


def get_files_stats(directory: str) -> tuple:
    """Get count and total size of files in directory"""
    count = 0
    total_size = 0
    if os.path.exists(directory):
        for root, dirs, filenames in os.walk(directory):
            for filename in filenames:
                full_path = os.path.join(root, filename)
                count += 1
                total_size += os.path.getsize(full_path)
    return count, total_size


@router.get("/backups/{backup_id}/download")
async def download_backup(
    backup_id: str, 
    include_files: bool = True,
    current_user: dict = Depends(get_current_user)
):
    """Download a backup as a ZIP file (PE Level)
    
    Args:
        backup_id: ID of the backup to download
        include_files: If True, include all uploaded files (documents, logos, etc.)
    """
    if not is_pe_level(current_user.get("role", 6)):
        raise HTTPException(status_code=403, detail="Only PE Desk or PE Manager can download backups")
    
    # Get backup with data
    backup = await db.database_backups.find_one({"id": backup_id}, {"_id": 0})
    
    if not backup:
        raise HTTPException(status_code=404, detail="Backup not found")
    
    backup_data = backup.get("data", {})
    
    # Get file stats
    files_count, files_size = get_files_stats(UPLOADS_DIR) if include_files else (0, 0)
    
    # Create ZIP file in memory
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        # Add metadata file
        metadata = {
            "id": backup["id"],
            "name": backup["name"],
            "description": backup.get("description"),
            "created_at": backup["created_at"],
            "created_by": backup["created_by"],
            "created_by_name": backup["created_by_name"],
            "collections": backup["collections"],
            "record_counts": backup["record_counts"],
            "size_bytes": backup["size_bytes"],
            "includes_files": include_files,
            "files_count": files_count,
            "files_size_bytes": files_size,
            "backup_version": "2.0"  # Version to identify new format with files
        }
        zip_file.writestr("metadata.json", json.dumps(metadata, indent=2))
        
        # Add each collection as a separate JSON file
        for collection_name, documents in backup_data.items():
            json_content = json.dumps(documents, indent=2, default=str)
            zip_file.writestr(f"collections/{collection_name}.json", json_content)
        
        # Add uploaded files if requested
        if include_files and os.path.exists(UPLOADS_DIR):
            all_files = get_all_files_in_directory(UPLOADS_DIR)
            for full_path, rel_path in all_files:
                try:
                    zip_file.write(full_path, f"uploads/{rel_path}")
                except Exception as e:
                    print(f"Error adding file {full_path}: {e}")
    
    zip_buffer.seek(0)
    
    # Generate filename
    safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in backup["name"])
    file_suffix = "_with_files" if include_files else ""
    filename = f"backup_{safe_name}{file_suffix}_{backup['created_at'][:10]}.zip"
    
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


# ============== Upload and Restore from ZIP ==============
@router.post("/restore-from-file")
async def restore_from_file(
    file: UploadFile = File(...),
    restore_files: bool = True,
    current_user: dict = Depends(get_current_user)
):
    """Restore database from an uploaded ZIP backup file (PE Desk only - restore restricted)
    
    Args:
        file: The ZIP backup file to restore from
        restore_files: If True, also restore uploaded files (documents, logos, etc.)
    
    WARNING: This will replace existing data in the selected collections and uploaded files!
    """
    if not is_pe_desk_only(current_user.get("role", 6)):
        raise HTTPException(status_code=403, detail="Only PE Desk can restore database")
    
    # Validate file type
    if not file.filename.endswith('.zip'):
        raise HTTPException(status_code=400, detail="Please upload a ZIP file")
    
    try:
        # Read the uploaded file
        content = await file.read()
        zip_buffer = io.BytesIO(content)
        
        # Extract and validate ZIP contents
        backup_data = {}
        metadata = None
        files_restored = 0
        files_errors = []
        
        with zipfile.ZipFile(zip_buffer, 'r') as zip_file:
            # Read metadata
            if "metadata.json" not in zip_file.namelist():
                raise HTTPException(status_code=400, detail="Invalid backup file: missing metadata.json")
            
            metadata_content = zip_file.read("metadata.json")
            metadata = json.loads(metadata_content)
            
            # Read each collection
            for filename in zip_file.namelist():
                if filename.startswith("collections/") and filename.endswith(".json"):
                    collection_name = filename.replace("collections/", "").replace(".json", "")
                    collection_content = zip_file.read(filename)
                    backup_data[collection_name] = json.loads(collection_content)
            
            # Restore uploaded files if present and requested
            if restore_files:
                for filename in zip_file.namelist():
                    if filename.startswith("uploads/") and not filename.endswith("/"):
                        try:
                            # Get the relative path after "uploads/"
                            rel_path = filename[8:]  # Remove "uploads/" prefix
                            target_path = os.path.join(UPLOADS_DIR, rel_path)
                            
                            # Create directory if it doesn't exist
                            target_dir = os.path.dirname(target_path)
                            os.makedirs(target_dir, exist_ok=True)
                            
                            # Extract file
                            with zip_file.open(filename) as src:
                                with open(target_path, 'wb') as dst:
                                    dst.write(src.read())
                            files_restored += 1
                        except Exception as e:
                            files_errors.append(f"Error restoring file {filename}: {str(e)}")
        
        if not backup_data:
            raise HTTPException(status_code=400, detail="Invalid backup file: no valid collection data found")
        
        # Restore the data
        restored_counts = {}
        errors = []
        
        for collection_name, documents in backup_data.items():
            if collection_name == "database_backups":
                # Skip restoring backups collection
                continue
            
            if collection_name == "users":
                # Special handling for users - preserve super admin
                await db.users.delete_many({"email": {"$ne": "pedesk@smifs.com"}})
                users_to_insert = [d for d in documents if d.get("email") != "pedesk@smifs.com"]
                if users_to_insert:
                    await db.users.insert_many(users_to_insert)
                restored_counts[collection_name] = len(users_to_insert)
            else:
                try:
                    collection = db[collection_name]
                    await collection.delete_many({})
                    if documents:
                        await collection.insert_many(documents)
                    restored_counts[collection_name] = len(documents)
                except Exception as e:
                    errors.append(f"Error restoring {collection_name}: {str(e)}")
        
        # Log the restore action
        await db.audit_logs.insert_one({
            "id": str(uuid.uuid4()),
            "action": "DATABASE_RESTORE_FROM_FILE",
            "entity_type": "database",
            "entity_id": metadata.get("id", "uploaded_file"),
            "user_id": current_user["id"],
            "user_name": current_user["name"],
            "user_role": current_user.get("role", 5),
            "details": {
                "backup_name": metadata.get("name", file.filename),
                "original_backup_date": metadata.get("created_at"),
                "collections_restored": list(restored_counts.keys()),
                "record_counts": restored_counts,
                "files_restored": files_restored,
                "errors": errors + files_errors
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        all_errors = errors + files_errors
        
        return {
            "message": "Database restored from file successfully" if not all_errors else "Database restored with some errors",
            "backup_info": {
                "name": metadata.get("name"),
                "original_date": metadata.get("created_at"),
                "original_creator": metadata.get("created_by_name"),
                "includes_files": metadata.get("includes_files", False)
            },
            "restored_counts": restored_counts,
            "files_restored": files_restored,
            "errors": all_errors
        }
        
    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="Invalid ZIP file")
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON in backup file: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing backup file: {str(e)}")
