#!/usr/bin/env python3

import asyncio
import os
import uuid
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
ROOT_DIR = Path(__file__).parent / 'backend'
load_dotenv(ROOT_DIR / '.env')

def generate_otc_ucc():
    """Generate unique OTC UCC code"""
    date_part = datetime.now(timezone.utc).strftime("%Y%m%d")
    unique_part = str(uuid.uuid4())[:8].upper()
    return f"OTC{date_part}{unique_part}"

async def fix_clients_otc_ucc():
    """Add OTC UCC codes to existing clients that don't have them"""
    
    # MongoDB connection
    mongo_url = os.environ['MONGO_URL']
    client = AsyncIOMotorClient(mongo_url)
    db = client[os.environ['DB_NAME']]
    
    try:
        # Find clients without otc_ucc field
        clients_without_otc = await db.clients.find({"otc_ucc": {"$exists": False}}).to_list(1000)
        
        print(f"Found {len(clients_without_otc)} clients without OTC UCC codes")
        
        updated_count = 0
        for client in clients_without_otc:
            otc_ucc = generate_otc_ucc()
            
            result = await db.clients.update_one(
                {"id": client["id"]},
                {"$set": {"otc_ucc": otc_ucc}}
            )
            
            if result.modified_count > 0:
                updated_count += 1
                print(f"Updated client {client['name']} with OTC UCC: {otc_ucc}")
        
        print(f"Successfully updated {updated_count} clients with OTC UCC codes")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(fix_clients_otc_ucc())