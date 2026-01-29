"""
Bulk Upload Router
Handles CSV bulk uploads for Clients, Vendors, Stocks, Purchases, and Bookings
PE Desk only access
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from typing import Optional, List
from datetime import datetime, timezone
import uuid
import csv
import io

from database import db
from routers.auth import get_current_user
from config import is_pe_desk_only

router = APIRouter(prefix="/bulk-upload", tags=["Bulk Upload"])


# ============== Sample CSV Templates ==============

SAMPLE_TEMPLATES = {
    "clients": {
        "headers": ["name", "email", "email_secondary", "phone", "mobile", "pan_number", "dp_id", "dp_type", "trading_ucc", "address", "pin_code"],
        "sample_rows": [
            ["John Doe", "john@example.com", "john.secondary@example.com", "0221234567", "9876543210", "ABCDE1234F", "12345678", "outside", "", "123 Main Street, Mumbai", "400001"],
            ["Jane Smith", "jane@example.com", "", "", "9876543211", "FGHIJ5678K", "87654321", "smifs", "SMF123456", "456 Park Avenue, Delhi", "110001"],
        ],
        "description": "Client bulk upload template. PAN number and DP ID are required. dp_type can be 'smifs' or 'outside'. trading_ucc is required if dp_type is 'smifs'."
    },
    "vendors": {
        "headers": ["name", "email", "email_secondary", "phone", "mobile", "pan_number", "dp_id", "dp_type", "address", "pin_code"],
        "sample_rows": [
            ["Vendor Corp Ltd", "vendor@example.com", "", "0221234567", "9876543210", "VNDOR1234F", "12345678", "outside", "789 Industrial Area, Pune", "411001"],
            ["Supply House Pvt", "supply@example.com", "", "", "9876543211", "SPLHS5678K", "87654321", "outside", "321 Trade Zone, Chennai", "600001"],
        ],
        "description": "Vendor bulk upload template. PAN number and DP ID are required. Vendors are clients with is_vendor=True."
    },
    "stocks": {
        "headers": ["symbol", "name", "exchange", "isin_number", "sector", "product", "face_value"],
        "sample_rows": [
            ["UNLISTED1", "Unlisted Company One Ltd", "OTC", "INE123A01234", "Technology", "Equity", "10"],
            ["UNLISTED2", "Unlisted Company Two Pvt", "OTC", "INE456B05678", "Finance", "Equity", "5"],
        ],
        "description": "Stock bulk upload template. Symbol and Name are required. ISIN must be unique if provided."
    },
    "purchases": {
        "headers": ["vendor_pan", "stock_symbol", "quantity", "price_per_unit", "purchase_date", "notes"],
        "sample_rows": [
            ["VNDOR1234F", "UNLISTED1", "1000", "100.50", "2026-01-15", "Initial purchase from vendor"],
            ["SPLHS5678K", "UNLISTED2", "500", "250.00", "2026-01-20", "Second batch"],
        ],
        "description": "Purchase bulk upload template. vendor_pan must match existing vendor. stock_symbol must match existing stock. Date format: YYYY-MM-DD."
    },
    "bookings": {
        "headers": ["client_pan", "stock_symbol", "quantity", "selling_price", "booking_date", "booking_type", "notes"],
        "sample_rows": [
            ["ABCDE1234F", "UNLISTED1", "100", "150.00", "2026-01-25", "client", "First booking for client"],
            ["FGHIJ5678K", "UNLISTED2", "50", "300.00", "2026-01-26", "client", "Booking for Jane"],
        ],
        "description": "Booking bulk upload template. client_pan must match existing client. stock_symbol must match existing stock. booking_type can be 'client', 'team', or 'own'. Date format: YYYY-MM-DD."
    }
}


def generate_csv_content(entity_type: str) -> str:
    """Generate CSV content for sample template"""
    template = SAMPLE_TEMPLATES.get(entity_type)
    if not template:
        raise ValueError(f"Unknown entity type: {entity_type}")
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write description as comment
    writer.writerow([f"# {template['description']}"])
    writer.writerow([])  # Empty row
    
    # Write headers
    writer.writerow(template['headers'])
    
    # Write sample rows
    for row in template['sample_rows']:
        writer.writerow(row)
    
    return output.getvalue()


async def generate_otc_ucc() -> str:
    """Generate unique OTC UCC code"""
    counter = await db.counters.find_one_and_update(
        {"_id": "otc_ucc"},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=True
    )
    seq = counter.get("seq", 1)
    return f"OTC{str(seq).zfill(6)}"


async def generate_booking_number() -> str:
    """Generate unique booking number"""
    now = datetime.now()
    year = now.year
    
    counter = await db.counters.find_one_and_update(
        {"_id": f"booking_{year}"},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=True
    )
    seq = counter.get("seq", 1)
    return f"BK-{year}-{str(seq).zfill(5)}"


# ============== Download Sample Templates ==============

@router.get("/template/{entity_type}")
async def download_sample_template(
    entity_type: str,
    current_user: dict = Depends(get_current_user)
):
    """Download sample CSV template for bulk upload (PE Desk only)"""
    if not is_pe_desk_only(current_user.get("role", 6)):
        raise HTTPException(status_code=403, detail="Only PE Desk can access bulk upload")
    
    if entity_type not in SAMPLE_TEMPLATES:
        raise HTTPException(status_code=400, detail=f"Invalid entity type. Valid types: {', '.join(SAMPLE_TEMPLATES.keys())}")
    
    csv_content = generate_csv_content(entity_type)
    
    return StreamingResponse(
        io.StringIO(csv_content),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=sample_{entity_type}_upload.csv"
        }
    )


@router.get("/templates")
async def list_templates(current_user: dict = Depends(get_current_user)):
    """List all available bulk upload templates (PE Desk only)"""
    if not is_pe_desk_only(current_user.get("role", 6)):
        raise HTTPException(status_code=403, detail="Only PE Desk can access bulk upload")
    
    return {
        "templates": [
            {
                "entity_type": key,
                "description": val["description"],
                "required_fields": val["headers"][:6],  # First 6 as required indicator
                "download_url": f"/api/bulk-upload/template/{key}"
            }
            for key, val in SAMPLE_TEMPLATES.items()
        ]
    }


# ============== Bulk Upload Endpoints ==============

@router.post("/clients")
async def bulk_upload_clients(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """Bulk upload clients from CSV (PE Desk only). Skips duplicates by PAN number."""
    if not is_pe_desk_only(current_user.get("role", 6)):
        raise HTTPException(status_code=403, detail="Only PE Desk can perform bulk uploads")
    
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed")
    
    content = await file.read()
    decoded = content.decode('utf-8-sig')  # Handle BOM
    reader = csv.DictReader(io.StringIO(decoded))
    
    results = {"added": 0, "skipped": 0, "errors": [], "skipped_pans": []}
    
    for row_num, row in enumerate(reader, start=2):
        try:
            # Skip comment rows
            if row.get('name', '').startswith('#'):
                continue
            
            # Validate required fields
            name = row.get('name', '').strip()
            pan_number = row.get('pan_number', '').strip().upper()
            dp_id = row.get('dp_id', '').strip()
            
            if not name or not pan_number or not dp_id:
                results["errors"].append(f"Row {row_num}: Missing required fields (name, pan_number, dp_id)")
                continue
            
            # Check for duplicate PAN
            existing = await db.clients.find_one({"pan_number": pan_number, "is_vendor": False})
            if existing:
                results["skipped"] += 1
                results["skipped_pans"].append(pan_number)
                continue
            
            # Create client
            otc_ucc = await generate_otc_ucc()
            client_doc = {
                "id": str(uuid.uuid4()),
                "otc_ucc": otc_ucc,
                "name": name,
                "email": row.get('email', '').strip() or None,
                "email_secondary": row.get('email_secondary', '').strip() or None,
                "phone": row.get('phone', '').strip() or None,
                "mobile": row.get('mobile', '').strip() or None,
                "pan_number": pan_number,
                "dp_id": dp_id,
                "dp_type": row.get('dp_type', 'outside').strip().lower() or "outside",
                "trading_ucc": row.get('trading_ucc', '').strip() or None,
                "address": row.get('address', '').strip() or None,
                "pin_code": row.get('pin_code', '').strip() or None,
                "bank_accounts": [],
                "is_vendor": False,
                "is_active": True,
                "approval_status": "approved",
                "is_suspended": False,
                "documents": [],
                "created_at": datetime.now(timezone.utc).isoformat(),
                "created_by": current_user["id"],
                "created_by_role": current_user.get("role", 1)
            }
            
            await db.clients.insert_one(client_doc)
            results["added"] += 1
            
        except Exception as e:
            results["errors"].append(f"Row {row_num}: {str(e)}")
    
    return {
        "message": f"Bulk upload completed. Added: {results['added']}, Skipped (duplicates): {results['skipped']}",
        "added": results["added"],
        "skipped": results["skipped"],
        "skipped_pans": results["skipped_pans"][:10],  # Show first 10
        "errors": results["errors"][:10]  # Show first 10 errors
    }


@router.post("/vendors")
async def bulk_upload_vendors(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """Bulk upload vendors from CSV (PE Desk only). Skips duplicates by PAN number."""
    if not is_pe_desk_only(current_user.get("role", 6)):
        raise HTTPException(status_code=403, detail="Only PE Desk can perform bulk uploads")
    
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed")
    
    content = await file.read()
    decoded = content.decode('utf-8-sig')
    reader = csv.DictReader(io.StringIO(decoded))
    
    results = {"added": 0, "skipped": 0, "errors": [], "skipped_pans": []}
    
    for row_num, row in enumerate(reader, start=2):
        try:
            if row.get('name', '').startswith('#'):
                continue
            
            name = row.get('name', '').strip()
            pan_number = row.get('pan_number', '').strip().upper()
            dp_id = row.get('dp_id', '').strip()
            
            if not name or not pan_number or not dp_id:
                results["errors"].append(f"Row {row_num}: Missing required fields (name, pan_number, dp_id)")
                continue
            
            # Check for duplicate PAN (vendor)
            existing = await db.clients.find_one({"pan_number": pan_number, "is_vendor": True})
            if existing:
                results["skipped"] += 1
                results["skipped_pans"].append(pan_number)
                continue
            
            otc_ucc = await generate_otc_ucc()
            vendor_doc = {
                "id": str(uuid.uuid4()),
                "otc_ucc": otc_ucc,
                "name": name,
                "email": row.get('email', '').strip() or None,
                "email_secondary": row.get('email_secondary', '').strip() or None,
                "phone": row.get('phone', '').strip() or None,
                "mobile": row.get('mobile', '').strip() or None,
                "pan_number": pan_number,
                "dp_id": dp_id,
                "dp_type": row.get('dp_type', 'outside').strip().lower() or "outside",
                "address": row.get('address', '').strip() or None,
                "pin_code": row.get('pin_code', '').strip() or None,
                "bank_accounts": [],
                "is_vendor": True,
                "is_active": True,
                "approval_status": "approved",
                "is_suspended": False,
                "documents": [],
                "created_at": datetime.now(timezone.utc).isoformat(),
                "created_by": current_user["id"],
                "created_by_role": current_user.get("role", 1)
            }
            
            await db.clients.insert_one(vendor_doc)
            results["added"] += 1
            
        except Exception as e:
            results["errors"].append(f"Row {row_num}: {str(e)}")
    
    return {
        "message": f"Bulk upload completed. Added: {results['added']}, Skipped (duplicates): {results['skipped']}",
        "added": results["added"],
        "skipped": results["skipped"],
        "skipped_pans": results["skipped_pans"][:10],
        "errors": results["errors"][:10]
    }


@router.post("/stocks")
async def bulk_upload_stocks(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """Bulk upload stocks from CSV (PE Desk only). Skips duplicates by symbol or ISIN."""
    if not is_pe_desk_only(current_user.get("role", 6)):
        raise HTTPException(status_code=403, detail="Only PE Desk can perform bulk uploads")
    
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed")
    
    content = await file.read()
    decoded = content.decode('utf-8-sig')
    reader = csv.DictReader(io.StringIO(decoded))
    
    results = {"added": 0, "skipped": 0, "errors": [], "skipped_symbols": []}
    
    for row_num, row in enumerate(reader, start=2):
        try:
            if row.get('symbol', '').startswith('#'):
                continue
            
            symbol = row.get('symbol', '').strip().upper()
            name = row.get('name', '').strip()
            isin_number = row.get('isin_number', '').strip().upper() or None
            
            if not symbol or not name:
                results["errors"].append(f"Row {row_num}: Missing required fields (symbol, name)")
                continue
            
            # Check for duplicate symbol
            existing = await db.stocks.find_one({"symbol": symbol})
            if existing:
                results["skipped"] += 1
                results["skipped_symbols"].append(symbol)
                continue
            
            # Check for duplicate ISIN if provided
            if isin_number:
                existing_isin = await db.stocks.find_one({"isin_number": isin_number})
                if existing_isin:
                    results["skipped"] += 1
                    results["skipped_symbols"].append(f"{symbol} (ISIN exists)")
                    continue
            
            face_value = row.get('face_value', '').strip()
            
            stock_doc = {
                "id": str(uuid.uuid4()),
                "symbol": symbol,
                "name": name,
                "exchange": row.get('exchange', '').strip() or "OTC",
                "isin_number": isin_number,
                "sector": row.get('sector', '').strip() or None,
                "product": row.get('product', '').strip() or "Equity",
                "face_value": float(face_value) if face_value else None,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "created_by": current_user["id"]
            }
            
            await db.stocks.insert_one(stock_doc)
            results["added"] += 1
            
        except Exception as e:
            results["errors"].append(f"Row {row_num}: {str(e)}")
    
    return {
        "message": f"Bulk upload completed. Added: {results['added']}, Skipped (duplicates): {results['skipped']}",
        "added": results["added"],
        "skipped": results["skipped"],
        "skipped_symbols": results["skipped_symbols"][:10],
        "errors": results["errors"][:10]
    }


@router.post("/purchases")
async def bulk_upload_purchases(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """Bulk upload purchases from CSV (PE Desk only). Updates inventory automatically."""
    if not is_pe_desk_only(current_user.get("role", 6)):
        raise HTTPException(status_code=403, detail="Only PE Desk can perform bulk uploads")
    
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed")
    
    content = await file.read()
    decoded = content.decode('utf-8-sig')
    reader = csv.DictReader(io.StringIO(decoded))
    
    results = {"added": 0, "skipped": 0, "errors": []}
    
    for row_num, row in enumerate(reader, start=2):
        try:
            if row.get('vendor_pan', '').startswith('#'):
                continue
            
            vendor_pan = row.get('vendor_pan', '').strip().upper()
            stock_symbol = row.get('stock_symbol', '').strip().upper()
            quantity = row.get('quantity', '').strip()
            price_per_unit = row.get('price_per_unit', '').strip()
            purchase_date = row.get('purchase_date', '').strip()
            
            if not vendor_pan or not stock_symbol or not quantity or not price_per_unit or not purchase_date:
                results["errors"].append(f"Row {row_num}: Missing required fields")
                continue
            
            # Find vendor by PAN
            vendor = await db.clients.find_one({"pan_number": vendor_pan, "is_vendor": True}, {"_id": 0})
            if not vendor:
                results["errors"].append(f"Row {row_num}: Vendor with PAN {vendor_pan} not found")
                continue
            
            # Find stock by symbol
            stock = await db.stocks.find_one({"symbol": stock_symbol}, {"_id": 0})
            if not stock:
                results["errors"].append(f"Row {row_num}: Stock with symbol {stock_symbol} not found")
                continue
            
            qty = int(quantity)
            price = float(price_per_unit)
            total = qty * price
            
            purchase_doc = {
                "id": str(uuid.uuid4()),
                "vendor_id": vendor["id"],
                "vendor_name": vendor["name"],
                "stock_id": stock["id"],
                "stock_symbol": stock["symbol"],
                "quantity": qty,
                "price_per_unit": price,
                "total_amount": total,
                "purchase_date": purchase_date,
                "notes": row.get('notes', '').strip() or None,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "created_by": current_user["id"],
                "payments": [],
                "total_paid": 0,
                "payment_status": "pending"
            }
            
            await db.purchases.insert_one(purchase_doc)
            
            # Update inventory
            existing_inv = await db.inventory.find_one({"stock_id": stock["id"]})
            if existing_inv:
                new_qty = existing_inv["available_quantity"] + qty
                old_value = existing_inv["available_quantity"] * existing_inv["weighted_avg_price"]
                new_value = old_value + total
                new_avg = new_value / new_qty if new_qty > 0 else 0
                
                await db.inventory.update_one(
                    {"stock_id": stock["id"]},
                    {"$set": {
                        "available_quantity": new_qty,
                        "weighted_avg_price": new_avg,
                        "total_value": new_qty * new_avg
                    }}
                )
            else:
                inv_doc = {
                    "id": str(uuid.uuid4()),
                    "stock_id": stock["id"],
                    "stock_symbol": stock["symbol"],
                    "stock_name": stock["name"],
                    "available_quantity": qty,
                    "blocked_quantity": 0,
                    "weighted_avg_price": price,
                    "total_value": total
                }
                await db.inventory.insert_one(inv_doc)
            
            results["added"] += 1
            
        except Exception as e:
            results["errors"].append(f"Row {row_num}: {str(e)}")
    
    return {
        "message": f"Bulk upload completed. Added: {results['added']}",
        "added": results["added"],
        "inventory_updated": True,
        "errors": results["errors"][:10]
    }


@router.post("/bookings")
async def bulk_upload_bookings(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """Bulk upload bookings from CSV (PE Desk only). Creates bookings in 'open' status."""
    if not is_pe_desk_only(current_user.get("role", 6)):
        raise HTTPException(status_code=403, detail="Only PE Desk can perform bulk uploads")
    
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed")
    
    content = await file.read()
    decoded = content.decode('utf-8-sig')
    reader = csv.DictReader(io.StringIO(decoded))
    
    results = {"added": 0, "skipped": 0, "errors": []}
    
    for row_num, row in enumerate(reader, start=2):
        try:
            if row.get('client_pan', '').startswith('#'):
                continue
            
            client_pan = row.get('client_pan', '').strip().upper()
            stock_symbol = row.get('stock_symbol', '').strip().upper()
            quantity = row.get('quantity', '').strip()
            selling_price = row.get('selling_price', '').strip()
            booking_date = row.get('booking_date', '').strip()
            
            if not client_pan or not stock_symbol or not quantity or not selling_price or not booking_date:
                results["errors"].append(f"Row {row_num}: Missing required fields")
                continue
            
            # Find client by PAN
            client = await db.clients.find_one({"pan_number": client_pan, "is_vendor": False}, {"_id": 0})
            if not client:
                results["errors"].append(f"Row {row_num}: Client with PAN {client_pan} not found")
                continue
            
            # Find stock by symbol
            stock = await db.stocks.find_one({"symbol": stock_symbol}, {"_id": 0})
            if not stock:
                results["errors"].append(f"Row {row_num}: Stock with symbol {stock_symbol} not found")
                continue
            
            # Get inventory for buying price
            inventory = await db.inventory.find_one({"stock_id": stock["id"]}, {"_id": 0})
            buying_price = inventory["weighted_avg_price"] if inventory else 0
            
            qty = int(quantity)
            sell_price = float(selling_price)
            
            booking_number = await generate_booking_number()
            
            booking_doc = {
                "id": str(uuid.uuid4()),
                "booking_number": booking_number,
                "client_id": client["id"],
                "client_name": client["name"],
                "stock_id": stock["id"],
                "stock_symbol": stock["symbol"],
                "quantity": qty,
                "buying_price": buying_price,
                "selling_price": sell_price,
                "booking_date": booking_date,
                "status": "open",
                "booking_type": row.get('booking_type', 'client').strip().lower() or "client",
                "notes": row.get('notes', '').strip() or None,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "created_by": current_user["id"],
                "created_by_name": current_user["name"],
                "insider_form_uploaded": False,
                "stock_transferred": False,
                "payment_completed": False
            }
            
            await db.bookings.insert_one(booking_doc)
            results["added"] += 1
            
        except Exception as e:
            results["errors"].append(f"Row {row_num}: {str(e)}")
    
    return {
        "message": f"Bulk upload completed. Added: {results['added']} bookings",
        "added": results["added"],
        "errors": results["errors"][:10]
    }


@router.get("/stats")
async def get_upload_stats(current_user: dict = Depends(get_current_user)):
    """Get current counts for all entities (PE Desk only)"""
    if not is_pe_desk_only(current_user.get("role", 6)):
        raise HTTPException(status_code=403, detail="Only PE Desk can access bulk upload")
    
    clients_count = await db.clients.count_documents({"is_vendor": False})
    vendors_count = await db.clients.count_documents({"is_vendor": True})
    stocks_count = await db.stocks.count_documents({})
    purchases_count = await db.purchases.count_documents({})
    bookings_count = await db.bookings.count_documents({})
    
    return {
        "clients": clients_count,
        "vendors": vendors_count,
        "stocks": stocks_count,
        "purchases": purchases_count,
        "bookings": bookings_count
    }
