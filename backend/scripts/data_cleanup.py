"""
Data Cleanup Script for PRIVITY
Identifies and fixes data quality issues in inventory and stocks collections.

Issues addressed:
1. Inventory items with stock_symbol = "Unknown" (orphaned records)
2. Inventory items with landing_price = None (missing LP)
3. Stocks without landing_price field

Run this script via the API endpoint or directly:
    python -m scripts.data_cleanup
"""
import asyncio
import logging
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

# Load environment
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def get_database():
    """Get database connection"""
    mongo_url = os.environ.get('MONGO_URL')
    db_name = os.environ.get('DB_NAME', 'test_database')
    client = AsyncIOMotorClient(mongo_url)
    return client, client[db_name]


async def cleanup_orphaned_inventory(db, dry_run=True):
    """
    Remove inventory records where the referenced stock no longer exists.
    These are identified by stock_symbol = "Unknown".
    
    Args:
        db: Database instance
        dry_run: If True, only report issues without making changes
    
    Returns:
        dict with cleanup results
    """
    results = {
        "orphaned_found": 0,
        "orphaned_deleted": 0,
        "orphan_details": []
    }
    
    # Find inventory with Unknown stock_symbol
    orphaned_cursor = db.inventory.find(
        {"$or": [
            {"stock_symbol": "Unknown"},
            {"stock_symbol": {"$exists": False}},
            {"stock_symbol": None}
        ]},
        {"_id": 0, "stock_id": 1, "stock_symbol": 1}
    )
    
    orphaned = await orphaned_cursor.to_list(1000)
    results["orphaned_found"] = len(orphaned)
    
    for item in orphaned:
        stock_id = item.get("stock_id")
        
        # Double-check if stock really doesn't exist
        stock = await db.stocks.find_one({"id": stock_id}, {"_id": 0, "symbol": 1, "name": 1})
        
        if stock:
            # Stock exists - fix the inventory record
            if not dry_run:
                await db.inventory.update_one(
                    {"stock_id": stock_id},
                    {"$set": {
                        "stock_symbol": stock.get("symbol"),
                        "stock_name": stock.get("name", stock.get("symbol")),
                        "updated_at": datetime.now(timezone.utc).isoformat()
                    }}
                )
            results["orphan_details"].append({
                "stock_id": stock_id,
                "action": "fixed" if not dry_run else "would_fix",
                "new_symbol": stock.get("symbol")
            })
        else:
            # Stock doesn't exist - delete orphaned inventory record
            if not dry_run:
                await db.inventory.delete_one({"stock_id": stock_id})
            results["orphaned_deleted"] += 1
            results["orphan_details"].append({
                "stock_id": stock_id,
                "action": "deleted" if not dry_run else "would_delete"
            })
    
    return results


async def fix_missing_landing_prices(db, dry_run=True):
    """
    Fix inventory items with missing or zero landing_price.
    Sets landing_price to weighted_avg_price as a fallback.
    
    Args:
        db: Database instance
        dry_run: If True, only report issues without making changes
    
    Returns:
        dict with fix results
    """
    results = {
        "missing_lp_found": 0,
        "lp_fixed": 0,
        "lp_unfixable": 0,
        "details": []
    }
    
    # Find inventory with missing or zero landing_price
    missing_lp_cursor = db.inventory.find(
        {"$or": [
            {"landing_price": {"$exists": False}},
            {"landing_price": None},
            {"landing_price": 0}
        ]},
        {"_id": 0}
    )
    
    missing_lp = await missing_lp_cursor.to_list(1000)
    results["missing_lp_found"] = len(missing_lp)
    
    for item in missing_lp:
        stock_id = item.get("stock_id")
        wap = item.get("weighted_avg_price", 0)
        stock_symbol = item.get("stock_symbol", "Unknown")
        
        # Try to get LP from stocks master collection
        stock = await db.stocks.find_one({"id": stock_id}, {"_id": 0, "landing_price": 1, "symbol": 1})
        master_lp = stock.get("landing_price") if stock else None
        
        # Determine the best fallback price
        fallback_price = None
        source = None
        
        if master_lp and master_lp > 0:
            fallback_price = master_lp
            source = "stocks_master"
        elif wap and wap > 0:
            fallback_price = wap
            source = "weighted_avg_price"
        
        if fallback_price and fallback_price > 0:
            if not dry_run:
                await db.inventory.update_one(
                    {"stock_id": stock_id},
                    {"$set": {
                        "landing_price": round(fallback_price, 2),
                        "landing_price_source": source,
                        "landing_price_auto_set": True,
                        "updated_at": datetime.now(timezone.utc).isoformat()
                    }}
                )
            results["lp_fixed"] += 1
            results["details"].append({
                "stock_id": stock_id,
                "stock_symbol": stock_symbol,
                "action": "fixed" if not dry_run else "would_fix",
                "new_lp": round(fallback_price, 2),
                "source": source
            })
        else:
            results["lp_unfixable"] += 1
            results["details"].append({
                "stock_id": stock_id,
                "stock_symbol": stock_symbol,
                "action": "unfixable",
                "reason": "No WAP or master LP available"
            })
    
    return results


