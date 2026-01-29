"""
Database Backup and Restore Router
Handles database backup creation, listing, and restoration (PE Desk only)
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

from database import db
from routers.auth import get_current_user
from config import is_pe_level, is_pe_desk_only

router = APIRouter(prefix="/database", tags=["Database Management"])

# Collections to backup
BACKUP_COLLECTIONS = [
    "users",
    "clients", 
    "stocks",
    "purchases",
    "bookings",
    "inventory",
    "corporate_actions",
    "notifications",
    "audit_logs",
    "email_templates",
    "smtp_settings"
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
    current_user: dict = Depends(get_current_user)
):
    """Create a new database backup (PE Level)"""
    if not is_pe_level(current_user.get("role", 6)):
        raise HTTPException(status_code=403, detail="Only PE Desk or PE Manager can create database backups")
    
    backup_id = str(uuid.uuid4())
    backup_data = {}
    record_counts = {}
    total_size = 0
    
    # Backup each collection
    for collection_name in BACKUP_COLLECTIONS:
        try:
            collection = db[collection_name]
            documents = await collection.find({}, {"_id": 0}).to_list(100000)
            backup_data[collection_name] = documents
            record_counts[collection_name] = len(documents)
            total_size += len(json.dumps(documents))
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
        "collections": BACKUP_COLLECTIONS,
        "record_counts": record_counts,
        "size_bytes": total_size,
        "data": backup_data
    }
    
    await db.database_backups.insert_one(backup_doc)
    
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
            "record_counts": record_counts,
            "size_bytes": total_size
        }
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
    
    for collection_name in BACKUP_COLLECTIONS:
        try:
            collection = db[collection_name]
            count = await collection.count_documents({})
            stats[collection_name] = count
        except:
            stats[collection_name] = 0
    
    return {
        "collections": stats,
        "total_records": sum(stats.values()),
        "backup_count": await db.database_backups.count_documents({})
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
@router.get("/backups/{backup_id}/download")
async def download_backup(backup_id: str, current_user: dict = Depends(get_current_user)):
    """Download a backup as a ZIP file (PE Level)"""
    if not is_pe_level(current_user.get("role", 6)):
        raise HTTPException(status_code=403, detail="Only PE Desk or PE Manager can download backups")
    
    # Get backup with data
    backup = await db.database_backups.find_one({"id": backup_id}, {"_id": 0})
    
    if not backup:
        raise HTTPException(status_code=404, detail="Backup not found")
    
    backup_data = backup.get("data", {})
    
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
            "size_bytes": backup["size_bytes"]
        }
        zip_file.writestr("metadata.json", json.dumps(metadata, indent=2))
        
        # Add each collection as a separate JSON file
        for collection_name, documents in backup_data.items():
            json_content = json.dumps(documents, indent=2, default=str)
            zip_file.writestr(f"collections/{collection_name}.json", json_content)
    
    zip_buffer.seek(0)
    
    # Generate filename
    safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in backup["name"])
    filename = f"backup_{safe_name}_{backup['created_at'][:10]}.zip"
    
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


# ============== Upload and Restore from ZIP ==============
@router.post("/restore-from-file")
async def restore_from_file(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """Restore database from an uploaded ZIP backup file (PE Desk only - restore restricted)
    
    WARNING: This will replace existing data in the selected collections!
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
                    if collection_name in BACKUP_COLLECTIONS:
                        collection_content = zip_file.read(filename)
                        backup_data[collection_name] = json.loads(collection_content)
        
        if not backup_data:
            raise HTTPException(status_code=400, detail="Invalid backup file: no valid collection data found")
        
        # Restore the data
        restored_counts = {}
        errors = []
        
        for collection_name, documents in backup_data.items():
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
                "errors": errors
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        return {
            "message": "Database restored from file successfully" if not errors else "Database restored with some errors",
            "backup_info": {
                "name": metadata.get("name"),
                "original_date": metadata.get("created_at"),
                "original_creator": metadata.get("created_by_name")
            },
            "restored_counts": restored_counts,
            "errors": errors
        }
        
    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="Invalid ZIP file")
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON in backup file: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing backup file: {str(e)}")
