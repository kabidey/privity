"""
Database Backup and Restore Router
Handles database backup creation, listing, and restoration (PE Desk only)
Includes support for backing up uploaded files from GridFS
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
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
import logging

from database import db
from routers.auth import get_current_user
from services.file_storage import upload_file_to_gridfs, download_file_from_gridfs, get_file_url
from services.permission_service import (
    has_permission,
    check_permission as check_dynamic_permission,
    require_permission
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/database", tags=["Database Management"])


# Helper functions for backward compatibility
def is_pe_level(role: int) -> bool:
    """Check if role is PE level (PE Desk or PE Manager)."""
    return role in [1, 2]


def is_pe_desk_only(role: int) -> bool:
    """Check if role is PE Desk only."""
    return role == 1


# Upload directory path (for backward compatibility)
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

# GridFS collections for file backup
GRIDFS_COLLECTIONS = [
    "fs.files",
    "fs.chunks"
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
    includes_gridfs: bool = False  # New: indicates if GridFS files are included
    gridfs_files_count: int = 0


class RestoreRequest(BaseModel):
    backup_id: str
    collections: Optional[List[str]] = None  # If None, restore all


# ============== Backup Endpoints ==============
@router.get("/backups")
async def list_backups(
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("database_backup.view", "view database backups"))
):
    """List all database backups (requires database_backup.view permission)"""
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
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("database_backup.create", "create database backups"))
):
    """Create a new database backup (requires database_backup.create permission)
    
    Args:
        name: Name for the backup
        description: Optional description
        include_all: If True, backup all collections dynamically (recommended)
    """
    backup_id = str(uuid.uuid4())
    backup_data = {}
    record_counts = {}
    total_size = 0
    
    # Determine which collections to backup
    if include_all:
        all_collections = await db.list_collection_names()
        # Exclude database_backups and fs.chunks (binary data) from backup
        collections_to_backup = [c for c in all_collections if c not in ["database_backups", "fs.chunks"]]
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
            logger.error(f"Error backing up {collection_name}: {str(e)}")
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
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("database_backup.full", "create full backups"))
):
    """Create a FULL database backup including ALL collections and files info (requires database_backup.full permission)
    
    This backup includes:
    - ALL database collections (dynamically detected)
    - Metadata about all uploaded files
    - Ready for complete system restore
    """
    backup_id = str(uuid.uuid4())
    backup_data = {}
    record_counts = {}
    total_size = 0
    
    # Get ALL collections dynamically
    all_collections = await db.list_collection_names()
    # Exclude database_backups and fs.chunks (binary data that breaks JSON serialization)
    collections_to_backup = [c for c in all_collections if c not in ["database_backups", "fs.chunks"]]
    
    # Backup each collection
    for collection_name in collections_to_backup:
        try:
            collection = db[collection_name]
            # For fs.files, exclude binary fields
            if collection_name == "fs.files":
                documents = await collection.find({}, {"_id": 0}).to_list(100000)
                # Convert ObjectId and datetime to strings
                for doc in documents:
                    for key, value in list(doc.items()):
                        if hasattr(value, '__str__') and not isinstance(value, (str, int, float, bool, list, dict, type(None))):
                            doc[key] = str(value)
            else:
                documents = await collection.find({}, {"_id": 0}).to_list(100000)
            backup_data[collection_name] = documents
            record_counts[collection_name] = len(documents)
            total_size += len(json.dumps(documents, default=str))
        except Exception as e:
            logger.error(f"Error backing up {collection_name}: {str(e)}")
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
async def get_backup_details(
    backup_id: str,
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("database_backup.view", "view backup details"))
):
    """Get backup details (requires database_backup.view permission)"""
    backup = await db.database_backups.find_one(
        {"id": backup_id},
        {"_id": 0, "data": 0}
    )
    
    if not backup:
        raise HTTPException(status_code=404, detail="Backup not found")
    
    return backup


@router.delete("/backups/{backup_id}")
async def delete_backup(
    backup_id: str,
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("database_backup.delete", "delete backups"))
):
    """Delete a backup (requires database_backup.delete permission)"""
    result = await db.database_backups.delete_one({"id": backup_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Backup not found")
    
    return {"message": "Backup deleted successfully"}


@router.post("/restore")
async def restore_database(
    restore_data: RestoreRequest,
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("database_backup.restore", "restore database"))
):
    """Restore database from a backup (requires database_backup.restore permission)
    
    WARNING: This will replace existing data in the selected collections!
    """
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
            await db.users.delete_many({"email": {"$ne": "pe@smifs.com"}})
            # Insert backup users except if they conflict with super admin
            users_to_insert = [d for d in documents if d.get("email") != "pe@smifs.com"]
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
async def get_database_stats(
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("database_backup.view", "view database stats"))
):
    """Get database statistics (requires database_backup.view permission)"""
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


# ============== Collection Categories ==============
COLLECTION_CATEGORIES = {
    "finance": {
        "name": "Finance Data",
        "description": "Payments, refunds, commissions, and financial records",
        "collections": ["refund_requests", "rp_payments", "bp_payments", "employee_commissions", "finance_settings"]
    },
    "logs": {
        "name": "System Logs",
        "description": "Audit logs, email logs, security logs",
        "collections": ["audit_logs", "email_logs", "security_logs", "login_locations"]
    },
    "clients": {
        "name": "Client Data",
        "description": "Clients, vendors, and their documents",
        "collections": ["clients"]
    },
    "bookings": {
        "name": "Booking Data",
        "description": "Bookings, contract notes, and related records",
        "collections": ["bookings", "contract_notes"]
    },
    "inventory": {
        "name": "Inventory & Purchases",
        "description": "Stock inventory, purchases, and supplier data",
        "collections": ["inventory", "purchases"]
    },
    "partners": {
        "name": "Partner Data",
        "description": "Business partners, referral partners, and OTPs",
        "collections": ["business_partners", "referral_partners", "bp_otps", "rp_otps"]
    },
    "stocks": {
        "name": "Stock Master Data",
        "description": "Stocks, corporate actions, and market data",
        "collections": ["stocks", "corporate_actions"]
    },
    "settings": {
        "name": "System Settings",
        "description": "Company settings, email templates, SMTP config",
        "collections": ["company_master", "email_templates", "smtp_settings", "roles"]
    },
    "notifications": {
        "name": "Notifications & Messages",
        "description": "Notifications, group chat messages",
        "collections": ["notifications", "group_chat_messages"]
    },
    "research": {
        "name": "Research & Reports",
        "description": "Research reports and analysis data",
        "collections": ["research_reports"]
    }
}


# ============== Clear Database Endpoint ==============
@router.delete("/clear")
async def clear_database(
    collections: Optional[List[str]] = Query(None, description="Specific collections to clear. If empty, clears all except protected."),
    exclude_ids: Optional[List[str]] = Query(None, description="Record IDs to exclude from deletion (format: collection:id)"),
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("database_backup.clear", "clear database"))
):
    """Clear selected database collections (requires database_backup.clear permission)
    
    If no collections specified, clears all except protected ones (users, database_backups).
    Pass specific collection names to selectively clear only those collections.
    Use exclude_ids to preserve specific records (format: "collection_name:record_id").
    
    WARNING: This permanently deletes data!
    """
    cleared_counts = {}
    preserved_counts = {}
    errors = []
    
    # Parse exclude_ids into a dict: {collection: [ids]}
    exclusions = {}
    if exclude_ids:
        for item in exclude_ids:
            if ":" in item:
                coll, record_id = item.split(":", 1)
                if coll not in exclusions:
                    exclusions[coll] = []
                exclusions[coll].append(record_id)
    
    # Get all collections dynamically from the database
    all_collections = await db.list_collection_names()
    
    # Collections to preserve (users for authentication, database_backups for recovery)
    protected_collections = ["users", "database_backups"]
    
    # Determine which collections to clear
    if collections and len(collections) > 0:
        # Selective clear - only clear specified collections (excluding protected)
        collections_to_clear = [c for c in collections if c in all_collections and c not in protected_collections]
    else:
        # Clear all collections except protected ones
        collections_to_clear = [c for c in all_collections if c not in protected_collections]
    
    for collection_name in collections_to_clear:
        try:
            collection = db[collection_name]
            
            # Build delete query - exclude specific IDs if provided
            delete_query = {}
            if collection_name in exclusions and exclusions[collection_name]:
                delete_query = {"id": {"$nin": exclusions[collection_name]}}
                preserved_counts[collection_name] = len(exclusions[collection_name])
            
            count_before = await collection.count_documents(delete_query)
            if count_before > 0:
                await collection.delete_many(delete_query)
                cleared_counts[collection_name] = count_before
        except Exception as e:
            errors.append(f"Error clearing {collection_name}: {str(e)}")
    
    # Log the clear action
    await db.audit_logs.insert_one({
        "id": str(uuid.uuid4()),
        "action": "DATABASE_CLEAR",
        "entity_type": "database",
        "entity_id": "all" if not collections else ",".join(collections),
        "user_id": current_user["id"],
        "user_name": current_user["name"],
        "user_role": current_user.get("role", 5),
        "details": {
            "collections_cleared": list(cleared_counts.keys()),
            "record_counts_deleted": cleared_counts,
            "records_preserved": preserved_counts,
            "protected_collections": protected_collections,
            "selective_clear": bool(collections),
            "requested_collections": collections,
            "exclusions": exclusions,
            "errors": errors
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    return {
        "message": "Selected collections cleared successfully" if not errors else "Collections cleared with some errors",
        "cleared_counts": cleared_counts,
        "preserved_counts": preserved_counts,
        "total_deleted": sum(cleared_counts.values()),
        "total_preserved": sum(preserved_counts.values()),
        "collections_cleared": len(cleared_counts),
        "protected_collections": protected_collections,
        "selective_clear": bool(collections),
        "errors": errors
    }


@router.get("/clearable-collections")
async def get_clearable_collections(
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("database_backup.clear", "view clearable collections"))
):
    """Get list of collections that can be cleared with their record counts and categories"""
    all_collections = await db.list_collection_names()
    protected_collections = ["users", "database_backups"]
    
    # Build reverse mapping: collection -> category
    collection_to_category = {}
    for cat_key, cat_data in COLLECTION_CATEGORIES.items():
        for coll in cat_data["collections"]:
            collection_to_category[coll] = cat_key
    
    clearable = []
    for collection_name in sorted(all_collections):
        if collection_name not in protected_collections:
            count = await db[collection_name].count_documents({})
            clearable.append({
                "name": collection_name,
                "count": count,
                "display_name": collection_name.replace("_", " ").title(),
                "category": collection_to_category.get(collection_name, "other")
            })
    
    # Build categories with counts
    categories = []
    for cat_key, cat_data in COLLECTION_CATEGORIES.items():
        cat_collections = [c for c in clearable if c["category"] == cat_key]
        if cat_collections:
            categories.append({
                "key": cat_key,
                "name": cat_data["name"],
                "description": cat_data["description"],
                "collections": [c["name"] for c in cat_collections],
                "total_records": sum(c["count"] for c in cat_collections)
            })
    
    # Add "other" category for uncategorized collections
    other_collections = [c for c in clearable if c["category"] == "other"]
    if other_collections:
        categories.append({
            "key": "other",
            "name": "Other Data",
            "description": "Miscellaneous collections",
            "collections": [c["name"] for c in other_collections],
            "total_records": sum(c["count"] for c in other_collections)
        })
    
    return {
        "collections": clearable,
        "categories": categories,
        "protected_collections": protected_collections,
        "total_clearable": len(clearable)
    }


@router.post("/clear/preview")
async def preview_clear(
    collections: Optional[List[str]] = Query(None, description="Collections to preview clearing"),
    exclude_ids: Optional[List[str]] = Query(None, description="Record IDs to exclude (format: collection:id)"),
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("database_backup.clear", "preview clear"))
):
    """Preview what would be deleted without actually deleting anything"""
    preview_data = {}
    sample_records = {}
    
    # Parse exclude_ids
    exclusions = {}
    if exclude_ids:
        for item in exclude_ids:
            if ":" in item:
                coll, record_id = item.split(":", 1)
                if coll not in exclusions:
                    exclusions[coll] = []
                exclusions[coll].append(record_id)
    
    all_collections = await db.list_collection_names()
    protected_collections = ["users", "database_backups"]
    
    if collections and len(collections) > 0:
        collections_to_preview = [c for c in collections if c in all_collections and c not in protected_collections]
    else:
        collections_to_preview = [c for c in all_collections if c not in protected_collections]
    
    total_to_delete = 0
    total_to_preserve = 0
    
    for collection_name in collections_to_preview:
        collection = db[collection_name]
        
        # Build query based on exclusions
        delete_query = {}
        if collection_name in exclusions and exclusions[collection_name]:
            delete_query = {"id": {"$nin": exclusions[collection_name]}}
        
        count_to_delete = await collection.count_documents(delete_query)
        total_count = await collection.count_documents({})
        count_to_preserve = total_count - count_to_delete
        
        # Get sample records that would be deleted (first 5)
        samples = await collection.find(
            delete_query, 
            {"_id": 0, "id": 1, "name": 1, "email": 1, "booking_number": 1, "client_name": 1, "symbol": 1, "created_at": 1}
        ).limit(5).to_list(5)
        
        preview_data[collection_name] = {
            "to_delete": count_to_delete,
            "to_preserve": count_to_preserve,
            "total": total_count
        }
        
        if samples:
            sample_records[collection_name] = samples
        
        total_to_delete += count_to_delete
        total_to_preserve += count_to_preserve
    
    return {
        "preview": preview_data,
        "sample_records": sample_records,
        "summary": {
            "total_to_delete": total_to_delete,
            "total_to_preserve": total_to_preserve,
            "collections_affected": len([c for c in preview_data.values() if c["to_delete"] > 0])
        },
        "exclusions_applied": exclusions
    }


@router.delete("/clear/files")
async def clear_uploaded_files(
    file_types: Optional[List[str]] = Query(None, description="File types to clear: client_docs, bp_docs, rp_docs, company_docs, logos"),
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("database_backup.clear", "clear uploaded files"))
):
    """Clear uploaded files from GridFS and file system without touching database records
    
    File types:
    - client_docs: Client documents (PAN, Aadhar, CML, etc.)
    - bp_docs: Business Partner documents
    - rp_docs: Referral Partner documents
    - company_docs: Company master documents
    - logos: Company and partner logos
    - all: Clear all uploaded files
    """
    from motor.motor_asyncio import AsyncIOMotorGridFSBucket
    
    cleared_files = {}
    errors = []
    
    # Define file type mappings to GridFS prefixes and directories
    FILE_TYPE_MAPPINGS = {
        "client_docs": {
            "gridfs_prefix": "client_",
            "directories": ["/app/uploads/clients"]
        },
        "bp_docs": {
            "gridfs_prefix": "bp_",
            "directories": ["/app/uploads/business_partners"]
        },
        "rp_docs": {
            "gridfs_prefix": "rp_",
            "directories": ["/app/uploads/referral_partners"]
        },
        "company_docs": {
            "gridfs_prefix": "company_",
            "directories": ["/app/uploads/company"]
        },
        "logos": {
            "gridfs_prefix": "logo_",
            "directories": ["/app/uploads/logos"]
        }
    }
    
    # If no specific types, don't clear anything (safety measure)
    if not file_types:
        return {
            "message": "No file types specified. Please specify which file types to clear.",
            "available_types": list(FILE_TYPE_MAPPINGS.keys()) + ["all"],
            "cleared_files": {},
            "total_cleared": 0
        }
    
    # Handle "all" option
    if "all" in file_types:
        file_types = list(FILE_TYPE_MAPPINGS.keys())
    
    # Initialize GridFS bucket
    fs_bucket = AsyncIOMotorGridFSBucket(db)
    
    for file_type in file_types:
        if file_type not in FILE_TYPE_MAPPINGS:
            errors.append(f"Unknown file type: {file_type}")
            continue
        
        mapping = FILE_TYPE_MAPPINGS[file_type]
        cleared_files[file_type] = {"gridfs": 0, "filesystem": 0}
        
        # Clear from GridFS
        try:
            # Find files with matching prefix
            async for grid_file in fs_bucket.find({"filename": {"$regex": f"^{mapping['gridfs_prefix']}"}}):
                await fs_bucket.delete(grid_file._id)
                cleared_files[file_type]["gridfs"] += 1
        except Exception as e:
            errors.append(f"Error clearing GridFS {file_type}: {str(e)}")
        
        # Clear from filesystem
        for directory in mapping["directories"]:
            if os.path.exists(directory):
                try:
                    file_count = sum(len(files) for _, _, files in os.walk(directory))
                    shutil.rmtree(directory)
                    os.makedirs(directory, exist_ok=True)  # Recreate empty directory
                    cleared_files[file_type]["filesystem"] += file_count
                except Exception as e:
                    errors.append(f"Error clearing directory {directory}: {str(e)}")
    
    # Calculate totals
    total_gridfs = sum(f["gridfs"] for f in cleared_files.values())
    total_filesystem = sum(f["filesystem"] for f in cleared_files.values())
    
    # Log the action
    await db.audit_logs.insert_one({
        "id": str(uuid.uuid4()),
        "action": "FILES_CLEAR",
        "entity_type": "files",
        "entity_id": ",".join(file_types),
        "user_id": current_user["id"],
        "user_name": current_user["name"],
        "user_role": current_user.get("role", 5),
        "details": {
            "file_types_cleared": file_types,
            "cleared_counts": cleared_files,
            "total_gridfs": total_gridfs,
            "total_filesystem": total_filesystem,
            "errors": errors
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    return {
        "message": "Files cleared successfully" if not errors else "Files cleared with some errors",
        "cleared_files": cleared_files,
        "total_cleared": total_gridfs + total_filesystem,
        "total_gridfs": total_gridfs,
        "total_filesystem": total_filesystem,
        "errors": errors
    }


@router.get("/files/stats")
async def get_file_stats(
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("database_backup.clear", "view file stats"))
):
    """Get statistics about uploaded files for clear preview"""
    from motor.motor_asyncio import AsyncIOMotorGridFSBucket
    
    FILE_TYPE_MAPPINGS = {
        "client_docs": {"gridfs_prefix": "client_", "directories": ["/app/uploads/clients"]},
        "bp_docs": {"gridfs_prefix": "bp_", "directories": ["/app/uploads/business_partners"]},
        "rp_docs": {"gridfs_prefix": "rp_", "directories": ["/app/uploads/referral_partners"]},
        "company_docs": {"gridfs_prefix": "company_", "directories": ["/app/uploads/company"]},
        "logos": {"gridfs_prefix": "logo_", "directories": ["/app/uploads/logos"]}
    }
    
    fs_bucket = AsyncIOMotorGridFSBucket(db)
    stats = {}
    
    for file_type, mapping in FILE_TYPE_MAPPINGS.items():
        gridfs_count = 0
        gridfs_size = 0
        filesystem_count = 0
        filesystem_size = 0
        
        # Count GridFS files
        try:
            async for grid_file in fs_bucket.find({"filename": {"$regex": f"^{mapping['gridfs_prefix']}"}}):
                gridfs_count += 1
                gridfs_size += grid_file.length
        except:
            pass
        
        # Count filesystem files
        for directory in mapping["directories"]:
            if os.path.exists(directory):
                for root, dirs, files in os.walk(directory):
                    for f in files:
                        filesystem_count += 1
                        try:
                            filesystem_size += os.path.getsize(os.path.join(root, f))
                        except:
                            pass
        
        stats[file_type] = {
            "name": file_type.replace("_", " ").title(),
            "gridfs_count": gridfs_count,
            "gridfs_size_mb": round(gridfs_size / (1024 * 1024), 2),
            "filesystem_count": filesystem_count,
            "filesystem_size_mb": round(filesystem_size / (1024 * 1024), 2),
            "total_count": gridfs_count + filesystem_count,
            "total_size_mb": round((gridfs_size + filesystem_size) / (1024 * 1024), 2)
        }
    
    return {
        "file_stats": stats,
        "total_files": sum(s["total_count"] for s in stats.values()),
        "total_size_mb": round(sum(s["total_size_mb"] for s in stats.values()), 2)
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
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("database_backup.view", "download backups"))
):
    """Download a backup as a ZIP file (requires database_backup.view permission)
    
    Args:
        backup_id: ID of the backup to download
        include_files: If True, include all uploaded files (documents, logos, etc.)
    """
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
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("database_backup.restore", "restore database from file"))
):
    """Restore database from an uploaded ZIP backup file (requires database_backup.restore permission)
    
    Args:
        file: The ZIP backup file to restore from
        restore_files: If True, also restore uploaded files (documents, logos, etc.)
    
    WARNING: This will replace existing data in the selected collections and uploaded files!
    """
    
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
                await db.users.delete_many({"email": {"$ne": "pe@smifs.com"}})
                users_to_insert = [d for d in documents if d.get("email") != "pe@smifs.com"]
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



# ============== GridFS File Backup/Restore Endpoints ==============

@router.post("/backups/gridfs")
async def create_gridfs_backup(
    current_user: dict = Depends(get_current_user)
):
    """
    Create a backup of all GridFS files (PE Desk only).
    This exports GridFS file metadata and data for persistent backup.
    
    Returns a downloadable ZIP file containing all GridFS files with metadata.
    """
    if not is_pe_desk_only(current_user.get("role", 6)):
        raise HTTPException(status_code=403, detail="Only PE Desk can create GridFS backups")
    
    try:
        # Create ZIP in memory
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Get all files from GridFS
            files_metadata = []
            total_files = 0
            total_size = 0
            
            async for file_doc in db["fs.files"].find({}):
                file_id = str(file_doc["_id"])
                filename = file_doc.get("filename", f"file_{file_id}")
                metadata = file_doc.get("metadata", {})
                length = file_doc.get("length", 0)
                
                try:
                    # Download file content from GridFS
                    content, _ = await download_file_from_gridfs(file_id)
                    
                    # Add file to ZIP
                    zip_path = f"gridfs_files/{metadata.get('category', 'uncategorized')}/{filename}"
                    zip_file.writestr(zip_path, content)
                    
                    # Store metadata
                    files_metadata.append({
                        "file_id": file_id,
                        "filename": filename,
                        "category": metadata.get("category"),
                        "entity_id": metadata.get("entity_id"),
                        "doc_type": metadata.get("doc_type"),
                        "content_type": metadata.get("content_type"),
                        "length": length,
                        "upload_date": str(file_doc.get("uploadDate", "")),
                        "original_filename": metadata.get("original_filename"),
                        "zip_path": zip_path
                    })
                    
                    total_files += 1
                    total_size += length
                    
                except Exception as e:
                    files_metadata.append({
                        "file_id": file_id,
                        "filename": filename,
                        "error": str(e)
                    })
            
            # Add metadata JSON
            backup_metadata = {
                "backup_type": "gridfs_files",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "created_by": current_user["name"],
                "total_files": total_files,
                "total_size_bytes": total_size,
                "files": files_metadata
            }
            zip_file.writestr("gridfs_metadata.json", json.dumps(backup_metadata, indent=2, default=str))
        
        # Return ZIP file for download
        zip_buffer.seek(0)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={
                "Content-Disposition": f'attachment; filename="gridfs_backup_{timestamp}.zip"'
            }
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating GridFS backup: {str(e)}")


@router.post("/restore/gridfs")
async def restore_gridfs_from_backup(
    file: UploadFile = File(...),
    skip_existing: bool = True,
    current_user: dict = Depends(get_current_user)
):
    """
    Restore GridFS files from a backup ZIP (PE Desk only).
    
    Args:
        file: ZIP file containing GridFS backup
        skip_existing: If True, skip files that already exist in GridFS
    """
    if not is_pe_desk_only(current_user.get("role", 6)):
        raise HTTPException(status_code=403, detail="Only PE Desk can restore GridFS files")
    
    if not file.filename.endswith('.zip'):
        raise HTTPException(status_code=400, detail="Please upload a ZIP file")
    
    try:
        content = await file.read()
        zip_buffer = io.BytesIO(content)
        
        restored_count = 0
        skipped_count = 0
        errors = []
        
        with zipfile.ZipFile(zip_buffer, 'r') as zip_file:
            # Read metadata
            if "gridfs_metadata.json" not in zip_file.namelist():
                raise HTTPException(status_code=400, detail="Invalid backup: missing gridfs_metadata.json")
            
            metadata_content = zip_file.read("gridfs_metadata.json")
            metadata = json.loads(metadata_content)
            
            # Restore each file
            for file_info in metadata.get("files", []):
                if file_info.get("error"):
                    continue
                
                zip_path = file_info.get("zip_path")
                if not zip_path or zip_path not in zip_file.namelist():
                    errors.append(f"File not found in backup: {file_info.get('filename')}")
                    continue
                
                # Check if file already exists
                existing = await db["fs.files"].find_one({"_id": file_info.get("file_id")})
                if existing and skip_existing:
                    skipped_count += 1
                    continue
                
                try:
                    # Read file content from ZIP
                    file_content = zip_file.read(zip_path)
                    
                    # Re-upload to GridFS
                    new_file_id = await upload_file_to_gridfs(
                        file_content,
                        file_info.get("filename"),
                        file_info.get("content_type", "application/octet-stream"),
                        {
                            "category": file_info.get("category"),
                            "entity_id": file_info.get("entity_id"),
                            "doc_type": file_info.get("doc_type"),
                            "original_filename": file_info.get("original_filename"),
                            "restored_from_backup": True,
                            "original_file_id": file_info.get("file_id"),
                            "restored_at": datetime.now(timezone.utc).isoformat()
                        }
                    )
                    
                    # Update references in database if entity_id exists
                    entity_id = file_info.get("entity_id")
                    category = file_info.get("category")
                    doc_type = file_info.get("doc_type")
                    
                    if entity_id and category:
                        new_url = get_file_url(new_file_id)
                        
                        # Update references based on category
                        if category == "client_documents":
                            await db.clients.update_one(
                                {"id": entity_id, "documents.doc_type": doc_type},
                                {"$set": {
                                    "documents.$.file_id": new_file_id,
                                    "documents.$.file_url": new_url
                                }}
                            )
                        elif category == "company_documents" or category == "company_logo":
                            await db.company_master.update_one(
                                {"_id": "company_settings"},
                                {"$set": {
                                    f"{doc_type}_file_id": new_file_id,
                                    f"{doc_type}_url": new_url
                                }}
                            )
                        elif category == "rp_documents":
                            await db.referral_partners.update_one(
                                {"id": entity_id},
                                {"$set": {
                                    f"{doc_type}_file_id": new_file_id,
                                    f"{doc_type}_url": new_url
                                }}
                            )
                        elif category == "bp_documents":
                            await db.business_partners.update_one(
                                {"id": entity_id, "documents.doc_type": doc_type},
                                {"$set": {
                                    "documents.$.file_id": new_file_id,
                                    "documents.$.file_url": new_url
                                }}
                            )
                        elif category == "research_reports":
                            await db.research_reports.update_one(
                                {"id": entity_id},
                                {"$set": {
                                    "file_id": new_file_id,
                                    "file_url": new_url
                                }}
                            )
                        elif category == "contract_notes":
                            await db.contract_notes.update_one(
                                {"id": entity_id},
                                {"$set": {
                                    "file_id": new_file_id,
                                    "pdf_url": new_url
                                }}
                            )
                    
                    restored_count += 1
                    
                except Exception as e:
                    errors.append(f"Error restoring {file_info.get('filename')}: {str(e)}")
        
        # Log the restore action
        await db.audit_logs.insert_one({
            "id": str(uuid.uuid4()),
            "action": "GRIDFS_RESTORE",
            "entity_type": "database",
            "entity_id": "gridfs",
            "user_id": current_user["id"],
            "user_name": current_user["name"],
            "user_role": current_user.get("role", 5),
            "details": {
                "restored_count": restored_count,
                "skipped_count": skipped_count,
                "errors_count": len(errors)
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        return {
            "message": "GridFS restore completed",
            "restored_count": restored_count,
            "skipped_count": skipped_count,
            "errors": errors[:10] if errors else []  # Return first 10 errors
        }
    
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON in backup file: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error restoring GridFS files: {str(e)}")


@router.get("/gridfs/stats")
async def get_gridfs_stats(
    current_user: dict = Depends(get_current_user)
):
    """Get GridFS storage statistics (PE Level)"""
    if not is_pe_level(current_user.get("role", 6)):
        raise HTTPException(status_code=403, detail="Only PE Desk or PE Manager can view GridFS stats")
    
    # Count total files
    total_files = await db["fs.files"].count_documents({})
    
    # Get total size
    pipeline = [
        {"$group": {"_id": None, "total_size": {"$sum": "$length"}}}
    ]
    size_result = await db["fs.files"].aggregate(pipeline).to_list(1)
    total_size = size_result[0]["total_size"] if size_result else 0
    
    # Count by category
    category_pipeline = [
        {"$group": {
            "_id": "$metadata.category",
            "count": {"$sum": 1},
            "size": {"$sum": "$length"}
        }},
        {"$sort": {"count": -1}}
    ]
    categories = await db["fs.files"].aggregate(category_pipeline).to_list(100)
    
    return {
        "total_files": total_files,
        "total_size_bytes": total_size,
        "total_size_mb": round(total_size / (1024 * 1024), 2),
        "by_category": [
            {
                "category": c["_id"] or "uncategorized",
                "count": c["count"],
                "size_bytes": c["size"],
                "size_mb": round(c["size"] / (1024 * 1024), 2)
            }
            for c in categories
        ]
    }



# ============== ULTIMATE FULL SYSTEM BACKUP ==============

@router.post("/backups/ultimate")
async def create_ultimate_backup(
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("database_backup.full", "create ultimate backup"))
):
    """
    Create an ULTIMATE full system backup including:
    - ALL database collections
    - ALL GridFS files (stored as base64)
    - Environment settings
    - System configuration
    - Log file summaries
    
    This is the most comprehensive backup option.
    """
    backup_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    backup_name = f"Ultimate_Backup_{now.strftime('%Y%m%d_%H%M%S')}"
    
    backup_data = {}
    record_counts = {}
    total_size = 0
    errors = []
    
    # 1. Get ALL collections dynamically
    all_collections = await db.list_collection_names()
    collections_to_backup = [c for c in all_collections if c != "database_backups"]
    
    # 2. Backup each collection (excluding GridFS chunks which are binary)
    for collection_name in collections_to_backup:
        if collection_name == "fs.chunks":
            # Skip fs.chunks as we'll backup GridFS files separately
            continue
        try:
            collection = db[collection_name]
            documents = await collection.find({}, {"_id": 0}).to_list(100000)
            backup_data[collection_name] = documents
            record_counts[collection_name] = len(documents)
            total_size += len(json.dumps(documents, default=str))
        except Exception as e:
            errors.append(f"Error backing up {collection_name}: {str(e)}")
            backup_data[collection_name] = []
            record_counts[collection_name] = 0
    
    # 3. Backup GridFS files with base64 content
    gridfs_files = []
    gridfs_total_size = 0
    
    try:
        async for file_doc in db["fs.files"].find({}):
            file_id = str(file_doc["_id"])
            try:
                content, content_type = await download_file_from_gridfs(file_id)
                gridfs_files.append({
                    "file_id": file_id,
                    "filename": file_doc.get("filename", ""),
                    "length": file_doc.get("length", 0),
                    "content_type": content_type,
                    "upload_date": str(file_doc.get("uploadDate", "")),
                    "metadata": file_doc.get("metadata", {}),
                    "content_base64": base64.b64encode(content).decode('utf-8')
                })
                gridfs_total_size += file_doc.get("length", 0)
            except Exception as e:
                errors.append(f"Error backing up GridFS file {file_id}: {str(e)}")
    except Exception as e:
        errors.append(f"Error reading GridFS files: {str(e)}")
    
    # 4. Get environment/system settings
    env_settings = {}
    env_files = ["/app/backend/.env", "/app/frontend/.env"]
    for env_file in env_files:
        if os.path.exists(env_file):
            try:
                with open(env_file, 'r') as f:
                    # Don't include sensitive keys, just structure
                    content = f.read()
                    # Mask sensitive values
                    masked_lines = []
                    for line in content.split('\n'):
                        if '=' in line and not line.startswith('#'):
                            key = line.split('=')[0]
                            if any(sensitive in key.lower() for sensitive in ['key', 'secret', 'password', 'token']):
                                masked_lines.append(f"{key}=***MASKED***")
                            else:
                                masked_lines.append(line)
                        else:
                            masked_lines.append(line)
                    env_settings[env_file] = '\n'.join(masked_lines)
            except Exception as e:
                errors.append(f"Error reading {env_file}: {str(e)}")
    
    # 5. Get log file stats (not full content to save space)
    log_stats = {}
    log_dirs = ["/var/log/supervisor"]
    for log_dir in log_dirs:
        if os.path.exists(log_dir):
            try:
                for log_file in os.listdir(log_dir):
                    log_path = os.path.join(log_dir, log_file)
                    if os.path.isfile(log_path):
                        stat = os.stat(log_path)
                        log_stats[log_file] = {
                            "size_bytes": stat.st_size,
                            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
                        }
                        # Get last 50 lines of error logs
                        if 'err' in log_file.lower():
                            try:
                                with open(log_path, 'r') as f:
                                    lines = f.readlines()
                                    log_stats[log_file]["last_50_lines"] = ''.join(lines[-50:])
                            except:
                                pass
            except Exception as e:
                errors.append(f"Error reading logs from {log_dir}: {str(e)}")
    
    # 6. Get uploaded files from filesystem
    files_metadata = {}
    if os.path.exists(UPLOADS_DIR):
        for root, dirs, files in os.walk(UPLOADS_DIR):
            for filename in files:
                file_path = os.path.join(root, filename)
                rel_path = os.path.relpath(file_path, UPLOADS_DIR)
                try:
                    stat = os.stat(file_path)
                    files_metadata[rel_path] = {
                        "size_bytes": stat.st_size,
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
                    }
                except:
                    pass
    
    # Store the ultimate backup
    backup_doc = {
        "id": backup_id,
        "name": backup_name,
        "description": f"Ultimate backup - {len(collections_to_backup)} collections, {len(gridfs_files)} GridFS files",
        "created_at": now.isoformat(),
        "created_by": current_user["id"],
        "created_by_name": current_user["name"],
        "backup_type": "ultimate",
        "collections": collections_to_backup,
        "record_counts": record_counts,
        "size_bytes": total_size,
        "gridfs_files_count": len(gridfs_files),
        "gridfs_total_size": gridfs_total_size,
        "filesystem_files_count": len(files_metadata),
        "errors": errors,
        "data": backup_data,
        "gridfs_data": gridfs_files,
        "env_settings": env_settings,
        "log_stats": log_stats,
        "files_metadata": files_metadata
    }
    
    await db.database_backups.insert_one(backup_doc)
    
    # Log the action
    await db.audit_logs.insert_one({
        "id": str(uuid.uuid4()),
        "action": "ULTIMATE_BACKUP",
        "entity_type": "database",
        "entity_id": backup_id,
        "user_id": current_user["id"],
        "user_name": current_user["name"],
        "user_role": current_user.get("role", 5),
        "details": {
            "backup_name": backup_name,
            "collections_count": len(collections_to_backup),
            "gridfs_files_count": len(gridfs_files),
            "total_records": sum(record_counts.values()),
            "errors_count": len(errors)
        },
        "timestamp": now.isoformat()
    })
    
    return {
        "message": "Ultimate backup created successfully" if not errors else "Backup created with some warnings",
        "backup": {
            "id": backup_id,
            "name": backup_name,
            "collections_count": len(collections_to_backup),
            "total_records": sum(record_counts.values()),
            "gridfs_files": len(gridfs_files),
            "gridfs_size_mb": round(gridfs_total_size / (1024 * 1024), 2),
            "filesystem_files": len(files_metadata),
            "size_bytes": total_size
        },
        "warnings": errors[:10] if errors else [],
        "download_url": f"/api/database/backups/{backup_id}/download-ultimate"
    }


@router.get("/backups/{backup_id}/download-ultimate")
async def download_ultimate_backup(
    backup_id: str,
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("database_backup.view", "download ultimate backup"))
):
    """
    Download an ultimate backup as a comprehensive ZIP file.
    Includes database, GridFS files, settings, and logs.
    """
    # Get backup
    backup = await db.database_backups.find_one({"id": backup_id}, {"_id": 0})
    
    if not backup:
        raise HTTPException(status_code=404, detail="Backup not found")
    
    # Create ZIP in memory
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        # 1. Add metadata
        metadata = {
            "id": backup["id"],
            "name": backup["name"],
            "description": backup.get("description"),
            "created_at": backup["created_at"],
            "created_by_name": backup["created_by_name"],
            "backup_type": backup.get("backup_type", "standard"),
            "collections": backup.get("collections", []),
            "record_counts": backup.get("record_counts", {}),
            "gridfs_files_count": backup.get("gridfs_files_count", 0),
            "filesystem_files_count": backup.get("filesystem_files_count", 0),
            "backup_version": "3.0-ultimate"
        }
        zip_file.writestr("metadata.json", json.dumps(metadata, indent=2))
        
        # 2. Add database collections
        backup_data = backup.get("data", {})
        for collection_name, documents in backup_data.items():
            json_content = json.dumps(documents, indent=2, default=str)
            zip_file.writestr(f"database/{collection_name}.json", json_content)
        
        # 3. Add GridFS files (decode base64 and store as actual files)
        gridfs_data = backup.get("gridfs_data", [])
        gridfs_manifest = []
        for gf in gridfs_data:
            try:
                content = base64.b64decode(gf.get("content_base64", ""))
                category = gf.get("metadata", {}).get("category", "uncategorized")
                filename = gf.get("filename", gf["file_id"])
                zip_path = f"gridfs/{category}/{filename}"
                zip_file.writestr(zip_path, content)
                
                # Add to manifest (without base64 content)
                manifest_entry = {k: v for k, v in gf.items() if k != "content_base64"}
                manifest_entry["zip_path"] = zip_path
                gridfs_manifest.append(manifest_entry)
            except Exception as e:
                gridfs_manifest.append({
                    "file_id": gf.get("file_id"),
                    "error": str(e)
                })
        
        zip_file.writestr("gridfs/manifest.json", json.dumps(gridfs_manifest, indent=2, default=str))
        
        # 4. Add environment settings
        env_settings = backup.get("env_settings", {})
        for env_file, content in env_settings.items():
            safe_name = env_file.replace("/", "_").replace("\\", "_")
            zip_file.writestr(f"settings/{safe_name}", content)
        
        # 5. Add log stats
        log_stats = backup.get("log_stats", {})
        zip_file.writestr("logs/log_stats.json", json.dumps(log_stats, indent=2, default=str))
        
        # 6. Add filesystem files metadata
        files_metadata = backup.get("files_metadata", {})
        zip_file.writestr("uploads/files_metadata.json", json.dumps(files_metadata, indent=2))
        
        # 7. Add actual upload files if they exist
        if os.path.exists(UPLOADS_DIR):
            for root, dirs, files in os.walk(UPLOADS_DIR):
                for filename in files:
                    file_path = os.path.join(root, filename)
                    rel_path = os.path.relpath(file_path, UPLOADS_DIR)
                    try:
                        zip_file.write(file_path, f"uploads/{rel_path}")
                    except Exception:
                        pass
        
        # 8. Add restore instructions
        restore_instructions = """