async def validate_inventory_stock_references(db, dry_run=True):
    """
    Ensure all inventory stock_id references point to valid stocks.
    Updates stock_symbol and stock_name from the stocks collection.
    
    Args:
        db: Database instance
        dry_run: If True, only report issues without making changes
    
    Returns:
        dict with validation results
    """
    results = {
        "total_inventory": 0,
        "valid_references": 0,
        "updated_metadata": 0,
        "invalid_references": 0,
        "details": []
    }
    
    inventory = await db.inventory.find({}, {"_id": 0}).to_list(10000)
    results["total_inventory"] = len(inventory)
    
    for item in inventory:
        stock_id = item.get("stock_id")
        current_symbol = item.get("stock_symbol")
        
        # Look up the stock
        stock = await db.stocks.find_one({"id": stock_id}, {"_id": 0, "symbol": 1, "name": 1})
        
        if stock:
            results["valid_references"] += 1
            
            # Check if metadata needs updating
            if current_symbol != stock.get("symbol") or item.get("stock_name") != stock.get("name"):
                if not dry_run:
                    await db.inventory.update_one(
                        {"stock_id": stock_id},
                        {"$set": {
                            "stock_symbol": stock.get("symbol"),
                            "stock_name": stock.get("name"),
                            "updated_at": datetime.now(timezone.utc).isoformat()
                        }}
                    )
                results["updated_metadata"] += 1
                results["details"].append({
                    "stock_id": stock_id,
                    "old_symbol": current_symbol,
                    "new_symbol": stock.get("symbol"),
                    "action": "metadata_updated" if not dry_run else "would_update"
                })
        else:
            results["invalid_references"] += 1
    
    return results


async def generate_data_quality_report(db):
    """
    Generate a comprehensive data quality report without making changes.
    
    Returns:
        dict with full report
    """
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {},
        "issues": {}
    }
    
    # Count totals
    total_stocks = await db.stocks.count_documents({})
    total_inventory = await db.inventory.count_documents({})
    
    report["summary"]["total_stocks"] = total_stocks
    report["summary"]["total_inventory"] = total_inventory
    
    # Check for orphaned inventory
    orphaned_count = await db.inventory.count_documents({
        "$or": [
            {"stock_symbol": "Unknown"},
            {"stock_symbol": {"$exists": False}},
            {"stock_symbol": None}
        ]
    })
    report["issues"]["orphaned_inventory"] = orphaned_count
    
    # Check for missing landing prices in inventory
    missing_lp_inv = await db.inventory.count_documents({
        "$or": [
            {"landing_price": {"$exists": False}},
            {"landing_price": None},
            {"landing_price": 0}
        ]
    })
    report["issues"]["inventory_missing_lp"] = missing_lp_inv
    
    # Check for missing landing prices in stocks
    missing_lp_stocks = await db.stocks.count_documents({
        "$or": [
            {"landing_price": {"$exists": False}},
            {"landing_price": None}
        ]
    })
    report["issues"]["stocks_missing_lp"] = missing_lp_stocks
    
    # Check for inventory without WAP
    missing_wap = await db.inventory.count_documents({
        "$or": [
            {"weighted_avg_price": {"$exists": False}},
            {"weighted_avg_price": None},
            {"weighted_avg_price": 0}
        ]
    })
    report["issues"]["inventory_missing_wap"] = missing_wap
    
    # Calculate health score (0-100)
    total_issues = orphaned_count + missing_lp_inv + missing_lp_stocks
    max_possible_issues = total_inventory + total_inventory + total_stocks
    if max_possible_issues > 0:
        health_score = round((1 - (total_issues / max_possible_issues)) * 100, 1)
    else:
        health_score = 100
    
    report["summary"]["health_score"] = health_score
    report["summary"]["total_issues"] = total_issues
    
    return report


async def run_full_cleanup(dry_run=True):
    """
    Run all cleanup operations.
    
    Args:
        dry_run: If True, only report issues without making changes
    
    Returns:
        dict with all results
    """
    client, db = await get_database()
    
    try:
        results = {
            "dry_run": dry_run,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "report_before": await generate_data_quality_report(db),
            "orphaned_cleanup": await cleanup_orphaned_inventory(db, dry_run),
            "landing_price_fix": await fix_missing_landing_prices(db, dry_run),
            "reference_validation": await validate_inventory_stock_references(db, dry_run)
        }
        
        if not dry_run:
            results["report_after"] = await generate_data_quality_report(db)
        
        return results
    finally:
        client.close()


# CLI entry point
if __name__ == "__main__":
    import argparse
    import json
    
    parser = argparse.ArgumentParser(description="PRIVITY Data Cleanup Tool")
    parser.add_argument("--dry-run", action="store_true", default=True,
                        help="Run in dry-run mode (default: True)")
    parser.add_argument("--apply", action="store_true",
                        help="Actually apply changes (disables dry-run)")
    parser.add_argument("--report-only", action="store_true",
                        help="Only generate report, don't attempt fixes")
    
    args = parser.parse_args()
    
    async def main():
        if args.report_only:
            client, db = await get_database()
            try:
                report = await generate_data_quality_report(db)
                print(json.dumps(report, indent=2))
            finally:
                client.close()
        else:
            dry_run = not args.apply
            results = await run_full_cleanup(dry_run=dry_run)
            print(json.dumps(results, indent=2, default=str))
    
    asyncio.run(main())
