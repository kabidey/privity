"""
Database Backup and Restore Router
Handles database backup creation, listing, and restoration (PE Desk only)
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime, timezone
import uuid
import json
import os

from database import db
from routers.auth import get_current_user

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
    """List all database backups (PE Desk only)"""
    if current_user.get("role", 5) != 1:
        raise HTTPException(status_code=403, detail="Only PE Desk can access database backups")
    
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
    """Create a new database backup (PE Desk only)"""
    if current_user.get("role", 5) != 1:
        raise HTTPException(status_code=403, detail="Only PE Desk can create database backups")
    
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
    """Get backup details (PE Desk only)"""
    if current_user.get("role", 5) != 1:
        raise HTTPException(status_code=403, detail="Only PE Desk can access database backups")
    
    backup = await db.database_backups.find_one(
        {"id": backup_id},
        {"_id": 0, "data": 0}
    )
    
    if not backup:
        raise HTTPException(status_code=404, detail="Backup not found")
    
    return backup


@router.delete("/backups/{backup_id}")
async def delete_backup(backup_id: str, current_user: dict = Depends(get_current_user)):
    """Delete a backup (PE Desk only)"""
    if current_user.get("role", 5) != 1:
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
    """Restore database from a backup (PE Desk only)
    
    WARNING: This will replace existing data in the selected collections!
    """
    if current_user.get("role", 5) != 1:
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
    """Get database statistics (PE Desk only)"""
    if current_user.get("role", 5) != 1:
        raise HTTPException(status_code=403, detail="Only PE Desk can access database stats")
    
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
