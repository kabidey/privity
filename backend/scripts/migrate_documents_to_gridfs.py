"""
Migration Script: Re-upload documents with missing file_id to GridFS

This script:
1. Finds all clients with documents that have file_id: None or missing
2. Checks if the local file still exists
3. If it exists, uploads to GridFS and updates the record
4. Creates a migration report

Run with: python scripts/migrate_documents_to_gridfs.py
"""
import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime, timezone

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from motor.motor_asyncio import AsyncIOMotorClient
from services.file_storage import upload_file_to_gridfs, get_file_url

# Configuration
MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
DB_NAME = os.environ.get('DB_NAME', 'test_database')
UPLOAD_DIR = Path("/app/uploads")


async def migrate_documents():
    """Main migration function"""
    print("=" * 60)
    print("Document Migration to GridFS")
    print("=" * 60)
    print(f"MongoDB: {MONGO_URL}")
    print(f"Database: {DB_NAME}")
    print(f"Upload Directory: {UPLOAD_DIR}")
    print()
    
    # Connect to MongoDB
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    # Statistics
    stats = {
        "total_clients_checked": 0,
        "clients_with_docs": 0,
        "docs_already_migrated": 0,
        "docs_migrated": 0,
        "docs_file_missing": 0,
        "docs_failed": 0,
        "errors": []
    }
    
    # Find all clients with documents
    clients_cursor = db.clients.find(
        {"documents": {"$exists": True, "$ne": []}},
        {"_id": 0, "id": 1, "name": 1, "documents": 1}
    )
    
    clients = await clients_cursor.to_list(None)
    stats["total_clients_checked"] = await db.clients.count_documents({})
    stats["clients_with_docs"] = len(clients)
    
    print(f"Found {len(clients)} clients with documents")
    print()
    
    for client_data in clients:
        client_id = client_data.get("id")
        client_name = client_data.get("name", "Unknown")[:40]
        documents = client_data.get("documents", [])
        
        print(f"Processing: {client_name} ({client_id})")
        
        updated_documents = []
        needs_update = False
        
        for doc in documents:
            doc_type = doc.get("doc_type", "unknown")
            file_id = doc.get("file_id")
            file_path = doc.get("file_path")
            filename = doc.get("filename", "unknown")
            
            # Check if already migrated
            if file_id and file_id != "None" and file_id != "null":
                print(f"  ✓ {doc_type}: Already migrated (file_id: {file_id[:12]}...)")
                stats["docs_already_migrated"] += 1
                updated_documents.append(doc)
                continue
            
            # Try to find and upload the file
            print(f"  → {doc_type}: Needs migration")
            
            # Check if local file exists
            local_path = None
            if file_path and Path(file_path).exists():
                local_path = Path(file_path)
            elif client_id:
                # Try to find in client directory
                client_dir = UPLOAD_DIR / client_id
                if client_dir.exists():
                    # Look for file matching doc_type
                    for f in client_dir.iterdir():
                        if f.name.startswith(doc_type) or f.name == filename:
                            local_path = f
                            break
            
            if local_path and local_path.exists():
                try:
                    # Read file content
                    with open(local_path, 'rb') as f:
                        content = f.read()
                    
                    # Determine content type
                    suffix = local_path.suffix.lower()
                    content_type_map = {
                        '.pdf': 'application/pdf',
                        '.png': 'image/png',
                        '.jpg': 'image/jpeg',
                        '.jpeg': 'image/jpeg',
                        '.gif': 'image/gif',
                        '.txt': 'text/plain',
                    }
                    content_type = content_type_map.get(suffix, 'application/octet-stream')
                    
                    # Upload to GridFS
                    new_file_id = await upload_file_to_gridfs(
                        content,
                        local_path.name,
                        content_type,
                        {
                            "category": "client_documents",
                            "entity_id": client_id,
                            "doc_type": doc_type,
                            "migrated_at": datetime.now(timezone.utc).isoformat(),
                            "migration_source": "migrate_documents_to_gridfs.py"
                        }
                    )
                    
                    # Update document record
                    doc["file_id"] = new_file_id
                    doc["file_url"] = get_file_url(new_file_id)
                    doc["migrated_at"] = datetime.now(timezone.utc).isoformat()
                    
                    print(f"    ✓ Uploaded to GridFS: {new_file_id[:12]}...")
                    stats["docs_migrated"] += 1
                    needs_update = True
                    
                except Exception as e:
                    print(f"    ✗ Error uploading: {str(e)}")
                    stats["docs_failed"] += 1
                    stats["errors"].append({
                        "client_id": client_id,
                        "doc_type": doc_type,
                        "error": str(e)
                    })
            else:
                print(f"    ✗ Local file not found: {file_path}")
                stats["docs_file_missing"] += 1
                doc["migration_status"] = "file_missing"
                doc["migration_checked_at"] = datetime.now(timezone.utc).isoformat()
                needs_update = True
            
            updated_documents.append(doc)
        
        # Update client document if needed
        if needs_update:
            await db.clients.update_one(
                {"id": client_id},
                {"$set": {"documents": updated_documents}}
            )
            print(f"  → Updated client record")
        
        print()
    
    # Print summary
    print("=" * 60)
    print("Migration Summary")
    print("=" * 60)
    print(f"Total clients in database: {stats['total_clients_checked']}")
    print(f"Clients with documents: {stats['clients_with_docs']}")
    print(f"Documents already migrated: {stats['docs_already_migrated']}")
    print(f"Documents migrated now: {stats['docs_migrated']}")
    print(f"Documents with missing files: {stats['docs_file_missing']}")
    print(f"Documents failed to migrate: {stats['docs_failed']}")
    
    if stats["errors"]:
        print()
        print("Errors:")
        for err in stats["errors"]:
            print(f"  - Client {err['client_id']}, {err['doc_type']}: {err['error']}")
    
    print()
    print("Migration complete!")
    
    client.close()
    return stats


if __name__ == "__main__":
    asyncio.run(migrate_documents())