# Ultimate Backup Restore Instructions

## Contents
- /database/ - All MongoDB collections as JSON files
- /gridfs/ - All GridFS files with manifest.json
- /settings/ - Environment configuration files (sensitive values masked)
- /logs/ - Log file statistics and recent error logs
- /uploads/ - All uploaded files from filesystem

## How to Restore

### Option 1: Use the API
POST /api/database/restore-from-file
- Upload this ZIP file
- All database collections will be restored

### Option 2: Manual Restore
1. Import each JSON file in /database/ to MongoDB
2. Upload files from /gridfs/ using the GridFS restore API
3. Copy files from /uploads/ to /app/uploads/

### Important Notes
- The super admin user (pe@smifs.com) is preserved during restore
- GridFS files include metadata for proper re-linking
- Environment files have sensitive values masked for security

## Backup Info
Created: {created_at}
By: {created_by}
Collections: {collections_count}
GridFS Files: {gridfs_count}
        """.format(
            created_at=backup["created_at"],
            created_by=backup["created_by_name"],
            collections_count=len(backup.get("collections", [])),
            gridfs_count=backup.get("gridfs_files_count", 0)
        )
        zip_file.writestr("RESTORE_INSTRUCTIONS.md", restore_instructions)
    
    zip_buffer.seek(0)
    
    # Generate filename
    safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in backup["name"])
    filename = f"{safe_name}_{backup['created_at'][:10]}.zip"
    
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.post("/restore-ultimate")
async def restore_ultimate_backup(
    file: UploadFile = File(...),
    restore_gridfs: bool = True,
    restore_files: bool = True,
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("database_backup.restore", "restore ultimate backup"))
):
    """
    Restore from an ultimate backup ZIP file.
    
    Args:
        file: The ultimate backup ZIP file
        restore_gridfs: If True, restore GridFS files
        restore_files: If True, restore filesystem files
    """
    if not file.filename.endswith('.zip'):
        raise HTTPException(status_code=400, detail="Please upload a ZIP file")
    
    try:
        content = await file.read()
        zip_buffer = io.BytesIO(content)
        
        restored = {
            "collections": {},
            "gridfs_files": 0,
            "upload_files": 0
        }
        errors = []
        
        with zipfile.ZipFile(zip_buffer, 'r') as zip_file:
            # Read metadata
            if "metadata.json" not in zip_file.namelist():
                raise HTTPException(status_code=400, detail="Invalid backup: missing metadata.json")
            
            metadata = json.loads(zip_file.read("metadata.json"))
            
            # 1. Restore database collections
            for filename in zip_file.namelist():
                if filename.startswith("database/") and filename.endswith(".json"):
                    collection_name = filename.replace("database/", "").replace(".json", "")
                    
                    if collection_name == "database_backups":
                        continue
                    
                    try:
                        documents = json.loads(zip_file.read(filename))
                        collection = db[collection_name]
                        
                        if collection_name == "users":
                            await collection.delete_many({"email": {"$ne": "pe@smifs.com"}})
                            users_to_insert = [d for d in documents if d.get("email") != "pe@smifs.com"]
                            if users_to_insert:
                                await collection.insert_many(users_to_insert)
                            restored["collections"][collection_name] = len(users_to_insert)
                        else:
                            await collection.delete_many({})
                            if documents:
                                await collection.insert_many(documents)
                            restored["collections"][collection_name] = len(documents)
                    except Exception as e:
                        errors.append(f"Error restoring {collection_name}: {str(e)}")
            
            # 2. Restore GridFS files
            if restore_gridfs and "gridfs/manifest.json" in zip_file.namelist():
                try:
                    manifest = json.loads(zip_file.read("gridfs/manifest.json"))
                    
                    for file_info in manifest:
                        if file_info.get("error"):
                            continue
                        
                        zip_path = file_info.get("zip_path")
                        if zip_path and zip_path in zip_file.namelist():
                            try:
                                file_content = zip_file.read(zip_path)
                                await upload_file_to_gridfs(
                                    file_content,
                                    file_info.get("filename", ""),
                                    file_info.get("content_type", "application/octet-stream"),
                                    file_info.get("metadata", {})
                                )
                                restored["gridfs_files"] += 1
                            except Exception as e:
                                errors.append(f"Error restoring GridFS file: {str(e)}")
                except Exception as e:
                    errors.append(f"Error processing GridFS manifest: {str(e)}")
            
            # 3. Restore filesystem files
            if restore_files:
                for filename in zip_file.namelist():
                    if filename.startswith("uploads/") and not filename.endswith("/") and not filename.endswith(".json"):
                        try:
                            rel_path = filename[8:]  # Remove "uploads/" prefix
                            target_path = os.path.join(UPLOADS_DIR, rel_path)
                            target_dir = os.path.dirname(target_path)
                            os.makedirs(target_dir, exist_ok=True)
                            
                            with zip_file.open(filename) as src:
                                with open(target_path, 'wb') as dst:
                                    dst.write(src.read())
                            restored["upload_files"] += 1
                        except Exception as e:
                            errors.append(f"Error restoring file {filename}: {str(e)}")
        
        # Log the restore
        await db.audit_logs.insert_one({
            "id": str(uuid.uuid4()),
            "action": "ULTIMATE_RESTORE",
            "entity_type": "database",
            "entity_id": metadata.get("id", "uploaded"),
            "user_id": current_user["id"],
            "user_name": current_user["name"],
            "user_role": current_user.get("role", 5),
            "details": {
                "backup_name": metadata.get("name"),
                "restored_collections": len(restored["collections"]),
                "restored_gridfs": restored["gridfs_files"],
                "restored_files": restored["upload_files"],
                "errors_count": len(errors)
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        return {
            "message": "Ultimate restore completed successfully" if not errors else "Restore completed with some warnings",
            "backup_info": {
                "name": metadata.get("name"),
                "original_date": metadata.get("created_at"),
                "backup_version": metadata.get("backup_version")
            },
            "restored": restored,
            "total_collections": len(restored["collections"]),
            "total_records": sum(restored["collections"].values()),
            "errors": errors[:20] if errors else []
        }
    
    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="Invalid ZIP file")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing backup: {str(e)}")
